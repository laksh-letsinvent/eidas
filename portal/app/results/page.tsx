import { ComingSoon } from "@/components/ComingSoon";

export const metadata = { title: "Results — eIDAS Wallet & QES Lab" };

export default function ResultsPage() {
  return (
    <ComingSoon eyebrow="Results" title="The verifier conformance matrix" arrives="Phase 3" icon="chart">
      A per-defect-species confusion matrix — the APCER/BPCER analogue for
      credential verification — plus the AI red-team run: where the deterministic
      crypto core holds, and where the policy layer leaks.
    </ComingSoon>
  );
}
