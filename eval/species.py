"""
The thirteen defect-species generators run through the Phase 2 verifier
(twelve from BUILD_PROMPT_PHASE3.md's original label set, plus
`cross_device_origin_phish` added in Phase 3.5), each producing one
`CorpusItem`: a presentation, the request it was made against, the verifier
configuration to check it under, and the expected verdict. `genuine` is the
negative class; every other species carries exactly one defect, mapped to
the one check that should catch it. A fourteenth species,
`stolen_device_presentation`, exists in the taxonomy but is deliberately
*not* here — see `eval/wallet_unlock_species.py`'s module docstring for why.

Six species (crypto/protocol, checks 2-6) reuse `issuer.tamper` byte-for-byte
— Phase 1's tamper harness *is* the corpus's crypto-defect generator, not a
reimplementation of it. The trust-chain and policy species have no Phase 1
equivalent because they aren't wire-level defects — they're
verifier-configuration facts (an unregistered issuer, a revoked credential,
a narrower registration certificate, a lower issuer LoA) applied to an
otherwise perfectly valid presentation. That's why each `CorpusItem` carries
its own `VerifierConfig`, not just a presentation string: the defect for
those species lives in the world the verifier checks against, not in the
bytes on the wire. `cross_device_origin_phish` (Phase 3.5) is neither — it's
the same aud-mismatch mechanism as `wrong_audience_kb_jwt`, reused rather
than reimplemented, because the verifier's `key_binding` check cannot tell a
lab-simulated attacker from a real QR-relay phishing scenario, and shouldn't
have to: the defect is identical, only the narrative that produces it differs.
"""

from __future__ import annotations

from dataclasses import dataclass

from contracts.trust_anchor import LocalDictTrustAnchorProvider
from contracts.wallet_unlock import AlwaysYesWalletUnlockProvider
from issuer import sdjwt, tamper
from issuer.crypto import KeyPair
from issuer.pid import SAMPLE_SUBJECT, VCT, build_pid_claims
from verifier.providers import (
    LocalDictIssuerKeyDirectory,
    LocalDictRegistrationProvider,
    LocalDictStatusListProvider,
)
from verifier.verify import VerifierConfig
from wallet.request import AuthorizationRequest, DcqlLiteQuery
from wallet.wallet import CredentialOffer, Wallet, verify_key_proof

DEFAULT_REQUIRED_CLAIMS = ("age_over_18", "nationality")
DEFAULT_REGISTRATION_CLAIMS = frozenset({"age_over_18", "nationality", "given_name"})

# Every species label this phase can express, in the taxonomy's own grouping
# order (BUILD_PROMPT_PHASE3.md "the defect taxonomy"; `cross_device_origin_phish`
# added in Phase 3.5). `genuine` first.
ALL_SPECIES = (
    "genuine",
    "broken_issuer_signature",
    "altered_disclosed_claim",
    "stripped_kb_jwt",
    "wrong_audience_kb_jwt",
    "stale_nonce_kb_jwt",
    "issuer_not_on_trusted_list",
    "revoked_credential",
    "expired_credential",
    "loa_below_requirement",
    "claim_inconsistency",
    "over_asking",
    "cross_device_origin_phish",
)

# The check each species is expected to be caught at. None only for `genuine`.
EXPECTED_CHECK = {
    "genuine": None,
    "broken_issuer_signature": "issuer_signature",
    "altered_disclosed_claim": "disclosure_integrity",
    "stripped_kb_jwt": "key_binding",
    "wrong_audience_kb_jwt": "key_binding",
    "stale_nonce_kb_jwt": "key_binding",
    "issuer_not_on_trusted_list": "trust_path",
    "revoked_credential": "revocation",
    "expired_credential": "policy",
    "loa_below_requirement": "policy",
    "claim_inconsistency": "policy",
    "over_asking": "registration_purpose",
    "cross_device_origin_phish": "key_binding",
}

# Cryptographic/protocol + trust-chain species — checks 2-6 plus 3-4's second
# half, all deterministic. APCER is expected to be exactly 0 here
# (BUILD_PROMPT_PHASE3.md acceptance criterion 3).
CRYPTO_AND_TRUST_SPECIES = (
    "broken_issuer_signature",
    "altered_disclosed_claim",
    "stripped_kb_jwt",
    "wrong_audience_kb_jwt",
    "stale_nonce_kb_jwt",
    "issuer_not_on_trusted_list",
    "revoked_credential",
    "cross_device_origin_phish",
)

