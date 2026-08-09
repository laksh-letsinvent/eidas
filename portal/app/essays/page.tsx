import Link from "next/link";
import { ESSAYS } from "@/lib/essays";

export const dynamic = "force-static";
export const metadata = { title: "Essays — eIDAS Wallet & QES Lab" };

export default function EssaysIndexPage() {
  return (
    <div className="max-w-2xl mx-auto px-6 py-12 space-y-8">
      <div>
        <h1
          className="text-3xl font-bold tracking-tight"
          style={{ fontFamily: "var(--font-display)", color: "var(--foreground)" }}
        >
          Essays
        </h1>
        <p className="text-sm text-[var(--text-2)] mt-2">
          Long-form write-ups off the back of the build — the eval discipline,
          the red-team&apos;s flagship finding, and the agentic-QES question
          Phase 4 makes concrete.
        </p>
      </div>

      <div className="space-y-4">
        {ESSAYS.map((essay) => (
          <Link
            key={essay.slug}
            href={`/essays/${essay.slug}`}
            className="block rounded-xl border border-[var(--border-c)] bg-[var(--surface)] p-5 hover:border-[var(--accent-c)] transition-colors"
          >
            <h2 className="text-lg font-semibold text-[var(--foreground)]" style={{ fontFamily: "var(--font-display)" }}>
              {essay.title}
            </h2>
            <p className="text-sm text-[var(--text-2)] mt-1.5">{essay.dek}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
