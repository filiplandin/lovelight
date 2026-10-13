"""Deterministic BAS account choice: corrections > activity policy > model, every choice with a written reason."""

from __future__ import annotations

from lovelight import knowledge
from lovelight.knowledge import KnowledgeBase
from lovelight.models import AccountCandidate, Classification, Extraction, History, KBMatch


def _pct(rates) -> str:
    return "/".join(f"{r * 100:.0f} %" for r in sorted(rates, reverse=True))


def same_key(stored_key: str | None, stored_vendor: str, key: str | None, vendor: str | None) -> bool:
    """Same supplier: equal vendor keys (KB entry / org nr / exact normalized name); never fuzzy similarity."""
    if stored_key and key:
        return stored_key == key
    a, b = knowledge.normalize(stored_vendor or ""), knowledge.normalize(vendor or "")
    return bool(a) and a == b


def _latest_correction(history: History | None, vendor: str | None, key: str | None = None):
    if not history or not (vendor or key):
        return None
    hits = [c for c in history.corrections if same_key(c.vendor_key, c.vendor, key, vendor)]
    return max(hits, key=lambda c: c.date) if hits else None


def choose(
    candidates: list[AccountCandidate],
    activity: str | None,
    history: History | None = None,
    *,
    vendor: str | None = None,
    vendor_key: str | None = None,
    kb: KnowledgeBase | None = None,
) -> Classification:
    """Pick an account from the model's ranked candidates under the activity policy and correction memory."""
    kb = kb or knowledge.load()
    ranked = sorted(candidates, key=lambda c: -c.probability)
    rejected = [c.account for c in ranked if not kb.is_cost(c.account)]
    ranked = [c for c in ranked if kb.is_cost(c.account)]  # control, revenue and equity accounts never take a cost
    top = ranked[0].account if ranked else None
    act = kb.activities.get(activity) if activity else None
    allowed = act.accounts if act else []
    rates = list(act.vat_rates) if act else []

    def build(account: str, source: str, rationale: str, overridden: str | None = None) -> Classification:
        return Classification(
            account=account, account_name=kb.accounts.get(account, "Unknown account"), activity=act.id if act else None,
            source=source, rationale=rationale, policy_consistent=account in allowed,
            overridden_model_account=overridden if overridden and overridden != account else None,
            expected_vat_rates=rates, vat_ambiguous=len(rates) > 1,
        )

    def name(account: str) -> str:
        return f"{account} {kb.accounts.get(account, 'Unknown account')}"

    if (corr := _latest_correction(history, vendor, vendor_key)) and kb.is_cost(corr.account):
        return build(corr.account, "correction",
                     f"{name(corr.account)}: learned from correction on {corr.date.isoformat()} by {corr.user} "
                     f"(was {corr.previous_account}; reason: {corr.reason}).", top)

    if act:
        policy = f"activity '{act.id}' allows {', '.join(name(a) for a in allowed)}"
        if top in allowed:
            return build(top, "model", f"{name(top)}: model's top choice ({ranked[0].probability:.0%}); fits {policy}.")
        fitting = next((c.account for c in ranked if c.account in allowed), None)
        account = fitting or allowed[0]
        why = f"model's top choice {name(top)} does not fit; {policy}" if top else f"no model candidate; {policy}"
        pick = "highest-ranked fitting candidate" if fitting else "policy default"
        return build(account, "policy", f"{name(account)}: {why}. Chose the {pick}.", top)

    if top:
        return build(top, "model", f"{name(top)}: model's top choice ({ranked[0].probability:.0%}); "
                                   "activity unknown, so the policy could not check it.")
    why = f"model proposed non-cost account(s) {', '.join(rejected)}" if rejected else "no model candidate"
    return build("6990", "fallback", f"{name('6990')}: no activity and {why}; needs review.")


def classify(
    ext: Extraction,
    kb_match: KBMatch | None = None,
    history: History | None = None,
    *,
    vendor_key: str | None = None,
    kb: KnowledgeBase | None = None,
) -> Classification:
    """Classify an extraction. Activity comes from the KB match when there is one, else from the model."""
    kb = kb or knowledge.load()
    vendor_key = vendor_key or knowledge.vendor_key(ext.vendor, kb_match, ext.vendor_org_nr)
    activity = kb_match.activity if kb_match else ext.activity
    unknown_model_activity = activity is not None and activity not in kb.activities
    if unknown_model_activity:
        activity = None
    candidates = ext.account_candidates or [
        AccountCandidate(account=ext.suggested_account, probability=ext.confidence, rationale="model suggested_account")
    ]
    c = choose(candidates, activity, history, vendor=ext.vendor, vendor_key=vendor_key, kb=kb)

    notes = []
    if kb_match:
        notes.append(f"Knowledge base: '{kb_match.vendor_name}' matched on {kb_match.matched_on} "
                     f"'{kb_match.matched_value}' -> {kb_match.activity}.")
    elif ext.activity and not unknown_model_activity:
        notes.append(f"Vendor not in knowledge base; activity '{ext.activity}' inferred by the model.")
    elif unknown_model_activity:
        notes.append(f"Model activity '{ext.activity}' is not in the taxonomy; ignored.")
    rates = list(c.expected_vat_rates)
    if kb_match and kb_match.vat_rates:
        rates = list(kb_match.vat_rates)
        notes.append(f"Vendor sells at {_pct(rates)} VAT only.")
    if len(rates) > 1:
        act = kb.activities[c.activity] if c.activity else None
        notes.append(f"VAT ambiguous: {_pct(rates)} are all legal here" + (f" ({act.vat_note.strip()})" if act and act.vat_note else "."))
    return c.model_copy(update={
        "rationale": " ".join([c.rationale, *notes]),
        "expected_vat_rates": rates,
        "vat_ambiguous": len(rates) > 1,
    })
