import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { C, FONT, Stage, Wordmark, fade, useSpring } from "../theme";

export const OUTRO_FRAMES = 150;

const STATS = [
  { v: 23, label: "documents" },
  { v: 36, label: "bank lines" },
  { v: 0, label: "typed" },
  { v: 4, label: "minutes" },
];

export const Outro: React.FC = () => {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [6, 44], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  const mark = useSpring(70, { damping: 15 });
  const glow = interpolate(frame, [60, 110], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <Stage>
      <AbsoluteFill style={{ background: `radial-gradient(900px 500px at 50% 70%, rgba(139,108,255,${0.22 * glow}), transparent 70%)` }} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column" }}>
        <div style={{ display: "flex", gap: 90, alignItems: "flex-end" }}>
          {STATS.map((s, i) => (
            <div key={s.label} style={{ textAlign: "center", opacity: fade(frame, i * 5, 12) }}>
              <div
                style={{
                  fontFamily: FONT,
                  fontVariantNumeric: "tabular-nums",
                  fontSize: 120,
                  fontWeight: 700,
                  letterSpacing: "-0.04em",
                  color: s.v === 0 ? C.green : C.text,
                }}
              >
                {Math.round(s.v * t)}
              </div>
              <div style={{ fontSize: 24, color: C.muted, marginTop: 4, letterSpacing: "0.04em" }}>{s.label}</div>
            </div>
          ))}
        </div>
        <div style={{ marginTop: 70, fontSize: 40, fontWeight: 600, letterSpacing: "-0.02em", opacity: fade(frame, 46, 14) }}>
          AI proposes, <span style={{ color: C.cyan }}>code disposes</span>, <span style={{ color: C.green }}>accountant approves.</span>
        </div>
        <div style={{ marginTop: 70, opacity: mark, transform: `scale(${0.9 + 0.1 * mark})` }}>
          <Wordmark size={46} />
        </div>
      </AbsoluteFill>
    </Stage>
  );
};
