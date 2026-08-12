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
          Four of the walkthrough&apos;s stories, run live against the real verifier in{" "}
          <code className="font-mono text-xs px-1 py-0.5 rounded bg-[var(--surface-2)]">service/</code> — a genuine
          non-extractable browser key, a real WebAuthn gate, the real eight-check ladder. Then six defect species
          broken live inside the same bank story, and a recorded QES run. Needs{" "}
          <code className="font-mono text-xs px-1 py-0.5 rounded bg-[var(--surface-2)]">
            uvicorn service.main:app --port 8420
          </code>{" "}
          running locally — see{" "}
          <Link href="/experiment" className="underline">
            The Experiment
          </Link>{" "}
          for what falls back when it isn&apos;t.
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
