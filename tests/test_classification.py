"""Acceptance for KB-aided, policy-checked classification. No network.

Contract:
- lovelight.knowledge: load(path=None) -> KnowledgeBase (pydantic-validated YAML in src/lovelight/knowledge/)
    KnowledgeBase.version, .vendors: list[VendorEntry], .activities: dict[id, Activity], .accounts: dict[code, English name]
    KnowledgeBase.lookup(vendor=None, bank_text=None, email=None, org_nr=None) -> KBMatch | None
    KnowledgeBase.retrieve(text, k=5) -> list[KBMatch]   (pre-extraction context from raw document text)
- lovelight.classify:
    choose(candidates, activity, history=None, *, vendor=None, kb=None) -> Classification
    classify(ext, kb_match=None, history=None, *, kb=None) -> Classification   (activity: KB > model)
"""

import json
import re
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import pytest

from lovelight import classify, knowledge
from lovelight.models import (
    VAT_RATES,
    AccountCandidate,
    Correction,
    DocType,
    Extraction,
    History,
)

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "lovelight"
VENDOR_WORDS = ["voi", "donkey", "uber", "bolt", "lime", "tier", "storstockholms", "kjell", "amzn", "msft"]


@pytest.fixture(scope="module")
def kb():
    return knowledge.load()


def cand(*pairs) -> list[AccountCandidate]:
    return [AccountCandidate(account=a, probability=p) for a, p in pairs]


def receipt(vendor, account, rate="0.25", activity=None, candidates=None) -> Extraction:
    net, r = D("100.00"), D(rate)
    return Extraction(
        doc_type=DocType.RECEIPT, vendor=vendor, date=date(2026, 10, 1), net=net, vat_rate=r, vat=net * r,
        gross=net * (1 + r), suggested_account=account, confidence=0.95, activity=activity,
        account_candidates=candidates or [],
    )


# ---------- knowledge base: schema and integrity ----------


def test_kb_files_are_data_and_validate(kb):
    for name in ("vendors.yaml", "activities.yaml", "accounts.yaml"):
        assert (SRC / "knowledge" / name).is_file(), name
    assert kb.version and kb.vendors and kb.activities and kb.accounts
    for v in kb.vendors:
        assert v.activity in kb.activities, f"{v.id}: unknown activity {v.activity}"
        assert v.vendor_profile.strip(), v.id
    assert len({v.id for v in kb.vendors}) == len(kb.vendors)
    for a in kb.activities.values():
        assert a.accounts and all(acct in kb.accounts for acct in a.accounts), a.id
        assert a.vat_rates and set(a.vat_rates) <= VAT_RATES, a.id
        assert a.description.strip(), a.id


def test_kb_rejects_vendor_with_unknown_activity(tmp_path):
    for name in ("activities.yaml", "accounts.yaml"):
        (tmp_path / name).write_text((SRC / "knowledge" / name).read_text())
    (tmp_path / "vendors.yaml").write_text(
        "version: test\nvendors:\n  - id: ghost\n    name: Ghost AB\n    vendor_profile: Haunts invoices.\n"
        "    activity: teleportation\n"
    )
    with pytest.raises(ValueError):
        knowledge.load(tmp_path)


def test_account_names_are_english(kb):
    assert kb.accounts["5800"] == "Travel"
    assert "ticket" in kb.accounts["5810"].lower()
    assert "car rental" in kb.accounts["5820"].lower()
    assert "software" in kb.accounts["5420"].lower()
    for code, name in kb.accounts.items():
        assert not re.search(r"[åäöÅÄÖ]", name), f"{code}: {name}"


# ---------- activity policy (BAS + Swedish VAT) ----------


@pytest.mark.parametrize(
    ("activity", "account", "rates_in", "rates_out"),
    [
        ("public_transport", "5810", {"0.06"}, {"0.25", "0.12"}),
        ("local_transport", "5800", {"0.06", "0.25"}, {"0.12"}),
        ("car_rental", "5820", {"0.25"}, set()),
        ("client_entertainment", "6072", {"0.12"}, set()),
        ("lodging", "5831", {"0.12"}, set()),
        ("software_subscription", "5420", {"0.25", "0"}, set()),
        ("rent", "5010", {"0.25"}, set()),
        ("consulting", "6550", {"0.25"}, set()),
        ("office_supplies", "6110", {"0.25"}, set()),
    ],
)
def test_activity_policy(kb, activity, account, rates_in, rates_out):
    a = kb.activities[activity]
    assert a.accounts[0] == account, f"{activity} default account"
    rates = set(a.vat_rates)
    assert {D(r) for r in rates_in} <= rates, a.vat_rates
    assert not ({D(r) for r in rates_out} & rates), a.vat_rates


