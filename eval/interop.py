"""
Interop cross-check: a correctness sanity check against the community `sd-jwt`
reference implementation (PyPI `sd-jwt`, the SPRIND/OpenWallet-Foundation-Labs
Python package implementing the IETF SD-JWT / SD-JWT VC drafts) — not a
runtime dependency of anything else in this lab. If our hand-rolled issuer
and decoder disagree with a library that exists specifically to implement
the spec, that's a bug in us, not a matter of opinion.

Both directions are checked:
  (a) a presentation our issuer/wallet produced, parsed and verified by
      their `SDJWTVerifier`
  (b) a credential their `SDJWTIssuer` produced, parsed and verified by our
      own `issuer.sdjwt.decode`

Install: `pip install sd-jwt` (already in this repo's `.venv`). Not imported
anywhere outside this module — the hand-rolled core stays the point.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

from jwcrypto.jwk import JWK
from sd_jwt.common import SDObj
from sd_jwt.issuer import SDJWTIssuer
from sd_jwt.verifier import SDJWTVerifier

from issuer import sdjwt
from issuer.crypto import KeyPair, jwk_to_public_key
from issuer.pid import SAMPLE_SUBJECT, VCT, build_pid_claims

ISSUER_ID = "https://pid-issuer.ie.eidas-lab.example"
VERIFIER_ID = "https://larabank.example/verify"

# Known, non-blocking format deltas between the two implementations —
# documented rather than papered over (BUILD_PROMPT_PHASE3.md "Interop
# cross-check": "Document any delta from the drafts.").
KNOWN_DELTAS = (
    "header `typ`: ours is `dc+sd-jwt` (current SD-JWT VC media type), "
    "theirs defaults to `example+sd-jwt` (their reference-example value). "
    "Neither verifier enforces the other's `typ` on the outer SD-JWT — only "
    "the KB-JWT's `typ: kb+jwt` is checked by both — so this never affects "
    "acceptance, only how a decoder might route by content type.",
)


@dataclass(frozen=True)
class InteropCheckResult:
    name: str
    passed: bool
    detail: str


def check_our_presentation_with_reference_verifier(now: int) -> InteropCheckResult:
    """(a): our issuer + wallet produce a presentation; their SDJWTVerifier
    checks issuer signature, disclosure integrity, and key binding (aud/nonce/
    sd_hash) — all of it, not just a parse."""
    issuer_kp = KeyPair.from_seed(1)
    holder_kp = KeyPair.from_seed(2)
    always_visible, disclosable = build_pid_claims(SAMPLE_SUBJECT, expiry_date_iso="2035-03-11")

    credential = sdjwt.issue(
        issuer_id=ISSUER_ID,
        issuer_private_key=issuer_kp.private_key,
        holder_public_jwk=holder_kp.public_jwk(),
        always_visible_claims=always_visible,
        disclosable_claims=disclosable,
        issued_at=now,
        expires_at=now + 3600 * 24 * 365,
        salt_seed=42,
    )
    nonce, aud = "interop-nonce", VERIFIER_ID
    presentation = sdjwt.present(
        credential,
        reveal={"age_over_18", "nationality"},
        holder_private_key=holder_kp.private_key,
        nonce=nonce,
        aud=aud,
        kb_issued_at=now,
    )

    issuer_jwk = JWK.from_json(json.dumps(issuer_kp.public_jwk()))

    def cb_get_issuer_key(issuer: str, header: dict) -> JWK:
        return issuer_jwk

    try:
        verifier = SDJWTVerifier(presentation, cb_get_issuer_key, expected_aud=aud, expected_nonce=nonce)
        payload = verifier.get_verified_payload()
    except Exception as exc:
        return InteropCheckResult("reference_verifies_our_presentation", False, f"reference library rejected a valid presentation: {exc}")

    expected_revealed = {"nationality": "IE", "age_over_18": True}
    actual_revealed = {k: payload.get(k) for k in expected_revealed}
    if actual_revealed != expected_revealed:
        return InteropCheckResult(
            "reference_verifies_our_presentation",
            False,
            f"revealed claims mismatch: expected {expected_revealed}, got {actual_revealed}",
        )
    hidden_leaked = any(k in payload for k in ("family_name", "given_name", "birth_date"))
    if hidden_leaked:
        return InteropCheckResult("reference_verifies_our_presentation", False, "a withheld claim leaked into the reference library's decoded payload")

    return InteropCheckResult(
        "reference_verifies_our_presentation",
        True,
        "reference SDJWTVerifier accepted our presentation: issuer signature, key binding (aud/nonce/sd_hash), and selective disclosure all verified correctly",
    )


def check_reference_credential_with_our_decoder(now: int) -> InteropCheckResult:
    """(b): their SDJWTIssuer produces a credential; our own `decode`
    verifies the issuer signature and unpacks the disclosures."""
    issuer_jwk = JWK.generate(kty="EC", crv="P-256")
    holder_jwk = JWK.generate(kty="EC", crv="P-256")

    always_visible, disclosable = build_pid_claims(SAMPLE_SUBJECT, expiry_date_iso="2035-03-11")
    claims: dict = {
        "iss": ISSUER_ID,
        "vct": VCT,
        "iat": now,
        "exp": now + 3600 * 24 * 365,
        **always_visible,
        **{SDObj(k): v for k, v in disclosable.items()},
    }

    try:
        reference_issuer = SDJWTIssuer(claims, issuer_jwk, holder_jwk)
        combined = reference_issuer.sd_jwt_issuance
    except Exception as exc:
        return InteropCheckResult("our_decoder_verifies_reference_credential", False, f"reference issuer failed to produce a credential: {exc}")

    issuer_public_key = jwk_to_public_key(json.loads(issuer_jwk.export_public()))
    report = sdjwt.decode(combined, issuer_public_key=issuer_public_key)

    if report["issuer_signature_valid"] is not True:
        return InteropCheckResult("our_decoder_verifies_reference_credential", False, "our decoder could not verify the reference issuer's signature")

    if report["revealed_claims"] != disclosable:
        return InteropCheckResult(
            "our_decoder_verifies_reference_credential",
            False,
            f"disclosed claims mismatch: expected {disclosable}, got {report['revealed_claims']}",
        )

    return InteropCheckResult(
        "our_decoder_verifies_reference_credential",
        True,
        "our decode() correctly verified the reference SDJWTIssuer's signature and unpacked every disclosure",
    )


def run_interop_check(now: int | None = None) -> dict:
    now = now if now is not None else int(time.time())
    results = [
        check_our_presentation_with_reference_verifier(now),
        check_reference_credential_with_our_decoder(now),
    ]
    return {
        "reference_library": "sd-jwt (PyPI)",
        "checks": [{"name": r.name, "passed": r.passed, "detail": r.detail} for r in results],
        "all_passed": all(r.passed for r in results),
        "known_deltas": list(KNOWN_DELTAS),
    }
