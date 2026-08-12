"use client";

import type { Step } from "@/lib/walkthrough/stories";

export function ExplainRail({ step }: { step: Step | null }) {
  return (
    <div className="rail">
      <div className="card">
        <h3 style={{ marginBottom: 8 }}>What just happened</h3>
        <h4>{step ? step.expl.t : "Welcome"}</h4>
        <p>{step ? step.expl.b : "Choose a story to begin."}</p>
      </div>
      <div className="card nerd">
        <h3 style={{ marginBottom: 8 }}>Under the hood</h3>
        <div className="tech" dangerouslySetInnerHTML={{ __html: step?.tech || "—" }} />
      </div>
      <div className="card">
        <h3 style={{ marginBottom: 8 }}>Worth knowing</h3>
        <div dangerouslySetInnerHTML={{ __html: step?.fact || '<div class="legalnote">—</div>' }} />
      </div>
    </div>
  );
}
