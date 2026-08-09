"""
qes/verify_pades.py — thin orchestration producing the schema-shaped `qes`
result object (`contracts/verification_result.schema.json`'s `qes` field).

Deliberately never called from `verifier/verify.py`, and `verify_pades()`
here is never called from there either. A PAdES-signed PDF is a completely
different document from an SD-JWT wallet presentation — no KB-JWT, no DCQL
request, no `AuthorizationRequest` to check it against. Forcing it through
`verify()`'s signature would mean inventing a fake wallet request for a PDF,
which is dishonest. `verify()` continues to always emit `"qes": None`; this
module's output is only ever placed into that field by a caller that has
independently decided to report both a wallet check and a QES check in one
record — which nothing in this lab currently does, by design.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field

from cryptography import x509
from pyhanko.sign.ades.qualified_asn1 import get_qc_statements

from qes.ca import CaWorld
from qes.pades import verify_pades_signature


@dataclass(frozen=True)
class QesVerifierConfig:
    trust_roots: list[x509.Certificate]
    revoked_serials: set[int] = field(default_factory=set)
    anchor_id: str | None = "eidas-lab-qtsp-root-1"


def config_from_ca_world(world: CaWorld) -> QesVerifierConfig:
    return QesVerifierConfig(trust_roots=[world.root_cert], revoked_serials=world.revoked_serials)


def _is_qualified(signing_cert) -> bool:
    """Reads the qcStatements extension straight off the signing cert —
    'everything cryptographically passed' is a completely separate question
    from 'is this a Qualified Certificate.' See qes/ca.py and
    docs/AES_VS_QES.md."""
    if signing_cert is None:
        return False
    statements = get_qc_statements(signing_cert)
    return any(s["statement_id"].native == "qc_compliance" for s in statements)


def verify_pades(pdf_bytes: bytes, config: QesVerifierConfig, *, now: datetime.datetime) -> dict:
    """Returns a dict matching the `qes` sub-object shape:
    signature_valid, chain_trusted, document_unmodified, timestamp_valid,
    is_qualified, anchor_id, detail.

    `document_unmodified` is its own field, deliberately not folded into
    `signature_valid`: a document changed via a further incremental update
    *after* signing still has a perfectly intact, valid, trusted signature
    over the *original* revision — pyHanko's own diff-analysis engine
    (`status.docmdp_ok`/`modification_level`) is what catches the
    after-the-fact change, and it's a genuinely separate question from
    whether the signature itself verifies, the same way this lab's wallet
    track keeps disclosure_integrity and key_binding as separate checks
    rather than one catch-all "the credential is fine" boolean."""
    try:
        status = verify_pades_signature(pdf_bytes, trust_roots=config.trust_roots, now=now)
    except Exception as exc:
        return {
            "signature_valid": False,
            "chain_trusted": False,
            "document_unmodified": False,
            "timestamp_valid": None,
            "is_qualified": False,
            "anchor_id": None,
            "detail": f"could not parse or verify the embedded signature: {exc}",
        }

    signature_valid = bool(status.intact and status.valid)
    chain_trusted = bool(status.trusted)
    document_unmodified = bool(status.docmdp_ok)

    # Revocation is deliberately NOT pyHanko's own CRL/OCSP support — a
    # trivial post-check against the toy revocation set instead, entirely
    # outside pyHanko, same set-membership pattern as the wallet track's
    # LocalDictStatusListProvider. See qes/ca.py's CaWorld docstring.
    serial = status.signing_cert.serial_number if status.signing_cert is not None else None
    revoked = serial is not None and serial in config.revoked_serials
    if revoked:
        chain_trusted = False

    timestamp_valid: bool | None = None
    if status.timestamp_validity is not None:
        ts = status.timestamp_validity
        timestamp_valid = bool(ts.intact and ts.valid and ts.trusted)

    is_qualified = _is_qualified(status.signing_cert)

    detail_parts: list[str] = []
    if not signature_valid:
        detail_parts.append("signature does not verify against the signed byte range")
    if not document_unmodified:
        detail_parts.append("the document was modified after the signature was applied")
    if revoked:
        detail_parts.append("signing certificate is on the revoked set")
    elif not chain_trusted:
        detail_parts.append("certificate chain does not resolve to a trusted anchor")
    if status.timestamp_validity is None:
        detail_parts.append("no timestamp present")
    elif not timestamp_valid:
        detail_parts.append("timestamp present but invalid or untrusted")
    if signature_valid and chain_trusted and not is_qualified:
        detail_parts.append("certificate is Advanced (AES), not Qualified (QES) — no qcStatements extension")

    return {
        "signature_valid": signature_valid,
        "chain_trusted": chain_trusted,
        "document_unmodified": document_unmodified,
        "timestamp_valid": timestamp_valid,
        "is_qualified": is_qualified,
        "anchor_id": config.anchor_id if chain_trusted else None,
        "detail": "; ".join(detail_parts) if detail_parts else None,
    }
