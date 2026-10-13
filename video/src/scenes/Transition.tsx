import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { C, Eyebrow, Stage, Wordmark, fade, fadeOut, useSpring } from "../theme";

export const TRANSITION_FRAMES = 90;

export const Transition: React.FC = () => {
  const frame = useCurrentFrame();
  const sweep = interpolate(frame, [0, 34], [-0.4, 1.4], { extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
  const logo = useSpring(18, { damping: 14 });
  const glow = interpolate(frame, [14, 30, 70], [0, 1, 0.55], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const out = fadeOut(frame, TRANSITION_FRAMES - 12, 12);

  return (
    <Stage>
      <AbsoluteFill
        style={{
          background: `radial-gradient(900px 500px at 50% 50%, rgba(139,108,255,${0.35 * glow}), rgba(61,214,245,${0.08 * glow}) 45%, transparent 70%)`,
        }}
      />
      {/* diagonal light sweep */}
      <AbsoluteFill
        style={{
          background: `linear-gradient(105deg, transparent ${sweep * 100 - 18}%, rgba(255,255,255,0.0) ${sweep * 100 - 10}%, rgba(200,190,255,0.55) ${sweep * 100}%, rgba(61,214,245,0.25) ${sweep * 100 + 4}%, transparent ${sweep * 100 + 14}%)`,
          mixBlendMode: "screen",
        }}
      />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: out }}>
        <div style={{ transform: `scale(${0.8 + 0.2 * logo})`, opacity: logo }}>
          <Wordmark size={84} />
        </div>
        <div style={{ marginTop: 40, opacity: fade(frame, 40, 14) }}>
          <Eyebrow color={C.muted}>AI bookkeeping for accounting bureaus</Eyebrow>
        </div>
      </AbsoluteFill>
    </Stage>
  );
};
