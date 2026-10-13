import React from "react";
import { AbsoluteFill, Html5Audio, Sequence, staticFile } from "remotion";
import { DOCS } from "./data";
import { BEFORE_FRAMES, Before } from "./scenes/Before";
import { BOOKS_FRAMES, Books } from "./scenes/Books";
import { INBOX_FRAMES, Inbox, arriveAt } from "./scenes/Inbox";
import { MATCHING_FRAMES, Matching, PAIR_STARTS } from "./scenes/Matching";
import { OUTRO_FRAMES, Outro } from "./scenes/Outro";
import { TRANSITION_FRAMES, Transition } from "./scenes/Transition";
import { TRUST_CARD_DELAYS, TRUST_FRAMES, Trust } from "./scenes/Trust";
import { C } from "./theme";

export const SCENES = [
  { id: "before", frames: BEFORE_FRAMES, C: Before },
  { id: "transition", frames: TRANSITION_FRAMES, C: Transition },
  { id: "inbox", frames: INBOX_FRAMES, C: Inbox },
  { id: "matching", frames: MATCHING_FRAMES, C: Matching },
  { id: "books", frames: BOOKS_FRAMES, C: Books },
  { id: "trust", frames: TRUST_FRAMES, C: Trust },
  { id: "outro", frames: OUTRO_FRAMES, C: Outro },
];

export const SCENE_START: Record<string, number> = {};
let acc = 0;
for (const s of SCENES) {
  SCENE_START[s.id] = acc;
  acc += s.frames;
}
export const TOTAL_FRAMES = acc;

type Cue = { at: number; sfx: string; vol: number };
const cues: Cue[] = [];
const add = (at: number, sfx: string, vol: number) => cues.push({ at, sfx, vol });

// Before: ticking clock, clicks on each manual save / dropdown pick.
for (let f = 40; f < BEFORE_FRAMES - 20; f += 15) add(f, "tick", 0.35);
[90, 150, 210].forEach((t) => add(t + 54, "click", 0.6));
[280, 336, 392].forEach((t) => {
  add(t + 27, "click", 0.5);
  add(t + 43, "click", 0.5);
});
// Transition.
add(SCENE_START.transition, "whoosh", 0.8);
add(SCENE_START.transition + 16, "shimmer", 0.5);
// Inbox: arrival pops and a few post checks.
add(SCENE_START.inbox + 8, "whoosh", 0.45);
DOCS.forEach((_, i) => {
  if (i % 3 === 0) add(SCENE_START.inbox + arriveAt(i), "pop", 0.22);
  if (i % 5 === 0) add(SCENE_START.inbox + arriveAt(i) + 75, "check", 0.25);
});
// Matching: whoosh per pair, check when the confidence pill lands.
PAIR_STARTS.forEach((s, i) => {
  add(SCENE_START.matching + s, "whoosh", 0.25);
  add(SCENE_START.matching + s + (i === 3 ? 54 : 26), "check", 0.45);
});
// Books.
add(SCENE_START.books + 64, "check", 0.5);
add(SCENE_START.books + 168, "pop", 0.4);
// Trust.
TRUST_CARD_DELAYS.forEach((d) => add(SCENE_START.trust + d, "alert", 0.35));
// Outro.
add(SCENE_START.outro + 66, "shimmer", 0.5);

export const Lovelight: React.FC = () => (
  <AbsoluteFill style={{ background: C.bg }}>
    {SCENES.map((s) => (
      <Sequence key={s.id} name={s.id} from={SCENE_START[s.id]} durationInFrames={s.frames}>
        <s.C />
      </Sequence>
    ))}
    {cues.map((c, i) => (
      <Sequence key={`${c.sfx}-${i}`} from={c.at} durationInFrames={60} layout="none">
        <Html5Audio src={staticFile(`sfx/${c.sfx}.wav`)} volume={c.vol} />
      </Sequence>
    ))}
  </AbsoluteFill>
);
