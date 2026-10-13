import React from "react";
import { Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { DOCS, Doc } from "../data";
import { C, Check, Eyebrow, Logo, MONO, Stage, fade, fadeOut, sek } from "../theme";

export const INBOX_FRAMES = 240;

const COLS = 6;
const CARD_W = 220;
const CARD_H = 196;
const GAP = 16;
const GRID_X = 450;
const GRID_Y = 170;

const SOURCES = {
  email: { y: 330, label: "Email", sub: "inbox@lovelight.se", icon: "✉" },
  upload: { y: 540, label: "Batch drop", sub: "one drag · any format", icon: "⇪" },
  photo: { y: 750, label: "Phone photos", sub: "IMG_4471 · 4502 · 4538", icon: "◉" },
} as const;

export const arriveAt = (i: number) => 14 + i * 4;

type Stage4 = { label: string; color: string };
const statusOf = (doc: Doc, t: number): Stage4 => {
  if (t < 30) return { label: "Received", color: C.muted };
  if (t < 55) return { label: "Extracted", color: C.violet };
  if (doc.flag) return { label: doc.flag, color: C.red };
  if (t < 75) return { label: "Matched", color: C.cyan };
  return { label: "Posted", color: C.green };
};

const Card: React.FC<{ doc: Doc; i: number }> = ({ doc, i }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = arriveAt(i);
  const p = spring({ frame: frame - a, fps, config: { damping: 17, stiffness: 110, mass: 0.9 } });
  const col = i % COLS;
  const row = Math.floor(i / COLS);
  const tx = GRID_X + col * (CARD_W + GAP);
  const ty = GRID_Y + row * (CARD_H + GAP);
  const sx = 150;
  const sy = SOURCES[doc.source].y - 60;
  const x = interpolate(p, [0, 1], [sx, tx]);
  const y = interpolate(p, [0, 1], [sy, ty]);
  const st = statusOf(doc, frame - a);
  const posted = st.label === "Posted";
  const checkP = interpolate(frame - a, [75, 85], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const amount = doc.currency === "SEK" ? sek(doc.gross) : `${sek(doc.gross, false)} ${doc.currency}`;

  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: CARD_W,
        height: CARD_H,
        opacity: frame < a ? 0 : Math.min(1, p * 2),
        transform: `scale(${0.55 + 0.45 * p})`,
        transformOrigin: "top left",
        borderRadius: 14,
        background: C.bg2,
        border: `1px solid ${doc.flag && frame - a >= 55 ? `${C.red}88` : C.border2}`,
        boxShadow: doc.flag && frame - a >= 55 ? `0 0 28px ${C.red}33` : "0 10px 30px rgba(0,0,0,0.35)",
        overflow: "hidden",
      }}
    >
      <div style={{ height: 92, background: "#e9e9ee", overflow: "hidden", position: "relative" }}>
        {doc.img ? (
          <Img src={staticFile(`docs/${doc.img}`)} style={{ width: "100%", objectFit: "cover", objectPosition: "top" }} />
        ) : (
          <div style={{ height: "100%", display: "grid", placeItems: "center", background: "#1a1d2a", color: C.cyan, fontSize: 38 }}>✉</div>
        )}
      </div>
      <div style={{ padding: "10px 12px" }}>
        <div style={{ fontSize: 15, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{doc.vendor}</div>
        <div style={{ fontFamily: MONO, fontSize: 14, color: C.muted, marginTop: 2 }}>{amount}</div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 8 }}>
          <div
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: st.color,
              background: `${st.color}1c`,
              border: `1px solid ${st.color}44`,
              padding: "3px 10px",
              borderRadius: 999,
            }}
          >
            {st.label}
          </div>
          {posted ? <Check size={22} progress={checkP} /> : null}
        </div>
      </div>
    </div>
  );
};

const Source: React.FC<{ k: keyof typeof SOURCES; delay: number }> = ({ k, delay }) => {
  const frame = useCurrentFrame();
  const s = SOURCES[k];
  return (
    <div
      style={{
        position: "absolute",
        left: 80,
        top: s.y - 60,
        width: 300,
        padding: "20px 22px",
        borderRadius: 16,
        background: C.panel,
        border: `1px solid ${C.border}`,
        opacity: fade(frame, delay, 12),
        display: "flex",
        gap: 16,
        alignItems: "center",
      }}
    >
      <div style={{ width: 48, height: 48, borderRadius: 12, background: C.panel2, display: "grid", placeItems: "center", fontSize: 24, color: C.cyan }}>
        {s.icon}
      </div>
      <div>
        <div style={{ fontSize: 20, fontWeight: 600 }}>{s.label}</div>
        <div style={{ fontSize: 14, color: C.muted, fontFamily: MONO, marginTop: 2 }}>{s.sub}</div>
      </div>
    </div>
  );
};

export const Inbox: React.FC = () => {
  const frame = useCurrentFrame();
  const received = DOCS.filter((_, i) => frame >= arriveAt(i)).length;
  const posted = DOCS.filter((d, i) => !d.flag && frame - arriveAt(i) >= 75).length;
  const held = DOCS.filter((d, i) => d.flag && frame - arriveAt(i) >= 55).length;
  const out = fadeOut(frame, INBOX_FRAMES - 12, 12);

  return (
    <Stage style={{ opacity: out }}>
      <div style={{ position: "absolute", left: 80, top: 56, display: "flex", alignItems: "center", gap: 18, opacity: fade(frame, 0) }}>
        <Logo size={40} />
        <div>
          <div style={{ fontSize: 30, fontWeight: 700, letterSpacing: "-0.02em" }}>Inbox</div>
          <div style={{ fontSize: 16, color: C.muted }}>Lovelight Design AB · Sep–Oct 2026</div>
        </div>
      </div>
      <div style={{ position: "absolute", right: 80, top: 66, display: "flex", gap: 28, fontSize: 22, fontWeight: 600, opacity: fade(frame, 6) }}>
        <span>
          <span style={{ color: C.muted, fontWeight: 500 }}>Received </span>
          {received}
        </span>
        <span style={{ color: C.green }}>
          <span style={{ color: C.muted, fontWeight: 500 }}>Posted </span>
          {posted}
        </span>
        <span style={{ color: held ? C.red : C.text }}>
          <span style={{ color: C.muted, fontWeight: 500 }}>Held </span>
          {held}
        </span>
        <span>
          <span style={{ color: C.muted, fontWeight: 500 }}>Typed </span>0
        </span>
      </div>
      <div style={{ position: "absolute", left: 80, top: 200 }}>
        <Eyebrow style={{ opacity: fade(frame, 0) }}>Sources</Eyebrow>
      </div>
      <Source k="email" delay={2} />
      <Source k="upload" delay={6} />
      <Source k="photo" delay={10} />
      {DOCS.map((d, i) => (
        <Card key={d.file} doc={d} i={i} />
      ))}
    </Stage>
  );
};
