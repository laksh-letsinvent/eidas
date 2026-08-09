# The Two-Posture Argument, Demonstrated

Phase 5 deliverable. The UK/EU two-posture argument, proved in running code rather than asserted — feeds directly into `../LaraBank-IDV-Strategy`'s UK/EU case study.

## The claim

A bank operating across the UK and the EU needs two trust postures, not one. `verifier/verify.py` doesn't need to know or care which — it's the same code either way. `eval/anchor_swap.py` runs the exact same Phase 3 corpus through the exact same verifier twice, swapping only the `TrustAnchorProvider` implementation (frozen contract #2), and shows precisely what changes and what doesn't.

## What's identical

Everything except one component:

- `verifier/verify.py` — genuinely zero changes. Check 3 (`trust_path`) only ever calls `config.trust_provider.resolve(issuer_id)` through the frozen Protocol; it has no idea whether that resolves against an EU trusted list or a UK DVS certificate.
- The corpus — `eval/corpus.py`/`eval/species.py` are untouched. `eval/anchor_swap.py` builds the corpus once, then produces two trust-provider-swapped *views* of it via `dataclasses.replace()` (both `CorpusItem` and `VerifierConfig` are frozen dataclasses), rather than rebuilding anything.
- Every check that isn't `trust_path` — format, issuer_signature, revocation, disclosure_integrity, key_binding, registration_purpose, policy all behave identically regardless of which anchor is in play.

## What's different

One thing: `verifier/uk_providers.py`'s `DiatfAnchorProvider`, a second implementation of `TrustAnchorProvider` alongside `LocalDictTrustAnchorProvider`. Same `resolve()` shape, different real-world framework behind it — a DVS-certified verification provider, not an eIDAS Article 22 trusted list. In the corpus, this shows up as a different `trust.anchor_id` on every item whose trust resolution actually runs (`eu-lab-anchor-1` vs `uk-diatf-anchor-1`).

## The honest finding: mutual recognition changes nothing observable

Run `examples/anchor_swap_demo.py` and the first result is a non-event, stated plainly rather than buried: **zero decision mismatches** across the 56-item corpus. Every `accept`/`reject` outcome is identical whether the issuer resolves against the EU provider or the UK one — both providers were asked to register the *same* issuer at the *same* functional tier and LoA, so of course they agree. The only visible difference is the `anchor_id` label on 44 of the 56 items (the ones where `trust_path` actually runs and passes; the rest either short-circuit before reaching it, or deliberately construct their own trust provider to express a different defect and are excluded from the swap — see `eval/anchor_swap.py`'s `TRUST_PROVIDER_SWAP_EXCLUDED_SPECIES`).

That's not a disappointing result. It's the accurate one: **for an issuer both frameworks agree to recognize, the two postures are operationally indistinguishable.** A verifier that only ever sees mutually-recognized issuers would never notice it was running under a different trust posture at all.

## The real divergence: an issuer registered under only one framework

`build_eu_only_issuer_scenario()` constructs the case that actually demonstrates something: a second issuer, registered in the EU provider, deliberately *not* registered in the UK-DIATF one — modeling a PID provider accredited under eIDAS with no DVS certification. The identical presentation, verified under each posture:

- **EU**: `accept` — `trust_path` passes.
- **UK-DIATF**: `reject` at `trust_path` — "issuer not on any trusted list." `issuer_signature` still passes (the cryptography is fine; this is `ATLAS_EUDI.md` §11's "valid signature ≠ trusted issuer" disambiguation, now demonstrated across a framework boundary rather than within one).

**What this means operationally**: a bank running both postures needs two separate registration/trust-resolution processes, not a config flag. An issuer accredited under eIDAS is not automatically accredited under DIATF, and vice versa — the verifier has correctly no opinion on that beyond what each `TrustAnchorProvider` tells it. Onboarding a new EU PID provider doesn't extend UK coverage; the two accreditation regimes are genuinely separate operational commitments, not two views of one list.

## The tier-mapping compromise, stated explicitly

`contracts/verification_result.schema.json`'s `trust.tier` is a closed enum (`"PID"|"QEAA"|"PuB-EAA"|"EAA"|null`) shaped around eIDAS's own vocabulary — that schema is frozen, and this phase's one sanctioned schema change was Phase 4's `qes` field, not this one. DIATF has no equivalent categories. `DiatfAnchorProvider` maps a GOV.UK-style state credential onto `tier="PID"` **functionally** — it plays the same foundational-identity role a PID plays under eIDAS — not because DIATF actually organizes credentials into PID/QEAA/EAA tiers. The real distinction lives in `anchor_id` and the provider's own `FRAMEWORK` constant (`"UK DIATF/DVS"`), both read directly by this document and the demo script, neither part of the schema. Read `tier` as "what role does this credential play," and `anchor_id`/framework as "under what regime was it accredited" — conflating the two would be the actual modeling error here, not this compromise.

## Feed line

This is the running-code version of the UK/EU two-posture argument already made in `../LaraBank-IDV-Strategy`: not a claim that the two regimes are interchangeable, but a demonstration of exactly where they agree (issuer trusted by both — behavior identical) and exactly where they don't (issuer trusted by one — a real, single-check divergence, `trust_path`, not a cascade of differences). For Lara Bank's Irish subsidiary running both a UK and an EU book of business, that's the actual shape of the integration cost: one verifier, two trust-resolution processes to maintain, and a clean, single-point failure mode when they disagree.
