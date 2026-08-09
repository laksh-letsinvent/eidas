"""
Tests against BUILD_PROMPT_PHASE1.md's acceptance criteria:

1. issued PID decodes to signed payload + _sd digests + separate disclosures
2. a presentation reveals a chosen subset; hidden claims are digest-only, never values
3. KB-JWT verifies against the embedded holder key over the right nonce/aud,
   fails over the wrong ones
4. every tamper function produces a *structurally* correct defect
5. the three frozen contracts are importable and the schema validates a
   hand-written sample VerificationResult
"""

from __future__ import annotations

import datetime
import json
import time
from pathlib import Path

import jsonschema
import pytest

from contracts.trust_anchor import LocalDictTrustAnchorProvider, TrustAnchorProvider, TrustResolution
from contracts.wallet_unlock import (
    AlwaysYesWalletUnlockProvider,
    PresentationContext,
    UnlockResult,
    WalletUnlockProvider,
)
from issuer import sdjwt, tamper
from issuer.crypto import KeyPair, decode_jwt_parts, es256_verify
from issuer.pid import SAMPLE_SUBJECT, build_pid_claims, compute_age_over_18
from issuer.sdjwt import Disclosure

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "contracts" / "verification_result.schema.json"


@pytest.fixture
def keys():
    return KeyPair.from_seed(1), KeyPair.from_seed(2)  # issuer, holder


@pytest.fixture
def now():
    return int(time.time())


@pytest.fixture
def claims():
    return build_pid_claims(SAMPLE_SUBJECT, expiry_date_iso="2035-03-11")


@pytest.fixture
def credential(keys, now, claims):
    issuer_kp, holder_kp = keys
    always_visible, disclosable = claims
    return sdjwt.issue(
        issuer_id="https://pid-issuer.ie.eidas-lab.example",
        issuer_private_key=issuer_kp.private_key,
        holder_public_jwk=holder_kp.public_jwk(),
        always_visible_claims=always_visible,
        disclosable_claims=disclosable,
        issued_at=now,
        expires_at=now + 3600 * 24 * 365,
        salt_seed=42,
    )


NONCE = "verifier-nonce-abc123"
AUD = "https://larabank.example/verify"
REVEAL = {"age_over_18", "nationality"}


@pytest.fixture
def presentation(credential, keys, now):
    _, holder_kp = keys
    return sdjwt.present(
        credential,
        reveal=REVEAL,
        holder_private_key=holder_kp.private_key,
        nonce=NONCE,
        aud=AUD,
        kb_issued_at=now,
    )


@pytest.fixture
def tamper_ctx(keys, now, claims):
    issuer_kp, holder_kp = keys
    always_visible, disclosable = claims
    return tamper.TamperContext(
        issuer_id="https://pid-issuer.ie.eidas-lab.example",
        issuer_private_key=issuer_kp.private_key,
        issuer_public_key=issuer_kp.public_key,
        holder_private_key=holder_kp.private_key,
        holder_public_jwk=holder_kp.public_jwk(),
        always_visible_claims=always_visible,
        disclosable_claims=disclosable,
        salt_seed=42,
        issued_at=now,
        expires_at=now + 3600 * 24 * 365,
        reveal=REVEAL,
        nonce=NONCE,
        aud=AUD,
        kb_issued_at=now,
    )


# --------------------------------------------------------------------------
# Criterion 1 — issuance decode
# --------------------------------------------------------------------------

class TestIssuance:
    def test_compact_form_has_trailing_tilde_and_five_disclosures(self, credential):
        compact = credential.compact()
        assert compact.endswith("~")
        assert compact.count("~") == 6  # 5 disclosures + trailing tilde
        assert len(credential.disclosures) == 5

    def test_decode_shows_sd_digests_and_matches_all_disclosures(self, credential, keys):
        issuer_kp, _ = keys
        report = sdjwt.decode(credential.compact(), issuer_public_key=issuer_kp.public_key)
        assert report["issuer_signature_valid"] is True
        assert len(report["payload"]["_sd"]) == 5
        assert set(report["revealed_claims"]) == {
            "family_name",
            "given_name",
            "birth_date",
            "nationality",
            "age_over_18",
        }
        assert report["hidden_claim_count"] == 0

    def test_always_visible_claims_are_in_clear_payload(self, credential):
        _, payload, _, _ = decode_jwt_parts(credential.issuer_jwt)
        assert payload["issuing_country"] == "IE"
        assert "family_name" not in payload  # disclosable claims never sit in the clear
        assert "_sd" in payload and "_sd_alg" in payload


# --------------------------------------------------------------------------
# Criterion 2 — selective disclosure at presentation
# --------------------------------------------------------------------------

