"use client";

import { STORIES } from "@/lib/walkthrough/stories";

export function StoryPicker({
  activeId,
  onSelect,
}: {
  activeId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="chooser">
      <h3>Pick a story</h3>
      <div>
        {STORIES.map((s) => (
          <button
            key={s.id}
            className={`scn${s.id === activeId ? " active" : ""}`}
            onClick={() => onSelect(s.id)}
          >
            <div className="ic">{s.icon}</div>
            <div className="scn-body">
              <b>{s.title}</b>
              <span>{s.blurb}</span>
              <span className="chip">{s.tag}</span>
            </div>
          </button>
        ))}
      </div>
      <div className="card" style={{ marginTop: 16, padding: 15 }}>
        <h4 style={{ fontSize: 12 }}>The one idea</h4>
        <p style={{ fontSize: 11.5 }}>
          You prove things about yourself without handing over your life. The wallet answers the
          question that was asked — and nothing more.
        </p>
      </div>
    </div>
  );
}
