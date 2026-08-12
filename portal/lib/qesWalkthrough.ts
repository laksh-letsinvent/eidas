import { readFileSync } from "fs";
import path from "path";

export interface QesResult {
  signature_valid: boolean;
  chain_trusted: boolean;
  document_unmodified: boolean;
  timestamp_valid: boolean | null;
  is_qualified: boolean;
  anchor_id: string | null;
  detail: string | null;
}

export interface QesExperiment {
  species: string;
  description: string;
  expected_field: string;
  result: QesResult;
}

export interface QesWalkthrough {
  chain: { root: string; qtsp: string; signer: string; tsa: string };
  blank_pdf_bytes: number;
  signed_pdf_bytes: number;
  happy_result: QesResult;
  experiments: QesExperiment[];
}

/**
 * Precomputed by examples/generate_qes_content.py — a real CA chain and a
 * real PAdES signature, generated once, not live. No browser can drive
 * PAdES signing interactively, so Try It labels this a recorded run rather
 * than faking it as live (BUILD_PROMPT_PHASE7-9.md 8d).
 */
export function getQesWalkthrough(): QesWalkthrough {
  const raw = readFileSync(path.join(process.cwd(), "content", "qes_walkthrough.json"), "utf-8");
  return JSON.parse(raw) as QesWalkthrough;
}
