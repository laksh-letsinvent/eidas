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
| **1** | Hand-rolled SD-JWT VC issuer in Python, crypto primitives only. Issue a PID, decode, selectively disclose, tamper. See `BUILD_PROMPT_PHASE1.md` | Spec'd, not built |
| **2** | Three-actor loop: issuer + wallet + Lara Bank verifier over simplified OpenID4VCI/VP (nonce, audience, KB-JWT) | Not started |
| **3** | The eval: ~50-presentation defect corpus → verifier harness → per-species confusion matrix + AI red-team run. Then interop-check against EU reference wallet libraries | Not started |
| **3.5 (v2)** | Real PWA wallet: WebCrypto non-extractable keys, WebAuthn unlock, QR cross-device OpenID4VP. Adds the attestation-wall lesson and two defect species the Python actor can't express | Not started |
| **4 (v2)** | QES track: toy QTSP (self-built CA chain), sign a PDF (PAdES), verify, five break-it experiments. AdES→QES ladder in code vs in law | Not started |
| **5** | Trust-anchor swap: same verifier, EU trusted list vs DIATF-style anchor. Demonstrates the UK/EU two-posture argument | Not started |
| **6** | Portal fill-out (In Action / Try It / Results) + long-form write-ups | Portal shell done |

Phases 1–3 are v1. Phases 3.5 and 4 are v2. Each phase is additive over the frozen contracts — same rule that kept bio-authn zero-churn.

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
- **Portal**: Next.js 16 static export (`output: "export"`) in `portal/`, served by nginx on the VM. Built on the exact bio-authn `portal-next` stack — Tailwind v4, shadcn (base-nova), next-themes (dark-first), Space Grotesk / Inter / JetBrains Mono, the `AppShell` sidebar. Brand is `data-brand="eidas"`, violet accent. Type-checks clean against the family modules; production build runs on the VM at deploy.
- Everything seeded and reproducible. The only outbound calls are the VLM (red-team, later phases) and one-time model/library downloads. Any other external call is a bug — flag it.

## Portal architecture

`portal/` is a Next.js app-router static export. Routes: `/` (Experiment — a cleaned public cut of the brief), `/atlas` (verbatim), and three stubs (`/in-action`, `/try-it`, `/results`) that name what each phase will fill. `lib/content.ts` loads the two markdown files and strips the brief's internal tail (open questions, next actions, `[ASSUMED]` tags) for the public Experiment view — single source, public-safe. Deploy via `portal/deploy/` (nginx vhost + `deploy.sh`) to `eidas.letsinvent.co.uk`; see `portal/README_DEPLOY.md`.

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
- Python core (v1); TypeScript with the PWA (Phase 3.5).
- Portal: Next.js 16 static export at eidas.letsinvent.co.uk, on the portal-next stack (Tailwind v4 + shadcn + next-themes); violet brand (`data-brand="eidas"`, #8B5CF6 / #7C3AED), the third sibling accent after Face Value cyan and Hard Copy burgundy.

---

*Created July 2026. Owned by Laksh. Update when scope, phase status, or a frozen contract changes.*
