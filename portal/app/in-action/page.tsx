import { getInActionSteps } from "@/lib/inAction";
import { VerificationResultView } from "@/components/wallet/VerificationResultView";

export const metadata = { title: "In Action — eIDAS Wallet & QES Lab" };

export default function InActionPage() {
  const steps = getInActionSteps();

  return (
    <div className="max-w-2xl mx-auto px-6 py-12 space-y-8">
      <div>
        <h1
          className="text-3xl font-bold tracking-tight"
          style={{ fontFamily: "var(--font-display)", color: "var(--foreground)" }}
        >
          In Action
        </h1>
        <p className="text-sm text-[var(--text-2)] mt-2">
          A precomputed walkthrough of the three-actor loop: issuer, wallet,
          and the Lara Bank verifier over OpenID4VP-lite. Real{" "}
          <code className="font-mono text-xs px-1 py-0.5 rounded bg-[var(--surface-2)]">VerificationResult</code>{" "}
          output from Phase 2&apos;s <code className="font-mono text-xs px-1 py-0.5 rounded bg-[var(--surface-2)]">verifier.verify.verify()</code>,
          not a mock.
        </p>
      </div>

      {steps.map((step, i) => (
        <div key={step.step_title} className="space-y-3">
          <div className="flex items-baseline gap-3">
            <span className="text-xs font-mono text-[var(--text-3)]">STEP {i + 1}</span>
            <h2 className="text-lg font-semibold" style={{ fontFamily: "var(--font-display)" }}>
              {step.step_title}
            </h2>
          </div>
          <p className="text-sm text-[var(--text-2)]">{step.narration}</p>
          <VerificationResultView result={step.result} />
        </div>
      ))}
    </div>
  );
}
