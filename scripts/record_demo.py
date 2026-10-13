"""Record real-app clips for the LinkedIn video: video/public/rec/<name>.mp4 plus <name>.json marks.

Each clip starts from a clean, deterministic book: POST /api/demo/reset, POST /api/demo/replay (gold cache),
then wait until /api/state stops changing. The page is driven with text/role/data-attribute selectors taken
from src/lovelight/static/app.js. Every important moment is saved as a mark (seconds from clip start plus the
element's box, normalised to the viewport) so the Remotion <Clip> can trim and zoom without hand-tuned numbers.

    uv run python scripts/generate_data.py
    LOVELIGHT_DB=/tmp/ll_rec.db GMAIL_USER= ANTHROPIC_API_KEY= uv run uvicorn lovelight.server:app --port 8600
    uv run --with playwright==1.60.0 python scripts/record_demo.py              # all clips
    uv run --with playwright==1.60.0 python scripts/record_demo.py recon why    # a subset

Capture modes:
  screencast  (default) CDP Page.startScreencast at device pixels (2880x2700 at the defaults), JPEG q95, encoded to
              H.264 CRF 16 at 30 fps CFR. Sharp enough for a 2x zoom.
  playwright  context.record_video_dir. Simpler, but Playwright encodes VP8 at ~1 Mbit/s, so zooms look soft.

--mock drives the in-browser mock backend (?mock=1) and skips the API calls. Use it for a selector dry run
against any static server of src/lovelight/static; its numbers are not the real pipeline's.
Headless Chromium draws no mouse pointer, so a small cursor overlay is injected into the page. Chromium runs with
--force-device-scale-factor so screencast frames are captured at device pixels, not CSS pixels.
"""

from __future__ import annotations

import argparse
import base64
import json
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "video" / "public" / "rec"
SHOTS = ["recon", "why", "approve", "trace", "inject", "correct", "audit", "books"]

CURSOR_JS = """
(() => {
  const install = () => {
    if (document.getElementById("__rec_cursor")) return;
    const c = document.createElement("div");
    c.id = "__rec_cursor";
    c.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24"><path d="M4 2l15 9.5-6.6 1.4L16 21l-3.2 1.4-3.6-8.2L4 18z" '
      + 'fill="#fff" stroke="#07080d" stroke-width="1.3" stroke-linejoin="round"/></svg>';
    Object.assign(c.style, { position: "fixed", left: "0", top: "0", zIndex: 2147483647, pointerEvents: "none",
      transform: "translate(-100px,-100px)", filter: "drop-shadow(0 2px 6px rgba(0,0,0,.55))" });
    document.body.appendChild(c);
    let x = -100, y = -100;
    addEventListener("mousemove", (e) => { x = e.clientX; y = e.clientY; c.style.transform = `translate(${x - 3}px,${y - 2}px)`; }, true);
    addEventListener("mousedown", () => {
      const r = document.createElement("div");
      Object.assign(r.style, { position: "fixed", left: `${x - 18}px`, top: `${y - 18}px`, width: "36px", height: "36px",
        borderRadius: "50%", border: "2px solid #8b6cff", zIndex: 2147483646, pointerEvents: "none",
        transition: "transform .45s ease-out, opacity .45s ease-out" });
      document.body.appendChild(r);
      requestAnimationFrame(() => { r.style.transform = "scale(1.9)"; r.style.opacity = "0"; });
      setTimeout(() => r.remove(), 600);
    }, true);
  };
  if (document.body) install(); else addEventListener("DOMContentLoaded", install);
})();
"""


# ---------------------------------------------------------------- backend


