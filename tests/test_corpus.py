"""
Tests against BUILD_PROMPT_PHASE3.md's acceptance criteria for the corpus:

1. >=~50 labelled items, reproducible under a fixed seed, all scoreable
   species present (thirteen as of Phase 3.5), `genuine` a meaningful share.
4. every species item, run through the real verifier, produces exactly its
   labelled defect (the correct decision, and — for defects — the correct
   check firing).
"""

from __future__ import annotations

from collections import Counter

import pytest

from eval.corpus import DEFAULT_SEED, build_corpus
from eval.species import ALL_SPECIES
from issuer import sdjwt
from verifier.verify import verify


@pytest.fixture(scope="module")
def corpus():
    return build_corpus()


class TestCorpusShape:
    def test_at_least_fifty_items(self, corpus):
        assert len(corpus.items) >= 50

    def test_all_species_present(self, corpus):
        species_seen = {item.species for item in corpus.items}
        assert species_seen == set(ALL_SPECIES)

    def test_genuine_is_a_meaningful_share(self, corpus):
        counts = Counter(item.species for item in corpus.items)
        assert counts["genuine"] >= 5
        assert counts["genuine"] / len(corpus.items) >= 0.10

    def test_item_ids_are_unique(self, corpus):
        ids = [item.item_id for item in corpus.items]
        assert len(ids) == len(set(ids))

    def test_reproducible_under_fixed_seed(self):
        """Reproducible means the same keys, salts, claims, nonces, and
        species structure every run — not byte-identical signatures. ECDSA
        (used throughout, issuer.crypto.es256_sign) randomizes its nonce `k`
        per signature by design, so re-signing identical bytes with an
        identical key legitimately produces different signature bytes each
        time; asserting raw presentation-string equality would be asserting
        away a real security property, not testing reproducibility."""
        corpus_a = build_corpus(seed=DEFAULT_SEED)
        corpus_b = build_corpus(seed=DEFAULT_SEED)
        assert [i.item_id for i in corpus_a.items] == [i.item_id for i in corpus_b.items]
        assert [i.species for i in corpus_a.items] == [i.species for i in corpus_b.items]

        for item_a, item_b in zip(corpus_a.items, corpus_b.items):
            issuer_jwt_a, disclosures_a, _ = sdjwt.split_compact(item_a.presentation)
            issuer_jwt_b, disclosures_b, _ = sdjwt.split_compact(item_b.presentation)
            payload_a = sdjwt.decode_jwt_parts(issuer_jwt_a)[1]
            payload_b = sdjwt.decode_jwt_parts(issuer_jwt_b)[1]
            assert payload_a == payload_b, f"{item_a.item_id}: signed payload differs across runs"
            assert disclosures_a == disclosures_b, f"{item_a.item_id}: disclosures differ across runs"

    def test_different_seeds_produce_different_material(self):
        corpus_a = build_corpus(seed=1)
        corpus_b = build_corpus(seed=2)
        payloads_a = [sdjwt.decode_jwt_parts(sdjwt.split_compact(i.presentation)[0])[1] for i in corpus_a.items]
        payloads_b = [sdjwt.decode_jwt_parts(sdjwt.split_compact(i.presentation)[0])[1] for i in corpus_b.items]
        assert payloads_a != payloads_b


class TestEverySpeciesCarriesItsIntendedDefect:
    """Runs every corpus item through the real Phase 2 verifier and checks
    the outcome matches what the species claims to produce."""

    def test_every_item_matches_its_label(self, corpus):
        mismatches = []
        for item in corpus.items:
            result = verify(item.presentation, request=item.request, config=item.verifier_config, now=corpus.now, presentation_id=item.item_id)
            failing = {c["name"] for c in result["checks"] if c["result"] == "fail"}

            decision_ok = result["decision"] == item.expected_decision
            check_ok = item.expected_check is None or item.expected_check in failing
            if not (decision_ok and check_ok):
                mismatches.append((item.item_id, item.expected_decision, result["decision"], item.expected_check, sorted(failing)))

        assert not mismatches, f"corpus items not matching their label: {mismatches}"

    @pytest.mark.parametrize("species", ALL_SPECIES)
    def test_species_has_at_least_one_item(self, corpus, species):
        assert any(item.species == species for item in corpus.items)
