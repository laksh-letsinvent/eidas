"""
Phase-2-local provider stubs: RegistrationProvider and StatusListProvider.

Unlike `contracts.trust_anchor` and `contracts.wallet_unlock`, these are not
frozen contracts — Phase 2 owns and can evolve them. They exist to make
verifier checks 7 (registration_purpose) and 4 (revocation) fire on real
data instead of skipping, without building real RP-registration or
token-status-list infrastructure (BUILD_PROMPT_PHASE2.md scope: "minimal,
real enough to make checks 7 and 4 fire").
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from cryptography.hazmat.primitives.asymmetric import ec


# --------------------------------------------------------------------------
# IssuerKeyDirectory — "what's this issuer's signature-verification key?"
# Deliberately separate from TrustAnchorProvider. In the real ecosystem an
# issuer's signing key is resolvable from its own published metadata (a JWKS
# endpoint, or an X.509 chain) regardless of whether any given relying party
# has chosen to trust it — key resolution and accreditation are different
# questions answered by different infrastructure. Modelling them as one
# lookup would make it impossible to express "signature verifies, but this
# issuer isn't on our trusted list" (ATLAS_EUDI.md §11's first
# disambiguation) — checks 2 and 3 would collapse into one.
# --------------------------------------------------------------------------

class IssuerKeyDirectory(Protocol):
    def public_key(self, issuer_id: str) -> ec.EllipticCurvePublicKey | None:
        ...


class LocalDictIssuerKeyDirectory:
    def __init__(self) -> None:
        self._keys: dict[str, ec.EllipticCurvePublicKey] = {}

    def publish(self, issuer_id: str, public_key: ec.EllipticCurvePublicKey) -> None:
        self._keys[issuer_id] = public_key

    def public_key(self, issuer_id: str) -> ec.EllipticCurvePublicKey | None:
        return self._keys.get(issuer_id)


# --------------------------------------------------------------------------
# RegistrationProvider — "which claims is this verifier accredited to ask
# for?" A real RP registration certificate (issued under a CIR, ATLAS_EUDI.md
# "Commission Implementing Regulations") names the purpose and the attribute
# set. Over-asking — requesting or receiving a claim outside that set — is
# check 7, ATLAS_EUDI.md §9.
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class RegistrationCertificate:
    verifier_id: str
    allowed_claims: frozenset[str]
    purpose: str


class RegistrationProvider(Protocol):
    def resolve(self, verifier_id: str) -> RegistrationCertificate | None:
        """None => this verifier has no registration on file at all => every
        request from it is over-asking, regardless of which claims."""
        ...


class LocalDictRegistrationProvider:
    def __init__(self) -> None:
        self._certs: dict[str, RegistrationCertificate] = {}

    def register(self, verifier_id: str, allowed_claims: set[str] | frozenset[str], purpose: str) -> None:
        self._certs[verifier_id] = RegistrationCertificate(
            verifier_id=verifier_id, allowed_claims=frozenset(allowed_claims), purpose=purpose
        )

    def resolve(self, verifier_id: str) -> RegistrationCertificate | None:
        return self._certs.get(verifier_id)


# --------------------------------------------------------------------------
# StatusListProvider — "is this credential still live?" Modelled after the
# shape of an IETF Token Status List (a credential either is or isn't on the
# revoked set), not the bitstring encoding — the encoding isn't the lesson,
# the fact that revocation is a *separate* check from signature validity is
# (ATLAS_EUDI.md §11: "signature valid ≠ credential live").
# --------------------------------------------------------------------------

class StatusListProvider(Protocol):
    def is_revoked(self, credential_id: str) -> bool:
        ...


class LocalDictStatusListProvider:
    """Open-world stub: a credential is revoked only if explicitly added to
    the revoked set. Everything else — including credentials this provider
    has never heard of — is treated as live. That's enough to make check 4
    fire (pass for normal credentials, fail for revoked ones) without
    needing a real status-list issuer or a bitstring index scheme."""

    def __init__(self) -> None:
        self._revoked: set[str] = set()

    def revoke(self, credential_id: str) -> None:
        self._revoked.add(credential_id)

    def is_revoked(self, credential_id: str) -> bool:
        return credential_id in self._revoked
