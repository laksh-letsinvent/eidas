// TS re-expression of issuer/sdjwt.py's presentation-building half — the
// wallet never issues, only presents, so only `split_compact`/`Disclosure`/
// `present` are mirrored here, not `issue`. Field names and the wire
// format (issuer-jwt~disclosure~...~ for issuance, with a KB-JWT appended
// at presentation) match byte-for-byte with the Python side.

import { b64urlDecode, bytesToUtf8, utf8ToBytes } from "./base64url";
import { encodeJwt, sha256B64url } from "./crypto";

const KB_JWT_TYP = "kb+jwt";

export interface Disclosure {
  salt: string;
  name: string;
  value: unknown;
  b64: string;
  digest: string;
}

export async function parseDisclosure(b64: string): Promise<Disclosure> {
  const raw = bytesToUtf8(b64urlDecode(b64));
  const [salt, name, value] = JSON.parse(raw) as [string, string, unknown];
  const digest = await sha256B64url(utf8ToBytes(b64));
  return { salt, name, value, b64, digest };
}

/** Mirrors issuer/sdjwt.py's split_compact: issuer-jwt~disclosure~...~ has a
 * trailing empty segment (issuance form, no KB-JWT); issuer-jwt~disclosure~
 * ...~kb-jwt has a non-empty last segment (presentation form). */
export function splitCompact(compact: string): { issuerJwt: string; disclosureB64s: string[]; kbJwt: string | null } {
  const parts = compact.split("~");
  const issuerJwt = parts[0];
  const last = parts[parts.length - 1];
  if (last === "") {
    return { issuerJwt, disclosureB64s: parts.slice(1, -1), kbJwt: null };
  }
  return { issuerJwt, disclosureB64s: parts.slice(1, -1), kbJwt: last };
}

function sdHashInput(issuerJwt: string, selected: Disclosure[]): string {
  return [issuerJwt, ...selected.map((d) => d.b64)].join("~") + "~";
}

export interface PresentArgs {
  reveal: Set<string>;
  holderPrivateKey: CryptoKey;
  nonce: string;
  aud: string;
  kbIssuedAt: number;
}

/** Mirrors issuer/sdjwt.py's present(): select the requested disclosures,
 * bind a KB-JWT over exactly that set via sd_hash, nonce, and aud. */
export async function present(credentialCompact: string, args: PresentArgs): Promise<string> {
  const { issuerJwt, disclosureB64s } = splitCompact(credentialCompact);
  const allDisclosures = await Promise.all(disclosureB64s.map(parseDisclosure));
  const selected = allDisclosures.filter((d) => args.reveal.has(d.name));

  const input = sdHashInput(issuerJwt, selected);
  const sdHash = await sha256B64url(utf8ToBytes(input));

  const kbHeader = { alg: "ES256", typ: KB_JWT_TYP };
  const kbPayload = { iat: args.kbIssuedAt, aud: args.aud, nonce: args.nonce, sd_hash: sdHash };
  const kbJwt = await encodeJwt(kbHeader, kbPayload, args.holderPrivateKey);

  return input + kbJwt;
}
