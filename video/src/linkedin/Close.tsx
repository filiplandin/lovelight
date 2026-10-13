// Shots 13-15: shoebox montage, books + SIE4, end card (loops back into the hook).
import React from "react";
import { AbsoluteFill, Img, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { C, Wordmark, sek } from "../theme";
import { Clip } from "./Clip";
import { AUTO_POSTED, BOOKS, DOC_COUNT, HACKATHON, LI_DOCS, REPO_URL, REVIEW, THREATS } from "./facts";
import { MatchGraphic } from "./Open";
import { BOX, Caption, Cut, LStage, Mono, Panel, Tick, ramp } from "./ui";

// ---------------------------------------------------------------- 13. montage

// 26 thumbnails rain into a grid and settle to a status colour; three large tallies carry the readable message.
const COLS = 7;
const GAP = 12;
const CW = (BOX.width - (COLS - 1) * GAP) / COLS;
const CHT = 104;
const GRID_TOP = 470;
export const MONTAGE_FRAMES = 84;
export const montageArrive = (i: number) => 3 + i;
const SETTLE = 12;
export const TALLY_AT = 34;
const STATUS = {
  posted: { label: "Posted", color: C.green },
  review: { label: "Review", color: C.amber },
  threat: { label: "Flagged", color: C.red },
};
const TALLIES = [
  { n: AUTO_POSTED, ...STATUS.posted, sub: "auto-posted" },
  { n: REVIEW, ...STATUS.review, sub: "to an accountant" },
  { n: THREATS, ...STATUS.threat, sub: "threats caught" },
];

export const Montage: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const count = Math.min(DOC_COUNT, LI_DOCS.filter((_, i) => frame >= montageArrive(i)).length);
  const rows = Math.ceil(LI_DOCS.length / COLS);
  return (
    <LStage>
      <Caption text="26 docs in. | *Posted* or !flagged.!" />
      <div style={{ position: "absolute", left: BOX.left, right: BOX.left, top: 370, display: "flex", alignItems: "baseline", gap: 16 }}>
        <Mono style={{ fontSize: 64 }}>{count}</Mono>
        <span style={{ fontSize: 34, color: C.muted, fontWeight: 600 }}>documents in</span>
      </div>
      <div style={{ position: "absolute", left: BOX.left, top: GRID_TOP, width: BOX.width, height: rows * CHT + (rows - 1) * GAP }}>
        {LI_DOCS.map((d, i) => {
          const a = montageArrive(i);
          const p = spring({ frame: frame - a, fps, config: { damping: 15, stiffness: 140 } });
          const s = ramp(frame, a + SETTLE, a + SETTLE + 4);
          const st = STATUS[d.status];
          const col = i % COLS;
          const row = Math.floor(i / COLS);
          const flagged = d.status !== "posted";
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
                background: d.img ? "#ececf1" : "#1a1d2a",
                border: `${flagged ? 3 : 2}px solid ${s > 0.5 ? st.color : C.border2}`,
                boxShadow: s > 0.5 && flagged ? `0 0 28px ${st.color}66` : "0 10px 30px rgba(0,0,0,0.4)",
                opacity: frame < a ? 0 : Math.min(1, p * 2),
                transform: `rotate(${(1 - p) * ((i % 3) - 1) * 10}deg)`,
                display: "grid",
                placeItems: d.img ? undefined : "center",
              }}
            >
              {d.img ? <Img src={staticFile(`docs/${d.img}`)} style={{ width: "100%", objectFit: "cover", objectPosition: "top" }} /> : <span style={{ color: C.cyan, fontSize: 40 }}>✉</span>}
              {/* posted docs fade back so the amber and red ones pop */}
              <div style={{ position: "absolute", inset: 0, background: `rgba(7,8,13,${0.5 * s * (flagged ? 0 : 1)})` }} />
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", left: BOX.left, right: BOX.left, top: 940, display: "flex", gap: 18 }}>
        {TALLIES.map((t, k) => {
          const p = spring({ frame: frame - TALLY_AT - k * 5, fps, config: { damping: 14, stiffness: 170 } });
          return (
            <div
              key={t.label}
              style={{
                flex: 1,
                height: 210,
                borderRadius: 26,
                background: `${t.color}14`,
                border: `2px solid ${t.color}88`,
                boxShadow: `0 0 40px ${t.color}22`,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                opacity: p,
                transform: `translateY(${(1 - p) * 40}px)`,
              }}
            >
              <div style={{ fontSize: 104, fontWeight: 800, letterSpacing: "-0.05em", lineHeight: 1, color: t.color }}>{t.n}</div>
              <div style={{ fontSize: 34, fontWeight: 700, marginTop: 8, color: C.text }}>{t.label}</div>
              <div style={{ fontSize: 23, color: C.muted, marginTop: 2 }}>{t.sub}</div>
            </div>
          );
        })}
      </div>
    </LStage>
  );
};

// ---------------------------------------------------------------- 14. REC books

export const BOOKS_FRAMES = 90;
export const BOOKS_CUT = 52;
const TOTALS_AT = 22;

/** Phone-readable restatement of the balance-sheet totals the clip rings, plus the voucher balance count. */
const BooksTotals: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: frame - TOTALS_AT, fps, config: { damping: 16, stiffness: 150 } });
  const eq = ramp(frame, TOTALS_AT + 10, TOTALS_AT + 16);
  const rows = [
    { label: "Total assets", v: BOOKS.assets },
    { label: "Equity + liabilities", v: BOOKS.liabEquity },
  ];
  return (
    <Panel
      glow={eq > 0.5 ? C.green : undefined}
      style={{
        position: "absolute",
        left: 60,
        right: 60,
        top: 560,
        padding: "34px 44px",
        background: "rgba(11,13,20,0.97)",
        opacity: p,
        transform: `translateY(${(1 - p) * 80}px)`,
      }}
    >
      {rows.map((r, i) => (
        <div key={r.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginTop: i ? 18 : 0 }}>
          <span style={{ fontSize: 34, color: C.muted, fontWeight: 600 }}>{r.label}</span>
          <Mono style={{ fontSize: 50, color: eq > 0.5 ? C.green : C.text }}>{sek(r.v, false)}</Mono>
        </div>
      ))}
      <div style={{ marginTop: 26, paddingTop: 22, borderTop: `1.5px solid ${C.border2}`, display: "flex", alignItems: "center", gap: 16, opacity: eq }}>
        <Tick ok size={52} p={eq} />
        <span style={{ fontSize: 38, fontWeight: 800, letterSpacing: "-0.02em" }}>
          <span style={{ color: C.green }}>
            {BOOKS.balanced} / {BOOKS.vouchers}
          </span>{" "}
          vouchers balanced
        </span>
      </div>
    </Panel>
  );
};

