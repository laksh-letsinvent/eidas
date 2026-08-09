"""
Phase 5's UK-side `TrustAnchorProvider` implementation: a DIATF/DVS-style
anchor, alongside the existing EU one (`contracts/trust_anchor.py`'s
`LocalDictTrustAnchorProvider`). Implements the frozen Protocol exactly —
same `resolve(issuer_id) -> TrustResolution | None` shape, no new methods —
because the whole point of Phase 5 is that the verifier and the corpus
don't need to know or care which trust framework they're running under.

`trust.tier` in `contracts/verification_result.schema.json` is a closed
enum (`"PID"|"QEAA"|"PuB-EAA"|"EAA"|null`) shaped around eIDAS's own
vocabulary — DIATF has no equivalent categories, and this frozen schema
cannot be widened for Phase 5 (the one sanctioned schema change across
Phases 4-6 is Phase 4's `qes` field). A GOV.UK-style state credential is
mapped onto `tier="PID"` *functionally* — it plays the same
foundational-identity role a PID plays under eIDAS — not because DIATF
actually has a PID concept. The real EU/UK distinction lives in `anchor_id`
and the `FRAMEWORK` constant below, both read directly by
`docs/TWO_POSTURE.md` and `examples/anchor_swap_demo.py`, neither part of
the schema or the frozen `TrustResolution` dataclass. This is an
acknowledged modeling compromise, not a claim that DIATF has an
eIDAS-shaped tier system — see `docs/TWO_POSTURE.md`.
"""

from __future__ import annotations

from cryptography.hazmat.primitives.asymmetric import ec

from contracts.trust_anchor import Loa, Tier, TrustResolution


class DiatfAnchorProvider:
    """UK DVS/DIATF-style trust anchor. Structurally near-identical to
    `contracts.trust_anchor.LocalDictTrustAnchorProvider` — that's
    deliberate, it demonstrates the same Protocol works for a completely
    different real-world framework — but kept as its own class, not a
    subclass, so it's an honest second implementation, not an inherited
    variant that could blur "these are the same thing with a different
    constructor default." """

    FRAMEWORK = "UK DIATF/DVS"

    def __init__(self) -> None:
        self._issuers: dict[str, TrustResolution] = {}

    def register(
        self,
        issuer_id: str,
        public_key: ec.EllipticCurvePublicKey,
        tier: Tier = "PID",
        loa: Loa = "high",
        anchor_id: str = "uk-diatf-anchor-1",
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
