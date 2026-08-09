"""
Conformance harness: run the Phase 2 verifier over the corpus, classify
every item's outcome, and produce a scored record per item.

Classification (BUILD_PROMPT_PHASE3.md "Scoring"):
  - genuine, accepted        -> accepted_correctly
  - genuine, rejected        -> false_reject   (the BPCER analogue)
  - defect, accepted         -> missed         (false accept — the APCER analogue)
  - defect, rejected at the expected check     -> caught
  - defect, rejected at a different check      -> wrong_check (right decision,
    wrong reason — a correctness bug even though nothing got through)
"""

from __future__ import annotations

from dataclasses import dataclass

from eval.species import CorpusItem
from verifier.verify import verify


@dataclass(frozen=True)
class ScoredItem:
    item_id: str
    species: str
    expected_decision: str
    expected_check: str | None
    actual_decision: str
    actual_failing_checks: list[str]
    outcome_category: str
    total_ms: float
    result: dict  # the full VerificationResult, kept for debugging/audit


def _classify(item: CorpusItem, result: dict) -> str:
    actual_decision = result["decision"]
    failing = [c["name"] for c in result["checks"] if c["result"] == "fail"]

    if item.species == "genuine":
        return "accepted_correctly" if actual_decision == "accept" else "false_reject"

    if actual_decision == "accept":
        return "missed"
    if item.expected_check in failing:
        return "caught"
    return "wrong_check"


def run_harness(items: list[CorpusItem], now: int) -> list[ScoredItem]:
    scored: list[ScoredItem] = []
    for item in items:
        result = verify(item.presentation, request=item.request, config=item.verifier_config, now=now, presentation_id=item.item_id)
        failing = [c["name"] for c in result["checks"] if c["result"] == "fail"]
        scored.append(
            ScoredItem(
                item_id=item.item_id,
                species=item.species,
                expected_decision=item.expected_decision,
                expected_check=item.expected_check,
                actual_decision=result["decision"],
                actual_failing_checks=failing,
                outcome_category=_classify(item, result),
                total_ms=result["timing"]["total_ms"],
                result=result,
            )
        )
    return scored
