"""Acceptance for explainable confidence: deterministic weighted checks, hard gates, calibration report.

Contract (lovelight.confidence):
- EXTRACTION_WEIGHTS / MATCH_WEIGHTS: dict[name, weight], each summing to 1
- AUTO_POST_THRESHOLD (pipeline auto-posts at score >= it), GATE_CAP (< AUTO_POST_THRESHOLD), VERSION
- score_extraction(ext, history=None, *, activity=None, account=None, expected_vat_rates=None, received=None)
    -> Confidence. activity/account/expected_vat_rates override ext.activity, ext.suggested_account and the
    activity's VAT set (pipeline passes the Classification's);
    received defaults to today. Not-applicable components have passed=None and are excluded;
    score = sum(w*v)/sum(w) over applicable components, then capped at GATE_CAP if a gate failed.
- score_match(doc, tx) -> Confidence with components amount, date, name, reference.
"""

import json
import subprocess
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal as D
from pathlib import Path

import pytest

from lovelight import confidence
from lovelight.models import (
    BankTx,
    DocType,
    Document,
    Extraction,
    History,
    HistoryEntry,
    Source,
)

ROOT = Path(__file__).resolve().parents[1]
EXTRACTION_COMPONENTS = {
    "arithmetic",
    "vat_rate_legal",
    "vat_activity",
    "required_fields",
    "identifier_checksum",
    "date_plausible",
    "model_self_report",
    "vendor_history",
    "classification",
}
GATES = {"arithmetic", "vat_rate_legal"}
MATCH_COMPONENTS = {"amount", "date", "name", "reference"}
RECEIVED = date(2026, 10, 13)
VALID_ORG = "556013-0683"  # Luhn-valid
INVALID_ORG = "556013-0684"


def ext(**kw) -> Extraction:
    base = dict(
        doc_type=DocType.RECEIPT, vendor="Testbolaget Nord AB", vendor_org_nr=VALID_ORG, date=date(2026, 10, 1),
        net=D("100.00"), vat_rate=D("0.25"), vat=D("25.00"), gross=D("125.00"), suggested_account="6110",
        confidence=0.97, activity="office_supplies",
    )
    return Extraction(**{**base, **kw})


def score(e: Extraction, history: History | None = None, **kw):
    return confidence.score_extraction(e, history, received=RECEIVED, **kw)


def comp(c, name):
    return next(x for x in c.components if x.name == name)


def weighted_mean(c) -> float:
    applicable = [x for x in c.components if x.passed is not None]
    return sum(x.weight * x.value for x in applicable) / sum(x.weight for x in applicable)


# ---------- extraction ----------


def test_weights_are_explicit_and_sum_to_one():
    assert set(confidence.EXTRACTION_WEIGHTS) == EXTRACTION_COMPONENTS
    assert sum(confidence.EXTRACTION_WEIGHTS.values()) == pytest.approx(1.0)
    assert set(confidence.MATCH_WEIGHTS) == MATCH_COMPONENTS
    assert sum(confidence.MATCH_WEIGHTS.values()) == pytest.approx(1.0)
    assert confidence.GATE_CAP < confidence.AUTO_POST_THRESHOLD


def test_clean_document_scores_high_with_named_evidence():
    c = score(ext())
    assert {x.name for x in c.components} == EXTRACTION_COMPONENTS
    assert c.score >= confidence.AUTO_POST_THRESHOLD
    assert c.score == pytest.approx(weighted_mean(c))
    assert c.gates == [] and c.method and c.version == confidence.VERSION
    for x in c.components:
        assert x.weight == pytest.approx(confidence.EXTRACTION_WEIGHTS[x.name])
        if x.passed is not None:
            assert x.detail, f"{x.name} needs human-readable evidence"
    assert comp(c, "vendor_history").passed is None  # no history: not applicable, not a penalty


