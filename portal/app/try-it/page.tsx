"use client";

import { useState } from "react";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { VerificationResultView, type VerificationResult } from "@/components/wallet/VerificationResultView";
import { postTamperDemo, postVerify, type TamperDemoResult } from "@/lib/wallet/api";

const SPECIES = [
  { id: "genuine", label: "Genuine", hint: "everything correct — should accept" },
  { id: "broken_issuer_signature", label: "Broken issuer signature", hint: "one bit flipped" },
  { id: "altered_disclosed_claim", label: "Altered claim", hint: "disclosure digest no longer matches" },
  { id: "stripped_kb_jwt", label: "Stripped KB-JWT", hint: "no proof of holder-key possession" },
  { id: "expired_credential", label: "Expired credential", hint: "exp in the past, signature still valid" },
  { id: "cross_device_origin_phish", label: "Cross-device phishing", hint: "KB-JWT bound to the wrong verifier" },
];

export default function TryItPage() {
  const [selected, setSelected] = useState<string | null>(null);
  const [demo, setDemo] = useState<TamperDemoResult | null>(null);
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(species: string) {
    setSelected(species);
    setLoading(true);
    setError(null);
    setDemo(null);
    setResult(null);
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
    <div className="max-w-2xl mx-auto px-6 py-12 space-y-6">
      <div>
        <h1
          className="text-3xl font-bold tracking-tight"
          style={{ fontFamily: "var(--font-display)", color: "var(--foreground)" }}
        >
          Try It
        </h1>
        <p className="text-sm text-[var(--text-2)] mt-2">
          Pick a defect species — the same generators Phase 3&apos;s eval
          corpus is scored against, run live here against the real verifier.
          Six of the taxonomy&apos;s thirteen species are shown; the other
          seven need a swapped verifier configuration this simple demo
          doesn&apos;t reproduce (their defect isn&apos;t in the wire bytes).
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {SPECIES.map((s) => (
          <button
            key={s.id}
            onClick={() => run(s.id)}
            disabled={loading}
            className={`text-left rounded-lg border px-4 py-3 transition-colors ${
              selected === s.id
                ? "border-[var(--accent-c)] bg-[var(--primary-wash)]"
                : "border-[var(--border-c)] bg-[var(--surface)] hover:bg-[var(--surface-2)]"
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

      {error && (
        <p className="text-sm text-[var(--reject)]">
          {error}. Is the verifier service running? (<code className="font-mono text-xs">uvicorn service.main:app --port 8420</code>)
        </p>
      )}

      {demo && (
        <div className="rounded-xl border border-[var(--border-c)] bg-[var(--surface)] p-4 text-sm">
          <p className="text-[var(--text-2)]">{demo.description}</p>
          <p className="text-xs text-[var(--text-3)] font-mono mt-2">
            expected: {demo.expected_decision}
            {demo.expected_check ? ` — caught at ${demo.expected_check}` : ""}
          </p>
        </div>
      )}

      {result && <VerificationResultView result={result} />}

      <div className="pt-6 border-t border-[var(--border-c)]">
        <p className="text-sm text-[var(--text-2)]">
          This picker uses precomputed presentations from the eval corpus. For
          the real thing — a browser wallet with a non-extractable key,
          WebAuthn-gated release, and a genuine cross-device presentation —
          see the PWA:
        </p>
        <div className="flex gap-3 mt-3">
          <Link href="/wallet">
            <Button variant="outline">Open the wallet</Button>
          </Link>
          <Link href="/verify-demo">
            <Button variant="outline">Open the verifier</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
