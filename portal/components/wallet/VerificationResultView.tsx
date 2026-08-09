"use client";

import { CheckCircle2, XCircle, MinusCircle } from "lucide-react";

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

export function VerificationResultView({ result }: { result: VerificationResult }) {
  const byName = new Map(result.checks.map((c) => [c.name, c]));

  return (
    <div className="rounded-xl border border-[var(--border-c)] bg-[var(--surface)] p-4">
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
  );
}
