// Synthesizes short UI sound effects as 16-bit mono WAVs into public/sfx.
import { writeFileSync, mkdirSync } from "node:fs";

const SR = 44100;
mkdirSync("public/sfx", { recursive: true });

function wav(samples) {
  const buf = Buffer.alloc(44 + samples.length * 2);
  buf.write("RIFF", 0); buf.writeUInt32LE(36 + samples.length * 2, 4); buf.write("WAVE", 8);
  buf.write("fmt ", 12); buf.writeUInt32LE(16, 16); buf.writeUInt16LE(1, 20); buf.writeUInt16LE(1, 22);
  buf.writeUInt32LE(SR, 24); buf.writeUInt32LE(SR * 2, 28); buf.writeUInt16LE(2, 32); buf.writeUInt16LE(16, 34);
  buf.write("data", 36); buf.writeUInt32LE(samples.length * 2, 40);
  samples.forEach((s, i) => buf.writeInt16LE(Math.max(-1, Math.min(1, s)) * 32767, 44 + i * 2));
  return buf;
}

let seed = 1;
const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647) * 2 - 1;

function whoosh(dur = 0.7) {
  const n = Math.floor(SR * dur); const out = new Array(n); let lp = 0;
  for (let i = 0; i < n; i++) {
    const t = i / n; const env = Math.sin(Math.PI * t) ** 2;
    const a = 0.02 + 0.25 * Math.sin(Math.PI * t); // sweeping low-pass coefficient
    lp += a * (rand() - lp); out[i] = lp * env * 0.9;
  }
  return out;
}
function tone(freqs, dur, vol = 0.3, decay = 18) {
  const n = Math.floor(SR * dur); const out = new Array(n);
  for (let i = 0; i < n; i++) {
    const t = i / SR; const env = Math.exp(-decay * t) * Math.min(1, t * 400);
    out[i] = freqs.reduce((s, f) => s + Math.sin(2 * Math.PI * f * t), 0) / freqs.length * env * vol;
  }
  return out;
}
function click() {
  const n = Math.floor(SR * 0.03); const out = new Array(n);
  for (let i = 0; i < n; i++) out[i] = rand() * Math.exp(-i / (SR * 0.004)) * 0.5;
  return out;
}
function tick() { return tone([2400], 0.04, 0.15, 120); }
function shimmer() {
  const notes = [523.25, 659.25, 783.99, 1046.5]; const n = Math.floor(SR * 1.6); const out = new Array(n).fill(0);
  notes.forEach((f, k) => {
    const off = Math.floor(k * SR * 0.09);
    const t1 = tone([f, f * 2], 1.6 - k * 0.09, 0.18, 3);
    t1.forEach((s, i) => { if (off + i < n) out[off + i] += s; });
  });
  return out;
}
function alert() { return [...tone([330, 311], 0.18, 0.25, 10), ...tone([311, 294], 0.22, 0.25, 10)]; }

writeFileSync("public/sfx/whoosh.wav", wav(whoosh()));
writeFileSync("public/sfx/pop.wav", wav(tone([880, 1320], 0.18, 0.25, 25)));
writeFileSync("public/sfx/check.wav", wav([...tone([1046.5], 0.08, 0.2, 30), ...tone([1568], 0.2, 0.2, 18)]));
writeFileSync("public/sfx/click.wav", wav(click()));
writeFileSync("public/sfx/tick.wav", wav(tick()));
writeFileSync("public/sfx/shimmer.wav", wav(shimmer()));
writeFileSync("public/sfx/alert.wav", wav(alert()));
console.log("sfx written");
