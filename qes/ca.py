"""
Toy CA chain for the QES track: root CA -> intermediate QTSP -> leaf signer,
built with `cryptography.x509` directly — hand-rolled, matching Phase 1's
ethos, since building the chain (not wrapping it in a PDF) is the mechanism
that's the point of this module. PDF/CMS embedding is `qes/pades.py`'s job,
delegated to pyHanko because that part is mature plumbing, not the lesson.

The whole AES-vs-QES distinction lives in one place: `build_leaf_cert`'s
`qualified` flag, which attaches (or omits) the real ETSI EN 319 412-5
`qcStatements` X.509 extension (id-pe-qcStatements, OID 1.3.6.1.5.5.7.1.3,
carrying a `qc_compliance` statement, OID 0.4.0.1862.1.1). Everything else
about a "qualified" and an "advanced" leaf cert in this lab is identical —
same chain, same key usage, same algorithm — because in the real world it's
supposed to be: qualified status is a legal/procedural fact the QTSP
asserts, not a cryptographic difference. See docs/AES_VS_QES.md.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field

import pyhanko.sign.ades.qualified_asn1 as qualified_asn1
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from issuer.crypto import KeyPair

# id-pe-qcStatements (RFC 3739 / ETSI EN 319 412-5) — the X.509 extension
# that carries the QcStatements SEQUENCE below.
QC_STATEMENTS_EXTENSION_OID = x509.ObjectIdentifier("1.3.6.1.5.5.7.1.3")

_DEFAULT_NOT_BEFORE = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)


def _qc_compliance_extension_value() -> bytes:
    """DER bytes for a QcStatements SEQUENCE carrying exactly one statement:
    qc_compliance (ETSI EN 319 412-5, OID 0.4.0.1862.1.1) — "this is a
    Qualified Certificate." Built with pyHanko's own asn1crypto classes
    (pyhanko.sign.ades.qualified_asn1), the same library that reads this
    extension back on the verify side — not hand-rolled DER."""
    statement = qualified_asn1.QcStatement({"statement_id": "qc_compliance"})
    return qualified_asn1.QcStatements([statement]).dump()


def _name(common_name: str) -> x509.Name:
    return x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "IE"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "eIDAS Lab"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]
    )


def _ca_key_usage() -> x509.KeyUsage:
    return x509.KeyUsage(
        digital_signature=False,
        content_commitment=False,
        key_encipherment=False,
        data_encipherment=False,
        key_agreement=False,
        key_cert_sign=True,
        crl_sign=True,
        encipher_only=False,
        decipher_only=False,
    )


def _signing_key_usage() -> x509.KeyUsage:
    return x509.KeyUsage(
        digital_signature=True,
        content_commitment=True,  # formerly "non_repudiation" — the AdES sole-control bit
        key_encipherment=False,
        data_encipherment=False,
        key_agreement=False,
        key_cert_sign=False,
        crl_sign=False,
        encipher_only=False,
        decipher_only=False,
    )


def build_root_ca(
    key: KeyPair,
    *,
    common_name: str = "eIDAS Lab Root CA",
    not_before: datetime.datetime | None = None,
    not_after: datetime.datetime | None = None,
) -> x509.Certificate:
    """Self-signed root — the trust anchor everything else chains to.
    `common_name` defaults to the lab's real root; callers building a
    *second*, deliberately untrusted root (`build_untrusted_root_and_leaf`)
    must pass a distinct name — reusing the same subject name as the real
    root confuses X.509 path-building (which can match candidates by name),
    even though the keys themselves are unrelated."""
    subject = _name(common_name)
    not_before = not_before or _DEFAULT_NOT_BEFORE
    not_after = not_after or not_before + datetime.timedelta(days=3650)
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_after)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(_ca_key_usage(), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key), critical=False)
    )
    return builder.sign(key.private_key, hashes.SHA256())


def build_qtsp_intermediate(
    issuer_cert: x509.Certificate,
    issuer_key: KeyPair,
    qtsp_key: KeyPair,
    *,
    not_before: datetime.datetime | None = None,
    not_after: datetime.datetime | None = None,
) -> x509.Certificate:
    """The toy QTSP: an intermediate CA the root vouches for. `path_length=0`
    means it can issue leaf certs but not further intermediates."""
    not_before = not_before or _DEFAULT_NOT_BEFORE
    not_after = not_after or not_before + datetime.timedelta(days=1825)
    builder = (
        x509.CertificateBuilder()
        .subject_name(_name("eIDAS Lab QTSP"))
        .issuer_name(issuer_cert.subject)
        .public_key(qtsp_key.public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_after)
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(_ca_key_usage(), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(qtsp_key.public_key), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(issuer_key.public_key), critical=False)
    )
    return builder.sign(issuer_key.private_key, hashes.SHA256())


def build_leaf_cert(
    issuer_cert: x509.Certificate,
    issuer_key: KeyPair,
    signer_key: KeyPair,
    *,
    qualified: bool,
    common_name: str = "eIDAS Lab QES Signer",
    not_before: datetime.datetime | None = None,
    not_after: datetime.datetime | None = None,
) -> x509.Certificate:
    """The document-signing leaf cert. `qualified=True` attaches the real
    qcStatements extension; `qualified=False` produces an otherwise-identical
    "advanced" (AES) certificate — same key usage, same chain, same
    everything except this one legal marker."""
    not_before = not_before or _DEFAULT_NOT_BEFORE
    not_after = not_after or not_before + datetime.timedelta(days=365)
    builder = (
        x509.CertificateBuilder()
        .subject_name(_name(common_name))
        .issuer_name(issuer_cert.subject)
        .public_key(signer_key.public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_after)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(_signing_key_usage(), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(signer_key.public_key), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(issuer_key.public_key), critical=False)
    )
    if qualified:
        builder = builder.add_extension(
            x509.UnrecognizedExtension(QC_STATEMENTS_EXTENSION_OID, _qc_compliance_extension_value()),
            critical=False,
        )
    return builder.sign(issuer_key.private_key, hashes.SHA256())


def build_untrusted_root_and_leaf(signer_key: KeyPair) -> tuple[x509.Certificate, x509.Certificate]:
    """A second, entirely separate root + leaf — never registered as a trust
    anchor anywhere in this lab. For `chain_to_untrusted_ca`: a signature
    that's cryptographically clean but chains to a root nobody trusts."""
    untrusted_root_key = KeyPair.from_seed(9099)
    untrusted_root_cert = build_root_ca(untrusted_root_key, common_name="Some Other CA (untrusted)")
    untrusted_leaf_cert = build_leaf_cert(
        untrusted_root_cert, untrusted_root_key, signer_key, qualified=True, common_name="Untrusted-Root Signer"
    )
    return untrusted_root_cert, untrusted_leaf_cert


