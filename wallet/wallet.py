"""
The wallet actor: holds a holder keypair + credential, proves key possession
at issuance, and resolves presentation requests against what it holds.

OpenID4VCI-lite issuance (ATLAS_EUDI.md §5): the issuer offers a credential
type + a nonce; the wallet proves possession of its holder key by signing a
proof-of-possession JWT over that nonce; the issuer verifies the proof and
calls `issuer.sdjwt.issue` binding the wallet's own key into `cnf`. This
module owns both sides of that tiny exchange in-process — no HTTP, no real
OpenID4VCI message set, just the fields that matter (aud, nonce, holder key).

OpenID4VP-lite presentation: given an `AuthorizationRequest` (verifier id,
nonce, DCQL-lite query), the wallet checks it actually holds every requested
claim, asks its `WalletUnlockProvider` whether release is authorized, and if
so calls `issuer.sdjwt.present` revealing exactly — not more, not less — the
requested claim set.
"""

from __future__ import annotations

from dataclasses import dataclass

from cryptography.hazmat.primitives.asymmetric import ec

from contracts.wallet_unlock import PresentationContext, UnlockResult, WalletUnlockProvider
from issuer import sdjwt
from issuer.crypto import KeyPair, decode_jwt_parts, encode_jwt, es256_verify, jwk_to_public_key
from issuer.sdjwt import Credential
from wallet.request import AuthorizationRequest

KEY_PROOF_TYP = "openid4vci-proof+jwt"


@dataclass(frozen=True)
class CredentialOffer:
    """What the issuer hands the wallet to start issuance."""

    issuer_id: str
    vct: str
    offer_nonce: str


class WalletCannotSatisfyRequest(Exception):
    """Raised when the wallet is asked for claims it doesn't hold on this credential."""


class Wallet:
    def __init__(self, unlock_provider: WalletUnlockProvider, holder_keypair: KeyPair | None = None) -> None:
        self.unlock_provider = unlock_provider
        self.holder_keypair = holder_keypair or KeyPair.generate()
        self.credential: Credential | None = None
        self.vct: str | None = None

    # -- issuance (OpenID4VCI-lite) --------------------------------------

    def generate_key_proof(self, offer: CredentialOffer, *, issued_at: int) -> str:
        """Sign a proof-of-possession JWT over the issuer's offer nonce.

        Public key travels in the JWT header (`jwk`), the way OpenID4VCI
        proof JWTs carry it — the issuer reads it from there, not from a
        side channel, to bind exactly the key that produced this signature.
        """
        header = {"alg": "ES256", "typ": KEY_PROOF_TYP, "jwk": self.holder_keypair.public_jwk()}
        payload = {"aud": offer.issuer_id, "nonce": offer.offer_nonce, "iat": issued_at}
        return encode_jwt(header, payload, self.holder_keypair.private_key)

    def receive_credential(self, credential: Credential, *, vct: str) -> None:
        self.credential = credential
        self.vct = vct

    # -- presentation (OpenID4VP-lite) ------------------------------------

    def handle_presentation_request(self, request: AuthorizationRequest, *, kb_issued_at: int) -> str:
        if self.credential is None:
            raise WalletCannotSatisfyRequest("wallet holds no credential")

        held_claim_names = {d.name for d in self.credential.disclosures}
        missing = set(request.query.required_claims) - held_claim_names
        if missing:
            raise WalletCannotSatisfyRequest(f"wallet does not hold requested claims: {sorted(missing)}")

        context = PresentationContext(
            credential_id=self.credential.issuer_jwt,
            audience=request.verifier_id,
            nonce=request.nonce,
            requested_claims=request.query.required_claims,
        )
        unlock: UnlockResult = self.unlock_provider.authorize(context)
        if not unlock.authorized:
            raise WalletCannotSatisfyRequest(f"wallet unlock denied: {unlock.reason}")

        return sdjwt.present(
            self.credential,
            reveal=set(request.query.required_claims),
            holder_private_key=self.holder_keypair.private_key,
            nonce=request.nonce,
            aud=request.verifier_id,
            kb_issued_at=kb_issued_at,
        )


def verify_key_proof(proof_jwt: str, *, expected_issuer_id: str, expected_nonce: str) -> tuple[bool, dict | None]:
    """Issuer side of the exchange: verify the wallet's proof-of-possession
    JWT and return (valid, holder_public_jwk). The returned JWK is what the
    issuer binds into the credential's `cnf` claim — issuance only proceeds
    if this function says the wallet really holds the private half."""
    header, payload, signature, signing_input = decode_jwt_parts(proof_jwt)
    holder_jwk = header.get("jwk")
    if holder_jwk is None:
        return False, None

    holder_public_key: ec.EllipticCurvePublicKey = jwk_to_public_key(holder_jwk)
    signature_valid = es256_verify(holder_public_key, signing_input, signature)
    aud_ok = payload.get("aud") == expected_issuer_id
    nonce_ok = payload.get("nonce") == expected_nonce

    return (signature_valid and aud_ok and nonce_ok), holder_jwk
