# Wallet & QES Lab — Project Brief

## Diagnosis

By December 2027, every EU bank — including Lara Bank's Irish subsidiary — must accept EUDI Wallet credentials wherever it requires strong customer authentication. The UK is building the same capability on a different trust stack: GOV.UK Wallet issuing state credentials, DIATF/DVS-certified private providers verifying them. Both regimes make the bank a *relying party* whose core new component is a **verifier**: software that takes a credential presentation and decides accept/reject against a trust chain.

Almost nobody in a bank product organisation can say what that verifier actually checks, byte by byte. Vendor pitches describe the wallet; regulation describes the obligation; neither describes the thirteen distinct ways a presentation can be defective and what a correct verifier does about each. That gap is the learning target. Laksh's depth is in the biometric/IDV substrate; the credential/trust-chain substrate is currently book-knowledge. This project converts it to built-knowledge, the same way bio-authn did for matching and PAD.

## Why it exists (priority order)

1. **Built understanding of the credential substrate** — SD-JWT VC anatomy, selective disclosure, holder binding, OpenID4VCI/VP, trust lists, wallet attestation, the AdES→QES ladder. The verifier is the vehicle; owning every byte of a verification decision is the destination.
2. **A publicly shareable artefact** — portal in the Face Value / Hard Copy family, plus a defensible non-obvious finding.
3. **Direct feed into the Lara Bank strategy** — the UK/EU two-posture argument, currently asserted in prose, demonstrated in running code by swapping one trust anchor.

Operating principle unchanged: speed of learning beats speed of shipping. A verifier that handles one credential format completely beats one that half-handles three.

## The instrument: what replaces the eval

Bio-authn had a measurable substrate — matcher scores, thresholds, ROC curves. Credentials and signatures are deterministic; there is no accuracy curve. The eval discipline survives anyway, transposed:

**Build a corpus of presentations where the defects are controlled and labelled, point the verifier at it, and score accept/reject per defect species.** "Attack presentation" becomes "tampered credential." The confusion matrix per species is the headline result — the APCER/BPCER analogue. A verifier that has never been run against a hostile corpus is exactly as trustworthy as a liveness check that has never seen a printed photo.

This framing is the publishable insight: relying-party verification logic is an evaluable surface, and by late 2027 it is a regulated gate at every EU bank. Nobody is writing about it that way yet.

### Defect species taxonomy (draft — refine in Phase 3)

| Family | Species |
|---|---|
| Cryptographic | Broken issuer signature · altered disclosure (digest mismatch) · stripped key-binding JWT · algorithm downgrade |
| Trust chain | Issuer absent from trust list · expired issuer certificate · revoked credential (status list) · missing/invalid wallet attestation |
| Protocol | Replayed nonce · wrong audience · expired presentation · origin mismatch (cross-device phishing pattern) |
| Semantic / policy | Expired credential · LoA below journey requirement · claim inconsistency (e.g. age_over_18 vs birthdate) |

QES break-it experiments (Phase 4): document modified after signing · signature from revoked certificate · missing or forged timestamp · chain to untrusted CA · advanced-but-not-qualified certificate presented as QES.

## Phases

| Phase   | Build                                                                                                                                                                                                                                                                                                                                                                  | Learning payoff                                                                                                                                                                                                                     |
| ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **0**   | `ATLAS_WALLET.md` (~100 terms) + `TRUST_MODEL.md` + UK/EU divergence note                                                                                                                                                                                                                                                                                              | Vocabulary: ARF, PID, (Q)EAA, SD-JWT VC, mdoc, OpenID4VCI/VP, DCQL, WSCD/WSCA, trust lists, QTSP, AdES ladder, DIATF/DVS, GOV.UK Wallet                                                                                             |
| **1**   | Hand-rolled SD-JWT VC issuer in Python — crypto primitives only, no SSI libraries. Issue a Lara Bank-relevant PID, decode it, tamper with it, do selective disclosure by hand                                                                                                                                                                                          | Why disclosure digests work; what the wallet actually holds; why the holder can't forge and the verifier can't over-read                                                                                                            |
| **2**   | Three-actor loop: mini issuer + wallet + Lara Bank verifier over simplified OpenID4VCI/VP (nonce, audience, key-binding JWT)                                                                                                                                                                                                                                           | Where replay and phishing defences live in the protocol, not the UI                                                                                                                                                                 |
| **3**   | **The eval.** ~50-presentation corpus across the defect taxonomy → verifier harness → per-species confusion matrix. Then validate the hand-rolled implementation against EU reference wallet libraries for interop                                                                                                                                                     | The instrument. The published finding                                                                                                                                                                                               |
| **3.5** | **The real wallet (v2).** PWA installable from the portal: WebCrypto non-extractable keys for genuine key binding, WebAuthn unlock, QR-scan cross-device OpenID4VP against the same verifier. Reuses the frozen contracts unchanged. Adds two defect species the Python actor can't express: stolen-device presentation (no unlock) and live cross-device origin phish | Where holder keys actually live; and the attestation wall — a browser wallet cannot produce wallet attestation and has no WSCD, which is *why* the ARF demands certified wallet solutions. Hitting that limit in code is the lesson |
| **4**   | QES track: toy QTSP (self-built CA chain), sign a PDF (PAdES), verify, then run the five break-it experiments. Map the AdES→QES ladder to what differs *in code* vs what differs only in legal status                                                                                                                                                                  | The distinction between cryptographic validity and qualified status — the thing everyone conflates                                                                                                                                  |
| **5**   | Swap the trust anchor: same verifier, EU trust list vs DIATF-style certificate. Document exactly what breaks                                                                                                                                                                                                                                                           | The two-posture argument from the IDV strategy, demonstrated                                                                                                                                                                        |
| **6**   | Portal (Next.js, same pattern: Experiment / Atlas / In Action / Try It / Results) + long-form write-up. With Phase 3.5 done, "Try It" is not a widget — the visitor installs the wallet, receives a credential, and presents it to Lara Bank live                                                                                                                      | The career artefact                                                                                                                                                                                                                 |

