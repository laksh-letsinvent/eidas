# Atlas — EUDI Wallet, eIDAS 2.0 & Qualified Signatures


## 1. Regulation and the ecosystem

**eIDAS 2.0** — Regulation (EU) 2024/1183, in force 20 May 2024, amending the original eIDAS (910/2014). It mandates that every member state offer citizens a Digital Identity Wallet and that named private-sector relying parties accept it. The regulation is the only binding text; everything below it (ARF, standards) is implementation detail that can and does move.

**Commission Implementing Regulations** *(CIRs / Implementing Acts)* — 30-plus delegated and implementing acts that turn the regulation's mandates into legally binding specifics (wallet certification, PID rulebook, relying party registration, trust lists). When someone says "the ARF requires X," check whether X is actually in a CIR or just in the ARF — only the CIR binds.

**Architecture and Reference Framework** *(ARF)* — the technical specification for the whole ecosystem: roles, credential formats, protocols, trust model. At **v2.x** (the 2.x line, updated iteratively through 2026 via public GitHub discussion topics). Critically, the ARF is **informative, not binding** — it translates the regulation and CIRs into buildable detail, but a conflict between ARF and a CIR is resolved in favour of the CIR. Treat it as the best available blueprint, not law.

**European Digital Identity Cooperation Group** *(EDICG)* — the member-state body that maintains the ARF. Matters only because it explains why the spec moves: it's negotiated, not decreed.

**Member State** — issues or accredits the wallet, runs or designates the PID Provider, publishes the trusted lists. The root of trust in the EU model is the member state, not a platform vendor. This is the structural contrast with Apple/Google wallets and the reason the regime exists.

**Wallet Provider** — the entity (member-state or accredited) that issues Wallet Units to users and stands behind their certification. One provider, many Wallet Units.

**Wallet Unit** — the instance of the wallet on a specific user's specific device. The thing that holds credentials and keys. Certification and attestation attach to the Wallet Unit, not the abstract app — which is exactly why a browser PWA cannot be a compliant Wallet Unit (see §6, and the attestation wall in the project brief).

**Relying Party** *(RP)* — any entity that requests and consumes a credential to deliver a service. Lara Bank is an RP. From 2027 it is an *obliged* RP: it must accept wallet presentations wherever it requires strong customer authentication. The RP's core new component is the **verifier** — this lab's subject.

**Intermediary** — a service that presents to the wallet on an RP's behalf. Introduces a delegation question the verifier must handle: is the attestation bound to the intermediary or the ultimate RP? Named here because it's a real trust-boundary trap, out of scope for the v1 build.

---

## 2. Credentials and the trust hierarchy

The single most useful mental model: credential *trust level* is set by *who issued it and under what accreditation*, not by its data format. Two credentials in identical SD-JWT VC format can sit at completely different legal tiers.

**Attestation** — the ARF's generic word for a credential: a signed set of claims about a subject. "Verifiable Credential" in the wider SSI world; the ARF prefers "attestation." Same object.

**Person Identification Data** *(PID)* — the foundational government-issued identity credential (name, date of birth, national identifier, etc.). Issued by a **PID Provider** designated by a member state, at Level of Assurance High. This is the credential that replaces "show us your passport" at onboarding. For Lara Bank, accepting a valid PID is near-equivalent to a completed identity-proofing step — which is the whole efficiency argument.

**PID Rulebook** — the CIR-defined schema and rules for what a PID contains and how it's issued. When the lab builds a corpus, copying the rulebook attributes verbatim buys realism for free (see brief, open question 1).

**Electronic Attestation of Attributes** *(EAA)* — a credential about attributes other than core identity (a diploma, a bank-account attestation, a membership). Three tiers by issuer:

| Tier                          | Issuer                                                                                                        | Legal weight                                                            | Verifier consequence                                            |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | --------------------------------------------------------------- |
| **QEAA** — Qualified EAA      | Qualified Trust Service Provider (QTSP)                                                                       | Presumption of accuracy; equivalent legal effect to a paper attestation | Highest non-PID trust; issuer is on a member-state trusted list |
| **PuB-EAA** — Public Body EAA | A public body responsible for an authentic source (not a QTSP, but holds a QTSP-issued qualified certificate) | Backed by the authentic source                                          | Trust anchor is the QTSP that signed the provider's certificate |
| **EAA** (non-qualified)       | Any trust service provider                                                                                    | No legal presumption — trust is contractual/bilateral                   | Verifier decides case-by-case; not on a qualified trusted list  |

