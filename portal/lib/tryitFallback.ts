import { readFileSync } from "fs";
import path from "path";
import type { VerificationResult } from "@/components/wallet/VerificationResultView";
import type { AuthorizationRequest } from "@/lib/wallet/request";

export interface TryitFallback {
  wallet: { vct: string; disclosable_claim_count: number };
  bank: { presentation: string; result: VerificationResult };
  age: { presentation: string; result: VerificationResult };
  phish: {
    presentation: string;
    result: VerificationResult;
    phishing_origin: string;
    real_verifier_id: string;
  };
  species: Record<
    string,
    {
      description: string;
      expected_decision: "accept" | "reject";
      expected_check: string | null;
      presentation: string;
      request: AuthorizationRequest;
      result: VerificationResult;
    }
  >;
}

/**
 * Precomputed by examples/generate_tryit_fallback.py, from the exact same
 * fixture service/main.py uses (eval.species.build_world/good_config) — so
 * fallback numbers match what the live service would produce, not a second
 * drifting set of fake data. Try It degrades to this when localhost:8420
 * isn't reachable (BUILD_PROMPT_PHASE7-9.md Phase 9).
 */
export function getTryitFallback(): TryitFallback {
  const raw = readFileSync(path.join(process.cwd(), "content", "tryit_fallback.json"), "utf-8");
  return JSON.parse(raw) as TryitFallback;
}
