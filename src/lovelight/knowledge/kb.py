"""Vendor/activity knowledge base: curated YAML data, validated on load, retrieved by whole-token matching."""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal
from functools import cache
from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError
from rapidfuzz import fuzz

from lovelight.models import VAT_RATES, Correction, KBMatch

DEFAULT_DIR = Path(__file__).resolve().parent
LEGAL_SUFFIXES = {
    "ab", "aktiebolag", "publ", "hb", "kb", "inc", "incorporated", "ltd", "limited", "llc", "gmbh", "ag", "as",
    "aps", "oy", "ou", "bv", "nv", "sa", "sarl", "srl", "plc", "corp", "corporation",
}
SCORES = {"org_nr": 1.0, "email_domain": 0.95, "alias": 0.9, "bank_pattern": 0.85}
SAME_VENDOR_MIN = 80  # rapidfuzz token_set_ratio on normalized names


def normalize(text: str) -> str:
    """Lowercase, strip accents and punctuation, drop legal-form suffixes: 'Nordic Mobility AB' -> 'nordic mobility'."""
    s = unicodedata.normalize("NFKD", text.lower())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace("a/s", " as ")
    s = re.sub(r"\b([a-z])\.", r"\1", s)  # "b.v." -> "bv"
    tokens = re.sub(r"[^a-z0-9]+", " ", s).split()
    return " ".join(t for t in tokens if t not in LEGAL_SUFFIXES)


def _contains(haystack: str, needle: str) -> bool:
    """Whole-token containment: 'nord' is in 'nord bygg' but not in 'nordic'."""
    return bool(needle) and f" {needle} " in f" {haystack} "


def _digits(s: str | None) -> str:
    return re.sub(r"\D", "", s or "")


def same_vendor(a: str, b: str) -> bool:
    na, nb = normalize(a), normalize(b)
    return bool(na and nb) and fuzz.token_set_ratio(na, nb) >= SAME_VENDOR_MIN


class VendorEntry(BaseModel):
    id: str
    name: str
    aliases: list[str] = []
    bank_patterns: list[str] = []
    email_domains: list[str] = []
    org_nr: str | None = None
    vendor_profile: str
    activity: str
    vat_rates: list[Decimal] = []
    country: str | None = None  # ISO 3166 alpha-2 of the selling entity; decides EU vs non-EU reverse charge
    notes: str | None = None


class Activity(BaseModel):
    id: str
    label: str
    accounts: list[str]  # first = default
    vat_rates: list[Decimal]
    description: str
    examples: list[str] = []
    vat_note: str | None = None
    requires_review: bool = False  # never auto-post: the booking needs facts the document lacks (e.g. headcount)
    reverse_charge_when_zero: bool = False  # 0 % invoice from abroad: buyer self-assesses 25 % VAT


class KnowledgeBase(BaseModel):
    version: str
    vendors: list[VendorEntry]
    activities: dict[str, Activity]
    accounts: dict[str, str]  # BAS code -> English name
    account_types: dict[str, str] = {}  # BAS code -> cost | control | revenue | equity | financial
    vat_deductible: dict[str, Decimal] = {}  # BAS code -> reclaimable share of input VAT (absent = 1)

    def account_type(self, account: str) -> str | None:
        if account not in self.accounts:
            return None
        return self.account_types.get(account, self.account_types.get("default", "cost"))

    def is_cost(self, account: str | None) -> bool:
        return bool(account) and self.account_type(account) == "cost"

    def input_vat_deductible(self, account: str | None) -> Decimal:
        return self.vat_deductible.get(account or "", Decimal("1"))

    def _match(self, v: VendorEntry, on: str, value: str, score: float | None = None) -> KBMatch:
        return KBMatch(
            entry_id=v.id, vendor_name=v.name, activity=v.activity, vendor_profile=v.vendor_profile,
            matched_on=on, matched_value=value, score=score if score is not None else SCORES[on], vat_rates=v.vat_rates,
        )

    def lookup(
        self, vendor: str | None = None, bank_text: str | None = None, email: str | None = None, org_nr: str | None = None
    ) -> KBMatch | None:
        """Best single entry for a document. Priority: org_nr > email_domain > alias > bank_pattern."""
        if org := _digits(org_nr):
            for v in self.vendors:
                if v.org_nr and _digits(v.org_nr) == org:
                    return self._match(v, "org_nr", org_nr)
        if email and "@" in email:
            domain = email.rsplit("@", 1)[1].strip().strip(">").lower()
            for v in self.vendors:
                if any(domain == d or domain.endswith("." + d) for d in v.email_domains):
                    return self._match(v, "email_domain", email)
        if vendor and (name := normalize(vendor)):
            best: tuple[int, VendorEntry, str] | None = None
            for v in self.vendors:
                for alias in v.aliases:
                    a = normalize(alias)
                    if _contains(name, a) and (best is None or len(a) > best[0]):
                        best = (len(a), v, alias)
            if best:
                _, v, _alias = best
                exact = normalize(v.name) == name or any(normalize(a) == name for a in v.aliases)
                return self._match(v, "alias", vendor, 1.0 if exact else SCORES["alias"])
        if bank_text and (text := normalize(bank_text)):
            for v in self.vendors:
                if any(_contains(text, normalize(p)) for p in v.bank_patterns):
                    return self._match(v, "bank_pattern", bank_text)
        return None

    def retrieve(self, text: str, k: int = 5) -> list[KBMatch]:
        """Entries mentioned anywhere in raw document text (alias, bank pattern, email domain or org nr)."""
        norm, low, digits = normalize(text), text.lower(), set(re.findall(r"\d{6}-?\d{4}", text))
        hits: list[KBMatch] = []
        for v in self.vendors:
            m = None
            if v.org_nr and any(_digits(d) == _digits(v.org_nr) for d in digits):
                m = self._match(v, "org_nr", v.org_nr)
            elif dom := next((d for d in v.email_domains if re.search(rf"[@./]{re.escape(d)}\b", low)), None):
                m = self._match(v, "email_domain", dom)
            elif alias := next((a for a in v.aliases if _contains(norm, normalize(a))), None):
                m = self._match(v, "alias", alias)
            elif pat := next((p for p in v.bank_patterns if _contains(norm, normalize(p))), None):
                m = self._match(v, "bank_pattern", pat)
            if m:
                hits.append(m)
        return sorted(hits, key=lambda m: (-m.score, m.entry_id))[:k]

    def default_account(self, activity: str) -> str | None:
        a = self.activities.get(activity)
        return a.accounts[0] if a else None


