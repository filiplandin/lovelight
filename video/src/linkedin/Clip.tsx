import React, { useEffect, useState } from "react";
import {
  Easing,
  Freeze,
  OffthreadVideo,
  cancelRender,
  continueRender,
  delayRender,
  getStaticFiles,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { C, MONO } from "../theme";
import { BOX } from "./ui";

// public/rec/<name>.mp4 + <name>.json come from scripts/record_demo.py. Mark boxes are [x, y, w, h] as fractions
// of the recorded viewport; times are seconds from clip start.
type Mark = { t: number; box: number[] | null };
type Meta = { viewport: [number, number]; scale: number; marks: Record<string, Mark> };

/** A mark name (its box centre), a point inside a mark's box, the midpoint of two marks, or an [x, y] viewport fraction. */
export type Focus = string | [number, number] | { m: string; fx?: number; fy?: number } | { mid: [string, string]; fx?: number };
/** Local frame, or a mark name (+ offset frames) so timing follows the recording. */
export type When = number | string | [string, number];
export type Cam = { f: When; at: Focus; z: number };
export type Ring = { f: When; at: Focus; dur?: number; color?: string };
export type Link = { f: When; from: Focus; to: Focus; dur?: number };

const FPS = 30;
const DEFAULT_VIEWPORT: [number, number] = [1440, 1350];

const useRec = (name: string) => {
  const files = getStaticFiles();
  const hasVideo = files.some((f) => f.name === `rec/${name}.mp4`);
  const hasMeta = files.some((f) => f.name === `rec/${name}.json`);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [handle] = useState(() => (hasMeta ? delayRender(`rec/${name}.json`) : null));
  useEffect(() => {
    if (handle === null) return;
    fetch(staticFile(`rec/${name}.json`))
      .then((r) => r.json())
      .then((m: Meta) => {
        setMeta(m);
        continueRender(handle);
      })
      .catch((e) => cancelRender(e));
  }, [handle, name]);
  return { hasVideo, meta };
};

const boxOf = (at: Focus, meta: Meta | null, fallback: Record<string, number[]>): number[] | null => {
  if (Array.isArray(at)) return [at[0], at[1], 0, 0];
  if (typeof at === "object" && "mid" in at) {
    const [a, b] = at.mid.map((k) => meta?.marks[k]?.box ?? fallback[k]);
    if (!a || !b) return a ?? b ?? null;
    const fx = at.fx ?? 0.5;
    return [(a[0] + a[2] * fx + b[0] + b[2] * fx) / 2, (a[1] + a[3] / 2 + b[1] + b[3] / 2) / 2, 0, 0];
  }
  const key = typeof at === "string" ? at : at.m;
  const b = meta?.marks[key]?.box ?? fallback[key] ?? null;
  if (!b || typeof at === "string") return b;
  return [b[0] + b[2] * (at.fx ?? 0.5), b[1] + b[3] * (at.fy ?? 0.5), 0, 0];
};
const centerOf = (at: Focus, meta: Meta | null, fallback: Record<string, number[]>): [number, number] => {
  const b = boxOf(at, meta, fallback);
  return b ? [b[0] + b[2] / 2, b[1] + b[3] / 2] : [0.5, 0.5];
};

const ease = Easing.inOut(Easing.cubic);

type Keyed = { f: number; at: Focus; z: number };
const camAt = (frame: number, cam: Keyed[], meta: Meta | null, fallback: Record<string, number[]>) => {
  const ks = cam.length ? cam : [{ f: 0, at: [0.5, 0.5] as Focus, z: 1 }];
  let i = 0;
  while (i < ks.length - 1 && frame >= ks[i + 1].f) i++;
  const a = ks[i];
  const b = ks[Math.min(i + 1, ks.length - 1)];
  const t = b === a || frame <= a.f ? 0 : ease(Math.min(1, (frame - a.f) / (b.f - a.f)));
  const [ax, ay] = centerOf(a.at, meta, fallback);
  const [bx, by] = centerOf(b.at, meta, fallback);
  return {
    x: ax + (bx - ax) * t,
    y: ay + (by - ay) * t,
    z: Math.exp(Math.log(a.z) + (Math.log(b.z) - Math.log(a.z)) * t),
  };
};

/**
 * Plays a real-app recording with a scripted camera. anchor/lead pick the source time that lines up with local frame 0
 * (lead seconds before the anchor mark). Missing file -> a placeholder card, so the composition always renders.
 */
export const Clip: React.FC<{
  name: string;
  title: string;
  steps?: string[];
  anchor?: string;
  lead?: number;
  cam?: Cam[];
  rings?: Ring[];
  links?: Link[];
  freeze?: number;
  rate?: number;
  fallback?: Record<string, number[]>;
  box?: { left: number; top: number; width: number; height: number };
  dim?: number;
}> = ({ name, title, steps = [], anchor = "start", lead = 0.3, cam = [], rings = [], links = [], freeze, rate = 1, fallback = {}, box = BOX, dim = 0 }) => {
  const frame = useCurrentFrame();
  const { hasVideo, meta } = useRec(name);
  if (!hasVideo) return <Placeholder name={name} title={title} steps={steps} box={box} dim={dim} />;

  const [vw, vh] = meta?.viewport ?? DEFAULT_VIEWPORT;
  const anchorT = meta?.marks[anchor]?.t ?? 0;
  const trim = Math.max(0, Math.round((anchorT - lead) * FPS));
  const lastLocal = meta?.marks.end ? Math.max(0, Math.floor((meta.marks.end.t * FPS - 2 - trim) / rate)) : Infinity;
  const freezeAt = Math.min(freeze ?? Infinity, lastLocal);
  const at = (w: When): number => {
    if (typeof w === "number") return w;
    const [key, off] = typeof w === "string" ? [w, 0] : w;
    const t = meta?.marks[key]?.t;
    return t === undefined ? off : Math.round(((t - anchorT + lead) * FPS) / rate) + off;
  };
  const keyed = cam.map((k) => ({ ...k, f: at(k.f) })).sort((a, b) => a.f - b.f);

  const { x, y, z } = camAt(frame, keyed, meta, fallback);
  const s = Math.max(box.width / vw, box.height / vh) * z;
  const tx = Math.min(0, Math.max(box.width - vw * s, box.width / 2 - x * vw * s));
  const ty = Math.min(0, Math.max(box.height - vh * s, box.height / 2 - y * vh * s));

  const video = <OffthreadVideo src={staticFile(`rec/${name}.mp4`)} trimBefore={trim} playbackRate={rate} muted style={{ width: vw, height: vh, display: "block" }} />;

  return (
    <div style={frameStyle(box)}>
      <div style={{ position: "absolute", left: 0, top: 0, width: vw, height: vh, transformOrigin: "0 0", transform: `translate(${tx}px, ${ty}px) scale(${s})` }}>
        {Number.isFinite(freezeAt) ? (
          <Freeze frame={freezeAt} active={(f) => f >= freezeAt}>
            {video}
          </Freeze>
        ) : (
          video
        )}
        <svg width={vw} height={vh} viewBox={`0 0 ${vw} ${vh}`} style={{ position: "absolute", inset: 0, overflow: "visible" }}>
          <defs>
            <linearGradient id={`lk-${name}`} x1="0" x2="1">
              <stop offset="0" stopColor={C.violet} />
              <stop offset="1" stopColor={C.cyan} />
            </linearGradient>
          </defs>
          {links.map((l, i) => {
            const [ax, ay] = centerOf(l.from, meta, fallback);
            const [bx, by] = centerOf(l.to, meta, fallback);
            const lf = at(l.f);
            const p = interpolate(frame, [lf, lf + (l.dur ?? 18)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
            if (p <= 0) return null;
            const [x0, y0, x1, y1] = [ax * vw, ay * vh, bx * vw, by * vh];
            const mx = (x0 + x1) / 2;
            return (
              <g key={i}>
                <path
                  d={`M ${x0} ${y0} C ${mx} ${y0}, ${mx} ${y1}, ${x1} ${y1}`}
                  stroke={`url(#lk-${name})`}
                  strokeWidth={4 / s}
                  fill="none"
                  strokeLinecap="round"
                  pathLength={1}
                  strokeDasharray={1}
                  strokeDashoffset={1 - p}
                  style={{ filter: `drop-shadow(0 0 ${6 / s}px ${C.violet})` }}
                />
                <circle cx={x0} cy={y0} r={7 / s} fill={C.violet} />
                {p > 0.98 ? <circle cx={x1} cy={y1} r={7 / s} fill={C.cyan} /> : null}
              </g>
            );
          })}
        </svg>
        {rings.map((r, i) => {
          const b = boxOf(r.at, meta, fallback);
          if (!b) return null;
          const dur = r.dur ?? 36;
          const local = frame - at(r.f);
          if (local < 0 || local > dur) return null;
          const p = local / dur;
          const pad = 10 / s;
          const point = b[2] === 0 && b[3] === 0;
          const rad = 34 / s;
          const col = r.color ?? C.cyan;
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: point ? b[0] * vw - rad : b[0] * vw - pad,
                top: point ? b[1] * vh - rad : b[1] * vh - pad,
                width: point ? rad * 2 : b[2] * vw + pad * 2,
                height: point ? rad * 2 : b[3] * vh + pad * 2,
                borderRadius: point ? "50%" : 14 / s,
                border: `${3.5 / s}px solid ${col}`,
                boxShadow: `0 0 ${24 / s}px ${col}, inset 0 0 ${18 / s}px ${col}55`,
                opacity: interpolate(p, [0, 0.12, 0.8, 1], [0, 1, 1, 0]),
                transform: `scale(${interpolate(p, [0, 0.15, 1], [1.12, 1, 1.02])})`,
              }}
            />
          );
        })}
      </div>
      {dim > 0 ? <div style={{ position: "absolute", inset: 0, background: `rgba(7,8,13,${dim})` }} /> : null}
    </div>
  );
};

