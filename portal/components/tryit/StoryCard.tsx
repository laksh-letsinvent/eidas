export function StoryCard({
  title,
  blurb,
  tag,
  children,
}: {
  title: string;
  blurb: string;
  tag?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-[var(--border-c)] bg-[var(--surface)] p-5 space-y-4">
      <div>
        <div className="flex items-baseline justify-between gap-3">
          <h3 className="text-base font-semibold" style={{ fontFamily: "var(--font-display)" }}>
            {title}
          </h3>
          {tag && (
            <span className="text-[10px] font-mono uppercase tracking-wide text-[var(--accent-c)] shrink-0">
              {tag}
            </span>
          )}
        </div>
        <p className="text-sm text-[var(--text-2)] mt-1">{blurb}</p>
      </div>
      {children}
    </div>
  );
}
