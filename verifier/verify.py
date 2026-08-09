"""
The verifier: the eight ordered checks (ATLAS_EUDI.md §9) -> VerificationResult.

Checks 1-6 are hard gates: format, issuer_signature, trust_path, revocation,
disclosure_integrity, key_binding. The first one to fail short-circuits
every later check to `skip` — there is no scenario where, say, a broken
issuer signature is followed by a meaningful registration_purpose result, so
the record shows the one fatal reason instead of a cascade of consequential
noise. Checks 7-8 (registration_purpose, policy) are the RP's own rules;
both always run once 1-6 all pass, independently of each other, because
either can fail without implying anything about the other.

That 1-6 vs 7-8 split is the seam Phase 3's AI red-team pulls on (CLAUDE.md
"flagship experiment") — checks 1-6 cannot be argued with, checks 7-8 can.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from contracts.trust_anchor import TrustAnchorProvider, TrustResolution
from issuer.crypto import decode_jwt_parts, es256_verify, jwk_to_public_key, sha256_b64url
from issuer.sdjwt import Disclosure, split_compact
from verifier.policy import POLICY_VERSION, evaluate_policy
from verifier.providers import IssuerKeyDirectory, RegistrationProvider, StatusListProvider
from wallet.request import AuthorizationRequest

CHECK_NAMES = (
    "format",
    "issuer_signature",
    "trust_path",
    "revocation",
    "disclosure_integrity",
    "key_binding",
    "registration_purpose",
    "policy",
)


@dataclass(frozen=True)
class VerifierConfig:
    trust_provider: TrustAnchorProvider
    issuer_key_directory: IssuerKeyDirectory
    registration_provider: RegistrationProvider
    status_provider: StatusListProvider | None = None
    policy_version: str = POLICY_VERSION


class _CheckRecorder:
    """Accumulates `{name, result, detail}` entries and tracks whether a
    hard-gate check has already failed, so remaining hard gates record as
    `skip` instead of running (or being silently omitted)."""

    def __init__(self) -> None:
        self.checks: list[dict] = []
        self.hard_gate_failed = False

    def record(self, name: str, result: str, detail: str | None) -> None:
        self.checks.append({"name": name, "result": result, "detail": detail})
        if name in _HARD_GATE_NAMES and result == "fail":
            self.hard_gate_failed = True

    def skip_remaining_hard_gates(self, from_index: int) -> None:
        for name in _HARD_GATE_NAMES[from_index:]:
            self.checks.append({"name": name, "result": "skip", "detail": "skipped after an earlier hard-gate failure"})

    def skip(self, name: str, detail: str) -> None:
        self.checks.append({"name": name, "result": "skip", "detail": detail})

    def decision(self) -> str:
        return "reject" if any(c["result"] == "fail" for c in self.checks) else "accept"


_HARD_GATE_NAMES = ("format", "issuer_signature", "trust_path", "revocation", "disclosure_integrity", "key_binding")


def _bail_if_hard_gate_failed(
    recorder: _CheckRecorder,
    *,
    next_hard_gate_index: int,
    presentation_id: str,
    trust: dict,
    policy_version: str,
    start: float,
) -> dict | None:
    """After a hard-gate check runs, either return None (keep going) or a
    finished `VerificationResult` with every remaining check — hard gates
    still to come, plus the always-skipped 7/8 — recorded as `skip`."""
    if not recorder.hard_gate_failed:
        return None
    recorder.skip_remaining_hard_gates(from_index=next_hard_gate_index)
    recorder.skip("registration_purpose", "skipped after an earlier hard-gate failure")
    recorder.skip("policy", "skipped after an earlier hard-gate failure")
    return _finalize(presentation_id, recorder, trust, policy_version, start)


def verify(
    presentation: str,
    *,
    request: AuthorizationRequest,
    config: VerifierConfig,
    now: int,
    presentation_id: str | None = None,
) -> dict:
    """Run the eight ordered checks against a presentation and return a
    `VerificationResult` dict (schema `wallet-1.0`)."""
    start = time.perf_counter()
    presentation_id = presentation_id or f"pres-{uuid.uuid4().hex[:12]}"
    recorder = _CheckRecorder()
    trust: dict = {"tier": None, "anchor_id": None, "loa": None}

    # -- check 1: format --------------------------------------------------
    try:
        issuer_jwt, disclosure_b64s, kb_jwt = split_compact(presentation)
        header, payload, signature, signing_input = decode_jwt_parts(issuer_jwt)
        disclosures = [Disclosure.parse(b) for b in disclosure_b64s]
        kb_header = kb_payload = kb_signature = kb_signing_input = None
        if kb_jwt is not None:
            kb_header, kb_payload, kb_signature, kb_signing_input = decode_jwt_parts(kb_jwt)
    except Exception as exc:
        recorder.record("format", "fail", f"malformed presentation: {exc}")
        return _bail_if_hard_gate_failed(
            recorder, next_hard_gate_index=1, presentation_id=presentation_id,
            trust=trust, policy_version=config.policy_version, start=start,
        )
    recorder.record("format", "pass", None)

    # -- check 2: issuer_signature -----------------------------------------
    issuer_id = payload.get("iss")
    issuer_public_key = config.issuer_key_directory.public_key(issuer_id) if issuer_id else None
    if issuer_public_key is None:
        recorder.record("issuer_signature", "fail", f"no signature-verification key available for issuer {issuer_id!r}")
    elif not es256_verify(issuer_public_key, signing_input, signature):
        recorder.record("issuer_signature", "fail", "issuer JWT signature does not verify")
    else:
        recorder.record("issuer_signature", "pass", None)

    bailed = _bail_if_hard_gate_failed(
        recorder, next_hard_gate_index=2, presentation_id=presentation_id,
        trust=trust, policy_version=config.policy_version, start=start,
    )
    if bailed is not None:
        return bailed

    # -- check 3: trust_path -------------------------------------------------
    resolution: TrustResolution | None = config.trust_provider.resolve(issuer_id)
    if resolution is None:
        recorder.record("trust_path", "fail", f"issuer {issuer_id!r} is not on any trusted list")
    else:
        trust = {"tier": resolution.tier, "anchor_id": resolution.anchor_id, "loa": resolution.loa}
        recorder.record("trust_path", "pass", f"anchor={resolution.anchor_id}, tier={resolution.tier}")

    bailed = _bail_if_hard_gate_failed(
        recorder, next_hard_gate_index=3, presentation_id=presentation_id,
        trust=trust, policy_version=config.policy_version, start=start,
    )
    if bailed is not None:
        return bailed

    # -- check 4: revocation -------------------------------------------------
    if config.status_provider is None:
        recorder.skip("revocation", "no status list configured")
    elif config.status_provider.is_revoked(issuer_jwt):
        recorder.record("revocation", "fail", "credential is on the revoked set")
    else:
        recorder.record("revocation", "pass", None)

    bailed = _bail_if_hard_gate_failed(
        recorder, next_hard_gate_index=4, presentation_id=presentation_id,
        trust=trust, policy_version=config.policy_version, start=start,
    )
    if bailed is not None:
        return bailed

    # -- check 5: disclosure_integrity --------------------------------------
    signed_digests = set(payload.get("_sd", []))
    unmatched = [d for d in disclosures if d.digest not in signed_digests]
    revealed_claims = {d.name: d.value for d in disclosures if d.digest in signed_digests}
    if unmatched:
        recorder.record(
            "disclosure_integrity",
            "fail",
            f"disclosure(s) do not match signed digests: {[d.name for d in unmatched]}",
        )
    else:
        recorder.record("disclosure_integrity", "pass", None)

    bailed = _bail_if_hard_gate_failed(
        recorder, next_hard_gate_index=5, presentation_id=presentation_id,
        trust=trust, policy_version=config.policy_version, start=start,
    )
    if bailed is not None:
        return bailed

    # -- check 6: key_binding ------------------------------------------------
    kb_failures: list[str] = []
    if kb_jwt is None:
        kb_failures.append("no KB-JWT present")
    else:
        cnf_jwk = payload.get("cnf", {}).get("jwk")
        if cnf_jwk is None:
            kb_failures.append("credential carries no cnf holder key")
        else:
            holder_public_key = jwk_to_public_key(cnf_jwk)
            if not es256_verify(holder_public_key, kb_signing_input, kb_signature):
                kb_failures.append("KB-JWT signature does not verify against holder key")
            # sd_hash is defined (issuer.sdjwt.present) as sha256 over
            # issuer-jwt~disclosure~..~ for exactly the disclosures presented.
            sd_hash_input = "~".join([issuer_jwt] + [d.b64 for d in disclosures]) + "~"
            expected_sd_hash = sha256_b64url(sd_hash_input.encode("ascii"))
            if kb_payload.get("sd_hash") != expected_sd_hash:
                kb_failures.append("sd_hash does not match the presented disclosure set")
            if kb_payload.get("nonce") != request.nonce:
                kb_failures.append("nonce does not match the one this verifier issued")
            if kb_payload.get("aud") != request.verifier_id:
                kb_failures.append("aud does not match this verifier")

    if kb_failures:
        recorder.record("key_binding", "fail", "; ".join(kb_failures))
    else:
        recorder.record("key_binding", "pass", None)

    bailed = _bail_if_hard_gate_failed(
        recorder, next_hard_gate_index=6, presentation_id=presentation_id,
        trust=trust, policy_version=config.policy_version, start=start,
    )
    if bailed is not None:
        return bailed

    # -- check 7: registration_purpose ---------------------------------------
    cert = config.registration_provider.resolve(request.verifier_id)
    requested_and_revealed = set(request.query.required_claims) | set(revealed_claims)
    if cert is None:
        recorder.record("registration_purpose", "fail", f"verifier {request.verifier_id!r} has no registration on file")
    else:
        over_asked = requested_and_revealed - cert.allowed_claims
        if over_asked:
            recorder.record(
                "registration_purpose",
                "fail",
                f"claims outside {request.verifier_id!r}'s registration ({cert.purpose!r}): {sorted(over_asked)}",
            )
        else:
            recorder.record("registration_purpose", "pass", None)

    # -- check 8: policy ------------------------------------------------------
    violations = evaluate_policy(
        revealed_claims=revealed_claims,
        exp=payload.get("exp", 0),
        now=now,
        actual_loa=trust["loa"],
        required_loa=request.query.required_loa,
    )
    if violations:
        recorder.record("policy", "fail", "; ".join(v.reason for v in violations))
    else:
        recorder.record("policy", "pass", None)

    return _finalize(presentation_id, recorder, trust, config.policy_version, start)


def _finalize(
    presentation_id: str,
    recorder: _CheckRecorder,
    trust: dict,
    policy_version: str,
    start: float,
) -> dict:
    total_ms = (time.perf_counter() - start) * 1000
    return {
        "schema_version": "wallet-1.0",
        "presentation_id": presentation_id,
        "decision": recorder.decision(),
        "checks": recorder.checks,
        "trust": trust,
        "policy_version": policy_version,
        "qes": None,
        "timing": {"total_ms": total_ms},
    }