const frameStyle = (box: { left: number; top: number; width: number; height: number }): React.CSSProperties => ({
  position: "absolute",
  left: box.left,
  top: box.top,
  width: box.width,
  height: box.height,
  overflow: "hidden",
  borderRadius: 28,
  border: `1.5px solid ${C.border2}`,
  boxShadow: "0 30px 90px rgba(0,0,0,0.55), 0 0 60px rgba(139,108,255,0.12)",
  background: C.bg2,
});

const Placeholder: React.FC<{ name: string; title: string; steps: string[]; box: { left: number; top: number; width: number; height: number }; dim: number }> = ({
  name,
  title,
  steps,
  box,
  dim,
}) => {
  const frame = useCurrentFrame();
  const sweep = (frame * 9) % (box.width * 2);
  const blink = Math.sin(frame / 6) > 0 ? 1 : 0.35;
  return (
    <div style={{ ...frameStyle(box), border: `2px dashed ${C.border2}` }}>
      <div style={{ position: "absolute", inset: 0, padding: 54, display: "flex", flexDirection: "column", gap: 22 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14, fontFamily: MONO, fontSize: 26, color: C.cyan, letterSpacing: "0.04em" }}>
          <span style={{ width: 16, height: 16, borderRadius: "50%", background: C.red, opacity: blink, boxShadow: `0 0 14px ${C.red}` }} />
          REC: {name}
        </div>
        <div style={{ fontSize: 40, fontWeight: 700, letterSpacing: "-0.02em", lineHeight: 1.15 }}>{title}</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 6 }}>
          {steps.map((s, i) => (
            <div key={i} style={{ fontSize: 24, color: C.muted, display: "flex", gap: 14 }}>
              <span style={{ fontFamily: MONO, color: C.faint }}>{i + 1}</span>
              {s}
            </div>
          ))}
        </div>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "flex-end", gap: 14 }}>
          {[0.92, 0.7, 0.82, 0.55].map((w, i) => (
            <div key={i} style={{ height: 22, width: `${w * 100}%`, borderRadius: 11, background: C.panel2, overflow: "hidden", position: "relative" }}>
              <div style={{ position: "absolute", top: 0, bottom: 0, width: 260, left: sweep - 300 - i * 80, background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent)" }} />
            </div>
          ))}
          <div style={{ fontFamily: MONO, fontSize: 18, color: C.faint, marginTop: 10 }}>scripts/record_demo.py {name} → public/rec/{name}.mp4</div>
        </div>
      </div>
      {dim > 0 ? <div style={{ position: "absolute", inset: 0, background: `rgba(7,8,13,${dim})` }} /> : null}
    </div>
  );
};
