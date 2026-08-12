"use client";

import { useEffect, useState } from "react";
import { CreditCard, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { fetchCredentialOffer, fetchCredential, fetchAuthorizationRequest, postVerify } from "@/lib/wallet/api";
import { generateKeyProof } from "@/lib/wallet/vci";
import { registerUnlockCredential } from "@/lib/wallet/unlock";
import { presentWithUnlock } from "@/lib/wallet/presentFlow";
import { loadCredential, saveCredential, type StoredCredential } from "@/lib/wallet/db";
import { VerificationResultView, type VerificationResult } from "@/components/wallet/VerificationResultView";
import { UnlockGate, type UnlockState } from "@/components/wallet/UnlockGate";
import type { AuthorizationRequest } from "@/lib/wallet/request";

export function WalletCard({ keyPair }: { keyPair: CryptoKeyPair | null }) {
  const [credential, setCredential] = useState<StoredCredential | null>(null);
  const [status, setStatus] = useState<"loading" | "empty" | "issuing" | "held" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [presenting, setPresenting] = useState(false);
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [presentation, setPresentation] = useState<string | null>(null);
  const [presentError, setPresentError] = useState<string | null>(null);
  const [unlockState, setUnlockState] = useState<UnlockState>("idle");
  const [unlockReason, setUnlockReason] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const existing = await loadCredential();
      if (existing) {
        setCredential(existing);
        setStatus("held");
      } else {
        setStatus("empty");
      }
    })();
  }, []);

  async function getPid() {
    if (!keyPair) return;
    setStatus("issuing");
    setError(null);
    try {
      const offer = await fetchCredentialOffer();
      const now = Math.floor(Date.now() / 1000);
      const proofJwt = await generateKeyProof(offer, keyPair, now);
      const { credential: credentialCompact } = await fetchCredential(offer.offer_id, proofJwt);
      // WebAuthn registration happens once, right when the PID is first
      // received — every later presentation challenges this same credential.
      const webauthnCredentialId = await registerUnlockCredential("wallet-holder");
      const record: StoredCredential = { credentialCompact, vct: offer.vct, webauthnCredentialId };
      await saveCredential(record);
      setCredential(record);
      setStatus("held");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("error");
    }
  }

  const disclosureCount = credential ? credential.credentialCompact.split("~").length - 2 : 0;

  async function presentToVerifier() {
    if (!keyPair || !credential?.webauthnCredentialId) return;
    setPresenting(true);
    setResult(null);
    setPresentError(null);
    setUnlockReason(null);
    try {
      const request: AuthorizationRequest = await fetchAuthorizationRequest();

      setUnlockState("waiting");
      const outcome = await presentWithUnlock(keyPair, credential, request);
      if (!outcome.authorized) {
        setUnlockState("denied");
        setUnlockReason(outcome.reason);
        return;
      }
      setUnlockState("authorized");
      setPresentation(outcome.presentation);

      const verificationResult = await postVerify(outcome.presentation, request);
      setResult(verificationResult as unknown as VerificationResult);
    } catch (err) {
      setPresentError(err instanceof Error ? err.message : String(err));
    } finally {
      setPresenting(false);
    }
  }

  return (
    <div className="rounded-xl border border-[var(--border-c)] bg-[var(--surface)] p-6">
      {status === "loading" && <p className="text-sm text-[var(--text-2)]">Checking wallet…</p>}

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
          <Loader2 size={14} className="animate-spin" /> Requesting a PID from the issuer…
        </p>
      )}

      {status === "held" && credential && (
        <div className="space-y-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <CreditCard size={20} className="text-[var(--accent-c)] shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-[var(--foreground)]">PID held</p>
                <p className="text-xs text-[var(--text-2)] mt-1">
                  vct: <span className="font-mono">{credential.vct}</span> · {disclosureCount} disclosable claims
                </p>
              </div>
            </div>
            <Button size="sm" disabled={presenting || !credential.webauthnCredentialId} onClick={presentToVerifier}>
              {presenting ? <Loader2 size={14} className="animate-spin" /> : "Present to Lara Bank"}
            </Button>
          </div>
          <UnlockGate state={unlockState} reason={unlockReason} />
          {presentError && <p className="text-xs text-[var(--reject)]">Presentation failed: {presentError}</p>}
          {result && <VerificationResultView result={result} presentation={presentation ?? undefined} />}
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
    </div>
  );
}
