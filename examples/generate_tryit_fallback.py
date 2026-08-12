#!/usr/bin/env python3
"""
Phase 9: generates `portal/content/tryit_fallback.json` — a committed twin
for every live surface in Try It (BUILD_PROMPT_PHASE7-9.md), so the page
degrades to a recorded run when `localhost:8420` is absent instead of
showing an error to a visitor who was never going to have the local
service running. Built from the exact same fixture `service/main.py` uses
(`eval.species.build_world`/`good_config`) so the numbers a visitor sees
here match what the live service would actually produce — not a second,
drifting set of fake data.

Run: .venv/bin/python examples/generate_tryit_fallback.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from contracts.wallet_unlock import AlwaysYesWalletUnlockProvider
from eval.species import GENERATORS, build_world, good_config
from issuer import sdjwt
from verifier.verify import verify
from wallet.request import AuthorizationRequest, DcqlLiteQuery
from wallet.wallet import CredentialOffer, Wallet, verify_key_proof

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "portal" / "content" / "tryit_fallback.json"

# Mirrors service/main.py's TAMPER_DEMO_SPECIES exactly.
SPECIES = (
    "genuine",
    "broken_issuer_signature",
    "altered_disclosed_claim",
    "stripped_kb_jwt",
    "expired_credential",
    "cross_device_origin_phish",
)

PHISHING_ORIGIN = "https://lara-bank-secure.verify-id.co"


def _issue_and_hold(world, config, index: int, now: int):
    wallet = Wallet(unlock_provider=AlwaysYesWalletUnlockProvider())
    offer = CredentialOffer(issuer_id=world.issuer_id, vct=sdjwt.VCT, offer_nonce=f"offer-nonce-{index}")
    proof = wallet.generate_key_proof(offer, issued_at=now)
    _, holder_jwk = verify_key_proof(proof, expected_issuer_id=world.issuer_id, expected_nonce=offer.offer_nonce)
    credential = sdjwt.issue(
        issuer_id=world.issuer_id,
        issuer_private_key=world.issuer_kp.private_key,
        holder_public_jwk=holder_jwk,
        always_visible_claims=world.always_visible_claims,
        disclosable_claims=world.disclosable_claims,
        issued_at=now,
        expires_at=now + 3600 * 24 * 365,
        salt_seed=3000 + index,
    )
    wallet.receive_credential(credential, vct=offer.vct)
    return wallet


def _present(world, wallet, config, *, required_claims, verifier_id, nonce, now):
    request = AuthorizationRequest(
        verifier_id=verifier_id,
        nonce=nonce,
        query=DcqlLiteQuery(vct=sdjwt.VCT, required_claims=tuple(required_claims), required_tier="PID", required_loa="high"),
    )
    presentation = wallet.handle_presentation_request(request, kb_issued_at=now)
    return presentation, request


def build_fallback() -> dict:
    now = int(time.time())
    world = build_world()
    config = good_config(world)

    # -- "Get your wallet": a representative held-credential summary -----
    wallet_summary = {
        "vct": sdjwt.VCT,
        "disclosable_claim_count": len(world.disclosable_claims),
    }

    # -- "Open a bank account": the real 2-claim default -----------------
    bank_wallet = _issue_and_hold(world, config, 1, now)
    bank_presentation, bank_request = _present(
        world, bank_wallet, config,
        required_claims=("age_over_18", "nationality"),
        verifier_id=world.verifier_id, nonce="fallback-nonce-bank", now=now,
    )
    bank_result = verify(bank_presentation, request=bank_request, config=config, now=now, presentation_id="fallback-bank-001")

    # -- "Prove you are over 18": 1 claim, client-constructed request ----
    age_wallet = _issue_and_hold(world, config, 2, now)
    age_presentation, age_request = _present(
        world, age_wallet, config,
        required_claims=("age_over_18",),
        verifier_id=world.verifier_id, nonce="fallback-nonce-age", now=now,
    )
    age_result = verify(age_presentation, request=age_request, config=config, now=now, presentation_id="fallback-age-001")

    # -- "A scammer tries it on": same-tab phishing relay -----------------
    phish_wallet = _issue_and_hold(world, config, 3, now)
    phish_presentation, _phish_built_request = _present(
        world, phish_wallet, config,
        required_claims=("age_over_18", "nationality"),
        verifier_id=PHISHING_ORIGIN, nonce="fallback-nonce-phish", now=now,
    )
    # The relay forwards to the REAL verifier_id — same nonce, so the
    # verifier's own request is what's actually checked against.
    real_phish_request = AuthorizationRequest(
        verifier_id=world.verifier_id,
        nonce="fallback-nonce-phish",
        query=DcqlLiteQuery(vct=sdjwt.VCT, required_claims=("age_over_18", "nationality"), required_tier="PID", required_loa="high"),
    )
    phish_result = verify(phish_presentation, request=real_phish_request, config=config, now=now, presentation_id="fallback-phish-001")

    # -- six live species, same generators the corpus and /tamper-demo use
    species_out = {}
    for species in SPECIES:
        item = GENERATORS[species](world, index=9000, now=now)
        result = verify(item.presentation, request=item.request, config=item.verifier_config, now=now, presentation_id=f"fallback-{species}-001")
        species_out[species] = {
            "description": item.description,
            "expected_decision": item.expected_decision,
            "expected_check": item.expected_check,
            "presentation": item.presentation,
            "request": {
                "verifier_id": item.request.verifier_id,
                "nonce": item.request.nonce,
                "query": {
                    "vct": item.request.query.vct,
                    "required_claims": list(item.request.query.required_claims),
                    "required_tier": item.request.query.required_tier,
                    "required_loa": item.request.query.required_loa,
                },
            },
            "result": result,
        }

    return {
        "wallet": wallet_summary,
        "bank": {"presentation": bank_presentation, "result": bank_result},
        "age": {"presentation": age_presentation, "result": age_result},
        "phish": {
            "presentation": phish_presentation,
            "result": phish_result,
            "phishing_origin": PHISHING_ORIGIN,
            "real_verifier_id": world.verifier_id,
        },
        "species": species_out,
    }


def main() -> None:
    fallback = build_fallback()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(fallback, indent=2) + "\n")
    print(f"wrote Try It fallback data ({len(fallback['species'])} species) to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
