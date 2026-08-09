"""
Phase 5's trust-anchor swap: run the exact same corpus through the exact
same verifier, twice — once under the EU trust anchor, once under a UK
DIATF-style one — and diff the outcomes. `verifier/verify.py` needs zero
changes (confirmed: check 3 only ever calls
`config.trust_provider.resolve(issuer_id)` through the frozen Protocol),
and neither does `eval/species.py`/`eval/corpus.py` — `CorpusItem` and
`VerifierConfig` are both `@dataclass(frozen=True)`, so
`dataclasses.replace()` produces a new item with a swapped trust provider
without touching either module.

Honest finding, not a workaround: because both providers register the same
issuer at the same functional tier/LoA, nothing in the 13-species corpus
actually diverges except `trust.anchor_id` — every `decision` is identical
between the two runs. That's the accurate result, not a null one: for an
issuer both frameworks recognize, the two postures are operationally
indistinguishable to the verifier. `build_eu_only_issuer_scenario` is the
one deliberately constructed case where an anchor-dependent decision
actually happens — see its docstring.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from contracts.trust_anchor import TrustAnchorProvider
from contracts.wallet_unlock import AlwaysYesWalletUnlockProvider
from eval.corpus import DEFAULT_NOW, DEFAULT_SEED, build_corpus
from eval.harness import ScoredItem, run_harness
from eval.species import CorpusItem, World, build_world, good_config
from issuer import sdjwt
from issuer.crypto import KeyPair
from issuer.pid import VCT
from verifier.uk_providers import DiatfAnchorProvider
from verifier.verify import VerifierConfig, verify
from wallet.request import AuthorizationRequest, DcqlLiteQuery
from wallet.wallet import CredentialOffer, Wallet, WalletCannotSatisfyRequest, verify_key_proof

EU_ANCHOR_ID = "eu-lab-anchor-1"
UK_ANCHOR_ID = "uk-diatf-anchor-1"

# These two species deliberately construct their own non-default trust
# provider (an empty trust list / a degraded-LoA registration) to express
# their defect — overwriting it with a different anchor's provider would
# silently change what they test, not demonstrate an anchor swap. Every
# other species uses good_config(world)'s plain trust_provider unmodified,
# so swapping it there is a faithful "same corpus, different anchor"
# comparison.
TRUST_PROVIDER_SWAP_EXCLUDED_SPECIES = {"issuer_not_on_trusted_list", "loa_below_requirement"}


def with_trust_provider(item: CorpusItem, trust_provider: TrustAnchorProvider) -> CorpusItem:
    if item.species in TRUST_PROVIDER_SWAP_EXCLUDED_SPECIES:
        return item
    new_config = dataclasses.replace(item.verifier_config, trust_provider=trust_provider)
    return dataclasses.replace(item, verifier_config=new_config)


def build_eu_trust_provider(world: World) -> TrustAnchorProvider:
    from contracts.trust_anchor import LocalDictTrustAnchorProvider

    provider = LocalDictTrustAnchorProvider()
    provider.register(world.issuer_id, world.issuer_kp.public_key, tier="PID", loa="high", anchor_id=EU_ANCHOR_ID)
    return provider


def build_uk_trust_provider(world: World) -> DiatfAnchorProvider:
    provider = DiatfAnchorProvider()
    provider.register(world.issuer_id, world.issuer_kp.public_key, tier="PID", loa="high", anchor_id=UK_ANCHOR_ID)
    return provider


def build_both_corpora(
    seed: int = DEFAULT_SEED, now: int = DEFAULT_NOW, world: World | None = None
) -> tuple[list[CorpusItem], list[CorpusItem]]:
    """Same World, same credentials, same corpus, built once — then two
    trust-provider-swapped views of it."""
    world = world or build_world()
    corpus = build_corpus(seed, now, world)

    eu_provider = build_eu_trust_provider(world)
    uk_provider = build_uk_trust_provider(world)

    eu_items = [with_trust_provider(item, eu_provider) for item in corpus.items]
    uk_items = [with_trust_provider(item, uk_provider) for item in corpus.items]
    return eu_items, uk_items


def run_both_corpora(
    seed: int = DEFAULT_SEED, now: int = DEFAULT_NOW, world: World | None = None
) -> tuple[list[ScoredItem], list[ScoredItem]]:
    """Convenience: build_both_corpora + run_harness on each side, since
    every caller (tests, the demo) needs both scored before diffing."""
    eu_items, uk_items = build_both_corpora(seed, now, world)
    return run_harness(eu_items, now), run_harness(uk_items, now)


@dataclass(frozen=True)
class OutcomeDiff:
    item_id: str
    species: str
    eu_decision: str
    uk_decision: str
    eu_anchor_id: str | None
    uk_anchor_id: str | None
    decisions_match: bool


def diff_outcomes(eu_scored: list[ScoredItem], uk_scored: list[ScoredItem]) -> list[OutcomeDiff]:
    """Pair by item_id (identical across both — same corpus, same order,
    only the trust provider differs) and report where decision/anchor_id
    diverge."""
    uk_by_id = {item.item_id: item for item in uk_scored}
    diffs = []
    for eu_item in eu_scored:
        uk_item = uk_by_id[eu_item.item_id]
        diffs.append(
            OutcomeDiff(
                item_id=eu_item.item_id,
                species=eu_item.species,
                eu_decision=eu_item.actual_decision,
                uk_decision=uk_item.actual_decision,
                eu_anchor_id=eu_item.result["trust"]["anchor_id"],
                uk_anchor_id=uk_item.result["trust"]["anchor_id"],
                decisions_match=eu_item.actual_decision == uk_item.actual_decision,
            )
        )
    return diffs


@dataclass(frozen=True)
class EuOnlyIssuerScenario:
    eu_result: dict
    uk_result: dict


def build_eu_only_issuer_scenario(world: World | None = None, now: int = DEFAULT_NOW) -> EuOnlyIssuerScenario:
    """The real demonstrated divergence: a second issuer, registered in the
    EU provider but absent from UK-DIATF (modeling a PID provider
    accredited under eIDAS with no DVS certification). The *same*
    presentation from this issuer, verified under each config: EU accepts
    (trust_path passes); UK-DIATF rejects at trust_path (issuer not on
    this list). This is the interesting divergence the mutual-recognition
    corpus above doesn't show — see this module's docstring."""
    world = world or build_world()

    second_issuer_id = "https://pid-issuer.eu-only.example"
    second_issuer_kp = KeyPair.from_seed(9500)
    holder_kp = KeyPair.from_seed(9501)

    wallet = Wallet(
        unlock_provider=AlwaysYesWalletUnlockProvider(),
        holder_keypair=holder_kp,
    )
    offer = CredentialOffer(issuer_id=second_issuer_id, vct=VCT, offer_nonce="eu-only-offer-nonce")
    proof = wallet.generate_key_proof(offer, issued_at=now)
    proof_valid, holder_jwk = verify_key_proof(proof, expected_issuer_id=second_issuer_id, expected_nonce=offer.offer_nonce)
    assert proof_valid

    credential = sdjwt.issue(
        issuer_id=second_issuer_id,
        issuer_private_key=second_issuer_kp.private_key,
        holder_public_jwk=holder_jwk,
        always_visible_claims=world.always_visible_claims,
        disclosable_claims=world.disclosable_claims,
        issued_at=now,
        expires_at=now + 3600 * 24 * 365,
        salt_seed=9502,
    )
    wallet.receive_credential(credential, vct=offer.vct)

    request = AuthorizationRequest(
        verifier_id=world.verifier_id,
        nonce="eu-only-verifier-nonce",
        query=DcqlLiteQuery(vct=VCT, required_claims=("age_over_18", "nationality"), required_tier="PID", required_loa="high"),
    )
    presentation = wallet.handle_presentation_request(request, kb_issued_at=now)

    base_config = good_config(world)

    eu_trust = build_eu_trust_provider(world)
    eu_trust.register(second_issuer_id, second_issuer_kp.public_key, tier="PID", loa="high", anchor_id=EU_ANCHOR_ID)
    eu_config = VerifierConfig(
        trust_provider=eu_trust,
        issuer_key_directory=base_config.issuer_key_directory,
        registration_provider=base_config.registration_provider,
        status_provider=base_config.status_provider,
    )
    # the second issuer's key must also be resolvable (a separate question
    # from trust) so its signature can be checked in the first place —
    # register it in both configs' key directories.
    eu_config.issuer_key_directory.publish(second_issuer_id, second_issuer_kp.public_key)
    eu_result = verify(presentation, request=request, config=eu_config, now=now, presentation_id="eu-only-eu-run")

    uk_trust = build_uk_trust_provider(world)  # deliberately NOT registering second_issuer_id
    uk_config = VerifierConfig(
        trust_provider=uk_trust,
        issuer_key_directory=base_config.issuer_key_directory,
        registration_provider=base_config.registration_provider,
        status_provider=base_config.status_provider,
    )
    uk_result = verify(presentation, request=request, config=uk_config, now=now, presentation_id="eu-only-uk-run")

    return EuOnlyIssuerScenario(eu_result=eu_result, uk_result=uk_result)
