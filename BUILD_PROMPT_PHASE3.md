# Build Prompt — Phase 3: The Eval (Defect Corpus · Conformance Matrix · AI Red-Team)

Handoff spec for Claude Code. Read `CLAUDE.md`, `ATLAS_EUDI.md` §9, `WALLET-QES-LAB-BRIEF.md` (defect taxonomy + flagship experiment), and the Phase 1–2 code first. This is the phase the whole project exists for: it turns the verifier from "seems to work" into a measured instrument. Additive over the frozen contracts.

---

## What this phase is

Credentials are deterministic — there is no ROC curve. The eval discipline transposes: build a corpus of presentations where every defect is controlled and labelled, run the Phase 2 verifier over it, and score accept/reject per defect species. The **per-species confusion matrix is the headline result** — the APCER/BPCER analogue for credential verification. Then run the flagship experiment: an AI red-team agent that tries to get invalid presentations accepted, producing the asymmetric finding this project publishes.

**Learning objective:** learn to measure a regulated gate you built. A verifier never run against a hostile, labelled corpus is exactly as trustworthy as a liveness check that has never seen a printed photo. The instrument, not the verifier, is the deliverable.

**The finding to prove (or falsify), stated up front:** checks 2–6 (cryptography and trust chain) cannot be bluffed past by an LLM; checks 7–8 (the policy layer the RP wrote) are where it finds holes. eIDAS makes the trust core AI-proof and pushes residual fraud risk into the policy layer the bank owns. Phase 3 either shows this in numbers or shows it is wrong.

## Scope

**IN:**
- A **defect corpus builder** (`eval/corpus.py`) that emits ~50 labelled presentations across the taxonomy, seeded and reproducible.
- A **conformance harness** (`eval/harness.py`) that runs the Phase 2 verifier over the corpus and scores per species.
- A **results artefact** (`results/wallet_eval.json`, schema `eval-1.0` — new, defined here, not a frozen contract) plus a rendered **per-species confusion matrix**.
- The **AI red-team run** (`eval/redteam.py`): an LLM agent generates candidate defective presentations against the verifier; log every attempt, classify which check it attacked, score success by check family.
- An **interop cross-check** (`eval/interop.py`): validate the hand-rolled issuance/presentation against one EU/community SD-JWT reference library — parse our output with theirs and/or verify their output with ours. A correctness check, not a runtime dependency.

**OUT (do not build in Phase 3):**
- The PWA wallet and its two extra defect species (stolen-device, live cross-device phish) — Phase 3.5.
- QES break-it experiments — Phase 4. The UK anchor swap — Phase 5. Portal Results-page fill — Phase 6 (this phase produces the JSON it will render).
- Any change to the verifier's logic beyond bug fixes the corpus reveals. If the corpus exposes a real verifier gap, fix it in `verifier/` and note it — that is a valid finding, not scope creep.

## The defect taxonomy (label set)

Twelve species for the Python actor (the PWA adds two more in 3.5). Each corpus item carries exactly one label; `genuine` is the negative class.

Cryptographic / protocol (checks 2–6, deterministic — expect APCER 0):
- `genuine` (negative class), `broken_issuer_signature`, `altered_disclosed_claim`, `stripped_kb_jwt`, `wrong_audience_kb_jwt`, `stale_nonce_kb_jwt`.

Trust chain (checks 3–4):
- `issuer_not_on_trusted_list`, `revoked_credential`.

Semantic / policy (checks 7–8 — where the interesting misses live):
- `expired_credential`, `loa_below_requirement`, `claim_inconsistency` (`age_over_18` vs `birth_date`), `over_asking` (request/disclose beyond the registration certificate).

Reuse `issuer.tamper.generate_all_variants` for the six it already produces. Build the rest from the Phase 2 providers (trust, status list, registration, policy).

## Scoring (the instrument)

