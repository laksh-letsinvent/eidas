// Shared "gate then present" orchestration — same sequence WalletCard uses
// for the same-device flow and the cross-device /wallet/present route use
// for the QR-scanned flow: fetch the unlock decision first, and only ever
// call sdjwt.present if it authorizes release.

import type { StoredCredential } from "./db";
import type { AuthorizationRequest } from "./request";
import { present } from "./sdjwt";
import { authorize, type PresentationContext, type UnlockResult } from "./unlock";

export type PresentWithUnlockResult = { authorized: true; presentation: string } | { authorized: false; reason: string };

export async function presentWithUnlock(
  keyPair: CryptoKeyPair,
  credential: StoredCredential,
  request: AuthorizationRequest
): Promise<PresentWithUnlockResult> {
  if (!credential.webauthnCredentialId) {
    throw new Error("no WebAuthn credential registered for this wallet");
  }

  const context: PresentationContext = {
    credentialId: credential.credentialCompact,
    audience: request.verifier_id,
    nonce: request.nonce,
    requestedClaims: request.query.required_claims,
  };
  const unlock: UnlockResult = await authorize(context, credential.webauthnCredentialId);
  if (!unlock.authorized) {
    return { authorized: false, reason: unlock.reason };
  }

  const now = Math.floor(Date.now() / 1000);
  const presentation = await present(credential.credentialCompact, {
    reveal: new Set(request.query.required_claims),
    holderPrivateKey: keyPair.privateKey,
    nonce: request.nonce,
    aud: request.verifier_id,
    kbIssuedAt: now,
  });
  return { authorized: true, presentation };
}