# Policy-layer species — checks 7-8, the RP's own rules. Where the AI
# red-team is expected to find holes (CLAUDE.md "flagship experiment").
POLICY_SPECIES = ("expired_credential", "loa_below_requirement", "claim_inconsistency", "over_asking")


@dataclass(frozen=True)
class CorpusItem:
    item_id: str
    species: str
    presentation: str
    request: AuthorizationRequest
    verifier_config: VerifierConfig
    expected_decision: str  # "accept" | "reject"
    expected_check: str | None
    description: str


@dataclass(frozen=True)
class World:
    """Fixed material every corpus item is built from — one issuer, one PID
    subject, one verifier identity — so that every item differs from a
    common valid baseline by exactly the one thing its species names."""

    issuer_id: str
    issuer_kp: KeyPair
    verifier_id: str
    always_visible_claims: dict
    disclosable_claims: dict


def build_world() -> World:
    issuer_kp = KeyPair.from_seed(1)
    always_visible, disclosable = build_pid_claims(SAMPLE_SUBJECT, expiry_date_iso="2035-03-11")
    return World(
        issuer_id="https://pid-issuer.ie.eidas-lab.example",
        issuer_kp=issuer_kp,
        verifier_id="https://larabank.example/verify",
        always_visible_claims=always_visible,
        disclosable_claims=disclosable,
    )


def good_config(world: World) -> VerifierConfig:
    """A fresh, unmodified verifier configuration: issuer trusted at PID/high,
    key published, registration covering the default claim set, nothing
    revoked. Every species starts from this and changes exactly one thing."""
    trust_provider = LocalDictTrustAnchorProvider()
    trust_provider.register(world.issuer_id, world.issuer_kp.public_key, tier="PID", loa="high", anchor_id="eu-lab-anchor-1")

    key_directory = LocalDictIssuerKeyDirectory()
    key_directory.publish(world.issuer_id, world.issuer_kp.public_key)

    registration_provider = LocalDictRegistrationProvider()
    registration_provider.register(world.verifier_id, allowed_claims=DEFAULT_REGISTRATION_CLAIMS, purpose="account-opening")

    return VerifierConfig(
        trust_provider=trust_provider,
        issuer_key_directory=key_directory,
        registration_provider=registration_provider,
        status_provider=LocalDictStatusListProvider(),
    )


def _baseline(
    world: World,
    index: int,
    now: int,
    *,
    reveal: tuple[str, ...] | None = None,
    required_loa: str | None = "high",
):
    """Issue a fresh PID to a fresh wallet, then present the requested claim
    subset — the valid, untampered starting point every species builds from.
    Deterministic per `index`: same index always produces the same keys,
    nonce, and salts."""
    reveal = reveal or DEFAULT_REQUIRED_CLAIMS
    holder_kp = KeyPair.from_seed(1000 + index)
    wallet = Wallet(unlock_provider=AlwaysYesWalletUnlockProvider(), holder_keypair=holder_kp)

    offer = CredentialOffer(issuer_id=world.issuer_id, vct=VCT, offer_nonce=f"offer-nonce-{index}")
    proof = wallet.generate_key_proof(offer, issued_at=now)
    proof_valid, holder_jwk = verify_key_proof(proof, expected_issuer_id=world.issuer_id, expected_nonce=offer.offer_nonce)
    assert proof_valid, "corpus builder's own key proof failed to verify — should never happen"

    credential = sdjwt.issue(
        issuer_id=world.issuer_id,
        issuer_private_key=world.issuer_kp.private_key,
        holder_public_jwk=holder_jwk,
        always_visible_claims=world.always_visible_claims,
        disclosable_claims=world.disclosable_claims,
        issued_at=now,
        expires_at=now + 3600 * 24 * 365,
        salt_seed=2000 + index,
    )
    wallet.receive_credential(credential, vct=offer.vct)

    request = AuthorizationRequest(
        verifier_id=world.verifier_id,
        nonce=f"verifier-nonce-{index}",
        query=DcqlLiteQuery(vct=VCT, required_claims=reveal, required_tier="PID", required_loa=required_loa),
    )
    presentation = wallet.handle_presentation_request(request, kb_issued_at=now)
    return wallet, credential, presentation, request