@pytest.mark.parametrize("model_conf", [0.0, 0.5, 0.99, 1.0])
def test_failed_arithmetic_can_never_auto_post(model_conf):
    c = score(ext(gross=D("135.00"), confidence=model_conf))
    a = comp(c, "arithmetic")
    assert a.passed is False and "135" in a.detail
    assert "arithmetic" in c.gates
    assert c.score <= confidence.GATE_CAP < confidence.AUTO_POST_THRESHOLD


def test_illegal_vat_rate_is_a_gate():
    c = score(ext(vat_rate=D("0.20"), vat=D("20.00"), gross=D("120.00")))
    assert comp(c, "vat_rate_legal").passed is False
    assert "vat_rate_legal" in c.gates and c.score < confidence.AUTO_POST_THRESHOLD


def test_vat_wrong_for_activity_drops_below_auto_post():
    ticket = ext(activity="public_transport", net=D("1000.00"), vat=D("250.00"), gross=D("1250.00"))
    c = score(ticket)
    assert comp(c, "vat_activity").passed is False
    assert c.score < confidence.AUTO_POST_THRESHOLD
    ok = score(ticket.model_copy(update={"vat_rate": D("0.06"), "vat": D("60.00"), "gross": D("1060.00")}))
    assert comp(ok, "vat_activity").passed is True


@pytest.mark.parametrize(("rate", "passed"), [("0.06", True), ("0.25", True), ("0.12", False)])
def test_local_transport_accepts_the_legal_set_not_a_guess(rate, passed):
    net = D("80.00")
    e = ext(activity="local_transport", net=net, vat_rate=D(rate), vat=net * D(rate), gross=net * (1 + D(rate)))
    assert comp(score(e), "vat_activity").passed is passed


def test_vendor_specific_vat_narrows_the_activity_set():
    net = D("300.00")
    taxi_25 = ext(activity="local_transport", net=net, vat=net * D("0.25"), gross=net * D("1.25"))
    assert comp(score(taxi_25), "vat_activity").passed is True
    assert comp(score(taxi_25, expected_vat_rates=[D("0.06")]), "vat_activity").passed is False


def test_activity_override_and_unknown_activity():
    assert comp(score(ext(activity=None)), "vat_activity").passed is None
    overridden = score(ext(activity=None), activity="public_transport")
    assert comp(overridden, "vat_activity").passed is False


def test_required_fields_depend_on_document_type():
    assert comp(score(ext(vendor=" ")), "required_fields").passed is False
    inv = ext(doc_type=DocType.SUPPLIER_INVOICE, invoice_number=None, due_date=date(2026, 10, 31))
    assert comp(score(inv), "required_fields").passed is False
    assert comp(score(inv.model_copy(update={"invoice_number": "F-1001"})), "required_fields").passed is True


def test_identifier_checksums_luhn():
    assert comp(score(ext()), "identifier_checksum").passed is True
    assert comp(score(ext(vendor_org_nr=INVALID_ORG)), "identifier_checksum").passed is False
    assert comp(score(ext(vendor_org_nr=None)), "identifier_checksum").passed is None
    assert comp(score(ext(vendor_org_nr=None, bankgiro="5050-1055")), "identifier_checksum").passed is True
    assert comp(score(ext(vendor_org_nr=None, bankgiro="5050-1056")), "identifier_checksum").passed is False
    assert comp(score(ext(vendor_org_nr=None, ocr_reference="7712345678")), "identifier_checksum").passed is not None


def test_date_plausibility():
    assert comp(score(ext()), "date_plausible").passed is True
    assert comp(score(ext(date=RECEIVED + timedelta(days=30))), "date_plausible").passed is False
    bad_due = ext(doc_type=DocType.SUPPLIER_INVOICE, invoice_number="1", due_date=date(2026, 9, 1))
    assert comp(score(bad_due), "date_plausible").passed is False


def test_model_self_report_is_one_capped_component():
    assert confidence.EXTRACTION_WEIGHTS["model_self_report"] <= 0.2
    c = score(ext(confidence=0.0))
    assert comp(c, "model_self_report").value == 0.0
    assert c.score < confidence.AUTO_POST_THRESHOLD  # model doubt alone blocks auto-post...
    assert score(ext(confidence=1.0)).score >= confidence.AUTO_POST_THRESHOLD  # ...but cannot force it


