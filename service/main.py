"""
Phase 3.5's "thin verifier HTTP endpoint" (BUILD_PROMPT_PHASE3_5.md). A local
FastAPI service wrapping the unchanged Phase 2/3 Python core so a browser
PWA has a real (if simplified) network channel to issue against and present
to. Every credential/verification decision is made by the exact same code
Phases 1-3 already tested — `issuer.sdjwt.issue`, `verifier.verify.verify`,
`wallet.wallet.verify_key_proof` — this module adds only HTTP plumbing
around them, nothing new.

Not deployed anywhere; local dev tool only (CLAUDE.md decision, Phase 3.5).
Run: uvicorn service.main:app --port 8420 --reload
"""

from __future__ import annotations

import time
import uuid
from random import SystemRandom

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from eval.species import GENERATORS, build_world, good_config
from issuer import sdjwt
from service.models import (
    AuthorizationRequestModel,
    CredentialOfferResponse,
    DcqlLiteQueryModel,
    IssueRequest,
    IssueResponse,
    PresentSubmitRequest,
    TamperDemoRequest,
    TamperDemoResponse,
    VerifyRequest,
)
from verifier.verify import verify
from wallet.request import AuthorizationRequest, DcqlLiteQuery
from wallet.wallet import verify_key_proof

_rand = SystemRandom()

# One issuer, one PID subject, one verifier identity — the exact fixture the
# Phase 3 eval corpus already scores against (eval/species.py), reused here
# rather than rebuilt, so this service's accept/reject behaviour is provably
# the same world the corpus and its tests already exercise.
WORLD = build_world()
CONFIG = good_config(WORLD)

DEFAULT_REQUIRED_CLAIMS = ("age_over_18", "nationality")

# Phase 6's /try-it picker: 6 of the corpus's 13 species, curated to those
# whose defect lives entirely in the wire bytes or the request — i.e. they
# verify correctly against this module's single, fixed CONFIG.
#
# Excluded, and verified by hand against this endpoint rather than assumed:
# issuer_not_on_trusted_list, revoked_credential, loa_below_requirement swap
# in a different VerifierConfig entirely (an empty trust list, a
# revoked-credential status entry, a degraded LoA registration). over_asking
# and claim_inconsistency looked config-independent at a glance but aren't —
# both swap in a *registration_provider* with a wider allowed-claims set
# than good_config()'s default (to admit birth_date/nationality without
# tripping registration_purpose) — against this endpoint's fixed CONFIG,
# over_asking silently flips to accept (wrong) and claim_inconsistency fires
# registration_purpose alongside policy (right decision, wrong/extra
# reason). Reproducing any of these five would mean adding new
# verifier-config logic to this endpoint, contradicting Phase 6's "no new
# verifier logic" scope. An honest, empirically-checked scope cut, not a
# silent gap.
TAMPER_DEMO_SPECIES = (
    "genuine",
    "broken_issuer_signature",
    "altered_disclosed_claim",
    "stripped_kb_jwt",
    "expired_credential",
    "cross_device_origin_phish",
)

app = FastAPI(title="eIDAS Lab — Phase 3.5 verifier service")

# Local dev tool only — narrow allow-list, not a wildcard (this is never
# deployed; see CLAUDE.md's Phase 3.5 decisions).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",  # next dev falls back here if 3000 is taken
        "http://127.0.0.1:3001",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# In-memory, process-lifetime state. A local single-process demo tool has no
# need for a real datastore; restarting the service drops all pending offers
# and in-flight cross-device relays, which is fine for this phase.
_offers: dict[str, dict] = {}
_presentations: dict[str, str] = {}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/credential-offer", response_model=CredentialOfferResponse)
def credential_offer() -> CredentialOfferResponse:
    offer_id = uuid.uuid4().hex
    offer_nonce = uuid.uuid4().hex
    _offers[offer_id] = {"issuer_id": WORLD.issuer_id, "vct": sdjwt.VCT, "offer_nonce": offer_nonce}
    return CredentialOfferResponse(offer_id=offer_id, issuer_id=WORLD.issuer_id, vct=sdjwt.VCT, offer_nonce=offer_nonce)


