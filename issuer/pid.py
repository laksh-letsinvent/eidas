"""
PID (Person Identification Data) claim schema and sample subject data.

Attributes are copied verbatim from the ARF PID Rulebook's minimum claim set
(BUILD_PROMPT_PHASE1.md, resolving brief open question 1 as "rulebook
verbatim" rather than inventing a Lara Bank-specific schema — realism is
free). `vct` follows the ARF's PID type identifier convention.

Claims split into two buckets:
  - ALWAYS_VISIBLE: metadata about the credential/issuance itself. These sit
    directly in the signed payload, in the clear, because hiding "who issued
    this and when" would break trust-path and revocation checks, not help
    privacy.
  - DISCLOSABLE: personal attributes. Each becomes a salted disclosure and
    only a digest of it lives in the signed payload (issuer.sdjwt.issue).

`age_over_18` is carried as its own disclosable claim, separate from
`birth_date`, exactly as the ARF wallet does it (the wallet discloses the
boolean without revealing the birth date). It is *derived* from birth_date
here at issuance time — flagged explicitly because a verifier that only
checks the boolean, without ever being able to check it against birth_date
(the discloser controls which of the two is shown), is exactly the
claim-consistency defect the brief's AI red-team experiment targets
(ATLAS_EUDI.md §9 check 8, WALLET-QES-LAB-BRIEF.md line 38).
"""

from __future__ import annotations

from datetime import date, datetime, timezone

VCT = "eu.europa.ec.eudi.pid.1"  # ARF PID type identifier

ALWAYS_VISIBLE_KEYS = ("issuing_country", "issuing_authority")
DISCLOSABLE_KEYS = (
    "family_name",
    "given_name",
    "birth_date",
    "age_over_18",
    "nationality",
)


def compute_age_over_18(birth_date_iso: str, as_of: date | None = None) -> bool:
    as_of = as_of or datetime.now(timezone.utc).date()
    b = date.fromisoformat(birth_date_iso)
    age = as_of.year - b.year - ((as_of.month, as_of.day) < (b.month, b.day))
    return age >= 18


# One fixed, reproducible sample subject — the Lara Bank-relevant PID holder
# for every example/test in this lab. No PII: invented person, invented number.
SAMPLE_SUBJECT = {
    "family_name": "O'Connell",
    "given_name": "Aoife",
    "birth_date": "1994-03-11",
    "nationality": "IE",
    "issuing_country": "IE",
    "issuing_authority": "IE Department of Public Expenditure, NDP Delivery and Reform",
}


def build_pid_claims(subject: dict, expiry_date_iso: str) -> tuple[dict, dict]:
    """Split a subject dict into (always_visible, disclosable) claim dicts.

    `expiry_date_iso` becomes the standard JWT `exp` claim at issuance
    (issuer.sdjwt.issue), not a disclosable claim — expiry is a protocol-level
    fact the verifier's policy check (§9 step 8) always needs to see.
    """
    always_visible = {k: subject[k] for k in ALWAYS_VISIBLE_KEYS}
    disclosable = {k: subject[k] for k in DISCLOSABLE_KEYS if k != "age_over_18"}
    disclosable["age_over_18"] = compute_age_over_18(subject["birth_date"])
    return always_visible, disclosable