def reset_and_replay(base: str, timeout_s: float) -> dict:
    """Clean book, deterministic gold replay, then block until the state signature is stable for 4 s."""
    with httpx.Client(base_url=base, timeout=30) as http:
        http.post("/api/demo/reset").raise_for_status()
        started = http.post("/api/demo/replay").raise_for_status().json()
        deadline = time.monotonic() + timeout_s
        last, stable_since = None, time.monotonic()
        while time.monotonic() < deadline:
            s = http.get("/api/state").raise_for_status().json()
            docs = [d for d in s["documents"] if d.get("source") != "light_csv"]
            sig = (
                tuple(sorted((d["id"], d["status"]) for d in docs)),
                len(s.get("vouchers", [])),
                tuple(sorted((m["id"], m.get("approved")) for m in s.get("matches", []))),
            )
            if sig != last:
                last, stable_since = sig, time.monotonic()
            elif docs and time.monotonic() - stable_since >= 4.0:
                return {"files": started.get("files"), "docs": len(docs), "matches": len(s.get("matches", []))}
            time.sleep(0.5)
    raise TimeoutError(f"replay did not settle within {timeout_s:.0f}s")


# ---------------------------------------------------------------- recorder


@dataclass
class Recorder:
    """Owns one page and one clip: cursor, eased mouse moves, marks, capture."""

    page: object
    vw: int
    vh: int
    mode: str
    t0: float = 0.0
    x: float = 540.0
    y: float = 675.0
    marks: dict = field(default_factory=dict)
    frames: list = field(default_factory=list)
    frame_dir: Path | None = None
    cdp: object = None
    targets: dict = field(default_factory=dict)

    def now(self) -> float:
        return time.time() - self.t0

    def hold(self, ms: int) -> None:
        self.page.wait_for_timeout(ms)

    def box(self, loc) -> list[float] | None:
        b = loc.bounding_box()
        if not b:
            return None
        return [
            round(b["x"] / self.vw, 4),
            round(b["y"] / self.vh, 4),
            round(b["width"] / self.vw, 4),
            round(b["height"] / self.vh, 4),
        ]

    def mark(self, key: str, loc=None) -> None:
        self.marks[key] = {"t": round(self.now(), 3), "box": self.box(loc) if loc is not None else None}

    def move(self, tx: float, ty: float, ms: int = 600) -> None:
        """Ease-in-out cubic path at ~60 Hz; page.mouse.move(steps=) is linear and looks robotic."""
        n = max(1, ms // 16)
        x0, y0 = self.x, self.y
        for i in range(1, n + 1):
            k = i / n
            e = 4 * k**3 if k < 0.5 else 1 - (-2 * k + 2) ** 3 / 2
            self.page.mouse.move(x0 + (tx - x0) * e, y0 + (ty - y0) * e)
            self.page.wait_for_timeout(16)
        self.x, self.y = tx, ty

    def move_to(self, loc, ms: int = 600, fx: float = 0.5, fy: float = 0.5) -> None:
        b = loc.bounding_box()
        if not b:
            raise RuntimeError(f"element not visible: {loc}")
        self.move(b["x"] + b["width"] * fx, b["y"] + b["height"] * fy, ms)

    def click(self, loc, ms: int = 600) -> None:
        self.move_to(loc, ms)
        self.hold(120)
        self.page.mouse.down()
        self.hold(70)
        self.page.mouse.up()

    def center(self, loc) -> None:
        loc.evaluate("el => el.scrollIntoView({block: 'center', inline: 'nearest'})")
        self.hold(250)

    # capture ------------------------------------------------------------

    def start(self, scale: int) -> None:
        self.page.mouse.move(self.x, self.y)
        if self.mode == "screencast":
            self.frame_dir = Path(tempfile.mkdtemp(prefix="rec_"))
            self.cdp = self.page.context.new_cdp_session(self.page)
            self.cdp.on("Page.screencastFrame", self._on_frame)
            self.cdp.send(
                "Page.startScreencast",
                {
                    "format": "jpeg",
                    "quality": 95,
                    "maxWidth": self.vw * scale,
                    "maxHeight": self.vh * scale,
                    "everyNthFrame": 1,
                },
            )
            self.hold(300)
            self.t0 = self.frames[0][0] if self.frames else time.time()
        else:
            self.t0 = time.time()
        self.mark("start")

    def _on_frame(self, ev: dict) -> None:
        i = len(self.frames)
        path = self.frame_dir / f"f{i:05d}.jpg"
        path.write_bytes(base64.b64decode(ev["data"]))
        self.frames.append((ev["metadata"]["timestamp"], path))
        self.cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})

    def stop(self) -> None:
        self.mark("end")
        if self.mode == "screencast":
            self.cdp.send("Page.stopScreencast")
            self.hold(100)

    def encode_screencast(self, out_mp4: Path) -> None:
        if not self.frames:
            raise RuntimeError("screencast produced no frames")
        end = self.t0 + self.marks["end"]["t"]
        lines = []
        for i, (ts, path) in enumerate(self.frames):
            nxt = self.frames[i + 1][0] if i + 1 < len(self.frames) else max(end, ts + 1 / 30)
            lines += [f"file '{path}'", f"duration {max(nxt - ts, 0.001):.4f}"]
        lines.append(f"file '{self.frames[-1][1]}'")
        listing = self.frame_dir / "frames.txt"
        listing.write_text("\n".join(lines) + "\n")
        ffmpeg(
            [
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(listing),
                "-vf",
                "fps=30,scale=trunc(iw/2)*2:trunc(ih/2)*2",
                "-c:v",
                "libx264",
                "-preset",
                "slow",
                "-crf",
                "16",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(out_mp4),
            ]
        )
        shutil.rmtree(self.frame_dir, ignore_errors=True)


