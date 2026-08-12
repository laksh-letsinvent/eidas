"use client";

// Shared browser-wallet state for Try It's live stories (BUILD_PROMPT_PHASE7-9.md
// 8b) — the exact same primitives WalletCard.tsx already uses (crypto.ts's
// non-extractable key, db.ts's IndexedDB store, api.ts's /credential-offer +
// /issue, unlock.ts's WebAuthn registration), lifted into a hook so several
// story cards on one page can share one held credential instead of each
// re-deriving its own. No new verifier logic, no new endpoints.

import { useCallback, useEffect, useState } from "react";
import { generateHolderKeyPair } from "./crypto";
import { loadHolderKeyPair, saveHolderKeyPair, loadCredential, saveCredential, type StoredCredential } from "./db";
import { fetchCredentialOffer, fetchCredential } from "./api";
import { generateKeyProof } from "./vci";
import { registerUnlockCredential } from "./unlock";

export type LocalWalletStatus = "loading" | "empty" | "issuing" | "held" | "error";

export function useLocalWallet() {
  const [keyPair, setKeyPair] = useState<CryptoKeyPair | null>(null);
  const [credential, setCredential] = useState<StoredCredential | null>(null);
  const [status, setStatus] = useState<LocalWalletStatus>("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      let kp = await loadHolderKeyPair();
      if (!kp) {
        kp = await generateHolderKeyPair();
        await saveHolderKeyPair(kp);
      }
      setKeyPair(kp);
      const existing = await loadCredential();
      if (existing) {
        setCredential(existing);
        setStatus("held");
      } else {
        setStatus("empty");
      }
    })();
  }, []);

  const getPid = useCallback(async () => {
    if (!keyPair) return;
    setStatus("issuing");
    setError(null);
    try {
      const offer = await fetchCredentialOffer();
      const now = Math.floor(Date.now() / 1000);
      const proofJwt = await generateKeyProof(offer, keyPair, now);
      const { credential: credentialCompact } = await fetchCredential(offer.offer_id, proofJwt);
      // WebAuthn gesture — cannot be browser-automated; see CLAUDE.md.
      const webauthnCredentialId = await registerUnlockCredential("wallet-holder");
      const record: StoredCredential = { credentialCompact, vct: offer.vct, webauthnCredentialId };
      await saveCredential(record);
      setCredential(record);
      setStatus("held");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("error");
    }
  }, [keyPair]);

  return { keyPair, credential, status, error, getPid };
}
