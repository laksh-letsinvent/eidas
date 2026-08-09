"""
Tests for `stolen_device_presentation` (eval/wallet_unlock_species.py) —
Phase 3.5's fourteenth species, deliberately kept out of the eval-1.0
confusion matrix. See that module's docstring for why.
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from eval.species import build_world
from eval.wallet_unlock_species import (
    AlwaysNoWalletUnlockProvider,
    build_unlock_gate_result,
    stolen_device_presentation_attempt,
)
from wallet.wallet import Wallet


@pytest.fixture(scope="module")
def world():
    return build_world()


@pytest.fixture
def now():
    return int(time.time())


class TestStolenDevicePresentation:
    def test_unlock_is_denied(self, world, now):
        record = stolen_device_presentation_attempt(world, index=0, now=now)
        assert record.unlock_result.authorized is False

    def test_release_is_blocked(self, world, now):
        record = stolen_device_presentation_attempt(world, index=1, now=now)
        assert record.blocked is True

    def test_present_is_never_called(self, world, now):
        """The real assertion: not just that the presentation is withheld,
        but that issuer.sdjwt.present is never invoked at all — the defence
        is pre-presentation, not merely a client that declines to send."""
        with patch("wallet.wallet.sdjwt.present") as mock_present:
            record = stolen_device_presentation_attempt(world, index=2, now=now)
        mock_present.assert_not_called()
        assert record.blocked is True

    def test_species_label(self, world, now):
        record = stolen_device_presentation_attempt(world, index=3, now=now)
        assert record.species == "stolen_device_presentation"

    def test_multiple_attempts_all_blocked(self, world, now):
        records = [stolen_device_presentation_attempt(world, index=i, now=now) for i in range(4)]
        assert all(r.blocked for r in records)

    def test_build_unlock_gate_result_shape(self, world, now):
        records = [stolen_device_presentation_attempt(world, index=i, now=now) for i in range(3)]
        result = build_unlock_gate_result(records)
        assert result["species"] == "stolen_device_presentation"
        assert result["n"] == 3
        assert result["all_blocked"] is True
        assert len(result["attempts"]) == 3


class TestAlwaysNoWalletUnlockProvider:
    def test_always_denies(self):
        from contracts.wallet_unlock import PresentationContext

        provider = AlwaysNoWalletUnlockProvider()
        result = provider.authorize(
            PresentationContext(credential_id="x", audience="y", nonce="z", requested_claims=("age_over_18",))
        )
        assert result.authorized is False

    def test_wallet_with_denying_provider_raises_on_present_request(self, world, now):
        from wallet.request import AuthorizationRequest, DcqlLiteQuery
        from wallet.wallet import CredentialOffer, WalletCannotSatisfyRequest, verify_key_proof
        from issuer import sdjwt
        from issuer.crypto import KeyPair
        from issuer.pid import VCT

        holder_kp = KeyPair.from_seed(9999)
        wallet = Wallet(unlock_provider=AlwaysNoWalletUnlockProvider(), holder_keypair=holder_kp)
        offer = CredentialOffer(issuer_id=world.issuer_id, vct=VCT, offer_nonce="test-nonce")
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
            salt_seed=42424242,
        )
        wallet.receive_credential(credential, vct=offer.vct)
        request = AuthorizationRequest(
            verifier_id=world.verifier_id,
            nonce="test-verifier-nonce",
            query=DcqlLiteQuery(vct=VCT, required_claims=("age_over_18",), required_tier="PID", required_loa="high"),
        )
        with pytest.raises(WalletCannotSatisfyRequest):
            wallet.handle_presentation_request(request, kb_issued_at=now)
