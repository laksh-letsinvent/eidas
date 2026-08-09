"""
Tests against BUILD_PROMPT_PHASE4-6.md's Phase 5 acceptance criteria:

1. Two TrustAnchorProvider implementations; the verifier runs unchanged
   under both.
2. A documented diff of what changes between anchors (trust fields, which
   credentials pass).
3. The two-posture argument is demonstrated, not asserted.
"""

from __future__ import annotations

import pytest

from contracts.trust_anchor import TrustResolution
from eval.anchor_swap import (
    TRUST_PROVIDER_SWAP_EXCLUDED_SPECIES,
    build_eu_only_issuer_scenario,
    diff_outcomes,
    run_both_corpora,
)
from issuer.crypto import KeyPair
from verifier.uk_providers import DiatfAnchorProvider


class TestDiatfAnchorProviderProtocolConformance:
    def test_resolves_a_registered_issuer(self):
        provider = DiatfAnchorProvider()
        kp = KeyPair.from_seed(1)
        provider.register("https://issuer.example", kp.public_key, tier="PID", loa="high", anchor_id="uk-diatf-anchor-1")
        resolution = provider.resolve("https://issuer.example")
        assert isinstance(resolution, TrustResolution)
        assert resolution.tier == "PID"
        assert resolution.anchor_id == "uk-diatf-anchor-1"

    def test_returns_none_for_unregistered_issuer(self):
        provider = DiatfAnchorProvider()
        assert provider.resolve("https://unknown.example") is None

    def test_default_registration_values(self):
        provider = DiatfAnchorProvider()
        kp = KeyPair.from_seed(2)
        provider.register("https://issuer.example", kp.public_key)
        resolution = provider.resolve("https://issuer.example")
        assert resolution.tier == "PID"
        assert resolution.loa == "high"
        assert resolution.anchor_id == "uk-diatf-anchor-1"


class TestMutualRecognition:
    """The honest finding: for an issuer both frameworks recognize, nothing
    about the corpus's accept/reject outcomes diverges."""

    @staticmethod
    @pytest.fixture(scope="class")
    def scored():
        return run_both_corpora()

    def test_every_mutually_recognized_item_has_identical_decision(self, scored):
        eu_scored, uk_scored = scored
        diffs = diff_outcomes(eu_scored, uk_scored)
        mismatches = [d for d in diffs if not d.decisions_match]
        assert not mismatches, f"decisions diverged for mutually-recognized items: {mismatches}"

    def test_swapped_items_carry_a_different_anchor_id(self, scored):
        """Items where trust_path actually ran and passed should show a
        different anchor_id between the two runs — the label differs even
        though the decision doesn't."""
        eu_scored, uk_scored = scored
        diffs = diff_outcomes(eu_scored, uk_scored)
        swapped_and_resolved = [
            d for d in diffs if d.species not in TRUST_PROVIDER_SWAP_EXCLUDED_SPECIES and d.eu_anchor_id is not None
        ]
        assert swapped_and_resolved, "expected at least some items to have a resolved anchor_id"
        assert all(d.eu_anchor_id != d.uk_anchor_id for d in swapped_and_resolved)

    def test_excluded_species_keep_their_own_anchor_unswapped(self, scored):
        eu_scored, uk_scored = scored
        diffs = diff_outcomes(eu_scored, uk_scored)
        excluded = [d for d in diffs if d.species in TRUST_PROVIDER_SWAP_EXCLUDED_SPECIES]
        assert excluded
        assert all(d.eu_anchor_id == d.uk_anchor_id for d in excluded)


class TestEuOnlyIssuerDivergence:
    """The real, deliberately constructed divergence: an issuer registered
    only under the EU framework."""

    def test_eu_accepts(self):
        scenario = build_eu_only_issuer_scenario()
        assert scenario.eu_result["decision"] == "accept"

    def test_uk_rejects_at_trust_path(self):
        scenario = build_eu_only_issuer_scenario()
        failing = [c["name"] for c in scenario.uk_result["checks"] if c["result"] == "fail"]
        assert failing == ["trust_path"]
        assert scenario.uk_result["decision"] == "reject"

    def test_uk_issuer_signature_still_passes(self):
        """Confirms the divergence is genuinely about trust accreditation,
        not a byte-level defect — the same distinction ATLAS_EUDI.md §11
        draws for the wallet track (valid signature != trusted issuer)."""
        scenario = build_eu_only_issuer_scenario()
        checks_by_name = {c["name"]: c for c in scenario.uk_result["checks"]}
        assert checks_by_name["issuer_signature"]["result"] == "pass"
