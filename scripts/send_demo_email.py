"""Send a file as an email attachment to the Lovelight intake inbox (live demo).

Usage: uv run python scripts/send_demo_email.py path/to/invoice.pdf [--subject "..."]
"""

from __future__ import annotations

import argparse
import mimetypes
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv


def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    ap = argparse.ArgumentParser()
    ap.add_argument("file", type=Path)
    ap.add_argument("--subject", default=None)
    ap.add_argument("--to", default=None, help="defaults to GMAIL_USER")
    args = ap.parse_args()

    user, password = os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASSWORD"]
    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = args.to or user
    msg["Subject"] = args.subject or f"Faktura: {args.file.name}"
    msg.set_content("Hej! Bifogar underlag för bokföring.\n")
    ctype = mimetypes.guess_type(args.file.name)[0] or "application/octet-stream"
    maintype, subtype = ctype.split("/", 1)
    msg.add_attachment(args.file.read_bytes(), maintype=maintype, subtype=subtype, filename=args.file.name)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)
    print(f"sent {args.file.name} → {msg['To']}")


if __name__ == "__main__":
    main()
