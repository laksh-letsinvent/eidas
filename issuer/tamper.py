"""
Tamper harness: single-defect variant generators.

Phase 1 manufactures defects; it does not judge them (BUILD_PROMPT_PHASE1.md
"what this phase deliberately leaves unresolved" — that's Phase 2/3's job).
Each function here takes a valid, freshly-built credential/presentation and
introduces exactly one defect species, so Phase 3's corpus builder can pull
labelled `{species, credential}` variants straight off this module.

Two different tampering strategies are used, deliberately:

  - Post-hoc byte/structure edits (altered claim, broken signature, stripped
    KB-JWT) operate directly on the compact wire string — this is what an
    attacker manipulating bytes in flight would actually do.
  - Re-signed variants (wrong audience, stale nonce, expired credential) call
    back into `issuer.sdjwt` with one parameter changed, because those claims
    live *inside* a signature the attacker doesn't hold the key for — you
    cannot forge a "wrong aud, still validly signed" KB-JWT by editing bytes;
    you can only produce one by asking the (compromised, or just
    differently-configured) holder to sign a different payload. That
    distinction is itself part of the learning surface: some defects are
    "attacker edits a wire message," others are "principal behaves badly."
"""

from __future__ import annotations

from dataclasses import dataclass, replace as dataclass_replace
from typing import Any

from cryptography.hazmat.primitives.asymmetric import ec

from issuer import sdjwt
from issuer.crypto import b64url_decode, b64url_encode
from issuer.sdjwt import Credential, Disclosure


@dataclass(frozen=True)
class TamperedVariant:
    species: str
    credential: str  # compact wire form (credential or presentation string)
    description: str


@dataclass(frozen=True)
class TamperContext:
    """Everything needed to build a baseline valid presentation, and then break it one way."""

    issuer_id: str
    issuer_private_key: ec.EllipticCurvePrivateKey
    issuer_public_key: ec.EllipticCurvePublicKey
    holder_private_key: ec.EllipticCurvePrivateKey
    holder_public_jwk: dict
    always_visible_claims: dict
    disclosable_claims: dict
    salt_seed: int
    issued_at: int
    expires_at: int
    reveal: set[str]
    nonce: str
    aud: str
    kb_issued_at: int


def build_credential(ctx: TamperContext, *, expires_at: int | None = None) -> Credential:
    return sdjwt.issue(
        issuer_id=ctx.issuer_id,
        issuer_private_key=ctx.issuer_private_key,
        holder_public_jwk=ctx.holder_public_jwk,
        always_visible_claims=ctx.always_visible_claims,
        disclosable_claims=ctx.disclosable_claims,
        issued_at=ctx.issued_at,
        expires_at=ctx.expires_at if expires_at is None else expires_at,
        salt_seed=ctx.salt_seed,
    )


def build_presentation(ctx: TamperContext, credential: Credential, *, nonce: str | None = None, aud: str | None = None) -> str:
    return sdjwt.present(
        credential,
        reveal=ctx.reveal,
        holder_private_key=ctx.holder_private_key,
        nonce=ctx.nonce if nonce is None else nonce,
        aud=ctx.aud if aud is None else aud,
        kb_issued_at=ctx.kb_issued_at,
    )


# --------------------------------------------------------------------------
# Post-hoc wire-level tampers
# --------------------------------------------------------------------------

def altered_disclosed_claim(presentation: str, claim_name: str, new_value: Any) -> TamperedVariant:
    """Change a revealed claim's value in place. Same salt, new value ⇒ the
    recomputed digest no longer equals the one the issuer signed — the
    disclosure_integrity check's exact failure mode (ATLAS_EUDI.md §9 step 5)."""
    issuer_jwt, disclosure_b64s, kb_jwt = sdjwt.split_compact(presentation)
    disclosures = [Disclosure.parse(b) for b in disclosure_b64s]

    found = False
    new_b64s = []
    for d in disclosures:
        if d.name == claim_name:
            found = True
            tampered = Disclosure.create(d.salt, d.name, new_value)
            new_b64s.append(tampered.b64)
        else:
            new_b64s.append(d.b64)
    if not found:
        raise ValueError(f"{claim_name!r} is not among the disclosures presented")

    parts = [issuer_jwt] + new_b64s
    reassembled = "~".join(parts) + ("~" + kb_jwt if kb_jwt is not None else "~")
    return TamperedVariant(
        species="altered_disclosed_claim",
        credential=reassembled,
        description=f"claim {claim_name!r} changed to {new_value!r}; disclosure digest no longer matches signed _sd entry",
    )


