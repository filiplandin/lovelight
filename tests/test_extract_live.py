"""Live Claude extraction on renamed inbox files (so gold.json cannot answer). Skipped without ANTHROPIC_API_KEY."""

import os
import shutil
import time
from decimal import Decimal
from pathlib import Path

import pytest
from dotenv import load_dotenv

from lovelight import extract

INBOX = extract.ROOT / "data" / "generated" / "inbox"

load_dotenv(extract.ROOT / ".env")
pytestmark = pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="no ANTHROPIC_API_KEY")


def _live(tmp_path: Path, monkeypatch, src: str, new_name: str):
    monkeypatch.setattr(extract, "CACHE_PATH", tmp_path / "cache.json")
    dst = tmp_path / new_name
    shutil.copy(INBOX / src, dst)
    t0 = time.perf_counter()
    ex, model = extract.extract(dst)
    print(f"{src}: {time.perf_counter() - t0:.1f}s model={model} vendor={ex.vendor} acct={ex.suggested_account}")
    assert model == extract.MODEL
    assert Decimal(ex.net) + Decimal(ex.vat) == Decimal(ex.gross)
    return ex


@pytest.mark.parametrize(
    ("src", "vendor_hint"),
    [("telia_faktura_88213456.pdf", "telia"), ("IMG_4471.png", None)],
)
def test_live_extraction_pdf_and_image(tmp_path, monkeypatch, src, vendor_hint):
    ex = _live(tmp_path, monkeypatch, src, f"live_{Path(src).stem}{Path(src).suffix}")
    assert ex.vendor
    if vendor_hint:
        assert vendor_hint in ex.vendor.lower()
    assert str(ex.suggested_account).isdigit() and len(str(ex.suggested_account)) == 4
    assert not ex.injection_suspected


def test_live_extraction_flags_injection(tmp_path, monkeypatch):
    ex = _live(tmp_path, monkeypatch, "faktura_nordic_growth_partners_7781.pdf", "live_ngp.pdf")
    assert ex.injection_suspected
