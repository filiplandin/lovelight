import React from "react";
import { AbsoluteFill, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT, MONO } from "../theme";

export const W = 1080;
export const H = 1350;
// Caption band y 80-330, content y 360-1220. LinkedIn's own UI covers the bottom; no text below SAFE_BOTTOM.
export const CAP = { top: 80, height: 250, side: 60 };
export const BOX = { left: 36, top: 360, width: W - 72, height: 860 };
export const SAFE_BOTTOM = H - 180;

export const GRAD_TEXT: React.CSSProperties = {
  background: C.grad,
  WebkitBackgroundClip: "text",
  backgroundClip: "text",
  color: "transparent",
};

export const LStage: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({ children, style }) => (
  <AbsoluteFill
    style={{
      background: `radial-gradient(900px 620px at 50% -8%, rgba(139,108,255,0.16), transparent 62%), radial-gradient(800px 500px at 50% 112%, rgba(61,214,245,0.07), transparent 60%), ${C.bg}`,
      fontFamily: FONT,
      color: C.text,
      fontFeatureSettings: '"tnum" 1, "cv11" 1',
      ...style,
    }}
  >
    {children}
  </AbsoluteFill>
);

type Tone = "grad" | "red" | "green" | "plain";
const MARK: Record<string, Tone> = { "*": "grad", "!": "red", "+": "green" };

/** "1 payment. | *Matched.*" -> words with tones. *grad*, !red!, +green+ wrap whole words; "|" breaks the line,
 * "~" glues two words (no wrap between them). */
const parse = (text: string) => {
  const out: { w: string; tone: Tone; br?: boolean }[] = [];
  let tone: Tone = "plain";
  for (const raw of text.split(/\s+/)) {
    if (raw === "|") {
      if (out.length) out[out.length - 1].br = true;
      continue;
    }
    if (!raw) continue;
    let w = raw.replace(/~/g, "\u00a0");
    let t = tone;
    const open = w.length > 1 ? MARK[w[0]] : undefined;
    if (open && tone === "plain") {
      tone = open;
      t = open;
      w = w.slice(1);
    }
    const close = w.length > 0 ? MARK[w[w.length - 1]] : undefined;
    if (close && tone !== "plain") {
      w = w.slice(0, -1);
      tone = "plain";
    }
    out.push({ w, tone: t });
  }
  return out;
};

const toneStyle = (t: Tone): React.CSSProperties =>
  t === "grad" ? GRAD_TEXT : t === "red" ? { color: C.red } : t === "green" ? { color: C.green } : { color: C.text };

/** Caption band: white Inter 800, max 2 lines, key words toned. Words rise in with a quick stagger. */
export const Caption: React.FC<{ text: string; size?: number; delay?: number; still?: boolean; shake?: number }> = ({
  text,
  size = 78,
  delay = 0,
  still = false,
  shake = -1,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const words = parse(text);
  const dx = shake >= 0 ? Math.sin((frame - shake) * 2.2) * interpolate(frame - shake, [0, 14], [10, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) * (frame >= shake ? 1 : 0) : 0;
  return (
    <div
      style={{
        position: "absolute",
        left: CAP.side,
        right: CAP.side,
        top: CAP.top,
        height: CAP.height,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
        transform: `translateX(${dx}px)`,
      }}
    >
      <div style={{ fontSize: size, fontWeight: 800, lineHeight: 1.06, letterSpacing: "-0.035em", textWrap: "balance", fontFeatureSettings: '"cv11" 1' } as React.CSSProperties}>
        {words.map((w, i) => {
          const p = still ? 1 : spring({ frame: frame - delay - i * 2, fps, config: { damping: 16, stiffness: 190, mass: 0.6 } });
          return (
            <React.Fragment key={i}>
              <span
                style={{
                  display: "inline-block",
                  opacity: Math.min(1, p * 1.4),
                  transform: `translateY(${(1 - p) * 26}px)`,
                  ...toneStyle(w.tone),
                }}
              >
                {w.w}
              </span>
              {w.br ? <br /> : i < words.length - 1 ? " " : null}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};

export const Panel: React.FC<{ style?: React.CSSProperties; children: React.ReactNode; glow?: string }> = ({ style, children, glow }) => (
  <div
    style={{
      borderRadius: 26,
      background: C.bg2,
      border: `1.5px solid ${glow ? `${glow}88` : C.border2}`,
      boxShadow: glow ? `0 0 50px ${glow}33, 0 24px 70px rgba(0,0,0,0.5)` : "0 24px 70px rgba(0,0,0,0.5)",
      boxSizing: "border-box",
      ...style,
    }}
  >
    {children}
  </div>
);

export const Mono: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({ children, style }) => (
  <span style={{ fontFamily: MONO, fontWeight: 500, letterSpacing: "-0.01em", ...style }}>{children}</span>
);

export const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
export const ramp = (frame: number, a: number, b: number) =>
  interpolate(frame, [a, b], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

/** Thick check / cross used across shots. */
export const Tick: React.FC<{ ok: boolean; size?: number; p?: number }> = ({ ok, size = 48, p = 1 }) => {
  const col = ok ? C.green : C.red;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" style={{ flexShrink: 0 }}>
      <circle cx="12" cy="12" r="11" fill={col} opacity={0.18 * p} />
      {ok ? (
        <path d="M7 12.5l3.2 3.2L17 9" fill="none" stroke={col} strokeWidth={2.6} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={20} strokeDashoffset={20 * (1 - p)} />
      ) : (
        <path d="M8.5 8.5l7 7M15.5 8.5l-7 7" fill="none" stroke={col} strokeWidth={2.6} strokeLinecap="round" strokeDasharray={20} strokeDashoffset={20 * (1 - p)} />
      )}
    </svg>
  );
};

/** Fades its children in over `fade` frames from `from`; used to cut between two segments of one recording. */
export const Cut: React.FC<{ from: number; dur: number; fade?: number; children: React.ReactNode }> = ({ from, dur, fade = 5, children }) => {
  const frame = useCurrentFrame();
  return (
    <Sequence from={from} durationInFrames={dur} layout="none">
      <AbsoluteFill style={{ opacity: fade > 0 ? ramp(frame, from, from + fade) : 1 }}>{children}</AbsoluteFill>
    </Sequence>
  );
};
