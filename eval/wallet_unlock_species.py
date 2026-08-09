"""
`stolen_device_presentation` — the fourteenth species in the taxonomy, and
the one that never enters `eval/matrix.py`'s confusion matrix at all.

Every other species (Phase 3's twelve, Phase 3.5's `cross_device_origin_phish`)
produces a presentation that reaches `verifier.verify()`, so it always has a
`VerificationResult` to score. `stolen_device_presentation` is different by
construction: it models a WebAuthn release that is *denied* — a stolen or
unlocked device where the platform-authenticator gesture fails or is
cancelled. Per `wallet/wallet.py`'s `handle_presentation_request`, a denied
`WalletUnlockProvider.authorize()` call raises `WalletCannotSatisfyRequest`
*before* `issuer.sdjwt.present` is ever invoked — no presentation is built,
so `verifier.verify()` is never called, so there is no 8-check
`VerificationResult` to classify as caught/missed/wrong_check/etc.

This is not a coverage gap to paper over. Both `contracts/verification_result.
schema.json` (frozen, `checks[].name` is a closed 8-value enum) and
`schemas/eval_result.schema.json` (Phase 3's, currently green across every
test) would have to grow a 9th/6th enum value to fold this species into the
existing matrix — and `expected_check: null` already means "genuine" there;
reusing it for "never reached the verifier" would conflate two different
reasons nothing fired. Recorded separately instead: `UnlockAttemptRecord` is
not a `VerificationResult` and never claims to be one. This is a deliberate,
confirmed design decision (not a unilateral one) — see CLAUDE.md's Phase 3.5
section.

The live PWA demonstrates the same fact end to end: cancelling the WebAuthn
prompt in `UnlockGate.tsx` blocks release and the wallet never calls
`POST /present` or `POST /verify` — verifiable via network inspection, not
just by reading this module.
"""

from __future__ import annotations

from dataclasses import dataclass

from contracts.wallet_unlock import PresentationContext, UnlockResult
from eval.species import DEFAULT_REQUIRED_CLAIMS, World
from issuer import sdjwt
from issuer.pid import VCT
from wallet.request import AuthorizationRequest, DcqlLiteQuery
from wallet.wallet import CredentialOffer, Wallet, WalletCannotSatisfyRequest, verify_key_proof
from issuer.crypto import KeyPair


class AlwaysNoWalletUnlockProvider:
    """The mirror image of `contracts.wallet_unlock.AlwaysYesWalletUnlockProvider`
    — every presentation is denied, unconditionally. Models a WebAuthn
    gesture that always fails: cancelled, no matching authenticator, or a
    stolen/locked device. Local to this module, not added to
    `contracts/wallet_unlock.py`, which stays frozen with only the
    always-yes stub."""

    def authorize(self, presentation_context: PresentationContext) -> UnlockResult:
        return UnlockResult(authorized=False, reason="webauthn gesture denied (stolen/locked device stub)")


@dataclass(frozen=True)
class UnlockAttemptRecord:
    item_id: str
    species: str
    unlock_result: UnlockResult
    blocked: bool
    description: str


def stolen_device_presentation_attempt(world: World, index: int, now: int) -> UnlockAttemptRecord:
    """Issue a real PID to a real wallet, then attempt a presentation with
    release denied — confirms the wallet never reaches `sdjwt.present` at
    all, not merely that it declines to send the result."""
    holder_kp = KeyPair.from_seed(1000 + index)
    wallet = Wallet(unlock_provider=AlwaysNoWalletUnlockProvider(), holder_keypair=holder_kp)

    offer = CredentialOffer(issuer_id=world.issuer_id, vct=VCT, offer_nonce=f"offer-nonce-{index}")
    proof = wallet.generate_key_proof(offer, issued_at=now)
    proof_valid, holder_jwk = verify_key_proof(proof, expected_issuer_id=world.issuer_id, expected_nonce=offer.offer_nonce)
    assert proof_valid

    credential = sdjwt.issue(
        issuer_id=world.issuer_id,
        issuer_private_key=world.issuer_kp.private_key,
        holder_public_jwk=holder_jwk,
        always_visible_claims=world.always_visible_claims,
        disclosable_claims=world.disclosable_claims,
        issued_at=now,
        expires_at=now + 3600 * 24 * 365,
        salt_seed=2000 + index,
    )
    wallet.receive_credential(credential, vct=offer.vct)

    request = AuthorizationRequest(
        verifier_id=world.verifier_id,
        nonce=f"verifier-nonce-{index}",
        query=DcqlLiteQuery(vct=VCT, required_claims=DEFAULT_REQUIRED_CLAIMS, required_tier="PID", required_loa="high"),
    )

    unlock_result = wallet.unlock_provider.authorize(
        PresentationContext(
            credential_id=credential.issuer_jwt,
            audience=request.verifier_id,
            nonce=request.nonce,
            requested_claims=request.query.required_claims,
        )
    )

    blocked = False
    try:
        wallet.handle_presentation_request(request, kb_issued_at=now)
    except WalletCannotSatisfyRequest:
        blocked = True

    return UnlockAttemptRecord(
        item_id=f"stolen_device_presentation-{index:03d}",
        species="stolen_device_presentation",
        unlock_result=unlock_result,
        blocked=blocked,
        description="WebAuthn release denied (device stolen/locked); no presentation was ever built",
    )


def build_unlock_gate_result(records: list[UnlockAttemptRecord]) -> dict:
    """A small, deliberately schema-less artefact (`results/wallet_unlock_gate.json`)
    — one boolean fact repeated a few times doesn't need a formal JSON Schema
    the way `eval-1.0` does."""
    return {
        "species": "stolen_device_presentation",
        "note": "checked before any presentation exists; not part of the eval-1.0 confusion matrix (see this module's docstring)",
        "n": len(records),
        "all_blocked": all(r.blocked for r in records),
        "attempts": [
            {
                "item_id": r.item_id,
                "unlock_authorized": r.unlock_result.authorized,
                "unlock_reason": r.unlock_result.reason,
                "blocked": r.blocked,
                "description": r.description,
            }
            for r in records
        ],
    }
