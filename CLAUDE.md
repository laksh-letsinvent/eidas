# CLAUDE.md — eIDAS Wallet & QES Lab

Project memory for any agent (Claude Code / Cowork) working in this repo. Read this first, then `WALLET-QES-LAB-BRIEF.md` for the vision and phase plan, `ATLAS_EUDI.md` for domain grounding, and `BUILD_PROMPT_PHASE1.md` for the v1 spec.

---

## What this is

The third build in Laksh's learning series, after Face Value (selfie biometric auth) and Hard Copy (document IDV). This one is the credential and trust-chain substrate: the EUDI Wallet, eIDAS 2.0, and qualified electronic signatures.

The thing built is a **relying-party verifier** and the eval harness around it. The wallet, issuer, and QES pieces are the vehicle; the destination is owning — byte by byte — what a bank's verifier checks when it accepts a wallet presentation, and being able to measure that verifier like any other regulated gate.

Owner: Laksh — Senior PM (Trust & Fraud Platform, consumer banking), 12+ years in identity/auth, moving toward AI-platform / AI-governance roles in regulated financial services.

Sibling to `../LaraBank-IDV-Strategy`. Findings feed that strategy (the UK/EU two-posture argument especially); the strategy's Lara Bank case study is the fictional anchor for this lab's verifier.

## Why it exists (motivation — keep this in view)

Three goals, in priority order:

1. **Built understanding of the credential substrate** — SD-JWT VC anatomy, selective disclosure, holder binding, OpenID4VCI/VP, trust lists, wallet attestation, the AdES→QES ladder. Converting book-knowledge to built-knowledge, the way bio-authn did for matching and PAD.
2. **A publicly shareable artefact** — a portal in the Face Value / Hard Copy family (`eidas.letsinvent.co.uk`) plus long-form write-ups, building domain authority for the AI-PM career pivot.
3. **A direct feed into the Lara Bank IDV strategy** — the two-posture (UK/EU) argument demonstrated in running code by swapping one trust anchor.

Operating principle, unchanged: speed of learning beats speed of shipping. A verifier that handles one credential format completely beats one that half-handles three.

## The diagnosis (why this project, now)

By December 2027 every EU bank — including Lara Bank's Irish subsidiary — must accept EUDI Wallet credentials wherever it requires strong customer authentication. The new component that obligation forces into the bank is a verifier: software that takes a presentation and decides accept/reject against a trust chain. Almost nobody in a bank product org can say what that verifier checks, byte by byte, or how it fails. That gap is the learning target and the publishable angle: **relying-party verification logic is an evaluable surface, and by late 2027 it is a regulated gate at every EU bank.** Nobody is writing about it that way yet.

## The instrument (what replaces the eval curve)

Credentials and signatures are deterministic — there is no accuracy curve like a matcher's ROC. The eval discipline transposes instead: **build a corpus of presentations where the defects are controlled and labelled, point the verifier at them, and score accept/reject per defect species.** The per-species confusion matrix is the headline result — the APCER/BPCER analogue for credential verification.

**Flagship experiment (decided):** an AI red-team agent generates defective presentations against the verifier. The finding is asymmetric and is the thing to publish — the deterministic crypto and trust-chain checks cannot be bluffed past by an LLM, but the policy layer the RP wrote (LoA sufficiency, claim consistency like `age_over_18` vs `birth_date`, over-asking) is where it finds holes. eIDAS makes the trust core AI-proof and pushes residual fraud risk into the policy layer the bank owns. Paired essay: "can an AI agent hold a QES and sign for you?" (the sole-control question).

## Scope by phase

