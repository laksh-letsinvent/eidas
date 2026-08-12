import { readFileSync } from "fs";
import path from "path";

/**
 * Public cut of the Experiment brief.
 *
 * The brief is a project charter written for Claude Code — phases, frozen
 * contracts, trilogy options, out-of-scope notes. A visitor needs none of
 * that. So this is an *allowlist*, not a blocklist: only the named sections
 * reach the page, and anything later added to the charter stays internal by
 * default rather than leaking onto the public site.
 *
 * The two sections kept are the ones that serve both audiences — why a bank
 * suddenly owns a verifier, and why that verifier is an evaluable surface.
 * Everything else the page needs (what was built, the defect catalogue) is
 * composed in app/experiment/page.tsx from real artefacts.
 */
const PUBLIC_SECTIONS = ["Diagnosis", "The instrument: what replaces the eval"];

/** Sentences that are internal framing rather than public content. */
const REDACTIONS = [
  /\s*Laksh's depth is in the biometric\/IDV substrate;[^]*?the same way bio-authn did for matching and PAD\./,
];

/**
 * Keep only the `## ` sections named in `wanted`. A `### ` subsection ends
 * the kept run — that is deliberate, and is what drops the draft defect
 * taxonomy from under "The instrument" (the live SpeciesCatalogue below it
 * on the page supersedes it, and carries the correct count of 13).
 */
function selectSections(raw: string, wanted: string[]): string {
  const out: string[] = [];
  let keeping = false;

  for (const line of raw.split("\n")) {
    const heading = /^##\s+(.+?)\s*$/.exec(line);
    if (heading) {
      keeping = wanted.includes(heading[1]);
      if (keeping) out.push(line);
      continue;
    }
    if (keeping && /^###\s+/.test(line)) {
      keeping = false;
      continue;
    }
    if (keeping) out.push(line);
  }

  return out.join("\n");
}

export function getExperiment(): string {
  const raw = readFileSync(
    path.join(process.cwd(), "content", "WALLET-QES-LAB-BRIEF.md"),
    "utf-8"
  );

  let body = selectSections(raw, PUBLIC_SECTIONS);
  for (const redaction of REDACTIONS) body = body.replace(redaction, "");
  body = body.replace(/\s*\[ASSUMED[^\]]*\]/g, "");
  body = body.replace(/\n{3,}/g, "\n\n");

  return body.trimEnd() + "\n";
}

export function getAtlas(): string {
  return readFileSync(
    path.join(process.cwd(), "content", "ATLAS_EUDI.md"),
    "utf-8"
  );
}

/** Inline "Phase N" build-sequencing references that survive the heading
 * cut below — the doc's body text refers to its own phase number in a few
 * sentences that otherwise carry real content, so those get trimmed rather
 * than the whole sentence dropped. */
const ATTESTATION_WALL_REDACTIONS: [RegExp, string][] = [
  [
    /^Phase 3\.5 deliverable\.[^]*?WUA, certification\)\.\n\n/m,
    "",
  ],
  [/\bthe Phase 2 verifier accepts\b/, "the verifier accepts"],
  [/\ba missing feature this phase forgot to build\b/, "a missing feature left unbuilt"],
  [/\bverified against the same Phase 2 verifier\b/, "verified against the same verifier"],
  [/\bThe protocol shape built in this phase is faithful\b/, "The protocol shape built here is faithful"],
  [/\bPhases 1–3 proved in Python\b/, "proved in Python"],
  [/\bis the phase's actual deliverable\b/, "is the point"],
];

/**
 * The attestation wall note, minus its H1 (the page supplies the heading),
 * its "Pointer to Phase 6" tail, and the inline phase references above —
 * all internal build sequencing a visitor has no context for.
 */
export function getAttestationWall(): string {
  const raw = readFileSync(
    path.join(process.cwd(), "content", "ATTESTATION_WALL.md"),
    "utf-8"
  );

  const lines = raw.split("\n");
  const end = lines.findIndex((line) => /^##\s+Pointer to Phase/i.test(line));

  let body = lines
    .slice(0, end === -1 ? lines.length : end)
    .filter((line) => !/^#\s+/.test(line))
    .join("\n")
    .trim() + "\n";

  for (const [pattern, replacement] of ATTESTATION_WALL_REDACTIONS) {
    body = body.replace(pattern, replacement);
  }
  body = body.replace(/\n{3,}/g, "\n\n");

  return body;
}
