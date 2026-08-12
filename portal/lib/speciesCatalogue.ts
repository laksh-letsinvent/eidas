// The 13 defect species from eval/species.py, described for /experiment's
// catalogue. Text here paraphrases each generator's own description string
// and docstring (eval/species.py, issuer/tamper.py) — not invented, and not
// re-derived from results/wallet_eval.json (which carries counts, not
// prose). `live` marks the six species Try It can run against the real
// verifier without a swapped VerifierConfig (service/main.py's
// TAMPER_DEMO_SPECIES); the rest need a trust/registration/status-list
// change this local service's single fixed CONFIG can't reproduce.

export interface SpeciesEntry {
  id: string;
  whatItIs: string;
  whatBreaks: string;
  caughtAt: string | null;
  verifierMustHandle: string;
  live: boolean;
}

export const SPECIES_CATALOGUE: SpeciesEntry[] = [
  {
    id: "genuine",
    whatItIs: "The control: an unmodified, validly issued presentation revealing the requested claims.",
    whatBreaks: "Nothing — every check should pass.",
    caughtAt: null,
    verifierMustHandle: "Establishes the baseline accept path every defect species is measured against.",
    live: true,
  },
  {
    id: "broken_issuer_signature",
    whatItIs: "One bit flipped in the issuer JWT's signature; the payload and disclosures are untouched.",
    whatBreaks: "The JWS no longer verifies against the issuer's public key.",
    caughtAt: "issuer_signature",
    verifierMustHandle: "Recompute the signature over the exact bytes received, not the bytes it expected.",
    live: true,
  },
  {
    id: "altered_disclosed_claim",
    whatItIs: "A disclosed claim's value (nationality) is changed after issuance.",
    whatBreaks: "The recomputed digest of the disclosure no longer matches the signed _sd entry.",
    caughtAt: "disclosure_integrity",
    verifierMustHandle: "Re-hash every disclosed value with its salt and compare against the signed digest list — never trust a disclosed value on its face.",
    live: true,
  },
  {
    id: "stripped_kb_jwt",
    whatItIs: "The KB-JWT is removed entirely; the credential is presented with no holder-binding proof at all.",
    whatBreaks: "There is nothing proving this presentation came from the credential's legitimate holder.",
    caughtAt: "key_binding",
    verifierMustHandle: "Reject a presentation with no key-binding proof outright — a bearer credential is not an acceptable substitute.",
    live: true,
  },
  {
    id: "wrong_audience_kb_jwt",
    whatItIs: "The KB-JWT's aud names a different verifier than the one actually checking it.",
    whatBreaks: "The holder-binding proof was made for someone else's request.",
    caughtAt: "key_binding",
    verifierMustHandle: "Check the KB-JWT's aud against its own identity, not just that an aud is present.",
    live: false,
  },
  {
    id: "stale_nonce_kb_jwt",
    whatItIs: "The KB-JWT signs over a nonce from a previous request instead of the one just issued.",
    whatBreaks: "The proof of freshness is stale — this could be a captured, replayed presentation.",
    caughtAt: "key_binding",
    verifierMustHandle: "Bind every request to a single-use nonce and check the KB-JWT against exactly that value.",
    live: false,
  },
  {
    id: "cross_device_origin_phish",
    whatItIs: "A relaying attacker sits between the verifier's QR and the wallet, substituting its own origin as the audience the wallet binds to. Byte-for-byte the same defect as wrong_audience_kb_jwt, deliberately not reimplemented — the check that stops one stops the other.",
    whatBreaks: "The wallet's KB-JWT is bound to the phishing relay, not the real verifier.",
    caughtAt: "key_binding",
    verifierMustHandle: "The same aud check that catches an ordinary audience mismatch catches a phishing relay too — no special-casing needed.",
    live: true,
  },
  {
    id: "issuer_not_on_trusted_list",
    whatItIs: "A cryptographically valid presentation, checked by a verifier with no trust-list registration for this issuer.",
    whatBreaks: "Nothing about the wire bytes — the defect is entirely in the verifier's own trust configuration.",
    caughtAt: "trust_path",
    verifierMustHandle: "Never treat a valid signature as proof of an accredited issuer — trust-path is a separate lookup (ATLAS_EUDI.md §11).",
    live: false,
  },
  {
    id: "revoked_credential",
    whatItIs: "A valid presentation whose credential has since been revoked by its issuer.",
    whatBreaks: "The credential was legitimate at issuance and is no longer live.",
    caughtAt: "revocation",
    verifierMustHandle: "Check status separately from signature validity — a valid signature does not mean a live credential.",
    live: false,
  },
  {
    id: "expired_credential",
    whatItIs: "The credential's exp claim is in the past; everything else about it verifies cleanly.",
    whatBreaks: "The credential has aged out, independent of any tampering.",
    caughtAt: "policy",
    verifierMustHandle: "Check expiry against the verification time, every time — a policy-layer check, not a crypto one.",
    live: true,
  },
  {
    id: "loa_below_requirement",
    whatItIs: "The issuer resolves at LoA substantial in the verifier's trust registration; the journey requires LoA high.",
    whatBreaks: "The assurance level backing this credential doesn't meet what the relying party's journey demands.",
    caughtAt: "policy",
    verifierMustHandle: "Compare the resolved LoA against the journey's own requirement — a bank-specific policy decision, not a protocol constant.",
    live: false,
  },
  {
    id: "claim_inconsistency",
    whatItIs: "age_over_18 is set to deliberately disagree with birth_date at issuance, then both are disclosed together — the flagship red-team finding.",
    whatBreaks: "A derived claim and its source claim tell two different stories, and nothing in the credential format stops that from being issued.",
    caughtAt: "policy",
    verifierMustHandle: "Cross-check derived claims against their source claims whenever both are disclosed — the crypto core cannot catch this; only a verifier's own consistency policy can.",
    live: false,
  },
  {
    id: "over_asking",
    whatItIs: "A verifier registered only for age-check purposes requests and receives nationality as well.",
    whatBreaks: "The claims requested/disclosed exceed what this verifier is actually accredited to ask for.",
    caughtAt: "registration_purpose",
    verifierMustHandle: "Check the requested-and-revealed claim set against the verifier's own registered scope, not just that a registration exists.",
    live: false,
  },
];