def broken_issuer_signature(compact: str) -> TamperedVariant:
    """Flip one bit in the issuer JWT's signature. Payload and disclosures
    are untouched — only the issuer_signature check (§9 step 2) should fail.

    Side effect worth noting: if this is applied to a presentation (not a
    bare credential), the KB-JWT's sd_hash was computed over the *original*
    issuer-JWT string, signature included — so this edit also makes sd_hash
    stop matching, even though no disclosure changed. One byte, two failing
    checks; that's a real interaction between the two mechanisms, not a bug."""
    issuer_jwt, disclosure_b64s, kb_jwt = sdjwt.split_compact(compact)
    header_b64, payload_b64, sig_b64 = issuer_jwt.split(".")

    sig_bytes = bytearray(b64url_decode(sig_b64))
    sig_bytes[-1] ^= 0x01  # flip the low bit of the last signature byte
    broken_sig_b64 = b64url_encode(bytes(sig_bytes))
    broken_issuer_jwt = f"{header_b64}.{payload_b64}.{broken_sig_b64}"

    parts = [broken_issuer_jwt] + disclosure_b64s
    reassembled = "~".join(parts) + ("~" + kb_jwt if kb_jwt is not None else "~")
    return TamperedVariant(
        species="broken_issuer_signature",
        credential=reassembled,
        description="one bit flipped in the issuer JWT signature; payload/disclosures unchanged",
    )


def stripped_kb_jwt(presentation: str) -> TamperedVariant:
    """Remove the KB-JWT entirely. What's left is bearer-token-shaped: a
    valid signed credential plus disclosures, no proof the presenter holds
    the private key named in `cnf` (§9 step 6; ATLAS_EUDI.md 'Holder ≠ bearer')."""
    issuer_jwt, disclosure_b64s, kb_jwt = sdjwt.split_compact(presentation)
    if kb_jwt is None:
        raise ValueError("presentation has no KB-JWT to strip")
    reassembled = "~".join([issuer_jwt] + disclosure_b64s) + "~"
    return TamperedVariant(
        species="stripped_kb_jwt",
        credential=reassembled,
        description="KB-JWT removed; credential now presented with no holder-binding proof at all",
    )


# --------------------------------------------------------------------------
# Re-signed tampers — the defect lives inside a signature we still hold the
# (holder or issuer) key for, so we re-sign rather than edit bytes.
# --------------------------------------------------------------------------

def wrong_audience_kb_jwt(ctx: TamperContext, credential: Credential, wrong_aud: str) -> TamperedVariant:
    """A validly-signed KB-JWT, but over an audience that isn't the verifier
    asking — a presentation minted for one RP, replayed at another (§9 step 6)."""
    presentation = build_presentation(ctx, credential, aud=wrong_aud)
    return TamperedVariant(
        species="wrong_audience_kb_jwt",
        credential=presentation,
        description=f"KB-JWT aud={wrong_aud!r} instead of the verifier's own audience {ctx.aud!r}",
    )


def stale_nonce_kb_jwt(ctx: TamperContext, credential: Credential, stale_nonce: str) -> TamperedVariant:
    """A validly-signed KB-JWT over a nonce the verifier didn't just issue —
    models both nonce replay and a stale/expired challenge (§9 step 6)."""
    presentation = build_presentation(ctx, credential, nonce=stale_nonce)
    return TamperedVariant(
        species="stale_nonce_kb_jwt",
        credential=presentation,
        description=f"KB-JWT nonce={stale_nonce!r} instead of the verifier's freshly-issued nonce {ctx.nonce!r}",
    )


def expired_credential(ctx: TamperContext, *, expired_at: int) -> TamperedVariant:
    """Reissue with `exp` in the past. Signature and disclosures are all
    otherwise perfectly valid — only the policy check (§9 step 8) should
    reject, which is the point: this defect is deliberately NOT a crypto failure."""
    credential = build_credential(ctx, expires_at=expired_at)
    presentation = build_presentation(ctx, credential)
    return TamperedVariant(
        species="expired_credential",
        credential=presentation,
        description=f"credential exp={expired_at} is in the past; everything else about it verifies cleanly",
    )


def generate_all_variants(ctx: TamperContext, credential: Credential, presentation: str) -> list[TamperedVariant]:
    """One variant per defect species this phase can express — the full set
    the acceptance criteria (BUILD_PROMPT_PHASE1.md) asks for."""
    reveal_name = next(iter(ctx.reveal))
    return [
        altered_disclosed_claim(presentation, reveal_name, "TAMPERED-VALUE"),
        broken_issuer_signature(presentation),
        stripped_kb_jwt(presentation),
        wrong_audience_kb_jwt(ctx, credential, wrong_aud="https://not-the-real-verifier.example"),
        stale_nonce_kb_jwt(ctx, credential, stale_nonce="stale-nonce-from-yesterday"),
        expired_credential(ctx, expired_at=ctx.issued_at - 3600 * 24),
    ]
