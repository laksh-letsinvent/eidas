import Link from "next/link";
import { Button } from "@/components/ui/button";
import { TryItLive } from "@/components/tryit/TryItLive";
import { QesRecordedStory } from "@/components/tryit/QesRecordedStory";
import { getTryitFallback } from "@/lib/tryitFallback";

export const metadata = { title: "Try It — eIDAS Wallet & QES Lab" };

export default function TryItPage() {
  const fallback = getTryitFallback();

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
          Four of the walkthrough&apos;s stories, put through the real verifier — the
          claims that travelled, the claims that stayed on the phone, and the
          eight-check ladder that decided. Then six ways the same bank story can
          go wrong on the wire, and a qualified signature with its five
          break-it experiments.
        </p>
        <p className="text-sm text-[var(--text-2)] mt-3">
          Every result here is real output, not a mock. Runs marked{" "}
          <span className="font-medium text-[var(--foreground)]">recorded</span>{" "}
          were produced by the same verifier ahead of time — the live path needs
          a local service that isn&apos;t part of this site. Clone the repo and
          the same screens run against your own wallet; see{" "}
          <Link href="/experiment" className="underline">
            The Experiment
          </Link>{" "}
          for what was built.
        </p>
      </div>

      <TryItLive fallback={fallback} />

      <QesRecordedStory />

      <div className="pt-6 border-t border-[var(--border-c)]">
        <p className="text-sm text-[var(--text-2)]">
          These stories hold a credential in this browser&apos;s own IndexedDB. For the standalone PWA — install
          prompt, key-export proof, cross-device QR presentation — see the wallet and verifier pages directly:
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
