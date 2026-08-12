"use client";

import { useEffect, useRef, useState } from "react";
import type { Step } from "@/lib/walkthrough/stories";
import { SelectiveDisclosureLab } from "./SelectiveDisclosureLab";

const QES_STAGES = [
  "Contacting qualified trust service provider…",
  "Verifying your identity to LoA High…",
  "Unlocking your signing key…",
  "Applying qualified timestamp…",
];

export function PhoneFrame({
  step,
  stepKey,
  autoplay,
  canGoBack,
  onPrimary,
  onSecondary,
  onBack,
  onRestart,
}: {
  step: Step | null;
  stepKey: string;
  autoplay: boolean;
  canGoBack: boolean;
  onPrimary: () => void;
  onSecondary: () => void;
  onBack: () => void;
  onRestart: () => void;
}) {
  const viewRef = useRef<HTMLDivElement>(null);
  const [primaryDisabled, setPrimaryDisabled] = useState(false);

  useEffect(() => {
    if (viewRef.current) viewRef.current.scrollTop = 0;
    setPrimaryDisabled(false);
    if (!step) return;

    const timeouts: ReturnType<typeof setTimeout>[] = [];
    const intervals: ReturnType<typeof setInterval>[] = [];

    if (step.auto) {
      setPrimaryDisabled(true);
      timeouts.push(
        setTimeout(() => {
          setPrimaryDisabled(false);
          if (autoplay) onPrimary();
        }, step.auto)
      );
    } else if (autoplay && step.primary) {
      timeouts.push(setTimeout(() => onPrimary(), 3400));
    }

    if (step.progress === "qes" && viewRef.current) {
      const bar = viewRef.current.querySelector<HTMLElement>("#qesbar");
      const lbl = viewRef.current.querySelector<HTMLElement>("#qeslbl");
      let p = 0;
      let i = 0;
      intervals.push(
        setInterval(() => {
          p += 4;
          if (bar) bar.style.width = p + "%";
          if (p % 25 === 0 && i < QES_STAGES.length && lbl) lbl.textContent = QES_STAGES[i++];
          if (p >= 100) intervals.forEach((iv) => clearInterval(iv));
        }, 110)
      );
    }

    const cleanupFns: Array<() => void> = [];
    if (viewRef.current) {
      viewRef.current.querySelectorAll<HTMLElement>(".field[data-opt] .sw").forEach((sw) => {
        const fn = () => sw.closest(".field")?.classList.toggle("off");
        sw.addEventListener("click", fn);
        cleanupFns.push(() => sw.removeEventListener("click", fn));
      });
    }

    return () => {
      timeouts.forEach((t) => clearTimeout(t));
      intervals.forEach((iv) => clearInterval(iv));
      cleanupFns.forEach((fn) => fn());
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stepKey]);

  return (
    <div className="phonewrap">
      <div className="phone">
        <div className="screen">
          <div className="notch" />
          <div className="statusbar">
            <span>09:41</span>
            <span>5G &nbsp; ▮▮▮ &nbsp; 87%</span>
          </div>
          <div className="appbar">
            <div className="lg">{step ? step.icon : "🇪🇺"}</div>
            <div>
              <div className="nm">{step ? step.app : "EU Digital Identity Wallet"}</div>
            </div>
            <div className="rt">{step?.right || ""}</div>
          </div>
          <div className="view" ref={viewRef}>
            {step ? (
              <div className="anim" key={stepKey}>
                <div dangerouslySetInnerHTML={{ __html: step.body }} />
                {step.mount === "sd" && <SelectiveDisclosureLab />}
              </div>
            ) : (
              <>
                <div className="hero">
                  <div className="glow" />
                  <div className="em">👛</div>
                </div>
                <div className="h1p">Pick a story to begin</div>
                <div className="pp">
                  Nine short journeys. Start at the top — they build on each other. The two marked{" "}
                  <b>Interactive</b> and <b>One org, two roles</b> are the ones that explain the
                  machinery.
                </div>
              </>
            )}
          </div>
          <div className="foot">
            {step?.primary && (
              <button className="btn" disabled={primaryDisabled} onClick={onPrimary}>
                {step.primary.label}
              </button>
            )}
            {step?.secondary && (
              <button className="btn ghost" onClick={onSecondary}>
                {step.secondary.label}
              </button>
            )}
          </div>
        </div>
      </div>
      <div className="ctl" style={{ width: 352 }}>
        <button onClick={onBack} disabled={!canGoBack}>
          ← Back
        </button>
        <button onClick={onRestart} disabled={!step}>
          ↺ Restart story
        </button>
      </div>
    </div>
  );
}
