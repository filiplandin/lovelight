import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { INJECTION } from "../data";
import { C, Eyebrow, MONO, Stage, fade, fadeOut, useSpring } from "../theme";

export const TRUST_FRAMES = 270;
export const TRUST_CARD_DELAYS = [12, 30, 50, 90, 108];
const TYPE_START = 64;
const TYPE_END = 150;

const AlertCard: React.FC<{
  delay: number;
  title: string;
  tag: string;
  x: number;
  y: number;
  w: number;
  h: number;
  children: React.ReactNode;
}> = ({ delay, title, tag, x, y, w, h, children }) => {
  const frame = useCurrentFrame();
  const p = useSpring(delay, { damping: 15 });
  const pulse = 0.6 + 0.4 * Math.sin((frame - delay) / 9);
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: w,
        height: h,
        boxSizing: "border-box",
        padding: "26px 30px",
        borderRadius: 20,
        background: "linear-gradient(180deg, rgba(248,113,113,0.10), rgba(248,113,113,0.03)), #0d0a0e",
        border: `1px solid ${C.red}88`,
        boxShadow: `0 0 ${40 + 20 * pulse}px rgba(248,113,113,${0.18 + 0.1 * pulse}), inset 0 1px 0 rgba(255,255,255,0.05)`,
        opacity: p,
        transform: `scale(${0.92 + 0.08 * p}) translateY(${(1 - p) * 30}px)`,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 12, height: 12, borderRadius: "50%", background: C.red, boxShadow: `0 0 14px ${C.red}` }} />
          <div style={{ fontSize: 26, fontWeight: 700, letterSpacing: "-0.01em" }}>{title}</div>
        </div>
        <div style={{ fontSize: 14, fontWeight: 600, color: C.red, border: `1px solid ${C.red}55`, padding: "3px 10px", borderRadius: 999, whiteSpace: "nowrap" }}>
          {tag}
        </div>
      </div>
      <div style={{ marginTop: 18 }}>{children}</div>
    </div>
  );
};

const Line: React.FC<{ children: React.ReactNode; mono?: boolean; color?: string; size?: number }> = ({ children, mono, color = C.muted, size = 20 }) => (
  <div style={{ fontFamily: mono ? MONO : undefined, color, fontSize: size, marginTop: 8 }}>{children}</div>
);

export const Trust: React.FC = () => {
  const frame = useCurrentFrame();
  const chars = Math.floor(interpolate(frame, [TYPE_START, TYPE_END], [0, INJECTION.length], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  const blocked = fade(frame, TYPE_END + 2, 8);
  const out = fadeOut(frame, TRUST_FRAMES - 12, 12);

  return (
    <Stage style={{ opacity: out, background: `radial-gradient(1200px 700px at 50% 120%, rgba(248,113,113,0.08), transparent 60%), ${C.bg}` }}>
      <div style={{ position: "absolute", left: 80, top: 70, opacity: fade(frame, 0) }}>
        <Eyebrow color={C.red}>Trust</Eyebrow>
        <div style={{ fontSize: 52, fontWeight: 700, letterSpacing: "-0.03em", marginTop: 10 }}>
          AI proposes. <span style={{ color: C.red }}>Code disposes.</span>
        </div>
      </div>

      <AlertCard delay={TRUST_CARD_DELAYS[0]} title="Bankgiro changed" tag="Held" x={80} y={250} w={470} h={260}>
        <Line color={C.text}>Fastighets AB Ringvägen · hyra okt</Line>
        <Line mono size={26} color={C.text}>
          <span style={{ textDecoration: "line-through", color: C.faint }}>5050-1055</span> → <span style={{ color: C.red }}>5916-4482</span>
        </Line>
        <Line>Payee account differs from last month</Line>
      </AlertCard>

      <AlertCard delay={TRUST_CARD_DELAYS[1]} title="Duplicate invoice" tag="Held" x={80} y={540} w={470} h={260}>
        <Line color={C.text}>Ljungbergs Tryckeri AB</Line>
        <Line mono size={26} color={C.text}>
          #30412 <span style={{ color: C.red }}>≈</span> #30519
        </Line>
        <Line>Same vendor, same amount: 15 500,00 kr</Line>
      </AlertCard>

      <AlertCard delay={TRUST_CARD_DELAYS[2]} title="Prompt injection blocked" tag="Quarantined" x={580} y={250} w={760} h={550}>
        <Line color={C.text}>Nordic Growth Partners · faktura 7781 · via email</Line>
        <div
          style={{
            marginTop: 20,
            padding: "22px 24px",
            borderRadius: 12,
            background: "rgba(248,113,113,0.07)",
            border: `1px dashed ${C.red}66`,
            fontFamily: MONO,
            fontSize: 23,
            lineHeight: 1.5,
            color: C.red,
            minHeight: 210,
          }}
        >
          {INJECTION.slice(0, chars)}
          {chars < INJECTION.length && frame >= TYPE_START ? <span style={{ opacity: Math.floor(frame / 8) % 2 ? 1 : 0 }}>▍</span> : null}
        </div>
        <div style={{ display: "flex", gap: 12, marginTop: 22, opacity: blocked, transform: `translateY(${(1 - blocked) * 10}px)` }}>
          {["No tools for the model", "Never auto-posted", "Sent to accountant"].map((t) => (
            <span key={t} style={{ fontSize: 17, fontWeight: 600, color: C.text, background: C.panel2, border: `1px solid ${C.border2}`, padding: "6px 14px", borderRadius: 999 }}>
              {t}
            </span>
          ))}
        </div>
      </AlertCard>

      <AlertCard delay={TRUST_CARD_DELAYS[3]} title="45M fat-finger" tag="Planted test" x={1370} y={250} w={470} h={260}>
        <Line mono size={28} color={C.red}>
          45 000 000,00 kr
        </Line>
        <Line>Amount far outside vendor history</Line>
      </AlertCard>

      <AlertCard delay={TRUST_CARD_DELAYS[4]} title="Invoice dated 1970" tag="Planted test" x={1370} y={540} w={470} h={260}>
        <Line mono size={28} color={C.red}>
          1970-01-01
        </Line>
        <Line>Outside the fiscal year</Line>
      </AlertCard>

      <div style={{ position: "absolute", bottom: 90, width: "100%", textAlign: "center", fontSize: 32, fontWeight: 600, color: C.text, opacity: fade(frame, 150, 15) }}>
        Every flag goes to the accountant. <span style={{ color: C.muted }}>Nothing posts on its own.</span>
      </div>
    </Stage>
  );
};
