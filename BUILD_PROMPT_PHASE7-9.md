# Build Prompt — Phases 7, 8, 9: Restructure the Portal Around the Experience

Handoff spec for Claude Code. Three phases in one file because together they are roughly one day of work and they only make sense as one restructure. Build them in order. Read `CLAUDE.md` first, then this file. `ATLAS_EUDI.md` §9 (the verification decision) and `docs/ATTESTATION_WALL.md` are the domain references you will need.

Recommended order: **7 -> 8 -> 9**. Phase 7 moves the furniture, Phase 8 fills it with real data, Phase 9 closes it out and makes it deployable.

---

## Why this exists (read before scoping anything)

Phase 6 shipped a portal where every interactive surface resolves to the same artefact: a pass/fail ladder over eight checks. `/in-action` narrates one, `/try-it` generates one, `/wallet` produces one, `/results` counts them, `/essays` argues about them. It reads as a backend test harness because that is structurally what it is.

Two consequences, both confirmed by Laksh running the portal locally at `localhost:3001`:

1. **`/in-action` and `/try-it` are near-duplicates.** Both end in a `VerificationResult` card. Neither tells a visitor what eIDAS *is*.
2. **"accept" is not information.** `/wallet` presents a credential to Lara Bank and reports a decision. It never shows the thing that would make a domain reader lean forward — *which claims travelled, which did not, and what the verifier actually bound them to*.

Meanwhile a separate prototype already solves the explanation problem completely: nine narrative stories in a phone frame, covering issuance, presentation, selective disclosure, phishing, QES and cross-border. It is the best asset this project has for its stated goal — a learning module for a London identity practitioner — and it is not in the portal.

**The guiding decision: the prototype becomes the spine of the portal, and the verifier checks live inside it rather than beside it.** eIDAS is unfamiliar enough that concept explanation is not a distraction from the eval; it is the on-ramp that makes the eval legible.

Budget: **one day.** Scope has been cut to fit. Do not expand it.

---

## Target information architecture

Five nav items. Everything else is reachable but unlisted.

| # | Nav item | Route | Contents |
|---|---|---|---|
| 1 | How this works | `/` | The nine prototype stories. The hero. |
| 2 | Atlas | `/atlas` | Unchanged |
| 3 | The Experiment | `/experiment` | What was built: the local PWA and the attestation wall; the 13 defect species as a catalogue |
| 4 | Try It | `/try-it` | Four stories run live, six species broken live, QES as a recorded run |
| 5 | Takeaway | `/takeaway` | Results, key learnings, links to the three essays |

Route changes:

- `/` stops rendering `WALLET-QES-LAB-BRIEF.md` and becomes the walkthrough. The brief moves to `/experiment` (reuse `lib/experiment.ts` unchanged — it already strips the internal tail and `[ASSUMED]` tags).
- `/in-action` — **delete the page shell.** Its precomputed steps in `content/in_action.json` are kept and re-parented as Try It's offline fallback data. Do not regenerate them.
- `/results` — content moves into `/takeaway`. `lib/results.ts` and `components/results/RatesChart.tsx` carry over untouched.
- `/essays` and `/essays/[slug]` — keep the routes, drop them from nav, link them from `/takeaway`.
- `/wallet`, `/wallet/present`, `/verify-demo`, `/verify-demo/phish` — keep the routes, drop them from nav, reach them from the Try It stories.

Nothing is deleted except the `/in-action` and `/results` page shells. Everything else is re-parented.

---

## Phase 7 — Restructure and the hero

### What this phase is

Move the nav to five items and get the nine-story prototype rendering inside the AppShell. No new data, no backend changes. This phase alone fixes the complaint that opened this work.

### The source

`/Users/lsinghal/Downloads/SPKJ-workbench/IDV-Workspace/LaraBank-IDV-Strategy/eudi-wallet-qes-demo-v3-pid-issuance-disclosure.html`

Note this is **not** a sibling directory of this repo despite what `CLAUDE.md` implies — use the absolute path. Copy it to `portal/content/walkthrough/source.html` first, unmodified, as provenance. Extract from the copy.

File anatomy: `<style>` at lines 7–322, `<body>` from 324, `<script>` at 451–1452. The `STORIES` array begins at line 590 and holds nine objects, each with `id`, `icon`, `title`, `tag`, `blurb` and a `steps` array. Each step has `app`, `icon`, `right`, a `body` HTML string built from helper functions, and an `expl` block (`{t, b}`). Helpers to be aware of: `heroBlock`, `okBlock`, `credCard`, `verifier`, `fields`, `withheld`, `compare`, `scanScreen`. The selective-disclosure story is interactive via `PID_CLAIMS`, `SD_PRESETS`, `sdRows()`, `sdOut()`, `mountSd()`.

### Take the shortcut — this is deliberate

**Do not rewrite the story bodies as React components.** They are HTML strings produced by pure functions. Port them as follows:

