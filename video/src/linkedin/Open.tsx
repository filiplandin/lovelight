// Shots 1-4: hook, two pains, bridge. All motion graphics.
import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, random, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { C, Logo, sek } from "../theme";
import { LI_DOCS, LUMP, LUMP_DOCS } from "./facts";
import { BOX, Caption, GRAD_TEXT, LStage, Mono, Panel, Tick, W, ramp } from "./ui";

// ---------------------------------------------------------------- shared bank card

export const BANK_TOP = 400;
const BANK_H = 168;

export const BankCard: React.FC<{ scale?: number; style?: React.CSSProperties; who?: number; matched?: number }> = ({
  scale = 1,
  style,
  who = 0,
  matched = 0,
}) => (
  <Panel
    glow={matched > 0.5 ? C.green : undefined}
    style={{
      position: "absolute",
      left: 90,
      width: W - 180,
      top: BANK_TOP,
      height: BANK_H,
      padding: "26px 36px",
      transform: `scale(${scale})`,
      transformOrigin: "50% 0%",
      ...style,
    }}
  >
    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 24, color: C.muted, fontWeight: 500 }}>
      <span>Bank · 1930</span>
      <Mono>
        {LUMP.id} · {LUMP.date}
      </Mono>
    </div>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginTop: 26 }}>
      <span style={{ position: "relative" }}>
        <Mono style={{ fontSize: 44 }}>{LUMP.text}</Mono>
        {who > 0 ? (
          <span
            style={{
              position: "absolute",
              left: "100%",
              top: -30,
              marginLeft: 12,
              padding: "4px 14px",
              borderRadius: 999,
              background: `${C.amber}22`,
              border: `1.5px solid ${C.amber}88`,
              color: C.amber,
              fontSize: 26,
              fontWeight: 700,
              opacity: who,
              transform: `scale(${0.6 + 0.4 * who}) rotate(-4deg)`,
            }}
          >
            who?
          </span>
        ) : null}
      </span>
      <Mono style={{ fontSize: 44 }}>{sek(LUMP.amount)}</Mono>
    </div>
  </Panel>
);

// ---------------------------------------------------------------- 1. hook

const DOC_TOP = 630;
const DOC_H = 112;
const DOC_GAP = 22;
const TRUNK_X = 130;
const docY = (k: number) => DOC_TOP + k * (DOC_H + DOC_GAP);
export const lineStart = (k: number) => 8 + k * 6;
const landAt = (k: number) => lineStart(k) + 10;
export const HOOK_DONE = landAt(LUMP_DOCS.length - 1) + 8;

/** Bank line -> 3 invoices -> sum. frame 0 already shows caption + bank card (LinkedIn thumbnail / loop point). */
export const MatchGraphic: React.FC<{ frame: number; fps: number; still?: boolean }> = ({ frame, fps, still }) => {
  const push = still ? 1 : interpolate(frame, [0, 60], [1, 1.04], { extrapolateRight: "clamp", easing: Easing.out(Easing.quad) });
  // Running total steps by each invoice's gross as it lands, so the counter only ever shows real partial sums.
  const landed = LUMP_DOCS.filter((_, k) => frame >= landAt(k) + 2);
  const total = landed.reduce((s, d) => s + d.gross, 0);
  const bump = landed.length ? 1 + 0.06 * (1 - ramp(frame, landAt(landed.length - 1) + 2, landAt(landed.length - 1) + 7)) : 1;
  const done = ramp(frame, HOOK_DONE - 4, HOOK_DONE);
  return (
    <>
      <BankCard scale={push} matched={done} />
      <svg width={W} height={1350} style={{ position: "absolute", inset: 0 }}>
        <defs>
          <linearGradient id="hookln" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor={C.violet} />
            <stop offset="1" stopColor={C.cyan} />
          </linearGradient>
        </defs>
        {LUMP_DOCS.map((_, k) => {
          const y1 = docY(k) + DOC_H / 2;
          const draw = interpolate(frame, [lineStart(k), lineStart(k) + 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const y0 = BANK_TOP + BANK_H;
          const d = `M ${TRUNK_X} ${y0} L ${TRUNK_X} ${y1 - 40} Q ${TRUNK_X} ${y1} ${TRUNK_X + 40} ${y1} L 196 ${y1}`;
          return <path key={k} d={d} stroke="url(#hookln)" strokeWidth={6} fill="none" strokeLinecap="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw} style={{ filter: `drop-shadow(0 0 10px ${C.violet}88)` }} />;
        })}
        <circle cx={TRUNK_X} cy={BANK_TOP + BANK_H} r={10 * ramp(frame, lineStart(0), lineStart(0) + 3)} fill={C.violet} />
      </svg>
      {LUMP_DOCS.map((d, k) => {
        const p = spring({ frame: frame - lineStart(k) - 4, fps, config: { damping: 16, stiffness: 170 } });
        const landed = ramp(frame, lineStart(k) + 10, lineStart(k) + 14);
        return (
          <Panel
            key={d.ref}
            glow={landed > 0.5 ? C.green : undefined}
            style={{
              position: "absolute",
              left: 196,
              right: 90,
              top: docY(k),
              height: DOC_H,
              padding: "0 30px 0 0",
              display: "flex",
              alignItems: "center",
              gap: 24,
              overflow: "hidden",
              opacity: still ? 0.32 : 0.32 + 0.68 * Math.min(1, p * 1.5),
              transform: `translateX(${(1 - p) * 24}px)`,
            }}
          >
            <div style={{ width: 92, height: DOC_H, background: "#ececf1", flexShrink: 0, overflow: "hidden" }}>
              <Img src={staticFile(`docs/${d.img}`)} style={{ width: "100%", objectFit: "cover", objectPosition: "top" }} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 34, fontWeight: 700, letterSpacing: "-0.02em", whiteSpace: "nowrap" }}>{d.short}</div>
              <Mono style={{ fontSize: 22, color: C.cyan }}>No. {d.ref}</Mono>
            </div>
            <Mono style={{ fontSize: 36 }}>{sek(d.gross, false)}</Mono>
            <Tick ok size={44} p={landed} />
          </Panel>
        );
      })}
      <div
        style={{
          position: "absolute",
          left: 90,
          right: 90,
          top: docY(3) + 6,
          height: 96,
          display: "flex",
          alignItems: "center",
          justifyContent: "flex-end",
          gap: 40,
          opacity: ramp(frame, landAt(0) - 2, landAt(0) + 2),
        }}
      >
        <span style={{ fontSize: 30, color: C.muted, fontWeight: 600 }}>Sum</span>
        <Mono style={{ fontSize: 60, color: done > 0.5 ? C.green : C.text, display: "inline-block", transform: `scale(${bump})`, transformOrigin: "100% 50%" }}>{sek(total)}</Mono>
        <Tick ok size={64} p={done} />
      </div>
    </>
  );
};