| Phase | Build | Status |
|---|---|---|
| **0** | Atlas + brief + portal (this repo, live at eidas.letsinvent.co.uk) | Atlas, brief, portal done; deploy pending |
| **1** | Hand-rolled SD-JWT VC issuer in Python, crypto primitives only. Issue a PID, decode, selectively disclose, tamper. See `BUILD_PROMPT_PHASE1.md` | Built — `issuer/`, `contracts/`, `examples/issue_and_inspect.py`, `tests/` (21 passing) |
| **2** | Three-actor loop: issuer + wallet + Lara Bank verifier over simplified OpenID4VCI/VP (nonce, audience, KB-JWT) | Built — `wallet/`, `verifier/`, `examples/loop_demo.py`, `tests/test_verifier.py` (35 passing total) |
| **3** | The eval: ~50-presentation defect corpus → verifier harness → per-species confusion matrix + AI red-team run. Then interop-check against EU reference wallet libraries | Built — `eval/`, `schemas/eval_result.schema.json`, `results/`, `examples/run_eval.py`, `tests/test_corpus.py` + `tests/test_harness.py` (63 tests passing total). APCER 0 on all crypto/protocol/trust species; red-team (heuristic, local, $0) found a real policy-layer hole (withholding `birth_date` defeats the `age_over_18` consistency check) and 0% success against the crypto core; interop cross-check against the `sd-jwt` reference library passes both directions. Claude-backed red-team run deferred — see below |
| **3.5 (v2)** | Real PWA wallet: WebCrypto non-extractable keys, WebAuthn unlock, QR cross-device OpenID4VP. Adds the attestation-wall lesson and two defect species the Python actor can't express | Built — `service/` (FastAPI verifier HTTP wrapper, local dev only), `portal/app/wallet/` + `portal/lib/wallet/` (TS PWA: non-extractable P-256 key, WebAuthn gate, TS SD-JWT presentation, two-tab QR cross-device flow, service worker), `eval/species.py`'s 13th species (`cross_device_origin_phish`), `eval/wallet_unlock_species.py` (14th species, `stolen_device_presentation` — deliberately outside the `eval-1.0` matrix), `docs/ATTESTATION_WALL.md`. 79 pytest tests passing; full browser verification done live (key export failure, real issuance/presentation round trip, WebAuthn authorize/cancel, live cross-device accept, live phishing-relay reject at `key_binding`) — WebAuthn gesture steps required the user's manual pass, everything else Chrome-automation-verified. Not deployed to the live VM this pass |
| **4 (v2)** | QES track: toy QTSP (self-built CA chain), sign a PDF (PAdES), verify, five break-it experiments. AdES→QES ladder in code vs in law | Built — `qes/` (ca.py, pades.py, tamper.py, verify_pades.py), `examples/qes_demo.py`, `docs/AES_VS_QES.md`, `tests/test_qes.py` (16 tests). `qes` field filled in `contracts/verification_result.schema.json` — the one sanctioned schema evolution, diff-checked byte-identical elsewhere. PAdES via pyHanko (offline `DummyTimeStamper`, no network); CA chain hand-rolled via `cryptography.x509`. All five experiments detected at the correct field; the AES-vs-QES experiment is the one non-rejection — everything cryptographic passes, only `is_qualified` flips (real ETSI qcStatements OID, not a house convention) |
| **5** | Trust-anchor swap: same verifier, EU trusted list vs DIATF-style anchor. Demonstrates the UK/EU two-posture argument | Built — `verifier/uk_providers.py` (`DiatfAnchorProvider`), `eval/anchor_swap.py`, `examples/anchor_swap_demo.py`, `docs/TWO_POSTURE.md`, `tests/test_anchor_swap.py` (9 tests). `verifier/verify.py` genuinely unchanged — swap is a `dataclasses.replace()` on frozen `CorpusItem`/`VerifierConfig`, no touch to `eval/species.py`/`eval/corpus.py`. Honest finding: mutual-recognition corpus shows 0 decision mismatches (only `anchor_id` labels differ); the real divergence is a deliberately constructed EU-only-issuer scenario (EU accept, UK reject at `trust_path`) |
| **6** | Portal fill-out (In Action / Try It / Results) + long-form write-ups | Built — `/in-action` (precomputed Phase 2 walkthrough, `examples/generate_in_action_content.py`), `/try-it` (live `POST /tamper-demo` + `/verify` round trip over 6 curated species — `issuer_not_on_trusted_list`/`revoked_credential`/`loa_below_requirement`/`over_asking`/`claim_inconsistency` excluded, each needs a swapped `VerifierConfig` this endpoint's single fixed `CONFIG` can't reproduce), `/results` (confusion matrix + `recharts` rate charts + anchor-swap section, reading `results/*.json` copied into `portal/content/results/`), `/essays` (`lib/essays.ts` registry, three essays, `/essays/[slug]` — first dynamic static-export route in this portal, `generateStaticParams()`). All "soon" nav badges removed. `npm run build` clean (15 routes incl. 3 essay slugs); full Chrome-automation sweep console-error-free. Not deployed to the live VM this pass — `./deploy/deploy.sh user@vm-host` ready, run only on a fresh explicit go-ahead |
| **7** | Portal restructure around the nine-story prototype (`BUILD_PROMPT_PHASE7-9.md`) — the prototype becomes the spine, five-item nav | Built — nav collapsed to 5 items (How this works / Atlas / The Experiment / Try It / Takeaway) in `components/AppShell.tsx`. `/` now renders the nine-story walkthrough ported from the standalone prototype (`portal/content/walkthrough/source.html`, kept verbatim as provenance) into `portal/lib/walkthrough/stories.ts` (typed data + pure HTML-string helpers, ported as-is per the build prompt's "take the shortcut") and a small React shell (`components/walkthrough/`: `Walkthrough`, `StoryPicker`, `PhoneFrame`, `ActorBand`, `ExplainRail`). The selective-disclosure story is the one step rebuilt as real React (`SelectiveDisclosureLab.tsx`, `useState` over the claim set) rather than ported as a string. Styles lifted into `portal/app/walkthrough.css`, scoped under `.wt`, with `--bg`/`--txt`/`--panel`/`--line`/`--ok`/`--bad` remapped onto the portal's own dark tokens and `--eu`/`--eu2`/`--gold` kept literal (content, not brand). The brief moved to `/experiment` (`lib/experiment.ts` unchanged). `/in-action` page shell deleted (JSON kept as future fallback data, not yet wired). `/results` content moved to `/takeaway` verbatim (`lib/results.ts`, `RatesChart.tsx` untouched); Phase 9 still owes it the anchor-swap-as-learnings prose and essay links. `/essays` and `/wallet` keep their routes, dropped from nav. `npm run build` clean (14 routes); Chrome-automation-verified live: story stepping, the three explanation panes, and the SD claim picker/meter (preset switch confirmed live, "Buying wine" → 1 of 10) |

| **8** | Real data in the portal: rich result view, four live Try It stories, six live species inside the story frame, a QES recorded run, `/experiment`'s attestation wall + species catalogue | Built — `components/wallet/VerificationResultView.tsx` now takes an optional `presentation` prop (raw compact SD-JWT) alongside the frozen `VerificationResult`; parsed client-side by new `lib/wallet/presentation.ts` (reuses `lib/wallet/sdjwt.ts`'s `splitCompact`/`parseDisclosure`) to show disclosed claims, withheld claims (against the fixed PID claim universe `issuer/pid.py`'s `DISCLOSABLE_KEYS` defines — the only claims `service/main.py`'s `WORLD` fixture can ever disclose), the KB-JWT's `sd_hash` digest, audience and nonce — then the eight-check ladder underneath. Same component, wired into `/try-it`, `/wallet`, `/verify-demo`, `/verify-demo/phish` alike. Try It rebuilt around `components/tryit/`: `useLocalWallet()` (shared IndexedDB-backed wallet state, same primitives `WalletCard.tsx` already used) powers four live story cards — get a wallet, open a bank account (2 registered claims: `age_over_18`, `nationality` — **not five**, see decision below), prove you're over 18 (1 claim, client-constructed request, the highest-value screen), a same-tab phishing relay (wrong `verifier_id` on the KB-JWT, real one on `/verify` — reproduces `cross_device_origin_phish` without a second tab) — followed by the six wire-level defect species (`SpeciesStory.tsx`, same `/tamper-demo` + `/verify` round trip as before, restyled as "the bank story going wrong") and a QES recorded run (`QesRecordedStory.tsx`, reading `content/qes_walkthrough.json`, generated by new `examples/generate_qes_content.py` — real CA chain, real PAdES signature, the `advanced_not_qualified_cert_as_qes` flip included, honestly labelled "Recorded run"). `/experiment` gained the attestation wall (`docs/ATTESTATION_WALL.md`, copied to `portal/content/`) and a 13-species catalogue (`lib/speciesCatalogue.ts`, hand-written against `eval/species.py`'s own generator docstrings, not invented) linking the six live ones to Try It. No new endpoints; no changes to `verifier/`, `eval/species.py`, or any frozen contract. `npm run build` clean (14 routes). Chrome-automation-verified live: both species results (accept and reject, disclosed/withheld/digest/audience/nonce all correct) and the QES recorded run render correctly. **Deferred to Laksh**: the three WebAuthn-gated stories (get your wallet, bank account, over-18, phishing) — confirmed they reach the real `navigator.credentials.get()`/`.create()` gate (a pending gesture visibly blocks the tab, exactly the documented Phase 3.5 limitation) but the gesture itself can't be driven by browser automation |

| **9** | Takeaway page, precomputed fallbacks for every Try It live surface, build green | Built — `/takeaway` (renamed from `/results`, same file) gained a "Key learnings" section (five paragraphs, hand-written synthesis, not generated) and an "Essays" section linking all three via `lib/essays.ts`'s existing registry; confusion matrix, rate charts and the anchor-swap section carried over untouched. Every live Try It surface now degrades quietly: new `examples/generate_tryit_fallback.py` (built from the identical `eval.species.build_world`/`good_config` fixture `service/main.py` itself uses, so fallback numbers match what the live service would produce) emits `content/tryit_fallback.json` — recorded `{presentation, result}` pairs for the wallet summary, bank, over-18 and phishing stories, plus all six live species. New `lib/wallet/useServiceHealth.ts` (`checkServiceHealth()` in `lib/wallet/api.ts`, 1.5s-timeout `GET /health`) probes once per page load; `GetWalletStory`/`PresentStory`/`SpeciesStory` switch on its result — a visitor without the service sees "Recorded run — local verifier service not detected" and the precomputed result, never a fetch error. A visitor's own IndexedDB-held credential (if any) still takes priority over the fallback for the wallet story specifically, since that read needs no network. Verified live: stopped the local `uvicorn` service, confirmed all four story cards and the species picker fell back quietly with correct disclosed/withheld/digest data and no console errors, then restarted it and confirmed the live path still works unchanged. Full Chrome-automation sweep (`/`, `/atlas`, `/experiment`, `/try-it` both live and fallback, `/takeaway`, `/essays` + one slug, `/wallet`, `/verify-demo`, `/verify-demo/phish`) console-error-free. `npm run build` clean — **14 routes** (`/`, `/atlas`, `/essays`, `/essays/[slug]` ×3, `/experiment`, `/takeaway`, `/try-it`, `/verify-demo`, `/verify-demo/phish`, `/wallet`, `/wallet/present`, plus `/_not-found`). Not deployed — `./deploy/deploy.sh` untouched, per the standing rule |

**Decision — bank story claim count.** The build prompt's IA table says "five claims travel" for Open a bank account; the fixed `CONFIG` in `service/main.py` only registers Lara Bank for `{age_over_18, nationality, given_name}` (`eval/species.py`'s `DEFAULT_REGISTRATION_CLAIMS`), and `/authorization-request` only ever asks for 2 of those 3. Requesting 5 would trip `registration_purpose` (correctly) — the same "known risk" class the build prompt flags for the over-18 story, just in the asking-too-much direction instead of asking-too-little. Rather than widen the verifier's registration (out of scope: "no new verifier logic"), Open a bank account uses the real 2-claim default and Prove you're over 18 asks for 1 of those same 3 — both genuinely live, neither trips the check. Noted here rather than silently shipped as "five."

