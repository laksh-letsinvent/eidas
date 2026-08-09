// WebCrypto wrapper mirroring issuer/crypto.py's primitives, named the same
// way on purpose so the two are readable side by side. This is the browser
// realization of "the holder key genuinely cannot leave the device" —
// acceptance criterion 2 of BUILD_PROMPT_PHASE3_5.md.

import { b64urlEncode, utf8ToBytes } from "./base64url";

export interface PublicJwk {
  kty: "EC";
  crv: "P-256";
  x: string;
  y: string;
}

/** P-256 keypair, ES256 in JOSE terms — matches issuer/crypto.py's
 * `ec.SECP256R1()`. `extractable: false` is the load-bearing argument: the
 * browser's WebCrypto implementation refuses to ever hand back the private
 * key material, to any caller, for the life of the key. */
export async function generateHolderKeyPair(): Promise<CryptoKeyPair> {
  return (await crypto.subtle.generateKey(
    { name: "ECDSA", namedCurve: "P-256" },
    false,
    ["sign"]
  )) as CryptoKeyPair;
}

/** Public key export is fine and required — it's what goes in the
 * credential's `cnf` claim. Only the private half is non-extractable. */
export async function exportPublicJwk(publicKey: CryptoKey): Promise<PublicJwk> {
  const jwk = await crypto.subtle.exportKey("jwk", publicKey);
  return { kty: "EC", crv: "P-256", x: jwk.x!, y: jwk.y! };
}

/** The documented non-extractability proof (acceptance criterion 2): calls
 * `exportKey` on the private key and expects it to throw. Surfaced in the UI
 * (components/wallet/KeyExportDemo.tsx) so the failure is demonstrated, not
 * just implied by the `extractable: false` flag above. */
export async function attemptExportPrivateKey(
  privateKey: CryptoKey
): Promise<{ succeeded: boolean; error: string | null }> {
  try {
    await crypto.subtle.exportKey("jwk", privateKey);
    return { succeeded: true, error: null };
  } catch (err) {
    const error = err instanceof Error ? `${err.name}: ${err.message}` : String(err);
    return { succeeded: false, error };
  }
}

export async function sha256B64url(data: Uint8Array): Promise<string> {
  // `as BufferSource`: lib.dom.d.ts types TypedArrays generically over their
  // backing buffer; at runtime this is always a real ArrayBuffer-backed
  // Uint8Array, WebCrypto just wants a narrower type than TS infers here.
  const digest = await crypto.subtle.digest("SHA-256", data as BufferSource);
  return b64urlEncode(new Uint8Array(digest));
}

/** WebCrypto's ECDSA signature output is already the raw r‖s concatenation
 * (fixed-width — 64 bytes for P-256), which is exactly the JWS ES256 wire
 * format. That's different from Python's `cryptography` library, which is
 * DER-native — issuer/crypto.py's `es256_sign`/`es256_verify` do a manual
 * DER↔raw conversion specifically to bridge that gap. No such conversion is
 * needed here: same algorithm, different library convention. */
export async function es256Sign(privateKey: CryptoKey, signingInput: Uint8Array): Promise<Uint8Array> {
  const signature = await crypto.subtle.sign(
    { name: "ECDSA", hash: "SHA-256" },
    privateKey,
    signingInput as BufferSource
  );
  return new Uint8Array(signature);
}

function jsonBytes(value: Record<string, unknown>): Uint8Array {
  return utf8ToBytes(JSON.stringify(value));
}

/** Hand-rolled JWT compact serialization, matching issuer/crypto.py's
 * `encode_jwt`: base64url(header).base64url(payload).base64url(signature). */
export async function encodeJwt(
  header: Record<string, unknown>,
  payload: Record<string, unknown>,
  privateKey: CryptoKey
): Promise<string> {
  const headerB64 = b64urlEncode(jsonBytes(header));
  const payloadB64 = b64urlEncode(jsonBytes(payload));
  const signingInput = utf8ToBytes(`${headerB64}.${payloadB64}`);
  const signature = await es256Sign(privateKey, signingInput);
  return `${headerB64}.${payloadB64}.${b64urlEncode(signature)}`;
}