def ffmpeg(args: list[str]) -> None:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("ffmpeg not found on PATH (brew install ffmpeg)")
    subprocess.run([exe, "-y", "-loglevel", "error", *args], check=True)


# ---------------------------------------------------------------- shots
# Selectors come from src/lovelight/static/app.js. Assumptions are noted where the UI could drift.


def lump_row(r: Recorder):
    """The 1:3 lump-sum row. Assumes the bank text (default 'LB LEVBET 3 ST') is rendered in .mrow (viewRecon)."""
    return r.page.locator(".mrow", has_text=r.targets["lump"]).first


def shot_recon(r: Recorder) -> None:
    row = lump_row(r)
    row.wait_for()
    r.center(row)
    r.mark("row", row)
    bank = row.locator(".side").first
    r.mark("bank", bank)
    r.mark("connector", row.locator(".connector"))
    r.mark("docs", row.locator(":scope > div").nth(2))
    r.move_to(bank, 700)
    r.hold(1000)
    r.mark("hover_bank", bank)
    r.move_to(row.locator(".connector"), 700)
    for i, side in enumerate(row.locator("[data-doc]").all()):
        r.move_to(side, 500, fx=0.3)
        r.mark(f"doc{i}", side)
        r.hold(350)
    r.hold(1200)


def shot_why(r: Recorder) -> None:
    row = lump_row(r)
    row.wait_for()
    r.center(row)
    r.mark("row", row)
    pill = row.locator("button.why")
    r.mark("pill", pill)
    r.click(pill, 700)
    pop = r.page.locator("#pop")
    pop.wait_for()
    r.hold(200)
    r.mark("pop", pop)
    for i, cb in enumerate(pop.locator(".cb-row").all()):
        r.move_to(cb, 420, fx=0.15)
        r.mark(f"check{i}", cb)
        r.hold(450)
    gate = pop.locator(".cb-gate")
    if gate.count():
        r.move_to(gate.first, 420, fx=0.2)
        r.mark("gate", gate.first)
    r.hold(3000)


