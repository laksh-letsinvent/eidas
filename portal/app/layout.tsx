import type { Metadata } from "next";
import Nav from "@/components/Nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "eIDAS Wallet & QES Lab",
  description:
    "A build-first study of the EUDI Wallet, eIDAS 2.0, and qualified signatures — the relying-party verifier as an evaluable surface.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Nav />
        <main className="page">{children}</main>
        <footer className="foot">
          <span>eIDAS Wallet &amp; QES Lab</span>
          <span>Part of the letsinvent identity series · Face Value · Hard Copy</span>
        </footer>
      </body>
    </html>
  );
}
