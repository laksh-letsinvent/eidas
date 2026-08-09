"""
Hand-rolled SD-JWT VC: issue, present, decode.

No SD-JWT/JOSE library — this module *is* the mechanism. Format follows the
SD-JWT / SD-JWT VC drafts closely enough to be recognisable, assembled by
hand so every byte is accounted for:

    Issuance (combined) format:
        <issuer-jwt>~<disclosure_1>~<disclosure_2>~...~
        (trailing tilde, no KB-JWT yet)

    Presentation format:
        <issuer-jwt>~<selected_disclosure_1>~...~<KB-JWT>
        (KB-JWT replaces what was after the last tilde; nothing appended
        at all if zero disclosures were selected, still one tilde before it)

A disclosure is `base64url(json([salt, claim_name, claim_value]))`. Its
SHA-256 digest is what the issuer puts in the signed `_sd` array — the
credential holder can withhold the disclosure string entirely (hiding the
claim), but cannot invent a new one, because they don't have the issuer's
private key to re-sign a payload with a substitute digest. That's the whole
selective-disclosure trick in one sentence.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from cryptography.hazmat.primitives.asymmetric import ec

from issuer.crypto import (
    b64url_decode,
    b64url_encode,
    decode_jwt_parts,
    encode_jwt,
    jwk_to_public_key,
    sha256_b64url,
    verify_jwt,
)
from issuer.pid import VCT

SD_ALG = "sha-256"
ISSUER_JWT_TYP = "dc+sd-jwt"  # current SD-JWT VC media-type-ish `typ`
KB_JWT_TYP = "kb+jwt"


# --------------------------------------------------------------------------
# Disclosures
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Disclosure:
    salt: str  # base64url, generated per claim
    name: str
    value: Any
    b64: str  # the wire form: base64url(json([salt, name, value]))
    digest: str  # sha256_b64url(b64) — what the signed payload actually carries

    @classmethod
    def create(cls, salt: str, name: str, value: Any) -> "Disclosure":
        raw = json.dumps([salt, name, value], separators=(",", ":")).encode("utf-8")
        b64 = b64url_encode(raw)
        digest = sha256_b64url(b64.encode("ascii"))
        return cls(salt=salt, name=name, value=value, b64=b64, digest=digest)

    @classmethod
    def parse(cls, b64: str) -> "Disclosure":
        raw = b64url_decode(b64)
        salt, name, value = json.loads(raw)
        digest = sha256_b64url(b64.encode("ascii"))
        return cls(salt=salt, name=name, value=value, b64=b64, digest=digest)


def _deterministic_salt(seed: int, claim_name: str) -> str:
    """16 bytes of salt derived from (seed, claim_name) — reproducible runs, lab-only.

    A real issuer must use a CSPRNG per disclosure; a fixed seed here exists
    only so example/test output is stable across runs (CLAUDE.md: "everything
    seeded and reproducible").
    """
    digest = hashlib.sha256(f"eidas-lab-disclosure-salt:{seed}:{claim_name}".encode()).digest()
    return b64url_encode(digest[:16])


# --------------------------------------------------------------------------
# Credential (post-issuance, pre-presentation)
# --------------------------------------------------------------------------

@dataclass
class Credential:
    issuer_jwt: str
    disclosures: list[Disclosure] = field(default_factory=list)

    def compact(self) -> str:
        """Issuance combined format: issuer-jwt~disclosure~...~ (trailing tilde)."""
        parts = [self.issuer_jwt] + [d.b64 for d in self.disclosures]
        return "~".join(parts) + "~"

    def disclosure_by_name(self, name: str) -> Disclosure:
        for d in self.disclosures:
            if d.name == name:
                return d
        raise KeyError(f"no disclosure named {name!r} on this credential")


def issue(
    *,
    issuer_id: str,
    issuer_private_key: ec.EllipticCurvePrivateKey,
    holder_public_jwk: dict,
    always_visible_claims: dict,
    disclosable_claims: dict,
    issued_at: int,
    expires_at: int,
    salt_seed: int,
) -> Credential:
    """Issue an SD-JWT VC. `disclosable_claims` becomes one Disclosure each;
    only their digests land in the signed payload's `_sd` array."""
    disclosures = [
        Disclosure.create(_deterministic_salt(salt_seed, name), name, value)
        for name, value in disclosable_claims.items()
    ]

    payload = {
        **always_visible_claims,
        "iss": issuer_id,
        "vct": VCT,
        "iat": issued_at,
        "exp": expires_at,
        "cnf": {"jwk": holder_public_jwk},
        "_sd": [d.digest for d in disclosures],
        "_sd_alg": SD_ALG,
    }
    header = {"alg": "ES256", "typ": ISSUER_JWT_TYP}
    issuer_jwt = encode_jwt(header, payload, issuer_private_key)
    return Credential(issuer_jwt=issuer_jwt, disclosures=disclosures)


# --------------------------------------------------------------------------
# Presentation (holder reveals a subset + proves key binding)
# --------------------------------------------------------------------------

def _sd_hash_input(issuer_jwt: str, selected: list[Disclosure]) -> str:
    return "~".join([issuer_jwt] + [d.b64 for d in selected]) + "~"


def present(
    credential: Credential,
    *,
    reveal: set[str],
    holder_private_key: ec.EllipticCurvePrivateKey,
    nonce: str,
    aud: str,
    kb_issued_at: int,
) -> str:
    """Produce a presentation: issuer-jwt~selected-disclosures~KB-JWT.

    The KB-JWT's `sd_hash` binds it to *exactly* this set of selected
    disclosures — swap in a different disclosure after the fact and sd_hash
    no longer matches (issuer.tamper exercises this)."""
    selected = [d for d in credential.disclosures if d.name in reveal]
    sd_hash_input = _sd_hash_input(credential.issuer_jwt, selected)

    kb_payload = {
        "iat": kb_issued_at,
        "aud": aud,
        "nonce": nonce,
        "sd_hash": sha256_b64url(sd_hash_input.encode("ascii")),
    }
    kb_header = {"alg": "ES256", "typ": KB_JWT_TYP}
    kb_jwt = encode_jwt(kb_header, kb_payload, holder_private_key)

    return sd_hash_input + kb_jwt


# --------------------------------------------------------------------------
# Decode / inspect — the learning surface. Tolerant of malformed input:
# this is an inspector, not the verifier (that's Phase 2).
# --------------------------------------------------------------------------

def split_compact(compact: str) -> tuple[str, list[str], str | None]:
    """Split any compact string (issuance or presentation) into
    (issuer_jwt, disclosure_b64_list, kb_jwt_or_None)."""
    parts = compact.split("~")
    issuer_jwt = parts[0]
    if parts[-1] == "":
        # issuance format: trailing tilde, no KB-JWT
        return issuer_jwt, parts[1:-1], None
    # presentation format: last part is the KB-JWT
    return issuer_jwt, parts[1:-1], parts[-1]


def decode(
    compact: str,
    *,
    issuer_public_key: ec.EllipticCurvePublicKey | None = None,
    expected_nonce: str | None = None,
    expected_aud: str | None = None,
) -> dict:
    """Decode a credential or presentation into a plain-dict report, verifying
    what keys are supplied for. Never raises on a *tampered* input — every
    field the tamper harness can break shows up as a False/mismatch in the
    report instead, since the whole point is to see the defect, not crash on it.
    """
    issuer_jwt, disclosure_b64s, kb_jwt = split_compact(compact)

    header, payload, signature, signing_input = decode_jwt_parts(issuer_jwt)
    issuer_sig_valid = None
    if issuer_public_key is not None:
        from issuer.crypto import es256_verify

        issuer_sig_valid = es256_verify(issuer_public_key, signing_input, signature)

    signed_digests = set(payload.get("_sd", []))
    disclosures = [Disclosure.parse(b64) for b64 in disclosure_b64s]

    matched, unmatched_disclosures = [], []
    for d in disclosures:
        (matched if d.digest in signed_digests else unmatched_disclosures).append(d)
    hidden_digests = signed_digests - {d.digest for d in matched}

    report: dict = {
        "header": header,
        "payload": payload,
        "issuer_signature_valid": issuer_sig_valid,
        "revealed_claims": {d.name: d.value for d in matched},
        "unmatched_disclosures": [
            {"name": d.name, "digest": d.digest, "reason": "digest not in signed _sd array"}
            for d in unmatched_disclosures
        ],
        "hidden_claim_count": len(hidden_digests),
        "kb_jwt": None,
    }

    if kb_jwt is not None:
        kb_header, kb_payload, kb_signature, kb_signing_input = decode_jwt_parts(kb_jwt)
        kb_report: dict = {"header": kb_header, "payload": kb_payload}

        cnf_jwk = payload.get("cnf", {}).get("jwk")
        if cnf_jwk is not None:
            from issuer.crypto import es256_verify

            holder_public_key = jwk_to_public_key(cnf_jwk)
            kb_report["signature_valid"] = es256_verify(holder_public_key, kb_signing_input, kb_signature)
        else:
            kb_report["signature_valid"] = None

        expected_sd_hash = sha256_b64url(_sd_hash_input(issuer_jwt, matched).encode("ascii"))
        kb_report["sd_hash_matches"] = kb_payload.get("sd_hash") == expected_sd_hash

        if expected_nonce is not None:
            kb_report["nonce_matches"] = kb_payload.get("nonce") == expected_nonce
        if expected_aud is not None:
            kb_report["aud_matches"] = kb_payload.get("aud") == expected_aud

        report["kb_jwt"] = kb_report

    return report


def pretty_print(report: dict) -> str:
    lines: list[str] = []
    lines.append("=== issuer JWT ===")
    lines.append(f"header:  {json.dumps(report['header'])}")
    payload_wo_sd = {k: v for k, v in report["payload"].items() if k != "_sd"}
    lines.append(f"payload (always-visible + protocol claims): {json.dumps(payload_wo_sd)}")
    lines.append(f"_sd digests (count={len(report['payload'].get('_sd', []))}): {report['payload'].get('_sd', [])}")
    lines.append(f"issuer signature valid: {report['issuer_signature_valid']}")
    lines.append("")
    lines.append("=== disclosures presented ===")
    if report["revealed_claims"]:
        for name, value in report["revealed_claims"].items():
            lines.append(f"  REVEALED  {name} = {value!r}")
    else:
        lines.append("  (none revealed)")
    for u in report["unmatched_disclosures"]:
        lines.append(f"  REJECTED  {u['name']}: {u['reason']}")
    lines.append(f"hidden claims (digest only, no disclosure presented): {report['hidden_claim_count']}")
    if report["kb_jwt"] is not None:
        kb = report["kb_jwt"]
        lines.append("")
        lines.append("=== key binding JWT ===")
        lines.append(f"header:  {json.dumps(kb['header'])}")
        lines.append(f"payload: {json.dumps(kb['payload'])}")
        lines.append(f"holder signature valid: {kb['signature_valid']}")
        lines.append(f"sd_hash matches presented disclosures: {kb['sd_hash_matches']}")
        if "nonce_matches" in kb:
            lines.append(f"nonce matches expected: {kb['nonce_matches']}")
        if "aud_matches" in kb:
            lines.append(f"aud matches expected: {kb['aud_matches']}")
    else:
        lines.append("")
        lines.append("(no KB-JWT present — this is an issued credential, not a presentation)")
    return "\n".join(lines)