def shot_approve(r: Recorder) -> None:
    """Matches >= 0.95 auto-approve during replay (pipeline.AUTO_APPROVE_MATCH), so BT014 usually arrives approved.
    Then the clip shows its green pill and method, and approves the next lower-scored match by hand if there is one."""
    page = r.page
    row = lump_row(r)
    row.wait_for()
    r.center(row)
    r.mark("row", row)
    btn = row.locator("[data-approve]")
    if btn.count():
        r.click(btn, 700)
        row.locator(".pill.green", has_text="Approved").wait_for()
        r.mark("approved", row.locator(".actions"))
        r.hold(1500)
        return
    actions = row.locator(".actions")
    r.move_to(actions, 700)
    r.mark("approved", actions)
    r.hold(1800)
    # Matches whose documents still need review are blocked server-side (409), so pick the first unblocked one.
    ready = page.evaluate(
        "() => window.Lovelight.state().matches.filter((m) => !m.approved && !(m.blocked_by || []).length).map((m) => m.id)"
    )
    btns = [b for b in page.locator(".mrow:not(.approved) [data-approve]").all() if b.get_attribute("data-approve") in ready]
    if btns:
        other = btns[0].locator("xpath=ancestor::*[contains(concat(' ', @class, ' '), ' mrow ')][1]")
        r.center(other)
        r.mark("other_row", other)
        ob = other.locator("[data-approve]")
        r.mark("other_btn", ob)
        r.click(ob, 700)
        r.mark("other_clicked")
    r.hold(1500)


def open_doc(r: Recorder, filename: str, filt: str | None = None) -> object:
    """Assumes inbox cards (.card.doc) show the filename in .fn, and filters are [data-filter=...] buttons."""
    page = r.page
    if filt:
        b = page.locator(f'[data-filter="{filt}"]')
        r.click(b, 600)
        r.hold(400)
    card = page.locator(".card.doc", has_text=filename).first
    card.wait_for()
    r.center(card)
    r.mark("card", card)
    r.click(card, 700)
    drawer = page.locator("#drawer.on")
    drawer.wait_for()
    r.hold(600)
    return drawer


def shot_trace(r: Recorder) -> None:
    drawer = open_doc(r, r.targets["trace"])
    preview = drawer.locator(".preview, .paper").first
    preview.wait_for()
    r.hold(1200)  # PDF/iframe paint
    r.mark("preview", preview)
    gross = drawer.locator(".field", has_text="Gross").first
    r.mark("gross", gross)
    r.move_to(preview, 700, fy=0.62)
    r.hold(400)
    r.move_to(gross, 700)
    r.hold(300)
    voucher = drawer.locator(".section", has=r.page.locator(".section-title", has_text="Voucher")).first
    r.center(voucher)
    r.hold(500)
    r.mark("voucher", voucher)
    r.mark("preview_after_scroll", preview)
    total = voucher.locator("tr.total")
    if total.count():  # absent when the document has no voucher yet
        r.move_to(total.first, 700)
        r.mark("voucher_total", total.first)
    r.hold(1500)


def shot_inject(r: Recorder) -> None:
    drawer = open_doc(r, r.targets["inject"], filt="quarantined")
    pill = drawer.locator(".drawer-head .pill.red").first
    r.mark("pill", pill)
    r.move_to(pill, 600)
    r.hold(900)
    anom = drawer.locator(".card.anom").first
    if anom.count():
        r.mark("anomaly", anom)
    never = drawer.locator(".empty", has_text="Never posted")
    r.center(never)
    r.mark("never", never)
    r.move_to(never, 700)
    r.hold(2000)


def shot_correct(r: Recorder) -> None:
    """Assumes the Kjell receipt has a live voucher (so .correct-form renders). Picks 6110 if offered.
    The receipt is bank-matched (status 'matched'), so it only appears under the 'all' filter, not 'posted'."""
    drawer = open_doc(r, r.targets["correct"])
    form = drawer.locator("form.correct-form")
    r.center(form)
    r.mark("form", form)
    select = form.locator("select[name=account]")
    values = select.locator("option").evaluate_all("os => os.map(o => o.value)")
    target = "6110" if "6110" in values else values[0]
    r.move_to(select, 600)
    select.select_option(target)
    r.hold(500)
    reason = form.locator("input[name=reason]")
    r.click(reason, 500)
    reason.press_sequentially("Office supplies, not equipment", delay=55)
    r.hold(300)
    r.click(form.locator("button[type=submit]"), 600)
    fix = drawer.locator(".fixcard")
    fix.wait_for(timeout=15000)
    r.hold(1000)  # submitCorrection() refreshes state and re-renders the drawer after the card first appears
    r.center(fix)
    r.mark("fix", fix)
    r.move_to(fix, 600, fx=0.3)
    r.hold(2500)


