// WebAuthn-backed realization of contracts/wallet_unlock.py's
// WalletUnlockProvider in the browser. Same question, same two-field
// answer: "may this credential be released for this presentation?" — here
// the answer is whatever a real platform-authenticator gesture (Touch ID,
// Windows Hello, a security key) says it is. There is no server-side check
// of the assertion signature: there's no registered "account" to check it
// against in this lab, the device owner's presence *is* the gate.

import { b64urlDecode, b64urlEncode } from "./base64url";

const RP_NAME = "eIDAS Wallet Lab";

function rpId(): string {
  return typeof window !== "undefined" ? window.location.hostname : "localhost";
}

function randomChallenge(): Uint8Array {
  return crypto.getRandomValues(new Uint8Array(32));
}

/** Registers a platform-authenticator credential, once, when the wallet
 * first receives a PID. Returns the credential ID (base64url) to store
 * alongside the held credential — `authorize()` needs it to know which
 * authenticator credential to challenge later. */
export async function registerUnlockCredential(userLabel: string): Promise<string> {
  const credential = (await navigator.credentials.create({
    publicKey: {
      rp: { name: RP_NAME, id: rpId() },
      user: {
        // `as BufferSource`: see the note on sha256B64url in crypto.ts —
        // lib.dom.d.ts types TypedArrays generically, WebAuthn wants a
        // narrower type than TS infers for a plain `new Uint8Array(...)`.
        id: crypto.getRandomValues(new Uint8Array(16)) as BufferSource,
        name: userLabel,
        displayName: userLabel,
      },
      challenge: randomChallenge() as BufferSource,
      pubKeyCredParams: [{ type: "public-key", alg: -7 }], // ES256, matches the holder key's own algorithm
      authenticatorSelection: { userVerification: "required" },
      timeout: 60000,
    },
  })) as PublicKeyCredential | null;

  if (!credential) throw new Error("WebAuthn registration returned no credential");
  return b64urlEncode(new Uint8Array(credential.rawId));
}

export interface PresentationContext {
  credentialId: string;
  audience: string;
  nonce: string;
  requestedClaims: string[];
}

export interface UnlockResult {
  authorized: boolean;
  reason: string;
}

/** Mirrors contracts/wallet_unlock.py's WalletUnlockProvider.authorize:
 * PresentationContext in, UnlockResult out. A successful assertion ->
 * authorized; a caught rejection (user cancels, no matching authenticator,
 * anything else WebAuthn can fail with) -> denied. The caller (WalletCard)
 * must check this *before* calling `sdjwt.present` — denial has to block a
 * presentation from ever being built, not just from being sent. */
export async function authorize(context: PresentationContext, webauthnCredentialId: string): Promise<UnlockResult> {
  try {
    const assertion = await navigator.credentials.get({
      publicKey: {
        challenge: randomChallenge() as BufferSource,
        allowCredentials: [{ type: "public-key", id: b64urlDecode(webauthnCredentialId) as BufferSource }],
        userVerification: "required",
        timeout: 60000,
      },
    });
    if (!assertion) return { authorized: false, reason: "no assertion returned" };
    return { authorized: true, reason: "webauthn gesture succeeded" };
  } catch (err) {
    const reason = err instanceof Error ? err.name : String(err);
    return { authorized: false, reason: `webauthn cancelled or denied: ${reason}` };
  }
}
