"use client";

import { useState } from "react";
import { PID_CLAIMS, PID_FIXED, SD_PRESETS, claimHash } from "@/lib/walkthrough/stories";

/**
 * The one piece of real interactivity in the walkthrough, reimplemented as
 * a proper React component (BUILD_PROMPT_PHASE7-9.md) rather than ported
 * as an HTML-string helper: it owns its own state over the claim set
 * instead of mutating a module-level `sdSel` the way the prototype did.
 */
export function SelectiveDisclosureLab() {
  const [selected, setSelected] = useState<Set<string>>(new Set(SD_PRESETS.bank));

  function toggle(k: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(k) ? next.delete(k) : next.add(k);
      return next;
    });
  }

  function applyPreset(name: string) {
    setSelected(new Set(SD_PRESETS[name]));
  }

  const n = selected.size;
  const tot = PID_CLAIMS.length;
  const open = PID_CLAIMS.filter((c) => selected.has(c.k));
  const shut = PID_CLAIMS.filter((c) => !selected.has(c.k));
  const pct = Math.round((n / tot) * 100);
  const verdict =
    n === 0
      ? "The verifier learns that a valid government credential exists, and literally nothing else."
      : n <= 2
        ? "Minimal. This is what a well-designed request looks like."
        : n <= 5
          ? "Proportionate for opening a regulated account."
          : "Over-collection. Ask why each of these is genuinely needed.";
  const meterColor = n > 5 ? "var(--bad)" : n > 2 ? "var(--gold)" : "var(--ok)";

  return (
    <div>
      <div className="sdpre">
        <button data-p="bank" onClick={() => applyPreset("bank")}>
          Bank onboarding
        </button>
        <button data-p="age" onClick={() => applyPreset("age")}>
          Buying wine
        </button>
        <button data-p="parcel" onClick={() => applyPreset("parcel")}>
          Parcel delivery
        </button>
        <button data-p="none" className="none" onClick={() => applyPreset("none")}>
          Reveal nothing
        </button>
      </div>

      <div>
        {PID_CLAIMS.map((c) => {
          const sel = selected.has(c.k);
          return (
            <div
              key={c.k}
              className={`sdrow${sel ? " sel" : ""}`}
              onClick={() => toggle(c.k)}
            >
              <div className="cb">{sel ? "✓" : ""}</div>
              <div>
                <div className="ck mono">{c.k}</div>
                <div className="cv">{sel ? c.v : "••••••"}</div>
              </div>
              <div className="ch mono">{claimHash(c.k, c.v).slice(0, 8)}…</div>
            </div>
          );
        })}
      </div>

      <div
        style={{
          fontSize: "9.5px",
          textTransform: "uppercase",
          letterSpacing: "1.1px",
          color: "var(--muted)",
          margin: "14px 0 7px",
        }}
      >
        Always visible — not selectively disclosable
      </div>
      {PID_FIXED.map((c) => (
        <div key={c.k} className="sdrow fixed">
          <div className="cb">🔒</div>
          <div>
            <div className="ck mono">{c.k}</div>
            <div className="cv">{c.v}</div>
          </div>
        </div>
      ))}

      <div className="sdout">
        <div className="hd">What actually leaves your phone</div>
        <div style={{ fontSize: 13, fontWeight: 600 }}>
          The verifier learns{" "}
          <span style={{ color: meterColor }}>
            {n} of {tot}
          </span>{" "}
          facts about you
        </div>
        <div className="meter">
          <b style={{ width: `${pct}%` }} />
        </div>
        <div className="pp sm" style={{ marginBottom: 11 }}>
          {verdict}
        </div>
        {open.length > 0 && (
          <>
            <div className="hd" style={{ marginTop: 11 }}>
              Readable — value plus its salt
            </div>
            {open.map((c) => (
              <span key={c.k} className="chip2 open mono">
                {c.k} = {c.v}
              </span>
            ))}
          </>
        )}
        {shut.length > 0 && (
          <>
            <div className="hd" style={{ marginTop: 11 }}>
              Sent as an opaque hash — unreadable, but signed
            </div>
            {shut.map((c) => (
              <span key={c.k} className="chip2 mono">
                {claimHash(c.k, c.v).slice(0, 10)}…
              </span>
            ))}
          </>
        )}
        <div className="okbox" style={{ marginTop: 12, fontSize: 11.5 }}>
          The Home Office signature covers <b>all {tot} hashes</b>. So the verifier can prove the{" "}
          {n} value{n === 1 ? "" : "s"} you revealed {n === 1 ? "is" : "are"} genuine government
          data — while the other {tot - n} stay unreadable. That is selective disclosure.
        </div>
      </div>
    </div>
  );
}
