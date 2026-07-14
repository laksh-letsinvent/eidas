import ComingSoon from "@/components/ComingSoon";

export const metadata = { title: "Try It — eIDAS Wallet & QES Lab" };

export default function TryItPage() {
  return (
    <ComingSoon eyebrow="Try It" title="Present a credential, watch it break" arrives="Phase 3.5">
      Install the wallet from this page, receive a PID, and present it to the
      verifier live. Tamper with a claim and watch the exact check fail — the
      defect taxonomy made interactive.
    </ComingSoon>
  );
}