def _tamper_ctx(world: World, wallet: Wallet, request: AuthorizationRequest, now: int, reveal: set[str], salt_seed: int) -> tamper.TamperContext:
    return tamper.TamperContext(
        issuer_id=world.issuer_id,
        issuer_private_key=world.issuer_kp.private_key,
        issuer_public_key=world.issuer_kp.public_key,
        holder_private_key=wallet.holder_keypair.private_key,
        holder_public_jwk=wallet.holder_keypair.public_jwk(),
        always_visible_claims=world.always_visible_claims,
        disclosable_claims=world.disclosable_claims,
        salt_seed=salt_seed,
        issued_at=now,
        expires_at=now + 3600 * 24 * 365,
        reveal=reveal,
        nonce=request.nonce,
        aud=request.verifier_id,
        kb_issued_at=now,
    )


def _item(item_id: str, species: str, presentation: str, request: AuthorizationRequest, config: VerifierConfig, description: str) -> CorpusItem:
    expected_decision = "accept" if species == "genuine" else "reject"
    return CorpusItem(
        item_id=item_id,
        species=species,
        presentation=presentation,
        request=request,
        verifier_config=config,
        expected_decision=expected_decision,
        expected_check=EXPECTED_CHECK[species],
        description=description,
    )


# --------------------------------------------------------------------------
# genuine — the negative class
# --------------------------------------------------------------------------

def genuine(world: World, index: int, now: int, reveal: tuple[str, ...] | None = None) -> CorpusItem:
    _, _, presentation, request = _baseline(world, index, now, reveal=reveal)
    config = good_config(world)
    return _item(f"genuine-{index:03d}", "genuine", presentation, request, config, f"unmodified valid presentation, revealing {reveal or DEFAULT_REQUIRED_CLAIMS}")


# --------------------------------------------------------------------------
# Crypto/protocol species — reuse issuer.tamper directly
# --------------------------------------------------------------------------

def broken_issuer_signature(world: World, index: int, now: int) -> CorpusItem:
    _, _, presentation, request = _baseline(world, index, now)
    variant = tamper.broken_issuer_signature(presentation)
    config = good_config(world)
    return _item(f"broken_issuer_signature-{index:03d}", "broken_issuer_signature", variant.credential, request, config, variant.description)


def altered_disclosed_claim(world: World, index: int, now: int) -> CorpusItem:
    _, _, presentation, request = _baseline(world, index, now)
    variant = tamper.altered_disclosed_claim(presentation, "nationality", "XX")
    config = good_config(world)
    return _item(f"altered_disclosed_claim-{index:03d}", "altered_disclosed_claim", variant.credential, request, config, variant.description)


def stripped_kb_jwt(world: World, index: int, now: int) -> CorpusItem:
    _, _, presentation, request = _baseline(world, index, now)
    variant = tamper.stripped_kb_jwt(presentation)
    config = good_config(world)
    return _item(f"stripped_kb_jwt-{index:03d}", "stripped_kb_jwt", variant.credential, request, config, variant.description)


def wrong_audience_kb_jwt(world: World, index: int, now: int) -> CorpusItem:
    wallet, credential, _, request = _baseline(world, index, now)
    ctx = _tamper_ctx(world, wallet, request, now, set(DEFAULT_REQUIRED_CLAIMS), salt_seed=2000 + index)
    variant = tamper.wrong_audience_kb_jwt(ctx, credential, wrong_aud="https://attacker.example")
    config = good_config(world)
    return _item(f"wrong_audience_kb_jwt-{index:03d}", "wrong_audience_kb_jwt", variant.credential, request, config, variant.description)


def stale_nonce_kb_jwt(world: World, index: int, now: int) -> CorpusItem:
    wallet, credential, _, request = _baseline(world, index, now)
    ctx = _tamper_ctx(world, wallet, request, now, set(DEFAULT_REQUIRED_CLAIMS), salt_seed=2000 + index)
    variant = tamper.stale_nonce_kb_jwt(ctx, credential, stale_nonce=f"stale-nonce-from-yesterday-{index}")
    config = good_config(world)
    return _item(f"stale_nonce_kb_jwt-{index:03d}", "stale_nonce_kb_jwt", variant.credential, request, config, variant.description)


