# Lovelight pitch video (Remotion)

Composition `Lovelight`, 1920x1080 @ 30fps, 1710 frames (57 s).

- `npm install`
- `npm run assets` — regenerate `public/docs` (PDF thumbnails via pdftoppm) and `public/sfx` (synthesized WAVs)
- `npm run studio` — preview / scrub
- `npm run render` — `out/lovelight.mp4`

Scenes: `src/scenes/` (Before, Transition, Inbox, Matching, Books, Trust, Outro); timeline + sound cues in `src/Video.tsx`; demo data mirrored from `data/generated/gold.json` in `src/data.ts`.

## LinkedIn cut

Composition `LovelightLinkedIn`, 1080x1350 @ 30fps, 1419 frames (47.3 s). Scenes, shot list and sound cues in `src/linkedin/` (`LinkedIn.tsx` is the timeline, `facts.ts` holds every on-screen number with its source).

- Real-app clips: start the app on a throwaway DB (`LOVELIGHT_DB=/tmp/ll_rec.db GMAIL_USER= ANTHROPIC_API_KEY= uv run uvicorn lovelight.server:app --port 8600`, gold-cache replay = deterministic numbers), then from the repo root `uv run --with playwright==1.60.0 python scripts/record_demo.py` → `public/rec/<shot>.mp4` + `.json` marks. Missing clips render as placeholder cards.
- `npm run render:linkedin` — `out/lovelight-linkedin.mp4`