For each corpus item: expected decision (genuine -> accept; any defect -> reject) vs the verifier's actual decision, plus **which check fired**. Compute per species:
- **caught** — defect correctly rejected.
- **missed (false accept)** — defect wrongly accepted. This is the security number, the APCER analogue. Target 0 on cryptographic species.
- **wrong check** — rejected, but at the wrong check (a correctness bug even when the decision is right).
- For `genuine`: **false reject** — wrongly rejected, the BPCER analogue.

Headline output: a confusion matrix with species as rows and the fired-check as columns, plus the three summary rates. Save to `results/wallet_eval.json` (`schema_version: "eval-1.0"`) and print a readable table.

## The AI red-team (flagship experiment)

Give an LLM agent the verifier's stated goal and public behaviour (not its source as an oracle — it must probe), a valid credential + holder key, and the task: produce a presentation the verifier **accepts** that it should reject. Run N attempts. For each: record the crafted presentation, the verifier's `VerificationResult`, whether it was accepted, and which check it targeted.

- Transport for the model follows the family convention (`vlm_mode`-style): develop on a local/cheap model, produce publishable numbers on the Claude CLI/API. Instrument tokens/cost per attempt — the token-economy discipline from bio-authn applies.
- Expected result: **0 successful accepts against checks 2–6**, nonzero probing success against checks 7–8 (e.g. a `claim_inconsistency` or `over_asking` the policy layer failed to encode). Report success rate by check family. If the agent breaches the crypto core, that is a real bug in the hand-rolled verifier — find and document it; that is a strong result either way.
- Paired write-up seed (not built here): "can an AI agent hold a QES and sign for you?" — the agentic-QES essay lives in Phase 4/6.

## Interop cross-check

Correctness sanity, not a dependency: take one community SD-JWT / SD-JWT VC library, and either (a) have it parse and validate a credential our issuer produced, or (b) have our `decode`/verifier accept a credential it produced. Document any delta from the drafts. Keep it a single, clearly-marked check — the hand-rolled core stays the point.

## Suggested file layout

```
eval/
  corpus.py         # build ~50 labelled presentations, seeded
  species.py        # the twelve defect-species generators
  harness.py        # run verifier over corpus -> scored records
  matrix.py         # per-species confusion matrix + summary rates
  redteam.py        # AI agent attack loop + token accounting
  interop.py        # cross-check against a reference library
results/
  wallet_eval.json      # schema eval-1.0 (corpus scoring)
  wallet_redteam.json   # red-team attempts + outcomes
schemas/
  eval_result.schema.json   # eval-1.0, defined this phase
examples/
  run_eval.py       # corpus -> matrix, printed
tests/
  test_corpus.py    # every species item carries its intended defect
  test_harness.py   # matrix maths on a tiny fixture
```

## Acceptance criteria

1. Corpus of >=~50 labelled presentations, reproducible under a fixed seed, covering all twelve species with `genuine` as a meaningful share.
2. Harness produces `results/wallet_eval.json` (validates against `eval-1.0`) and a printed per-species confusion matrix.
3. **APCER = 0 on all cryptographic/protocol species** — every deterministic defect caught, at the correct check. Any `genuine` false reject is investigated and explained.
4. If the corpus exposes a verifier bug, it is fixed in `verifier/` and the fix noted as a finding.
5. Red-team run completes N attempts, logs each with its `VerificationResult`, token cost, and targeted check; reports success rate by check family; and states the asymmetric finding backed by the numbers (or documents a crypto-core breach if found).
6. Interop cross-check runs and either passes or documents the exact delta from the reference library.
7. `examples/run_eval.py` runs clean end to end and reads as the artefact the Results page (Phase 6) will render.

## What this phase deliberately leaves unresolved

Two defect species that need real holder keys and a live channel (stolen-device presentation, cross-device origin phish) wait for the PWA in Phase 3.5. QES defects wait for Phase 4. The UK-anchor variant of the trust_path species waits for Phase 5. This phase measures the EU wallet verifier as it stands — completely — and publishes that.

---

*Owned by Laksh. Phase 3 of the Wallet & QES lab. The eval is the deliverable; the verifier is the vehicle. `eval-1.0` is a new results schema, separate from the frozen `wallet-1.0` — do not conflate them.*
