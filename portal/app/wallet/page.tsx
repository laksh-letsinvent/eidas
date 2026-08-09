"use client";

import { useEffect, useState } from "react";
import { WalletCard } from "@/components/wallet/WalletCard";
import { InstallPrompt } from "@/components/wallet/InstallPrompt";
import { KeyExportDemo } from "@/components/wallet/KeyExportDemo";
import { generateHolderKeyPair } from "@/lib/wallet/crypto";
import { loadHolderKeyPair, saveHolderKeyPair } from "@/lib/wallet/db";

export default function WalletPage() {
  const [keyPair, setKeyPair] = useState<CryptoKeyPair | null>(null);
  const [keyStatus, setKeyStatus] = useState<"loading" | "generated" | "restored">("loading");

  useEffect(() => {
    (async () => {
      const existing = await loadHolderKeyPair();
      if (existing) {
        setKeyPair(existing);
        setKeyStatus("restored");
        return;
      }
      const generated = await generateHolderKeyPair();
      await saveHolderKeyPair(generated);
      setKeyPair(generated);
      setKeyStatus("generated");
    })();
  }, []);

  return (
    <div className="max-w-2xl mx-auto px-6 py-12 space-y-4">
      <div>
        <h1
          className="text-3xl font-bold tracking-tight"
          style={{ fontFamily: "var(--font-display)", color: "var(--foreground)" }}
        >
          Wallet
        </h1>
        <p className="text-sm text-[var(--text-2)] mt-2">
          A PWA holding a PID with a non-extractable WebCrypto key, gated by
          WebAuthn, presenting over a real (if local) OpenID4VP-lite channel
          to the Lara Bank verifier from Phase 2.
        </p>
        <div className="mt-4">
          <InstallPrompt />
        </div>
      </div>

      <div className="text-xs font-mono text-[var(--text-3)]">
        {keyStatus === "loading" && "holder key: loading…"}
        {keyStatus === "generated" && "holder key: freshly generated, non-extractable, stored in IndexedDB"}
        {keyStatus === "restored" && "holder key: restored from IndexedDB"}
      </div>

      <KeyExportDemo privateKey={keyPair?.privateKey ?? null} />

      <WalletCard keyPair={keyPair} />
    </div>
  );
}
