# Build Prompt — Phases 4, 5, 6 (clipped): QES · Anchor Swap · Portal

Handoff spec for Claude Code — three phases in one file because they are medium/small and finish the project. Build them in order; each is additive over the frozen contracts and over the Phase 1–3 code. Read `CLAUDE.md`, `ATLAS_EUDI.md` (§7 trust infrastructure, §8 QES, §9 verification decision), and `WALLET-QES-LAB-BRIEF.md` first. Phase 6 is the visible finale — the browser payoff.

Recommended order: **4 -> 5 -> 6**. Phase 6 renders the outputs of 2, 3, (3.5), 4, and 5, so it comes last.

---

## Phase 4 (v2) — QES track

### What this phase is

Build the qualified-signature side of the title. A toy QTSP with a self-built CA chain issues a qualified certificate; a signer signs a PDF (PAdES); a verifier checks it; then five break-it experiments show what a correct QES verifier catches. The recurring lesson: **cryptographic validity and qualified legal status are different axes** — in code, AES and QES look near-identical; the difference is the QSCD and the qualified certificate, much of it legal not cryptographic.

### Scope

**IN:**
- A toy **QTSP / CA chain** (root -> intermediate QTSP) using `cryptography` x509, reusing `issuer.crypto` primitives where sensible.
- Issue a **qualified certificate** to a signer; **sign a PDF with PAdES** (baseline B-level); verify integrity + chain-to-trust-anchor + timestamp.
- The **five break-it experiments** (defect species): `document_modified_after_signing`, `signature_from_revoked_cert`, `missing_or_forged_timestamp`, `chain_to_untrusted_ca`, `advanced_not_qualified_cert_as_qes`.
- Fill the reserved **`qes` field** in the result. This is the pre-declared slot in `verification_result.schema.json` (it was set to `null` in Phase 1 precisely for this). Evolve the schema additively so `qes` is either `null` (wallet track) or a QES-result object (signature track); document it as the sanctioned reserved-slot fill, and version it (e.g. note in the schema `description`). This is the one anticipated schema evolution — treat it as a deliberate decision, not a silent change.
- An **AdES-vs-QES diff note** (`docs/AES_VS_QES.md`): what differs in code vs what differs only in law.

**OUT:** real QSCD/HSM, real QTSP accreditation, XAdES/CAdES/JAdES (PAdES only), long-term archival beyond a basic timestamp, the agentic-QES essay (that is Phase 6 prose).

### Acceptance

1. CA chain builds; a PDF signed with PAdES verifies (integrity + chain + timestamp).
2. Each of the five break-it experiments is detected with the correct failure reason.
3. `qes` result object is populated and schema-validates; the schema evolution is documented as the reserved-slot fill.
4. `docs/AES_VS_QES.md` names precisely which parts of "qualified" are cryptographic and which are legal.

---

## Phase 5 — Trust-anchor swap (the two-posture argument)

### What this phase is

Prove the UK/EU two-posture argument in running code by swapping one component. The verifier does not change; only the `TrustAnchorProvider` implementation does. Show exactly what differs when the anchor is an EU trusted list versus a UK DIATF-style certificate.

### Scope

**IN:**
- Two implementations of the frozen `TrustAnchorProvider` (contract #2): an `EUTrustedListProvider` (formalising the Phase 2 stub as an EU Article 22 trusted-list model) and a `DiatfAnchorProvider` (UK: DVS-certified provider model, no eIDAS trusted list, different trust semantics and LoA mapping).
- Run the **same verifier and the same Phase 3 corpus** under each provider; capture the diff in `trust.tier` / `trust.loa` / framework and in which credentials pass the trust_path check.
- A **divergence note** (`docs/TWO_POSTURE.md`): what a bank must run differently for UK vs EU, demonstrated — feeds the LaraBank strategy directly.

**OUT:** live UK integration (not yet possible), real DIATF certificates, GOV.UK Wallet integration. This is the anchor swap, not a UK build.

### Acceptance

1. Two `TrustAnchorProvider` implementations; the verifier runs **unchanged** under both.
2. A documented diff of what changes between anchors (trust fields, which credentials pass).
3. `docs/TWO_POSTURE.md` states the two-posture argument as demonstrated, not asserted.

---

## Phase 6 — Portal fill-out + write-ups (the visible finale)

### What this phase is

Turn everything built into the thing a person opens in a browser. Fill the three stub pages with real content from Phases 2/3/(3.5)/4/5, and publish the long-form write-ups. This is where the project becomes the public artefact.

### Scope

**IN:**
- **In Action** (`/in-action`): a precomputed walkthrough of the three-actor loop from Phase 2's `examples/loop_demo.py` output — the eight checks firing, an accept and a reject.
- **Try It** (`/try-it`): interactive. If Phase 3.5 is built, this surfaces the PWA wallet — install, receive a PID, present to the verifier live, tamper and watch a check fail. If 3.5 is not built, fall back to an in-page simulated tamper demo over precomputed presentations.
- **Results** (`/results`): render `results/wallet_eval.json` (the per-species confusion matrix) and `results/wallet_redteam.json` (the crypto-vs-policy asymmetry) using recharts (already in the portal deps), plus the Phase 5 anchor-swap diff.
- **Write-ups** (rendered as markdown in the portal): at minimum two essays — the defect taxonomy ("the fourteen ways a wallet presentation lies") and the flagship red-team finding ("eIDAS makes the trust core AI-proof — here is where the fraud risk actually moves"). Add the agentic-QES essay ("can an AI agent hold a QES and sign for you?") if Phase 4 is done.
- Rebuild and deploy via the existing `portal/deploy/deploy.sh` to eidas.letsinvent.co.uk.

**OUT:** new backend work — Phase 6 renders what earlier phases produced. No new verifier logic, no new corpus.

### Acceptance

1. All three stub pages replaced with real content driven by the actual Phase 2/3/(3.5)/4/5 outputs.
2. Results renders the real JSON (not hardcoded numbers); charts match the files.
3. Try It is interactive (PWA path) or a documented simulated fallback.
4. The two (or three) essays are published and readable, in the violet brand.
5. The portal still type-checks and builds; the site is rebuilt and deployed.

---

## After Phase 6

The build is complete: the full eIDAS loop — issue, hold, present, verify, attack, measure — plus the QES track and the UK/EU two-posture, all visible in a browser. Remaining open items from the brief (trilogy fusion via the Face Value matcher; a Claude-backed red-team run for publishable numbers) stay parked behind their contracts and decisions, to pick up only if wanted.

---

*Owned by Laksh. Phases 4–6 of the Wallet & QES lab. Build 4 -> 5 -> 6. Additive over the frozen contracts; the one sanctioned schema evolution is the `qes` reserved-slot fill in Phase 4.*
