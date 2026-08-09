"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { UnlockGate, type UnlockState } from "@/components/wallet/UnlockGate";
import { presentWithUnlock } from "@/lib/wallet/presentFlow";
import { submitPresentation } from "@/lib/wallet/api";
import { b64urlDecode, bytesToUtf8 } from "@/lib/wallet/base64url";
import { loadCredential, loadHolderKeyPair, type StoredCredential } from "@/lib/wallet/db";
import type { AuthorizationRequest } from "@/lib/wallet/request";

/** Decoding `?req=` is a pure derivation of the URL, not a side effect —
 * `useMemo` instead of `useEffect`+`setState` avoids the extra render pass
 * `setState`-in-effect causes. */
function parseRequestParam(encoded: string | null): { request: AuthorizationRequest | null; error: string | null } {
  if (!encoded) {
    return { request: null, error: "no ?req= parameter — this page expects the URL a verifier's QR encodes" };
  }
  try {
    return { request: JSON.parse(bytesToUtf8(b64urlDecode(encoded))) as AuthorizationRequest, error: null };
  } catch {
    return { request: null, error: "could not decode the request parameter" };
  }
}

function PresentInner() {
  const searchParams = useSearchParams();
  const { request, error: parseError } = useMemo(
    () => parseRequestParam(searchParams.get("req")),
    [searchParams]
  );
  const [keyPair, setKeyPair] = useState<CryptoKeyPair | null>(null);
  const [credential, setCredential] = useState<StoredCredential | null>(null);
  const [walletLoaded, setWalletLoaded] = useState(false);
  const [unlockState, setUnlockState] = useState<UnlockState>("idle");
  const [unlockReason, setUnlockReason] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setKeyPair((await loadHolderKeyPair()) ?? null);
      setCredential((await loadCredential()) ?? null);
      setWalletLoaded(true);
    })();
  }, []);

  async function presentNow() {
    if (!keyPair || !credential || !request) return;
    setError(null);
    setUnlockState("waiting");
    try {
      const outcome = await presentWithUnlock(keyPair, credential, request);
      if (!outcome.authorized) {
        setUnlockState("denied");
        setUnlockReason(outcome.reason);
        return;
      }
      setUnlockState("authorized");
      await submitPresentation(request.nonce, outcome.presentation);
      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  if (parseError) {
    return <p className="text-sm text-[var(--reject)]">{parseError}</p>;
  }
  if (!request || !walletLoaded) {
    return (
      <p className="text-sm text-[var(--text-2)] flex items-center gap-2">
        <Loader2 size={14} className="animate-spin" /> Loading…
      </p>
    );
  }
  if (!keyPair || !credential) {
    return <p className="text-sm text-[var(--text-2)]">This wallet doesn&apos;t hold a credential yet — visit /wallet first.</p>;
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-[var(--border-c)] bg-[var(--surface)] p-4 text-xs font-mono text-[var(--text-2)]">
        <p>verifier: {request.verifier_id}</p>
        <p>nonce: {request.nonce}</p>
        <p>requested claims: {request.query.required_claims.join(", ")}</p>
      </div>

      {!submitted && (
        <Button onClick={presentNow} disabled={unlockState === "waiting"}>
          {unlockState === "waiting" ? <Loader2 size={14} className="animate-spin" /> : "Present"}
        </Button>
      )}
      <UnlockGate state={unlockState} reason={unlockReason} />
      {error && <p className="text-xs text-[var(--reject)]">{error}</p>}
      {submitted && <p className="text-sm text-[var(--accept)]">Presentation sent — check the verifier tab.</p>}
    </div>
  );
}

export default function WalletPresentPage() {
  return (
    <div className="max-w-2xl mx-auto px-6 py-12 space-y-6">
      <div>
        <h1
          className="text-3xl font-bold tracking-tight"
          style={{ fontFamily: "var(--font-display)", color: "var(--foreground)" }}
        >
          Present (scanned)
        </h1>
        <p className="text-sm text-[var(--text-2)] mt-2">
          This is what a QR scan lands on — the request came from another
          tab/device, decoded from the URL rather than a same-tab fetch.
        </p>
      </div>
      <Suspense fallback={<p className="text-sm text-[var(--text-2)]">Loading…</p>}>
        <PresentInner />
      </Suspense>
    </div>
  );
}