The practical point for the verifier: **QEAA and PuB-EAA are discoverable through trusted lists; plain EAA is not.** Your `TrustAnchorProvider` must answer "what tier is this, and where's its anchor" — that branching is the core of the trust check.

**Authentic Source** — the authoritative register a PuB-EAA draws from (vehicle registry, population register). The reason a PuB-EAA is trusted: it's the source of record signing its own data.

**Qualified Trust Service Provider** *(QTSP)* — a trust service provider granted qualified status by a member-state supervisory body. Issues QEAAs and qualified certificates, and operates qualified signature services. The QTSP is the commercial engine of the trust hierarchy — and QES-via-wallet (§8) reshapes its business model.

---

## 3. Credential formats

Format is a transport-and-encoding choice, deliberately separated from trust tier (§2). The ARF backs two, and the verifier may need both.

**SD-JWT VC** — Selective Disclosure JWT Verifiable Credential. A JWT-based format where individual claims can be selectively revealed or withheld by the holder without breaking the issuer's signature. The lab's chosen format because it's JSON, hand-rollable on JWT primitives, and where selective disclosure is easiest to demonstrate byte-by-byte.

**mdoc / mDL** — the ISO/IEC 18013-5 mobile document format (CBOR-encoded, designed for the mobile driving licence and proximity/offline use). The ARF's second mandated format. Out of scope for this lab (proximity flows, CBOR tooling) but named because a real Lara Bank verifier will eventually have to parse both, and "we only handle SD-JWT VC" is an incomplete verifier.

**JWT** — JSON Web Token: signed, base64url-encoded claims. The container SD-JWT VC builds on.

**CBOR** — Concise Binary Object Representation. The binary encoding mdoc uses. Named to explain why mdoc is a different tooling world from SD-JWT VC.

**Claim** — a single asserted attribute (`family_name`, `age_over_18`, `birth_date`). Verification and selective disclosure both operate at claim granularity.

---

## 4. Selective disclosure and privacy mechanics

This is where the EUDI design is genuinely clever, and where the most interesting attacks live. Worth building by hand.

**Selective disclosure** — the holder reveals only the claims a verifier needs, from a credential containing more. Show `age_over_18` without revealing `birth_date`, name, or document number. The privacy promise of the whole regime.

**Salted-hash disclosure (SD-JWT mechanism)** — the issuer replaces each selectively-disclosable claim with a salted hash in the signed payload, and hands the holder the salt+value pairs (**disclosures**) separately. To reveal a claim, the holder presents its disclosure; the verifier hashes it and matches against the signed digest. Reveal nothing, and the verifier sees only an opaque hash. The issuer's signature covers the hashes, so **the holder can hide claims but cannot forge or alter them** — the property that makes the whole thing work. Building this by hand is Phase 1's core lesson.

**Disclosure** — the salt-and-value pair for one selectively-disclosable claim. Present it to reveal; withhold it to hide.

**Holder binding / key binding** — proof that the party presenting the credential is the party it was issued to, not someone replaying a stolen credential. The wallet holds a private key; the credential embeds the matching public key; at presentation the wallet signs a fresh challenge. See **KB-JWT** below. Strip this and a leaked credential becomes a bearer token — one of the defect species in the eval.

**Key Binding JWT** *(KB-JWT)* — the short JWT the wallet signs at presentation time, over a verifier-supplied nonce and audience, proving possession of the holder key. The verifier that skips KB-JWT validation accepts replays. This single check is where a large share of the eval's protocol defects concentrate.