@app.post("/issue", response_model=IssueResponse)
def issue(body: IssueRequest) -> IssueResponse:
    offer = _offers.get(body.offer_id)
    if offer is None:
        raise HTTPException(status_code=400, detail="unknown or expired offer_id")

    proof_valid, holder_jwk = verify_key_proof(
        body.proof_jwt, expected_issuer_id=offer["issuer_id"], expected_nonce=offer["offer_nonce"]
    )
    if not proof_valid or holder_jwk is None:
        raise HTTPException(status_code=400, detail="key proof did not verify")

    now = int(time.time())
    credential = sdjwt.issue(
        issuer_id=WORLD.issuer_id,
        issuer_private_key=WORLD.issuer_kp.private_key,
        holder_public_jwk=holder_jwk,
        always_visible_claims=WORLD.always_visible_claims,
        disclosable_claims=WORLD.disclosable_claims,
        issued_at=now,
        expires_at=now + 3600 * 24 * 365,
        salt_seed=_rand.randrange(1, 10**9),
    )
    del _offers[body.offer_id]  # one-shot: an offer is consumed by exactly one issuance
    return IssueResponse(credential=credential.compact())


@app.post("/authorization-request", response_model=AuthorizationRequestModel)
def authorization_request() -> AuthorizationRequestModel:
    nonce = uuid.uuid4().hex
    return AuthorizationRequestModel(
        verifier_id=WORLD.verifier_id,
        nonce=nonce,
        query=DcqlLiteQueryModel(
            vct=sdjwt.VCT,
            required_claims=list(DEFAULT_REQUIRED_CLAIMS),
            required_tier="PID",
            required_loa="high",
        ),
    )


@app.post("/verify")
def verify_presentation(body: VerifyRequest) -> dict:
    """Returns the `VerificationResult` dict verbatim — schema conformance
    against contracts/verification_result.schema.json is asserted in
    tests/test_service.py, not re-derived as a second model here."""
    request = AuthorizationRequest(
        verifier_id=body.request.verifier_id,
        nonce=body.request.nonce,
        query=DcqlLiteQuery(
            vct=body.request.query.vct,
            required_claims=tuple(body.request.query.required_claims),
            required_tier=body.request.query.required_tier,
            required_loa=body.request.query.required_loa,
        ),
    )
    return verify(body.presentation, request=request, config=CONFIG, now=int(time.time()))


@app.post("/tamper-demo", response_model=TamperDemoResponse)
def tamper_demo(body: TamperDemoRequest) -> TamperDemoResponse:
    """Phase 6's /try-it endpoint: reuses eval.species.GENERATORS (the same
    corpus generators the Phase 3 eval scores) to build one labelled
    CorpusItem server-side, returning its presentation + request for the
    browser to POST straight to /verify. No tamper logic duplicated in
    TypeScript; no new verifier logic here."""
    if body.species not in TAMPER_DEMO_SPECIES:
        raise HTTPException(
            status_code=400,
            detail=f"unknown or unsupported species {body.species!r}; supported: {TAMPER_DEMO_SPECIES}",
        )
    item = GENERATORS[body.species](WORLD, index=_rand.randrange(1, 10**6), now=int(time.time()))
    return TamperDemoResponse(
        species=item.species,
        description=item.description,
        presentation=item.presentation,
        request=AuthorizationRequestModel(
            verifier_id=item.request.verifier_id,
            nonce=item.request.nonce,
            query=DcqlLiteQueryModel(
                vct=item.request.query.vct,
                required_claims=list(item.request.query.required_claims),
                required_tier=item.request.query.required_tier,
                required_loa=item.request.query.required_loa,
            ),
        ),
        expected_decision=item.expected_decision,
        expected_check=item.expected_check,
    )


@app.post("/present")
def submit_presentation(body: PresentSubmitRequest) -> dict:
    """Cross-device relay, wallet side: the wallet tab POSTs its finished
    presentation here, keyed by the nonce the verifier tab handed it via the
    QR — lets two browser tabs coordinate through this one process instead
    of needing WebRTC/BroadcastChannel."""
    _presentations[body.nonce] = body.presentation
    return {"ok": True}


@app.get("/present/{nonce}")
def poll_presentation(nonce: str) -> dict:
    """Cross-device relay, verifier side: polled until the wallet's
    presentation shows up under this nonce."""
    presentation = _presentations.get(nonce)
    if presentation is None:
        raise HTTPException(status_code=404, detail="no presentation yet for this nonce")
    return {"presentation": presentation}
