"""
AI red-team harness: the flagship experiment (CLAUDE.md, BUILD_PROMPT_PHASE3.md
"The AI red-team"). An agent playing a malicious holder — it has a valid
credential and holder key, and knows the verifier's *stated* checks
(ATLAS_EUDI.md §9's eight names and what each is supposed to catch), not its
source — tries to craft a presentation the verifier accepts but should
reject. Every attempt is scored against the real Phase 2 verifier and logged
with its `VerificationResult`, so "the agent got in" is never a claim, only
a verifiable fact.

Transport is pluggable (`RedTeamAgent` Protocol) so the harness can run
against a free local/heuristic agent during development and a real
Claude-backed agent for the publishable numbers, without changing anything
else (BUILD_PROMPT_PHASE3.md "develop on a local/cheap model, produce
publishable numbers on the Claude CLI/API" — the `vlm_mode` convention from
the bio-authn sibling project). `HeuristicRedTeamAgent` below is the
zero-cost development-mode agent: no network calls, no tokens, a fixed set
of hand-authored attack strategies chosen to probe exactly the checks
CLAUDE.md predicts will and won't hold.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Protocol

from contracts.wallet_unlock import AlwaysYesWalletUnlockProvider
from eval.species import World, good_config
from issuer import sdjwt, tamper
from issuer.crypto import KeyPair
from issuer.pid import SAMPLE_SUBJECT, VCT, build_pid_claims
from verifier.verify import VerifierConfig, verify
from wallet.request import AuthorizationRequest, DcqlLiteQuery
from wallet.wallet import CredentialOffer, Wallet, verify_key_proof

CHECK_FAMILY = {
    "format": "crypto",
    "issuer_signature": "crypto",
    "trust_path": "crypto",
    "revocation": "crypto",
    "disclosure_integrity": "crypto",
    "key_binding": "crypto",
    "registration_purpose": "policy",
    "policy": "policy",
}


@dataclass(frozen=True)
class RedTeamWorld:
    """What the agent is given: a legitimate credential + holder key it
    controls, and the exact request a real verifier issued against it. The
    agent may craft *any* presentation string in response — it is not
    restricted to `issuer.sdjwt.present` — but it never sees `verifier/`'s
    source, only ATLAS §9's check names and what each is documented to do."""

    world: World
    config: VerifierConfig
    request: AuthorizationRequest
    credential: object  # issuer.sdjwt.Credential
    holder_keypair: KeyPair
    now: int
    stated_checks: dict[str, str]  # check name -> one-line public description


@dataclass(frozen=True)
class RedTeamAttempt:
    attempt_id: str
    targeted_check_family: str  # "crypto" | "policy" — the agent's own framing
    targeted_check: str  # the specific check name it's aiming at
    strategy: str  # short human-readable description of the attack
    presentation: str
    result: dict  # VerificationResult
    accepted: bool
    tokens_in: int | None
    tokens_out: int | None
    cost_usd: float | None
    agent_notes: str


class RedTeamAgent(Protocol):
    def name(self) -> str: ...

    def attempt(self, rt_world: RedTeamWorld, attempt_number: int, history: list[RedTeamAttempt]) -> RedTeamAttempt:
        """Craft and submit one attempt, returning the scored result. The
        agent is responsible for calling `verify(...)` itself (or via a
        helper) so `RedTeamAttempt.result` always reflects a real run."""
        ...


STATED_CHECKS = {
    "format": "presentation must be well-formed SD-JWT VC + KB-JWT",
    "issuer_signature": "the issuer's signature over the credential must verify",
    "trust_path": "the issuer must resolve on this verifier's trusted list",
    "revocation": "the credential must not be on the revoked set",
    "disclosure_integrity": "every presented disclosure must hash to a signed digest",
    "key_binding": "the KB-JWT must verify against the credential's holder key, over this verifier's own nonce and audience",
    "registration_purpose": "requested/disclosed claims must be within this verifier's registration",
    "policy": "not expired, LoA meets the journey requirement, disclosed claims must be internally consistent",
}


