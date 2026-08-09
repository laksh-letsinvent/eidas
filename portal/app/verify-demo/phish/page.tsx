"use client";

import { useEffect, useRef, useState } from "react";
import QRCode from "qrcode";
import { Button } from "@/components/ui/button";
import { VerificationResultView, type VerificationResult } from "@/components/wallet/VerificationResultView";
import { fetchAuthorizationRequest, postVerify, pollPresentation } from "@/lib/wallet/api";
import { b64urlEncode, utf8ToBytes } from "@/lib/wallet/base64url";
import type { AuthorizationRequest } from "@/lib/wallet/request";

const PHISHING_ORIGIN = "https://phishing-relay.example";
const POLL_INTERVAL_MS = 1500;

/**
 * cross_device_origin_phish, live: a relaying attacker sits between the
 * QR and the wallet. The wallet is shown a request that names the
 * *phishing* origin as `verifier_id` — its KB-JWT's `aud` binds to whatever
 * it was told, that's the whole design of holder binding. The relay then
 * forwards the resulting presentation to the *real* Lara Bank verifier,
 * hoping it passes. It doesn't: /verify checks the KB-JWT's aud against
 * the real request's own verifier_id, and they don't match — the same
 * key_binding check, the same mechanism as the Python `wrong_audience_kb_jwt`
 * / `cross_device_origin_phish` species (eval/species.py).
 */
export default function PhishDemoPage() {
  const [realRequest, setRealRequest] = useState<AuthorizationRequest | null>(null);
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "waiting" | "verifying" | "done">("idle");
  const [result, setResult] = useState<VerificationResult | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  async function startPhish() {
    setStatus("waiting");
    setResult(null);

    // The real request the verifier actually issued.
    const real = await fetchAuthorizationRequest();
    setRealRequest(real);

    // What the phishing relay shows the wallet instead: same nonce (so the
    // relay's timing lines up), but its OWN identity as verifier_id.
    const phishing: AuthorizationRequest = { ...real, verifier_id: PHISHING_ORIGIN };
    const encoded = b64urlEncode(utf8ToBytes(JSON.stringify(phishing)));
    const scanUrl = `${window.location.origin}/wallet/present?req=${encoded}`;
    setQrDataUrl(await QRCode.toDataURL(scanUrl, { margin: 1, width: 240 }));

    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      const presentation = await pollPresentation(real.nonce);
      if (presentation) {
        if (pollRef.current) clearInterval(pollRef.current);
        setStatus("verifying");
        // The relay forwards the presentation to the REAL verifier — using
        // the real request (real verifier_id), which is what a genuine
        // relying party actually checks against.
        const verificationResult = await postVerify(presentation, real);
        setResult(verificationResult as unknown as VerificationResult);
        setStatus("done");
      }
    }, POLL_INTERVAL_MS);
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-12 space-y-6">
      <div>
        <h1
          className="text-3xl font-bold tracking-tight"
          style={{ fontFamily: "var(--font-display)", color: "var(--foreground)" }}
        >
          cross_device_origin_phish — live demo
        </h1>
        <p className="text-sm text-[var(--text-2)] mt-2">
          The QR below asks the wallet to present to <span className="font-mono">{PHISHING_ORIGIN}</span>,
          not the real Lara Bank verifier — then this page relays the
          resulting presentation to the real one anyway. Watch{" "}
          <span className="font-mono">key_binding</span> catch the mismatch.
        </p>
      </div>

      {status === "idle" && <Button onClick={startPhish}>Start the phishing relay</Button>}

      {(status === "waiting" || status === "verifying") && qrDataUrl && (
        <div className="rounded-xl border border-[var(--border-c)] bg-[var(--surface)] p-6 flex flex-col items-center gap-4">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={qrDataUrl} alt="Scan with the wallet" width={240} height={240} />
          <p className="text-xs text-[var(--text-2)] font-mono break-all">
            wallet is told verifier_id: {PHISHING_ORIGIN}
          </p>
          <p className="text-xs text-[var(--text-2)] font-mono break-all">
            real verifier_id: {realRequest?.verifier_id}
          </p>
          <p className="text-sm text-[var(--text-2)]">
            {status === "waiting" ? "Waiting for the wallet to present…" : "Relaying to the real verifier…"}
          </p>
        </div>
      )}

      {status === "done" && result && (
        <div className="space-y-4">
          <VerificationResultView result={result} />
          <p className="text-xs text-[var(--text-2)]">
            {result.decision === "reject"
              ? "Caught: the KB-JWT was bound to the phishing origin, not the real verifier — key_binding correctly rejects it."
              : "Unexpected accept — this would be a real verifier bug."}
          </p>
          <Button variant="outline" onClick={startPhish}>
            Run again
          </Button>
        </div>
      )}
    </div>
  );
}
