"""
Frozen contract #3: WalletUnlockProvider.

The question a wallet asks itself before releasing a credential for a given
presentation: "may this be released?" v1 is always-yes because Phase 1's
"holder" is a keypair and a function, not a wallet with a user to gate.
Freezing this now is what keeps the PWA wallet (Phase 3.5, WebAuthn) and the
trilogy option (Face Value matcher as step-up) additive later, per
CLAUDE.md's frozen-contracts section.

Do not add parameters to `authorize` without raising it as a scope decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PresentationContext:
    """What the wallet knows about the presentation it's being asked to release."""

    credential_id: str
    audience: str
    nonce: str
    requested_claims: tuple[str, ...]


@dataclass(frozen=True)
class UnlockResult:
    authorized: bool
    reason: str


class WalletUnlockProvider(Protocol):
    def authorize(self, presentation_context: PresentationContext) -> UnlockResult:
        ...


class AlwaysYesWalletUnlockProvider:
    """Phase 1 stub. Every presentation is authorized, unconditionally."""

    def authorize(self, presentation_context: PresentationContext) -> UnlockResult:
        return UnlockResult(authorized=True, reason="always-yes stub (Phase 1)")
