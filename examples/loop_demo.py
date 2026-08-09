#!/usr/bin/env python3
"""
Phase 2 walkthrough: the full three-actor loop. An issuer issues a PID to a
wallet (OpenID4VCI-lite); Lara Bank's verifier asks for a subset of claims
(OpenID4VP-lite, DCQL-lite); the wallet presents; the verifier runs its
eight ordered checks and emits a `VerificationResult`. Then the same loop
runs again with one tampered presentation, to see a reject and read exactly
which check caught it.

Run: .venv/bin/python examples/loop_demo.py
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

SEP = "\n" + "=" * 78 + "\n"


def section(title: str) -> None:
    print(SEP + title + SEP)


def print_result(result: dict) -> None:
    print(f"decision: {result['decision'].upper()}  (presentation_id={result['presentation_id']})")
    print(f"trust: {result['trust']}")
    for check in result["checks"]:
        marker = {"pass": "PASS", "fail": "FAIL", "skip": "skip"}[check["result"]]
        detail = f" — {check['detail']}" if check["detail"] else ""
        print(f"  [{marker:4s}] {check['name']:22s}{detail}")
    print(f"timing: {result['timing']['total_ms']:.3f} ms")


def main() -> None:
    now = int(time.time())
    issuer_kp = KeyPair.from_seed(1)
    issuer_id = "https://pid-issuer.ie.eidas-lab.example"
    verifier_id = "https://larabank.example/verify"

    section("STEP 1 — issuance (OpenID4VCI-lite)")
    wallet = Wallet(unlock_provider=AlwaysYesWalletUnlockProvider())
    offer = CredentialOffer(issuer_id=issuer_id, vct=VCT, offer_nonce="offer-nonce-1")
    print(f"issuer offers: vct={offer.vct}, nonce={offer.offer_nonce!r}")

    proof_jwt = wallet.generate_key_proof(offer, issued_at=now)
    print("wallet proves possession of its holder key (proof-of-possession JWT, header carries the JWK)")

    proof_valid, holder_jwk = verify_key_proof(proof_jwt, expected_issuer_id=issuer_id, expected_nonce=offer.offer_nonce)
    print(f"issuer verifies the proof: valid={proof_valid}")

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
    print(f"issuer issues a PID bound to the wallet's key; wallet now holds {len(credential.disclosures)} disclosures")

    section("STEP 2 — configure Lara Bank's verifier")
    trust_provider = LocalDictTrustAnchorProvider()
    trust_provider.register(issuer_id, issuer_kp.public_key, tier="PID", loa="high", anchor_id="eu-lab-anchor-1")
    print(f"trust anchor: {issuer_id} registered as tier=PID, loa=high, anchor=eu-lab-anchor-1")

    key_directory = LocalDictIssuerKeyDirectory()
    key_directory.publish(issuer_id, issuer_kp.public_key)
    print("issuer key directory: issuer's signature-verification key published (separate from trust)")

    registration_provider = LocalDictRegistrationProvider()
    registration_provider.register(
        verifier_id, allowed_claims={"age_over_18", "nationality", "given_name"}, purpose="account-opening"
    )
    print("registration: Lara Bank is accredited to ask for age_over_18, nationality, given_name — account-opening")

    status_provider = LocalDictStatusListProvider()
    print("status list: empty — nothing revoked yet")

    config = VerifierConfig(
        trust_provider=trust_provider,
        issuer_key_directory=key_directory,
        registration_provider=registration_provider,
        status_provider=status_provider,
    )

    section("STEP 3 — presentation request (OpenID4VP-lite, DCQL-lite)")
    request = AuthorizationRequest(
        verifier_id=verifier_id,
        nonce="lara-bank-nonce-abc123",
        query=DcqlLiteQuery(
            vct=VCT,
            required_claims=("age_over_18", "nationality"),
            required_tier="PID",
            required_loa="high",
        ),
    )
    print(f"Lara Bank asks for: {request.query.required_claims}, nonce={request.nonce!r}, aud={request.verifier_id!r}")

    presentation = wallet.handle_presentation_request(request, kb_issued_at=now)
    print("wallet checks it holds every requested claim, calls WalletUnlockProvider.authorize, then presents")

    section("STEP 4 — verify: happy path")
    result = verify(presentation, request=request, config=config, now=now, presentation_id="pres-happy-001")
    print_result(result)

    section("STEP 5 — verify: a tampered presentation (broken issuer signature)")
    ctx = tamper.TamperContext(
        issuer_id=issuer_id,
        issuer_private_key=issuer_kp.private_key,
        issuer_public_key=issuer_kp.public_key,
        holder_private_key=wallet.holder_keypair.private_key,
        holder_public_jwk=wallet.holder_keypair.public_jwk(),
        always_visible_claims=always_visible,
        disclosable_claims=disclosable,
        salt_seed=42,
        issued_at=now,
        expires_at=now + 3600 * 24 * 365,
        reveal=set(request.query.required_claims),
        nonce=request.nonce,
        aud=request.verifier_id,
        kb_issued_at=now,
    )
    broken = tamper.broken_issuer_signature(presentation)
    print(f"defect injected: {broken.description}")
    bad_result = verify(broken.credential, request=request, config=config, now=now, presentation_id="pres-tampered-001")
    print_result(bad_result)

    section("STEP 6 — verify: an untrusted issuer")
    empty_trust_config = VerifierConfig(
        trust_provider=LocalDictTrustAnchorProvider(),  # nothing registered
        issuer_key_directory=key_directory,  # key still resolvable — signature will verify fine
        registration_provider=registration_provider,
        status_provider=status_provider,
    )
    untrusted_result = verify(
        presentation, request=request, config=empty_trust_config, now=now, presentation_id="pres-untrusted-001"
    )
    print("Same valid presentation, but this verifier has no trust registration for the issuer:")
    print_result(untrusted_result)
    print()
    print("Notice: issuer_signature still PASSes — the crypto is intact. trust_path is what")
    print("fails. Valid signature and trusted issuer are two different questions (ATLAS_EUDI.md §11).")

    section("done")
    print("Eight checks, three outcomes: a clean accept, a hard-gate reject (crypto), and a")
    print("trust-path reject (accreditation) on an otherwise perfectly valid credential.")
    print("Phase 3 builds the defect corpus and confusion matrix across all of this.")


if __name__ == "__main__":
    main()
