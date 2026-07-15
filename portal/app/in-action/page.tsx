import { ComingSoon } from "@/components/ComingSoon";

export const metadata = { title: "In Action — eIDAS Wallet & QES Lab" };

export default function InActionPage() {
  return (
    <ComingSoon eyebrow="In Action" title="The three-actor loop" arrives="Phase 2" icon="workflow">
      A precomputed walkthrough of a credential moving through issuer, wallet, and
      the Lara Bank verifier over OpenID4VP — every check in the verification
      decision shown firing in order, pass and fail.
    </ComingSoon>
  );
}
