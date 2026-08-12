"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { StoryCard } from "./StoryCard";
import { VerificationResultView, type VerificationResult } from "@/components/wallet/VerificationResultView";
import { postTamperDemo, postVerify, type TamperDemoResult } from "@/lib/wallet/api";
import type { ServiceHealth } from "@/lib/wallet/useServiceHealth";
import type { TryitFallback } from "@/lib/tryitFallback";

const SPECIES = [
  { id: "genuine", label: "Nothing wrong", hint: "the control run — should accept" },
  { id: "broken_issuer_signature", label: "A tampered credential", hint: "one bit flipped in the issuer's signature" },
  { id: "altered_disclosed_claim", label: "A changed answer", hint: "a disclosed value no longer matches its digest" },
  { id: "stripped_kb_jwt", label: "No proof it's your phone", hint: "the key-binding proof is missing entirely" },
  { id: "expired_credential", label: "An expired PID", hint: "signature still valid, expiry date has passed" },
  { id: "cross_device_origin_phish", label: "A phished QR", hint: "bound to the wrong verifier's identity" },
];

/**
 * The six wire-level defect species, restyled so each reads as "the bank
 * story going wrong" rather than a standalone check name (BUILD_PROMPT_PHASE7-9.md
 * 8c) — same /tamper-demo -> /verify round trip the old Try It picker used,
 * same six species (service/main.py's TAMPER_DEMO_SPECIES), just framed as
 * Lara Bank's onboarding story hitting each defect in turn. Falls back to
 * examples/generate_tryit_fallback.py's precomputed results when the local
 * service isn't reachable (Phase 9).
 */
export function SpeciesStory({ health, fallback }: { health: ServiceHealth; fallback: TryitFallback["species"] }) {
  const [selected, setSelected] = useState<string | null>(null);
  const [demo, setDemo] = useState<TamperDemoResult | null>(null);
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const live = health === "up";

  async function run(species: string) {
    setSelected(species);
    setResult(null);
    setDemo(null);
    setError(null);

    if (!live) {
      const recorded = fallback[species];
      setResult(recorded.result);
      setDemo({
        species,
        description: recorded.description,
        presentation: recorded.presentation,
        request: recorded.request,
        expected_decision: recorded.expected_decision,
        expected_check: recorded.expected_check,
      });
      return;
    }

    setLoading(true);
    try {
      const demoResult = await postTamperDemo(species);
      setDemo(demoResult);
      const verificationResult = await postVerify(demoResult.presentation, demoResult.request);
      setResult(verificationResult as unknown as VerificationResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <StoryCard
      title="Open a bank account — but something's wrong"
      blurb="Same onboarding story as before, six ways it can go wrong on the wire. Pick one and watch which of the eight checks catches it."
      tag={live ? "6 of 13 species" : "6 of 13 species · recorded"}
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {SPECIES.map((s) => (
          <button
            key={s.id}
            onClick={() => run(s.id)}
            disabled={loading}
            className={`text-left rounded-lg border px-3 py-2 transition-colors ${
              selected === s.id
                ? "border-[var(--accent-c)] bg-[var(--primary-wash)]"
                : "border-[var(--border-c)] bg-[var(--surface-2)] hover:bg-[var(--surface-2)]/70"
            }`}
          >
            <div className="text-sm font-medium text-[var(--foreground)]">{s.label}</div>
            <div className="text-xs text-[var(--text-2)] mt-0.5">{s.hint}</div>
          </button>
        ))}
      </div>

      {loading && (
        <p className="text-sm text-[var(--text-2)] flex items-center gap-2">
          <Loader2 size={14} className="animate-spin" /> Building the presentation and verifying…
        </p>
      )}

      {error && <p className="text-sm text-[var(--reject)]">{error}.</p>}

      {!live && demo && (
        <p className="text-[10px] uppercase tracking-wide text-[var(--text-3)]">Recorded run</p>
      )}

      {demo && (
        <p className="text-xs text-[var(--text-3)] font-mono">
          expected: {demo.expected_decision}
          {demo.expected_check ? ` — caught at ${demo.expected_check}` : ""}
        </p>
      )}

      {result && <VerificationResultView result={result} presentation={demo?.presentation} />}
    </StoryCard>
  );
}
