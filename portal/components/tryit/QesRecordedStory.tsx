import { CheckCircle2, XCircle, MinusCircle } from "lucide-react";
import { StoryCard } from "./StoryCard";
import { getQesWalkthrough, type QesResult } from "@/lib/qesWalkthrough";

const FIELD_LABELS: Record<string, string> = {
  signature_valid: "signature_valid",
  chain_trusted: "chain_trusted",
  document_unmodified: "document_unmodified",
  timestamp_valid: "timestamp_valid",
  is_qualified: "is_qualified",
};

function FieldRow({ name, value, flipped }: { name: string; value: boolean | null; flipped: boolean }) {
  const Icon = value === null ? MinusCircle : value ? CheckCircle2 : XCircle;
  const color = value === null ? "text-[var(--text-3)]" : value ? "text-[var(--accept)]" : "text-[var(--reject)]";
  return (
    <li className={`flex items-center gap-2 text-xs ${flipped ? "font-semibold" : ""}`}>
      <Icon size={13} className={`shrink-0 ${color}`} />
      <span className="font-mono text-[var(--text-2)]">{name}</span>
      <span className={`ml-auto font-mono ${color}`}>{value === null ? "null" : String(value)}</span>
    </li>
  );
}

function ResultCard({ result, flippedField }: { result: QesResult; flippedField: string | null }) {
  return (
    <div className="rounded-lg border border-[var(--border-c)] bg-[var(--surface-2)] p-3">
      <ul className="space-y-1">
        {Object.entries(FIELD_LABELS).map(([field, label]) => (
          <FieldRow
            key={field}
            name={label}
            value={result[field as keyof QesResult] as boolean | null}
            flipped={field === flippedField}
          />
        ))}
      </ul>
      {result.detail && <p className="text-[11px] text-[var(--text-3)] mt-2">{result.detail}</p>}
    </div>
  );
}

/**
 * QES surfaced in the portal for the first time since Phase 4 — a recorded
 * run (real CA chain, real PAdES signature, honestly labelled as recorded
 * rather than live), including the AES-vs-QES flip where every
 * cryptographic check passes and only `is_qualified` disagrees.
 */
export function QesRecordedStory() {
  const data = getQesWalkthrough();
  const flip = data.experiments.find((e) => e.expected_field === "is_qualified");

  return (
    <StoryCard
      title="Sign a mortgage — qualified signature"
      blurb="A real CA chain and a real PAdES signature, recorded once rather than driven live — no browser can perform PAdES signing interactively."
      tag="Recorded run"
    >
      <div className="text-xs font-mono text-[var(--text-3)] space-y-0.5">
        <div>root → {data.chain.root}</div>
        <div>root → qtsp → {data.chain.qtsp}</div>
        <div>qtsp → signer → {data.chain.signer}</div>
        <div>{data.signed_pdf_bytes.toLocaleString()} bytes signed ({data.blank_pdf_bytes} blank)</div>
      </div>

      <div>
        <div className="text-[10px] uppercase tracking-wide text-[var(--text-3)] mb-1.5">Happy path</div>
        <ResultCard result={data.happy_result} flippedField={null} />
      </div>

      <div className="space-y-2">
        <div className="text-[10px] uppercase tracking-wide text-[var(--text-3)]">
          Five break-it experiments
        </div>
        {data.experiments.map((exp) => (
          <div key={exp.species} className="space-y-1">
            <p className="text-xs text-[var(--text-2)]">
              <span className="font-mono text-[var(--foreground)]">{exp.species}</span> — {exp.description}
            </p>
            <ResultCard result={exp.result} flippedField={exp.expected_field} />
          </div>
        ))}
      </div>

      {flip && (
        <p className="text-xs text-[var(--text-2)] pt-1 border-t border-[var(--border-c)]">
          The one non-rejection: <span className="font-mono">{flip.species}</span> passes every cryptographic
          check — <span className="font-mono">signature_valid</span>, <span className="font-mono">chain_trusted</span>,{" "}
          <span className="font-mono">document_unmodified</span>, <span className="font-mono">timestamp_valid</span> all
          stay true. Only <span className="font-mono">is_qualified</span> flips — a real ETSI qcStatements
          extension the QTSP chose to attach or withhold, a legal fact, not a mathematical one.
        </p>
      )}
    </StoryCard>
  );
}