class TestPresentation:
    def test_reveals_only_requested_subset(self, presentation, keys):
        issuer_kp, _ = keys
        report = sdjwt.decode(presentation, issuer_public_key=issuer_kp.public_key)
        assert set(report["revealed_claims"]) == REVEAL
        assert report["revealed_claims"]["nationality"] == "IE"
        assert report["revealed_claims"]["age_over_18"] is True

    def test_hidden_claims_never_appear_as_values(self, presentation, keys):
        issuer_kp, _ = keys
        report = sdjwt.decode(presentation, issuer_public_key=issuer_kp.public_key)
        hidden_names = {"family_name", "given_name", "birth_date"}
        assert not hidden_names & set(report["revealed_claims"])
        assert report["hidden_claim_count"] == 3
        # the raw wire string must not contain the withheld plaintext values at all
        assert "O'Connell" not in presentation
        assert "Aoife" not in presentation
        assert "1994-03-11" not in presentation


# --------------------------------------------------------------------------
# Criterion 3 — key binding
# --------------------------------------------------------------------------

class TestKeyBinding:
    def test_kb_jwt_verifies_over_right_nonce_and_aud(self, presentation, keys):
        issuer_kp, _ = keys
        report = sdjwt.decode(
            presentation, issuer_public_key=issuer_kp.public_key, expected_nonce=NONCE, expected_aud=AUD
        )
        kb = report["kb_jwt"]
        assert kb["signature_valid"] is True
        assert kb["sd_hash_matches"] is True
        assert kb["nonce_matches"] is True
        assert kb["aud_matches"] is True

    def test_kb_jwt_fails_over_wrong_nonce_or_aud(self, presentation, keys):
        issuer_kp, _ = keys
        report = sdjwt.decode(
            presentation,
            issuer_public_key=issuer_kp.public_key,
            expected_nonce="some-other-nonce",
            expected_aud="https://someone-else.example",
        )
        kb = report["kb_jwt"]
        assert kb["signature_valid"] is True  # signature itself is still valid...
        assert kb["nonce_matches"] is False  # ...but it was signed over the wrong nonce
        assert kb["aud_matches"] is False  # ...and the wrong audience

    def test_kb_jwt_signature_rejected_by_holder_key_mismatch(self, presentation):
        wrong_holder = KeyPair.generate()
        _, _, kb_jwt = sdjwt.split_compact(presentation)
        _, _, sig, signing_input = decode_jwt_parts(kb_jwt)
        assert es256_verify(wrong_holder.public_key, signing_input, sig) is False


# --------------------------------------------------------------------------
# Criterion 4 — tamper harness produces structurally correct defects
# --------------------------------------------------------------------------

class TestTamperHarness:
    def test_altered_disclosed_claim_digest_mismatches(self, presentation, keys):
        issuer_kp, _ = keys
        original_salt = next(
            d.salt for d in (Disclosure.parse(b) for b in sdjwt.split_compact(presentation)[1]) if d.name == "nationality"
        )
        variant = tamper.altered_disclosed_claim(presentation, "nationality", "XX")
        report = sdjwt.decode(variant.credential, issuer_public_key=issuer_kp.public_key)
        assert variant.species == "altered_disclosed_claim"
        assert any(u["name"] == "nationality" for u in report["unmatched_disclosures"])
        assert "nationality" not in report["revealed_claims"]
        # the recomputed digest (same salt, new value) really does differ from every signed digest
        tampered_digest = Disclosure.create(original_salt, "nationality", "XX").digest
        assert tampered_digest not in report["payload"]["_sd"]

    def test_broken_issuer_signature_fails_verification_only(self, presentation, keys):
        issuer_kp, _ = keys
        variant = tamper.broken_issuer_signature(presentation)
        report = sdjwt.decode(variant.credential, issuer_public_key=issuer_kp.public_key)
        assert variant.species == "broken_issuer_signature"
        assert report["issuer_signature_valid"] is False
        # disclosures themselves are untouched — digests still match
        assert report["unmatched_disclosures"] == []
        # sd_hash *does* cascade-fail here: it's computed over the whole
        # issuer-JWT string, signature included, so flipping a signature byte
        # changes that string and the untouched KB-JWT's sd_hash no longer
        # matches it. One edit, two check failures — a real interaction, not
        # a second independent defect.
        assert report["kb_jwt"]["sd_hash_matches"] is False

    def test_stripped_kb_jwt_removes_holder_binding_entirely(self, presentation, keys):
        issuer_kp, _ = keys
        variant = tamper.stripped_kb_jwt(presentation)
        report = sdjwt.decode(variant.credential, issuer_public_key=issuer_kp.public_key)
        assert variant.species == "stripped_kb_jwt"
        assert report["kb_jwt"] is None
        assert report["issuer_signature_valid"] is True  # everything else still verifies

    def test_wrong_audience_kb_jwt_signs_over_different_aud(self, tamper_ctx, credential, keys):
        issuer_kp, _ = keys
        variant = tamper.wrong_audience_kb_jwt(tamper_ctx, credential, wrong_aud="https://attacker.example")
        report = sdjwt.decode(
            variant.credential, issuer_public_key=issuer_kp.public_key, expected_nonce=NONCE, expected_aud=AUD
        )
        assert variant.species == "wrong_audience_kb_jwt"
        assert report["kb_jwt"]["signature_valid"] is True  # validly signed...
        assert report["kb_jwt"]["aud_matches"] is False  # ...just not for this verifier

    def test_stale_nonce_kb_jwt_signs_over_different_nonce(self, tamper_ctx, credential, keys):
        issuer_kp, _ = keys
        variant = tamper.stale_nonce_kb_jwt(tamper_ctx, credential, stale_nonce="old-nonce")
        report = sdjwt.decode(
            variant.credential, issuer_public_key=issuer_kp.public_key, expected_nonce=NONCE, expected_aud=AUD
        )
        assert variant.species == "stale_nonce_kb_jwt"
        assert report["kb_jwt"]["signature_valid"] is True
        assert report["kb_jwt"]["nonce_matches"] is False

    def test_expired_credential_has_past_exp_but_verifies_otherwise(self, tamper_ctx, now, keys):
        issuer_kp, _ = keys
        variant = tamper.expired_credential(tamper_ctx, expired_at=now - 3600)
        report = sdjwt.decode(
            variant.credential, issuer_public_key=issuer_kp.public_key, expected_nonce=NONCE, expected_aud=AUD
        )
        assert variant.species == "expired_credential"
        assert report["payload"]["exp"] < now
        assert report["issuer_signature_valid"] is True
        assert report["kb_jwt"]["signature_valid"] is True
        assert report["kb_jwt"]["sd_hash_matches"] is True

    def test_generate_all_variants_covers_all_six_species(self, tamper_ctx, credential, presentation):
        variants = tamper.generate_all_variants(tamper_ctx, credential, presentation)
        assert {v.species for v in variants} == {
            "altered_disclosed_claim",
            "broken_issuer_signature",
            "stripped_kb_jwt",
            "wrong_audience_kb_jwt",
            "stale_nonce_kb_jwt",
            "expired_credential",
        }