def cross_device_origin_phish(world: World, index: int, now: int) -> CorpusItem:
    """The Phase 3.5 cross-device scenario: a relaying attacker sits between
    the verifier's QR and the wallet, so the wallet ends up binding its
    KB-JWT to an audience that isn't the real verifier's own identity. Same
    byte-level defect as `wrong_audience_kb_jwt` (aud mismatch, caught at
    key_binding) — reused rather than reimplemented, because the verifier
    has no way to distinguish "a lab test picked the wrong aud" from "a
    phishing relay substituted its own origin," and it shouldn't need to:
    the check that stops one stops the other."""
    wallet, credential, _, request = _baseline(world, index, now)
    ctx = _tamper_ctx(world, wallet, request, now, set(DEFAULT_REQUIRED_CLAIMS), salt_seed=2000 + index)
    variant = tamper.wrong_audience_kb_jwt(ctx, credential, wrong_aud="https://phishing-relay.example")
    config = good_config(world)
    return _item(
        f"cross_device_origin_phish-{index:03d}",
        "cross_device_origin_phish",
        variant.credential,
        request,
        config,
        "cross-device QR relayed through a phishing origin; KB-JWT aud binds to the phishing site, not the real verifier",
    )


# --------------------------------------------------------------------------
# Trust-chain species — the defect is in the verifier's configuration, not
# the wire bytes: an otherwise perfectly valid presentation, checked against
# a world where the issuer isn't accredited or the credential's been revoked.
# --------------------------------------------------------------------------

def issuer_not_on_trusted_list(world: World, index: int, now: int) -> CorpusItem:
    _, _, presentation, request = _baseline(world, index, now)
    config = good_config(world)
    # swap in an empty trust list — everything else about the config (key
    # directory, registration, status) stays exactly as `good_config` built it
    empty_trust_config = VerifierConfig(
        trust_provider=LocalDictTrustAnchorProvider(),
        issuer_key_directory=config.issuer_key_directory,
        registration_provider=config.registration_provider,
        status_provider=config.status_provider,
    )
    return _item(
        f"issuer_not_on_trusted_list-{index:03d}",
        "issuer_not_on_trusted_list",
        presentation,
        request,
        empty_trust_config,
        "valid presentation from an issuer with no trust-list registration at this verifier",
    )


def revoked_credential(world: World, index: int, now: int) -> CorpusItem:
    _, credential, presentation, request = _baseline(world, index, now)
    config = good_config(world)
    config.status_provider.revoke(credential.issuer_jwt)
    return _item(
        f"revoked_credential-{index:03d}",
        "revoked_credential",
        presentation,
        request,
        config,
        "valid presentation whose credential has since been revoked",
    )


# --------------------------------------------------------------------------
# Policy-layer species — checks 7-8. The RP's own rules, not cryptography.
# --------------------------------------------------------------------------

def expired_credential(world: World, index: int, now: int) -> CorpusItem:
    wallet, credential, _, request = _baseline(world, index, now)
    ctx = _tamper_ctx(world, wallet, request, now, set(DEFAULT_REQUIRED_CLAIMS), salt_seed=2000 + index)
    variant = tamper.expired_credential(ctx, expired_at=now - 3600 * 24)
    config = good_config(world)
    return _item(f"expired_credential-{index:03d}", "expired_credential", variant.credential, request, config, variant.description)


def loa_below_requirement(world: World, index: int, now: int) -> CorpusItem:
    _, _, presentation, request = _baseline(world, index, now, required_loa="high")
    config = good_config(world)
    # re-register the same issuer, same key, but at a lower LoA than the
    # journey requires — the credential and its signature are untouched
    low_loa_trust = LocalDictTrustAnchorProvider()
    low_loa_trust.register(world.issuer_id, world.issuer_kp.public_key, tier="PID", loa="substantial", anchor_id="eu-lab-anchor-1")
    low_loa_config = VerifierConfig(
        trust_provider=low_loa_trust,
        issuer_key_directory=config.issuer_key_directory,
        registration_provider=config.registration_provider,
        status_provider=config.status_provider,
    )
    return _item(
        f"loa_below_requirement-{index:03d}",
        "loa_below_requirement",
        presentation,
        request,
        low_loa_config,
        "issuer resolves at LoA substantial; journey requires LoA high",
    )


