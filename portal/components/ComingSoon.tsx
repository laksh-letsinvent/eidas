import { Workflow, FlaskConical, BarChart2, LucideIcon } from "lucide-react";

const ICONS: Record<string, LucideIcon> = {
  workflow: Workflow,
  flask: FlaskConical,
  chart: BarChart2,
};

export function ComingSoon({
  eyebrow,
  title,
  arrives,
  icon = "workflow",
  children,
}: {
  eyebrow: string;
  title: string;
  arrives: string;
  icon?: keyof typeof ICONS;
  children: React.ReactNode;
}) {
  const Icon = ICONS[icon] ?? Workflow;
  return (
    <div className="px-6 py-10 lg:px-12 lg:py-16 max-w-3xl">
      <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--accent-c)]">
        {eyebrow}
      </div>
      <div className="flex items-center gap-3 mb-4">
        <div
          className="flex items-center justify-center w-10 h-10 rounded-xl border"
          style={{ background: "var(--primary-wash)", borderColor: "var(--accent-c)" }}
        >
          <Icon size={18} className="text-[var(--accent-c)]" />
        </div>
        <h1 className="text-2xl font-bold" style={{ fontFamily: "var(--font-display)" }}>
          {title}
        </h1>
      </div>
      <p className="text-[var(--text-2)] leading-relaxed">{children}</p>
      <div
        className="inline-block mt-6 px-3 py-1.5 rounded-full text-[12px] font-mono border"
        style={{ background: "var(--surface-2)", borderColor: "var(--border-c)", color: "var(--text-2)" }}
      >
        Arrives in {arrives}
      </div>
    </div>
  );
}
