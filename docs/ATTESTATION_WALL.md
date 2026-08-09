# The Attestation Wall

Phase 3.5 deliverable. Precise engineering statement of where the PWA wallet built in this phase stops being able to satisfy eIDAS — the essay seed for Phase 6's long-form write-up (paired with the agentic-QES essay, Phase 4/6). See `ATLAS_EUDI.md` §6 for the underlying vocabulary (WSCD, WSCA, WUA, certification).

## The claim being tested

This PWA holds a genuine non-extractable P-256 key (`portal/lib/wallet/crypto.ts`), gates every release behind a real WebAuthn platform-authenticator gesture, produces a real KB-JWT holder binding, and completes a real (if local) cross-device OpenID4VP-lite presentation that the Phase 2 verifier accepts. Does that make it an EUDI Wallet Unit?

No. Not because any of it is fake — it isn't — but because none of it reaches the specific bar the ARF sets, and that gap is structural, not a missing feature this phase forgot to build.

## What's real here

Worth stating plainly, because the wall means nothing if the rest is hand-waved:

- **Non-extractable key.** `crypto.subtle.generateKey({name: "ECDSA", namedCurve: "P-256"}, false, ["sign"])` — the `false` is `extractable`. `components/wallet/KeyExportDemo.tsx` calls `crypto.subtle.exportKey("jwk", privateKey)` against that key and it throws `InvalidAccessError: ... key is not extractable`, live, on a button press. That's not a claim — it's a demonstrated failure, verified in this build against a real Chrome instance.
- **WebAuthn-gated release.** `lib/wallet/unlock.ts`'s `authorize()` realizes `contracts/wallet_unlock.py`'s frozen `WalletUnlockProvider` shape in the browser: `navigator.credentials.get()` is the gesture, a cancelled or failed assertion returns `{authorized: false}`, and — verified via network inspection during this build — the wallet never calls `sdjwt.present` or POSTs anything when denied. Not merely "declines to send the result": no presentation is ever built.
- **Real KB-JWT holder binding.** `lib/wallet/sdjwt.ts`'s `present()` is a line-for-line re-expression of `issuer/sdjwt.py`'s presentation logic — the same `sd_hash`, the same nonce/aud binding, verified against the same Phase 2 verifier.
- **A real cross-device presentation.** The two-tab (QR) flow in `app/verify-demo/` and `app/wallet/present/` was driven end to end during this build: a separate "verifier" tab renders a live authorization request as a QR, a separate "wallet" tab scans it, presents, and the verifier tab — coordinating only through the FastAPI relay (`service/main.py`'s `/present` + `/present/{nonce}`) — renders a real `ACCEPT` with all eight checks passing.

## The wall, precisely

Three separately-named gaps, each a specific ARF term this PWA cannot produce:

**No WSCD.** The ARF's Wallet Secure Cryptographic Device is certified hardware — a secure element, an eSIM, an external smartcard — where keys physically live and signing physically happens, keys never leaving it. `extractable: false` is a genuine, useful property, but it's a *software* promise enforced by the browser's WebCrypto implementation, not hardware-backed key isolation with a certification trail behind it. The practical difference: an OS-level compromise (malware running with the same user's privileges) cannot *export* this key, but it can still *invoke* it — ask the browser process to sign something, exactly as the legitimate wallet code does. A WSCD is certified specifically against that stronger threat model, not just against export.

**No WUA.** Nothing this build produced attests the wallet app's own provenance or integrity to anyone. Look at `service/main.py`'s `POST /issue` handler: it verifies the wallet's key-proof JWT (proof of possession of the holder key) and then issues a PID — full stop. A real PID Provider's issuance flow additionally requires a Wallet Unit Attestation before that point: a signed statement, from a certified Wallet Provider, that *this* Wallet Unit is genuine and backed by a real WSCD. This build's `/issue` endpoint has no such check to perform, because there is no WUA to check — that absence is the literal, concrete place a real issuer would refuse this wallet.

**No certification.** No CIR-defined conformance or security assessment has run against any of this code. The Wallet Solution as a whole — not just one key or one flow — is what the ARF requires certified before an issuer will provision a genuine PID to it.

## What a certified Wallet Unit does instead

Keys live in a certified WSCD from the moment of provisioning, managed by a WSCA the certification regime has also assessed. At issuance, the wallet presents a WUA — a signed attestation of its own genuineness — the way this build's credential presents its `cnf` claim to prove holder-key possession, one level up: the Wallet Unit proving *itself* before it's trusted to hold anything. That attestation is periodically re-checked, not a one-time formality. The whole chain — WSCD, WSCA, WUA, certification — is what lets an issuer provision a PID to a device it has never seen, and lets a relying party trust a presentation from a wallet it has never talked to directly.

## Why this still teaches the real thing

The protocol shape built in this phase is faithful: OpenID4VCI-lite issuance, OpenID4VP-lite presentation with DCQL-lite, SD-JWT VC selective disclosure, KB-JWT holder binding, nonce/audience freshness, a real cross-device relay. None of that is simulated or approximated — it's the same mechanism Phases 1–3 proved in Python, now realized against browser primitives. The wall is specifically about *hardware trust and certification*, a layer beneath the protocol, not about the credential format or presentation protocol being make-believe. Understanding exactly where that layer starts — by hitting it in working code rather than reading about it in the ARF's prose — is the phase's actual deliverable.

## Pointer to Phase 6

This document is the seed for the long-form public write-up, paired with the agentic-QES essay ("can an AI agent hold a QES and sign for you?") that Phase 4/6 develops. The parallel is deliberate: one essay asks whether *software* can be trusted with sole control of a signing key; this one shows, in code, the specific certification apparatus that has to exist before *any* software — agentic or not, browser-based or not — clears that bar for a real EUDI Wallet Unit.
