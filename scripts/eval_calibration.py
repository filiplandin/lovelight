"""Calibration report for lovelight.confidence: does a score of 0.9 mean "right 9 times out of 10"?

--source perturbed  gold extractions plus seeded, deterministic perturbations (arithmetic slips, wrong or
                    illegal VAT rates, impossible dates, identifier typos, silent digit misreads, model doubt).
                    Labels are known by construction. Synthetic: it measures the scorer, not the model.
--source cache      live extractions cached in data/cache/extractions.json, labelled against gold.json.

Prints reliability bins, expected calibration error (ECE), Brier score and auto-post precision.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from lovelight import classify, confidence, knowledge
from lovelight.models import VAT_RATES, DocType, Extraction, History, HistoryEntry

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "data" / "generated" / "gold.json"
CACHE = ROOT / "data" / "cache" / "extractions.json"
SEED = 20261013
RECEIVED = date(2026, 10, 13)
N_BINS = 10
C2 = Decimal("0.01")


def _with_amounts(e: Extraction, net: Decimal, rate: Decimal) -> Extraction:
    vat = (net * rate).quantize(C2)
    return e.model_copy(update={"net": net, "vat_rate": rate, "vat": vat, "gross": net + vat})


def perturbations(e: Extraction, rng: random.Random, kb) -> list[tuple[str, Extraction, bool]]:
    """(name, extraction, is_correct). Each gold document yields the clean copy plus several variants."""
    out = [("clean", e, True)]
    out.append(("model_doubt", e.model_copy(update={"confidence": round(rng.uniform(0.3, 0.8), 2)}), True))
    out.append(("arithmetic_slip", e.model_copy(update={"gross": e.gross + Decimal(rng.randint(1, 90))}), False))
    out.append(("illegal_rate", _with_amounts(e, e.net, Decimal("0.20")), False))
    act = kb.activities.get(e.activity or "")
    wrong = sorted(VAT_RATES - set(act.vat_rates)) if act else []
    if wrong:
        out.append(("rate_outside_activity", _with_amounts(e, e.net, rng.choice(wrong)), False))
    out.append(("future_date", e.model_copy(update={"date": RECEIVED + timedelta(days=rng.randint(20, 60))}), False))
    if e.vendor_org_nr:
        digits = e.vendor_org_nr[:-1] + str((int(e.vendor_org_nr[-1]) + rng.randint(1, 9)) % 10)
        out.append(("org_nr_typo", e.model_copy(update={"vendor_org_nr": digits}), False))
    # A consistent misread (e.g. 1 295 read as 1 925) passes every deterministic check: kept on purpose.
    s = str(e.net)
    if len(s.replace(".", "")) >= 4 and s[0] != s[1] and s[1] != ".":
        swapped = Decimal(s[1] + s[0] + s[2:])
        out.append(("silent_digit_swap", _with_amounts(e, swapped, e.vat_rate), False))
    return out


def _history(gold: dict, exclude: str) -> History:
    entries = []
    for name, g in gold.items():
        e = Extraction.model_validate(g["extraction"])
        if name != exclude and e.doc_type != DocType.CUSTOMER_INVOICE and not g["anomalies"]:
            entries.append(HistoryEntry(vendor=e.vendor, account=e.suggested_account, vat_rate=e.vat_rate, date=e.date))
    return History(entries=entries)


def _score(e: Extraction, history: History, kb) -> float:
    c = classify.classify(e, kb.lookup(vendor=e.vendor, org_nr=e.vendor_org_nr), history, kb=kb)
    conf = confidence.score_extraction(e, history, activity=c.activity, account=c.account,
                                       expected_vat_rates=c.expected_vat_rates, received=RECEIVED)
    return conf.score


def perturbed_samples() -> list[tuple[float, bool, str]]:
    kb, gold, rng = knowledge.load(), json.loads(GOLD.read_text()), random.Random(SEED)
    samples = []
    for name in sorted(gold):
        if gold[name]["anomalies"]:
            continue  # planted anomalies are not clean ground truth
        e = Extraction.model_validate(gold[name]["extraction"])
        history = _history(gold, name)
        samples += [(_score(x, history, kb), ok, kind) for kind, x, ok in perturbations(e, rng, kb)]
    return samples


def cache_samples() -> list[tuple[float, bool, str]]:
    if not CACHE.exists():
        sys.exit(f"no live cache at {CACHE}; run extraction with ANTHROPIC_API_KEY first")
    kb, gold = knowledge.load(), json.loads(GOLD.read_text())
    samples = []
    for entry in json.loads(CACHE.read_text()).values():
        g = gold.get(entry.get("filename", ""))
        if not g:
            continue
        e, ref = Extraction.model_validate(entry["extraction"]), Extraction.model_validate(g["extraction"])
        fields = ("doc_type", "net", "vat_rate", "vat", "gross", "date", "currency")
        ok = all(getattr(e, f) == getattr(ref, f) for f in fields)
        samples.append((_score(e, _history(gold, entry["filename"]), kb), ok, "live"))
    return samples


def report(labelled: list[tuple[float, bool, str]], source: str) -> dict:
    samples = [(s, ok) for s, ok, _ in labelled]
    n = len(samples)
    bins = []
    for i in range(N_BINS):
        lo, hi = i / N_BINS, (i + 1) / N_BINS
        inside = [(s, ok) for s, ok in samples if lo <= s < hi or (i == N_BINS - 1 and s == 1.0)]
        if inside:
            bins.append({
                "lo": lo, "hi": hi, "n": len(inside),
                "mean_confidence": round(sum(s for s, _ in inside) / len(inside), 4),
                "accuracy": round(sum(ok for _, ok in inside) / len(inside), 4),
            })
    ece = sum(b["n"] / n * abs(b["accuracy"] - b["mean_confidence"]) for b in bins)
    brier = sum((s - ok) ** 2 for s, ok in samples) / n
    auto = [ok for s, ok in samples if s >= confidence.AUTO_POST_THRESHOLD]
    return {
        "source": source, "n": n, "scoring_version": confidence.VERSION, "bins": bins,
        "ece": round(ece, 4), "brier": round(brier, 4), "threshold": confidence.AUTO_POST_THRESHOLD,
        "auto_post": {"n": len(auto), "precision": round(sum(auto) / len(auto), 4) if auto else None},
        "by_kind": {
            kind: {"n": len(xs), "correct": xs[0][1], "auto_posted": sum(s >= confidence.AUTO_POST_THRESHOLD for s, _ in xs)}
            for kind in sorted({k for *_, k in labelled})
            if (xs := [(s, ok) for s, ok, k in labelled if k == kind])
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source", choices=["perturbed", "cache"], default="perturbed")
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
    args = ap.parse_args()
    out = report(perturbed_samples(), "perturbed-gold") if args.source == "perturbed" else report(cache_samples(), "live-cache")
    if args.json:
        print(json.dumps(out, indent=1))
        return
    print(f"{out['source']}: n={out['n']}  ECE={out['ece']}  Brier={out['brier']}")
    for b in out["bins"]:
        print(f"  [{b['lo']:.1f}, {b['hi']:.1f})  n={b['n']:3d}  conf={b['mean_confidence']:.3f}  acc={b['accuracy']:.3f}")
    ap_ = out["auto_post"]
    print(f"auto-post >= {out['threshold']}: n={ap_['n']}  precision={ap_['precision']}")
    for kind, k in out["by_kind"].items():
        print(f"  {kind:<22} n={k['n']:3d}  correct={k['correct']!s:<5}  auto-posted={k['auto_posted']}")


if __name__ == "__main__":
    main()
