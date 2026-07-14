# Build Prompt — Phase 1: Hand-Rolled SD-JWT VC Issuer

Handoff spec for Claude Code. This document is the contract between the design (in `WALLET-QES-LAB-BRIEF.md` and `ATLAS_EUDI.md`) and the first code. Read both of those first. When this prompt and the brief disagree, the brief wins on scope; this prompt wins on implementation detail.

Owner: Laksh. Build agent: Claude Code, in the new sibling repo (not the strategy folder).

---

## What this phase is

Build an SD-JWT VC issuer by hand, in Python, on cryptographic primitives only — no SSI or wallet libraries. Issue a Lara Bank-relevant PID, decode it, selectively disclose from it, and tamper with it. The point is not a working issuer; the point is that after this phase you can explain, byte by byte, why a holder can hide a claim but cannot forge one, and where the issuer's signature draws that line.

**Learning objective (the reason this exists):** own the SD-JWT VC structure completely — the salted-hash disclosure mechanism, the issuer signature's scope, the holder key binding — so that every later verifier check in the eval maps to something you built, not something a library did for you.

**Definition of done for the learning, not just the code:** you can take a valid credential, alter one disclosed claim, and predict exactly which verifier check fails and why, before running it.

## Scope

**IN:**
- One PID issuer (`issuer/`) producing SD-JWT VC credentials.
- Selective disclosure: issue with N disclosable claims, present a subset.
- Holder key binding: credential embeds a holder public key; a key-binding JWT is producible over a nonce + audience.
- A tamper harness: functions that take a valid credential and produce each single-defect variant (altered claim, broken signature, stripped KB-JWT, etc.) for later eval use.
- The three frozen contracts defined as code stubs (below), even where Phase 1 doesn't exercise them.

**OUT (deliberately — do not build in Phase 1):**
- The verifier. That is Phase 2. Phase 1 produces credentials and defects; it does not judge them.
- Any network protocol (OpenID4VCI/VP). Issuance here is a direct function call, not an HTTP flow.
- mdoc/CBOR. SD-JWT VC only.
- Trust lists, revocation status lists, RP registration. Stubbed via the contract interface, not implemented.
- The wallet as an actor. A "holder" here is a keypair and a function, not a wallet.
- Any real key management (HSM, WSCD). Keys are software keys in memory/files, seeded.

## The three frozen contracts

Freeze these before writing issuer logic. They are the shapes everything downstream stays additive against. If Phase 1 experience suggests one is wrong, stop and raise it as a scope decision — do not quietly change it mid-build.

### 1. `VerificationResult` schema (`schema_version: "wallet-1.0"`)

The per-presentation record the Phase 2 verifier will emit. Phase 1 does not produce these, but the schema is fixed now so the verifier and eval are zero-churn later. It deliberately carries null fields for checks Phase 1/2 don't run (the QES track fills them in Phase 4), exactly as the bio-authn schema reserved `pad`.

Required shape (JSON):
- `schema_version`: `"wallet-1.0"`
- `presentation_id`: string
- `decision`: `"accept" | "reject"`
- `checks`: ordered array, each: `{ name, result: "pass"|"fail"|"skip", detail }` — names drawn from ATLAS §9 (`format`, `issuer_signature`, `trust_path`, `revocation`, `disclosure_integrity`, `key_binding`, `registration_purpose`, `policy`)
- `trust`: `{ tier: "PID"|"QEAA"|"PuB-EAA"|"EAA"|null, anchor_id: string|null, loa: "high"|"substantial"|"low"|null }`
- `policy_version`: string
- `qes`: null in wallet track (reserved for Phase 4)
- `timing`: `{ total_ms }`

Validate every emitted result against this schema in Phase 2. Define it as a JSON Schema file now.

### 2. `TrustAnchorProvider` interface

The single question the verifier asks about an issuer: "is this issuer trusted, at what tier, under which framework, and what's its anchor?" One method, swappable implementations (EU trusted list in Phase 2, DIATF-style in Phase 5).

```
class TrustAnchorProvider(Protocol):
    def resolve(self, issuer_id: str) -> TrustResolution | None: ...
    # returns tier, loa, anchor_id, public_key(s) for signature verification
    # None => issuer not on any list => untrusted
```

Phase 1 ships a stub implementation backed by a local dict of the issuer(s) it creates. That is enough to keep the interface honest.

### 3. `WalletUnlockProvider` interface

The question a wallet asks before releasing a credential: "may this be released for this presentation?" v1 stub is always-yes. Frozen now so the PWA (WebAuthn) and the trilogy option (Face Value matcher) slot in without churn.

