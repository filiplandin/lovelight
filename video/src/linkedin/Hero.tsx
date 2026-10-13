// Shots 5-12: HERO 1 (the 1:3 match, why 95%, approval) and HERO 2 (trace, injection, reversal, hash chain).
import React from "react";
import { Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { C, sek } from "../theme";
import { Clip } from "./Clip";
import { CHAIN, INJECTION, LUMP, LUMP_DOCS, WHY } from "./facts";
import { BOX, Caption, LStage, Mono, Panel, Tick, W, ramp } from "./ui";

// Rough boxes for a 1440x1350 recording, used only if a clip's .json marks are missing.
const FB_RECON = { row: [0.18, 0.4, 0.8, 0.16], bank: [0.19, 0.42, 0.3, 0.1], connector: [0.5, 0.42, 0.1, 0.12], docs: [0.6, 0.4, 0.3, 0.16] };

// ---------------------------------------------------------------- 5. REC recon

export const Recon: React.FC = () => (
  <LStage>
    <Caption text="The bank text names *nobody.*" />
    <Clip
      name="recon"
      title="Reconciliation · BT014 'LB LEVBET 3 ST' · 1:3"
      steps={["/?view=recon", "centre the LB LEVBET 3 ST row", "hover the bank side 1 s", "pan along the connectors to the 3 documents"]}
      anchor="row"
      lead={0.2}
      fallback={FB_RECON}
      cam={[
        { f: 0, at: "row", z: 1.15 },
        { f: 26, at: { m: "bank", fx: 0.35 }, z: 1.8 },
        { f: 62, at: { m: "bank", fx: 0.35 }, z: 1.8 },
        { f: 92, at: "connector", z: 1.6 },
        { f: 118, at: "docs", z: 1.7 },
      ]}
      rings={[{ f: 30, at: "bank", dur: 40 }]}
    />
  </LStage>
);

// ---------------------------------------------------------------- 6. references + exact sum (overlay on frozen recon)

const REF_FONT = 38;
const CH = REF_FONT * 0.6; // JetBrains Mono advance width
const REF_X = (W - LUMP.reference.length * CH) / 2;
const REF_Y = 470;
const ROW_Y = (k: number) => 620 + k * 128;
const SLOT_X = 400;
const landAt = (k: number) => 18 + k * 6;

export const RefsSum: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tokens = LUMP_DOCS.map((d) => ({ ...d, idx: LUMP.reference.indexOf(d.ref) }));
  const split = ramp(frame, 6, 10);
  const total = ramp(frame, 54, 62);
  return (
    <LStage>
      <Caption text="References + exact sum. | *To the öre.*" />
      <Clip name="recon" title="Reconciliation (frozen frame)" anchor="end" lead={0.4} freeze={0} dim={0.82} fallback={FB_RECON} cam={[{ f: 0, at: "row", z: 1.1 }]} />
      <div style={{ position: "absolute", left: 0, right: 0, top: REF_Y - 52, textAlign: "center", fontSize: 24, color: C.muted, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase" }}>
        Bank reference
      </div>
      <div style={{ position: "absolute", left: REF_X, top: REF_Y, fontSize: REF_FONT, opacity: 1 - split, whiteSpace: "pre" }}>
        <Mono style={{ color: C.muted }}>{LUMP.reference}</Mono>
      </div>
      {LUMP_DOCS.map((d, k) => {
        const p = spring({ frame: frame - 2 - k * 3, fps, config: { damping: 18 } });
        const landed = ramp(frame, landAt(k), landAt(k) + 3);
        return (
          <Panel
            key={d.ref}
            glow={landed > 0.5 ? C.cyan : undefined}
            style={{ position: "absolute", left: 90, right: 90, top: ROW_Y(k), height: 104, padding: "0 34px", display: "flex", alignItems: "center", opacity: p, transform: `translateY(${(1 - p) * 30}px)` }}
          >
            <div style={{ width: SLOT_X - 90 - 34, fontSize: 32, fontWeight: 700, letterSpacing: "-0.02em", whiteSpace: "nowrap" }}>{d.short}</div>
            <div style={{ flex: 1, height: 50, borderBottom: `2px dashed ${landed > 0.5 ? "transparent" : C.border2}` }} />
            <Mono style={{ fontSize: 34 }}>{sek(d.gross, false)}</Mono>
          </Panel>
        );
      })}
      {tokens.map((t, k) => {
        const p = interpolate(frame, [8 + k * 6, landAt(k)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
        const x = interpolate(p, [0, 1], [REF_X + t.idx * CH, SLOT_X]);
        const y = interpolate(p, [0, 1], [REF_Y, ROW_Y(k) + 30]);
        const landed = p >= 1;
        return (
          <div key={t.ref} style={{ position: "absolute", left: x, top: y - (landed ? 0 : Math.sin(p * Math.PI) * 40), fontSize: REF_FONT, whiteSpace: "nowrap", opacity: frame >= 6 ? 1 : 0 }}>
            <Mono style={{ color: C.cyan, textShadow: `0 0 18px ${C.cyan}88` }}>{t.ref}</Mono>
          </div>
        );
      })}
      <div style={{ position: "absolute", left: 90, right: 90, top: 1010, display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6 }}>
        <div style={{ fontSize: 34, color: C.muted }}>
          {LUMP_DOCS.map((d, k) => (
            <span key={d.ref} style={{ opacity: ramp(frame, landAt(k) + 4, landAt(k) + 10) }}>
              <Mono>{(k ? " + " : "") + sek(d.gross, false)}</Mono>
            </span>
          ))}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 18, opacity: total }}>
          <Mono style={{ fontSize: 62, color: C.green }}>= {sek(-LUMP.amount)}</Mono>
          <Tick ok size={62} p={total} />
        </div>
      </div>
    </LStage>
  );
};

// ---------------------------------------------------------------- 7. why 95%

export const WHY_ROW_AT = [56, 64, 72, 80];
export const WHY_SCORE_AT = 100;

export const Why: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const card = spring({ frame: frame - 42, fps, config: { damping: 18, stiffness: 120 } });
  const contrib = WHY.rows.map((r) => r.weight * r.value);
  const shown = contrib.reduce((s, c, i) => s + c * ramp(frame, WHY_ROW_AT[i], WHY_ROW_AT[i] + 8), 0);
  const floor = ramp(frame, WHY_SCORE_AT - 4, WHY_SCORE_AT);
  const score = frame >= WHY_SCORE_AT ? WHY.score : Math.round(shown);
  const pop = spring({ frame: frame - WHY_SCORE_AT, fps, config: { damping: 9, stiffness: 200 } });
  return (
    <LStage>
      <Caption text="Why 95%? | Four checks. !One failed.!" />
      <Clip
        name="why"
        title="The real 'Why 95% · 1:3 ?' popover"
        steps={["/?view=recon", "click the BT014 pill '95% · 1:3 ?'", "hold the popover 3 s"]}
        anchor="pop"
        lead={0.8}
        dim={0.75 * card}
        fallback={{ pill: [0.5, 0.44, 0.07, 0.02], pop: [0.38, 0.47, 0.31, 0.3] }}
        cam={[
          { f: 0, at: "pill", z: 1.6 },
          { f: 22, at: "pop", z: 2.2 },
        ]}
        rings={[{ f: 2, at: "pill", dur: 22 }]}
      />
      <Panel
        style={{
          position: "absolute",
          left: 60,
          right: 60,
          top: 372,
          height: 820,
          padding: "34px 44px",
          opacity: card,
          transform: `translateY(${(1 - card) * 120}px)`,
          background: "rgba(11,13,20,0.97)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{ fontSize: 24, color: C.muted, fontWeight: 600 }}>Bank match · {LUMP.text}</div>
            <div style={{ fontSize: 58, fontWeight: 800, letterSpacing: "-0.03em", marginTop: 6 }}>Why {WHY.score}%?</div>
          </div>
          <div style={{ fontSize: 104, fontWeight: 800, letterSpacing: "-0.05em", color: frame >= WHY_SCORE_AT ? C.green : C.amber, transform: `scale(${frame >= WHY_SCORE_AT ? 1 + 0.12 * (1 - pop) : 1})`, transformOrigin: "100% 50%" }}>
            {score}%
          </div>
        </div>
        <div style={{ marginTop: 26, display: "flex", flexDirection: "column", gap: 12 }}>
          {WHY.rows.map((r, i) => {
            const p = spring({ frame: frame - WHY_ROW_AT[i], fps, config: { damping: 16, stiffness: 170 } });
            const col = r.pass ? C.green : C.red;
            return (
              <div
                key={r.label}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 22,
                  padding: "16px 22px",
                  borderRadius: 18,
                  background: r.pass ? C.panel : `${C.red}14`,
                  border: `1.5px solid ${r.pass ? C.border : `${C.red}77`}`,
                  opacity: p,
                  transform: `translateX(${(1 - p) * 50}px)`,
                }}
              >
                <Tick ok={r.pass} size={54} p={ramp(frame, WHY_ROW_AT[i] + 3, WHY_ROW_AT[i] + 10)} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 38, fontWeight: 700, letterSpacing: "-0.02em", color: r.pass ? C.text : C.red }}>{r.label}</div>
                  <div style={{ fontSize: 25, color: C.muted, marginTop: 2 }}>{r.note}</div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <Mono style={{ fontSize: 34, color: col }}>+{(r.weight * r.value).toFixed(0)}</Mono>
                  <div style={{ fontSize: 21, color: C.faint, marginTop: 2 }}>weight {r.weight}%</div>
                </div>
              </div>
            );
          })}
        </div>
        <div style={{ marginTop: 22, display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 28, opacity: ramp(frame, 88, 94) }}>
          <span style={{ color: C.muted }}>Weighted mean</span>
          <Mono style={{ fontSize: 34 }}>{WHY.weighted}%</Mono>
        </div>
        <div
          style={{
            marginTop: 14,
            padding: "14px 20px",
            borderRadius: 16,
            border: `1.5px solid ${C.cyan}66`,
            background: `${C.cyan}12`,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            opacity: floor,
            transform: `translateY(${(1 - floor) * 16}px)`,
          }}
        >
          <span style={{ fontSize: 28, fontWeight: 600, color: C.cyan }}>Rule: {WHY.rule}</span>
          <Mono style={{ fontSize: 34, color: C.green }}>{WHY.score}%</Mono>
        </div>
      </Panel>
    </LStage>
  );
};