def _read(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a mapping")
    return data


def load(path: Path | None = None) -> KnowledgeBase:
    """Load and validate the KB from a directory with vendors/activities/accounts.yaml. Cached for the default dir."""
    return _load_cached(DEFAULT_DIR) if path is None or Path(path) == DEFAULT_DIR else _load(Path(path))


@cache
def _load_cached(path: Path) -> KnowledgeBase:
    return _load(path)


def _load(path: Path) -> KnowledgeBase:
    vendors, activities, accounts = (_read(path / f) for f in ("vendors.yaml", "activities.yaml", "accounts.yaml"))
    try:
        kb = KnowledgeBase(
            version=str(vendors.get("version", "")),
            vendors=vendors.get("vendors") or [],
            activities={k: {"id": k, **v} for k, v in (activities.get("activities") or {}).items()},
            accounts={str(k): v for k, v in (accounts.get("accounts") or {}).items()},
            account_types={str(k): v for k, v in (accounts.get("types") or {}).items()},
            vat_deductible={str(k): Decimal(str(v)) for k, v in (accounts.get("input_vat_deductible") or {}).items()},
        )
    except ValidationError as e:
        raise ValueError(f"invalid knowledge base in {path}: {e}") from e
    errors = []
    for a in kb.activities.values():
        errors += [f"activity {a.id}: unknown account {x}" for x in a.accounts if x not in kb.accounts]
        errors += [f"activity {a.id}: illegal VAT rate {r}" for r in a.vat_rates if r not in VAT_RATES]
        errors += [f"activity {a.id}: {x} is not a cost account" for x in a.accounts if x in kb.accounts and not kb.is_cost(x)]
        if not a.accounts or not a.vat_rates:
            errors.append(f"activity {a.id}: needs accounts and vat_rates")
    ids = [v.id for v in kb.vendors]
    errors += [f"input_vat_deductible {k}: must be within 0..1" for k, v in kb.vat_deductible.items() if not 0 <= v <= 1]
    errors += [f"duplicate vendor id {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
    for v in kb.vendors:
        if v.activity not in kb.activities:
            errors.append(f"vendor {v.id}: unknown activity {v.activity}")
            continue
        legal = set(kb.activities[v.activity].vat_rates)
        errors += [f"vendor {v.id}: VAT {r} outside activity {v.activity}" for r in v.vat_rates if r not in legal]
    if errors:
        raise ValueError(f"invalid knowledge base in {path}: " + "; ".join(errors))
    return kb


def propose_from_correction(
    c: Correction, kb: KnowledgeBase, current_activity: str | None = None, email: str | None = None
) -> dict:
    """Turn an accountant's correction into a proposed KB vendor entry (a human still has to accept it).

    The activity is the document's current one when it allows the corrected account, else the single activity whose
    default is that account; otherwise left open for the reviewer.
    """
    current = kb.activities.get(current_activity) if current_activity else None
    if current and c.account in current.accounts:
        activity = current.id
    else:
        defaults = [a.id for a in kb.activities.values() if a.accounts[0] == c.account]
        activity = defaults[0] if len(defaults) == 1 else None
    domain = email.rsplit("@", 1)[1].strip().strip(">").lower() if email and "@" in email else None
    return {
        "vendor": c.vendor,
        "account": c.account,
        "activity": activity,
        "aliases": [n] if (n := normalize(c.vendor)) else [],
        "org_nr": c.org_nr,
        "email_domains": [domain] if domain else [],
        "source": "correction",
        "status": "proposed",
    }


def vendor_key(vendor: str | None, kb_match: KBMatch | None = None, org_nr: str | None = None) -> str | None:
    """Identity used for correction memory and vendor history: KB entry, else org nr, else exact normalized name.

    Fuzzy name similarity is deliberately not used: a food-delivery arm and a ride-hailing arm of one brand
    share tokens but are different suppliers.
    """
    if kb_match:
        return f"kb:{kb_match.entry_id}"
    if org := _digits(org_nr):
        return f"org:{org[-10:]}"
    name = normalize(vendor or "")
    return f"name:{name}" if name else None