Phases 1–3 are v1. Phases 3.5 and 4 are v2. Phases 7–9 restructure the portal without touching Python or any frozen contract. Each phase is additive over the frozen contracts — same rule that kept bio-authn zero-churn.

## The frozen contracts (do not break)

Defined precisely in `BUILD_PROMPT_PHASE1.md` §"three frozen contracts". Freeze before Phase 1 code.

1. **`VerificationResult` schema** (`schema_version: "wallet-1.0"`) — the per-presentation record the verifier emits. Deliberately carries null fields for checks not yet run (QES fills them in Phase 4), the way the bio-authn schema reserved `pad`. Validate every emitted file against it.
2. **`TrustAnchorProvider` interface** — the single "is this issuer trusted, at what tier, under which framework, what's its anchor" question. EU trusted list and DIATF anchor are swappable implementations. This is Phase 5 designed in from day one.
3. **`WalletUnlockProvider` interface** — "may this credential be released for this presentation?" v1 stub is always-yes; PWA uses WebAuthn; the trilogy option uses the Face Value matcher. Freezing it now keeps the trilogy decision deferrable without churn.

If a change would alter any contract, stop and raise it — that's a scope decision, not an implementation detail.

## The verification decision (the spec spine)

The verifier runs an ordered set of checks; each maps to a defect species and a column in the results matrix. From `ATLAS_EUDI.md` §9:

