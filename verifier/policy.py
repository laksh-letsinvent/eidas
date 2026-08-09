"""
Policy layer: check 8 of ATLAS_EUDI.md §9 — the soft layer the RP wrote, as
opposed to checks 2-6's deterministic cryptography. Everything here is a
business rule Lara Bank chose (LoA floor, expiry, claim consistency), not a
cryptographic fact — which is exactly why it's the layer Phase 3's AI
red-team targets, not the crypto (CLAUDE.md "flagship experiment").
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from issuer.pid import compute_age_over_18

POLICY_VERSION = "lara-onboarding-v1"

_LOA_RANK = {"low": 0, "substantial": 1, "high": 2}


def loa_meets_requirement(actual_loa: str | None, required_loa: str | None) -> bool:
    """None `required_loa` means the journey doesn't gate on LoA at all."""
    if required_loa is None:
        return True
    if actual_loa is None:
        return False
    return _LOA_RANK.get(actual_loa, -1) >= _LOA_RANK.get(required_loa, 99)


@dataclass(frozen=True)
class PolicyViolation:
    reason: str


def evaluate_policy(
    *,
    revealed_claims: dict[str, Any],
    exp: int,
    now: int,
    actual_loa: str | None,
    required_loa: str | None,
) -> list[PolicyViolation]:
    """Every rule the journey requires, evaluated independently — all
    violations are collected, not just the first, so the `detail` field on a
    failing `policy` check can name every reason at once."""
    violations: list[PolicyViolation] = []

    if exp <= now:
        violations.append(PolicyViolation(f"credential expired at exp={exp} (now={now})"))

    if not loa_meets_requirement(actual_loa, required_loa):
        violations.append(
            PolicyViolation(f"trust LoA {actual_loa!r} does not meet journey requirement {required_loa!r}")
        )

    # Claim consistency: only checkable when the holder disclosed both
    # halves. Disclosing only age_over_18 (the intended selective-disclosure
    # use) leaves this rule with nothing to check against — a known
    # limitation, not a bug (issuer/pid.py's docstring on age_over_18).
    if "age_over_18" in revealed_claims and "birth_date" in revealed_claims:
        claimed = revealed_claims["age_over_18"]
        derived = compute_age_over_18(revealed_claims["birth_date"])
        if claimed != derived:
            violations.append(
                PolicyViolation(
                    f"age_over_18={claimed!r} disagrees with birth_date={revealed_claims['birth_date']!r} "
                    f"(derived {derived!r})"
                )
            )

    return violations
