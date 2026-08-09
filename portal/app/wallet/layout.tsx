import type { Metadata } from "next";
import { RegisterServiceWorker } from "@/components/wallet/RegisterServiceWorker";

// `manifest` here (not in the root layout) scopes installability to /wallet —
// Next resolves metadata per-route, so /, /atlas, /results etc. never link a
// manifest tag at all; only pages under this layout do.
export const metadata: Metadata = {
  title: "Wallet — eIDAS Wallet & QES Lab",
  manifest: "/manifest.json",
};

export default function WalletLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <RegisterServiceWorker />
      {children}
    </>
  );
}
