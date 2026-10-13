import React from "react";
import { Img, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { MatchPair, PAIRS } from "../data";
import { C, Check, Eyebrow, MONO, Stage, fade, fadeOut, sek } from "../theme";

export const PAIR_STARTS = [0, 55, 110, 165];
const PAIR_LENS = [55, 55, 55, 135];
export const MATCHING_FRAMES = 300;
const TOTAL_LINES = 36;

const BANK_X = 140;
const BANK_W = 620;
const DOC_X = 1140;
const DOC_W = 640;
const MID_Y = 520;

const BankCard: React.FC<{ pair: MatchPair; p: number; showRefs: boolean }> = ({ pair, p, showRefs }) => {
  const refs = pair.docs.map((d) => d.ref).filter(Boolean) as string[];
  return (
    <div
      style={{
        position: "absolute",
        left: BANK_X - (1 - p) * 200,
        top: MID_Y - 85,
        width: BANK_W,
        height: 170,
        opacity: p,
        borderRadius: 18,
        background: C.bg2,
        border: `1px solid ${C.border2}`,
        padding: "24px 30px",
        boxSizing: "border-box",
        boxShadow: "0 20px 60px rgba(0,0,0,0.4)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 16, color: C.muted }}>
        <span>Bank · 1930 Företagskonto</span>
        <span style={{ fontFamily: MONO }}>
          {pair.bank.id} · {pair.bank.date}
        </span>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginTop: 22 }}>
        <span style={{ fontFamily: MONO, fontSize: 30, fontWeight: 500, whiteSpace: "nowrap" }}>{pair.bank.text}</span>
        <span style={{ fontFamily: MONO, fontSize: 30, fontWeight: 500, color: C.text, whiteSpace: "nowrap" }}>{sek(pair.bank.amount, false)}</span>
      </div>
      {refs.length ? (
        <div style={{ display: "flex", gap: 10, marginTop: 14, opacity: showRefs ? 1 : 0.0 }}>
          {refs.map((r) => (
            <span key={r} style={{ fontFamily: MONO, fontSize: 15, color: C.cyan, background: `${C.cyan}14`, border: `1px solid ${C.cyan}44`, padding: "3px 10px", borderRadius: 8 }}>
              {r}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
};

const DocCard: React.FC<{ d: MatchPair["docs"][number]; top: number; height: number; p: number; matched: number }> = ({ d, top, height, p, matched }) => (
  <div
    style={{
      position: "absolute",
      left: DOC_X + (1 - p) * 200,
      top,
      width: DOC_W,
      height,
      opacity: p,
      borderRadius: 18,
      background: C.bg2,
      border: `1px solid ${matched > 0.5 ? `${C.green}66` : C.border2}`,
      display: "flex",
      overflow: "hidden",
      boxShadow: matched > 0.5 ? `0 0 40px ${C.green}22` : "0 20px 60px rgba(0,0,0,0.4)",
    }}
  >
    <div style={{ width: height * 0.78, background: "#eee", overflow: "hidden", flexShrink: 0 }}>
      <Img src={staticFile(`docs/${d.img}`)} style={{ width: "100%", objectFit: "cover", objectPosition: "top" }} />
    </div>
    <div style={{ padding: "18px 26px", display: "flex", flexDirection: "column", justifyContent: "center", gap: 8, flex: 1 }}>
      <div style={{ fontSize: height > 200 ? 28 : 22, fontWeight: 600 }}>{d.vendor}</div>
      {d.ref ? <div style={{ fontFamily: MONO, fontSize: 15, color: C.cyan }}>ref {d.ref}</div> : null}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontFamily: MONO, fontSize: height > 200 ? 30 : 24 }}>{sek(d.gross)}</span>
        <Check size={height > 200 ? 36 : 30} progress={matched} />
      </div>
    </div>
  </div>
);

const PairView: React.FC<{ pair: MatchPair; len: number }> = ({ pair, len }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 18, stiffness: 140 } });
  const exit = fadeOut(frame, len - 10, 10);
  const multi = pair.docs.length > 1;
  const docH = multi ? 140 : 280;
  const docTops = multi ? [MID_Y - 250, MID_Y - 90, MID_Y + 70] : [MID_Y - docH / 2];
  const lineStart = multi ? 18 : 12;
  const pillAt = multi ? 54 : 26;
  const pill = spring({ frame: frame - pillAt, fps, config: { damping: 12, stiffness: 180 } });
  const sumP = fade(frame, 62, 12);

  return (
    <div style={{ position: "absolute", inset: 0, opacity: exit, transform: `translateY(${(1 - exit) * -30}px)` }}>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        <defs>
          <linearGradient id="ln" x1="0" x2="1">
            <stop offset="0" stopColor={C.violet} />
            <stop offset="1" stopColor={C.cyan} />
          </linearGradient>
        </defs>
        {pair.docs.map((_, k) => {
          const y1 = docTops[k] + docH / 2;
          const draw = interpolate(frame, [lineStart + k * 8, lineStart + k * 8 + 16], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const x0 = BANK_X + BANK_W;
          const x1 = DOC_X;
          const d = `M ${x0} ${MID_Y} C ${x0 + 190} ${MID_Y}, ${x1 - 190} ${y1}, ${x1} ${y1}`;
          return (
            <g key={k}>
              <path d={d} stroke="url(#ln)" strokeWidth={3} fill="none" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw} />
              <circle cx={x0} cy={MID_Y} r={6 * draw} fill={C.violet} />
              <circle cx={x1} cy={y1} r={6 * (draw > 0.98 ? 1 : 0)} fill={C.cyan} />
            </g>
          );
        })}
      </svg>
      <BankCard pair={pair} p={enter} showRefs={frame > lineStart} />
      {pair.docs.map((d, k) => {
        const p = spring({ frame: frame - 3 - k * 4, fps, config: { damping: 18, stiffness: 140 } });
        const matched = interpolate(frame, [lineStart + k * 8 + 16, lineStart + k * 8 + 24], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        return <DocCard key={d.img} d={d} top={docTops[k]} height={docH} p={p} matched={matched} />;
      })}
      <div
        style={{
          position: "absolute",
          left: (BANK_X + BANK_W + DOC_X) / 2 - 90,
          top: MID_Y - 26 - (multi ? 0 : 0),
          width: 180,
          height: 52,
          borderRadius: 999,
          background: "#0f1a17",
          border: `1px solid ${C.green}88`,
          color: C.green,
          fontSize: 22,
          fontWeight: 700,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 8,
          transform: `scale(${pill})`,
          boxShadow: `0 0 30px ${C.green}33`,
          fontFeatureSettings: '"tnum" 1',
        }}
      >
        {pair.confidence}% match
      </div>
      {multi ? (
        <div style={{ position: "absolute", left: DOC_X, top: MID_Y + 232, width: DOC_W, fontFamily: MONO, fontSize: 22, color: C.muted, opacity: sumP, textAlign: "right" }}>
          {pair.docs.map((d) => sek(d.gross, false)).join(" + ")} = <span style={{ color: C.green }}>{sek(-pair.bank.amount)}</span>
        </div>
      ) : null}
      {multi ? (
        <div style={{ position: "absolute", left: BANK_X, top: MID_Y + 120, width: BANK_W, fontSize: 22, color: C.muted, opacity: sumP }}>
          One payment · three invoices · split by reference
        </div>
      ) : null}
    </div>
  );
};

const Progress: React.FC = () => {
  const frame = useCurrentFrame();
  // 4 shown one by one, then the remaining lines auto-match; BT023 (Amazon, missing receipt) stays amber.
  const shown = PAIR_STARTS.filter((s, i) => frame >= s + (i === 3 ? 60 : 30)).length;
  const auto = Math.floor(interpolate(frame, [240, 285], [0, TOTAL_LINES - 4], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  const filled = shown + auto;
  return (
    <div style={{ position: "absolute", left: 140, right: 140, bottom: 80 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 20, color: C.muted, marginBottom: 14 }}>
        <span>Bank lines reconciled</span>
        <span style={{ fontFamily: MONO, color: C.text }}>
          {filled} / {TOTAL_LINES}
        </span>
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        {Array.from({ length: TOTAL_LINES }).map((_, i) => {
          const on = i < filled;
          const amber = on && i === TOTAL_LINES - 1;
          return (
            <div
              key={i}
              style={{
                flex: 1,
                height: 10,
                borderRadius: 5,
                background: on ? (amber ? C.amber : C.green) : C.panel2,
                boxShadow: on ? `0 0 10px ${amber ? C.amber : C.green}55` : "none",
              }}
            />
          );
        })}
      </div>
    </div>
  );
};

export const Matching: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <Stage style={{ opacity: fadeOut(frame, MATCHING_FRAMES - 10, 10) }}>
      <div style={{ position: "absolute", left: 140, top: 70, opacity: fade(frame, 0) }}>
        <Eyebrow color={C.cyan}>Matching</Eyebrow>
        <div style={{ fontSize: 52, fontWeight: 700, letterSpacing: "-0.03em", marginTop: 10 }}>Every bank line finds its document.</div>
      </div>
      {PAIRS.map((pair, i) => (
        <Sequence key={pair.bank.id} from={PAIR_STARTS[i]} durationInFrames={PAIR_LENS[i]} layout="none">
          <PairView pair={pair} len={PAIR_LENS[i]} />
        </Sequence>
      ))}
      <Progress />
    </Stage>
  );
};