def test_micromobility_and_bikes_are_local_transport_not_tickets(kb):
    lt = kb.activities["local_transport"]
    text = (lt.description + " " + " ".join(lt.examples)).lower()
    for word in ("taxi", "scooter", "bike"):
        assert word in text, word
    assert "5810" not in lt.accounts
    assert lt.vat_note, "two legal VAT rates: explain the ambiguity instead of guessing"


# ---------- KB retrieval ----------


@pytest.mark.parametrize(
    ("kwargs", "activity", "matched_on"),
    [
        ({"vendor": "Voi Technology AB"}, "local_transport", "alias"),
        ({"vendor": "Donkey Republic ApS"}, "local_transport", "alias"),
        ({"bank_text": "DONKEY REPUBLIC 2210"}, "local_transport", "bank_pattern"),
        ({"email": "noreply@uber.com"}, "local_transport", "email_domain"),
        ({"vendor": "SL (Storstockholms Lokaltrafik)"}, "public_transport", "alias"),
        ({"bank_text": "SL ACCESS"}, "public_transport", "bank_pattern"),
        ({"org_nr": "556013-0683"}, "public_transport", "org_nr"),
    ],
)
def test_kb_lookup(kb, kwargs, activity, matched_on):
    m = kb.lookup(**kwargs)
    assert m is not None, kwargs
    assert (m.activity, m.matched_on) == (activity, matched_on)
    assert 0 < m.score <= 1 and m.vendor_profile


@pytest.mark.parametrize("vendor", ["Voiceflow Inc", "Limestone Consulting AB", "Tierp Bygg AB", "Cykelpool Sthlm"])
def test_kb_lookup_has_no_false_positives_on_short_aliases(kb, vendor):
    assert kb.lookup(vendor=vendor) is None, vendor


def test_kb_retrieve_from_raw_text(kb):
    hits = kb.retrieve("Tack för resan med Voi! Elsparkcykel 12 min. Moms 25 %", k=3)
    assert hits and hits[0].activity == "local_transport"
    assert kb.retrieve("Faktura från Ateljé Nordljus AB", k=3) == []


# ---------- deterministic choice ----------


def test_policy_overrides_inconsistent_model_account_with_rationale(kb):
    c = classify.choose(cand(("5810", 0.8), ("5800", 0.2)), "local_transport", kb=kb)
    assert c.account == "5800" and c.source == "policy" and c.policy_consistent
    assert c.overridden_model_account == "5810"
    assert "5810" in c.rationale and "5800" in c.rationale
    assert c.account_name == "Travel"


def test_policy_default_when_no_candidate_fits(kb):
    c = classify.choose(cand(("6110", 0.9)), "local_transport", kb=kb)
    assert c.account == "5800" and c.source == "policy" and c.overridden_model_account == "6110"


def test_model_choice_kept_when_policy_consistent(kb):
    c = classify.choose(cand(("5420", 0.9), ("6540", 0.1)), "software_subscription", kb=kb)
    assert c.account == "5420" and c.source == "model" and c.overridden_model_account is None


def test_local_transport_flags_vat_ambiguity(kb):
    c = classify.choose(cand(("5800", 0.9)), "local_transport", kb=kb)
    assert c.vat_ambiguous and set(c.expected_vat_rates) >= {D("0.06"), D("0.25")}
    assert not classify.choose(cand(("5810", 0.9)), "public_transport", kb=kb).vat_ambiguous


def test_vendor_entry_can_narrow_activity_vat(kb):
    taxi = kb.lookup(vendor="Taxi Stockholm 15 00 00")
    assert taxi is not None and taxi.activity == "local_transport" and taxi.vat_rates == [D("0.06")]
    c = classify.classify(receipt("Taxi Stockholm 15 00 00", "5800", rate="0.06"), taxi, kb=kb)
    assert c.expected_vat_rates == [D("0.06")] and not c.vat_ambiguous
    # Voi's 25 % is verified from a real receipt; operators without a verified rate keep the activity's legal set
    voi = kb.lookup(org_nr="559160-2999")
    assert voi is not None and voi.entry_id == "voi" and voi.vat_rates == [D("0.25")]
    c = classify.classify(receipt("VOI Technology AB", "5800", rate="0.25"), voi, kb=kb)
    assert (c.account, c.expected_vat_rates, c.vat_ambiguous) == ("5800", [D("0.25")], False)
    lime = kb.lookup(vendor="Lime Scooter")
    assert lime is not None and lime.vat_rates == []
    assert classify.classify(receipt("Lime Scooter", "5800"), lime, kb=kb).vat_ambiguous