def shot_audit(r: Recorder) -> None:
    page = r.page
    badge = page.locator(".chain-hero .chain-badge.ok")
    badge.wait_for(timeout=15000)
    r.mark("badge", badge)
    r.move_to(badge, 700)
    r.hold(700)
    r.click(page.locator('[data-act="verify"]'), 700)
    page.locator(".toast", has_text="Chain verified").wait_for(timeout=10000)
    r.mark("verified_toast", page.locator(".toast", has_text="Chain verified").last)
    head = page.locator(".chain-head")
    r.move_to(head, 700)
    r.mark("head", head)
    r.hold(1000)
    r.mark("badge_after", page.locator(".chain-hero .chain-badge.ok"))
    r.hold(1200)


def shot_books(r: Recorder) -> None:
    page = r.page
    assets = page.locator("tr.total", has_text="Total assets")
    liab = page.locator("tr.total", has_text="Total equity")
    assets.wait_for()
    r.center(assets)
    r.mark("assets", assets)
    r.mark("liab", liab)
    r.move_to(assets, 600, fx=0.85)
    r.hold(600)
    r.move_to(liab, 600, fx=0.85)
    r.hold(1000)
    btn = page.locator('[data-act="siePreview"]')
    r.center(btn)
    r.click(btn, 700)
    pre = page.locator("#modal pre")
    page.wait_for_function(
        "() => { const p = document.querySelector('#modal pre'); return p && p.textContent.startsWith('#'); }",
        timeout=15000,
    )
    r.mark("sie", pre)
    r.hold(1500)


@dataclass
class Shot:
    view: str
    run: Callable[[Recorder], None]
    describe: str


SHOT_DEFS = {
    "recon": Shot("recon", shot_recon, "BT014 'LB LEVBET 3 ST' row centred, hover bank side, walk the 1:3 connectors"),
    "why": Shot("recon", shot_why, "click the BT014 confidence pill, hold the 'Why' popover"),
    "approve": Shot(
        "recon",
        shot_approve,
        "BT014 approved state (auto-approved at >=95%), then approve a lower-scored match by hand",
    ),
    "trace": Shot("inbox", shot_trace, "Telia invoice drawer: source PDF, Gross field, voucher totals"),
    "inject": Shot("inbox", shot_inject, "Quarantined filter, Nordic Growth Partners drawer, 'Never posted' note"),
    "correct": Shot("inbox", shot_correct, "Kjell receipt: change account, reason, reverse & re-post, result note"),
    "audit": Shot("audit", shot_audit, "Chain verified badge, Re-verify, hover head hash"),
    "books": Shot("books", shot_books, "Balance sheet totals, SIE4 preview modal"),
}


def record(pw, args, name: str) -> Path:
    shot = SHOT_DEFS[name]
    if not args.mock:
        info = reset_and_replay(args.base_url, args.replay_timeout)
        print(f"  replay settled: {info}")
    # Screencast frames come at CSS-pixel size unless Chromium itself renders at the higher scale.
    launch_args = [f"--force-device-scale-factor={args.scale}"]
    browser = pw.chromium.launch(headless=not args.headed, channel=args.channel, args=launch_args)
    try:
        return _record(browser, args, name, shot)
    finally:
        browser.close()


