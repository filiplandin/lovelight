"""FastAPI app: HTTP contract from AGENTS.md, SSE event stream, static UI."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections import Counter
from contextlib import asynccontextmanager
from datetime import date
from importlib.metadata import version
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from lovelight import audit, extract, intake, pipeline, store
from lovelight.metrics import METRICS
from lovelight.models import CLIENT_NAME, CLIENT_ORG_NR, Match, Source, Voucher

load_dotenv(store.ROOT / ".env")
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("lovelight.server")

STATIC = Path(__file__).parent / "static"
REPLAY_DELAY_S = 0.7
KEEPALIVE_S = 15
MAX_FILES_PER_UPLOAD = 200
UPLOAD_CHUNK = 1024 * 1024
# Uploaded and emailed files are untrusted: never let them run script or load anything on the app's origin.
FILE_HEADERS = {
    "Content-Security-Policy": "sandbox; default-src 'none'; img-src data:; style-src 'unsafe-inline'",
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "no-store",
}
# Browsers refuse to run their PDF viewer under a sandbox CSP, so byte-verified PDFs get nosniff + same-origin
# framing only; PDF rendering then relies on the browser's own PDF sandbox.
PDF_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Cache-Control": "no-store",
}

_replay_task: asyncio.Task | None = None
_background: set[asyncio.Task] = set()


def _spawn(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _background.add(task)
    task.add_done_callback(_background.discard)
    return task


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.connect()
    pipeline.bootstrap_if_empty()  # a restart keeps the books; /api/demo/reset starts over explicitly
    intake.start(asyncio.get_running_loop())
    yield
    intake.stop()


app = FastAPI(title="Lovelight", lifespan=lifespan)



@app.get("/api/state")
def get_state() -> dict:
    return pipeline.state()


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": version("lovelight"),
        "docs": store.count("documents"),
        "vouchers": store.count("vouchers"),
        "extraction_mode": extract.mode(),
    }


@app.get("/api/metrics")
def metrics() -> dict:
    """Pipeline latency per stage and outcome counts since the last reset/replay."""
    return {**METRICS.snapshot(limit=pipeline.MAX_CONCURRENCY), "extraction_mode": extract.mode()}


@app.get("/api/events")
async def events() -> StreamingResponse:
    q = pipeline.subscribe()

    async def stream():
        try:
            yield ": connected\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), KEEPALIVE_S)
                    yield f"data: {json.dumps(event)}\n\n"
                except TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            pipeline.unsubscribe(q)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/upload")
async def upload(files: list[UploadFile]) -> dict:
    if len(files) > MAX_FILES_PER_UPLOAD:
        raise HTTPException(413, f"at most {MAX_FILES_PER_UPLOAD} files per upload")
    pipeline.INCOMING.mkdir(parents=True, exist_ok=True)
    blobs = []
    for f in files:  # read in chunks and stop at the limit, so one huge file cannot exhaust memory
        chunks, size = [], 0
        while chunk := await f.read(UPLOAD_CHUNK):
            size += len(chunk)
            if size > pipeline.MAX_FILE_BYTES:
                raise HTTPException(413, f"{f.filename}: larger than {pipeline.MAX_FILE_BYTES // (1024 * 1024)} MB")
            chunks.append(chunk)
        blobs.append((f.filename, b"".join(chunks)))
    paths = []
    for filename, data in blobs:
        name = pipeline.safe_name(data, filename or "upload.bin")  # extension follows the bytes, not the client
        path = pipeline.INCOMING / f"{uuid.uuid4().hex[:8]}_{name}"
        path.write_bytes(data)
        paths.append(path)

    async def run():
        results = await pipeline.run_batch(intake.ingest_file(p, Source.UPLOAD) for p in paths)
        for p, r in zip(paths, results, strict=True):
            if isinstance(r, Exception):  # one unreadable file must not stop the batch
                log.error("failed to ingest %s", p, exc_info=r)

    _spawn(run())
    return {"accepted": len(paths), "filenames": [p.name for p in paths]}


async def _ingest_safe(path: Path, gold: bool = False) -> None:
    try:
        await intake.ingest_file(path, Source.UPLOAD, gold=gold)
    except Exception:  # one unreadable file must not stop the batch
        log.exception("failed to ingest %s", path)


async def _replay(live: bool = False) -> None:
    """Re-run the demo inbox from a clean book.

    Gold (default): sequential, deterministic extractions from gold.json, so every run produces identical books.
    Live: real Claude calls, staggered by REPLAY_DELAY_S and overlapping up to pipeline.MAX_CONCURRENCY.
    """
    files = sorted(p for p in pipeline.INBOX.iterdir() if p.is_file() and not p.name.startswith("."))
    async with pipeline.ledger_lock():
        pipeline.bootstrap()
    pipeline.emit("state.reset")
    if not live:
        for i, p in enumerate(files):
            if i:
                await asyncio.sleep(REPLAY_DELAY_S)
            await _ingest_safe(p, gold=True)
        return

    async def staggered(i: int, p: Path) -> None:
        await asyncio.sleep(i * REPLAY_DELAY_S)
        await _ingest_safe(p)

    await asyncio.gather(*(staggered(i, p) for i, p in enumerate(files)))


@app.post("/api/demo/replay")
async def demo_replay(live: bool = Query(False, description="Extract with Claude instead of gold.json")) -> dict:
    global _replay_task
    if not pipeline.INBOX.exists():
        raise HTTPException(404, f"inbox missing: {pipeline.INBOX}")
    if live and extract.mode() != "live":
        raise HTTPException(400, "live replay needs ANTHROPIC_API_KEY")
    if _replay_task and not _replay_task.done():
        return {"status": "already_running"}
    _replay_task = _spawn(_replay(live=live))
    return {
        "status": "started",
        "mode": "live" if live else "gold-cache",
        "files": sum(1 for p in pipeline.INBOX.iterdir() if p.is_file()),
    }


@app.post("/api/demo/reset")
async def demo_reset() -> dict:
    global _replay_task
    if _replay_task and not _replay_task.done():
        _replay_task.cancel()
    _replay_task = None
    async with pipeline.ledger_lock():
        pipeline.bootstrap()
    pipeline.emit("state.reset")
    return {"status": "reset"}


@app.post("/api/matches/{match_id}/approve")
async def approve_match(match_id: str) -> dict:
    m = store.get("matches", match_id, Match)
    if m is None:
        raise HTTPException(404, "match not found")
    async with pipeline.ledger_lock():
        try:
            m = pipeline.approve_match(m, actor="user:accountant")
        except pipeline.MatchBlocked as e:
            raise HTTPException(409, f"approve the documents first: {e}") from e
    return pipeline.to_json(m)


@app.post("/api/matches/approve-all")
async def approve_all() -> dict:
    approved = []
    async with pipeline.ledger_lock():
        for m in store.all("matches", Match):
            if not m.approved and m.confidence >= pipeline.AUTO_APPROVE_MATCH and not pipeline.match_blockers(m):
                approved.append(pipeline.approve_match(m, actor="user:accountant").id)
    return {"approved": approved}


@app.get("/api/export/sie4")
def export_sie4() -> Response:
    from lovelight import ledger, sie

    posted = [v for v in store.all("vouchers", Voucher) if v.status in ("posted", "reversed")]
    if bad := ledger.validate_all(posted):
        raise HTTPException(409, f"voucher {bad} does not balance; run /api/audit/verify before exporting")
    years = Counter(v.date.year for v in posted)  # majority year; planted bad dates must not pick the FY
    year = years.most_common(1)[0][0] if years else date.today().year
    text = sie.to_sie4(posted, CLIENT_NAME, CLIENT_ORG_NR, year)
    return Response(
        content=text.encode("cp437", errors="replace"),
        media_type="text/plain; charset=cp437",
        headers={"Content-Disposition": 'attachment; filename="lovelight.se"'},
    )


@app.get("/api/documents/{doc_id}/file")
def document_file(doc_id: str) -> FileResponse:
    """The original file, sandboxed: HTML and other text is served as text/plain under a no-script CSP."""
    path = store.get_file(doc_id)
    if path is None or not path.exists():
        raise HTTPException(404, "file not found")
    with path.open("rb") as f:
        mime = pipeline.sniff_mime(f.read(4096)) or "application/octet-stream"
    if mime.startswith("text/"):
        mime = "text/plain; charset=utf-8"
    headers = PDF_HEADERS if mime == "application/pdf" else FILE_HEADERS
    return FileResponse(path, media_type=mime, headers=headers, content_disposition_type="inline")


@app.get("/api/documents/{doc_id}/model-output")
def document_model_output(doc_id: str) -> dict:
    """The schema-validated model output for a document, as hashed into its doc.extracted audit event."""
    raw = store.get_raw("model_outputs", doc_id)
    if raw is None:
        raise HTTPException(404, "no model output for this document")
    return json.loads(raw)


class ApproveIn(BaseModel):
    user: str = "accountant"
    note: str | None = None


class RejectIn(BaseModel):
    reason: str
    user: str = "accountant"


@app.post("/api/documents/{doc_id}/approve")
async def approve_document(doc_id: str, body: ApproveIn | None = None) -> dict:
    """Post the proposed voucher of a document in review. User names are self-asserted (no per-user auth)."""
    body = body or ApproveIn()
    async with pipeline.ledger_lock():
        try:
            return pipeline.approve_document(doc_id, body.user, body.note)
        except pipeline.CorrectionError as e:
            raise HTTPException(e.status, str(e)) from e


@app.post("/api/documents/{doc_id}/reject")
async def reject_document(doc_id: str, body: RejectIn) -> dict:
    """Reject a document in review or quarantine; its proposed voucher is never posted."""
    async with pipeline.ledger_lock():
        try:
            return pipeline.reject_document(doc_id, body.reason, body.user)
        except pipeline.CorrectionError as e:
            raise HTTPException(e.status, str(e)) from e


class CorrectionIn(BaseModel):
    account: str
    reason: str
    user: str = "accountant"


@app.post("/api/documents/{doc_id}/correct")
async def correct_document(doc_id: str, body: CorrectionIn) -> dict:
    """Re-book a document: reversal + corrected voucher, never an edit. User names are self-asserted (no auth yet)."""
    async with pipeline.ledger_lock():
        try:
            return pipeline.correct(doc_id, body.account, body.reason, body.user)
        except pipeline.CorrectionError as e:
            raise HTTPException(e.status, str(e)) from e


@app.get("/api/audit")
def get_audit(entity_id: str | None = None, limit: int = Query(500, ge=1, le=10000)) -> list[dict]:
    """Audit events (oldest first), optionally those concerning one entity/document; the newest `limit`."""
    return [e.model_dump(mode="json") for e in audit.events(entity_id)[-limit:]]


@app.get("/api/audit/verify")
def verify_audit() -> dict:
    return audit.verify()


@app.get("/api/knowledge")
def get_knowledge() -> dict:
    from lovelight import knowledge

    kb = knowledge.load()
    counts = Counter(e.action for e in audit.events())
    return pipeline.to_json(
        {
            "version": kb.version,
            "activities": kb.activities,
            "accounts": kb.accounts,
            "vendors": kb.vendors,
            "stats": {"hits": counts["kb.hit"], "misses": counts["kb.miss"]},
            "proposals": pipeline.kb_proposals(),
        }
    )


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