// ---------------------------------------------------------------- 8. REC approve

export const Approve: React.FC = () => (
  <LStage>
    <Caption text="Scored by code. | *Below 95%, you decide.*" />
    <Clip
      name="approve"
      title="Approval · ≥95% auto-approves, the rest wait for a click"
      steps={["/?view=recon after a fresh replay", "BT014 shows green 'Approved' + method", "click Approve on a lower-scored match"]}
      anchor="approved"
      lead={0.6}
      fallback={{ row: [0.18, 0.4, 0.8, 0.16], approved: [0.88, 0.42, 0.1, 0.08] }}
      cam={[
        { f: 0, at: "row", z: 1.3 },
        { f: 18, at: "approved", z: 1.9 },
        { f: "other_row", at: "other_btn", z: 1.9 },
      ]}
      rings={[
        { f: 14, at: "approved", dur: 30, color: C.green },
        { f: ["other_clicked", -4], at: "other_btn", dur: 24, color: C.green },
      ]}
    />
  </LStage>
);

// ---------------------------------------------------------------- 9. REC trace

export const Trace: React.FC = () => (
  <LStage>
    <Caption text="Every krona traces to a *source.*" />
    <Clip
      name="trace"
      title="Telia invoice: source PDF ↔ extracted fields ↔ voucher"
      steps={["/?view=inbox", "open telia_faktura_88213456.pdf", "wait for the PDF preview", "scroll the drawer to the Voucher section"]}
      anchor="preview"
      lead={0.2}
      rate={1.25}
      fallback={{ preview: [0.37, 0.1, 0.31, 0.5], gross: [0.7, 0.35, 0.13, 0.05], voucher: [0.68, 0.5, 0.3, 0.25] }}
      cam={[
        { f: 0, at: { m: "preview", fx: 0.75, fy: 0.42 }, z: 2.0 },
        { f: 30, at: { m: "preview", fx: 0.75, fy: 0.42 }, z: 2.0 },
        { f: 48, at: "gross", z: 1.8 },
        { f: ["voucher", -6], at: "gross", z: 1.5 },
        { f: ["voucher", 8], at: "voucher_total", z: 1.7 },
      ]}
      links={[{ f: 22, from: { m: "preview", fx: 0.86, fy: 0.42 }, to: "gross", dur: 22 }]}
      rings={[{ f: 44, at: "gross", dur: 30, color: C.green }]}
    />
  </LStage>
);

