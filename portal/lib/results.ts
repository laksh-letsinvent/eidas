import { readFileSync } from "fs";
import path from "path";

/**
 * Typed getters over the three results artefacts (results/*.json, copied
 * verbatim into content/results/ — same manual-copy convention as the
 * markdown docs; re-copy after re-running the eval/red-team/anchor-swap
 * scripts). Hand-written interfaces matching eval/matrix.py's,
 * eval/redteam.py's (or equivalent), and eval/anchor_swap.py's actual
 * output shapes, not full JSON-Schema codegen — same local-interface
 * pattern as VerificationResultView.tsx.
 */

export interface EvalItem {
  item_id: string;
  species: string;
  expected_decision: "accept" | "reject";
  expected_check: string | null;
  actual_decision: "accept" | "reject";
  actual_failing_checks: string[];
  outcome_category: string;
  total_ms: number;
}

export type ConfusionMatrix = Record<string, Record<string, number>>;

export interface PerSpeciesCounts {
  n: number;
  caught: number;
  missed: number;
  wrong_check: number;
  accepted_correctly: number;
  false_reject: number;
}

export interface EvalSummary {
  total: number;
  apcer: number | null;
  apcer_species: string[];
  bpcer: number | null;
  wrong_check_rate: number;
  per_species: Record<string, PerSpeciesCounts>;
}

export interface WalletEval {
  schema_version: string;
  seed: number;
  generated_at: string;
  corpus_size: number;
  items: EvalItem[];
  matrix: ConfusionMatrix;
  summary: EvalSummary;
}

export interface RedteamAttempt {
  attempt_id: string;
  targeted_check_family: "crypto" | "policy";
  targeted_check: string;
  strategy: string;
  accepted: boolean;
  decision: "accept" | "reject";
  failing_checks: string[];
  tokens_in: number | null;
  tokens_out: number | null;
  cost_usd: number;
  agent_notes: string;
}

export interface WalletRedteam {
  schema_version: string;
  agent: string;
  generated_at_epoch: number;
  n_attempts: number;
  attempts: RedteamAttempt[];
  by_check_family: Record<string, { n: number; accepted: number; success_rate: number }>;
  token_accounting: { total_tokens_in: number; total_tokens_out: number; total_cost_usd: number };
}

export interface AnchorSwap {
  schema_version: string;
  mutual_recognition: {
    total_items: number;
    decision_mismatches: number;
    items_with_differing_anchor_id: number;
  };
  eu_only_issuer_scenario: {
    eu_decision: "accept" | "reject";
    uk_decision: "accept" | "reject";
    uk_failing_checks: string[];
  };
}

function readResultsJson<T>(filename: string): T {
  const raw = readFileSync(path.join(process.cwd(), "content", "results", filename), "utf-8");
  return JSON.parse(raw) as T;
}

export function getWalletEval(): WalletEval {
  return readResultsJson<WalletEval>("wallet_eval.json");
}

export function getWalletRedteam(): WalletRedteam {
  return readResultsJson<WalletRedteam>("wallet_redteam.json");
}

export function getAnchorSwap(): AnchorSwap {
  return readResultsJson<AnchorSwap>("wallet_anchor_swap.json");
}

// Canonical §9 check order, mirroring eval/matrix.py's OUTCOME_COLUMNS —
// duplicated here (not imported, there's no cross-language import) because
// the matrix's column order is meaningful (checks run in this order; a
// column further right means more checks passed before the failure).
export const OUTCOME_COLUMNS = [
  "format",
  "issuer_signature",
  "trust_path",
  "revocation",
  "disclosure_integrity",
  "key_binding",
  "registration_purpose",
  "policy",
  "accept",
] as const;
