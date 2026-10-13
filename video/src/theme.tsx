import React from "react";
import { loadFont } from "@remotion/google-fonts/Inter";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

const inter = loadFont("normal", { weights: ["400", "500", "600", "700", "800"], subsets: ["latin"] });
const mono = loadMono("normal", { weights: ["400", "500"], subsets: ["latin"] });

export const FONT = inter.fontFamily;
export const MONO = mono.fontFamily;

// Palette mirrors the live app (src/lovelight/static/styles.css).
export const C = {
  bg: "#07080d",
  bg2: "#0b0d14",
  panel: "rgba(255,255,255,0.035)",
  panel2: "rgba(255,255,255,0.06)",
  border: "rgba(255,255,255,0.075)",
  border2: "rgba(255,255,255,0.14)",
  text: "#eceef4",
  muted: "#8a90a2",
  faint: "#5b6072",
  violet: "#8b6cff",
  blue: "#5b8cff",
  cyan: "#3dd6f5",
  green: "#34d399",
  amber: "#fbbf24",
  red: "#f87171",
  grad: "linear-gradient(135deg, #8b6cff 0%, #5b8cff 50%, #3dd6f5 100%)",
};

export const FPS = 30;

/** Swedish money format: "1 234,50 kr" (narrow no-break space as thousands separator). */
export const sek = (n: number, withUnit = true) => {
  const neg = n < 0;
  const [int, dec] = Math.abs(n).toFixed(2).split(".");
  const grouped = int.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${neg ? "−" : ""}${grouped},${dec}${withUnit ? " kr" : ""}`;
};

export const useSpring = (delay = 0, config: { damping?: number; mass?: number; stiffness?: number } = {}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - delay, fps, config: { damping: 18, mass: 0.8, stiffness: 120, ...config } });
};

export const fade = (frame: number, start: number, dur = 12) =>
  interpolate(frame, [start, start + dur], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

export const fadeOut = (frame: number, start: number, dur = 12) =>
  interpolate(frame, [start, start + dur], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

export const Stage: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({ children, style }) => (
  <AbsoluteFill
    style={{
      background: `radial-gradient(1200px 700px at 50% -10%, rgba(139,108,255,0.10), transparent 60%), ${C.bg}`,
      fontFamily: FONT,
      color: C.text,
      fontFeatureSettings: '"tnum" 1, "cv11" 1',
      ...style,
    }}
  >
    {children}
  </AbsoluteFill>
);

export const Logo: React.FC<{ size?: number }> = ({ size = 34 }) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: size * 0.29,
      background: C.grad,
      display: "grid",
      placeItems: "center",
      boxShadow: `0 0 ${size * 0.7}px rgba(139,108,255,0.45)`,
    }}
  >
    <div
      style={{
        width: size * 0.35,
        height: size * 0.35,
        borderRadius: "50%",
        background: "#fff",
        boxShadow: `0 0 ${size * 0.4}px #fff`,
      }}
    />
  </div>
);

export const Wordmark: React.FC<{ size?: number }> = ({ size = 34 }) => (
  <div style={{ display: "flex", alignItems: "center", gap: size * 0.45 }}>
    <Logo size={size * 1.4} />
    <div style={{ fontSize: size * 1.3, fontWeight: 700, letterSpacing: "-0.035em" }}>Lovelight</div>
  </div>
);

export const Eyebrow: React.FC<{ children: React.ReactNode; color?: string; style?: React.CSSProperties }> = ({
  children,
  color = C.muted,
  style,
}) => (
  <div
    style={{
      fontSize: 20,
      fontWeight: 600,
      letterSpacing: "0.14em",
      textTransform: "uppercase",
      color,
      ...style,
    }}
  >
    {children}
  </div>
);

export const Check: React.FC<{ size?: number; color?: string; progress?: number }> = ({
  size = 22,
  color = C.green,
  progress = 1,
}) => (
  <svg width={size} height={size} viewBox="0 0 24 24">
    <circle cx="12" cy="12" r="11" fill={color} opacity={0.18 * progress} />
    <path
      d="M7 12.5l3.2 3.2L17 9"
      fill="none"
      stroke={color}
      strokeWidth={2.4}
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeDasharray={20}
      strokeDashoffset={20 * (1 - progress)}
    />
  </svg>
);

export const Pill: React.FC<{ color: string; children: React.ReactNode; style?: React.CSSProperties }> = ({
  color,
  children,
  style,
}) => (
  <div
    style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 8,
      padding: "6px 14px",
      borderRadius: 999,
      background: `${color}1f`,
      border: `1px solid ${color}55`,
      color,
      fontWeight: 600,
      fontSize: 18,
      ...style,
    }}
  >
    {children}
  </div>
);