export const Books: React.FC = () => {
  const frame = useCurrentFrame();
  return (
  <LStage>
    <Caption text="Debit = credit. | Ready for *Fortnox~&~Visma.*" size={68} />
    {/* Balance-sheet totals, then cut to the SIE4 export that Fortnox and Visma import. */}
    <Cut from={0} dur={BOOKS_CUT + 4} fade={0}>
      <Clip
        name="books"
        title="Books · balance sheet totals"
        steps={["/?view=books", "centre 'Total assets' and 'Total equity & liabilities', hold 1 s", "click 'SIE4 preview', hold 0.7 s"]}
        anchor="assets"
        lead={0.1}
        dim={0.8 * ramp(frame, TOTALS_AT - 2, TOTALS_AT + 6)}
        fallback={{ assets: [0.6, 0.45, 0.36, 0.03], liab: [0.6, 0.6, 0.36, 0.03] }}
        cam={[
          { f: 0, at: { m: "assets", fx: 0.58 }, z: 1.75 },
          { f: 16, at: { mid: ["assets", "liab"], fx: 0.58 }, z: 1.6 },
        ]}
        rings={[
          { f: 4, at: "assets", dur: 30, color: C.green },
          { f: 12, at: "liab", dur: 26, color: C.green },
        ]}
      />
    </Cut>
    <Sequence from={0} durationInFrames={BOOKS_CUT + 4} layout="none">
      <BooksTotals />
    </Sequence>
    <Cut from={BOOKS_CUT} dur={BOOKS_FRAMES - BOOKS_CUT}>
      <Clip
        name="books"
        title="Books · SIE4 preview"
        anchor="sie"
        lead={0.3}
        fallback={{ sie: [0.2, 0.2, 0.6, 0.6] }}
        cam={[
          { f: 0, at: [0.36, 0.2], z: 2.1 },
          { f: BOOKS_FRAMES - BOOKS_CUT, at: [0.36, 0.3], z: 2.1 },
        ]}
      />
    </Cut>
  </LStage>
  );
};

