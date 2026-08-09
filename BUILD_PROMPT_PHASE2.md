# Build Prompt — Phase 2: The Three-Actor Loop (Issuer · Wallet · Verifier)

Handoff spec for Claude Code. Read `CLAUDE.md`, `ATLAS_EUDI.md` (especially §5 protocols and §9 the verification decision), and the Phase 1 code before starting. When this prompt and `CLAUDE.md` disagree, `CLAUDE.md` wins on scope; this prompt wins on implementation detail.

Phase 1 built the issuer and the tamper harness. Phase 2 builds the other two actors — a wallet and the **Lara Bank verifier** — and wires them into a loop over a simplified OpenID4VCI/VP. The verifier is the product. Everything additive over the three frozen contracts; do not modify them.

---

## What this phase is

Stand up the full request/response loop a real relying party runs, minus the HTTP: an issuer offers a credential, a wallet holds it and presents on request, and the verifier decides accept/reject by running the ordered checks from ATLAS §9 and emitting a `VerificationResult`.

**Learning objective:** understand where each defence actually lives. Replay defence is the nonce/aud binding in the KB-JWT, not the UI. Trust is the path from issuer signature to a trusted-list anchor, not the signature itself. Over-asking is caught by the registration certificate, not by good manners. After this phase you can point at the exact check that stops each attack, and name the ones the protocol *can't* stop (which is Phase 3's finding).

**Done for the learning, not just the code:** given any Phase 1 tamper variant, you can predict which of the eight checks fails and why, then run the verifier and watch it happen.

## Scope