def build_redteam_world(world: World | None = None, now: int | None = None) -> RedTeamWorld:
    from eval.species import build_world as _build_world

    world = world or _build_world()
    now = now if now is not None else 1_785_600_000
    holder_kp = KeyPair.generate()
    wallet = Wallet(unlock_provider=AlwaysYesWalletUnlockProvider(), holder_keypair=holder_kp)

    offer = CredentialOffer(issuer_id=world.issuer_id, vct=VCT, offer_nonce="redteam-offer-nonce")
    proof = wallet.generate_key_proof(offer, issued_at=now)
    valid, holder_jwk = verify_key_proof(proof, expected_issuer_id=world.issuer_id, expected_nonce=offer.offer_nonce)
    assert valid

    credential = sdjwt.issue(
        issuer_id=world.issuer_id,
        issuer_private_key=world.issuer_kp.private_key,
        holder_public_jwk=holder_jwk,
        always_visible_claims=world.always_visible_claims,
        disclosable_claims=world.disclosable_claims,
        issued_at=now,
        expires_at=now + 3600 * 24 * 365,
        salt_seed=99_001,
    )
    wallet.receive_credential(credential, vct=offer.vct)

    request = AuthorizationRequest(
        verifier_id=world.verifier_id,
        nonce="redteam-verifier-nonce",
        query=DcqlLiteQuery(vct=VCT, required_claims=("age_over_18",), required_tier="PID", required_loa="high"),
    )
    config = good_config(world)

    return RedTeamWorld(
        world=world,
        config=config,
        request=request,
        credential=credential,
        holder_keypair=holder_kp,
        now=now,
        stated_checks=STATED_CHECKS,
    )


def _submit(rt_world: RedTeamWorld, presentation: str, attempt_id: str) -> dict:
    return verify(presentation, request=rt_world.request, config=rt_world.config, now=rt_world.now, presentation_id=attempt_id)


