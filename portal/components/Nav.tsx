import Link from "next/link";

const links = [
  { href: "/", label: "The Experiment" },
  { href: "/atlas/", label: "Atlas" },
  { href: "/in-action/", label: "In Action" },
  { href: "/try-it/", label: "Try It" },
  { href: "/results/", label: "Results" },
];

export default function Nav() {
  return (
    <header className="nav">
      <div className="nav-inner">
        <Link href="/" className="brand">
          <span className="brand-mark">eIDAS</span>
          <span className="brand-sub">Wallet &amp; QES Lab</span>
        </Link>
        <nav className="nav-links">
          {links.map((l) => (
            <Link key={l.href} href={l.href}>
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
