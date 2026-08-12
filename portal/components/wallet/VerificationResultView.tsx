"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, XCircle, MinusCircle } from "lucide-react";
import { KNOWN_PID_CLAIMS, parsePresentation, type ParsedPresentation } from "@/lib/wallet/presentation";

const CHECK_ORDER = [
  "format",
  "issuer_signature",
  "trust_path",
  "revocation",
  "disclosure_integrity",
  "key_binding",
  "registration_purpose",
  "policy",
];

interface Check {
  name: string;
  result: "pass" | "fail" | "skip";
  detail: string | null;
}

export interface VerificationResult {
  decision: "accept" | "reject";
  checks: Check[];
  trust: { tier: string | null; anchor_id: string | null; loa: string | null };
  timing: { total_ms: number };
}

function formatValue(v: unknown): string {
  if (typeof v === "boolean") return v ? "true" : "false";
  return String(v);
}

/**
 * Leads with what actually moved on the wire — disclosed claims, withheld
 * claims, the digest and audience/nonce the key-binding proof covers —
 * then the eight-check ladder underneath. `result` is the frozen
 * `VerificationResult` (contracts/verification_result.schema.json,
 * unchanged); `presentation` is the raw compact SD-JWT string, parsed
 * client-side (lib/wallet/presentation.ts) — optional, so callers with only
 * a precomputed `VerificationResult` (no wire capture, e.g. content/in_action.json)
 * still get the check ladder without the top section.
 */
export function VerificationResultView({
  result,
  presentation,
}: {
  result: VerificationResult;
  presentation?: string;
}) {
  const byName = new Map(result.checks.map((c) => [c.name, c]));
  const [parsed, setParsed] = useState<ParsedPresentation | null>(null);
  const [parseError, setParseError] = useState(false);

  useEffect(() => {
    setParsed(null);
    setParseError(false);
    if (!presentation) return;
    let cancelled = false;
    parsePresentation(presentation)
      .then((p) => {
        if (!cancelled) setParsed(p);
      })
      .catch(() => {
        if (!cancelled) setParseError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [presentation]);

  const disclosedNames = new Set((parsed?.disclosed ?? []).map((d) => d.name));
  const withheld = KNOWN_PID_CLAIMS.filter((k) => !disclosedNames.has(k));

  return (
    <div className="rounded-xl border border-[var(--border-c)] bg-[var(--surface)] overflow-hidden">
      {presentation && !parseError && (
        <div className="p-4 border-b border-[var(--border-c)] space-y-3">
          {!parsed ? (
            <p className="text-xs text-[var(--text-3)]">Parsing presentation…</p>
          ) : (
            <>
              <div>
                <div className="text-[10px] uppercase tracking-wide text-[var(--text-3)] mb-1.5">
                  Claims disclosed
                </div>
                {parsed.disclosed.length === 0 ? (
                  <p className="text-xs text-[var(--text-3)]">None — nothing beyond the credential's existence.</p>
                ) : (
                  <ul className="space-y-1">
                    {parsed.disclosed.map((c) => (
                      <li key={c.name} className="flex items-baseline gap-2 text-xs">
                        <span className="font-mono text-[var(--accept)]">{c.name}</span>
                        <span className="text-[var(--foreground)]">= {formatValue(c.value)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              {withheld.length > 0 && (
                <div>
                  <div className="text-[10px] uppercase tracking-wide text-[var(--text-3)] mb-1.5">
                    Claims withheld
                  </div>
                  <ul className="flex flex-wrap gap-1.5">
                    {withheld.map((name) => (
                      <li
                        key={name}
                        className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-[var(--surface-2)] text-[var(--text-3)]"
                      >
                        {name}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {parsed.kb && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1.5 pt-1 text-[11px] font-mono">
                  <div className="flex gap-2">
                    <span className="text-[var(--text-3)] shrink-0">digest</span>
                    <span className="text-[var(--text-2)] truncate">{parsed.kb.sd_hash}</span>
                  </div>
                  <div className="flex gap-2">
                    <span className="text-[var(--text-3)] shrink-0">audience</span>
                    <span className="text-[var(--text-2)] truncate">{parsed.kb.aud}</span>
                  </div>
                  <div className="flex gap-2 sm:col-span-2">
                    <span className="text-[var(--text-3)] shrink-0">nonce</span>
                    <span className="text-[var(--text-2)] truncate">{parsed.kb.nonce}</span>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      <div className="p-4">
        <div className="flex items-center justify-between mb-3">
          <span
            className={`text-sm font-semibold px-2 py-1 rounded-full ${
              result.decision === "accept"
                ? "bg-[var(--accept-zone)] text-[var(--accept)]"
                : "bg-[var(--reject-zone)] text-[var(--reject)]"
            }`}
          >
            {result.decision.toUpperCase()}
          </span>
          <span className="text-[10px] font-mono text-[var(--text-3)]">{result.timing.total_ms.toFixed(3)} ms</span>
        </div>
        <ul className="space-y-1">
          {CHECK_ORDER.map((name) => {
            const check = byName.get(name);
            if (!check) return null;
            const Icon = check.result === "pass" ? CheckCircle2 : check.result === "fail" ? XCircle : MinusCircle;
            const color =
              check.result === "pass"
                ? "text-[var(--accept)]"
                : check.result === "fail"
                  ? "text-[var(--reject)]"
                  : "text-[var(--text-3)]";
            return (
              <li key={name} className="flex items-start gap-2 text-xs">
                <Icon size={13} className={`shrink-0 mt-0.5 ${color}`} />
                <span className="font-mono text-[var(--text-2)]">{name}</span>
                {check.detail && <span className="text-[var(--text-3)]">— {check.detail}</span>}
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
