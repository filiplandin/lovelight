"""Gmail IMAP poller: unseen mails → attachments (or HTML body) → pipeline.ingest."""

from __future__ import annotations

import asyncio
import email
import imaplib
import logging
import os
import threading
import uuid
from email.message import EmailMessage
from email.policy import default as default_policy
from email.utils import parseaddr
from pathlib import Path

from lovelight import pipeline
from lovelight.models import Source

log = logging.getLogger("lovelight.intake")

IMAP_HOST = "imap.gmail.com"
POLL_INTERVAL_S = 10
ATTACHMENT_EXTS = {".pdf", ".png", ".jpg", ".jpeg"}

_stop = threading.Event()
_thread: threading.Thread | None = None


def _save(name: str, data: bytes) -> Path:
    pipeline.INCOMING.mkdir(parents=True, exist_ok=True)
    path = pipeline.INCOMING / f"{uuid.uuid4().hex[:8]}_{Path(name).name}"
    path.write_bytes(data)
    return path


def parse_message(raw: bytes) -> list[tuple[Path, str | None]]:
    """Save a mail's attachments (or its body if none). Returns (path, email_body) per item."""
    msg: EmailMessage = email.message_from_bytes(raw, policy=default_policy)
    items = []
    for part in msg.iter_attachments():
        name = part.get_filename() or ""
        if Path(name).suffix.lower() in ATTACHMENT_EXTS:
            items.append((_save(name, part.get_payload(decode=True)), None))
    if not items:
        body_part = msg.get_body(preferencelist=("html", "plain"))
        body = body_part.get_content() if body_part else ""
        subject = (msg["Subject"] or "email").strip().replace("/", "_")[:60]
        items.append((_save(f"{subject}.html", body.encode("utf-8")), body))
    return items


async def ingest_file(path: Path, source: Source = Source.UPLOAD, gold: bool = False) -> None:
    """Ingest an uploaded/replayed file; .eml files are unpacked into attachments or HTML body."""
    if path.suffix.lower() != ".eml":
        await pipeline.ingest(path, source, gold=gold)
        return
    raw = path.read_bytes()
    msg = email.message_from_bytes(raw, policy=default_policy)
    sender = parseaddr(msg["From"] or "")[1].lower() or None
    attachments = [p for p in msg.iter_attachments() if Path(p.get_filename() or "").suffix.lower() in ATTACHMENT_EXTS]
    if attachments:
        for path_, body in parse_message(raw):
            await pipeline.ingest(path_, source, sender=sender, email_body=body, gold=gold)
        return
    body_part = msg.get_body(preferencelist=("html", "plain"))
    body = body_part.get_content() if body_part else ""
    await pipeline.ingest(path, source, sender=sender, email_body=body, gold=gold)


def poll_once(user: str, password: str, loop: asyncio.AbstractEventLoop) -> int:
    with imaplib.IMAP4_SSL(IMAP_HOST) as imap:
        imap.login(user, password)
        imap.select("INBOX")
        _, data = imap.search(None, "UNSEEN")
        ids = data[0].split()
        for num in ids:
            _, msg_data = imap.fetch(num, "(RFC822)")  # marks as \Seen
            raw = msg_data[0][1]
            sender = parseaddr(email.message_from_bytes(raw)["From"] or "")[1].lower() or None
            if not pipeline.sender_allowed(sender):
                log.warning("mail from non-allowlisted sender %s → will be quarantined", sender)
            for path, body in parse_message(raw):
                fut = asyncio.run_coroutine_threadsafe(
                    pipeline.ingest(path, Source.EMAIL, sender=sender, email_body=body), loop
                )
                fut.result()
        return len(ids)


def _run(user: str, password: str, loop: asyncio.AbstractEventLoop) -> None:
    log.info("IMAP poller started for %s", user)
    while not _stop.is_set():
        try:
            n = poll_once(user, password, loop)
            if n:
                log.info("processed %d new mail(s)", n)
        except imaplib.IMAP4.error as e:
            log.warning("IMAP login/protocol error (%s); email intake disabled until restart", e)
            return
        except Exception:  # keep polling through transient network errors
            log.exception("IMAP poll failed")
        _stop.wait(POLL_INTERVAL_S)


def start(loop: asyncio.AbstractEventLoop) -> bool:
    global _thread
    user, password = os.environ.get("GMAIL_USER"), os.environ.get("GMAIL_APP_PASSWORD")
    if not (user and password):
        log.info("GMAIL_USER/GMAIL_APP_PASSWORD not set; email intake disabled")
        return False
    _stop.clear()
    _thread = threading.Thread(target=_run, args=(user, password, loop), daemon=True)
    _thread.start()
    return True


def stop() -> None:
    _stop.set()
