// Shots 13-15: shoebox montage, books + SIE4, end card (loops back into the hook).
import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { C, Wordmark, sek } from "../theme";
import { Clip } from "./Clip";
import { DOC_COUNT, HACKATHON, LI_DOCS, REPO_URL, THREATS } from "./facts";
import { MatchGraphic } from "./Open";
import { BOX, Caption, LStage, Mono, ramp } from "./ui";

// ---------------------------------------------------------------- 13. montage

const COLS = 7;
const GAP = 10;
const CW = (BOX.width - (COLS - 1) * GAP) / COLS;
const CHT = 160;
const GRID_TOP = 450;
export const montageArrive = (i: number) => 4 + i * 2;
const STATUS = {
  posted: { label: "Posted", color: C.green },
  review: { label: "Review", color: C.amber },
  threat: { label: "Flagged", color: C.red },
};

export const Montage: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const zoom = interpolate(frame, [0, 40], [1.5, 1], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  const count = Math.min(DOC_COUNT, LI_DOCS.filter((_, i) => frame >= montageArrive(i)).length);
  const chip = spring({ frame: frame - 62, fps, config: { damping: 13 } });
  return (
    <LStage>
      <Caption text="26 docs in. | *Posted* or !flagged.!" />
      <div style={{ position: "absolute", left: BOX.left, right: BOX.left, top: 362, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
          <Mono style={{ fontSize: 56 }}>{count}</Mono>
          <span style={{ fontSize: 28, color: C.muted, fontWeight: 600 }}>documents in</span>
        </div>
        <div style={{ padding: "10px 22px", borderRadius: 999, background: `${C.red}1c`, border: `2px solid ${C.red}77`, color: C.red, fontSize: 28, fontWeight: 700, opacity: chip, transform: `scale(${0.8 + 0.2 * chip})` }}>
          {THREATS} threats caught
        </div>
      </div>
      <div style={{ position: "absolute", left: BOX.left, top: GRID_TOP, width: BOX.width, height: 4 * CHT + 3 * GAP, transform: `scale(${zoom})`, transformOrigin: "50% 30%" }}>
        {LI_DOCS.map((d, i) => {
          const a = montageArrive(i);
          const p = spring({ frame: frame - a, fps, config: { damping: 15, stiffness: 140 } });
          const settled = frame - a > 24;
          const st = settled ? STATUS[d.status] : { label: "Reading", color: C.violet };
          const col = i % COLS;
          const row = Math.floor(i / COLS);
          const amount = d.currency === "SEK" ? sek(d.gross, false) : `${sek(d.gross, false)} ${d.currency}`;
          return (
            <div
              key={d.file}
              style={{
                position: "absolute",
                left: col * (CW + GAP),
                top: row * (CHT + GAP) - (1 - p) * 500,
                width: CW,
                height: CHT,
                borderRadius: 14,
                overflow: "hidden",
                background: C.bg2,
                border: `1.5px solid ${settled && d.status !== "posted" ? `${st.color}aa` : C.border2}`,
                boxShadow: settled && d.status === "threat" ? `0 0 26px ${C.red}44` : "0 10px 30px rgba(0,0,0,0.4)",
                opacity: frame < a ? 0 : Math.min(1, p * 2),
                transform: `rotate(${(1 - p) * ((i % 3) - 1) * 10}deg)`,
              }}
            >
              <div style={{ height: 86, background: d.img ? "#ececf1" : "#1a1d2a", overflow: "hidden", display: "grid", placeItems: d.img ? undefined : "center" }}>
                {d.img ? <Img src={staticFile(`docs/${d.img}`)} style={{ width: "100%", objectFit: "cover", objectPosition: "top" }} /> : <span style={{ color: C.cyan, fontSize: 36 }}>✉</span>}
              </div>
              <div style={{ padding: "8px 10px" }}>
                <div style={{ fontSize: 15, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{d.vendor}</div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 6 }}>
                  <Mono style={{ fontSize: 13, color: C.muted }}>{amount}</Mono>
                  <span style={{ width: 10, height: 10, borderRadius: "50%", background: st.color, boxShadow: `0 0 8px ${st.color}` }} />
                </div>
                <div style={{ fontSize: 13, fontWeight: 700, color: st.color, marginTop: 4 }}>{st.label}</div>
              </div>
            </div>
          );
        })}
      </div>
    </LStage>
  );
};

// ---------------------------------------------------------------- 14. REC books

export const Books: React.FC = () => (
  <LStage>
    <Caption text="Debit = credit. | Ready for *Fortnox~&~Visma.*" size={68} />
    <Clip
      name="books"
      title="Books · balance sheet totals · SIE4 preview"
      steps={["/?view=books", "centre 'Total assets' and 'Total equity & liabilities', hold 1 s", "click 'SIE4 preview', hold 0.7 s"]}
      anchor="assets"
      lead={0.1}
      rate={1.5}
      fallback={{ assets: [0.6, 0.45, 0.36, 0.03], liab: [0.6, 0.6, 0.36, 0.03], sie: [0.2, 0.2, 0.6, 0.6] }}
      cam={[
        { f: 0, at: { m: "assets", fx: 0.75 }, z: 1.8 },
        { f: 16, at: { mid: ["assets", "liab"], fx: 0.75 }, z: 1.8 },
        { f: ["sie", -6], at: { mid: ["assets", "liab"], fx: 0.75 }, z: 1.6 },
        { f: ["sie", 6], at: "sie", z: 1.1 },
      ]}
      rings={[
        { f: 4, at: "assets", dur: 28, color: C.green },
        { f: 12, at: "liab", dur: 28, color: C.green },
      ]}
    />
  </LStage>
);

// ---------------------------------------------------------------- 15. end card

export const END_FRAMES = 120;
const LOOP_FADE = 12;
const LINES = [
  { t: "AI proposes.", c: C.violet },
  { t: "Code disposes.", c: C.blue },
  { t: "Accountant approves.", c: C.green },
];

export const EndCard: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const glow = 0.6 + 0.4 * Math.sin(frame / 14);
  const loop = ramp(frame, END_FRAMES - LOOP_FADE, END_FRAMES - 1);
  return (
    <LStage>
      <AbsoluteFill style={{ background: `radial-gradient(700px 520px at 50% 46%, rgba(139,108,255,${0.18 * glow}), transparent 70%)` }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 170, display: "flex", justifyContent: "center", opacity: ramp(frame, 0, 10) }}>
        <Wordmark size={44} />
      </div>
      <div style={{ position: "absolute", left: 70, right: 70, top: 420, display: "flex", flexDirection: "column", gap: 16 }}>
        {LINES.map((l, i) => {
          const p = spring({ frame: frame - 6 - i * 10, fps, config: { damping: 15, stiffness: 140 } });
          return (
            <div key={l.t} style={{ fontSize: 86, fontWeight: 800, letterSpacing: "-0.045em", lineHeight: 1.08, whiteSpace: "nowrap", color: l.c, opacity: p, transform: `translateY(${(1 - p) * 40}px)`, textShadow: `0 0 50px ${l.c}44` }}>
              {l.t}
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", left: 70, right: 70, top: 840, opacity: ramp(frame, 44, 54) }}>
        {REPO_URL.includes("<") ? null : (
          <div style={{ fontSize: 36, color: C.text, fontWeight: 600, marginBottom: 24 }}>
            Open source · <Mono style={{ color: C.cyan }}>{REPO_URL}</Mono>
          </div>
        )}
        <div style={{ fontSize: 32, color: C.muted, lineHeight: 1.35, fontWeight: 500, textWrap: "balance" } as React.CSSProperties}>{HACKATHON}</div>
      </div>
      {loop > 0 ? (
        <AbsoluteFill style={{ opacity: loop }}>
          <LStage>
            <Caption text="1 payment. 3~invoices. | *Matched.*" still />
            <MatchGraphic frame={0} fps={fps} still />
          </LStage>
        </AbsoluteFill>
      ) : null}
    </LStage>
  );
};
