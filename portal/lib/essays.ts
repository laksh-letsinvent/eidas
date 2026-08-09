import { readFileSync } from "fs";
import path from "path";

/**
 * Long-form write-ups (Phase 6). Generalizes experiment.ts's two-hardcoded-
 * functions pattern into a small registry + getter, since there are three
 * essays now instead of two fixed documents. Hand-written metadata (title,
 * dek) rather than parsed from markdown frontmatter — one less moving part
 * for three files.
 */

export interface EssayMeta {
  slug: string;
  title: string;
  dek: string;
}

export const ESSAYS: EssayMeta[] = [
  {
    slug: "defect-taxonomy",
    title: "A confusion matrix for credential verification",
    dek: "Credentials are deterministic — there's no ROC curve to plot. The eval discipline transposes into a labelled defect corpus and a per-species confusion matrix instead.",
  },
  {
    slug: "crypto-vs-policy",
    title: "What an AI agent found in a wallet verifier (and what it couldn't touch)",
    dek: "The flagship finding: the deterministic trust core resists every red-team attempt aimed at it. The policy layer — where selective disclosure removes the verifier's ability to cross-check — doesn't.",
  },
  {
    slug: "agentic-qes",
    title: "Can an AI agent hold a QES and sign for you?",
    dek: "The AES/QES boundary is mostly legal, not cryptographic — except for the one requirement that is: a QSCD's sole-control gate, which an agent can't clear by getting more capable.",
  },
];

export function getEssayMeta(slug: string): EssayMeta | undefined {
  return ESSAYS.find((e) => e.slug === slug);
}

export function getEssayContent(slug: string): string {
  return readFileSync(path.join(process.cwd(), "content", "essays", `${slug}.md`), "utf-8");
}
