"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StoryCard } from "./StoryCard";
import { UnlockGate, type UnlockState } from "@/components/wallet/UnlockGate";
import { VerificationResultView, type VerificationResult } from "@/components/wallet/VerificationResultView";
import { fetchAuthorizationRequest, postVerify } from "@/lib/wallet/api";
import { presentWithUnlock } from "@/lib/wallet/presentFlow";
import type { useLocalWallet } from "@/lib/wallet/useLocalWallet";
import type { ServiceHealth } from "@/lib/wallet/useServiceHealth";
import type { AuthorizationRequest } from "@/lib/wallet/request";

export function PresentStory({
  wallet,
  health,
  fallback,
  title,
  blurb,
  tag,
  actionLabel,
  buildPresentRequest,
  buildVerifyRequest,
  interpret,
}: {
  wallet: ReturnType<typeof useLocalWallet>;
  health: ServiceHealth;
  fallback: { presentation: string; result: VerificationResult };
  title: string;
  blurb: string;
  tag: string;
  actionLabel: string;
  /** Transforms the fresh request into what's used to build the presentation
   * (the claims revealed, the audience the KB-JWT binds to). */
  buildPresentRequest: (base: AuthorizationRequest) => AuthorizationRequest;
  /** Transforms the fresh request into what's used to verify — identical to
   * buildPresentRequest except for the phishing story, where the relay
   * forwards to the *real* verifier_id regardless of what the wallet saw. */
  buildVerifyRequest?: (base: AuthorizationRequest) => AuthorizationRequest;
  interpret?: (result: VerificationResult) => string;
}) {
  const { keyPair, credential } = wallet;
  const [presenting, setPresenting] = useState(false);
  const [unlockState, setUnlockState] = useState<UnlockState>("idle");
  const [unlockReason, setUnlockReason] = useState<string | null>(null);
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [presentation, setPresentation] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    if (!keyPair || !credential?.webauthnCredentialId) return;
    setPresenting(true);
    setError(null);
    setResult(null);
    setUnlockReason(null);
    try {
      const base = await fetchAuthorizationRequest();
      const presentRequest = buildPresentRequest(base);
      const verifyRequest = buildVerifyRequest ? buildVerifyRequest(base) : presentRequest;

      setUnlockState("waiting");
      const outcome = await presentWithUnlock(keyPair, credential, presentRequest);
      if (!outcome.authorized) {
        setUnlockState("denied");
        setUnlockReason(outcome.reason);
        return;
      }
      setUnlockState("authorized");
      setPresentation(outcome.presentation);

      const verificationResult = await postVerify(outcome.presentation, verifyRequest);
      setResult(verificationResult as unknown as VerificationResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setPresenting(false);
    }
  }

  const ready = !!(credential?.webauthnCredentialId && keyPair);

  if (health === "down" && !result) {
    return (
      <StoryCard title={title} blurb={blurb} tag={tag}>
        <p className="text-[10px] uppercase tracking-wide text-[var(--text-3)] mb-1">
          Recorded run — local verifier service not detected
        </p>
        <VerificationResultView result={fallback.result} presentation={fallback.presentation} />
        {interpret && <p className="text-xs text-[var(--text-2)]">{interpret(fallback.result)}</p>}
      </StoryCard>
    );
  }

  return (
    <StoryCard title={title} blurb={blurb} tag={tag}>
      {health === "checking" && !result ? (
        <p className="text-xs text-[var(--text-3)]">Checking for the local verifier service…</p>
      ) : !ready ? (
        <p className="text-xs text-[var(--text-3)]">Get your wallet first — this story presents from it.</p>
      ) : (
        <div className="flex items-center justify-between gap-4">
          <UnlockGate state={unlockState} reason={unlockReason} />
          <Button size="sm" disabled={presenting} onClick={run} className="ml-auto shrink-0">
            {presenting ? <Loader2 size={14} className="animate-spin" /> : actionLabel}
          </Button>
        </div>
      )}

      {error && <p className="text-xs text-[var(--reject)]">{error}.</p>}

      {result && (
        <div className="space-y-2">
          <VerificationResultView result={result} presentation={presentation ?? undefined} />
          {interpret && <p className="text-xs text-[var(--text-2)]">{interpret(result)}</p>}
        </div>
      )}
    </StoryCard>
  );
}