class HeuristicRedTeamAgent:
    """Zero-cost, zero-network development-mode agent (no LLM). Runs a fixed
    set of hand-authored strategies chosen to probe both sides of the
    asymmetry CLAUDE.md predicts: forging/replaying past checks 2-6 (expected
    to always fail), and exploiting the policy layer's actual blind spots
    (checks 7-8 — expected to sometimes succeed)."""

    def name(self) -> str:
        return "heuristic-v1 (local, no LLM, $0)"

    def attempt(self, rt_world: RedTeamWorld, attempt_number: int, history: list[RedTeamAttempt]) -> RedTeamAttempt:
        strategy_fn = self._strategies()[(attempt_number - 1) % len(self._strategies())]
        return strategy_fn(rt_world, attempt_number)

    def _strategies(self):
        return [
            self._attack_forged_disclosure,
            self._attack_replayed_kb_jwt,
            self._attack_over_ask_by_disclosure,
            self._attack_withhold_birthdate,
        ]

    # -- attacks targeting checks 2-6 (crypto/protocol) — expected to fail --

    def _attack_forged_disclosure(self, rt_world: RedTeamWorld, n: int) -> RedTeamAttempt:
        """Take a legitimately-presented credential and alter a disclosed
        claim's value in place — the textbook forgery attempt. No private
        key to re-sign with, so this can only ever break the digest."""
        presentation = sdjwt.present(
            rt_world.credential,
            reveal={"age_over_18"},
            holder_private_key=rt_world.holder_keypair.private_key,
            nonce=rt_world.request.nonce,
            aud=rt_world.request.verifier_id,
            kb_issued_at=rt_world.now,
        )
        variant = tamper.altered_disclosed_claim(presentation, "age_over_18", False)
        result = _submit(rt_world, variant.credential, f"redteam-{n:03d}-forged-disclosure")
        return RedTeamAttempt(
            attempt_id=f"redteam-{n:03d}-forged-disclosure",
            targeted_check_family="crypto",
            targeted_check="disclosure_integrity",
            strategy="alter a disclosed claim's value without the issuer's private key",
            presentation=variant.credential,
            result=result,
            accepted=result["decision"] == "accept",
            tokens_in=None,
            tokens_out=None,
            cost_usd=0.0,
            agent_notes="no private key available to re-sign; expect the digest mismatch to be caught",
        )

    def _attack_replayed_kb_jwt(self, rt_world: RedTeamWorld, n: int) -> RedTeamAttempt:
        """Present a KB-JWT signed for a *different* nonce (simulating a
        captured presentation replayed against a fresh challenge)."""
        presentation = sdjwt.present(
            rt_world.credential,
            reveal={"age_over_18"},
            holder_private_key=rt_world.holder_keypair.private_key,
            nonce="a-previously-issued-nonce-now-stale",
            aud=rt_world.request.verifier_id,
            kb_issued_at=rt_world.now,
        )
        result = _submit(rt_world, presentation, f"redteam-{n:03d}-replayed-kb-jwt")
        return RedTeamAttempt(
            attempt_id=f"redteam-{n:03d}-replayed-kb-jwt",
            targeted_check_family="crypto",
            targeted_check="key_binding",
            strategy="replay a KB-JWT signed over a stale nonce instead of the verifier's fresh one",
            presentation=presentation,
            result=result,
            accepted=result["decision"] == "accept",
            tokens_in=None,
            tokens_out=None,
            cost_usd=0.0,
            agent_notes="hoping nonce freshness isn't actually enforced",
        )

    # -- attacks targeting checks 7-8 (policy) — where holes are expected --

    def _attack_over_ask_by_disclosure(self, rt_world: RedTeamWorld, n: int) -> RedTeamAttempt:
        """The request only asked for age_over_18 — volunteer family_name
        too, a claim outside this verifier's registration (which only covers
        age_over_18/nationality/given_name), hoping registration_purpose
        only checks what was asked for in the query, not what actually came
        back in the disclosures."""
        presentation = sdjwt.present(
            rt_world.credential,
            reveal={"age_over_18", "family_name"},
            holder_private_key=rt_world.holder_keypair.private_key,
            nonce=rt_world.request.nonce,
            aud=rt_world.request.verifier_id,
            kb_issued_at=rt_world.now,
        )
        result = _submit(rt_world, presentation, f"redteam-{n:03d}-over-ask-by-disclosure")
        return RedTeamAttempt(
            attempt_id=f"redteam-{n:03d}-over-ask-by-disclosure",
            targeted_check_family="policy",
            targeted_check="registration_purpose",
            strategy="volunteer family_name — outside registration and unrequested — hoping only the DCQL query, not the actual disclosure, is checked",
            presentation=presentation,
            result=result,
            accepted=result["decision"] == "accept",
            tokens_in=None,
            tokens_out=None,
            cost_usd=0.0,
            agent_notes="registration_purpose checks requested UNION revealed claims, so this is expected to fail — included to confirm that in numbers, not just by reading the code",
        )

    def _attack_withhold_birthdate(self, rt_world: RedTeamWorld, n: int) -> RedTeamAttempt:
        """The real find: issue a credential where age_over_18 is set to
        True for a subject who is actually a minor, then disclose ONLY
        age_over_18 — never birth_date. The policy check's consistency rule
        (verifier/policy.py) only fires when *both* claims are disclosed
        together; withholding birth_date isn't a crypto defect (selective
        disclosure is the credential's whole design), so nothing upstream of
        `policy` has any reason to object."""
        minor_subject = dict(SAMPLE_SUBJECT)
        minor_subject["birth_date"] = "2015-01-01"  # actually under 18 as of now
        always_visible, disclosable = build_pid_claims(minor_subject, expiry_date_iso="2035-03-11")
        disclosable["age_over_18"] = True  # the lie: claims adult, subject is a minor

        holder_kp = KeyPair.generate()
        wallet = Wallet(unlock_provider=AlwaysYesWalletUnlockProvider(), holder_keypair=holder_kp)
        offer = CredentialOffer(issuer_id=rt_world.world.issuer_id, vct=VCT, offer_nonce=f"redteam-offer-nonce-{n}")
        proof = wallet.generate_key_proof(offer, issued_at=rt_world.now)
        _, holder_jwk = verify_key_proof(proof, expected_issuer_id=rt_world.world.issuer_id, expected_nonce=offer.offer_nonce)
        credential = sdjwt.issue(
            issuer_id=rt_world.world.issuer_id,
            issuer_private_key=rt_world.world.issuer_kp.private_key,
            holder_public_jwk=holder_jwk,
            always_visible_claims=always_visible,
            disclosable_claims=disclosable,
            issued_at=rt_world.now,
            expires_at=rt_world.now + 3600 * 24 * 365,
            salt_seed=99_100 + n,
        )
        wallet.receive_credential(credential, vct=offer.vct)

        presentation = sdjwt.present(
            credential,
            reveal={"age_over_18"},  # birth_date deliberately withheld
            holder_private_key=holder_kp.private_key,
            nonce=rt_world.request.nonce,
            aud=rt_world.request.verifier_id,
            kb_issued_at=rt_world.now,
        )
        result = _submit(rt_world, presentation, f"redteam-{n:03d}-withhold-birthdate")
        return RedTeamAttempt(
            attempt_id=f"redteam-{n:03d}-withhold-birthdate",
            targeted_check_family="policy",
            targeted_check="policy",
            strategy="issue age_over_18=True for an actual minor, disclose only age_over_18, never birth_date — the consistency check has nothing to compare against",
            presentation=presentation,
            result=result,
            accepted=result["decision"] == "accept",
            tokens_in=None,
            tokens_out=None,
            cost_usd=0.0,
            agent_notes="selective disclosure is the credential's intended feature, not a bug being exploited — that's what makes this hole structural rather than an implementation slip",
        )


