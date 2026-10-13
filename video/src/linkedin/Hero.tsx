// Shots 5-12: HERO 1 (the 1:3 match, why 95%, approval) and HERO 2 (trace, injection, reversal, hash chain).
import React from "react";
import { Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { C, sek } from "../theme";
import { Clip } from "./Clip";
import { CHAIN, INJECTION, LUMP, LUMP_DOCS, WHY } from "./facts";
import { BOX, Caption, Cut, LStage, Mono, Panel, Tick, W, ramp } from "./ui";

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
        { f: 0, at: "row", z: 1.25 },
        { f: 16, at: "bank", z: 2.8 },
        { f: 56, at: "bank", z: 2.8 },
        { f: 76, at: { m: "connector", fx: 0.45 }, z: 2.6 },
        { f: 96, at: "docs", z: 2.4 },
      ]}
      rings={[
        { f: 16, at: "bank", dur: 40, color: C.amber },
        { f: 96, at: "docs", dur: 24 },
      ]}
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
      <Caption text="References + exact sum. | *To the last digit.*" />
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
  // Steps through real partial sums (40, 70, 75, 84) as each row lands, then the gate lifts it to 95.
  const shown = contrib.reduce((s, c, i) => s + (frame >= WHY_ROW_AT[i] + 4 ? c : 0), 0);
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
          { f: 0, at: "pill", z: 2.6 },
          { f: 24, at: "pop", z: 2.6 },
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
      lead={0.3}
      rate={1.6}
      // BT014 auto-approved at 95%, then the 94% Figma row approved by hand; its "Match approved" toast sits bottom-right.
      fallback={{ row: [0.18, 0.4, 0.8, 0.16], approved: [0.88, 0.42, 0.1, 0.08], toast: [0.737, 0.935, 0.248, 0.049] }}
      cam={[
        { f: 0, at: [0.74, 0.666], z: 2.0 },
        { f: ["other_row", -12], at: [0.74, 0.666], z: 2.0 },
        { f: ["other_row", -2], at: [0.735, 0.41], z: 2.0 },
        { f: ["other_clicked", -2], at: [0.735, 0.41], z: 2.0 },
        { f: ["other_clicked", 8], at: "toast", z: 2.2 },
      ]}
      rings={[
        { f: 4, at: "approved", dur: 30, color: C.green },
        { f: ["other_clicked", -10], at: "other_btn", dur: 14, color: C.green },
        { f: ["other_clicked", 8], at: "toast", dur: 22, color: C.green },
      ]}
    />
  </LStage>
);

// ---------------------------------------------------------------- 9. REC trace

const TRACE_CUT = 48;

export const Trace: React.FC = () => (
  <LStage>
    <Caption text="Every krona traces to a *source.*" />
    {/* PDF total -> extracted Gross field, then cut past the drawer scroll to the balanced voucher. */}
    <Cut from={0} dur={TRACE_CUT + 4} fade={0}>
      <Clip
        name="trace"
        title="Telia invoice: source PDF ↔ extracted fields ↔ voucher"
        steps={["/?view=inbox", "open telia_faktura_88213456.pdf", "wait for the PDF preview", "scroll the drawer to the Voucher section"]}
        anchor="preview"
        lead={0.2}
        rate={1.25}
        fallback={{ preview: [0.37, 0.1, 0.31, 0.5], gross: [0.7, 0.35, 0.13, 0.05] }}
        cam={[
          { f: 0, at: { m: "preview", fx: 0.76, fy: 0.52 }, z: 2.5 },
          { f: 12, at: { m: "preview", fx: 0.76, fy: 0.52 }, z: 2.5 },
          { f: 30, at: [0.575, 0.32], z: 2.0 },
        ]}
        links={[{ f: 16, from: { m: "preview", fx: 0.86, fy: 0.52 }, to: { m: "gross", fx: 0.1 }, dur: 16 }]}
        rings={[{ f: 30, at: "gross", dur: 22, color: C.green }]}
      />
    </Cut>
    <Cut from={TRACE_CUT} dur={90 - TRACE_CUT}>
      <Clip
        name="trace"
        title="Telia voucher · balanced"
        anchor="voucher_total"
        lead={0.6}
        fallback={{ voucher: [0.68, 0.5, 0.3, 0.25], balanced: [0.885, 0.433, 0.098, 0.022] }}
        cam={[
          { f: 0, at: { m: "voucher", fy: 0.55 }, z: 2.2 },
          { f: 42, at: { m: "voucher", fy: 0.55 }, z: 2.35 },
        ]}
        rings={[
          { f: 6, at: "voucher_total", dur: 30, color: C.green },
          { f: 12, at: "balanced", dur: 28, color: C.green },
        ]}
      />
    </Cut>
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
        lead={0}
        box={{ ...BOX, height: 470 }}
        // Drawer header + red "quarantined" pill, the injection warning box, then "Never posted" in the voucher slot.
        fallback={{ pill: [0.75, 0.02, 0.07, 0.03], anomaly: [0.5949, 0.0712, 0.3847, 0.1841], never: [0.68, 0.6, 0.3, 0.08] }}
        cam={[
          { f: 0, at: [0.46, 0.03], z: 2.0 },
          { f: 12, at: [0.46, 0.03], z: 2.0 },
          { f: 26, at: { m: "anomaly", fy: 0.42 }, z: 2.2 },
          { f: ["never", -14], at: { m: "anomaly", fy: 0.42 }, z: 2.2 },
          { f: ["never", -2], at: "never", z: 2.4 },
        ]}
        rings={[
          { f: 2, at: "pill", dur: 24, color: C.red },
          { f: ["never", 2], at: "never", dur: 26, color: C.red },
        ]}
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
      lead={1.0}
      fallback={{ form: [0.7, 0.5, 0.28, 0.12], fix: [0.7, 0.45, 0.28, 0.06] }}
      cam={[
        { f: 0, at: "form", z: 2.4 },
        { f: ["fix", -6], at: "form", z: 2.4 },
        { f: ["fix", 6], at: { m: "fix", fy: 0.85 }, z: 2.4 },
        { f: 90, at: { m: "fix", fy: 0.85 }, z: 2.55 },
      ]}
      rings={[{ f: ["fix", 4], at: "fix", dur: 44, color: C.green }]}
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
          { f: 0, at: "badge", z: 2.7 },
          { f: 40, at: "badge", z: 2.95 },
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
