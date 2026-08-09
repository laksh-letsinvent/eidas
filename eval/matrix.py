"""
Per-species confusion matrix + summary rates — the headline result
(CLAUDE.md "the instrument that replaces the eval curve").

The matrix's columns are "which check fired first" (canonical §9 order) plus
`accept` for items nothing failed. `primary_outcome` picks the *first*
fatal check in canonical order rather than listing every failing check,
because hard-gate checks already short-circuit to one fatal reason
(verifier/verify.py) — the only case with more than one failing check is
registration_purpose + policy (checks 7-8, which don't short-circuit each
other), and canonical order picks registration_purpose there, consistent
with it being checked first.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path

from eval.corpus import Corpus
from eval.harness import ScoredItem
from eval.species import ALL_SPECIES, CRYPTO_AND_TRUST_SPECIES
from verifier.verify import CHECK_NAMES

OUTCOME_COLUMNS = CHECK_NAMES + ("accept",)


def primary_outcome(result: dict) -> str:
    failing = {c["name"] for c in result["checks"] if c["result"] == "fail"}
    for name in CHECK_NAMES:
        if name in failing:
            return name
    return "accept"


def build_matrix(scored_items: list[ScoredItem]) -> dict[str, dict[str, int]]:
    matrix: dict[str, dict[str, int]] = {species: dict.fromkeys(OUTCOME_COLUMNS, 0) for species in ALL_SPECIES}
    for item in scored_items:
        outcome = primary_outcome(item.result)
        matrix[item.species][outcome] += 1
    return matrix


def render_matrix_table(matrix: dict[str, dict[str, int]]) -> str:
    col_width = 12
    header = "species".ljust(28) + "".join(c[:col_width].rjust(col_width) for c in OUTCOME_COLUMNS)
    lines = [header, "-" * len(header)]
    for species in ALL_SPECIES:
        row = matrix.get(species, {})
        line = species.ljust(28) + "".join(str(row.get(c, 0)).rjust(col_width) for c in OUTCOME_COLUMNS)
        lines.append(line)
    return "\n".join(lines)


def per_species_counts(scored_items: list[ScoredItem]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {
        species: {"n": 0, "caught": 0, "missed": 0, "wrong_check": 0, "accepted_correctly": 0, "false_reject": 0}
        for species in ALL_SPECIES
    }
    for item in scored_items:
        c = counts[item.species]
        c["n"] += 1
        c[item.outcome_category] += 1
    return counts


def summary_rates(scored_items: list[ScoredItem]) -> dict:
    """APCER (false-accept rate) over the crypto/protocol + trust-chain
    species — expected 0 (BUILD_PROMPT_PHASE3.md acceptance criterion 3).
    BPCER (false-reject rate) over `genuine` only. `wrong_check_rate` over
    every item, since a right-decision-wrong-reason bug can happen anywhere."""
    per_species = per_species_counts(scored_items)

    crypto_trust_total = sum(per_species[s]["n"] for s in CRYPTO_AND_TRUST_SPECIES)
    crypto_trust_missed = sum(per_species[s]["missed"] for s in CRYPTO_AND_TRUST_SPECIES)
    apcer = (crypto_trust_missed / crypto_trust_total) if crypto_trust_total else None

    genuine = per_species["genuine"]
    bpcer = (genuine["false_reject"] / genuine["n"]) if genuine["n"] else None

    total = len(scored_items)
    wrong_check_total = sum(s["wrong_check"] for s in per_species.values())
    wrong_check_rate = (wrong_check_total / total) if total else 0.0

    return {
        "total": total,
        "apcer": apcer,
        "apcer_species": list(CRYPTO_AND_TRUST_SPECIES),
        "bpcer": bpcer,
        "wrong_check_rate": wrong_check_rate,
        "per_species": per_species,
    }


def build_eval_result(corpus: Corpus, scored_items: list[ScoredItem]) -> dict:
    """Assemble the `eval-1.0` results artefact (schemas/eval_result.schema.json)."""
    return {
        "schema_version": "eval-1.0",
        "seed": corpus.seed,
        "generated_at": datetime.datetime.fromtimestamp(corpus.now, tz=datetime.timezone.utc).isoformat(),
        "corpus_size": len(corpus.items),
        "items": [
            {
                "item_id": item.item_id,
                "species": item.species,
                "expected_decision": item.expected_decision,
                "expected_check": item.expected_check,
                "actual_decision": item.actual_decision,
                "actual_failing_checks": item.actual_failing_checks,
                "outcome_category": item.outcome_category,
                "total_ms": item.total_ms,
            }
            for item in scored_items
        ],
        "matrix": build_matrix(scored_items),
        "summary": summary_rates(scored_items),
    }


def save_eval_result(eval_result: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(eval_result, indent=2) + "\n")