def test_vendor_history_agreement():
    def hist(account):
        return History(
            entries=[
                HistoryEntry(vendor="Testbolaget Nord", account=account, vat_rate=D("0.25"), date=date(2026, 9, d))
                for d in (1, 8, 15)
            ]
        )

    assert comp(score(ext(), hist("6110")), "vendor_history").passed is True
    disagree = score(ext(), hist("5410"))
    assert comp(disagree, "vendor_history").passed is False and "5410" in comp(disagree, "vendor_history").detail
    assert comp(score(ext(), hist("5410"), account="5410"), "vendor_history").passed is True
    other = History(entries=[HistoryEntry(vendor="Helt Annat AB", account="5410", vat_rate=D("0.25"), date=RECEIVED)])
    assert comp(score(ext(), other), "vendor_history").passed is None


def test_scores_are_reproducible():
    e = ext(confidence=0.83)
    assert score(e).model_dump() == score(e).model_dump()


# ---------- matching ----------


def _doc(vendor, gross, d, ocr=None) -> Document:
    e = Extraction(
        doc_type=DocType.SUPPLIER_INVOICE, vendor=vendor, date=d, net=D(gross), vat_rate=D("0"), vat=D("0"),
        gross=D(gross), ocr_reference=ocr, invoice_number="F-1", suggested_account="6550", confidence=0.9,
    )
    return Document(id=f"d-{vendor[:4]}", source=Source.UPLOAD, filename="x.pdf", sha256="x",
                    received_at=datetime(2026, 10, 1), extraction=e)


def test_match_confidence_components_and_consistency():
    from lovelight import matching

    d = _doc("Telia Sverige AB", "499.00", date(2026, 10, 5), ocr="7712345678")
    tx = BankTx(id="t1", date=date(2026, 10, 6), amount=D("-499.00"), text="TELIA SVERIGE", reference="7712345678")
    c = confidence.score_match(d, tx)
    assert {x.name for x in c.components} == MATCH_COMPONENTS
    assert sum(x.weight for x in c.components) == pytest.approx(1.0)
    assert c.score >= 0.95
    if not c.gates:
        assert c.score == pytest.approx(weighted_mean(c))
    assert confidence.score_match(d, tx).model_dump() == c.model_dump()

    worse = confidence.score_match(d, tx.model_copy(update={"date": date(2026, 10, 14), "reference": None}))
    assert worse.score < c.score

    [m] = matching.match([d], [tx])
    assert m.confidence_detail is not None
    assert m.confidence == pytest.approx(m.confidence_detail.score)


# ---------- calibration ----------


def _run_calibration() -> dict:
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "eval_calibration.py"), "--source", "perturbed", "--json"],
        cwd=ROOT, capture_output=True, text=True, check=False, timeout=120,
    )
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_eval_calibration_reports_reliability_bins_and_ece():
    out = _run_calibration()
    assert set(out) >= {"source", "n", "bins", "ece", "brier", "threshold", "auto_post"}
    assert out["source"] == "perturbed-gold"
    gold = json.loads((ROOT / "data" / "generated" / "gold.json").read_text())
    assert out["n"] > len(gold)  # gold plus deterministic perturbations
    assert sum(b["n"] for b in out["bins"]) == out["n"]
    for b in out["bins"]:
        assert set(b) >= {"lo", "hi", "n", "mean_confidence", "accuracy"}
        assert 0 <= b["lo"] < b["hi"] <= 1
    assert 0 <= out["ece"] <= 1 and 0 <= out["brier"] <= 1
    assert out["threshold"] == confidence.AUTO_POST_THRESHOLD
    assert set(out["auto_post"]) >= {"n", "precision"}
    assert out == _run_calibration(), "calibration report must be deterministic"