def test_corrections_memory_beats_policy_and_model(kb):
    hist = History(
        corrections=[
            Correction(vendor="Cykelpool Stockholm AB", account="5810", previous_account="6990",
                       date=date(2026, 10, 2), reason="first try", user="maja"),
            Correction(vendor="Cykelpool Stockholm AB", account="5800", previous_account="5810",
                       date=date(2026, 10, 10), reason="bike share is local transport", user="maja"),
            Correction(vendor="Taxi Kurir AB", account="6990", previous_account="5800",
                       date=date(2026, 10, 11), reason="other vendor", user="maja"),
        ]
    )
    c = classify.choose(cand(("5810", 0.9)), "public_transport", hist, vendor="Cykelpool Stockholm", kb=kb)
    assert c.account == "5800" and c.source == "correction"
    assert "learned from correction on 2026-10-10" in c.rationale
    unrelated = classify.choose(cand(("5420", 0.9)), "software_subscription", hist, vendor="Fortnox AB", kb=kb)
    assert unrelated.source != "correction"
    # similar names are not the same supplier: a correction must not leak across vendors
    near = classify.choose(cand(("5800", 0.9)), "local_transport", hist, vendor="Taxi Kurir Stockholm AB", kb=kb)
    assert near.source != "correction"


def test_non_cost_accounts_are_never_chosen(kb):
    for acct in ("1930", "2440", "2611", "2099", "3001"):
        c = classify.choose(cand((acct, 0.99)), None, kb=kb)
        assert c.account == "6990" and c.source == "fallback", acct


def test_voi_like_receipt_resolves_via_kb_to_travel(kb):
    e = receipt("Voi Technology AB", "5810", candidates=cand(("5810", 0.6), ("5800", 0.4)))
    c = classify.classify(e, kb.lookup(vendor=e.vendor), kb=kb)
    assert (c.activity, c.account) == ("local_transport", "5800")
    assert "knowledge base" in c.rationale.lower()


def test_donkey_like_receipt_resolves_via_bank_text(kb):
    e = receipt("DR Bike Rental", "6990")
    c = classify.classify(e, kb.lookup(vendor=e.vendor, bank_text="DONKEY REPUBLIC 2210"), kb=kb)
    assert (c.activity, c.account) == ("local_transport", "5800")


def test_sl_ticket_is_public_transport_tickets(kb):
    e = receipt("SL (Storstockholms Lokaltrafik)", "5800", rate="0.06")
    c = classify.classify(e, kb.lookup(vendor=e.vendor), kb=kb)
    assert (c.activity, c.account) == ("public_transport", "5810")


def test_unknown_vendor_uses_model_activity_and_policy(kb):
    e = receipt("Skuttla Mobility AB", "5810", activity="local_transport", candidates=cand(("5810", 0.7)))
    assert kb.lookup(vendor=e.vendor) is None
    c = classify.classify(e, None, kb=kb)
    assert (c.activity, c.account, c.source) == ("local_transport", "5800", "policy")


def test_unknown_vendor_without_activity_falls_back_to_model_account(kb):
    c = classify.classify(receipt("Ateljé Nordljus AB", "6110"), None, kb=kb)
    assert c.account == "6110" and c.activity is None and c.source in {"model", "fallback"}


def test_classifier_reproduces_gold_accounts(kb):
    gold = json.loads((ROOT / "data" / "generated" / "gold.json").read_text())
    scenarios = [g.get("scenario") for g in gold.values()]
    assert sum(s in {"micromobility", "bike_share"} for s in scenarios) >= 2, "add synthetic micromobility/bike receipts"
    for name, g in gold.items():
        e = Extraction.model_validate(g["extraction"])
        if e.doc_type == DocType.CUSTOMER_INVOICE:
            continue
        assert e.activity in kb.activities, f"{name}: gold needs an activity"
        c = classify.classify(e, kb.lookup(vendor=e.vendor, org_nr=e.vendor_org_nr), kb=kb)
        assert c.account == e.suggested_account, (name, c.rationale)


# ---------- no vendor logic in code ----------


def test_no_vendor_names_hard_coded_in_python():
    rx = re.compile(r"\b(" + "|".join(VENDOR_WORDS) + r")\b", re.I)
    hits = [
        f"{p.relative_to(ROOT)}:{i}: {m.group(0)}"
        for p in SRC.rglob("*.py")
        for i, line in enumerate(p.read_text().splitlines(), 1)
        if (m := rx.search(line))
    ]
    assert not hits, f"vendor names belong in src/lovelight/knowledge/*.yaml: {hits}"


def test_extraction_prompt_carries_taxonomy_and_kb_context(kb):
    from lovelight import extract

    base = extract.build_system_prompt([])
    for activity in kb.activities:
        assert activity in base, activity
    with_ctx = extract.build_system_prompt(kb.retrieve("Donkey Republic bike rental", k=1))
    assert "Donkey" in with_ctx and len(with_ctx) > len(base)
    assert extract.PROMPT_VERSION != "v1"
