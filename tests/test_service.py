"""
Tests against BUILD_PROMPT_PHASE3_5.md's service acceptance bar: the FastAPI
service is a faithful, thin wrapper around the unchanged Phase 2/3 verifier
core. Uses FastAPI's TestClient (starlette, in-process, no real socket) —
this proves the HTTP plumbing is correct before any TypeScript exists.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import jsonschema
import pytest
from fastapi.testclient import TestClient

from contracts.wallet_unlock import AlwaysYesWalletUnlockProvider
from issuer.sdjwt import Credential, Disclosure, split_compact
from service.main import app
from wallet.request import AuthorizationRequest, DcqlLiteQuery
from wallet.wallet import CredentialOffer, Wallet

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "contracts" / "verification_result.schema.json"


@pytest.fixture
def client():
    return TestClient(app)


def _credential_from_compact(compact: str) -> Credential:
    issuer_jwt, disclosure_b64s, _ = split_compact(compact)
    return Credential(issuer_jwt=issuer_jwt, disclosures=[Disclosure.parse(b) for b in disclosure_b64s])


class TestHealth:
    def test_health_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestFullRoundTrip:
    def test_offer_issue_present_verify_accepts(self, client):
        now = int(time.time())

        offer_response = client.post("/credential-offer")
        assert offer_response.status_code == 200
        offer_body = offer_response.json()

        wallet = Wallet(unlock_provider=AlwaysYesWalletUnlockProvider())
        offer = CredentialOffer(issuer_id=offer_body["issuer_id"], vct=offer_body["vct"], offer_nonce=offer_body["offer_nonce"])
        proof_jwt = wallet.generate_key_proof(offer, issued_at=now)

        issue_response = client.post("/issue", json={"offer_id": offer_body["offer_id"], "proof_jwt": proof_jwt})
        assert issue_response.status_code == 200
        credential_compact = issue_response.json()["credential"]

        credential = _credential_from_compact(credential_compact)
        wallet.receive_credential(credential, vct=offer.vct)

        auth_request_response = client.post("/authorization-request")
        assert auth_request_response.status_code == 200
        auth_body = auth_request_response.json()

        request = AuthorizationRequest(
            verifier_id=auth_body["verifier_id"],
            nonce=auth_body["nonce"],
            query=DcqlLiteQuery(
                vct=auth_body["query"]["vct"],
                required_claims=tuple(auth_body["query"]["required_claims"]),
                required_tier=auth_body["query"]["required_tier"],
                required_loa=auth_body["query"]["required_loa"],
            ),
        )
        presentation = wallet.handle_presentation_request(request, kb_issued_at=now)

        verify_response = client.post("/verify", json={"presentation": presentation, "request": auth_body})
        assert verify_response.status_code == 200
        result = verify_response.json()

        assert result["decision"] == "accept"
        assert all(c["result"] == "pass" for c in result["checks"])

        schema = json.loads(SCHEMA_PATH.read_text())
        jsonschema.validate(result, schema)

    def test_issue_rejects_unknown_offer_id(self, client):
        response = client.post("/issue", json={"offer_id": "does-not-exist", "proof_jwt": "irrelevant"})
        assert response.status_code == 400

    def test_offer_is_single_use(self, client):
        now = int(time.time())
        offer_body = client.post("/credential-offer").json()
        wallet = Wallet(unlock_provider=AlwaysYesWalletUnlockProvider())
        offer = CredentialOffer(issuer_id=offer_body["issuer_id"], vct=offer_body["vct"], offer_nonce=offer_body["offer_nonce"])
        proof_jwt = wallet.generate_key_proof(offer, issued_at=now)

        first = client.post("/issue", json={"offer_id": offer_body["offer_id"], "proof_jwt": proof_jwt})
        assert first.status_code == 200

        second = client.post("/issue", json={"offer_id": offer_body["offer_id"], "proof_jwt": proof_jwt})
        assert second.status_code == 400


class TestVerifyTolerance:
    def test_malformed_presentation_rejects_cleanly_not_500(self, client):
        auth_body = client.post("/authorization-request").json()
        response = client.post("/verify", json={"presentation": "not-a-real-presentation", "request": auth_body})
        assert response.status_code == 200
        result = response.json()
        assert result["decision"] == "reject"
        assert any(c["name"] == "format" and c["result"] == "fail" for c in result["checks"])


class TestCrossDeviceRelay:
    def test_present_then_poll_returns_it(self, client):
        submit = client.post("/present", json={"nonce": "relay-nonce-1", "presentation": "abc~def~"})
        assert submit.status_code == 200

        poll = client.get("/present/relay-nonce-1")
        assert poll.status_code == 200
        assert poll.json()["presentation"] == "abc~def~"

    def test_poll_unknown_nonce_is_404(self, client):
        response = client.get("/present/never-submitted-nonce")
        assert response.status_code == 404


class TestTamperDemo:
    """/tamper-demo (Phase 6's /try-it endpoint): every curated species must
    round-trip through /verify with the *exact* expected check firing, not
    just the expected decision — this caught two species (over_asking,
    claim_inconsistency) that looked config-independent but weren't, and
    both were removed from TAMPER_DEMO_SPECIES rather than papered over."""

    @pytest.mark.parametrize("species", [
        "genuine", "broken_issuer_signature", "altered_disclosed_claim",
        "stripped_kb_jwt", "expired_credential", "cross_device_origin_phish",
    ])
    def test_curated_species_verify_with_exact_expected_check(self, client, species):
        demo_response = client.post("/tamper-demo", json={"species": species})
        assert demo_response.status_code == 200
        body = demo_response.json()
        assert body["species"] == species

        verify_response = client.post("/verify", json={"presentation": body["presentation"], "request": body["request"]})
        result = verify_response.json()
        failing = [c["name"] for c in result["checks"] if c["result"] == "fail"]
        expected_failing = [body["expected_check"]] if body["expected_check"] else []

        assert result["decision"] == body["expected_decision"]
        assert failing == expected_failing, f"{species}: expected only {expected_failing} to fail, got {failing}"

    def test_unsupported_species_is_rejected(self, client):
        response = client.post("/tamper-demo", json={"species": "issuer_not_on_trusted_list"})
        assert response.status_code == 400

    def test_unknown_species_is_rejected(self, client):
        response = client.post("/tamper-demo", json={"species": "not-a-real-species"})
        assert response.status_code == 400
