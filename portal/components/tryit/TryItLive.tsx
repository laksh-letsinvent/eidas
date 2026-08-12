"use client";

import { useLocalWallet } from "@/lib/wallet/useLocalWallet";
import { useServiceHealth } from "@/lib/wallet/useServiceHealth";
import type { TryitFallback } from "@/lib/tryitFallback";
import { GetWalletStory } from "./GetWalletStory";
import { PresentStory } from "./PresentStory";
import { SpeciesStory } from "./SpeciesStory";

const PHISHING_ORIGIN = "https://lara-bank-secure.verify-id.co";

export function TryItLive({ fallback }: { fallback: TryitFallback }) {
  const wallet = useLocalWallet();
  const health = useServiceHealth();

  return (
    <div className="space-y-4">
      <GetWalletStory wallet={wallet} health={health} fallback={fallback.wallet} />

      <PresentStory
        wallet={wallet}
        health={health}
        fallback={fallback.bank}
        title="Open a bank account"
        blurb="Lara Bank's registered claim set — age_over_18 and nationality — requested and revealed, nothing else."
        tag="11 minutes → 40 seconds"
        actionLabel="Present to Lara Bank"
        buildPresentRequest={(base) => base}
        interpret={() => "Two claims travelled. Everything else in the PID stayed on the phone."}
      />

      <PresentStory
        wallet={wallet}
        health={health}
        fallback={fallback.age}
        title="Prove you are over 18"
        blurb="Same wallet, same verifier — but the request asks for one claim instead of two. Watch the disclosed list shrink and the verifier still accept."
        tag="The magic trick"
        actionLabel="Present just age_over_18"
        buildPresentRequest={(base) => ({
          ...base,
          query: { ...base.query, required_claims: ["age_over_18"] },
        })}
        interpret={(result) =>
          result.decision === "accept"
            ? "One claim travelled instead of two — proof without the extra disclosure, and registration_purpose still passes because it's a subset of what Lara Bank is registered to ask for."
            : "Unexpected reject — this would be a real verifier bug."
        }
      />

      <PresentStory
        wallet={wallet}
        health={health}
        fallback={fallback.phish}
        title="A scammer tries it on"
        blurb={`The wallet is told it's presenting to "${PHISHING_ORIGIN}" — a phishing relay. That KB-JWT is bound to the wrong audience, then forwarded to the real Lara Bank verifier anyway.`}
        tag="The bit nobody demos"
        actionLabel="Run the phishing relay"
        buildPresentRequest={(base) => ({ ...base, verifier_id: PHISHING_ORIGIN })}
        buildVerifyRequest={(base) => base}
        interpret={(result) =>
          result.decision === "reject"
            ? "Caught: the KB-JWT was bound to the phishing origin, not the real verifier — key_binding correctly rejects it."
            : "Unexpected accept — this would be a real verifier bug."
        }
      />

      <SpeciesStory health={health} fallback={fallback.species} />
    </div>
  );
}
