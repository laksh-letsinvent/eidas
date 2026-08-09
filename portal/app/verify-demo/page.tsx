"use client";

import { useEffect, useRef, useState } from "react";
import QRCode from "qrcode";
import { Button } from "@/components/ui/button";
import { VerificationResultView, type VerificationResult } from "@/components/wallet/VerificationResultView";
import { fetchAuthorizationRequest, postVerify, pollPresentation } from "@/lib/wallet/api";
import { b64urlEncode, utf8ToBytes } from "@/lib/wallet/base64url";
import type { AuthorizationRequest } from "@/lib/wallet/request";

const POLL_INTERVAL_MS = 1500;

export default function VerifyDemoPage() {
  const [request, setRequest] = useState<AuthorizationRequest | null>(null);
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "waiting" | "verifying" | "done">("idle");
  const [result, setResult] = useState<VerificationResult | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  async function startRequest() {
    setStatus("waiting");
    setResult(null);
    const req = await fetchAuthorizationRequest();
    setRequest(req);

    const encoded = b64urlEncode(utf8ToBytes(JSON.stringify(req)));
    const scanUrl = `${window.location.origin}/wallet/present?req=${encoded}`;
    setQrDataUrl(await QRCode.toDataURL(scanUrl, { margin: 1, width: 240 }));

    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      const presentation = await pollPresentation(req.nonce);
      if (presentation) {
        if (pollRef.current) clearInterval(pollRef.current);
        setStatus("verifying");
        const verificationResult = await postVerify(presentation, req);
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
          Lara Bank — verify a wallet presentation
        </h1>
        <p className="text-sm text-[var(--text-2)] mt-2">
          Renders a live authorization request as a QR. Scan it with the
          wallet (or open the encoded link in another tab) to present
          cross-device — the same OpenID4VP-lite request/response, just
          relayed through the FastAPI service instead of a same-tab call.
        </p>
      </div>

      {status === "idle" && (
        <Button onClick={startRequest}>Request a presentation</Button>
      )}

      {(status === "waiting" || status === "verifying") && qrDataUrl && (
        <div className="rounded-xl border border-[var(--border-c)] bg-[var(--surface)] p-6 flex flex-col items-center gap-4">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={qrDataUrl} alt="Scan with the wallet" width={240} height={240} />
          <p className="text-xs text-[var(--text-2)] font-mono break-all">nonce: {request?.nonce}</p>
          <p className="text-sm text-[var(--text-2)]">
            {status === "waiting" ? "Waiting for the wallet to present…" : "Verifying…"}
          </p>
        </div>
      )}

      {status === "done" && result && (
        <div className="space-y-4">
          <VerificationResultView result={result} />
          <Button variant="outline" onClick={startRequest}>
            Request another presentation
          </Button>
        </div>
      )}
    </div>
  );
}