def run_redteam(agent: RedTeamAgent, rt_world: RedTeamWorld, n_attempts: int) -> list[RedTeamAttempt]:
    history: list[RedTeamAttempt] = []
    for i in range(1, n_attempts + 1):
        history.append(agent.attempt(rt_world, i, history))
    return history


def summarize_by_check_family(attempts: list[RedTeamAttempt]) -> dict:
    families: dict[str, dict] = {"crypto": {"n": 0, "accepted": 0}, "policy": {"n": 0, "accepted": 0}}
    for a in attempts:
        fam = families.setdefault(a.targeted_check_family, {"n": 0, "accepted": 0})
        fam["n"] += 1
        if a.accepted:
            fam["accepted"] += 1
    for fam in families.values():
        fam["success_rate"] = (fam["accepted"] / fam["n"]) if fam["n"] else None
    return families


def build_redteam_result(agent: RedTeamAgent, attempts: list[RedTeamAttempt], now: int) -> dict:
    total_tokens_in = sum(a.tokens_in for a in attempts if a.tokens_in is not None)
    total_tokens_out = sum(a.tokens_out for a in attempts if a.tokens_out is not None)
    total_cost = sum(a.cost_usd for a in attempts if a.cost_usd is not None)
    return {
        "schema_version": "redteam-1.0",
        "agent": agent.name(),
        "generated_at_epoch": now,
        "n_attempts": len(attempts),
        "attempts": [
            {
                "attempt_id": a.attempt_id,
                "targeted_check_family": a.targeted_check_family,
                "targeted_check": a.targeted_check,
                "strategy": a.strategy,
                "accepted": a.accepted,
                "decision": a.result["decision"],
                "failing_checks": [c["name"] for c in a.result["checks"] if c["result"] == "fail"],
                "tokens_in": a.tokens_in,
                "tokens_out": a.tokens_out,
                "cost_usd": a.cost_usd,
                "agent_notes": a.agent_notes,
            }
            for a in attempts
        ],
        "by_check_family": summarize_by_check_family(attempts),
        "token_accounting": {
            "total_tokens_in": total_tokens_in,
            "total_tokens_out": total_tokens_out,
            "total_cost_usd": total_cost,
        },
    }
