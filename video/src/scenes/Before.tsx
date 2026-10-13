import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, random, staticFile, useCurrentFrame } from "remotion";
import { BANK, DOCS } from "../data";
import { C, Eyebrow, FONT, MONO, fade, sek, useSpring } from "../theme";

export const BEFORE_FRAMES = 450;

const SCATTER = DOCS.filter((d) => d.img).slice(0, 18);

const Scatter: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill>
      {SCATTER.map((d, i) => {
        const delay = i * 3 - 12;
        const p = interpolate(frame - delay, [0, 22], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.out(Easing.back(1.4)),
        });
        const x = 60 + random(`x${i}`) * 1640;
        const y = 40 + random(`y${i}`) * 760;
        const rot = (random(`r${i}`) - 0.5) * 50;
        const drift = Math.sin((frame + i * 20) / 40) * 4;
        const w = d.source === "photo" ? 230 : 200;
        return (
          <div
            key={d.file}
            style={{
              position: "absolute",
              left: x,
              top: y + (1 - p) * -500 + drift,
              width: w,
              transform: `rotate(${rot + (1 - p) * 30}deg)`,
              opacity: p,
              boxShadow: "0 18px 40px rgba(0,0,0,0.55)",
              borderRadius: 4,
              overflow: "hidden",
              background: "#fff",
            }}
          >
            <Img src={staticFile(`docs/${d.img}`)} style={{ width: "100%", display: "block" }} />
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// Window-local coordinates (window is 1300x720).
const BTN = { x: 390, y: 452 };
const ROW_Y = (i: number) => 172 + i * 44 + 22;
const DROP_X = 1170;
const UPLOADS = [
  { img: "IMG_4471.png", vendor: "Restaurang Pelikan", amount: 1344, date: "2026-09-23", konto: "6071" },
  { img: "kvitto_sl_30dagar_sep.png", vendor: "SL", amount: 1060, date: "2026-09-01", konto: "5810" },
  { img: "telia_faktura_88213456.png", vendor: "Telia Sverige AB", amount: 4990, date: "2026-09-20", konto: "6212" },
];
const UPLOAD_START = 90;
const UPLOAD_LEN = 60;
const MATCH_START = 280;
const MATCH_LEN = 56;

const cursorKeys = (() => {
  const k: [number, number, number][] = [[60, 650, 640]];
  UPLOADS.forEach((_, i) => {
    const t = UPLOAD_START + i * UPLOAD_LEN;
    k.push([t + 4, 430, 190], [t + 40, 420, 312], [t + 52, BTN.x, BTN.y]);
  });
  [0, 1, 2].forEach((i) => {
    const t = MATCH_START + i * MATCH_LEN;
    k.push([t + 16, DROP_X, ROW_Y(i)], [t + 26, DROP_X, ROW_Y(i)], [t + 42, DROP_X + 10, ROW_Y(i) + 18 + i * 34 + 17]);
  });
  return k;
})();

const cursorAt = (f: number) => {
  const frames = cursorKeys.map((k) => k[0]);
  const opts = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const, easing: Easing.inOut(Easing.cubic) };
  // Interpolate segment-wise so easing applies to each move.
  let i = frames.findIndex((t) => t > f);
  if (i === -1) i = frames.length - 1;
  if (i === 0) return { x: cursorKeys[0][1], y: cursorKeys[0][2] };
  const [t0, x0, y0] = cursorKeys[i - 1];
  const [t1, x1, y1] = cursorKeys[i];
  return {
    x: interpolate(f, [t0, t1], [x0, x1], opts),
    y: interpolate(f, [t0, t1], [y0, y1], opts),
  };
};

const Cursor: React.FC<{ x: number; y: number; pressed: boolean }> = ({ x, y, pressed }) => (
  <svg
    width={30}
    height={30}
    viewBox="0 0 24 24"
    style={{ position: "absolute", left: x, top: y, transform: `scale(${pressed ? 0.85 : 1})`, zIndex: 20 }}
  >
    <path d="M3 2l7 19 2.5-7.5L20 11z" fill="#111" stroke="#fff" strokeWidth={1.5} strokeLinejoin="round" />
  </svg>
);

const Field: React.FC<{ label: string; value: string; active?: boolean; y: number }> = ({ label, value, active, y }) => (
  <div style={{ position: "absolute", left: 240, top: y, width: 300 }}>
    <div style={{ fontSize: 13, color: "#555", marginBottom: 3 }}>{label}</div>
    <div
      style={{
        height: 30,
        border: `1px solid ${active ? "#5a7aa8" : "#9a9a9a"}`,
        background: "#fff",
        fontSize: 15,
        padding: "5px 8px",
        fontFamily: "Tahoma, Verdana, sans-serif",
        color: "#222",
        boxShadow: "inset 1px 1px 2px rgba(0,0,0,0.15)",
      }}
    >
      {value}
      {active ? <span style={{ borderLeft: "1px solid #222", marginLeft: 1 }} /> : null}
    </div>
  </div>
);

const LegacyWindow: React.FC = () => {
  const frame = useCurrentFrame();
  const enter = useSpring(70, { damping: 16 });
  const cur = cursorAt(frame);

  const upIdx = Math.max(0, Math.min(UPLOADS.length - 1, Math.floor((frame - UPLOAD_START) / UPLOAD_LEN)));
  const local = frame - UPLOAD_START - upIdx * UPLOAD_LEN;
  const up = UPLOADS[upIdx];
  const savedCount = Math.max(0, Math.min(3, Math.floor((frame - UPLOAD_START - 52) / UPLOAD_LEN) + 1));
  const counter = Math.min(63, Math.max(1, savedCount + (frame >= UPLOAD_START ? 1 : 0)));
  const typing = frame >= UPLOAD_START && frame < MATCH_START;
  const vendorTyped = typing ? up.vendor.slice(0, Math.max(0, Math.floor((local - 6) / 1.4))) : "";
  const amountTyped = typing && local > 34 ? sek(up.amount, false).slice(0, Math.floor((local - 34) / 1.5)) : "";
  const dateTyped = typing && local > 30 ? up.date : "";
  const kontoTyped = typing && local > 46 ? up.konto : "";

  const matchedRows = [0, 1, 2].filter((i) => frame >= MATCH_START + i * MATCH_LEN + 44);
  const openRow = [0, 1, 2].find((i) => {
    const t = MATCH_START + i * MATCH_LEN;
    return frame >= t + 26 && frame < t + 44;
  });

  const pressed =
    UPLOADS.some((_, i) => Math.abs(frame - (UPLOAD_START + i * UPLOAD_LEN + 54)) < 3) ||
    [0, 1, 2].some((i) => {
      const t = MATCH_START + i * MATCH_LEN;
      return Math.abs(frame - (t + 27)) < 3 || Math.abs(frame - (t + 43)) < 3;
    });

  const options = ["SL", "Kjell & Company", "Adobe", "Uber B.V.", "Taxi Stockholm"];

  return (
    <div
      style={{
        position: "absolute",
        left: 310,
        top: 170,
        width: 1300,
        height: 720,
        transform: `scale(${0.9 + 0.1 * enter}) translateY(${(1 - enter) * 60}px)`,
        opacity: enter,
        background: "#ece9e2",
        border: "1px solid #7a7a7a",
        boxShadow: "0 40px 120px rgba(0,0,0,0.7)",
        fontFamily: "Tahoma, Verdana, sans-serif",
        color: "#222",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          height: 34,
          background: "linear-gradient(#6d7f99, #4c5d78)",
          color: "#fff",
          fontSize: 15,
          fontWeight: 700,
          display: "flex",
          alignItems: "center",
          padding: "0 12px",
          justifyContent: "space-between",
        }}
      >
        <span>Bokföring 2.4 — Leverantörsunderlag [Lovelight Design AB]</span>
        <span style={{ letterSpacing: 10 }}>_ □ ×</span>
      </div>
      <div style={{ height: 26, borderBottom: "1px solid #b5b2aa", fontSize: 14, display: "flex", gap: 18, padding: "4px 12px" }}>
        {["Arkiv", "Redigera", "Visa", "Register", "Verktyg", "Hjälp"].map((m) => (
          <span key={m}>{m}</span>
        ))}
      </div>

      {/* Left: one-by-one upload */}
      <div style={{ position: "absolute", left: 0, top: 60, width: 560, height: 660, borderRight: "1px solid #b5b2aa" }}>
        <div style={{ position: "absolute", left: 20, top: 14, fontWeight: 700, fontSize: 17 }}>Ladda upp underlag</div>
        <div style={{ position: "absolute", left: 20, top: 44, fontSize: 30, fontWeight: 700, fontFamily: MONO }}>
          Underlag {counter} / 63
        </div>
        <div style={{ position: "absolute", left: 20, top: 90, width: 200, height: 270, background: "#fff", border: "1px solid #999", overflow: "hidden" }}>
          {frame >= UPLOAD_START ? (
            <Img src={staticFile(`docs/${up.img}`)} style={{ width: "100%", opacity: fade(local, 0, 8) }} />
          ) : (
            <div style={{ fontSize: 13, color: "#777", padding: 12 }}>Dra fil hit eller klicka Bläddra…</div>
          )}
        </div>
        <Field label="Leverantör" value={vendorTyped} active={typing && local < 34} y={90} />
        <Field label="Fakturadatum" value={dateTyped} y={146} />
        <Field label="Belopp inkl. moms" value={amountTyped} active={typing && local >= 34 && local < 46} y={202} />
        <Field label="Konto" value={kontoTyped} y={258} />
        <div
          style={{
            position: "absolute",
            left: 240,
            top: BTN.y - 60 - 22,
            width: 300,
            height: 44,
            background: "linear-gradient(#fdfdfd, #d9d6cf)",
            border: "1px solid #707070",
            display: "grid",
            placeItems: "center",
            fontSize: 15,
          }}
        >
          Spara och nästa ›
        </div>
        <div style={{ position: "absolute", left: 20, top: 440, width: 520, height: 18, border: "1px solid #888", background: "#fff" }}>
          <div style={{ width: `${(savedCount / 63) * 100}%`, height: "100%", background: "#6a8a6a" }} />
        </div>
        <div style={{ position: "absolute", left: 20, top: 466, fontSize: 13, color: "#555" }}>
          {savedCount} av 63 sparade · uppskattad tid kvar: {Math.max(0, 63 - savedCount) * 3} min
        </div>
      </div>

      {/* Right: manual bank matching */}
      <div style={{ position: "absolute", left: 580, top: 60, width: 700, height: 660 }}>
        <div style={{ position: "absolute", left: 0, top: 14, fontWeight: 700, fontSize: 17 }}>Bankavstämning — konto 1930</div>
        <div style={{ position: "absolute", left: 0, top: 44, fontSize: 30, fontWeight: 700, fontFamily: MONO }}>
          Avstämda {matchedRows.length} / 36
        </div>
        <div style={{ position: "absolute", left: 0, top: 86, width: 690, fontSize: 14, fontWeight: 700, display: "flex", borderBottom: "1px solid #888", paddingBottom: 4 }}>
          <span style={{ width: 110 }}>Datum</span>
          <span style={{ width: 260 }}>Text</span>
          <span style={{ width: 110, textAlign: "right" }}>Belopp</span>
          <span style={{ marginLeft: 28 }}>Underlag</span>
        </div>
        {BANK.slice(0, 9).map((b, i) => {
          const isActive = openRow === i;
          const done = matchedRows.includes(i);
          return (
            <div
              key={b.id}
              style={{
                position: "absolute",
                left: 0,
                top: ROW_Y(i) - 60 - 22,
                width: 690,
                height: 44,
                display: "flex",
                alignItems: "center",
                fontSize: 15,
                background: isActive ? "#d8dce4" : i % 2 ? "#e4e1da" : "transparent",
                borderBottom: "1px solid #cfccc4",
              }}
            >
              <span style={{ width: 110, fontFamily: MONO, fontSize: 14 }}>{b.date}</span>
              <span style={{ width: 260, whiteSpace: "nowrap", overflow: "hidden" }}>{b.text}</span>
              <span style={{ width: 110, textAlign: "right", fontFamily: MONO, fontSize: 14 }}>{sek(b.amount, false)}</span>
              <span
                style={{
                  marginLeft: 20,
                  width: 180,
                  height: 28,
                  border: "1px solid #888",
                  background: "#fff",
                  fontSize: 13,
                  padding: "5px 6px",
                  color: done ? "#222" : "#888",
                  display: "flex",
                  justifyContent: "space-between",
                }}
              >
                <span>{done ? options[i] : "— Välj —"}</span>
                <span>▾</span>
              </span>
            </div>
          );
        })}
        {openRow !== undefined ? (
          <div
            style={{
              position: "absolute",
              left: 510,
              top: ROW_Y(openRow) - 60 + 18,
              width: 180,
              background: "#fff",
              border: "1px solid #555",
              boxShadow: "2px 4px 10px rgba(0,0,0,0.3)",
              zIndex: 10,
            }}
          >
            {options.map((o, k) => (
              <div key={o} style={{ height: 34, fontSize: 13, padding: "8px 6px", background: k === openRow ? "#3b5b8c" : "#fff", color: k === openRow ? "#fff" : "#222" }}>
                {o}
              </div>
            ))}
          </div>
        ) : null}
      </div>
      <Cursor x={cur.x} y={cur.y} pressed={pressed} />
    </div>
  );
};

const Clock: React.FC = () => {
  const frame = useCurrentFrame();
  const minutes = 8 * 60 + Math.floor(frame / 10) * 3;
  const hh = String(Math.floor(minutes / 60)).padStart(2, "0");
  const mm = String(minutes % 60).padStart(2, "0");
  const angle = (frame / 10) * 18;
  return (
    <div style={{ position: "absolute", right: 80, top: 54, display: "flex", alignItems: "center", gap: 18, opacity: fade(frame, 40, 15) }}>
      <svg width={54} height={54} viewBox="0 0 54 54">
        <circle cx={27} cy={27} r={24} fill="none" stroke={C.muted} strokeWidth={2.5} />
        <line x1={27} y1={27} x2={27} y2={10} stroke={C.text} strokeWidth={2.5} strokeLinecap="round" transform={`rotate(${angle} 27 27)`} />
        <line x1={27} y1={27} x2={38} y2={27} stroke={C.muted} strokeWidth={3} strokeLinecap="round" transform={`rotate(${angle / 12} 27 27)`} />
      </svg>
      <div style={{ fontFamily: MONO, fontSize: 52, fontWeight: 500, color: C.text }}>
        {hh}:{mm}
      </div>
    </div>
  );
};

export const Before: React.FC = () => {
  const frame = useCurrentFrame();
  const zoom = interpolate(frame, [0, BEFORE_FRAMES], [1, 1.05]);
  const sceneDim = interpolate(frame, [60, 100], [1, 0.35], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const exit = interpolate(frame, [BEFORE_FRAMES - 20, BEFORE_FRAMES], [1, 0.0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: "#121214", fontFamily: FONT, overflow: "hidden" }}>
      <AbsoluteFill style={{ filter: "saturate(0.18) contrast(0.95)", transform: `scale(${zoom})`, opacity: exit }}>
        <AbsoluteFill style={{ opacity: sceneDim, filter: `blur(${(1 - sceneDim) * 3}px)` }}>
          <Scatter />
        </AbsoluteFill>
        <LegacyWindow />
      </AbsoluteFill>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.65) 100%)" }} />
      <div style={{ position: "absolute", left: 80, top: 62, opacity: fade(frame, 10) * exit }}>
        <Eyebrow color={C.red}>Today</Eyebrow>
      </div>
      <div style={{ opacity: exit }}>
        <Clock />
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 70,
          width: "100%",
          textAlign: "center",
          fontSize: 44,
          fontWeight: 600,
          letterSpacing: "-0.02em",
          color: C.text,
          opacity: exit,
          textShadow: "0 4px 30px rgba(0,0,0,0.9)",
        }}
      >
        <span style={{ opacity: fade(frame, 100, 15) }}>Accountants upload receipts one at a time. </span>
        <span style={{ opacity: fade(frame, 270, 15), color: C.muted }}>Then match every bank line by hand.</span>
      </div>
    </AbsoluteFill>
  );
};