def generate_tsa_rsa_key() -> rsa.RSAPrivateKey:
    """The toy TSA's own signing key. RSA, not P-256 — a narrow, deliberate
    exception: pyHanko's offline toy TSA (`DummyTimeStamper`, see
    qes/pades.py) requires an RSA key, and `issuer.crypto.KeyPair` is
    deliberately P-256-only by design. This is plumbing for the TSA's own
    signature only — the document signer's key stays P-256/ES256
    throughout, unaffected by this exception."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def build_tsa_cert(
    issuer_cert: x509.Certificate,
    issuer_key: KeyPair,
    tsa_private_key: rsa.RSAPrivateKey,
    *,
    not_before: datetime.datetime | None = None,
    not_after: datetime.datetime | None = None,
) -> x509.Certificate:
    """The toy TSA's own cert, signed by the QTSP — so the timestamp chains
    to the same trust root as the document signature it stamps."""
    not_before = not_before or _DEFAULT_NOT_BEFORE
    not_after = not_after or not_before + datetime.timedelta(days=1825)
    builder = (
        x509.CertificateBuilder()
        .subject_name(_name("eIDAS Lab TSA"))
        .issuer_name(issuer_cert.subject)
        .public_key(tsa_private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_after)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(_signing_key_usage(), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.TIME_STAMPING]), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(tsa_private_key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(issuer_key.public_key), critical=False)
    )
    return builder.sign(issuer_key.private_key, hashes.SHA256())


@dataclass(frozen=True)
class CaWorld:
    """Everything a demo/test needs: the whole chain, both leaf variants,
    the TSA, an untrusted second chain, and a toy revocation set.

    `revoked_serials` is a hand-rolled in-memory set keyed by certificate
    serial number — not pyHanko's own CRL/OCSP machinery, which is
    real-protocol-shaped and heavier (and network-riskier) than this lab
    needs. Same pattern as `verifier/providers.py`'s
    `LocalDictStatusListProvider`: revocation is a set-membership question,
    not the lesson."""

    root_key: KeyPair
    root_cert: x509.Certificate
    qtsp_key: KeyPair
    qtsp_cert: x509.Certificate
    signer_key: KeyPair
    qualified_leaf_cert: x509.Certificate
    advanced_leaf_cert: x509.Certificate
    tsa_rsa_key: rsa.RSAPrivateKey
    tsa_cert: x509.Certificate
    untrusted_root_cert: x509.Certificate
    untrusted_leaf_cert: x509.Certificate
    revoked_serials: set[int] = field(default_factory=set)


def build_ca_world() -> CaWorld:
    """One-call fixture, mirrors `eval.species.build_world()`. Deterministic
    (seeded P-256 keys) except the TSA's RSA key, which `cryptography`
    doesn't offer a seeded-generation path for — reproducibility there isn't
    needed since the TSA's key never affects which check catches which
    defect, only the timestamp signature bytes."""
    root_key = KeyPair.from_seed(9001)
    root_cert = build_root_ca(root_key)

    qtsp_key = KeyPair.from_seed(9002)
    qtsp_cert = build_qtsp_intermediate(root_cert, root_key, qtsp_key)

    signer_key = KeyPair.from_seed(9003)
    qualified_leaf_cert = build_leaf_cert(qtsp_cert, qtsp_key, signer_key, qualified=True)
    advanced_leaf_cert = build_leaf_cert(
        qtsp_cert, qtsp_key, signer_key, qualified=False, common_name="eIDAS Lab AES Signer"
    )

    tsa_rsa_key = generate_tsa_rsa_key()
    tsa_cert = build_tsa_cert(qtsp_cert, qtsp_key, tsa_rsa_key)

    untrusted_root_cert, untrusted_leaf_cert = build_untrusted_root_and_leaf(signer_key)

    return CaWorld(
        root_key=root_key,
        root_cert=root_cert,
        qtsp_key=qtsp_key,
        qtsp_cert=qtsp_cert,
        signer_key=signer_key,
        qualified_leaf_cert=qualified_leaf_cert,
        advanced_leaf_cert=advanced_leaf_cert,
        tsa_rsa_key=tsa_rsa_key,
        tsa_cert=tsa_cert,
        untrusted_root_cert=untrusted_root_cert,
        untrusted_leaf_cert=untrusted_leaf_cert,
    )
