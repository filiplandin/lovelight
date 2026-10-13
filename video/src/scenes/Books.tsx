import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { C, Check, Eyebrow, MONO, Stage, fade, fadeOut, sek, useSpring } from "../theme";

export const BOOKS_FRAMES = 240;

// Telia supplier invoice 88213456 (gold.json: net 3 992, VAT 998, account 6212).
const LINES = [
  { acct: "6212", name: "Telefon", debit: 3992, credit: 0 },
  { acct: "2640", name: "Ingående moms", debit: 998, credit: 0 },
  { acct: "2440", name: "Leverantörsskulder", debit: 0, credit: 4990 },
];

// Box values are produced by the live app; the video shows only which boxes get filled.
const VAT = [
  { box: "05", label: "Momspliktig försäljning" },
  { box: "10", label: "Utgående moms 25 %" },
  { box: "48", label: "Ingående moms" },
  { box: "49", label: "Moms att betala" },
];

const Panel: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({ children, style }) => (
  <div
    style={{
      position: "absolute",
      borderRadius: 20,
      background: C.bg2,
      border: `1px solid ${C.border2}`,
      boxShadow: "0 20px 60px rgba(0,0,0,0.45)",
      padding: "28px 34px",
      boxSizing: "border-box",
      ...style,
    }}
  >
    {children}
  </div>
);

