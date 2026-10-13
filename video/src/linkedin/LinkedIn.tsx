// LovelightLinkedIn: 1080x1350 portrait, 47.3 s. Shot list and sound cues; scenes live next to this file.
import React from "react";
import { AbsoluteFill, Html5Audio, Sequence, staticFile } from "remotion";
import { C } from "../theme";
import { BOOKS_CUT, BOOKS_FRAMES, Books, END_FRAMES, EndCard, MONTAGE_FRAMES, Montage, TALLY_AT, montageArrive } from "./Close";
import { LI_DOCS } from "./facts";
import { Approve, Audit, BREAK_AT, CHAIN_AT, Correct, VERIFY_AT, Inject, Recon, RefsSum, STAMP_AT, Trace, WHY_ROW_AT, WHY_SCORE_AT, Why } from "./Hero";
import { BlackBox, Bridge, HOOK_DONE, Hook, Hunt, lineStart } from "./Open";

export const LI_SHOTS = [
  { id: "01-hook", frames: 60, C: Hook },
  { id: "02-hunt", frames: 90, C: Hunt },
  { id: "03-blackbox", frames: 90, C: BlackBox },
  { id: "04-bridge", frames: 60, C: Bridge },
  { id: "05-recon", frames: 120, C: Recon },
  { id: "06-refs-sum", frames: 90, C: RefsSum },
  { id: "07-why", frames: 120, C: Why },
  { id: "08-approve", frames: 90, C: Approve },
  { id: "09-trace", frames: 90, C: Trace },
  { id: "10-inject", frames: 90, C: Inject },
  { id: "11-correct", frames: 90, C: Correct },
  { id: "12-audit", frames: 120, C: Audit },
  { id: "13-montage", frames: MONTAGE_FRAMES, C: Montage },
  { id: "14-books", frames: BOOKS_FRAMES, C: Books },
  { id: "15-end", frames: END_FRAMES, C: EndCard },
];

export const LI_START: Record<string, number> = {};
let acc = 0;
for (const s of LI_SHOTS) {
  LI_START[s.id] = acc;
  acc += s.frames;
}
export const LI_TOTAL = acc; // 1419 (47.3 s)

type Cue = { at: number; sfx: string; vol: number; rate?: number };
const cues: Cue[] = [];
const add = (shot: string, f: number, sfx: string, vol: number, rate?: number) => cues.push({ at: LI_START[shot] + f, sfx, vol, rate });

add("01-hook", 0, "whoosh", 0.6);
[0, 1, 2].forEach((k) => add("01-hook", lineStart(k) + 10, "tick", 0.5));
add("01-hook", HOOK_DONE, "check", 0.6);
add("02-hunt", 0, "whoosh", 0.3, 1.6);
for (let f = 6; f < 88; f += 10) add("02-hunt", f, "tick", 0.3);
add("03-blackbox", 50, "alert", 0.35);
add("04-bridge", 2, "shimmer", 0.5);
add("05-recon", 14, "whoosh", 0.3);
add("05-recon", 18, "tick", 0.4);
add("05-recon", 74, "whoosh", 0.22);
add("05-recon", 98, "tick", 0.4);
[0, 1, 2].forEach((k) => add("06-refs-sum", 18 + k * 6, "tick", 0.5));
add("06-refs-sum", 56, "check", 0.55);
add("07-why", 42, "whoosh", 0.25);
WHY_ROW_AT.forEach((f, i) => add("07-why", f, i === 2 ? "alert" : "tick", i === 2 ? 0.2 : 0.45));
add("07-why", WHY_SCORE_AT, "check", 0.6);
add("08-approve", 5, "check", 0.45);
add("08-approve", 64, "click", 0.5);
add("08-approve", 74, "pop", 0.4);
add("09-trace", 0, "whoosh", 0.3);
add("09-trace", 30, "check", 0.45);
add("09-trace", 47, "whoosh", 0.22);
add("09-trace", 56, "check", 0.45);
add("10-inject", 3, "alert", 0.4);
add("10-inject", STAMP_AT, "pop", 0.7, 0.5);
add("11-correct", 24, "click", 0.5);
add("11-correct", 34, "pop", 0.45);
[0, 1, 2, 3].forEach((i) => add("12-audit", CHAIN_AT + i * 5, "tick", 0.45));
add("12-audit", VERIFY_AT, "shimmer", 0.45);
add("12-audit", VERIFY_AT + 2, "check", 0.55);
add("12-audit", BREAK_AT, "alert", 0.4);
LI_DOCS.forEach((_, i) => {
  if (i % 4 === 0) add("13-montage", montageArrive(i), "pop", 0.22);
});
[0, 1, 2].forEach((k) => add("13-montage", TALLY_AT + k * 5, k === 2 ? "alert" : "tick", k === 2 ? 0.3 : 0.45));
add("14-books", 5, "check", 0.5);
add("14-books", 24, "tick", 0.45);
add("14-books", 36, "check", 0.5);
add("14-books", BOOKS_CUT - 1, "whoosh", 0.25);
add("15-end", 0, "whoosh", 0.5);

export const LovelightLinkedIn: React.FC = () => (
  <AbsoluteFill style={{ background: C.bg }}>
    {LI_SHOTS.map((s) => (
      <Sequence key={s.id} name={s.id} from={LI_START[s.id]} durationInFrames={s.frames}>
        <s.C />
      </Sequence>
    ))}
    {cues.map((c, i) => (
      <Sequence key={`${c.sfx}-${i}`} from={c.at} durationInFrames={60} layout="none">
        <Html5Audio src={staticFile(`sfx/${c.sfx}.wav`)} volume={c.vol} playbackRate={c.rate ?? 1} />
      </Sequence>
    ))}
  </AbsoluteFill>
);
