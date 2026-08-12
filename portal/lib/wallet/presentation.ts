// Client-side parse of a compact SD-JWT presentation (issuer-jwt~disclosure~
// ...~kb-jwt) into the data a verifier's decision is actually made from:
// which claims were revealed, the aggregate digest the KB-JWT signs over,
// and the audience/nonce it was bound to. This is deliberately separate
// from `VerificationResult` (contracts/verification_result.schema.json,
// frozen) — the schema only carries the pass/fail ladder, never the wire
// data, so this reads the presentation string directly, the same way a
// verifier implementation would before running its checks.

import { b64urlDecode, bytesToUtf8 } from "./base64url";
import { splitCompact, parseDisclosure } from "./sdjwt";

export interface DisclosedClaim {
  name: string;
  value: unknown;
}

export interface KbPayload {
  iat: number;
  aud: string;
  nonce: string;
  sd_hash: string;
}

export interface ParsedPresentation {
  disclosed: DisclosedClaim[];
  kb: KbPayload | null;
}

function decodeJwtPayload(jwt: string): Record<string, unknown> {
  const [, payloadB64] = jwt.split(".");
  return JSON.parse(bytesToUtf8(b64urlDecode(payloadB64)));
}

/** The fixed PID disclosable-claim universe `service/main.py`'s WORLD
 * fixture issues against (issuer/pid.py's DISCLOSABLE_KEYS). Used only to
 * compute *names* of withheld claims — the presentation itself never
 * reveals what it didn't disclose, by design. */
export const KNOWN_PID_CLAIMS = ["family_name", "given_name", "birth_date", "age_over_18", "nationality"];

export async function parsePresentation(compact: string): Promise<ParsedPresentation> {
  const { disclosureB64s, kbJwt } = splitCompact(compact);
  const disclosures = await Promise.all(disclosureB64s.map(parseDisclosure));
  const disclosed = disclosures.map((d) => ({ name: d.name, value: d.value }));
  const kb = kbJwt ? (decodeJwtPayload(kbJwt) as unknown as KbPayload) : null;
  return { disclosed, kb };
}