1. format/parse · 2. issuer signature · 3. trust path · 4. revocation/status · 5. disclosure integrity · 6. key binding · 7. registration/purpose · 8. policy.

Checks 2–6 are deterministic cryptography (AI-unbluffable). Checks 7–8 are the policy layer (where the red-team finds holes). This split is the flagship finding — keep it central.

## Stack

- **Python core** for issuer / verifier / eval (v1). Crypto via `cryptography`; no SSI or JWT libraries in Phase 1 — assemble and sign by hand. That is the point.
- **TypeScript** arrives only with the PWA wallet (Phase 3.5) and is already the portal's language.
- **Portal**: Next.js 16 static export (`output: "export"`) in `portal/`, served by Caddy on the VM. Built on the exact bio-authn `portal-next` stack — Tailwind v4, shadcn (base-nova), next-themes (dark-first), Space Grotesk / Inter / JetBrains Mono, the `AppShell` sidebar. Brand is `data-brand="eidas"`, violet accent. Type-checks clean against the family modules; production build runs on the VM at deploy.
- Everything seeded and reproducible. The only outbound calls are the VLM (red-team, later phases) and one-time model/library downloads. Any other external call is a bug — flag it.

## Portal architecture

`portal/` is a Next.js app-router static export. Routes: `/` (Experiment — a cleaned public cut of the brief), `/atlas` (verbatim), and three stubs (`/in-action`, `/try-it`, `/results`) that name what each phase will fill. `lib/content.ts` loads the two markdown files and strips the brief's internal tail (open questions, next actions, `[ASSUMED]` tags) for the public Experiment view — single source, public-safe. Deploy via `portal/deploy/` (Caddy vhost + `deploy.sh`) to `eidas.letsinvent.co.uk`; see `portal/README_DEPLOY.md`.

