"""
The five QES break-it experiments (BUILD_PROMPT_PHASE4-6.md), mirroring
`issuer.tamper`'s single-defect-variant pattern: each function produces a
signed PDF with exactly one thing wrong, labelled with which field in
`qes/verify_pades.py`'s output should flip.

Four of the five are straightforward rejections. The fifth,
`advanced_not_qualified_cert_as_qes`, is deliberately NOT a rejection —
everything about it verifies cleanly. That's the phase's actual lesson: a
correct QES verifier's job on that one isn't to reject, it's to correctly
report `is_qualified=False`. See docs/AES_VS_QES.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from pyhanko.pdf_utils import generic
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.pdf_utils.writer import PageObject

from qes.ca import CaWorld
from qes.pades import build_dummy_timestamper, build_signer, make_blank_pdf, sign_pdf_qes


@dataclass(frozen=True)
class TamperedPades:
    species: str
    pdf_bytes: bytes
    description: str
    expected_field: str  # which qes/verify_pades.py output field should flip


def _baseline_signed_pdf(world: CaWorld, *, leaf_cert=None, chain_certs=None, use_timestamper: bool = True) -> bytes:
    leaf_cert = leaf_cert if leaf_cert is not None else world.qualified_leaf_cert
    chain_certs = chain_certs if chain_certs is not None else [world.qtsp_cert, world.root_cert]
    signer = build_signer(leaf_cert, world.signer_key, chain_certs)
    timestamper = None
    if use_timestamper:
        timestamper = build_dummy_timestamper(world.tsa_cert, world.tsa_rsa_key, [world.qtsp_cert, world.root_cert])
    return sign_pdf_qes(make_blank_pdf(), signer=signer, timestamper=timestamper)


def document_modified_after_signing(world: CaWorld) -> TamperedPades:
    """Sign normally, then perform a *second* incremental update on the
    already-signed PDF (insert a page) without re-signing. The original
    signature stays perfectly intact/valid/trusted over its own revision —
    pyHanko's diff-analysis engine is what catches the after-the-fact
    change (`document_unmodified` flips, nothing else does)."""
    signed_pdf = _baseline_signed_pdf(world)
    writer = IncrementalPdfFileWriter(BytesIO(signed_pdf))
    injected_stream = generic.StreamObject({}, stream_data=b"injected-after-signing")
    content_ref = writer.add_object(injected_stream)
    writer.insert_page(PageObject(contents=content_ref, media_box=[0, 0, 612, 792]))
    buf = BytesIO()
    writer.write(buf)
    return TamperedPades(
        species="document_modified_after_signing",
        pdf_bytes=buf.getvalue(),
        description="a page was inserted via a second incremental update after the signature was applied",
        expected_field="document_unmodified",
    )


def signature_from_revoked_cert(world: CaWorld) -> TamperedPades:
    """Sign normally with the qualified leaf, then add that leaf's serial
    to the world's toy revocation set. Caught by `verify_pades()`'s
    post-pyHanko revocation lookup, not by pyHanko itself (see
    qes/verify_pades.py's docstring)."""
    signed_pdf = _baseline_signed_pdf(world)
    world.revoked_serials.add(world.qualified_leaf_cert.serial_number)
    return TamperedPades(
        species="signature_from_revoked_cert",
        pdf_bytes=signed_pdf,
        description="signed with a certificate whose serial is on the revoked set",
        expected_field="chain_trusted",
    )


def missing_or_forged_timestamp(world: CaWorld) -> TamperedPades:
    """Sign with no timestamper at all — the simplest, unambiguous
    "no timestamp" defect. (A second variant — a timestamp from a TSA whose
    own cert doesn't chain to the trust root — is a documented alternative,
    not a sixth species: see this module's docstring.)"""
    signed_pdf = _baseline_signed_pdf(world, use_timestamper=False)
    return TamperedPades(
        species="missing_or_forged_timestamp",
        pdf_bytes=signed_pdf,
        description="signed with no timestamper — no timestamp token embedded at all",
        expected_field="timestamp_valid",
    )


def chain_to_untrusted_ca(world: CaWorld) -> TamperedPades:
    """Sign with a leaf cert issued by the entirely separate untrusted root
    (`CaWorld.untrusted_root_cert`) — cryptographically clean, but the root
    is never registered as a trust anchor."""
    signed_pdf = _baseline_signed_pdf(
        world, leaf_cert=world.untrusted_leaf_cert, chain_certs=[world.untrusted_root_cert]
    )
    return TamperedPades(
        species="chain_to_untrusted_ca",
        pdf_bytes=signed_pdf,
        description="signed by a certificate chaining to a root that isn't a registered trust anchor",
        expected_field="chain_trusted",
    )


def advanced_not_qualified_cert_as_qes(world: CaWorld) -> TamperedPades:
    """Sign with the advanced (AES) leaf cert — no qcStatements extension —
    but otherwise a perfectly clean, fully-chained, timestamped signature.
    NOT a rejection: `signature_valid`, `chain_trusted`, `document_unmodified`,
    and `timestamp_valid` all stay True. Only `is_qualified` flips. This is
    the experiment where "everything passed" correctly does NOT mean
    "this is a QES" — the whole point of the phase."""
    signed_pdf = _baseline_signed_pdf(world, leaf_cert=world.advanced_leaf_cert)
    return TamperedPades(
        species="advanced_not_qualified_cert_as_qes",
        pdf_bytes=signed_pdf,
        description="signed with an Advanced (AES) certificate — no qcStatements extension — everything else clean",
        expected_field="is_qualified",
    )


ALL_EXPERIMENTS = (
    document_modified_after_signing,
    signature_from_revoked_cert,
    missing_or_forged_timestamp,
    chain_to_untrusted_ca,
    advanced_not_qualified_cert_as_qes,
)
