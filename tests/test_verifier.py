"""
Tests against BUILD_PROMPT_PHASE2.md's acceptance criteria:

1. happy path accepts, every applicable check passes, schema-valid
2. every Phase 1 tamper species rejects at the correct check
3. untrusted issuer rejects at trust_path even with a valid signature
4. revoked credential rejects at revocation; unset status provider -> skip
5. over-asking rejects at registration_purpose
6. age_over_18/birth_date inconsistency and LoA-below-requirement both
   reject at policy
7. every emitted VerificationResult validates against the frozen schema
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import jsonschema
import pytest

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

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "contracts" / "verification_result.schema.json"
ISSUER_ID = "https://pid-issuer.ie.eidas-lab.example"
VERIFIER_ID = "https://larabank.example/verify"
REQUIRED_CLAIMS = ("age_over_18", "nationality")


@pytest.fixture(scope="module")
def schema():
    return json.loads(SCHEMA_PATH.read_text())


def assert_valid_result(result: dict, schema: dict) -> None:
    jsonschema.validate(result, schema)


@pytest.fixture
def now():
    return int(time.time())


@pytest.fixture
def issuer_kp():
    return KeyPair.from_seed(1)


@pytest.fixture
def claims():
    return build_pid_claims(SAMPLE_SUBJECT, expiry_date_iso="2035-03-11")


@pytest.fixture
def issued_wallet(issuer_kp, claims, now):
    """A wallet that has completed OpenID4VCI-lite issuance and holds a PID."""
    always_visible, disclosable = claims
    wallet = Wallet(unlock_provider=AlwaysYesWalletUnlockProvider())
    offer = CredentialOffer(issuer_id=ISSUER_ID, vct=VCT, offer_nonce="offer-nonce-1")
    proof = wallet.generate_key_proof(offer, issued_at=now)
    valid, holder_jwk = verify_key_proof(proof, expected_issuer_id=ISSUER_ID, expected_nonce=offer.offer_nonce)
    assert valid

    credential = sdjwt.issue(
        issuer_id=ISSUER_ID,
        issuer_private_key=issuer_kp.private_key,
        holder_public_jwk=holder_jwk,
        always_visible_claims=always_visible,
        disclosable_claims=disclosable,
        issued_at=now,
        expires_at=now + 3600 * 24 * 365,
        salt_seed=42,
    )
    wallet.receive_credential(credential, vct=offer.vct)
    return wallet


@pytest.fixture
def auth_request():
    return AuthorizationRequest(
        verifier_id=VERIFIER_ID,
        nonce="verifier-nonce-xyz",
        query=DcqlLiteQuery(vct=VCT, required_claims=REQUIRED_CLAIMS, required_tier="PID", required_loa="high"),
    )


@pytest.fixture
def presentation(issued_wallet, auth_request, now):
    return issued_wallet.handle_presentation_request(auth_request, kb_issued_at=now)


@pytest.fixture
def key_directory(issuer_kp):
    directory = LocalDictIssuerKeyDirectory()
    directory.publish(ISSUER_ID, issuer_kp.public_key)
    return directory


@pytest.fixture
def trust_provider(issuer_kp):
    provider = LocalDictTrustAnchorProvider()
    provider.register(ISSUER_ID, issuer_kp.public_key, tier="PID", loa="high", anchor_id="eu-lab-anchor-1")
    return provider


@pytest.fixture
def registration_provider():
    provider = LocalDictRegistrationProvider()
    provider.register(
        VERIFIER_ID, allowed_claims={"age_over_18", "nationality", "given_name"}, purpose="account-opening"
    )
    return provider


@pytest.fixture
def status_provider():
    return LocalDictStatusListProvider()


@pytest.fixture
def config(trust_provider, key_directory, registration_provider, status_provider):
    return VerifierConfig(
        trust_provider=trust_provider,
        issuer_key_directory=key_directory,
        registration_provider=registration_provider,
        status_provider=status_provider,
    )


@pytest.fixture
def tamper_ctx(issuer_kp, issued_wallet, claims, now, auth_request):
    always_visible, disclosable = claims
    return tamper.TamperContext(
        issuer_id=ISSUER_ID,
        issuer_private_key=issuer_kp.private_key,
        issuer_public_key=issuer_kp.public_key,
        holder_private_key=issued_wallet.holder_keypair.private_key,
        holder_public_jwk=issued_wallet.holder_keypair.public_jwk(),
        always_visible_claims=always_visible,
        disclosable_claims=disclosable,
        salt_seed=42,
        issued_at=now,
        expires_at=now + 3600 * 24 * 365,
        reveal=set(REQUIRED_CLAIMS),
        nonce=auth_request.nonce,
        aud=auth_request.verifier_id,
        kb_issued_at=now,
    )


# --------------------------------------------------------------------------
# Criterion 1 — happy path
# --------------------------------------------------------------------------

class TestHappyPath:
    def test_accepts_with_every_check_passing(self, presentation, auth_request, config, now, schema):
        result = verify(presentation, request=auth_request, config=config, now=now, presentation_id="pres-happy")
        assert result["decision"] == "accept"
        assert all(c["result"] == "pass" for c in result["checks"])
        assert result["trust"] == {"tier": "PID", "anchor_id": "eu-lab-anchor-1", "loa": "high"}
        assert result["qes"] is None
        assert_valid_result(result, schema)


# --------------------------------------------------------------------------
# Criterion 2 — every tamper species rejects at the correct check
# --------------------------------------------------------------------------

class TestTamperSpeciesRejectAtCorrectCheck:
    def _failing_checks(self, result: dict) -> list[str]:
        return [c["name"] for c in result["checks"] if c["result"] == "fail"]

    def test_altered_disclosed_claim_fails_disclosure_integrity(self, presentation, auth_request, config, now, schema):
        variant = tamper.altered_disclosed_claim(presentation, "nationality", "XX")
        result = verify(variant.credential, request=auth_request, config=config, now=now)
        assert result["decision"] == "reject"
        assert self._failing_checks(result) == ["disclosure_integrity"]
        assert_valid_result(result, schema)

    def test_broken_issuer_signature_fails_issuer_signature(self, presentation, auth_request, config, now, schema):
        variant = tamper.broken_issuer_signature(presentation)
        result = verify(variant.credential, request=auth_request, config=config, now=now)
        assert result["decision"] == "reject"
        assert self._failing_checks(result) == ["issuer_signature"]
        assert_valid_result(result, schema)

    def test_stripped_kb_jwt_fails_key_binding(self, presentation, auth_request, config, now, schema):
        variant = tamper.stripped_kb_jwt(presentation)
        result = verify(variant.credential, request=auth_request, config=config, now=now)
        assert result["decision"] == "reject"
        assert self._failing_checks(result) == ["key_binding"]
        assert_valid_result(result, schema)

    def test_wrong_audience_kb_jwt_fails_key_binding(self, tamper_ctx, issued_wallet, auth_request, config, now, schema):
        variant = tamper.wrong_audience_kb_jwt(tamper_ctx, issued_wallet.credential, wrong_aud="https://attacker.example")
        result = verify(variant.credential, request=auth_request, config=config, now=now)
        assert result["decision"] == "reject"
        assert self._failing_checks(result) == ["key_binding"]
        assert_valid_result(result, schema)

    def test_stale_nonce_kb_jwt_fails_key_binding(self, tamper_ctx, issued_wallet, auth_request, config, now, schema):
        variant = tamper.stale_nonce_kb_jwt(tamper_ctx, issued_wallet.credential, stale_nonce="old-nonce")
        result = verify(variant.credential, request=auth_request, config=config, now=now)
        assert result["decision"] == "reject"
        assert self._failing_checks(result) == ["key_binding"]
        assert_valid_result(result, schema)

    def test_expired_credential_fails_policy(self, tamper_ctx, auth_request, config, now, schema):
        variant = tamper.expired_credential(tamper_ctx, expired_at=now - 3600)
        result = verify(variant.credential, request=auth_request, config=config, now=now)
        assert result["decision"] == "reject"
        assert self._failing_checks(result) == ["policy"]
        assert_valid_result(result, schema)


# --------------------------------------------------------------------------
# Criterion 3 — untrusted issuer
# --------------------------------------------------------------------------

class TestTrustPath:
    def test_untrusted_issuer_rejects_at_trust_path_despite_valid_signature(
        self, presentation, auth_request, key_directory, registration_provider, status_provider, now, schema
    ):
        config_no_trust = VerifierConfig(
            trust_provider=LocalDictTrustAnchorProvider(),  # nothing registered
            issuer_key_directory=key_directory,
            registration_provider=registration_provider,
            status_provider=status_provider,
        )
        result = verify(presentation, request=auth_request, config=config_no_trust, now=now)
        checks_by_name = {c["name"]: c for c in result["checks"]}
        assert checks_by_name["issuer_signature"]["result"] == "pass"
        assert checks_by_name["trust_path"]["result"] == "fail"
        assert result["decision"] == "reject"
        assert result["trust"] == {"tier": None, "anchor_id": None, "loa": None}
        assert_valid_result(result, schema)


# --------------------------------------------------------------------------
# Criterion 4 — revocation
# --------------------------------------------------------------------------

class TestRevocation:
    def test_revoked_credential_rejects_at_revocation(
        self, issued_wallet, presentation, auth_request, config, status_provider, now, schema
    ):
        status_provider.revoke(issued_wallet.credential.issuer_jwt)
        result = verify(presentation, request=auth_request, config=config, now=now)
        checks_by_name = {c["name"]: c for c in result["checks"]}
        assert checks_by_name["revocation"]["result"] == "fail"
        assert result["decision"] == "reject"
        assert_valid_result(result, schema)

    def test_no_status_provider_configured_skips_revocation_but_can_still_accept(
        self, presentation, auth_request, trust_provider, key_directory, registration_provider, now, schema
    ):
        config_no_status = VerifierConfig(
            trust_provider=trust_provider,
            issuer_key_directory=key_directory,
            registration_provider=registration_provider,
            status_provider=None,
        )
        result = verify(presentation, request=auth_request, config=config_no_status, now=now)
        checks_by_name = {c["name"]: c for c in result["checks"]}
        assert checks_by_name["revocation"]["result"] == "skip"
        assert result["decision"] == "accept"
        assert_valid_result(result, schema)


# --------------------------------------------------------------------------
# Criterion 5 — over-asking
# --------------------------------------------------------------------------

class TestRegistrationPurpose:
    def test_over_asking_rejects_at_registration_purpose(
        self, presentation, auth_request, trust_provider, key_directory, status_provider, now, schema
    ):
        narrow_registration = LocalDictRegistrationProvider()
        narrow_registration.register(VERIFIER_ID, allowed_claims={"age_over_18"}, purpose="age-check-only")
        config_narrow = VerifierConfig(
            trust_provider=trust_provider,
            issuer_key_directory=key_directory,
            registration_provider=narrow_registration,
            status_provider=status_provider,
        )
        result = verify(presentation, request=auth_request, config=config_narrow, now=now)
        checks_by_name = {c["name"]: c for c in result["checks"]}
        assert checks_by_name["registration_purpose"]["result"] == "fail"
        assert "nationality" in checks_by_name["registration_purpose"]["detail"]
        assert result["decision"] == "reject"
        assert_valid_result(result, schema)

    def test_unregistered_verifier_rejects_at_registration_purpose(
        self, presentation, auth_request, trust_provider, key_directory, status_provider, now, schema
    ):
        config_unregistered = VerifierConfig(
            trust_provider=trust_provider,
            issuer_key_directory=key_directory,
            registration_provider=LocalDictRegistrationProvider(),  # nothing registered
            status_provider=status_provider,
        )
        result = verify(presentation, request=auth_request, config=config_unregistered, now=now)
        checks_by_name = {c["name"]: c for c in result["checks"]}
        assert checks_by_name["registration_purpose"]["result"] == "fail"
        assert result["decision"] == "reject"
        assert_valid_result(result, schema)


# --------------------------------------------------------------------------
# Criterion 6 — policy defects: claim inconsistency and LoA shortfall
# --------------------------------------------------------------------------

class TestPolicy:
    def test_age_over_18_inconsistent_with_birth_date_rejects_at_policy(
        self, issuer_kp, config, now, schema
    ):
        always_visible, disclosable = build_pid_claims(SAMPLE_SUBJECT, expiry_date_iso="2035-03-11")
        disclosable["age_over_18"] = not disclosable["age_over_18"]  # deliberately wrong
        holder_kp = KeyPair.generate()
        bad_credential = sdjwt.issue(
            issuer_id=ISSUER_ID,
            issuer_private_key=issuer_kp.private_key,
            holder_public_jwk=holder_kp.public_jwk(),
            always_visible_claims=always_visible,
            disclosable_claims=disclosable,
            issued_at=now,
            expires_at=now + 3600 * 24 * 365,
            salt_seed=99,
        )
        request = AuthorizationRequest(
            verifier_id=VERIFIER_ID,
            nonce="verifier-nonce-xyz",
            query=DcqlLiteQuery(vct=VCT, required_claims=("age_over_18", "birth_date"), required_tier="PID", required_loa="high"),
        )
        bad_presentation = sdjwt.present(
            bad_credential,
            reveal={"age_over_18", "birth_date"},
            holder_private_key=holder_kp.private_key,
            nonce=request.nonce,
            aud=request.verifier_id,
            kb_issued_at=now,
        )
        result = verify(bad_presentation, request=request, config=config, now=now)
        checks_by_name = {c["name"]: c for c in result["checks"]}
        assert checks_by_name["policy"]["result"] == "fail"
        assert "age_over_18" in checks_by_name["policy"]["detail"]
        assert result["decision"] == "reject"
        assert_valid_result(result, schema)

    def test_loa_below_requirement_rejects_at_policy(
        self, issuer_kp, presentation, auth_request, key_directory, registration_provider, status_provider, now, schema
    ):
        substantial_trust = LocalDictTrustAnchorProvider()
        substantial_trust.register(ISSUER_ID, issuer_kp.public_key, tier="PID", loa="substantial", anchor_id="eu-lab-anchor-1")
        config_low_loa = VerifierConfig(
            trust_provider=substantial_trust,
            issuer_key_directory=key_directory,
            registration_provider=registration_provider,
            status_provider=status_provider,
        )
        result = verify(presentation, request=auth_request, config=config_low_loa, now=now)
        checks_by_name = {c["name"]: c for c in result["checks"]}
        assert checks_by_name["policy"]["result"] == "fail"
        assert "LoA" in checks_by_name["policy"]["detail"]
        assert result["decision"] == "reject"
        assert_valid_result(result, schema)
