"""
pyHanko wiring: the PDF/CMS plumbing layer. Everything in `qes/ca.py` is
hand-rolled because the CA chain is the mechanism this lab teaches; this
module is deliberately a thin wrapper around a mature library, because
PAdES's byte-range digest, CMS SignedData structure, and PDF incremental
updates are established machinery, not the lesson (BUILD_PROMPT_PHASE4-6.md;
same reasoning as Phase 3.5 using FastAPI rather than hand-rolling an HTTP
server).

Revocation is deliberately NOT checked here via pyHanko's own CRL/OCSP
support — that machinery is real-protocol-shaped and heavier (and
network-riskier) than this lab needs. `qes/verify_pades.py` layers a
trivial post-check against `CaWorld.revoked_serials` instead, entirely
outside pyHanko, guaranteeing zero network risk from that path.
"""

from __future__ import annotations

import datetime
from io import BytesIO

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa
from pyhanko.keys.internal import (
    translate_pyca_cryptography_cert_to_asn1,
    translate_pyca_cryptography_key_to_asn1,
)
from pyhanko.pdf_utils import generic
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.pdf_utils.writer import PageObject, PdfFileWriter
from pyhanko.sign.fields import SigSeedSubFilter
from pyhanko.sign.signers import SimpleSigner
from pyhanko.sign.signers.functions import sign_pdf
from pyhanko.sign.signers.pdf_signer import PdfSignatureMetadata
from pyhanko.sign.timestamps.dummy_client import DummyTimeStamper
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko.sign.validation.pdf_embedded import collect_embedded_signatures
from pyhanko.sign.validation.status import PdfSignatureStatus
from pyhanko_certvalidator.context import ValidationContext
from pyhanko_certvalidator.registry import SimpleCertificateStore

from issuer.crypto import KeyPair

FIELD_NAME = "Signature1"


def to_asn1_cert(cert: x509.Certificate):
    return translate_pyca_cryptography_cert_to_asn1(cert)


def to_asn1_key(private_key):
    return translate_pyca_cryptography_key_to_asn1(private_key)


def build_signer(leaf_cert: x509.Certificate, signer_key: KeyPair, chain_certs: list[x509.Certificate]) -> SimpleSigner:
    """The document signer. `chain_certs` (QTSP + root) are registered into
    the embedded certificate store so the signature carries its own chain —
    a verifier doesn't need out-of-band access to the intermediate."""
    registry = SimpleCertificateStore()
    registry.register_multiple(to_asn1_cert(c) for c in chain_certs)
    return SimpleSigner(
        signing_cert=to_asn1_cert(leaf_cert),
        signing_key=to_asn1_key(signer_key.private_key),
        cert_registry=registry,
    )


def build_dummy_timestamper(
    tsa_cert: x509.Certificate,
    tsa_rsa_key: rsa.RSAPrivateKey,
    chain_certs: list[x509.Certificate],
    fixed_dt: datetime.datetime | None = None,
) -> DummyTimeStamper:
    """pyHanko's own offline, self-signing toy TSA — no RFC 3161 network
    call. `chain_certs` (QTSP + root) are embedded alongside the timestamp
    token, same reason as `build_signer`'s `cert_registry`: without them, a
    verifier can build a path for the *document* signature but not for the
    *timestamp*'s own signing cert, since they're separate CMS structures.
    `fixed_dt` pins the timestamp for reproducible demo/test output, same
    pattern as `eval/corpus.py`'s `DEFAULT_NOW`."""
    registry = SimpleCertificateStore()
    registry.register_multiple(to_asn1_cert(c) for c in chain_certs)
    return DummyTimeStamper(
        tsa_cert=to_asn1_cert(tsa_cert),
        tsa_key=to_asn1_key(tsa_rsa_key),
        certs_to_embed=registry,
        fixed_dt=fixed_dt,
    )


def make_blank_pdf() -> bytes:
    """A minimal one-page valid PDF to sign. Content is irrelevant — the
    lesson is the signature, not the document — so the content stream is
    deliberately empty rather than pulling in font/text-rendering plumbing."""
    writer = PdfFileWriter()
    content_stream = generic.StreamObject({}, stream_data=b"")
    content_ref = writer.add_object(content_stream)
    page = PageObject(contents=content_ref, media_box=[0, 0, 612, 792])
    writer.insert_page(page)
    buf = BytesIO()
    writer.write(buf)
    return buf.getvalue()


def sign_pdf_qes(pdf_bytes: bytes, *, signer: SimpleSigner, timestamper: DummyTimeStamper | None, field_name: str = FIELD_NAME) -> bytes:
    """Sign `pdf_bytes` with a PAdES baseline-B signature (subfilter
    ETSI.CAdES.detached). `timestamper=None` produces a signature with no
    embedded timestamp token at all — used by the
    `missing_or_forged_timestamp` tamper generator, not just a valid path."""
    incremental_writer = IncrementalPdfFileWriter(BytesIO(pdf_bytes))
    signature_meta = PdfSignatureMetadata(field_name=field_name, subfilter=SigSeedSubFilter.PADES)
    signed = sign_pdf(incremental_writer, signature_meta, signer=signer, timestamper=timestamper)
    return signed.getvalue() if hasattr(signed, "getvalue") else bytes(signed)


def verify_pades_signature(
    pdf_bytes: bytes, *, trust_roots: list[x509.Certificate], now: datetime.datetime
) -> PdfSignatureStatus:
    """Offline chain validation (`allow_fetching=False` — no OCSP/CRL
    network fetch) against exactly the given trust roots. Returns pyHanko's
    own `PdfSignatureStatus` for the first (only, in this lab) embedded
    signature — callers read `.intact`, `.trusted`, `.timestamp_validity`."""
    reader = PdfFileReader(BytesIO(pdf_bytes))
    signatures = list(collect_embedded_signatures(reader))
    if not signatures:
        raise ValueError("no embedded signature found in this PDF")

    validation_context = ValidationContext(
        trust_roots=[to_asn1_cert(root) for root in trust_roots],
        allow_fetching=False,
        moment=now,
    )
    return validate_pdf_signature(
        signatures[0],
        signer_validation_context=validation_context,
        ts_validation_context=validation_context,
    )
