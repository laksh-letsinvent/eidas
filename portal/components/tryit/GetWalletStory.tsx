"use client";

import { CreditCard, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StoryCard } from "./StoryCard";
import type { useLocalWallet } from "@/lib/wallet/useLocalWallet";
import type { ServiceHealth } from "@/lib/wallet/useServiceHealth";
import type { TryitFallback } from "@/lib/tryitFallback";

export function GetWalletStory({
  wallet,
  health,
  fallback,
}: {
  wallet: ReturnType<typeof useLocalWallet>;
  health: ServiceHealth;
  fallback: TryitFallback["wallet"];
}) {
  const { keyPair, credential, status, error, getPid } = wallet;
  const disclosureCount = credential ? credential.credentialCompact.split("~").length - 2 : 0;

  // Local wallet state (held in this browser's own IndexedDB) always wins
  // over the fallback once it's known — a visitor who already holds a
  // credential should see it regardless of the service check's outcome.
  const showLive = status === "held" || health !== "down";

  return (
    <StoryCard
      title="Get your wallet"
      blurb="One PID, issued once, held in a non-extractable WebCrypto key. Every other story on this page presents from it."
      tag="Once, then never again"
    >
      {!showLive ? (
        <div className="flex items-start gap-3">
          <CreditCard size={20} className="text-[var(--text-3)] shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-[var(--foreground)]">PID held (recorded)</p>
            <p className="text-xs text-[var(--text-2)] mt-1">
              vct: <span className="font-mono">{fallback.vct}</span> · {fallback.disclosable_claim_count}{" "}
              disclosable claims · local verifier service not detected, showing a recorded example
            </p>
          </div>
        </div>
      ) : (
        <>
          {status === "loading" && <p className="text-sm text-[var(--text-2)]">Checking for a held credential…</p>}

          {status === "empty" && (
            <div className="flex items-center justify-between gap-4">
              <p className="text-sm text-[var(--text-2)]">No credential held yet.</p>
              <Button size="sm" disabled={!keyPair} onClick={getPid}>
                Get PID
              </Button>
            </div>
          )}

          {status === "issuing" && (
            <p className="text-sm text-[var(--text-2)] flex items-center gap-2">
              <Loader2 size={14} className="animate-spin" /> Requesting a PID, then registering a WebAuthn unlock
              gesture…
            </p>
          )}

          {status === "held" && credential && (
            <div className="flex items-start gap-3">
              <CreditCard size={20} className="text-[var(--accent-c)] shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-[var(--foreground)]">PID held</p>
                <p className="text-xs text-[var(--text-2)] mt-1">
                  vct: <span className="font-mono">{credential.vct}</span> · {disclosureCount} disclosable claims ·
                  non-extractable P-256 key in IndexedDB
                </p>
              </div>
            </div>
          )}

          {status === "error" && (
            <div className="text-sm text-[var(--reject)]">
              Issuance failed: {error}
              <div className="mt-2">
                <Button size="sm" variant="outline" onClick={getPid}>
                  Retry
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </StoryCard>
  );
}
