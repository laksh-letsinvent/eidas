#!/usr/bin/env python3
"""
Phase 1 walkthrough: issue a PID, decode it, selectively disclose from it,
tamper with it. Read this output top to bottom — it is the SD-JWT VC
mechanism, not a description of it.

Run: .venv/bin/python examples/issue_and_inspect.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from issuer import sdjwt, tamper
from issuer.crypto import KeyPair
from issuer.pid import SAMPLE_SUBJECT, build_pid_claims

SEP = "\n" + "=" * 78 + "\n"


def section(title: str) -> None:
    print(SEP + title + SEP)


def main() -> None:
    now = int(time.time())

    # --- Step 0: keys. One issuer, one holder. Seeded, so this is the same
    # keypair on every run — a real issuer would never do this. ---------
    issuer_kp = KeyPair.from_seed(1)
    holder_kp = KeyPair.from_seed(2)
    issuer_id = "https://pid-issuer.ie.eidas-lab.example"

    section("STEP 1 — issue a PID")
    always_visible, disclosable = build_pid_claims(SAMPLE_SUBJECT, expiry_date_iso="2035-03-11")
    print("subject (never written to the credential in this form):", SAMPLE_SUBJECT)
    print()
    print("always-visible claims (sit in the clear in the signed payload):", always_visible)
    print("disclosable claims (each becomes a salted disclosure, only its")
    print("  digest reaches the signed payload):", disclosable)

    credential = sdjwt.issue(
        issuer_id=issuer_id,
        issuer_private_key=issuer_kp.private_key,
        holder_public_jwk=holder_kp.public_jwk(),
        always_visible_claims=always_visible,
        disclosable_claims=disclosable,
        issued_at=now,
        expires_at=now + 3600 * 24 * 365,
        salt_seed=42,
    )
    print()
    print("issued credential, compact form (issuer-jwt~disclosure~disclosure~...~):")
    print(credential.compact())

    section("STEP 2 — decode the issued credential")
    report = sdjwt.decode(credential.compact(), issuer_public_key=issuer_kp.public_key)
    print(sdjwt.pretty_print(report))
    print()
    print("Notice: every claim is 'revealed' here because decode() was given every")
    print("disclosure the issuer produced. A holder in the wild only forwards a")
    print("subset at presentation time — that's step 3.")

    section("STEP 3 — present a subset (selective disclosure)")
    nonce = "verifier-nonce-abc123"
    aud = "https://larabank.example/verify"
    reveal = {"age_over_18", "nationality"}
    print(f"Lara Bank's verifier asks for: {sorted(reveal)}, nonce={nonce!r}, aud={aud!r}")

    presentation = sdjwt.present(
        credential,
        reveal=reveal,
        holder_private_key=holder_kp.private_key,
        nonce=nonce,
        aud=aud,
        kb_issued_at=now,
    )
    print()
    print("presentation, compact form (issuer-jwt~disclosure~...~KB-JWT):")
    print(presentation)

    print()
    print("decoded:")
    pres_report = sdjwt.decode(
        presentation,
        issuer_public_key=issuer_kp.public_key,
        expected_nonce=nonce,
        expected_aud=aud,
    )
    print(sdjwt.pretty_print(pres_report))
    print()
    print(f"family_name, given_name, and birth_date are withheld: only their digests")
    print(f"survive in _sd, with no matching disclosure in this presentation.")
    print(f"hidden_claim_count = {pres_report['hidden_claim_count']} (3 withheld of 5 total)")

    section("STEP 4 — tamper: six single-defect variants")
    ctx = tamper.TamperContext(
        issuer_id=issuer_id,
        issuer_private_key=issuer_kp.private_key,
        issuer_public_key=issuer_kp.public_key,
        holder_private_key=holder_kp.private_key,
        holder_public_jwk=holder_kp.public_jwk(),
        always_visible_claims=always_visible,
        disclosable_claims=disclosable,
        salt_seed=42,
        issued_at=now,
        expires_at=now + 3600 * 24 * 365,
        reveal=reveal,
        nonce=nonce,
        aud=aud,
        kb_issued_at=now,
    )
    variants = tamper.generate_all_variants(ctx, credential, presentation)

    for variant in variants:
        print(f"\n--- {variant.species} ---")
        print(f"defect: {variant.description}")
        r = sdjwt.decode(
            variant.credential,
            issuer_public_key=issuer_kp.public_key,
            expected_nonce=nonce,
            expected_aud=aud,
        )
        print(f"  issuer_signature_valid = {r['issuer_signature_valid']}")
        print(f"  unmatched_disclosures  = {[u['name'] for u in r['unmatched_disclosures']]}")
        if r["kb_jwt"] is None:
            print("  kb_jwt = absent")
        else:
            kb = r["kb_jwt"]
            print(
                f"  kb_jwt.signature_valid = {kb['signature_valid']}, "
                f"sd_hash_matches = {kb['sd_hash_matches']}, "
                f"nonce_matches = {kb.get('nonce_matches')}, "
                f"aud_matches = {kb.get('aud_matches')}"
            )
        print(f"  exp = {r['payload'].get('exp')} (now = {now})")

    section("done")
    print("Every variant above differs from the valid presentation in exactly one")
    print("field. Phase 2's verifier will map each of these fields to a named check")
    print("(ATLAS_EUDI.md §9) and a pass/fail column in the eval's confusion matrix.")


if __name__ == "__main__":
    main()
