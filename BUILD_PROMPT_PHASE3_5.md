# Build Prompt — Phase 3.5 (v2): The Real PWA Wallet

Handoff spec for Claude Code. Read `CLAUDE.md`, `ATLAS_EUDI.md` (§6 wallet security architecture, §5 protocols), `WALLET-QES-LAB-BRIEF.md` (Phase 3.5 row + the attestation wall), and the Phase 1–3 code first. This is the first TypeScript in the lab. Additive over the three frozen contracts — the browser realises them, it does not change them.

Phases 1–3 proved the substrate in Python. Phase 3.5 makes it real in a browser: an installable wallet a person can actually use, with keys that genuinely can't leave the device and a presentation that travels cross-device to the verifier. The point is not a prettier demo — it is to hit, in code, the wall where a browser wallet stops being eIDAS-legal.

---

## What this phase is

Build a Progressive Web App wallet, installable from the portal, that holds a PID and presents it to the Lara Bank verifier over a real (if simplified) OpenID4VP channel. The holder key is a WebCrypto non-extractable key — real key binding, not a Python keypair in a file. Release is gated by WebAuthn — the `WalletUnlockProvider` contract, realised in the browser. Presentation is cross-device: the verifier shows a QR, the phone scans and presents.

**Learning objective:** understand where holder keys actually live and why the wallet's security is hardware, not software. A WebCrypto non-extractable key teaches the shape of holder binding; then you hit the limit — a browser has no WSCD and cannot produce a Wallet Unit Attestation, so no real issuer would provision a PID to it. Discovering that boundary as an engineering fact is the lesson the ARF only states in prose.

**Done for the learning:** you can demonstrate the key cannot be exported, gate a release behind WebAuthn, complete a cross-device presentation the verifier accepts, and write down the exact point where the PWA cannot satisfy eIDAS (the attestation wall).

## Scope

**IN:**
- An installable PWA (manifest + service worker) in TypeScript, on the portal-next stack already in `portal/` (or a `wallet/` route within it — decide and keep it in the family).
- Holder keypair via **WebCrypto with `extractable: false`**; credential + key handle stored in IndexedDB.
- **WebAuthn** unlock gating credential release — the browser implementation of `WalletUnlockProvider.authorize`.
- A **cross-device OpenID4VP-lite** flow: verifier renders a QR carrying the authorization request (nonce, aud, DCQL-lite query); the wallet scans, builds the presentation (reusing the Phase 1 SD-JWT mechanism, re-expressed in TS), and returns it.
- A **thin verifier HTTP endpoint** wrapping the Phase 2 Python verifier so the browser has a real channel to present to. Minimal — just enough to POST a presentation and get back a `VerificationResult`.
- **Two new defect species** the Python actor could not express, added to the taxonomy (12 -> 14) and fed to the Phase 3 corpus as PWA-only: `stolen_device_presentation` (credential present, WebAuthn unlock absent/forged) and `cross_device_origin_phish` (a relaying attacker between the QR and the wallet — the origin/aud mismatch).
- An **attestation-wall note** (`docs/ATTESTATION_WALL.md`): the concrete point where the PWA cannot produce a WUA/WSCD, why, and what a certified Wallet Unit does instead. This is an essay seed for Phase 6.

**OUT (do not build):**
- Any real WSCD, secure enclave, or eIDAS certification — the wall is the lesson, not something to engineer around.
- mdoc/CBOR, QES (Phase 4), the UK anchor (Phase 5).
- Production key management, real push/issuance infrastructure, app-store packaging.
- The Face Value matcher as step-up — the `WalletUnlockProvider` stays WebAuthn here; the trilogy fusion remains deferred behind the contract.

## Realise the frozen contracts, don't change them

- `WalletUnlockProvider` -> WebAuthn implementation. Same shape as `contracts/wallet_unlock.py` (`PresentationContext` in, `UnlockResult` out), expressed in TS.
- `VerificationResult` (`wallet-1.0`) -> the HTTP endpoint returns exactly this shape; the browser renders it. No schema change.
- `TrustAnchorProvider` -> unchanged; the wrapped Python verifier still resolves trust server-side.

If the browser flow seems to need a contract change, stop and raise it — that is a scope decision.

## Acceptance criteria

1. The PWA installs from the portal (Add to Home Screen), works offline for the wallet view, and holds a PID in IndexedDB.
2. The holder key is provably non-extractable — a documented attempt to export it fails.
3. A presentation requires a successful WebAuthn gesture; cancelling WebAuthn blocks release (`stolen_device_presentation`).
4. A full cross-device flow works: verifier QR -> phone scans -> presents -> verifier returns `accept` with the eight checks, rendered in the browser.
5. The `cross_device_origin_phish` species is demonstrated: a mismatched origin/aud is rejected at key_binding.
6. Both new species are added to the Phase 3 corpus as PWA-only and appear in the confusion matrix.
7. `docs/ATTESTATION_WALL.md` states precisely where and why the PWA cannot be a compliant Wallet Unit.

## What this phase deliberately leaves unresolved

The wall itself — the PWA never becomes eIDAS-compliant, by design. QES signing (Phase 4), the UK anchor (Phase 5), and the interactive Try It page that surfaces this wallet to visitors (Phase 6) come next. The Face Value step-up stays deferred behind `WalletUnlockProvider`.

---

*Owned by Laksh. Phase 3.5 (v2) of the Wallet & QES lab. First TypeScript; on the portal-next stack. Additive over the three frozen contracts.*