export const Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <LStage>
      <Caption text="1 payment. 3~invoices. | *Matched.*" still />
      <MatchGraphic frame={frame} fps={fps} />
    </LStage>
  );
};

// ---------------------------------------------------------------- 2. the hunt

const THUMBS = LI_DOCS.filter((d) => d.img).map((d) => d.img as string);
const COLS = 5;
const TW = 176;
const TH = 236;
const TG = 16;

export const Hunt: React.FC = () => {
  const frame = useCurrentFrame();
  const glitch = frame < 7 ? 1 - frame / 7 : 0;
  const drift = interpolate(frame, [0, 90], [0, -620]);
  const who = spring({ frame: frame - 14, fps: 30, config: { damping: 11, stiffness: 160 } });
  // Cursor hops between random cards; each hop eased.
  const hop = Math.floor(frame / 14);
  const t = Easing.inOut(Easing.cubic)(Math.min(1, (frame % 14) / 10));
  const pt = (h: number) => [120 + random(`x${h}`) * 820, 760 + random(`y${h}`) * 360];
  const [ax, ay] = pt(hop);
  const [bx, by] = pt(hop + 1);
  const cx = ax + (bx - ax) * t;
  const cy = ay + (by - ay) * t;
  const gridW = COLS * TW + (COLS - 1) * TG;
  return (
    <LStage>
      <Caption text="Lump-sum payment. | Now go *find the invoices.*" />
      <div style={{ position: "absolute", left: BOX.left, top: 600, width: BOX.width, height: 620, overflow: "hidden", maskImage: "linear-gradient(180deg, transparent, #000 14%, #000 82%, transparent)" }}>
        <div style={{ position: "absolute", left: (BOX.width - gridW) / 2, top: 20 + drift + 300, width: gridW, display: "flex", flexWrap: "wrap", gap: TG }}>
          {Array.from({ length: 40 }).map((_, i) => (
            <div key={i} style={{ width: TW, height: TH, borderRadius: 14, overflow: "hidden", background: "#ececf1", opacity: 0.85, border: `1px solid ${C.border2}` }}>
              <Img src={staticFile(`docs/${THUMBS[(i * 7) % THUMBS.length]}`)} style={{ width: "100%", objectFit: "cover", objectPosition: "top" }} />
            </div>
          ))}
        </div>
      </div>
      <div style={{ transform: `translateX(${glitch * 24 * Math.sin(frame * 3)}px)`, filter: glitch ? `drop-shadow(${6 * glitch}px 0 0 ${C.red}) drop-shadow(${-6 * glitch}px 0 0 ${C.cyan})` : undefined }}>
        <BankCard who={who} />
      </div>
      <svg width={40} height={40} viewBox="0 0 24 24" style={{ position: "absolute", left: cx, top: cy, filter: "drop-shadow(0 3px 8px rgba(0,0,0,.6))" }}>
        <path d="M4 2l15 9.5-6.6 1.4L16 21l-3.2 1.4-3.6-8.2L4 18z" fill="#fff" stroke="#07080d" strokeWidth={1.2} strokeLinejoin="round" />
      </svg>
      {glitch > 0 ? <AbsoluteFill style={{ background: `repeating-linear-gradient(0deg, rgba(255,255,255,${0.05 * glitch}) 0 2px, transparent 2px 6px)` }} /> : null}
    </LStage>
  );
};

