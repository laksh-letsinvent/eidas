"""
Pydantic request/response models for the Phase 3.5 verifier service.

Deliberately thin: everything here mirrors an existing Python shape
(`wallet.wallet.CredentialOffer`, `wallet.request.AuthorizationRequest`/
`DcqlLiteQuery`) rather than inventing a new one. The one exception is
`/verify`'s response, which is NOT modelled here — it's returned as a plain
dict straight from `verifier.verify.verify()` so there is no second copy of
`VerificationResult`'s shape to drift out of sync with the frozen
`contracts/verification_result.schema.json`. Schema conformance is checked
in `tests/test_service.py`, not enforced by a Pydantic model here.
"""

from __future__ import annotations

from pydantic import BaseModel


class CredentialOfferResponse(BaseModel):
    offer_id: str
    issuer_id: str
    vct: str
    offer_nonce: str


class IssueRequest(BaseModel):
    offer_id: str
    proof_jwt: str


class IssueResponse(BaseModel):
    credential: str


class DcqlLiteQueryModel(BaseModel):
    vct: str
    required_claims: list[str]
    required_tier: str | None = None
    required_loa: str | None = None


class AuthorizationRequestModel(BaseModel):
    verifier_id: str
    nonce: str
    query: DcqlLiteQueryModel


class VerifyRequest(BaseModel):
    presentation: str
    request: AuthorizationRequestModel


class PresentSubmitRequest(BaseModel):
    nonce: str
    presentation: str


class TamperDemoRequest(BaseModel):
    species: str


class TamperDemoResponse(BaseModel):
    species: str
    description: str
    presentation: str
    request: AuthorizationRequestModel
    expected_decision: str
    expected_check: str | None