export const Books: React.FC = () => {
  const frame = useCurrentFrame();
  const v = useSpring(0);
  const bal = useSpring(64, { damping: 11, stiffness: 160 });
  const pnl = useSpring(84);
  const vat = useSpring(100);
  const exp = useSpring(140);
  const exported = interpolate(frame, [168, 180], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const out = fadeOut(frame, BOOKS_FRAMES - 10, 10);
  const totalD = LINES.reduce((s, l) => s + l.debit, 0);
  const totalC = LINES.reduce((s, l) => s + l.credit, 0);

  return (
    <Stage style={{ opacity: out }}>
      <div style={{ position: "absolute", left: 120, top: 70, opacity: fade(frame, 0) }}>
        <Eyebrow color={C.violet}>Books</Eyebrow>
        <div style={{ fontSize: 52, fontWeight: 700, letterSpacing: "-0.03em", marginTop: 10 }}>Balanced vouchers. Books that close.</div>
      </div>

      <Panel style={{ left: 120, top: 330, width: 800, height: 520, opacity: v, transform: `translateY(${(1 - v) * 40}px)` }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <div style={{ fontSize: 28, fontWeight: 700 }}>Verifikation A 47</div>
          <div style={{ fontFamily: MONO, fontSize: 17, color: C.muted }}>2026-09-05 · Telia 88213456</div>
        </div>
        <div style={{ display: "flex", fontSize: 16, color: C.muted, marginTop: 30, paddingBottom: 10, borderBottom: `1px solid ${C.border2}` }}>
          <span style={{ width: 90 }}>Konto</span>
          <span style={{ flex: 1 }}>Benämning</span>
          <span style={{ width: 170, textAlign: "right" }}>Debet</span>
          <span style={{ width: 170, textAlign: "right" }}>Kredit</span>
        </div>
        {LINES.map((l, i) => (
          <div
            key={l.acct}
            style={{
              display: "flex",
              fontSize: 23,
              padding: "16px 0",
              borderBottom: `1px solid ${C.border}`,
              opacity: fade(frame, 14 + i * 9, 10),
              transform: `translateX(${(1 - fade(frame, 14 + i * 9, 10)) * -20}px)`,
            }}
          >
            <span style={{ width: 90, fontFamily: MONO, color: C.cyan }}>{l.acct}</span>
            <span style={{ flex: 1 }}>{l.name}</span>
            <span style={{ width: 170, textAlign: "right", fontFamily: MONO }}>{l.debit ? sek(l.debit, false) : ""}</span>
            <span style={{ width: 170, textAlign: "right", fontFamily: MONO }}>{l.credit ? sek(l.credit, false) : ""}</span>
          </div>
        ))}
        <div style={{ display: "flex", fontSize: 23, padding: "16px 0", fontWeight: 700, opacity: fade(frame, 46, 10) }}>
          <span style={{ width: 90 }} />
          <span style={{ flex: 1, color: C.muted, fontWeight: 500 }}>Summa</span>
          <span style={{ width: 170, textAlign: "right", fontFamily: MONO }}>{sek(totalD, false)}</span>
          <span style={{ width: 170, textAlign: "right", fontFamily: MONO }}>{sek(totalC, false)}</span>
        </div>
        <div
          style={{
            marginTop: 18,
            display: "inline-flex",
            alignItems: "center",
            gap: 12,
            padding: "10px 22px",
            borderRadius: 999,
            background: `${C.green}1c`,
            border: `1px solid ${C.green}66`,
            color: C.green,
            fontSize: 24,
            fontWeight: 700,
            transform: `scale(${bal})`,
            transformOrigin: "left center",
            boxShadow: `0 0 30px ${C.green}33`,
          }}
        >
          <Check size={28} progress={bal} /> Balanced
        </div>
      </Panel>

      <Panel style={{ left: 980, top: 330, width: 820, height: 150, opacity: pnl, transform: `translateY(${(1 - pnl) * 40}px)`, display: "flex", gap: 40, alignItems: "center" }}>
        {["Resultaträkning", "Balansräkning", "Huvudbok"].map((k, i) => (
          <div key={k} style={{ flex: 1, opacity: fade(frame, 90 + i * 6, 10) }}>
            <div style={{ fontSize: 16, color: C.muted, textTransform: "uppercase", letterSpacing: "0.1em" }}>{k}</div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 28, fontWeight: 600, marginTop: 8, color: C.green }}>
              <Check size={26} progress={fade(frame, 96 + i * 6, 10)} /> Ready
            </div>
          </div>
        ))}
      </Panel>

      <Panel style={{ left: 980, top: 505, width: 820, height: 225, opacity: vat, transform: `translateY(${(1 - vat) * 40}px)` }}>
        <div style={{ fontSize: 16, color: C.muted, textTransform: "uppercase", letterSpacing: "0.1em" }}>Momsdeklaration</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px 40px", marginTop: 16 }}>
          {VAT.map((b, i) => (
            <div key={b.box} style={{ display: "flex", alignItems: "center", gap: 14, opacity: fade(frame, 106 + i * 6, 10) }}>
              <span
                style={{
                  fontFamily: MONO,
                  fontSize: 18,
                  fontWeight: 500,
                  color: C.violet,
                  border: `1px solid ${C.violet}66`,
                  borderRadius: 8,
                  padding: "2px 8px",
                }}
              >
                {b.box}
              </span>
              <span style={{ flex: 1, fontSize: 15, color: C.muted, whiteSpace: "nowrap" }}>{b.label}</span>
              <Check size={24} progress={fade(frame, 112 + i * 6, 10)} />
            </div>
          ))}
        </div>
      </Panel>

      <Panel
        style={{
          left: 980,
          top: 755,
          width: 820,
          height: 95,
          opacity: exp,
          transform: `translateY(${(1 - exp) * 40}px)`,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 34px",
          background: exported > 0 ? `linear-gradient(90deg, ${C.bg2}, rgba(139,108,255,${0.18 * exported}))` : C.bg2,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
          <div style={{ fontSize: 26, fontWeight: 700 }}>Export SIE4</div>
          <div style={{ fontSize: 24, color: C.muted }}>→ Fortnox / Visma</div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontFamily: MONO, fontSize: 17, color: C.cyan, opacity: exported }}>lovelight_design_ab.se</span>
          <Check size={34} progress={exported} />
        </div>
      </Panel>
    </Stage>
  );
};