Phases 1–3 are v1. Phases 3.5 and 4 are v2. Phases 5–6 close it out. Same rule as bio-authn: each phase is additive over frozen contracts.

### The trilogy option (decide at v2)

The three projects compose into one ecosystem: Hard Copy's IDV pipeline is what a PID issuer's evidence check *is* (document authentication + face-on-document match at LoA High); Face Value's matcher is what the ARF's user-binding requirement *is* (biometric release of a device-held key). Wiring them in — Hard Copy playing the issuer's proofing step, Face Value gating high-value presentations from the PWA — makes this the full eIDAS 2.0 loop built solo: proofing → issuance → holding → presentation → verification → hostile eval of the chain. Decision deferred until the Phase 3 eval ships; the unlock interface below keeps both paths open.

## Frozen contracts (define precisely in the build prompt, freeze before Phase 1 code)

1. **`VerificationResult` JSON schema** (`schema_version: "wallet-1.0"`) — per-presentation record: checks run, per-check pass/fail, trust path, policy version, final decision. Reserve null fields for the QES track now (as bio-authn reserved `pad`), so Phase 4 is zero-churn.
2. **`TrustAnchorProvider` interface** — the verifier asks "is this issuer trusted, at what LoA, under which framework?" through one interface. EU trust list and DIATF anchor become swappable implementations. This is Phase 5 designed in from day one, not bolted on.
3. **`WalletUnlockProvider` interface** — the wallet asks "may this credential be released for this presentation?" through one interface. v1 Python actor: always-yes stub. PWA: WebAuthn. Trilogy option: Face Value matcher as step-up. Freezing this now is what keeps the trilogy decision deferrable without churn.

## Regulatory facts anchoring the build (verified July 2026)

- eIDAS 2.0 is Regulation (EU) 2024/1183, in force 20 May 2024. The ARF is at v2.x and translates the regulation plus 30+ Commission Implementing Regulations into technical specs; the ARF itself is informative, the acts are binding.
- Member states must offer wallets to citizens by end of 2026. SCA-obliged relying parties — banks explicitly — must accept them by **December 2027**.
- QES via the wallet is **free of charge for natural persons**. This guts the paid consumer e-signing market and makes QES a wallet feature, not a product.
- Credential formats in scope: mdoc (ISO/IEC 18013-5) and SD-JWT VC. Protocols: OpenID4VCI (issuance), OpenID4VP with DCQL (remote presentation). This build uses SD-JWT VC + OpenID4VP; mdoc/proximity is out of scope.
- UK, as of July 2026: GOV.UK Wallet live with the Veteran Card only (Oct 2025); mDL in private beta with public rollout during 2026; legislation expected late 2026 to make retailers accept digital ID for age-restricted sales. GOV.UK Wallet shares data only with DIATF/DVS-certified providers (50+ certified). Private-sector RP integration is not yet open — so the UK track is trust-model analysis plus the Phase 5 anchor swap, not live integration.

## Out of scope

mdoc / ISO 18013-5 proximity flows. Wallet UI (the "wallet" is a Python actor, not an app). Production key management / HSMs. Zero-knowledge proof schemes beyond a glossary entry. UK live integration (not yet possible). Anything AMLR-specific — that stays in the strategy folder.

**Named trade-off on the AI pillars:** token economy and LLM eval carry almost no weight here — there is no model in the hot path. The payoff is protocol and regulatory authority, which serves the AMLR/eIDAS side of the positioning more than the AI side. A v2 AI layer exists if wanted (an LLM red-team agent generating novel defect presentations against the verifier; LLM-drafted evidence packs per verification decision) — parked, deliberately.

## Open questions

1. Corpus PID realism — invent a Lara Bank-plausible PID schema or copy the ARF PID rulebook attributes verbatim? (Lean: rulebook verbatim; realism is free.)
2. Trilogy fusion (Hard Copy as issuer proofing, Face Value as unlock step-up) — deferred to v2; the `WalletUnlockProvider` contract keeps it open.
3. Publish the defect taxonomy as a standalone reference ("the twelve ways a wallet presentation lies" — fourteen with the PWA species)? Likely yes — it may be the most-shared artefact.
4. Does "Try It" also let visitors tamper with a presentation and watch the verifier's checks fail one by one? Decide at Phase 6.

## Next actions

1. Draft `ATLAS_WALLET.md` (Phase 0) — needs a dedicated research session; regulatory facts above are the seed.
2. Write `BUILD_PROMPT_PHASE1.md` — freeze the two contracts, spec the hand-rolled issuer.
3. Create the sibling repo with this brief as the base of its CLAUDE.md.

---

*Created July 2026. Owned by Laksh. Decisions recorded: wallet before QES; hand-rolled core with library interop check in Phase 3; new sibling repo/portal; portal as primary public artefact; real PWA wallet as v2 track after the eval (Phase 3.5); trilogy fusion deferred to v2 behind the `WalletUnlockProvider` contract.*
