"""
Tests against BUILD_PROMPT_PHASE3.md's acceptance criteria for the harness:

2. harness produces a schema-valid `eval-1.0` result and a printed matrix.
3. APCER = 0 on all cryptographic/protocol/trust-chain species when run
   over the real corpus; any genuine false reject is investigated.
   (matrix maths itself is tested against a tiny hand-built fixture, not the
   full corpus, so the arithmetic is verified independently of whether the
   verifier happens to behave.)
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from eval.corpus import build_corpus
from eval.harness import ScoredItem, run_harness
from eval.matrix import build_eval_result, build_matrix, per_species_counts, primary_outcome, summary_rates

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "eval_result.schema.json"


def _result(decision: str, failing_checks: tuple[str, ...] = ()) -> dict:
    checks = [{"name": n, "result": "fail", "detail": None} for n in failing_checks]
    return {"decision": decision, "checks": checks, "timing": {"total_ms": 1.0}}


def _scored(species: str, expected_decision: str, expected_check: str | None, actual_decision: str, failing: tuple[str, ...], outcome: str) -> ScoredItem:
    return ScoredItem(
        item_id=f"{species}-fixture",
        species=species,
        expected_decision=expected_decision,
        expected_check=expected_check,
        actual_decision=actual_decision,
        actual_failing_checks=list(failing),
        outcome_category=outcome,
        total_ms=1.0,
        result=_result(actual_decision, failing),
    )


# --------------------------------------------------------------------------
# Matrix maths on a tiny hand-built fixture — independent of the real corpus
# --------------------------------------------------------------------------

class TestMatrixMathsOnFixture:
    @pytest.fixture
    def fixture_items(self):
        return [
            _scored("genuine", "accept", None, "accept", (), "accepted_correctly"),
            _scored("genuine", "accept", None, "accept", (), "accepted_correctly"),
            _scored("genuine", "accept", None, "reject", ("policy",), "false_reject"),
            _scored("broken_issuer_signature", "reject", "issuer_signature", "reject", ("issuer_signature",), "caught"),
            _scored("broken_issuer_signature", "reject", "issuer_signature", "accept", (), "missed"),
        ]

    def test_primary_outcome_picks_canonical_first_failure(self):
        # registration_purpose comes before policy in canonical check order
        result = _result("reject", ("policy", "registration_purpose"))
        assert primary_outcome(result) == "registration_purpose"

    def test_primary_outcome_is_accept_when_nothing_fails(self):
        assert primary_outcome(_result("accept", ())) == "accept"

    def test_build_matrix_counts_by_species_and_outcome(self, fixture_items):
        matrix = build_matrix(fixture_items)
        assert matrix["genuine"]["accept"] == 2
        assert matrix["genuine"]["policy"] == 1
        assert matrix["broken_issuer_signature"]["issuer_signature"] == 1
        assert matrix["broken_issuer_signature"]["accept"] == 1

    def test_per_species_counts(self, fixture_items):
        counts = per_species_counts(fixture_items)
        assert counts["genuine"] == {"n": 3, "caught": 0, "missed": 0, "wrong_check": 0, "accepted_correctly": 2, "false_reject": 1}
        assert counts["broken_issuer_signature"]["n"] == 2
        assert counts["broken_issuer_signature"]["caught"] == 1
        assert counts["broken_issuer_signature"]["missed"] == 1

    def test_summary_rates_apcer_bpcer_on_fixture(self, fixture_items):
        summary = summary_rates(fixture_items)
        # only broken_issuer_signature is in CRYPTO_AND_TRUST_SPECIES within this fixture: 1 missed of 2 -> 0.5
        assert summary["apcer"] == pytest.approx(0.5)
        # genuine: 1 false_reject of 3 -> 1/3
        assert summary["bpcer"] == pytest.approx(1 / 3)
        assert summary["total"] == 5


# --------------------------------------------------------------------------
# Real corpus run: APCER must be exactly 0, schema must validate
# --------------------------------------------------------------------------

class TestHarnessOnRealCorpus:
    @staticmethod
    @pytest.fixture(scope="class")
    def scored():
        corpus = build_corpus()
        return corpus, run_harness(corpus.items, now=corpus.now)

    def test_apcer_is_zero_on_crypto_and_trust_species(self, scored):
        _, scored_items = scored
        summary = summary_rates(scored_items)
        assert summary["apcer"] == 0.0, f"APCER should be 0 on deterministic species; missed items exist: {[i.item_id for i in scored_items if i.outcome_category == 'missed']}"

    def test_no_unexplained_genuine_false_rejects(self, scored):
        _, scored_items = scored
        false_rejects = [i for i in scored_items if i.outcome_category == "false_reject"]
        assert not false_rejects, f"genuine items falsely rejected (investigate): {[(i.item_id, i.actual_failing_checks) for i in false_rejects]}"

    def test_no_wrong_check_outcomes(self, scored):
        _, scored_items = scored
        wrong = [i for i in scored_items if i.outcome_category == "wrong_check"]
        assert not wrong, f"defects caught at the wrong check (correctness bug): {[(i.item_id, i.expected_check, i.actual_failing_checks) for i in wrong]}"

    def test_eval_result_validates_against_schema(self, scored):
        corpus, scored_items = scored
        eval_result = build_eval_result(corpus, scored_items)
        schema = json.loads(SCHEMA_PATH.read_text())
        jsonschema.validate(eval_result, schema)
