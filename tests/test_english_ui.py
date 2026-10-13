"""Static UI gate: English copy (ledger stays SEK/BAS) and the UI consumes the trust/KB contract."""

import re
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[1] / "src" / "lovelight" / "static"
UI_FILES = ["index.html", "app.js", "tour.js", "mock.js"]
SWEDISH_UI = {
    "Att betala": r"att betala",
    "Summa": r"\bsumma\b",
    "Resultat": r"resultat",
    "Underlag": r"underlag",
    "Kundfordringar": r"kundfordringar",
    "öre": r"\böre\b",
    "Momspliktig": r"momspliktig",
    "Balansräkning": r"balansräkning",
    "Leverantörsskulder": r"leverantörsskulder",
    "Ingående moms": r"ingående moms",
    "Utgående moms": r"utgående moms",
}


@pytest.mark.parametrize("name", UI_FILES)
def test_no_swedish_ui_words(name):
    text = (STATIC / name).read_text()
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        hits += [f"{name}:{i}: {word}" for word, rx in SWEDISH_UI.items() if re.search(rx, line, re.I)]
    assert not hits, hits


def _account_map() -> dict[str, str]:
    js = (STATIC / "app.js").read_text()
    block = re.search(r"const ACCOUNTS = \{(.*?)\};", js, re.S)
    assert block, "app.js must define const ACCOUNTS = {...}"
    return dict(re.findall(r'"(\d{4})":\s*"([^"]*)"', block.group(1)))


def test_account_names_are_english():
    names = _account_map()
    assert names["5800"] == "Travel"
    assert "ticket" in names["5810"].lower()
    assert "bank" in names["1930"].lower()
    assert "receivable" in names["1510"].lower()
    assert "payable" in names["2440"].lower()
    assert "input vat" in names["2640"].lower()
    for code, name in names.items():
        assert not re.search(r"[åäöÅÄÖ]", name), f"{code}: {name}"


def test_ui_consumes_trust_and_kb_contract():
    js = (STATIC / "app.js").read_text()
    for needle in ("confidence_detail", "classification", "kb_match", "/api/audit", "/api/audit/verify", "/correct",
                   "/api/knowledge"):
        assert needle in js, f"app.js should use {needle}"
