#!/usr/bin/env python3
"""
Phase 5 walkthrough: the same verifier, the same 13-species corpus, run
under two different TrustAnchorProviders — an EU trusted-list-style stub
and a UK DIATF/DVS-style one — then the one deliberately constructed
scenario where the postures actually diverge.

Run: .venv/bin/python examples/anchor_swap_demo.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.anchor_swap import (
    TRUST_PROVIDER_SWAP_EXCLUDED_SPECIES,
    build_eu_only_issuer_scenario,
    diff_outcomes,
    run_both_corpora,
)
from verifier.uk_providers import DiatfAnchorProvider

SEP = "\n" + "=" * 78 + "\n"


def section(title: str) -> None:
    print(SEP + title + SEP)


def main() -> None:
    section("STEP 1 — run the same corpus under two trust anchors")
    eu_scored, uk_scored = run_both_corpora()
    print(f"{len(eu_scored)} items, verified once under each anchor")
    print(f"EU anchor: eu-lab-anchor-1 (local trusted-list stub)")
    print(f"UK anchor: uk-diatf-anchor-1 ({DiatfAnchorProvider.FRAMEWORK})")

    section("STEP 2 — mutual recognition: the honest finding")
    diffs = diff_outcomes(eu_scored, uk_scored)
    mismatches = [d for d in diffs if not d.decisions_match]
    swapped_and_resolved = [
        d for d in diffs if d.species not in TRUST_PROVIDER_SWAP_EXCLUDED_SPECIES and d.eu_anchor_id is not None
    ]
    print(f"decision mismatches across the corpus: {len(mismatches)}")
    print(f"items whose anchor_id differs between runs: {len(swapped_and_resolved)} (label only, decision unchanged)")
    print()
    print("For an issuer both frameworks recognize, the two postures are operationally")
    print("indistinguishable to the verifier — every accept/reject decision is identical.")
    print("The difference is entirely in anchor/framework provenance, not behavior.")

    section("STEP 3 — the constructed divergence: an EU-only issuer")
    scenario = build_eu_only_issuer_scenario()
    print("A second issuer, registered under the EU provider but absent from UK-DIATF")
    print("(modeling a PID provider accredited under eIDAS with no DVS certification).")
    print("The exact same presentation, verified under each posture:")
    print()
    print(f"  EU decision:  {scenario.eu_result['decision'].upper()}")
    print(f"  UK decision:  {scenario.uk_result['decision'].upper()}")
    uk_failing = [c["name"] for c in scenario.uk_result["checks"] if c["result"] == "fail"]
    print(f"  UK failing checks: {uk_failing}")
    print()
    uk_checks = {c["name"]: c for c in scenario.uk_result["checks"]}
    print(f"  UK issuer_signature: {uk_checks['issuer_signature']['result']} (the crypto is fine)")
    print(f"  UK trust_path:       {uk_checks['trust_path']['result']} — {uk_checks['trust_path']['detail']}")

    section("the two-posture argument")
    print(
        "Same verifier code, same corpus, one component swapped. The postures agree\n"
        "until they don't — and where they don't is exactly where accreditation lives,\n"
        "not where cryptography does. A bank running both postures needs two separate\n"
        "registration/trust-resolution processes, not a config flag: an issuer accredited\n"
        "under one framework is not automatically accredited under the other, and the\n"
        "verifier correctly has no opinion about that beyond what each TrustAnchorProvider\n"
        "tells it."
    )

    result = {
        "schema_version": "anchor-swap-1.0",
        "mutual_recognition": {
            "total_items": len(diffs),
            "decision_mismatches": len(mismatches),
            "items_with_differing_anchor_id": len(swapped_and_resolved),
        },
        "eu_only_issuer_scenario": {
            "eu_decision": scenario.eu_result["decision"],
            "uk_decision": scenario.uk_result["decision"],
            "uk_failing_checks": uk_failing,
        },
    }
    output_path = Path(__file__).resolve().parent.parent / "results" / "wallet_anchor_swap.json"
    output_path.write_text(json.dumps(result, indent=2) + "\n")
    print(f"\nsaved to {output_path.relative_to(output_path.parent.parent)}")


if __name__ == "__main__":
    main()