def _record(browser, args, name: str, shot: Shot) -> Path:
    vw, vh, scale = args.width, args.height, args.scale
    ctx_kw = {"viewport": {"width": vw, "height": vh}, "device_scale_factor": scale, "color_scheme": "dark"}
    tmp_video = None
    if args.capture == "playwright":
        tmp_video = Path(tempfile.mkdtemp(prefix="recvid_"))
        ctx_kw |= {"record_video_dir": str(tmp_video), "record_video_size": {"width": vw * scale, "height": vh * scale}}
    ctx = browser.new_context(**ctx_kw)
    ctx.add_init_script(CURSOR_JS)
    page = ctx.new_page()
    page.set_default_timeout(args.step_timeout * 1000)
    qs = f"view={shot.view}" + ("&mock=1" if args.mock else "")
    page.goto(f"{args.base_url.rstrip('/')}/?{qs}")
    page.wait_for_function(
        "() => window.Lovelight && window.Lovelight.state() && window.Lovelight.state().documents.length > 0"
    )
    page.evaluate("() => document.fonts.ready")
    page.wait_for_timeout(1200)  # entry animations + audit/knowledge fetches
    targets = {
        "lump": args.lump_text,
        "trace": args.trace_file,
        "inject": args.inject_file,
        "correct": args.correct_file,
    }
    r = Recorder(page=page, vw=vw, vh=vh, mode=args.capture, targets=targets)
    r.start(scale)
    r.hold(400)
    shot.run(r)
    r.stop()
    args.out.mkdir(parents=True, exist_ok=True)
    mp4 = args.out / f"{name}.mp4"
    if args.capture == "screencast":
        r.encode_screencast(mp4)
        ctx.close()
    else:
        video = page.video
        ctx.close()
        webm = args.out / f"{name}.webm"
        shutil.move(video.path(), webm)
        shutil.rmtree(tmp_video, ignore_errors=True)
        if shutil.which("ffmpeg"):
            ffmpeg(["-i", str(webm), "-vf", "fps=30", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(mp4)])
        else:
            print(f"  ffmpeg missing: kept {webm}; convert to {mp4.name} before rendering")
    meta = {
        "name": name,
        "describe": shot.describe,
        "viewport": [vw, vh],
        "scale": scale,
        "capture": args.capture,
        "mock": args.mock,
        "base_url": args.base_url,
        "marks": r.marks,
    }
    (args.out / f"{name}.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    return mp4


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("shots", nargs="*", metavar="SHOT", help=f"clips to record (default: all): {', '.join(SHOTS)}")
    ap.add_argument("--base-url", default="http://localhost:8600")
    ap.add_argument("--out", type=Path, default=OUT, help="output dir (default: video/public/rec)")
    # 1440 wide: at 1080 the sidebar leaves ~280 px per recon column and long bank texts get ellipsised.
    # Remotion crops/zooms the clip into the 1080x1350 frame either way.
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=1350)
    ap.add_argument("--scale", type=int, default=2, help="deviceScaleFactor; capture is width*scale x height*scale")
    ap.add_argument("--capture", choices=["screencast", "playwright"], default="screencast")
    ap.add_argument(
        "--channel",
        default="chromium",
        help="'chromium' (default) is full headless Chromium, which renders the PDF preview iframe; the bare headless "
        "shell leaves it blank. 'chrome' uses installed Google Chrome.",
    )
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--mock", action="store_true", help="drive ?mock=1 (no backend calls); selector dry run only")
    ap.add_argument("--lump-text", default="LB LEVBET 3 ST", help="bank text of the 1:n row")
    ap.add_argument("--trace-file", default="telia_faktura_88213456.pdf")
    ap.add_argument("--inject-file", default="faktura_nordic_growth_partners_7781.pdf")
    ap.add_argument("--correct-file", default="kvitto_kjell_0911.pdf")
    ap.add_argument("--replay-timeout", type=float, default=240)
    ap.add_argument("--step-timeout", type=float, default=20, help="seconds per UI wait")
    args = ap.parse_args()

    names = args.shots or SHOTS
    unknown = sorted(set(names) - set(SHOTS))
    if unknown:
        ap.error(f"unknown shot(s): {', '.join(unknown)}")

    from playwright.sync_api import sync_playwright  # imported late so --help works without playwright

    failed = []
    with sync_playwright() as pw:
        for name in names:
            print(f"[{name}] {SHOT_DEFS[name].describe}")
            try:
                print(f"  -> {record(pw, args, name)}")
            except Exception as e:  # keep recording the other clips; report at the end
                failed.append(name)
                print(f"  FAILED: {type(e).__name__}: {e}")
    if failed:
        sys.exit(f"failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
