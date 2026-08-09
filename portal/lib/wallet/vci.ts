// OpenID4VCI-lite issuance, wallet side — mirrors wallet/wallet.py's
// `Wallet.generate_key_proof` exactly (same header/payload shape, same
// `typ`), so the FastAPI service's `verify_key_proof` (unchanged Python)
// accepts it without any special-casing for a browser-originated proof.

import { encodeJwt, exportPublicJwk } from "./crypto";

const KEY_PROOF_TYP = "openid4vci-proof+jwt";

export interface CredentialOffer {
  issuer_id: string;
  vct: string;
  offer_nonce: string;
}

export async function generateKeyProof(
  offer: CredentialOffer,
  holderKeyPair: CryptoKeyPair,
  issuedAt: number
): Promise<string> {
  const holderPublicJwk = await exportPublicJwk(holderKeyPair.publicKey);
  const header = { alg: "ES256", typ: KEY_PROOF_TYP, jwk: holderPublicJwk };
  const payload = { aud: offer.issuer_id, nonce: offer.offer_nonce, iat: issuedAt };
  return encodeJwt(header, payload, holderKeyPair.privateKey);
}