// ---------------------------------------------------------------- 15. end card

export const END_FRAMES = 135;
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
  const cta = spring({ frame: frame - 34, fps, config: { damping: 16, stiffness: 130 } });
  return (
    <LStage>
      <AbsoluteFill style={{ background: `radial-gradient(700px 520px at 50% 46%, rgba(139,108,255,${0.18 * glow}), transparent 70%)` }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 150, display: "flex", justifyContent: "center", opacity: ramp(frame, 0, 10) }}>
        <Wordmark size={44} />
      </div>
      <div style={{ position: "absolute", left: 70, right: 70, top: 330, display: "flex", flexDirection: "column", gap: 16 }}>
        {LINES.map((l, i) => {
          const p = spring({ frame: frame - 6 - i * 10, fps, config: { damping: 15, stiffness: 140 } });
          return (
            <div key={l.t} style={{ fontSize: 86, fontWeight: 800, letterSpacing: "-0.045em", lineHeight: 1.08, whiteSpace: "nowrap", color: l.c, opacity: p, transform: `translateY(${(1 - p) * 40}px)`, textShadow: `0 0 50px ${l.c}44` }}>
              {l.t}
            </div>
          );
        })}
      </div>
      <div
        style={{
          position: "absolute",
          left: 70,
          right: 70,
          top: 760,
          padding: 3,
          borderRadius: 30,
          background: C.grad,
          boxShadow: `0 0 ${40 + 30 * glow}px rgba(91,140,255,0.35)`,
          opacity: cta,
          transform: `translateY(${(1 - cta) * 40}px)`,
        }}
      >
        <div style={{ borderRadius: 27, background: "#0b0d16", padding: "30px 36px 34px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14, fontSize: 30, fontWeight: 700, color: C.text, letterSpacing: "0.02em" }}>
            Open source
            <svg width={40} height={24} viewBox="0 0 40 24" style={{ transform: `translateX(${6 * Math.sin(frame / 6)}px)` }}>
              <path d="M2 12h32M24 3l10 9-10 9" fill="none" stroke={C.cyan} strokeWidth={3.5} strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <Mono style={{ display: "block", marginTop: 14, fontSize: 42, color: C.cyan, whiteSpace: "nowrap", textShadow: `0 0 24px ${C.cyan}55` }}>{REPO_URL}</Mono>
        </div>
      </div>
      <div style={{ position: "absolute", left: 90, right: 90, top: 1010, display: "flex", flexDirection: "column", alignItems: "center", gap: 18, opacity: ramp(frame, 46, 56) }}>
        <div style={{ width: 120, height: 2, background: C.border2 }} />
        <div style={{ fontSize: 32, color: C.muted, lineHeight: 1.35, fontWeight: 500, textAlign: "center", textWrap: "balance" } as React.CSSProperties}>{HACKATHON}</div>
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