Content files in `portal/content/` are copies of the lab-root `ATLAS_EUDI.md` and `WALLET-QES-LAB-BRIEF.md`. Re-copy and rebuild when the originals change.

## How to show up (voice)

Peer-level, direct, intellectually engaged. Take positions and defend them; name what would change your mind. Name trade-offs explicitly — never hide them. Prose over bullet-point soup. Outcome-first: open with why it matters. When uncertain, say "I think X, but worth validating because Y" rather than hedging softly. Outputs should be usable immediately.

Avoid this vocabulary: delve, crucial, pivotal, landscape (figurative), foster, cultivate, underscore, highlight (verb), robust, seamless, holistic, leverage (verb), tapestry, garner, interplay, "Moreover/Furthermore/Additionally" as openers, "It's important to note," "In conclusion," synergy, alignment (as a vague noun), best practice, move the needle, end-to-end. No significance inflation — replace "this is pivotal" with a specific number or consequence.

## Domain guardrails (precision matters — see ATLAS_EUDI.md §11)

- **Valid signature ≠ trusted issuer.** Cryptographic verification says the signature is intact; the trusted-list path says the issuer is accredited.
- **Signature valid ≠ credential live.** Revocation is a separate check.
- **Trust tier ≠ data format.** QEAA and plain EAA can share SD-JWT VC and sit at different legal levels.
- **AES ≠ QES.** In code they look near-identical; the qualified status is the QSCD plus the qualified certificate, much of it legal not cryptographic.
- **Holder ≠ bearer.** Key binding (KB-JWT) is what stops a leaked credential being a bearer token.
- **PWA wallet ≠ Wallet Unit.** No WSCD, no WUA, no certification — a browser wallet teaches the protocol but cannot be eIDAS-compliant. That wall is the lesson.
- **Selective disclosure ≠ unlinkability.** Hiding claims doesn't prevent correlating presentations; batch/one-time credentials are the mitigation and they cost something.

## Regulatory anchors (verified July 2026 — keep accurate, flag if unsure)

- eIDAS 2.0 = Regulation (EU) 2024/1183, in force 20 May 2024. ARF at v2.x, informative not binding; the regulation and 30+ CIRs bind.
- Wallets offered to citizens by end 2026; SCA-obliged relying parties (banks) must accept by **December 2027**.
- QES via the wallet is **free for natural persons** — reframes QES from paid product to wallet feature.
- Formats: SD-JWT VC (this lab) and mdoc/ISO 18013-5 (out of scope). Protocols: OpenID4VCI, OpenID4VP with DCQL.
- UK (July 2026): GOV.UK Wallet live with the Veteran Card only; mDL in private beta; no open private-sector RP integration yet. UK is Phase 5's anchor swap, not a live integration.

## Out of scope

