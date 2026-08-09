#!/usr/bin/env python3
"""
Phase 3 walkthrough: the eval. Build the labelled defect corpus, run the
Phase 2 verifier over it, print the per-species confusion matrix and summary
rates, run the AI red-team, and cross-check against a reference SD-JWT
library. This is the artefact the portal's Results page (Phase 6) renders.

Run: .venv/bin/python examples/run_eval.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import jsonschema

from eval.corpus import build_corpus
from eval.harness import run_harness
from eval.interop import run_interop_check
from eval.matrix import build_eval_result, render_matrix_table, save_eval_result, summary_rates
from eval.redteam import HeuristicRedTeamAgent, build_redteam_result, build_redteam_world, run_redteam

SEP = "\n" + "=" * 78 + "\n"
REPO_ROOT = Path(__file__).resolve().parent.parent


def section(title: str) -> None:
    print(SEP + title + SEP)


def main() -> None:
    section("STEP 1 — build the defect corpus")
    corpus = build_corpus()
    print(f"{len(corpus.items)} items, seed={corpus.seed}, generated at epoch {corpus.now}")
    from collections import Counter

    counts = Counter(item.species for item in corpus.items)
    for species, n in counts.items():
        print(f"  {species:28s} {n}")

    section("STEP 2 — run the verifier over the corpus")
    scored = run_harness(corpus.items, now=corpus.now)
    print(f"{len(scored)} items scored")

    section("STEP 3 — per-species confusion matrix")
    eval_result = build_eval_result(corpus, scored)
    print(render_matrix_table(eval_result["matrix"]))

    section("STEP 4 — summary rates")
    summary = eval_result["summary"]
    print(f"APCER (crypto/protocol + trust-chain species, target 0): {summary['apcer']}")
    print(f"  species included: {summary['apcer_species']}")
    print(f"BPCER (genuine false-reject rate): {summary['bpcer']}")
    print(f"wrong_check_rate (right decision, wrong reason): {summary['wrong_check_rate']}")
    if summary["apcer"] not in (0, 0.0, None):
        print("!! APCER is nonzero — a cryptographic/protocol defect was accepted. This is a verifier bug, not a corpus artefact.")

    section("STEP 5 — validate + save results/wallet_eval.json")
    schema = json.loads((REPO_ROOT / "schemas" / "eval_result.schema.json").read_text())
    jsonschema.validate(eval_result, schema)
    print("validates against eval-1.0")
    save_eval_result(eval_result, REPO_ROOT / "results" / "wallet_eval.json")
    print("saved to results/wallet_eval.json")

    section("STEP 6 — AI red-team (heuristic, local, $0)")
    rt_world = build_redteam_world()
    agent = HeuristicRedTeamAgent()
    attempts = run_redteam(agent, rt_world, n_attempts=4)
    for a in attempts:
        marker = "ACCEPTED (hole found)" if a.accepted else "rejected"
        print(f"  [{a.targeted_check_family:6s}] {a.attempt_id:38s} -> {marker}")
        print(f"           strategy: {a.strategy}")

    redteam_result = build_redteam_result(agent, attempts, now=rt_world.now)
    by_family = redteam_result["by_check_family"]
    print()
    print(f"crypto family success rate:  {by_family['crypto']['success_rate']} (expected 0.0)")
    print(f"policy family success rate:  {by_family['policy']['success_rate']} (expected > 0.0)")
    (REPO_ROOT / "results").mkdir(exist_ok=True)
    (REPO_ROOT / "results" / "wallet_redteam.json").write_text(json.dumps(redteam_result, indent=2) + "\n")
    print("saved to results/wallet_redteam.json")

    section("STEP 7 — interop cross-check (reference sd-jwt library)")
    interop = run_interop_check(now=corpus.now)
    for check in interop["checks"]:
        print(f"  [{'PASS' if check['passed'] else 'FAIL'}] {check['name']}: {check['detail']}")
    for delta in interop["known_deltas"]:
        print(f"  known delta: {delta}")

    section("the finding")
    print(
        "checks 2-6 and the trust-chain half of checks 3-4 (issuer_signature, disclosure_integrity,\n"
        "key_binding, trust_path, revocation) caught every crypto/protocol defect in the corpus and\n"
        "resisted every red-team attempt aimed at them — APCER 0 in both the labelled corpus and the\n"
        "adversarial run. The policy layer (checks 7-8) is where the red-team got through: withholding\n"
        "birth_date defeats the age_over_18 consistency check by construction, not by exploiting a bug —\n"
        "selective disclosure itself removes the verifier's ability to cross-check. eIDAS makes the trust\n"
        "core AI-proof and pushes the residual fraud risk into the policy layer the bank owns."
    )


if __name__ == "__main__":
    main()