# --------------------------------------------------------------------------
# Criterion 5 — frozen contracts
# --------------------------------------------------------------------------

class TestFrozenContracts:
    def test_trust_anchor_provider_stub_resolves_registered_issuer(self, keys):
        issuer_kp, _ = keys
        provider: TrustAnchorProvider = LocalDictTrustAnchorProvider()
        provider.register("https://pid-issuer.ie.eidas-lab.example", issuer_kp.public_key, tier="PID", loa="high")

        resolution = provider.resolve("https://pid-issuer.ie.eidas-lab.example")
        assert isinstance(resolution, TrustResolution)
        assert resolution.tier == "PID"
        assert resolution.loa == "high"

        assert provider.resolve("https://unknown-issuer.example") is None

    def test_wallet_unlock_provider_stub_always_authorizes(self):
        provider: WalletUnlockProvider = AlwaysYesWalletUnlockProvider()
        ctx = PresentationContext(
            credential_id="cred-1", audience=AUD, nonce=NONCE, requested_claims=("age_over_18",)
        )
        result = provider.authorize(ctx)
        assert isinstance(result, UnlockResult)
        assert result.authorized is True

    def test_verification_result_schema_validates_hand_written_sample(self):
        schema = json.loads(SCHEMA_PATH.read_text())
        sample = {
            "schema_version": "wallet-1.0",
            "presentation_id": "pres-0001",
            "decision": "accept",
            "checks": [
                {"name": "format", "result": "pass", "detail": None},
                {"name": "issuer_signature", "result": "pass", "detail": None},
                {"name": "trust_path", "result": "pass", "detail": "anchor lab-anchor-1"},
                {"name": "revocation", "result": "skip", "detail": "not implemented in Phase 1/2"},
                {"name": "disclosure_integrity", "result": "pass", "detail": None},
                {"name": "key_binding", "result": "pass", "detail": None},
                {"name": "registration_purpose", "result": "skip", "detail": None},
                {"name": "policy", "result": "pass", "detail": None},
            ],
            "trust": {"tier": "PID", "anchor_id": "lab-anchor-1", "loa": "high"},
            "policy_version": "policy-0.1",
            "qes": None,
            "timing": {"total_ms": 4.2},
        }
        jsonschema.validate(sample, schema)  # raises on failure

    def test_verification_result_schema_rejects_bad_decision(self):
        schema = json.loads(SCHEMA_PATH.read_text())
        sample = {
            "schema_version": "wallet-1.0",
            "presentation_id": "pres-0001",
            "decision": "maybe",
            "checks": [],
            "trust": {"tier": None, "anchor_id": None, "loa": None},
            "policy_version": "policy-0.1",
            "qes": None,
            "timing": {"total_ms": 1.0},
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(sample, schema)


# --------------------------------------------------------------------------
# PID claim helpers
# --------------------------------------------------------------------------

class TestPidClaims:
    def test_age_over_18_derivation(self):
        assert compute_age_over_18("1994-03-11", as_of=datetime.date(2026, 7, 20)) is True
        assert compute_age_over_18("2015-01-01", as_of=datetime.date(2026, 7, 20)) is False

    def test_build_pid_claims_splits_correctly(self, claims):
        always_visible, disclosable = claims
        assert set(always_visible) == {"issuing_country", "issuing_authority"}
        assert set(disclosable) == {"family_name", "given_name", "birth_date", "nationality", "age_over_18"}
