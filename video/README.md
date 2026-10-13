# Lovelight pitch video (Remotion)

Composition `Lovelight`, 1920x1080 @ 30fps, 1710 frames (57 s).

- `npm install`
- `npm run assets` — regenerate `public/docs` (PDF thumbnails via pdftoppm) and `public/sfx` (synthesized WAVs)
- `npm run studio` — preview / scrub
- `npm run render` — `out/lovelight.mp4`

Scenes: `src/scenes/` (Before, Transition, Inbox, Matching, Books, Trust, Outro); timeline + sound cues in `src/Video.tsx`; demo data mirrored from `data/generated/gold.json` in `src/data.ts`.
