#!/usr/bin/env python3
"""
Phase 6: generates `portal/content/in_action.json`, the precomputed data
the /in-action page renders. Run once now, re-run whenever Phase 2's loop
changes. Built from the exact same functions `examples/loop_demo.py` walks
through interactively (`verifier.verify.verify`, `issuer.tamper`) — this is
a frozen snapshot of an already-tested code path, not a new computation, so
Phase 6 stays honestly "no new verifier logic."

Run: .venv/bin/python examples/generate_in_action_content.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from contracts.trust_anchor import LocalDictTrustAnchorProvider
from contracts.wallet_unlock import AlwaysYesWalletUnlockProvider
from issuer import sdjwt, tamper
from issuer.crypto import KeyPair
from issuer.pid import SAMPLE_SUBJECT, VCT, build_pid_claims
from verifier.providers import (
    LocalDictIssuerKeyDirectory,
    LocalDictRegistrationProvider,
    LocalDictStatusListProvider,
)
from verifier.verify import VerifierConfig, verify
from wallet.request import AuthorizationRequest, DcqlLiteQuery
from wallet.wallet import CredentialOffer, Wallet, verify_key_proof

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "portal" / "content" / "in_action.json"


def build_walkthroughs() -> list[dict]:
    now = int(time.time())
    issuer_kp = KeyPair.from_seed(1)
    issuer_id = "https://pid-issuer.ie.eidas-lab.example"
    verifier_id = "https://larabank.example/verify"

    wallet = Wallet(unlock_provider=AlwaysYesWalletUnlockProvider())
    offer = CredentialOffer(issuer_id=issuer_id, vct=VCT, offer_nonce="offer-nonce-1")
    proof_jwt = wallet.generate_key_proof(offer, issued_at=now)
    proof_valid, holder_jwk = verify_key_proof(proof_jwt, expected_issuer_id=issuer_id, expected_nonce=offer.offer_nonce)
    assert proof_valid

    always_visible, disclosable = build_pid_claims(SAMPLE_SUBJECT, expiry_date_iso="2035-03-11")
    credential = sdjwt.issue(
        issuer_id=issuer_id,
        issuer_private_key=issuer_kp.private_key,
        holder_public_jwk=holder_jwk,
        always_visible_claims=always_visible,
        disclosable_claims=disclosable,
        issued_at=now,
        expires_at=now + 3600 * 24 * 365,
        salt_seed=42,
    )
    wallet.receive_credential(credential, vct=offer.vct)

    trust_provider = LocalDictTrustAnchorProvider()
    trust_provider.register(issuer_id, issuer_kp.public_key, tier="PID", loa="high", anchor_id="eu-lab-anchor-1")
    key_directory = LocalDictIssuerKeyDirectory()
    key_directory.publish(issuer_id, issuer_kp.public_key)
    registration_provider = LocalDictRegistrationProvider()
    registration_provider.register(
        verifier_id, allowed_claims={"age_over_18", "nationality", "given_name"}, purpose="account-opening"
    )
    status_provider = LocalDictStatusListProvider()
    config = VerifierConfig(
        trust_provider=trust_provider,
        issuer_key_directory=key_directory,
        registration_provider=registration_provider,
        status_provider=status_provider,
    )

    request = AuthorizationRequest(
        verifier_id=verifier_id,
        nonce="lara-bank-nonce-abc123",
        query=DcqlLiteQuery(vct=VCT, required_claims=("age_over_18", "nationality"), required_tier="PID", required_loa="high"),
    )
    presentation = wallet.handle_presentation_request(request, kb_issued_at=now)

    walkthroughs = []

    happy_result = verify(presentation, request=request, config=config, now=now, presentation_id="pres-happy-001")
    walkthroughs.append(
        {
            "step_title": "Happy path",
            "narration": (
                "A PID issued to the wallet, requested by Lara Bank's verifier, presented "
                "revealing a subset of claims, and accepted — all eight checks pass in order."
            ),
            "result": happy_result,
        }
    )

    broken = tamper.broken_issuer_signature(presentation)
    tampered_result = verify(broken.credential, request=request, config=config, now=now, presentation_id="pres-tampered-001")
    walkthroughs.append(
        {
            "step_title": "Tampered presentation",
            "narration": f"Defect injected: {broken.description}. A single bit flipped in the issuer signature.",
            "result": tampered_result,
        }
    )

    empty_trust_config = VerifierConfig(
        trust_provider=LocalDictTrustAnchorProvider(),  # nothing registered
        issuer_key_directory=key_directory,
        registration_provider=registration_provider,
        status_provider=status_provider,
    )
    untrusted_result = verify(
        presentation, request=request, config=empty_trust_config, now=now, presentation_id="pres-untrusted-001"
    )
    walkthroughs.append(
        {
            "step_title": "Untrusted issuer",
            "narration": (
                "The same valid presentation, checked by a verifier with no trust registration "
                "for this issuer. issuer_signature still passes — the crypto is intact. trust_path "
                "is what fails: valid signature and trusted issuer are two different questions "
                "(ATLAS_EUDI.md §11)."
            ),
            "result": untrusted_result,
        }
    )

    return walkthroughs


def main() -> None:
    walkthroughs = build_walkthroughs()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps({"walkthroughs": walkthroughs}, indent=2) + "\n")
    print(f"wrote {len(walkthroughs)} walkthrough steps to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
