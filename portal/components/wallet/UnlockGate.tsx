"use client";

import { Fingerprint, ShieldOff, Loader2 } from "lucide-react";

export type UnlockState = "idle" | "waiting" | "authorized" | "denied";

export function UnlockGate({ state, reason }: { state: UnlockState; reason: string | null }) {
  if (state === "idle") return null;

  return (
    <div className="flex items-center gap-2 text-xs">
      {state === "waiting" && (
        <>
          <Loader2 size={13} className="animate-spin text-[var(--text-2)]" />
          <span className="text-[var(--text-2)]">Waiting for WebAuthn gesture…</span>
        </>
      )}
      {state === "authorized" && (
        <>
          <Fingerprint size={13} className="text-[var(--accept)]" />
          <span className="text-[var(--accept)]">Release authorized</span>
        </>
      )}
      {state === "denied" && (
        <>
          <ShieldOff size={13} className="text-[var(--reject)]" />
          <span className="text-[var(--reject)]">
            Release blocked — no presentation was sent{reason ? `: ${reason}` : ""}
          </span>
        </>
      )}
    </div>
  );
}