**IN:**
- A **wallet actor** (`wallet/`) that holds a credential + holder key, receives a presentation request, calls `WalletUnlockProvider.authorize`, and produces a presentation via `issuer.sdjwt.present`.
- A **verifier** (`verifier/`) that runs the eight ordered checks and emits a `VerificationResult` (schema `wallet-1.0`) validated against `contracts/verification_result.schema.json`.
- A **simplified OpenID4VCI** issuance exchange: credential offer -> wallet key-proof -> issued credential. In-process objects, not HTTP.
- A **simplified OpenID4VP** presentation exchange: verifier builds an authorization request (nonce, aud, and a **DCQL-lite** query naming required claims + required tier/LoA); wallet responds; verifier verifies.
- Two Phase-2-local provider stubs (not frozen contracts, but designed swappable): a `RegistrationProvider` (the RP's registration certificate — which claims it may request) and a `StatusListProvider` (revocation). Minimal, real enough to make checks 7 and 4 fire.
- An `examples/loop_demo.py` runnable walkthrough and tests covering happy path + every Phase 1 tamper species.

**OUT (do not build in Phase 2):**
- The eval corpus, confusion matrix, and AI red-team — that is Phase 3.
- Real HTTP, real OpenID4VP wire format, real DCQL, response encryption (JARM). Model the fields that matter (nonce, aud, query, sd_hash), skip the transport.
- mdoc/CBOR, the PWA wallet, QES, real trusted lists, real revocation infrastructure.
- Batch issuance / unlinkability mitigations (named in the Atlas, not built here).

## Build on the Phase 1 surface (exact names)

Reuse, do not reimplement:
- `issuer.sdjwt`: `issue(...)`, `present(credential, reveal, holder_private_key, nonce, aud, kb_issued_at)`, `decode(...)`, `split_compact(...)`, `Credential`, `Disclosure`.
- `issuer.crypto`: `es256_verify`, `decode_jwt_parts`, `verify_jwt`, `sha256_b64url`, `jwk_to_public_key`, `KeyPair`.
- `issuer.pid`: `build_pid_claims`, `SAMPLE_SUBJECT`, `compute_age_over_18`, `VCT`, `DISCLOSABLE_KEYS`.
- `issuer.tamper`: `TamperContext`, `generate_all_variants(...)`, the six `species` labels (`altered_disclosed_claim`, `broken_issuer_signature`, `stripped_kb_jwt`, `wrong_audience_kb_jwt`, `stale_nonce_kb_jwt`, `expired_credential`).
- `contracts.trust_anchor`: `TrustAnchorProvider`, `LocalDictTrustAnchorProvider`, `TrustResolution`.
- `contracts.wallet_unlock`: `WalletUnlockProvider`, `AlwaysYesWalletUnlockProvider`, `PresentationContext`, `UnlockResult`.

## The verifier: the eight checks (ATLAS §9)

The verifier runs these in order and records each as `{name, result: pass|fail|skip, detail}` in the `checks` array. Ordering matters: a hard cryptographic failure short-circuits later checks to `skip`, so the record shows the first fatal reason rather than a cascade.

1. **format** — parse issuer-JWT + disclosures + KB-JWT via `split_compact`/`decode`. Malformed -> fail, rest skip.
2. **issuer_signature** — `es256_verify` the issuer JWT against the key from the trust provider. Deterministic.
3. **trust_path** — `TrustAnchorProvider.resolve(iss)`; None -> fail (untrusted issuer even if the signature verified). Records `trust.tier`, `trust.anchor_id`, `trust.loa`.
4. **revocation** — `StatusListProvider`; revoked -> fail. If no status source configured, `skip` (allowed by schema) — but prefer a real minimal status list so the check can fire.
5. **disclosure_integrity** — recompute each presented disclosure's digest, match against the signed `_sd` array. Altered claim -> fail.
6. **key_binding** — verify the KB-JWT against the holder key in `cnf`, check `aud` == this verifier, `nonce` == the one issued, and `sd_hash` matches the presented disclosure set. Replay/wrong-audience/stripped-KB -> fail.
7. **registration_purpose** — compare the claims actually disclosed (and requested in the DCQL-lite query) against the `RegistrationProvider` certificate. Requesting or receiving beyond registration -> fail (over-asking).
8. **policy** — `exp` not passed; `trust.loa` meets the journey's required LoA; claim consistency (`age_over_18` must agree with `birth_date` via `compute_age_over_18`). Any violation -> fail.

`decision` = accept iff every non-skipped check is pass. `policy_version` is a string the verifier stamps (e.g. `"lara-onboarding-v1"`). `timing.total_ms` measured.

Checks 2–6 are deterministic cryptography. Checks 7–8 are policy the RP wrote. Keep that split legible in the code — it is the seam Phase 3's red-team pulls on.

## The loop

**Issuance (OpenID4VCI-lite):** issuer emits a credential offer for the PID; wallet generates/holds a holder keypair and proves possession; issuer calls `issuer.sdjwt.issue` binding the holder's `cnf` key; wallet stores the `Credential`. Register the issuer in a `LocalDictTrustAnchorProvider` as tier `PID`, LoA `high`.

**Presentation (OpenID4VP-lite):** verifier builds an authorization request — fresh `nonce`, its own `aud`, and a DCQL-lite query listing required claims (e.g. `age_over_18`, `given_name`) and required tier/LoA. Wallet resolves the query against its credential, calls `WalletUnlockProvider.authorize(PresentationContext(...))`, and if authorized calls `present(...)` revealing only the requested claims. Verifier runs the eight checks -> `VerificationResult`.

## Suggested file layout

```
wallet/
  wallet.py         # holds credential + holder key; handles offer + present-request
  request.py        # DCQL-lite query + authorization-request objects
verifier/
  verify.py         # the eight checks -> VerificationResult
  providers.py      # RegistrationProvider + StatusListProvider stubs (Phase-2-local)
  policy.py         # LoA table, required-claims policy, claim-consistency rules
examples/
  loop_demo.py      # issue -> request -> present -> verify, printed end to end
tests/
  test_verifier.py  # happy path + one test per tamper species + policy defects
```

## Acceptance criteria

1. Happy path: a PID issued, requested, presented revealing a subset, and **accepted** — every applicable check `pass`, `decision: "accept"`, result validates against the schema.
2. Every Phase 1 tamper species, run through the verifier, is **rejected at the correct check** (altered claim -> disclosure_integrity; broken signature -> issuer_signature; stripped/wrong-aud/stale-nonce KB -> key_binding; expired -> policy).
3. An untrusted issuer (not registered in the trust provider) -> reject at trust_path, even with a valid signature.
4. A revoked credential -> reject at revocation (if the status list is built); otherwise that check is `skip` and documented.
5. Over-asking (query/disclosure beyond the registration certificate) -> reject at registration_purpose.
6. A policy defect where `age_over_18` disagrees with `birth_date`, and one where LoA is below the journey requirement -> reject at policy.
7. Every emitted `VerificationResult` validates against `contracts/verification_result.schema.json` (assert in tests). `qes` stays null.
8. `examples/loop_demo.py` runs clean and reads as a teaching artefact: the eight checks visible, firing in order, for both an accept and a reject.

## What this phase deliberately leaves unresolved

Whether the verifier is *right at scale* — that is Phase 3's corpus and confusion matrix. Whether an adversary can find gaps in checks 7–8 — that is the red-team. The `RegistrationProvider` and `StatusListProvider` are thin stubs, not real infrastructure. Unlinkability is not addressed. mdoc, HTTP, and the PWA are still out.

---

*Owned by Laksh. Phase 2 of the Wallet & QES lab. Python core. Additive over the three frozen contracts — if a check can't be expressed without changing `verification_result.schema.json`, stop and raise it.*