```
class WalletUnlockProvider(Protocol):
    def authorize(self, presentation_context) -> UnlockResult: ...
```

Phase 1 ships the always-yes stub only. It exists so Phase 3.5 is additive.

## What to build (issuer)

1. **Crypto layer.** Use `cryptography` for primitives (EC keys, ES256 signing, SHA-256). No JWT/SD-JWT library — assemble and sign the JWT by hand (base64url header.payload, sign, append signature). Writing this by hand is the point.

2. **Issuer.** Given a claims dict and a holder public key, produce an SD-JWT VC:
   - Split claims into always-visible vs selectively-disclosable.
   - For each disclosable claim: generate a salt, build the disclosure (`[salt, name, value]`), hash it (SHA-256, base64url), place the digest in the signed payload's `_sd` array.
   - Embed the holder public key (`cnf` claim) for key binding.
   - Sign the payload with the issuer key (ES256).
   - Output the combined format: `<issuer-jwt>~<disclosure1>~<disclosure2>~...~` (trailing tilde; KB-JWT appended at presentation, not issuance).

3. **Holder-side present.** Given an issued credential and a chosen subset of claims to reveal, produce a presentation: the issuer JWT + only the selected disclosures + a KB-JWT signed by the holder key over a supplied `nonce` and `aud`.

4. **Decode / inspect.** A function that pretty-prints any credential or presentation: header, payload, which digests have matching disclosures, which claims are hidden. This is the learning surface — make it readable.

5. **Tamper harness.** Functions producing single-defect variants from a valid credential/presentation, one per defect species this phase can express:
   - altered disclosed claim (value changed, digest now mismatches)
   - broken issuer signature (flip a byte)
   - stripped KB-JWT
   - wrong-audience KB-JWT
   - replayed/stale nonce
   - expired credential (`exp` in the past)
   Each returns a labelled object `{ species, credential }` so Phase 3's corpus builder can consume them directly.

## PID corpus / schema

Copy the ARF **PID Rulebook** attributes verbatim rather than inventing a schema (brief, open question 1 — resolved: verbatim). Minimum claim set: `family_name`, `given_name`, `birth_date`, `age_over_18`, `nationality`, `issuing_country`, `issuing_authority`, `expiry_date`. Mark the derived `age_over_18` claim explicitly — it's the one the AI red-team will later probe for consistency against `birth_date` (the §8 policy-layer defect).

Everything seeded and reproducible. One issuer keypair, one or two holder keypairs, fixed salts under a seed so runs are deterministic. The only files written are credentials and their decoded views. No network calls at all in this phase — any outbound call is a bug.

## Suggested file layout (Claude Code may refine)

```
issuer/
  crypto.py         # primitives: keys, sign, verify, hash, base64url
  sdjwt.py          # issue, present, decode
  pid.py            # PID schema + sample subject data
  tamper.py         # single-defect variant generators
contracts/
  verification_result.schema.json
  trust_anchor.py   # Protocol + local-dict stub
  wallet_unlock.py  # Protocol + always-yes stub
examples/
  issue_and_inspect.py   # the runnable walkthrough
tests/
  test_sdjwt.py     # roundtrip, disclosure integrity, tamper detection intent
```

## Acceptance criteria

The phase is done when:
1. A PID is issued, and `decode` shows the signed payload with `_sd` digests and the separate disclosures.
2. A presentation reveals a chosen subset; hidden claims appear only as unmatched digests, never as values.
3. The KB-JWT verifies against the embedded holder key over the right nonce/aud, and fails over the wrong ones.
4. Every tamper function produces a variant that is *structurally* the intended defect (verified by a test asserting the specific corruption — e.g. altered-claim's recomputed digest ≠ signed digest). Note: Phase 1 asserts the defect exists, not that a verifier catches it — that's Phase 2.
5. The three contracts exist as importable stubs and the schema validates a hand-written sample result.
6. `examples/issue_and_inspect.py` runs clean and reads as a teaching artefact — someone can follow the SD-JWT mechanism from its output alone.

## What this phase deliberately leaves unresolved

The verifier (Phase 2) decides whether these defects are caught — Phase 1 only manufactures them. The trust path, revocation, and registration checks are interfaces, not logic. Unlinkability/correlation is not addressed; batch issuance is not built. Those are named here so they're not mistaken for gaps.

---

*Created July 2026. Owned by Laksh. Phase 1 of the Wallet & QES lab. Stack: Python core (TypeScript arrives with the PWA wallet in Phase 3.5). Freezes: `VerificationResult` (wallet-1.0), `TrustAnchorProvider`, `WalletUnlockProvider`.*
