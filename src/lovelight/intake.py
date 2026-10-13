"""Gmail IMAP poller and .eml unpacking: unseen mails → every document attachment (or the HTML body) → pipeline.ingest."""

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
MIN_INLINE_IMAGE_BYTES = 15_000  # smaller inline images are logos, signatures or tracking pixels
BODY_TYPES = {"text/plain", "text/html"}

_stop = threading.Event()
_thread: threading.Thread | None = None


def _save(name: str, data: bytes) -> Path:
    pipeline.INCOMING.mkdir(parents=True, exist_ok=True)
    path = pipeline.INCOMING / f"{uuid.uuid4().hex[:8]}_{pipeline.safe_name(data, name)}"
    path.write_bytes(data)
    return path


def _body(msg: EmailMessage) -> str:
    part = msg.get_body(preferencelist=("html", "plain"))
    return part.get_content() if part else ""


def split_message(msg: EmailMessage) -> tuple[str, list[tuple[str, bytes]], list[str]]:
    """(body, documents, skipped) for one mail. Types are sniffed from bytes; filenames and declared types are hints.

    Documents are every PDF/image part, plus text/HTML parts explicitly attached as files. Small inline images
    (logos, signatures) and non-document attachments (calendar invites, archives, ...) are skipped by name.
    """
    body_part = msg.get_body(preferencelist=("html", "plain"))
    docs: list[tuple[str, bytes]] = []
    skipped: list[str] = []
    for i, part in enumerate(msg.walk()):
        if part.is_multipart() or part is body_part:
            continue
        disposition = part.get_content_disposition()
        declared = part.get_content_type()
        name = part.get_filename() or f"attachment_{i}"
        if declared in BODY_TYPES and disposition != "attachment":
            continue  # alternative body rendering
        data = part.get_payload(decode=True) or b""
        mime = pipeline.sniff_mime(data[:4096]) if data else None
        if mime is None or (mime.startswith("text/") and declared not in BODY_TYPES):
            skipped.append(f"{name} ({declared})")
            continue
        if mime.startswith("image/") and disposition != "attachment" and len(data) < MIN_INLINE_IMAGE_BYTES:
            skipped.append(f"{name} (inline image, {len(data)} bytes)")
            continue
        docs.append((name, data))
    return _body(msg), docs, skipped


def _log_skipped(msg: EmailMessage, skipped: list[str]) -> None:
    if skipped:
        log.info("skipped non-document parts in mail %s: %s", msg["Message-ID"], ", ".join(skipped))


def parse_message(raw: bytes) -> list[tuple[Path, str | None]]:
    """Save a mail's documents (each attachment, else the body). Returns (path, email_body) per document.

    With attachments, the body travels with each one as context (it often names the purchase); it is not
    booked separately, so a receipt PDF and the mail describing it are never double-counted.
    """
    msg: EmailMessage = email.message_from_bytes(raw, policy=default_policy)
    body, docs, skipped = split_message(msg)
    _log_skipped(msg, skipped)
    if docs:
        return [(_save(name, data), body or None) for name, data in docs]
    subject = (msg["Subject"] or "email").strip().replace("/", "_")[:60]
    return [(_save(f"{subject}.html", body.encode("utf-8")), body)]


async def ingest_file(path: Path, source: Source = Source.UPLOAD, gold: bool = False) -> None:
    """Ingest an uploaded/replayed file; .eml files are unpacked into attachments or HTML body."""
    if path.suffix.lower() != ".eml":
        await pipeline.ingest(path, source, gold=gold)
        return
    msg = email.message_from_bytes(path.read_bytes(), policy=default_policy)
    sender = parseaddr(msg["From"] or "")[1].lower() or None
    body, docs, skipped = split_message(msg)
    _log_skipped(msg, skipped)
    if not docs:  # body-only mail: the .eml itself is the document
        await pipeline.ingest(path, source, sender=sender, email_body=body, gold=gold)
        return
    for name, data in docs:
        await pipeline.ingest(_save(name, data), source, sender=sender, email_body=body or None, gold=gold)


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