**Unlinkability** — the property that two presentations of the same credential (or the same person) can't be correlated by verifiers or issuers colluding. eIDAS 2.0 asks for it; SD-JWT VC's basic form only partially delivers it, because the issuer signature and disclosure hashes can be stable across presentations. This gap is real and academically documented — and is the basis of the **selective-disclosure correlation experiment** (brief, candidate experiment #3). A strong, contrarian, shareable finding lives here: "EUDI promises unlinkability; here's the correlation that survives."

**Batch issuance / one-time credentials** — the main mitigation for the unlinkability gap: issue many single-use credential copies so each presentation uses a fresh one. Trades storage and issuance complexity for privacy. Worth naming because it's the ARF's answer to the correlation attack, and the answer has a cost.

---

## 5. Protocols

Two OpenID protocols carry the ecosystem. The verifier lives inside the presentation one.

**OpenID4VCI** — OpenID for Verifiable Credential Issuance. The protocol by which a wallet obtains a credential from an issuer (authorisation, proof of key possession, credential delivery). Phase 1–2 of the build implements a simplified version.

**OpenID4VP** — OpenID for Verifiable Presentations. The protocol by which a wallet presents credentials to a relying party. This is the verifier's protocol. Nonce, audience, response encryption, and the KB-JWT all live here. The lab's verifier is an OpenID4VP verifier.

**Digital Credentials Query Language** *(DCQL)* — the JSON query language introduced in OpenID4VP v1.0 by which a verifier states exactly which credentials and which claims it wants. Replaced the older **Presentation Exchange (PE)**. Matters because DCQL is where the RP declares its data appetite in machine-readable form — and where "asking for more than you're registered for" becomes detectable (§7).

**Presentation Exchange** *(PE)* — the DIF query language DCQL superseded. Named only so older docs and libraries don't confuse you; build against DCQL.

**nonce** — a fresh, single-use random value the verifier issues per presentation request; the wallet signs it in the KB-JWT. Defeats replay. A verifier that reuses or doesn't check nonces has a replay hole — an eval defect species.

**audience** — the identifier of the intended verifier, bound into the presentation. Defeats a presentation captured by one RP and replayed to another. Wrong-audience acceptance is another defect species.

**same-device vs cross-device flow** — same-device: wallet and browser on one phone. Cross-device: verifier shows a QR code, a separate phone's wallet scans and presents. Cross-device is where the **origin/phishing** attack lives (a relaying attacker sits between the QR and the wallet) — the defect species that only the real PWA wallet (Phase 3.5) can demonstrate live.

---

## 6. Wallet security architecture

The part that a browser cannot fake, and therefore the part that teaches the most.

**Level of Assurance** *(LoA)* — eIDAS's graded identity-confidence: **Low / Substantial / High**. The EUDI Wallet operates at **LoA High**. Lara Bank's verifier will require High for account opening and step-up; accepting a Substantial credential where High is mandated is a policy defect the eval should catch.

**Wallet Secure Cryptographic Device** *(WSCD)* — the certified hardware (secure element, eSIM, external smartcard) where the wallet's private keys physically live and where signing happens. Keys never leave it. This is the "something you have" made concrete and certifiable.

**Wallet Secure Cryptographic Application** *(WSCA)* — the software running against the WSCD that manages keys and crypto operations. WSCA + WSCD together are the wallet's secure core.

**Wallet Unit Attestation** *(WUA)** — a signed attestation, verifiable by issuers and (in some flows) relying parties, that *this* Wallet Unit is genuine, certified, and backed by a real WSCD. It carries a public key whose private half is WSCD-protected. Earlier ARF drafts called the related evidence **Wallet Trust Evidence (WTE)**; the 2.x line consolidates around WUA. This is the certification hook — and **the exact thing a PWA cannot produce**, because a browser has no WSCD and no certified provider to attest it. Discovering that in code is the attestation-wall lesson.

**Wallet Trust Evidence** *(WTE)* — the older term for the evidence a Wallet Unit presents to prove its trustworthiness to an issuer. Folded into WUA in ARF 2.x; noted so older docs parse.

**certification (of the Wallet Solution)** — the formal, CIR-defined conformance and security certification a Wallet Solution must pass to be trusted at LoA High. The reason "just ship a web app" fails eIDAS isn't snobbery; it's that an uncertified solution with no WSCD can't attest itself, so no issuer will provision a PID to it.

---

## 7. Trust infrastructure

How the verifier answers "should I trust this issuer, and is this RP allowed to ask?" This is the `TrustAnchorProvider` made real.

**Trusted List** *(Trusted Lists)* — member-state-published, signed lists of accredited providers (PID Providers, QEAA Providers, PuB-EAA Providers) and their trust anchors, under Article 22 of eIDAS. The verifier walks from a credential's issuer signature to a trust anchor on a trusted list. No path to a list = untrusted issuer, regardless of a perfectly valid signature. **Valid signature ≠ trusted issuer** is the disambiguation that trips people; the trusted list is what separates them.

**Trust anchor** — the root key/certificate at the top of a trust path, published on a trusted list. What the verifier ultimately checks against.

**Relying Party Registration** — the CIR-mandated process by which an RP registers with a member state before it can request credentials, declaring its identity and its intended purpose/attributes. Lara Bank must be a registered RP to operate a verifier at all.

**Registration Certificate** — the credential an RP receives on registration, stating which attributes it is entitled to request. The privacy control with teeth: the **wallet can refuse** to disclose attributes the RP isn't registered for, before the user ever sees a consent screen. This flips the usual model — the data minimisation is enforced at the wallet, not trusted to the RP's good behaviour. A verifier/RP that requests beyond its registration is the "over-asking" defect, and it's structurally detectable.

**Revocation / Status List** — the mechanism (e.g. a token status list) by which an issuer signals a credential is no longer valid. The verifier must check it; a credential can be cryptographically perfect and revoked. "Signature valid" and "credential live" are different questions — skipping the status check is a defect species.

**Trust over IP / trust registry** — the general pattern (trust anchors + status + registration) the EU implements via trusted lists. Named for orientation against the wider SSI vocabulary.

---

## 8. Qualified signatures and trust services

The QES track (Phase 4). The recurring confusion this section kills: **cryptographic validity and qualified legal status are different axes.**

**Electronic signature (the eIDAS ladder)** — three tiers of increasing legal weight:

| Tier | Name | What it requires | Legal effect |
|---|---|---|---|
| **SES** | Simple Electronic Signature | Any electronic mark (a typed name, a tickbox) | Admissible, but weak |
| **AES** | Advanced Electronic Signature | Uniquely linked to and under sole control of the signer; detects later tampering | Stronger; still not presumed equivalent to handwritten |
| **QES** | Qualified Electronic Signature | AES + created by a QSCD + backed by a qualified certificate from a QTSP | **Legal equivalence to a handwritten signature across all member states** |

The lab's Phase 4 lesson: in *code*, AES and QES can look nearly identical — the difference is largely the certificate's qualified status and the device (QSCD). Much of what makes a signature "qualified" is legal and procedural, not cryptographic. Everyone conflates these; building both and diffing them is the payoff.

**Advanced Electronic Signature** *(AES / AdES)* — signature uniquely linked to the signer, capable of identifying them, under their sole control, and tamper-evident. Cryptographically serious; legally not top-tier.

**Qualified Electronic Signature** *(QES)* — AES made qualified by a QSCD and a qualified certificate. Under eIDAS 2.0, the wallet can produce QES, and it is **free of charge for natural persons**. This is the sleeper disruption: qualified signing stops being a paid product and becomes a wallet feature — the basis of the QES-free market-teardown essay (brief, candidate #5).

**Qualified Signature Creation Device** *(QSCD)* — the certified device that creates a QES, protecting the signing key. Can be local (smartcard) or, increasingly, a **remote QSCD** operated by a QTSP with the signer in sole control.

**Sole control** — the eIDAS requirement that only the signer can use their signing key. Straightforward for a smartcard; subtle for remote signing; and genuinely unresolved when the "signer" is an autonomous agent — the frontier the **agentic-QES essay** (brief, candidate #2) probes. This is the entry where the AI-PM angle and the signature domain actually collide.

**Qualified Certificate** — a certificate issued by a QTSP binding a verified identity to a signing key, meeting eIDAS Annex I. The "qualified" in QES.

**PAdES / XAdES / CAdES / JAdES** — the ETSI signature formats for PDF / XML / CMS / JSON respectively. Phase 4 signs a PDF, so **PAdES** is the relevant one. Named so the format zoo doesn't surprise you.

**Timestamp (qualified)** — a QTSP-issued, signed assertion of the time a signature existed, giving long-term non-repudiation. A missing or forged timestamp is one of the five QES break-it experiments.

---

## 9. The verification decision (what the verifier actually checks)

The lab's product. A correct OpenID4VP verifier, given a presentation, runs an ordered set of checks. Naming them precisely is half the learning, because each maps to a defect species and to a column in the results confusion matrix.

1. **Format and parse** — is this well-formed SD-JWT VC + KB-JWT? Malformed input is the trivial reject.
2. **Issuer signature** — does the issuer's signature over the credential verify? (Cryptographic validity.)
3. **Trust path** — does the issuer chain to a trust anchor on a trusted list, at the required tier? (Trusted issuer — distinct from step 2.)
4. **Revocation/status** — is the credential still live? (Distinct from both above.)
5. **Disclosure integrity** — do the presented disclosures hash to the signed digests? (Selective disclosure not tampered.)
6. **Key binding** — does the KB-JWT verify against the credential's holder key, over *this* nonce and audience? (Not a replay, not the wrong verifier.)
7. **Registration/purpose** — is the RP requesting only attributes it's registered for? (Over-asking / data-minimisation.)
8. **Policy** — does the credential satisfy the journey's requirements: LoA high enough, not expired, claims internally consistent (`age_over_18` vs `birth_date`)? (The soft layer.)

The **asymmetry that becomes the flagship finding**: checks 2–6 are deterministic cryptography — an LLM adversary cannot bluff past a hash or a signature. Checks 7–8 are policy logic the RP wrote, and that's where the AI red-team (brief, candidate #1) will find holes. eIDAS makes the trust core AI-proof and pushes all the residual fraud risk into the policy layer the bank owns. That's the sentence a head of risk remembers.

---

## 10. UK divergence (pointer)

Full treatment in `TRUST_MODEL.md`. The one-line orientation: the UK solves the same problem with a different trust anchor. **GOV.UK Wallet** issues state credentials; the **DIATF / DVS trust framework** certifies private verification providers; there is no eIDAS trusted-list equivalent and, as of mid-2026, no open private-sector RP integration. For the lab, the UK is Phase 5's anchor swap — same verifier, `TrustAnchorProvider` pointed at a DIATF-style certificate instead of an EU trusted list — not a live integration. The two-posture argument from the IDV strategy is demonstrated by what breaks when you flip that one component.

---

## 11. Quick disambiguations (the ones people get wrong)

- **Valid signature ≠ trusted issuer.** Cryptographic verification (§9 step 2) says the signature is intact; the trusted-list path (step 3) says the issuer is accredited. A perfect signature from an unlisted issuer is untrusted.
- **Signature valid ≠ credential live.** Revocation is a separate check. A cryptographically perfect credential can be revoked.
- **Trust tier ≠ data format.** QEAA and plain EAA can share the SD-JWT VC format and sit at completely different legal levels. Who issued it, under what accreditation, sets the tier.
- **AES ≠ QES.** In code they can look nearly identical; the qualified status is the QSCD plus the qualified certificate, much of it legal rather than cryptographic.
- **Holder ≠ bearer.** Key binding is what stops a leaked credential being a bearer token. No KB-JWT check, no holder binding.
- **PWA wallet ≠ Wallet Unit.** No WSCD, no WUA, no certification — a browser wallet teaches the protocol but cannot be eIDAS-compliant. That wall is the lesson, not a bug.
- **Selective disclosure ≠ unlinkability.** Hiding claims doesn't prevent correlating presentations; stable issuer signatures and digests can still link them. Batch/one-time credentials are the mitigation, and they cost something.
- **Requesting ≠ entitled to request.** Registration certificates mean the wallet can refuse over-asking before consent. Data minimisation is enforced, not trusted.

---

*Created July 2026. Owned by Laksh. Companion to `WALLET-QES-LAB-BRIEF.md`. Next Atlas siblings: `TRUST_MODEL.md` (trust-path mechanics + UK/EU divergence in depth), `ATLAS_QES.md` if the QES vocabulary outgrows §8.*