mdoc / ISO 18013-5 proximity flows. Production key management / HSMs. Real wallet UI beyond the PWA. Zero-knowledge schemes beyond a glossary entry. UK live RP integration (not yet possible). AMLR-specific work — that stays in `../LaraBank-IDV-Strategy`.

## Document map

- `WALLET-QES-LAB-BRIEF.md` — vision, phases, defect taxonomy, experiments, open questions. The charter.
- `ATLAS_EUDI.md` — EUDI / eIDAS / QES domain glossary (~100 terms), organised around the verification decision (§9).
- `BUILD_PROMPT_PHASE1.md` — the buildable v1 spec: three frozen contracts + hand-rolled issuer. Hand this to Claude Code to start Phase 1.
- `portal/` — the Next.js portal + deploy config. See `portal/README_DEPLOY.md`.

## Decisions recorded (read before re-opening)

- Wallet before QES.
- Hand-rolled core; library interop-check only at Phase 3.
- New sibling repo/portal (this folder), kept under `IDV-Workspace/` parallel to LaraBank-IDV-Strategy.
- Real PWA wallet as a v2 track after the eval (Phase 3.5), not a replacement for the Python wallet actor.
- Trilogy fusion (Hard Copy as issuer proofing, Face Value as unlock step-up) deferred to v2 behind the `WalletUnlockProvider` contract.
- Flagship experiment: AI red-team vs the verifier; paired essay on agentic QES.
- Red-team transport (Phase 3): built `eval/redteam.py` with a pluggable `RedTeamAgent` Protocol. Development and the numbers currently in `results/wallet_redteam.json` use `HeuristicRedTeamAgent` — a zero-cost, zero-network, hand-authored set of attack strategies, no LLM in the loop. A Claude-backed agent for the eventual publishable run is deferred, pending a decision on transport (API key vs. other) — raise before Phase 6 needs final numbers.
- Python core (v1); TypeScript with the PWA (Phase 3.5).
- Portal: Next.js 16 static export at eidas.letsinvent.co.uk, on the portal-next stack (Tailwind v4 + shadcn + next-themes); violet brand (`data-brand="eidas"`, #8B5CF6 / #7C3AED), the third sibling accent after Face Value cyan and Hard Copy burgundy.
- Portal deploy is Caddy, not nginx (corrects this file's earlier Stack section — verify against `portal/README_DEPLOY.md` if it drifts again). Static export means no Next.js API routes are possible from within `portal/`.
- Phase 3.5's "thin verifier HTTP endpoint" is a new standalone `service/` (FastAPI + uvicorn), wrapping `verifier.verify()` unchanged, reusing `eval.species.build_world()`/`good_config()` as its fixture. Local dev tool only — narrow CORS allow-list, never deployed. Run: `uvicorn service.main:app --port 8420 --reload`.
- `cross_device_origin_phish` (Phase 3.5) is a full citizen of the Phase 3 eval pipeline — 13th species in `eval/species.py`, same mechanism as `wrong_audience_kb_jwt`, no schema changes needed.
- `stolen_device_presentation` (Phase 3.5's 14th species) is deliberately **outside** the `eval-1.0` confusion matrix — confirmed with the user rather than decided unilaterally. It's inherently unscoreable by the 8-check verifier (WebAuthn denial blocks release before any presentation exists, so `verifier.verify()` is never called). Lives in its own module (`eval/wallet_unlock_species.py`) with its own tiny artefact (`results/wallet_unlock_gate.json`), not folded into either JSON Schema. If this needs revisiting, the alternative (widening `eval_result.schema.json`'s enums) is a real but more invasive option — see that module's docstring.
- WebAuthn's actual hardware gesture (Touch ID / cancel) cannot be driven by browser automation in this environment (`navigator.credentials.*` needs real OS window focus) — verified live by the user manually at three points during the Phase 3.5 build (registration, authorized presentation, cancel). Everything else (key generation/export, IndexedDB, issuance, same-device and cross-device presentation, the phishing-relay reject) was Chrome-automation-verified.
- Service workers must not run under `next dev` — Turbopack's content-hashed dev chunks recompile per request, and a cache-first SW fighting that causes a reload loop (hit and fixed during Phase 3.5; `RegisterServiceWorker.tsx` now gates registration behind `NODE_ENV === "production"`).

---

*Created July 2026. Owned by Laksh. Update when scope, phase status, or a frozen contract changes.*
