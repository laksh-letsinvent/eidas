"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import { useState, useSyncExternalStore } from "react";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import {
  Menu, Sun, Moon, Monitor,
  Map, Workflow, FlaskConical, BarChart2,
  Zap, FileText, Fingerprint,
} from "lucide-react";

const EIDAS_NAV = [
  { href: "/",           label: "How this works", icon: Workflow },
  { href: "/atlas",      label: "Atlas",          icon: Map },
  { href: "/experiment", label: "The Experiment", icon: FlaskConical },
  { href: "/try-it",     label: "Try It",         icon: Zap },
  { href: "/takeaway",   label: "Takeaway",       icon: BarChart2 },
];

const BRAND = {
  name: "eIDAS Lab",
  sub: "EUDI Wallet · QES",
  footer: "SD-JWT VC · Verifier · Eval",
  homeHref: "/",
};

function NavLinks({ pathname, onClick }: { pathname: string; onClick?: () => void }) {
  return (
    <nav className="flex flex-col gap-0.5">
      {EIDAS_NAV.map((item) => {
        const Icon = item.icon;
        const active =
          item.href === "/"
            ? pathname === "/" || pathname === ""
            : pathname.startsWith(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onClick}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
              active
                ? "bg-[var(--primary-wash)] text-[var(--accent-c)] font-semibold border border-[var(--accent-c)]/20"
                : "text-[var(--foreground)] hover:text-[var(--accent-c)] hover:bg-[var(--surface-2)] font-medium"
            }`}
          >
            <Icon size={15} className={active ? "text-[var(--accent-c)]" : "text-[var(--text-2)]"} />
            <span className="flex-1">{item.label}</span>
          </Link>
        );
      })}

      {/* Cross-links to the sibling portals */}
      <div className="mt-4 pt-3 border-t border-[var(--border-c)] flex flex-col gap-0.5">
        <a
          href="https://bio-authn.letsinvent.co.uk"
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs text-[var(--text-3)] hover:text-[var(--text-2)] hover:bg-[var(--surface-2)] transition-all"
        >
          <Fingerprint size={12} className="shrink-0" />
          <span>Face Value →</span>
        </a>
        <a
          href="https://bio-idv.letsinvent.co.uk"
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs text-[var(--text-3)] hover:text-[var(--text-2)] hover:bg-[var(--surface-2)] transition-all"
        >
          <FileText size={12} className="shrink-0" />
          <span>Hard Copy →</span>
        </a>
      </div>
    </nav>
  );
}

function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const mounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  );
  if (!mounted) return <div className="w-8 h-8" />;

  const cycle = () => {
    if (theme === "dark") setTheme("light");
    else if (theme === "light") setTheme("system");
    else setTheme("dark");
  };

  return (
    <button
      onClick={cycle}
      className="p-1.5 rounded-lg text-[var(--text-2)] hover:text-[var(--foreground)] hover:bg-[var(--surface-2)] transition-colors"
      title={`Theme: ${theme}`}
    >
      {theme === "dark" ? <Moon size={15} /> : theme === "light" ? <Sun size={15} /> : <Monitor size={15} />}
    </button>
  );
}

function SidebarContent({ pathname, onClose }: { pathname: string; onClose?: () => void }) {
  return (
    <div className="flex flex-col h-full bg-[var(--surface)] border-r border-[var(--border-c)]">
      <div className="px-5 py-5 border-b border-[var(--border-c)]">
        <Link href={BRAND.homeHref} onClick={onClose} className="block">
          <div
            className="text-xl font-bold tracking-tight leading-tight"
            style={{ fontFamily: "var(--font-display)", color: "var(--foreground)" }}
          >
            {BRAND.name}
          </div>
          <div className="text-[11px] text-[var(--accent-c)] font-medium mt-0.5">{BRAND.sub}</div>
        </Link>
      </div>

      <div className="flex-1 px-3 py-4 overflow-y-auto">
        <NavLinks pathname={pathname} onClick={onClose} />
      </div>

      <div className="px-4 py-3 border-t border-[var(--border-c)] flex items-center justify-between">
        <div className="text-[11px] text-[var(--text-2)] font-mono">{BRAND.footer}</div>
        <ThemeToggle />
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <div className="flex flex-col min-h-screen">
      <div
        className="fixed top-0 left-0 right-0 z-50 h-[3px]"
        style={{ background: "linear-gradient(90deg, var(--accent-c) 0%, var(--accent-2) 50%, var(--accept) 100%)" }}
      />

      <div className="flex flex-1 pt-[3px]">
        <aside
          className="hidden lg:flex lg:flex-col shrink-0 sticky top-[3px] h-[calc(100vh-3px)] overflow-y-auto"
          style={{ width: "var(--sidebar-w)" }}
        >
          <SidebarContent pathname={pathname} />
        </aside>

        <div className="lg:hidden fixed top-[3px] left-0 right-0 z-40 flex items-center gap-3 px-4 py-3 bg-[var(--surface)] border-b border-[var(--border-c)]">
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger className="p-1.5 rounded-lg text-[var(--text-2)] hover:text-[var(--foreground)] hover:bg-[var(--surface-2)] transition-colors">
              <Menu size={20} />
            </SheetTrigger>
            <SheetContent side="left" className="p-0 bg-[var(--surface)] border-[var(--border-c)]" style={{ width: "var(--sidebar-w)" }}>
              <SidebarContent pathname={pathname} onClose={() => setOpen(false)} />
            </SheetContent>
          </Sheet>
          <div className="flex-1 flex items-baseline gap-2">
            <span className="text-base font-bold" style={{ fontFamily: "var(--font-display)", color: "var(--foreground)" }}>
              {BRAND.name}
            </span>
            <span className="text-[11px] text-[var(--accent-c)] font-medium">{BRAND.sub}</span>
          </div>
          <ThemeToggle />
        </div>

        <main className="flex-1 min-w-0 lg:pt-0 pt-[52px]">
          <div className="min-h-screen" style={{ background: "var(--page-glow), var(--background)" }}>
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
