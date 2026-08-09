# AES vs QES: What's Cryptographic, What's Legal

Phase 4 deliverable. Precise statement of the AES/QES distinction as built, not just described — the essay seed for Phase 6's write-up, paired with `docs/ATTESTATION_WALL.md`'s wallet-side version of the same question.

## The claim being tested

`qes/` builds a toy CA chain — root, an intermediate acting as a QTSP, a leaf signing certificate — and signs a PDF with it (PAdES baseline-B, ECDSA P-256, a real embedded timestamp). Two versions of that leaf certificate exist: one marked "qualified," one marked "advanced." Is the resulting signature distinguishable, byte by byte, before you check which leaf signed it?

No. That's not a limitation of this lab's toy model — it's the actual state of affairs eIDAS encodes, made visible in code.

## What's identical

Everything that matters cryptographically:

- Same curve, same algorithm — P-256, ECDSA, SHA-256, via `issuer.crypto.KeyPair`, the same primitives Phase 1's wallet track uses.
- Same CMS/PAdES container — a detached CAdES signature embedded in the PDF's `/Contents`, the same byte-range digest mechanism, the same chain-of-trust validation algorithm (`pyhanko_certvalidator`, offline, no network fetch).
- Same timestamp mechanism — an RFC 3161-shaped token from the same toy TSA, chained through the same QTSP.
- Same key usage, same certificate fields, down to the extension list — with exactly one exception.

Run `examples/qes_demo.py`'s last experiment and look at the output: `signature_valid`, `chain_trusted`, `document_unmodified`, `timestamp_valid` are all `true` for the advanced-cert signature. A verifier checking only those four fields would accept it as readily as the qualified one. Nothing about the bytes says otherwise.

## The one bit that differs

`qes/ca.py`'s `build_leaf_cert(..., qualified=True)` attaches a single X.509 extension: `id-pe-qcStatements` (OID `1.3.6.1.5.5.7.1.3`, RFC 3739), carrying a `qc_compliance` statement (ETSI EN 319 412-5, OID `0.4.0.1862.1.1`). `qualified=False` omits it. That's the entire mechanism — not a house convention invented for this lab, the real standard a real QTSP uses to assert "this certificate meets the qualified requirements," read back by the same library (`pyhanko.sign.ades.qualified_asn1`) that a real relying party's PAdES validator would use.

What that extension actually asserts is a chain of legal and procedural facts, not a cryptographic one: the QTSP verified the signer's identity to eIDAS's standard, the signing key was generated and held in a QSCD, the QTSP itself holds accreditation to issue qualified certificates at all. None of that is checkable by inspecting the signature — it's checkable by trusting the QTSP's attestation, the same way a driving licence's legal weight comes from the issuing authority's accreditation, not from the card stock.

## What a real QSCD adds that this lab's model can't

`qes/ca.py`'s keys are software keys in a Python process. A real QSCD (Qualified Signature Creation Device — a smartcard, or increasingly a remote QSCD run by a QTSP with the signer in sole control) is certified hardware, the signing-side mirror of Phase 3.5's WSCD/attestation-wall lesson: the qcStatements extension's `qc_sscd` variant (`0.4.0.1862.1.4`, not used in this lab) is specifically how a certificate asserts "this key lives in one of those." A `qualified=True` leaf cert in this lab asserts the identity-verification half of "qualified" honestly enough to demonstrate the extension mechanism — it cannot assert the hardware half, because there's no hardware behind it. Same wall, same shape, different signature.

## The five break-it experiments

| Defect | What's tampered | Check that catches it | Crypto or legal/procedural failure? |
|---|---|---|---|
| `document_modified_after_signing` | A second incremental PDF update after signing, no re-sign | `document_unmodified` | Crypto-adjacent — pyHanko's diff-analysis engine, not the signature digest itself (which stays valid over its own revision) |
| `signature_from_revoked_cert` | Leaf serial added to the toy revocation set | `chain_trusted` | Procedural — the signature is mathematically sound; the QTSP has withdrawn its vouching |
| `missing_or_forged_timestamp` | Signed with no timestamper | `timestamp_valid` | Crypto — no token to verify at all |
| `chain_to_untrusted_ca` | Signed by a cert chaining to an unregistered root | `chain_trusted` | Crypto — path-building genuinely fails |
| `advanced_not_qualified_cert_as_qes` | Advanced cert, no qcStatements extension, otherwise clean | `is_qualified` (not a rejection) | **Purely legal/procedural** — every cryptographic check passes |

Four of the five are rejections. The fifth is the point: a correct QES verifier's job on that one row isn't to reject anything — it's to correctly report `is_qualified: false` on a signature that verified perfectly. Building a verifier that only checks `signature_valid`/`chain_trusted`/`timestamp_valid` and calls it done would silently accept AES as QES. That's not a hypothetical bug; it's the natural failure mode of not knowing this distinction exists.

## Pointer to Phase 6

This is the essay seed for the agentic-QES write-up ("can an AI agent hold a QES and sign for you?"). The sole-control question that essay asks turns on exactly the axis this document names: an AI agent holding a private key can produce a cryptographically perfect signature indistinguishable from a human's, the same way the advanced cert's signature is indistinguishable from the qualified one. Whatever answer that essay lands on, it isn't going to come from the cryptography — same lesson, same place the answer actually has to live.
