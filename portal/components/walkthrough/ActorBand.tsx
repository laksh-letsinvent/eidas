"use client";

import { BAND, BAND_DEFAULT_ISS, BAND_DEFAULT_VER, type BandEntry } from "@/lib/walkthrough/stories";

export function ActorBand({ storyId, idx }: { storyId: string | null; idx: number }) {
  const key = storyId ? `${storyId}:${idx}` : null;
  const b: Partial<BandEntry> = (key && BAND[key]) || {};

  const issRole = b.issRole || BAND_DEFAULT_ISS.role;
  const issName = b.iss || BAND_DEFAULT_ISS.name;
  const issDesc = b.issDesc || BAND_DEFAULT_ISS.desc;
  const issIcon = b.issIcon || BAND_DEFAULT_ISS.icon;
  const verRole = b.verRole || BAND_DEFAULT_VER.role;
  const verName = b.ver || BAND_DEFAULT_VER.name;
  const verDesc = b.verDesc || BAND_DEFAULT_VER.desc;
  const verIcon = b.verIcon || BAND_DEFAULT_VER.icon;

  const nIssClass = "node" + (b.iss ? " on" : "");
  const nVerClass = "node" + (b.verBad ? " bad" : "") + (b.ver ? " on" : "");

  const flow = b.flow || "";
  const issOn = flow === "iss>you" || flow === "you>iss";
  const verOn = flow === "ver>you" || flow === "you>ver";

  const eIssClass = "edge" + (issOn ? " on " + (flow === "iss>you" ? "r" : "l") : " idle");
  const eVerClass = "edge" + (verOn ? " on " + (flow === "you>ver" ? "r" : "l") : " idle") + (b.verBad ? " bad" : "");

  const issLabel = issOn ? b.label : "";
  const verLabel = verOn ? b.label : "";
  const issArrow = issOn ? (flow === "iss>you" ? "▸▸▸" : "◂◂◂") : "";
  const verArrow = verOn ? (flow === "you>ver" ? "▸▸▸" : "◂◂◂") : "";

  return (
    <div className="actorband">
      <div className="bandhead">
        Who is involved right now{" "}
        <span className="hint">— three parties, always. Watch which ones light up.</span>
      </div>
      <div className="triad">
        <div className={nIssClass}>
          <div className="nic">{issIcon}</div>
          <div>
            <div className="role">{issRole}</div>
            <div className="nname">{issName}</div>
            <div className="ndesc">{issDesc}</div>
          </div>
        </div>

        <div className={eIssClass}>
          <div className="elabel">{issLabel}</div>
          <div className="track">
            <i className="pkt" />
          </div>
          <div className="arrow">{issArrow}</div>
          <div className="quiet">no traffic</div>
        </div>

        <div className="node you on">
          <div className="nic">👛</div>
          <div>
            <div className="role">Holder — this is you</div>
            <div className="nname">Your wallet</div>
            <div className="ndesc">Holds the credentials. Decides what leaves the phone.</div>
          </div>
        </div>

        <div className={eVerClass}>
          <div className="elabel">{verLabel}</div>
          <div className="track">
            <i className="pkt" />
          </div>
          <div className="arrow">{verArrow}</div>
          <div className="quiet">no traffic</div>
        </div>

        <div className={nVerClass}>
          <div className="nic">{verIcon}</div>
          <div>
            <div className="role">{verRole}</div>
            <div className="nname">{verName}</div>
            <div className="ndesc">{verDesc}</div>
          </div>
        </div>
      </div>
      <div className="nolink">
        <div className="ln" />
        <div className="tag">
          <b>✕</b> the issuer and the verifier never talk to each other
        </div>
      </div>
      <div
        className="bandcap"
        dangerouslySetInnerHTML={{ __html: b.cap || "Pick a story and the parties will change with it." }}
      />
    </div>
  );
}
