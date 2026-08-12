import Link from "next/link";
import { SPECIES_CATALOGUE } from "@/lib/speciesCatalogue";

export function SpeciesCatalogue() {
  return (
    <div className="space-y-4">
      {SPECIES_CATALOGUE.map((s) => (
        <div key={s.id} className="rounded-xl border border-[var(--border-c)] bg-[var(--surface)] p-4">
          <div className="flex items-baseline justify-between gap-3 flex-wrap">
            <span className="font-mono text-sm text-[var(--foreground)]">{s.id}</span>
            <div className="flex items-center gap-2">
              {s.caughtAt && (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-[var(--surface-2)] text-[var(--text-2)]">
                  caught at {s.caughtAt}
                </span>
              )}
              {s.live ? (
                <Link
                  href="/try-it"
                  className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-[var(--accept-zone)] text-[var(--accept)]"
                >
                  live in Try It →
                </Link>
              ) : (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-[var(--surface-2)] text-[var(--text-3)]">
                  config-dependent
                </span>
              )}
            </div>
          </div>
          <dl className="mt-3 space-y-2 text-sm">
            <div>
              <dt className="text-[10px] uppercase tracking-wide text-[var(--text-3)]">What it is</dt>
              <dd className="text-[var(--text-2)] mt-0.5">{s.whatItIs}</dd>
            </div>
            <div>
              <dt className="text-[10px] uppercase tracking-wide text-[var(--text-3)]">What breaks</dt>
              <dd className="text-[var(--text-2)] mt-0.5">{s.whatBreaks}</dd>
            </div>
            <div>
              <dt className="text-[10px] uppercase tracking-wide text-[var(--text-3)]">What a verifier must handle</dt>
              <dd className="text-[var(--text-2)] mt-0.5">{s.verifierMustHandle}</dd>
            </div>
          </dl>
        </div>
      ))}
    </div>
  );
}
