import { MarkdownDoc } from "@/components/MarkdownDoc";
import { SpeciesCatalogue } from "@/components/SpeciesCatalogue";
import { getExperiment, getAttestationWall } from "@/lib/experiment";

export const dynamic = "force-static";
export const metadata = { title: "The Experiment — eIDAS Wallet & QES Lab" };

function Divider() {
  return (
    <div className="px-6 lg:px-12 max-w-5xl">
      <div className="border-t border-[var(--border-c)]" />
    </div>
  );
}

export default function ExperimentPage() {
  return (
    <div>
      <div className="px-6 pt-10 lg:px-12 lg:pt-12 max-w-5xl">
        <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--accent-c)]">
          The Experiment
        </div>
        <h1
          className="text-3xl font-bold tracking-tight"
          style={{ fontFamily: "var(--font-display)", color: "var(--foreground)" }}
        >
          A verifier, and a way to measure it
        </h1>
        <p className="text-sm text-[var(--text-2)] mt-3 max-w-2xl">
          The walkthrough shows what the EUDI Wallet feels like. This page is
          what was built underneath it, and why — a wallet running on real
          browser primitives, and a labelled corpus of the ways a presentation
          can lie.
        </p>
      </div>

      <MarkdownDoc content={getExperiment()} />

      <Divider />

      <div className="px-6 pt-10 lg:px-12 lg:pt-12 max-w-5xl">
        <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--accent-c)]">
          What was built · the wallet
        </div>
        <h2
          className="text-2xl font-bold tracking-tight"
          style={{ fontFamily: "var(--font-display)", color: "var(--foreground)" }}
        >
          The attestation wall
        </h2>
        <p className="text-sm text-[var(--text-2)] mt-3 max-w-2xl">
          A wallet you can install from this site, holding a non-extractable
          key and gated by your device&apos;s own biometrics. It is still not
          an EUDI Wallet Unit, and the exact point where it stops being one is
          the lesson.
        </p>
      </div>

      <MarkdownDoc content={getAttestationWall()} />

      <Divider />

      <div className="px-6 py-10 lg:px-12 lg:py-12 max-w-5xl">
        <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--accent-c)]">
          What was built · the defects
        </div>
        <h2
          className="text-2xl font-bold tracking-tight"
          style={{ fontFamily: "var(--font-display)", color: "var(--foreground)" }}
        >
          Thirteen defect species
        </h2>
        <p className="text-sm text-[var(--text-2)] mt-3 mb-6 max-w-2xl">
          One row per way a presentation can be wrong, each labelled with the
          check that should catch it. Six break the wire bytes themselves and
          run live in Try It. The other seven need a different verifier
          configuration — another trust list, registration scope, or status
          entry — than the single fixed instance Try It runs against.
        </p>
        <SpeciesCatalogue />
      </div>
    </div>
  );
}
