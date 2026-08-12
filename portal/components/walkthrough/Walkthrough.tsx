"use client";

import { useEffect, useRef, useState } from "react";
import { Maximize, Minimize } from "lucide-react";
import { STORIES } from "@/lib/walkthrough/stories";
import { StoryPicker } from "./StoryPicker";
import { PhoneFrame } from "./PhoneFrame";
import { ExplainRail } from "./ExplainRail";
import { ActorBand } from "./ActorBand";
import "@/app/walkthrough.css";

export function Walkthrough() {
  const [curId, setCurId] = useState<string | null>(null);
  const [idx, setIdx] = useState(0);
  const [autoplay, setAutoplay] = useState(false);
  const [nerdOn, setNerdOn] = useState(false);
  const [bandOff, setBandOff] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onChange = () => setIsFullscreen(document.fullscreenElement === wrapperRef.current);
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  function toggleFullscreen() {
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      wrapperRef.current?.requestFullscreen();
    }
  }

  const cur = curId ? STORIES.find((s) => s.id === curId) || null : null;
  const step = cur ? cur.steps[idx] : null;

  function start(id: string) {
    setCurId(id);
    setIdx(0);
  }

  function go(next: string) {
    if (next.startsWith("story:")) {
      start(next.split(":")[1]);
      return;
    }
    if (!cur) return;
    if (next === "back") {
      setIdx((i) => Math.max(i - 1, 0));
    } else if (next === "stay") {
      return;
    } else {
      // next / next2 / next3 all just advance one step (prototype behaviour)
      setIdx((i) => Math.min(i + 1, cur.steps.length - 1));
    }
  }

  const stepKey = cur && step ? `${cur.id}:${idx}` : "none";

  return (
    <div ref={wrapperRef} className={`wt${nerdOn ? " nerdon" : ""}${bandOff ? " bandoff" : ""}`}>
      <div className="wrap">
        <header className="top">
          <div className="brand">
            <svg className="stars" viewBox="0 0 100 100" aria-hidden="true">
              <circle cx="50" cy="50" r="48" fill="#0b3fb5" />
              <g fill="#ffcc00">
                <circle cx="50" cy="18" r="4" />
                <circle cx="66" cy="22" r="4" />
                <circle cx="78" cy="34" r="4" />
                <circle cx="82" cy="50" r="4" />
                <circle cx="78" cy="66" r="4" />
                <circle cx="66" cy="78" r="4" />
                <circle cx="50" cy="82" r="4" />
                <circle cx="34" cy="78" r="4" />
                <circle cx="22" cy="66" r="4" />
                <circle cx="18" cy="50" r="4" />
                <circle cx="22" cy="34" r="4" />
                <circle cx="34" cy="22" r="4" />
              </g>
            </svg>
            <div>
              <h1>Issued to you. Held on your phone. Shared one claim at a time.</h1>
              <div className="sub">
                Every EU Digital Identity Wallet flow has exactly three parties. The band below
                shows which one is acting and which way the data moves. Start with{" "}
                <b style={{ color: "var(--txt)" }}>Get your wallet</b> to meet the PID, then watch
                a driving licence get issued, then open a credential up claim by claim and choose
                what leaves your phone.
              </div>
            </div>
          </div>
          <div className="toggles">
            <button className={`tg${nerdOn ? " on" : ""}`} onClick={() => setNerdOn((v) => !v)}>
              <span className="dotled" />
              Show the tech
            </button>
            <button className={`tg${!bandOff ? " on" : ""}`} onClick={() => setBandOff((v) => !v)}>
              <span className="dotled" />
              Show the three parties
            </button>
            <button className={`tg${autoplay ? " on" : ""}`} onClick={() => setAutoplay((v) => !v)}>
              <span className="dotled" />
              Auto-play
            </button>
            <button className={`tg${isFullscreen ? " on" : ""}`} onClick={toggleFullscreen}>
              {isFullscreen ? <Minimize size={12} /> : <Maximize size={12} />}
              {isFullscreen ? "Exit full screen" : "Full screen"}
            </button>
          </div>
        </header>

        <ActorBand storyId={curId} idx={idx} />

        <div className="stage">
          <StoryPicker activeId={curId} onSelect={start} />

          <PhoneFrame
            step={step}
            stepKey={stepKey}
            autoplay={autoplay}
            canGoBack={!!cur && idx > 0}
            onPrimary={() => step?.primary && go(step.primary.next)}
            onSecondary={() => step?.secondary && go(step.secondary.next)}
            onBack={() => cur && idx > 0 && setIdx((i) => i - 1)}
            onRestart={() => cur && setIdx(0)}
          />

          <ExplainRail step={step} />
        </div>

        <footer>
          Illustrative prototype. Lara Bank is fictional. Flows follow the EUDI Wallet architecture
          (ARF), eIDAS 2.0 and the eIDAS trust-service rules for qualified signatures.
          <br />
          Not affiliated with the European Commission. Built to make a policy change feel like a
          product.
        </footer>
      </div>
    </div>
  );
}
