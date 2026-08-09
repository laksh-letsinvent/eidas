"use client";

import { useState } from "react";
import { ShieldCheck, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { attemptExportPrivateKey } from "@/lib/wallet/crypto";

export function KeyExportDemo({ privateKey }: { privateKey: CryptoKey | null }) {
  const [result, setResult] = useState<{ succeeded: boolean; error: string | null } | null>(null);
  const [running, setRunning] = useState(false);

  if (!privateKey) return null;

  return (
    <div className="rounded-xl border border-[var(--border-c)] bg-[var(--surface)] p-4">
      <p className="text-sm text-[var(--text-2)] mb-3">
        The holder key was generated with{" "}
        <code className="font-mono text-xs px-1 py-0.5 rounded bg-[var(--surface-2)]">extractable: false</code>.
        Try to export it anyway:
      </p>
      <Button
        size="sm"
        variant="outline"
        disabled={running}
        onClick={async () => {
          setRunning(true);
          setResult(await attemptExportPrivateKey(privateKey));
          setRunning(false);
        }}
      >
        Attempt to export the holder key
      </Button>
      {result && (
        <div
          className={`mt-3 flex items-start gap-2 text-xs rounded-lg p-3 ${
            result.succeeded
              ? "bg-[var(--reject-zone)] text-[var(--reject)]"
              : "bg-[var(--accept-zone)] text-[var(--accept)]"
          }`}
        >
          {result.succeeded ? (
            <ShieldAlert size={14} className="shrink-0 mt-0.5" />
          ) : (
            <ShieldCheck size={14} className="shrink-0 mt-0.5" />
          )}
          <div>
            {result.succeeded ? (
              <span>Export succeeded — this would be a bug. Key material must never leave the browser&apos;s WebCrypto keystore.</span>
            ) : (
              <span>
                Export failed, by design: <span className="font-mono">{result.error}</span>. The
                private key can be used to sign but never read.
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