def claim_inconsistency(world: World, index: int, now: int) -> CorpusItem:
    """Unlike the others, this defect is baked in at issuance: age_over_18 is
    set to disagree with birth_date from the start, then both are disclosed
    together — the one combination that makes the inconsistency checkable
    (issuer/pid.py's docstring on why this needs both halves revealed)."""
    holder_kp = KeyPair.from_seed(1000 + index)
    wallet = Wallet(unlock_provider=AlwaysYesWalletUnlockProvider(), holder_keypair=holder_kp)

    disclosable = dict(world.disclosable_claims)
    disclosable["age_over_18"] = not disclosable["age_over_18"]

    offer = CredentialOffer(issuer_id=world.issuer_id, vct=VCT, offer_nonce=f"offer-nonce-{index}")
    proof = wallet.generate_key_proof(offer, issued_at=now)
    _, holder_jwk = verify_key_proof(proof, expected_issuer_id=world.issuer_id, expected_nonce=offer.offer_nonce)

    credential = sdjwt.issue(
        issuer_id=world.issuer_id,
        issuer_private_key=world.issuer_kp.private_key,
        holder_public_jwk=holder_jwk,
        always_visible_claims=world.always_visible_claims,
        disclosable_claims=disclosable,
        issued_at=now,
        expires_at=now + 3600 * 24 * 365,
        salt_seed=2000 + index,
    )
    wallet.receive_credential(credential, vct=offer.vct)

    request = AuthorizationRequest(
        verifier_id=world.verifier_id,
        nonce=f"verifier-nonce-{index}",
        query=DcqlLiteQuery(vct=VCT, required_claims=("age_over_18", "birth_date"), required_tier="PID", required_loa="high"),
    )
    presentation = wallet.handle_presentation_request(request, kb_issued_at=now)

    # this species discloses birth_date (needed to make the inconsistency
    # checkable at all) — register it so registration_purpose doesn't also
    # fire and blur which check actually caught the intended defect
    config = good_config(world)
    registration_with_birth_date = LocalDictRegistrationProvider()
    registration_with_birth_date.register(
        world.verifier_id, allowed_claims=DEFAULT_REGISTRATION_CLAIMS | {"birth_date"}, purpose="account-opening"
    )
    config = VerifierConfig(
        trust_provider=config.trust_provider,
        issuer_key_directory=config.issuer_key_directory,
        registration_provider=registration_with_birth_date,
        status_provider=config.status_provider,
    )
    return _item(
        f"claim_inconsistency-{index:03d}",
        "claim_inconsistency",
        presentation,
        request,
        config,
        "age_over_18 deliberately disagrees with the disclosed birth_date",
    )


def over_asking(world: World, index: int, now: int) -> CorpusItem:
    reveal = ("age_over_18", "nationality")
    _, _, presentation, request = _baseline(world, index, now, reveal=reveal)
    config = good_config(world)
    # registration only covers age_over_18 — nationality is disclosed and
    # requested beyond what this verifier is accredited to ask for
    narrow_registration = LocalDictRegistrationProvider()
    narrow_registration.register(world.verifier_id, allowed_claims={"age_over_18"}, purpose="age-check-only")
    narrow_config = VerifierConfig(
        trust_provider=config.trust_provider,
        issuer_key_directory=config.issuer_key_directory,
        registration_provider=narrow_registration,
        status_provider=config.status_provider,
    )
    return _item(
        f"over_asking-{index:03d}",
        "over_asking",
        presentation,
        request,
        narrow_config,
        "nationality requested/disclosed beyond this verifier's registration (age-check-only)",
    )


GENERATORS = {
    "genuine": genuine,
    "broken_issuer_signature": broken_issuer_signature,
    "altered_disclosed_claim": altered_disclosed_claim,
    "stripped_kb_jwt": stripped_kb_jwt,
    "wrong_audience_kb_jwt": wrong_audience_kb_jwt,
    "stale_nonce_kb_jwt": stale_nonce_kb_jwt,
    "issuer_not_on_trusted_list": issuer_not_on_trusted_list,
    "revoked_credential": revoked_credential,
    "expired_credential": expired_credential,
    "loa_below_requirement": loa_below_requirement,
    "claim_inconsistency": claim_inconsistency,
    "over_asking": over_asking,
    "cross_device_origin_phish": cross_device_origin_phish,
}