- Extract `STORIES`, `PID_CLAIMS`, `SD_PRESETS` and the helper functions into `portal/lib/walkthrough/stories.ts` with types. The helpers stay as functions returning strings.
- Render step bodies with `dangerouslySetInnerHTML` inside a wrapper element carrying a single scoping class.
- Rebuild only the outer chrome in React: story picker, step navigation, the three explanation panes ("What just happened", "Under the hood", "Worth knowing"), restart and back controls.
- Port the selective-disclosure interaction as a small React component using `useState` over the claim set. It is the one piece of real interactivity and it is worth doing properly.

A component-by-component rewrite does not fit the budget and buys nothing.

### Styling — do not restyle the interior

The prototype's palette and the portal's dark tokens are already nearly the same file. `--bg #0a0d14` is byte-identical to the portal's `--background #0A0D14`; `--txt #e8edf7` against `--foreground #E7ECF3`; `--panel`, `--line`, `--ok`, `--bad` all sit within a few points of `--surface-2`, `--border-c`, `--accept`, `--reject`.

So:

- Lift the `<style>` block into `portal/app/walkthrough.css`, wrap every selector under one scoping class (`.wt`) so nothing leaks either direction. Verify no portal styles bleed in and no walkthrough styles escape.
- Remap the eight variables above onto portal tokens.
- **Keep `--eu` (#3b6fe0 / #5b8cff) as it is.** That blue is content, not styling — it is the EU identity on a wallet screen. Do not make it violet.
- The phone frame interior stays dark regardless of theme. The prototype is dark-only and a phone UI that follows a documentation site's light mode looks wrong. Outer chrome follows the portal theme normally.

### Scope

**IN:** nav array edit in `components/AppShell.tsx`; new `/` walkthrough; brief moved to `/experiment`; `/in-action` and `/results` shells removed and their content re-parented per the table above; scoped stylesheet; story data extraction.

**OUT:** live data of any kind, deep links per story, light mode inside the phone frames, touching any Python.

### Acceptance

1. Nav shows exactly five items in the specified order.
2. `/` renders all nine stories, each steppable start to finish, with the three explanation panes intact.
3. The selective-disclosure story's claim picker works, and its meter updates.
4. No style leakage in either direction — check a portal page and a story side by side.
5. `/experiment` renders the brief. No route 404s; no orphaned links anywhere in the portal.
6. `npm run build` clean.

---

## Phase 8 — Real data

### What this phase is

Answer the "it just says accept" complaint. Build one result view that shows what moved, then use it everywhere. Fill Try It with four live stories and the species catalogue with all thirteen.

### 8a — The result view

Replace `components/wallet/VerificationResultView.tsx`'s presentation (not its input contract — the `VerificationResult` schema is frozen and must not change) so it leads with data and follows with the ladder:

- Claims disclosed, with values.
- Claims withheld — as important as what was sent, and currently invisible.
- The disclosure digest that matched.
- The audience and nonce the presentation was bound to.
- Then the eight-check ladder underneath.

The prototype's `fields()`, `withheld()` and `compare()` helpers are the reference for what this should look like. Build it once. It appears in Try It's live stories, in the species demos, and in the walkthrough where a story shows a verifier result.

### 8b — Try It: four live stories

Reuse the existing endpoints in `service/main.py`. **Add no new endpoints.**

| Story | Path | Notes |
|---|---|---|
| Get your wallet | `/credential-offer` -> `/issue` | Existing `/wallet` flow, restyled into the story frame |
| Open a bank account | QR -> `/wallet/present` -> `/verify` | Existing `/verify-demo`; five claims travel |
| Prove you are over 18 | same plumbing, one claim | See below |
| A scammer tries it on | relay -> `/verify` | Existing `/verify-demo/phish`, unchanged |

The over-18 story needs no service change. `/authorization-request` returns a fixed claim set, but `/verify` honours `request.query.required_claims` supplied by the client — so construct a request client-side asking for `age_over_18` alone. One claim travels instead of five, against the real verifier, and the new result view shows the difference. This is the highest-value screen in the build.

**Known risk:** `registration_purpose` checks the union of requested and revealed claims against the fixed `CONFIG`. Asking for *fewer* claims should pass. If it trips, do not chase it — fall back to the bank request, note it in `CLAUDE.md`, move on. This is a nice-to-have, not a blocker.

**Explicitly not live:** the DVLA issuance story (needs a second issuer that does not exist), the interactive disclosure picker (stays client-side in tab 1 where it belongs), cross-border (no endpoint; belongs in Takeaway with the Phase 5 anchor-swap data), "take it all back" (not built).

### 8c — Try It: six live species

Keep the existing `/tamper-demo` path and its six species. Render each inside the story frame rather than as a standalone card, so a defect reads as *the bank story going wrong* rather than an abstract check name. Use the new result view.

Do not build endpoints for the seven config-dependent species.

### 8d — Try It: QES as a recorded run

`qes/` and `examples/qes_demo.py` have had no portal presence since Phase 4. Surface them cheaply, following the pattern `examples/generate_in_action_content.py` already establishes:

- Write `examples/generate_qes_content.py` that runs the existing QES demo once and emits `portal/content/qes_walkthrough.json` — real CA chain, real PAdES signature, and the `advanced_not_qualified_cert_as_qes` flip where every cryptographic check passes and `is_qualified` is still false.
- Render it in Try It as a recorded run, labelled honestly as recorded, not live.

No new crypto. No interactive signing — that does not fit the day and pretending otherwise is worse than labelling it.

### 8e — The Experiment page

Two sections, per the target IA:

- **The local PWA and the attestation wall.** Source `docs/ATTESTATION_WALL.md`. This is where the "a browser wallet cannot be a Wallet Unit" lesson gets its page.
- **The 13 defect species as a catalogue.** Read `content/results/wallet_eval.json`, which already contains every species. For each: what it is, what breaks, which check catches it, what a verifier must therefore handle. Precomputed, so it always works. Link the six live ones through to Try It.

### Acceptance

1. The result view shows disclosed claims, withheld claims, digest, audience and nonce before the check ladder. `VerificationResult` schema unchanged.
2. Four stories run live against the running service (or three, if the over-18 fallback was taken — record which in `CLAUDE.md`).
3. Six species break live inside the story frame.
4. `content/qes_walkthrough.json` is generated by a committed script and renders, labelled as a recorded run.
5. `/experiment` shows the attestation wall and all 13 species, driven by the real JSON rather than hardcoded.
6. No new endpoints in `service/main.py`. No changes to `verifier/`, `eval/species.py`, or any frozen contract.

---

## Phase 9 — Takeaway, fallbacks, build green

### What this phase is

Close it out and make the portal survive without the local service.

### Scope

**IN:**

- **`/takeaway`** — one page: the confusion matrix and rate charts (`lib/results.ts` and `RatesChart.tsx` carried over untouched), the Phase 5 anchor-swap divergence, key learnings in prose, and links to the three existing essays. Essays keep their own routes. Total reading surface: two to three pages, not more.
- **Precomputed fallbacks.** Every live surface in Try It needs a committed twin so the page degrades to a recorded run when `localhost:8420` is absent. `content/in_action.json` covers the bank story; generate the rest the same way. Detect service availability via `/health` and switch quietly — do not show an error state to a visitor who was never going to have the service.
- Rebuild, type-check, Chrome-automation sweep for console errors.

**OUT:** deployment. `./deploy/deploy.sh` runs only on a fresh explicit go-ahead from Laksh — the standing rule in `CLAUDE.md`, unchanged by this work.

### Acceptance

1. `/takeaway` renders results, learnings and essay links in two to three pages.
2. With the service stopped, every page in the portal renders and every Try It surface falls back to recorded data with no console errors.
3. With the service running, the live paths work as in Phase 8.
4. `npm run build` clean; route count recorded in `CLAUDE.md`.
5. Not deployed.

---

## Constraints that apply across all three phases

- **The frozen contracts do not move.** `VerificationResult` schema, `TrustAnchorProvider`, `WalletUnlockProvider`. If a change appears to require touching one, stop and raise it.
- **No new verifier logic, no new corpus, no new endpoints.** These phases render and re-parent what Phases 1–6 built. Treat the existing modules as lego.
- **Static export.** `output: "export"` means no Next.js API routes are possible in `portal/`. Everything either runs client-side against the local service or is precomputed at build time.
- **Service workers must not run under `next dev`** — `RegisterServiceWorker.tsx` already gates on `NODE_ENV === "production"`. Leave that gate alone.
- **WebAuthn gestures cannot be browser-automated** in this environment. Verify everything else with Chrome automation; flag the WebAuthn steps for Laksh to check manually rather than spinning on them.
- **Voice rules apply to any prose written.** See `CLAUDE.md` "How to show up". No emoji in portal chrome — note that the prototype's emoji stay inside the phone frames, where they read as app icons, but strip them from the story-picker cards.
- **Update `CLAUDE.md`** at the end of each phase: status, route count, decisions taken, anything deferred.

---

## What is deliberately not being built

Recorded here so it is a decision rather than an omission. Interactive QES signing. Live endpoints for the seven config-dependent defect species. The DVLA role-switch story as a live flow. Per-story deep links. Light mode inside the phone frames. A Claude-backed red-team run (still parked from Phase 3).

If the day runs short, drop in this order: per-story deep links first, then the Takeaway prose, then 8d.

---

*Owned by Laksh. Phases 7–9 of the Wallet & QES lab. Build 7 -> 8 -> 9. Additive over the frozen contracts; the prototype is the spine and the checks live inside it.*
