"""
Frozen contract #2: TrustAnchorProvider.

The single question a verifier asks about an issuer: is it trusted, at what
tier, under which framework, and what's its anchor? EU trusted list (Phase 2)
and a DIATF-style anchor (Phase 5, the UK swap) are both just implementations
of `resolve()`. Phase 1 ships only the local-dict stub below, wired to the
issuer keypair(s) this phase actually creates — enough to keep the interface
honest without building a trust list.

Do not add methods or change `resolve`'s signature without raising it as a
scope decision (CLAUDE.md "frozen contracts").
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from cryptography.hazmat.primitives.asymmetric import ec

Tier = str  # "PID" | "QEAA" | "PuB-EAA" | "EAA" — see VerificationResult.trust.tier
Loa = str  # "high" | "substantial" | "low"


@dataclass(frozen=True)
class TrustResolution:
    issuer_id: str
    tier: Tier
    loa: Loa
    anchor_id: str
    public_key: ec.EllipticCurvePublicKey


class TrustAnchorProvider(Protocol):
    def resolve(self, issuer_id: str) -> TrustResolution | None:
        """Return the issuer's trust resolution, or None if it's on no trusted list at all."""
        ...


class LocalDictTrustAnchorProvider:
    """Phase 1/2 stub: a hardcoded dict standing in for a trusted list.

    Not a real trust list — no chain-of-trust validation, no expiry, no
    revocation of the anchor itself. It exists only so the verifier (Phase 2)
    can call a real `TrustAnchorProvider` instead of hardcoding key lookups.
    """

    def __init__(self) -> None:
        self._issuers: dict[str, TrustResolution] = {}

    def register(
        self,
        issuer_id: str,
        public_key: ec.EllipticCurvePublicKey,
        tier: Tier = "PID",
        loa: Loa = "high",
        anchor_id: str = "lab-anchor-1",
    ) -> None:
        self._issuers[issuer_id] = TrustResolution(
            issuer_id=issuer_id,
            tier=tier,
            loa=loa,
            anchor_id=anchor_id,
            public_key=public_key,
        )

    def resolve(self, issuer_id: str) -> TrustResolution | None:
        return self._issuers.get(issuer_id)