// ---------------------------------------------------------------- 3. black box

export const BlackBox: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const box = spring({ frame: frame - 2, fps, config: { damping: 15 } });
  const outP = spring({ frame: frame - 26, fps, config: { damping: 13, stiffness: 150 } });
  const pulse = frame > 44 ? 0.5 + 0.5 * Math.sin((frame - 44) / 4) : 0;
  const red = ramp(frame, 44, 52);
  const qs = ["Which rule?", "Which document?", "Who approved?"];
  return (
    <LStage>
      <Caption text="And AI you can't audit? | !No thanks.!" shake={50} />
      {/* docs flying in */}
      {[0, 1, 2].map((k) => {
        const p = interpolate(frame, [4 + k * 5, 22 + k * 5], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.in(Easing.quad) });
        return (
          <div
            key={k}
            style={{
              position: "absolute",
              left: interpolate(p, [0, 1], [70, 420]),
              top: 560 + k * 70 + p * (150 - k * 70),
              width: 120,
              height: 160,
              borderRadius: 10,
              overflow: "hidden",
              background: "#ececf1",
              opacity: p < 0.95 ? 1 : 0,
              transform: `scale(${1 - 0.5 * p}) rotate(${(k - 1) * 8}deg)`,
            }}
          >
            <Img src={staticFile(`docs/${LUMP_DOCS[k].img}`)} style={{ width: "100%" }} />
          </div>
        );
      })}
      <div
        style={{
          position: "absolute",
          left: 540 - 190,
          top: 560,
          width: 380,
          height: 380,
          borderRadius: 34,
          background: "linear-gradient(160deg, #1a1b22, #050507)",
          border: `3px solid ${red ? `rgba(248,113,113,${0.4 + 0.6 * pulse})` : "#26272f"}`,
          boxShadow: red ? `0 0 ${50 + 50 * pulse}px rgba(248,113,113,${0.25 + 0.25 * pulse}), inset 0 2px 0 rgba(255,255,255,.06)` : "0 40px 90px rgba(0,0,0,.7), inset 0 2px 0 rgba(255,255,255,.06)",
          display: "grid",
          placeItems: "center",
          transform: `scale(${0.8 + 0.2 * box})`,
          opacity: box,
        }}
      >
        <div style={{ fontSize: 150, fontWeight: 800, letterSpacing: "-0.05em", color: "#2c2d36" }}>AI</div>
      </div>
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 990,
          display: "flex",
          justifyContent: "center",
          opacity: outP,
          transform: `translateY(${(1 - outP) * -60}px)`,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14, padding: "14px 30px", borderRadius: 999, background: `${C.green}1c`, border: `2px solid ${C.green}66`, color: C.green, fontSize: 40, fontWeight: 700 }}>
          Posted <Tick ok size={44} />
        </div>
      </div>
      {qs.map((q, i) => {
        const p = spring({ frame: frame - 40 - i * 6, fps, config: { damping: 14 } });
        const pos = [
          [70, 420],
          [720, 470],
          [60, 1080],
        ][i];
        return (
          <div key={q} style={{ position: "absolute", left: pos[0], top: pos[1], fontSize: 32, fontWeight: 700, color: C.red, opacity: p, transform: `scale(${0.7 + 0.3 * p}) rotate(${(i - 1) * -4}deg)` }}>
            {q}
          </div>
        );
      })}
    </LStage>
  );
};

// ---------------------------------------------------------------- 4. bridge

export const Bridge: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: frame - 2, fps, config: { damping: 13, stiffness: 120 } });
  const glow = ramp(frame, 0, 30);
  return (
    <LStage>
      <AbsoluteFill style={{ background: `radial-gradient(600px 460px at 50% 56%, rgba(139,108,255,${0.3 * glow}), transparent 70%)` }} />
      <Caption text="Every number | *shows its work.*" />
      <div style={{ position: "absolute", left: 0, right: 0, top: 560, display: "flex", flexDirection: "column", alignItems: "center", gap: 46, opacity: p, transform: `scale(${0.82 + 0.18 * p})` }}>
        <Logo size={170} />
        <div style={{ fontSize: 120, fontWeight: 800, letterSpacing: "-0.045em" }}>Lovelight</div>
      </div>
      <div style={{ position: "absolute", left: 80, right: 80, top: 1020, textAlign: "center", fontSize: 34, color: C.muted, fontWeight: 500, lineHeight: 1.4, opacity: ramp(frame, 14, 26) }}>
        AI bookkeeping for accounting firms
        <br />
        <span style={GRAD_TEXT}>Fortnox / Visma</span>
      </div>
    </LStage>
  );
};