// ---------------------------------------------------------------- 10. REC inject + payload overlay

export const STAMP_AT = 58;

export const Inject: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const show = spring({ frame: frame - 8, fps, config: { damping: 18 } });
  const typed = Math.floor(interpolate(frame, [12, 54], [0, 92], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  const stamp = spring({ frame: frame - STAMP_AT, fps, config: { damping: 10, stiffness: 260, mass: 0.7 } });
  const text = INJECTION.slice(0, typed) + (typed < 92 ? "▍" : "…");
  return (
    <LStage>
      <Caption text="Poisoned invoice? | Quarantined. *0~kr~moved.*" />
      <Clip
        name="inject"
        title="Nordic Growth Partners · 8 750 kr · Quarantined"
        steps={["/?view=inbox → filter 'Quarantined'", "open faktura_nordic_growth_partners_7781.pdf", "hold on 'Never posted. Quarantined documents cannot reach the ledger.'"]}
        anchor="pill"
        lead={0.5}
        box={{ ...BOX, height: 470 }}
        fallback={{ pill: [0.75, 0.02, 0.07, 0.03], never: [0.68, 0.6, 0.3, 0.08] }}
        cam={[
          { f: 0, at: "pill", z: 1.8 },
          { f: 40, at: "pill", z: 1.8 },
          { f: ["never", 0], at: "never", z: 1.6 },
        ]}
        rings={[{ f: 6, at: "pill", dur: 34, color: C.red }]}
      />
      <Panel
        glow={C.red}
        style={{
          position: "absolute",
          left: BOX.left,
          width: BOX.width,
          top: 860,
          height: 300,
          padding: "26px 34px",
          background: "linear-gradient(180deg, rgba(248,113,113,0.10), rgba(248,113,113,0.03)), #0d0a0e",
          opacity: show,
          transform: `translateY(${(1 - show) * 40}px)`,
          overflow: "hidden",
        }}
      >
        <div style={{ fontSize: 22, color: C.red, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase" }}>Hidden text in the PDF</div>
        <div style={{ marginTop: 14, fontSize: 30, lineHeight: 1.4, color: "#f3d0d0" }}>
          <Mono>{text}</Mono>
        </div>
        <div
          style={{
            position: "absolute",
            right: 40,
            top: 70,
            padding: "8px 28px",
            border: `6px solid ${C.red}`,
            borderRadius: 14,
            color: C.red,
            fontSize: 76,
            fontWeight: 800,
            letterSpacing: "0.06em",
            opacity: stamp > 0.01 ? 1 : 0,
            transform: `rotate(-9deg) scale(${interpolate(stamp, [0, 1], [2.2, 1])})`,
            background: "rgba(13,10,14,0.85)",
            boxShadow: `0 0 40px ${C.red}55`,
          }}
        >
          BLOCKED
        </div>
      </Panel>
    </LStage>
  );
};

// ---------------------------------------------------------------- 11. REC correction

export const Correct: React.FC = () => (
  <LStage>
    <Caption text="Corrections are reversals. | *Never edits.*" />
    <Clip
      name="correct"
      title="Change account → reversal + re-post, nothing edited"
      steps={["open the posted Kjell & Company receipt (349 kr)", "Change account → 6110, reason 'Office supplies, not equipment'", "Reverse & re-post", "hold on 'A## reverses A##; A## re-posts it. Nothing was edited.'"]}
      anchor="fix"
      lead={1.6}
      fallback={{ form: [0.7, 0.5, 0.28, 0.12], fix: [0.7, 0.45, 0.28, 0.06] }}
      cam={[
        { f: 0, at: "form", z: 1.7 },
        { f: ["fix", 0], at: "fix", z: 2.0 },
      ]}
      rings={[{ f: ["fix", 4], at: "fix", dur: 40, color: C.green }]}
    />
  </LStage>
);

// ---------------------------------------------------------------- 12. REC audit + chain overlay

// Chain builds, verifies green, then row #2 is edited and the chain breaks from #2 onward; holds red to the cut.
export const CHAIN_AT = 46;
export const VERIFY_AT = 66;
export const BREAK_AT = 86;

export const Audit: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const over = ramp(frame, CHAIN_AT - 6, CHAIN_AT + 4);
  const broken = frame >= BREAK_AT;
  const ok = frame >= VERIFY_AT && !broken;
  const status = spring({ frame: frame - (broken ? BREAK_AT : VERIFY_AT), fps, config: { damping: 12, stiffness: 200 } });
  const CARD_H = 124;
  const GAP = 36;
  const top = 396;
  return (
    <LStage>
      <Caption text="Hash-chained log. | Edit one row, !chain~breaks.!" size={70} />
      <Clip
        name="audit"
        title="Audit trail · 'Chain verified · N events · head ab12cd…'"
        steps={["/?view=audit", "click Re-verify", "hover the head hash 1 s"]}
        anchor="badge"
        lead={0.2}
        dim={0.97 * over}
        fallback={{ badge: [0.18, 0.2, 0.3, 0.04], head: [0.6, 0.2, 0.2, 0.03] }}
        cam={[
          { f: 0, at: "badge", z: 2.0 },
          { f: 40, at: "badge", z: 2.2 },
        ]}
        rings={[{ f: 6, at: "badge", dur: 34, color: C.green }]}
      />
      {CHAIN.map((c, i) => {
        const p = spring({ frame: frame - CHAIN_AT - i * 5, fps, config: { damping: 16, stiffness: 170 } });
        const bad = broken && i >= 1;
        const tampered = broken && i === 1;
        const col = bad ? C.red : ok ? C.green : C.border2;
        const y = top + i * (CARD_H + GAP);
        return (
          <React.Fragment key={c.label}>
            {i > 0 ? (
              <div style={{ position: "absolute", left: 150, top: y - GAP, width: 4, height: GAP, background: bad ? C.red : C.violet, opacity: p, boxShadow: `0 0 12px ${bad ? C.red : C.violet}` }} />
            ) : null}
            <Panel
              glow={bad ? C.red : ok ? C.green : undefined}
              style={{
                position: "absolute",
                left: 90,
                right: 90,
                top: y,
                height: CARD_H,
                padding: "0 34px",
                display: "flex",
                alignItems: "center",
                gap: 22,
                opacity: p * over,
                transform: `translateX(${(1 - p) * 60}px)`,
                borderColor: col,
              }}
            >
              <Mono style={{ fontSize: 28, color: C.faint, width: 46 }}>#{i + 1}</Mono>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 34, fontWeight: 700, letterSpacing: "-0.02em" }}>{c.label}</div>
                {i === 1 ? (
                  <Mono style={{ fontSize: 24, color: tampered ? C.red : C.muted }}>{tampered ? "Telia 9 490,00 kr · edited" : "Telia 4 990,00 kr"}</Mono>
                ) : (
                  <div style={{ fontSize: 22, color: C.muted }}>{["telia_faktura_88213456.pdf", "", "6212 / 2640 / 2440", "BT014 · 1:3 · 0.95"][i]}</div>
                )}
              </div>
              <Mono style={{ fontSize: 34, color: bad ? C.red : ok ? C.green : C.cyan }}>{bad ? c.bad : c.hash}</Mono>
            </Panel>
          </React.Fragment>
        );
      })}
      <div style={{ position: "absolute", left: 0, right: 0, top: top + 4 * (CARD_H + GAP) - 6, display: "flex", justifyContent: "center", opacity: frame >= VERIFY_AT ? 1 : 0 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 16,
            padding: "14px 32px",
            borderRadius: 999,
            fontSize: 40,
            fontWeight: 800,
            color: broken ? C.red : C.green,
            background: broken ? `${C.red}1c` : `${C.green}1c`,
            border: `2px solid ${broken ? C.red : C.green}88`,
            transform: `scale(${0.85 + 0.15 * status})`,
          }}
        >
          {broken ? "Chain broken at #2" : "Chain verified"}
          <Tick ok={!broken} size={46} p={status} />
        </div>
      </div>
    </LStage>
  );
};
