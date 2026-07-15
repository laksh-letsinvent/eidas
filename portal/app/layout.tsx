import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/ThemeProvider";
import { AppShell } from "@/components/AppShell";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

const BASE_URL = "https://eidas.letsinvent.co.uk";

export const metadata: Metadata = {
  title: "eIDAS Wallet & QES Lab",
  description:
    "A build-first study of the EUDI Wallet, eIDAS 2.0, and qualified signatures — treating the relying-party verifier as an evaluable surface. Part of the letsinvent identity series.",
  metadataBase: new URL(BASE_URL),
  openGraph: {
    type: "website",
    url: BASE_URL,
    siteName: "eIDAS Wallet & QES Lab",
    title: "eIDAS Wallet & QES Lab",
    description:
      "EUDI Wallet · eIDAS 2.0 · QES. The relying-party verifier as an evaluable surface — hand-rolled, then attacked.",
  },
  twitter: {
    card: "summary_large_image",
    title: "eIDAS Wallet & QES Lab",
    description:
      "EUDI Wallet · eIDAS 2.0 · QES. The relying-party verifier as an evaluable surface.",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${inter.variable} h-full`}
      data-brand="eidas"
      suppressHydrationWarning
    >
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="h-full antialiased">
        <ThemeProvider>
          <AppShell>{children}</AppShell>
        </ThemeProvider>
      </body>
    </html>
  );
}
