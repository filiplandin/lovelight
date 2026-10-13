# Lovelight

**A shoebox of receipts goes in. Balanced, bank-reconciled Swedish books come out, and every number can explain itself.**

![Lovelight inbox after the demo replay: 26 documents, 77% auto-posted, 3 threats caught](docs/assets/inbox.png)

> **AI proposes, code disposes, accountant approves.** Claude reads the documents. Deterministic code does every
> krona of money math, picks the account under a written policy and decides what may post. A human signs off on
> anything the checks cannot vouch for, and every step lands in a hash-chained audit log.

Ledger currency is SEK: BAS chart of accounts, Swedish VAT, SIE4 export for Fortnox and Visma.

## The problem

Accounting bureaus spend most of their month on low-judgement work:

- **Keying documents.** Every receipt, invoice and phone photo is typed in by hand.
- **Ticking off the bank.** Bank lines are matched to documents one by one, including one payment that covers three invoices.
- **AI they can't audit.** An LLM that "does the bookkeeping" can miscount VAT, can't say why it chose an account,
  and can be steered by a malicious invoice. An auditor can't sign off on that.

## How it works (architecture)

```mermaid
flowchart LR
    U[Upload / email<br/>type sniffed from bytes] --> D[Document<br/>sha256 dedupe]
    D --> K[(Knowledge base<br/>vendors · activities · accounts<br/>YAML)]
    K -- vendor context --> X[Claude extraction<br/>no tools · schema-validated]
    D --> X
    X --> C[Classify<br/>corrections > activity policy > model]
    K -- policy prior --> C
    C --> S{Confidence<br/>named checks + gates}
    S -- "≥ 0.90, no anomaly" --> L[Deterministic ledger<br/>balanced BAS voucher]
    S -- doubt / anomaly --> R[Needs review]
    S -- injection / bad file --> Q[Quarantine]
    L --> M[Bank matching<br/>1:N payments]
    R -- accountant approves --> L
    L & R & Q & M --> A[(Hash-chained<br/>audit log)]
    L --> E[Books · VAT return · SIE4]
```

| Layer | Who | Guarantee |
| --- | --- | --- |
| Propose | Claude | Returns fields, an activity and ranked account candidates. No tools: it cannot pay, post or send. Output is parsed into a strict pydantic schema or rejected. |
| Dispose | Code | Picks the account under the activity policy, builds the voucher from BAS rules (balanced by construction, re-checked before write), restricts VAT to legal Swedish rates and re-verifies the arithmetic. |
| Guard | Code | Rule-based anomaly scan; every flag names the rule that fired. A high-severity anomaly holds the document before posting, or reverses a system-posted, unpaid voucher if it fires later. Payments are not approved while any of their documents is in review. |
| Approve | Accountant | Review queue with approve / reject / change account. The ledger is append-only: a correction is a reversal plus a new voucher. |

Trust model and threat table: [SECURITY.md](SECURITY.md). Design rationale: [DECISIONS.md](DECISIONS.md).

## How confidence is computed

![Document drawer: the 99% score broken into named checks, next to "Why this account"](docs/assets/drawer.png)

Every document gets a score from [src/lovelight/confidence.py](src/lovelight/confidence.py) (`conf-v2`). It is the
weighted mean of the checks that apply, and each check is shown in the UI with its weight, result and evidence.

| Check | Weight | Passes when |
| --- | --- | --- |
| `arithmetic` | 0.10, **gate** | net + VAT = gross (±0.01) and net × rate = VAT (±0.05) |
| `vat_rate_legal` | 0.10, **gate** | the rate is 25, 12, 6 or 0 % |
| `vat_activity` | 0.10 | the rate is in the legal set for the activity (or the vendor's narrower set) |
| `required_fields` | 0.10 | vendor, gross and (for invoices) invoice number are present |
| `identifier_checksum` | 0.10 | every Swedish org nr, bankgiro, OCR (Luhn) and IBAN (mod 97) on the document is valid |
| `date_plausible` | 0.10 | not dated after receipt; due date within 120 days |
| `model_self_report` | 0.20 | the model's own confidence (its value, not pass/fail) |
| `vendor_history` | 0.10 | the account agrees with at least half of this vendor's posted history |
| `classification` | 0.10, gate if fallback | the account fits the activity policy and is a cost account |

- **Gates.** A failed gate caps the score at 0.50, whatever the other checks say. Auto-post needs ≥ 0.90, no
  high-severity anomaly and an activity that does not always require review (client meals do).
- **The model's self-report is bounded.** It is one check worth 20 % of the weight. A model claiming 100 % cannot
  lift a document past a failed gate or failed checks; a doubtful model can still send a correct document to review
  (it does in 11 of 22 such cases in the calibration run), which costs a click, not a wrong posting.
- **Bank matches** use the same mechanism: amount 0.40, reference 0.30, name 0.20, date 0.10, with a recorded 0.95
  floor when the bank reference quotes every document and the amount is exact.

**Calibration.** [scripts/eval_calibration.py](scripts/eval_calibration.py) measures whether the score means what it
says. Latest run (13 Oct 2026):

| Source | n | ECE | Auto-post (≥ 0.90) precision |
| --- | --- | --- | --- |
| Gold extractions + seeded errors (`--source perturbed`) | 171 | 0.55 | 0.60 (33 of 55 correct) |
| Cached live Claude extractions vs gold (`--source cache`) | 23 | 0.10 | 1.00 (9 of 9) |

Read it honestly: the score is a **gate, not a probability**. On the perturbed set, 0 of 105 documents with an
error the checks can see (arithmetic slips, illegal or out-of-policy VAT, future dates, org-nr typos) auto-posted,
and all 22 clean documents did. All 22 *silent digit swaps* also auto-posted: a consistent misread passes every
check, and bank matching is the only backstop. The precision figure depends on the error mix we chose, and n = 23
for live extractions is small. Neither is a headline accuracy claim.

## Classification

Account choice is four explicit steps in [src/lovelight/classify.py](src/lovelight/classify.py), driven by a
curated, editable knowledge base stored as data in [src/lovelight/knowledge/](src/lovelight/knowledge/):

1. **Vendor profile.** The document is matched against `vendors.yaml` on org nr, email domain, whole-token alias or
   bank-text pattern. A hit gives the vendor profile and activity, and is passed to Claude as context. A miss falls
   back to the activity Claude infers. Hits and misses are audited (`kb.hit` / `kb.miss`).
2. **Activity.** `activities.yaml` says what a cost *is*, independent of who sold it: the allowed BAS accounts and
   the legal VAT rates.
3. **Policy-constrained account.** Claude's top candidate is kept only if the activity allows it; otherwise the
   policy picks the highest-ranked fitting candidate and records the overridden model account. Control, revenue and
   equity accounts are never chosen.
4. **Corrections memory.** An accountant's correction beats both policy and model for the same supplier, matched by
   knowledge-base id, then org nr, then exact name, never by fuzzy similarity. A correction can propose a new
   knowledge-base entry for review.

No vendor name appears in the classification code under `src/` (a test enforces it). Vendors live in the YAML files,
so the knowledge base is edited, reviewed and versioned like data.

**Example: an e-scooter ride books to 5800 Travel, not 5810 Tickets.** A shared e-scooter or bike-share trip is a
point-to-point local trip that replaces the metro or a bike, so it belongs with taxi and ride-hailing under
`local_transport` → **5800 Travel**. 5810 is for ticketed public transport, rail and flights; 5820 is passenger-car
hire, whose input VAT is only 50 % deductible. Operators sell scooter trips either as transport (6 %) or as vehicle
hire (25 %), so both rates are legal: the system accepts the rate printed on the receipt and flags the ambiguity
instead of guessing. In the demo, a fictional e-scooter operator that is *not* in the knowledge base still books to
5800 at 25 %, flagged ambiguous, via the model-inferred activity.

## Audit trail

![Audit trail: 585 hash-chained events, chain verified](docs/assets/audit.png)

Every state change appends an event to an append-only table:
`hash = sha256(prev_hash + canonical_json(event))`. SQLite triggers reject `UPDATE` and `DELETE` on it, and a store
reset never clears it.

- **Logged:** `doc.received`, `doc.extracted` (input, prompt and output hashes, model, knowledge-base entries used,
  cache hit), `kb.hit` / `kb.miss`, `doc.classified`, `voucher.proposed` / `posted` / `approved` / `corrected`,
  `doc.needs_review` / `quarantined` / `rejected` (with a reason code), `anomaly.found` / `resolved`,
  `match.found` / `approved`, `kb.proposed`, `books.reset`, plus retries and skipped duplicates. The actor is
  `system`, `model:<id>` or `user:<name>`.
- **Verify:**

  ```bash
  curl -s localhost:8000/api/audit/verify
  # {"ok":true,"events":585,"chain_ok":true,"ledger_ok":true,"first_bad_seq":null,"first_bad_voucher":null,...}
  ```

  `chain_ok` recomputes every hash from the first event. `ledger_ok` checks that every posted voucher balances and
  equals its last audited `voucher.posted` event, so a direct edit to the vouchers table is caught too.
- **Limit:** the chain proves the history is internally consistent, not that nobody with raw write access to the
  database rewrote all of it. Anchoring the head hash outside the database is on the roadmap.

## Verified results

Re-run on 13 Oct 2026 from a fresh database: demo replay of 26 inbox documents plus 153 Light sandbox AR invoices,
in gold-cache mode (recorded extractions, no network). These numbers measure the deterministic pipeline, not live
model accuracy. The invariants are asserted in [tests/test_acceptance.py](tests/test_acceptance.py).

| Check | Result |
| --- | --- |
| Planted inbox anomalies caught (injection, IBAN change, duplicate, VAT mismatch, missing receipt) | **5 / 5**, no other inbox anomalies |
| Prompt-injection invoice | Quarantined, **0 kr posted** |
| Planted errors in the Light AR export flagged and held from posting | **10 / 10** |
| Inbox documents auto-posted by the system (no human touch) | **20 / 26 (76.9 %)**. The rest: quarantined (1) or in review: client meals (2, VAT cap needs headcount), duplicate (1), bank-detail change (1), VAT outside the activity's rate (1) |
| Payment matched to 3 supplier invoices via OCR references | **0.95**, via the reference + amount floor |
| Matches held because a document is still in review | **5**, none posted |
| Audit chain and ledger (`/api/audit/verify`) | `chain_ok` and `ledger_ok` over **585 events, 165 posted or reversed vouchers** |
| Balance sheet (assets = equity + liabilities) | **10 833 688,50 kr = 10 833 688,50 kr** |
| Replay is idempotent (same bytes booked once) | ✓ |
| `uv run pytest tests/` | **150 passed** |

![Reconciliation: each match scored, with the checks one click away](docs/assets/recon.png)

![Books: P&L, balance sheet, VAT return boxes and SIE4 export](docs/assets/books.png)

## Connectors

| Connector | Status |
| --- | --- |
| Email (IMAP) and batch upload | Implemented. Sender allowlist; file type from bytes; one document per attachment; >20 MB, empty or unsupported files quarantined before any model call |
| SIE4 (PC8) export → Fortnox, Visma | Implemented. Refuses to export an unbalanced ledger |
| Light (light.inc), AR invoices and bank transactions | **Read-only** client in [src/lovelight/connectors/light.py](src/lovelight/connectors/light.py): refuses every non-GET before any I/O. The API contract is our assumption, tested only against a mock transport. `sync --dry-run` only |
| Fortnox and Visma APIs, Tink (PSD2 bank feed), Peppol e-invoices | Roadmap |

## Deploy and security

- **Docker:** multi-stage `uv` build, non-root user 10001, `HEALTHCHECK` on `/api/health`.
  `docker compose up --build` → <http://localhost:8000>. A CI job builds the image and checks it becomes healthy
  as the non-root user. The image has not been built and run outside CI yet.
- **Fly.io, region `arn` (Stockholm):** [fly.toml](fly.toml), one machine with a volume (SQLite has one writer),
  rolling deploys that halt on a failed health check. Rollback is manual.
- **No authentication yet.** Deploy with fictional demo data only. Details and roadmap: [SECURITY.md](SECURITY.md).

![Trust Center: quarantined prompt injection and rule-based findings](docs/assets/trust.png)

## Roadmap from hackathon MVP to production

| | Now (done) | Next | Later |
| --- | --- | --- | --- |
| **Data & ops** | SQLite, single machine, Docker, Fly `arn`, health-checked deploys | Postgres (EU) with point-in-time recovery; Litestream for the single-node setup; restore drills that re-verify the audit chain | Blue-green deploys; 7-year retention lock (Bokföringslagen) on documents, vouchers and audit log |
| **Access control** | None (localhost / demo data) | OIDC sign-in; RBAC: preparer, reviewer, partner; actors taken from the token | Four-eyes rule (preparer ≠ approver); per-client tenancy for bureaus |
| **Integrations** | SIE4 export; read-only Light client; IMAP + upload | Fortnox and Visma APIs; PSD2 bank feed (Tink) replacing bank CSV | Peppol e-invoices in and out |
| **Intelligence** | Knowledge base + activity policy; corrections memory; explainable confidence | Active learning: accountant corrections propose KB entries and become per-client examples | Calibrated probabilities on a labelled benchmark of 1 000 real receipts; per-activity thresholds |
| **Assurance** | Hash-chained audit log; `ledger_ok`; injection quarantine | Head hash anchored outside the database (signed, daily) | SOC 2 / ISAE 3402 readiness |
| **Accounting scope** | Vouchers, VAT return boxes, P&L, balance sheet, reverse charge | Period close: accruals, prepayments, FX revaluation | VAT return filing; annual accounts |

## Quickstart

You need [uv](https://docs.astral.sh/uv/) and Python 3.12. No API key is required: without one, extraction replays a
recorded gold set, so the demo runs offline and deterministically.

```bash
uv sync
cp .env.example .env                       # optional: add ANTHROPIC_API_KEY for live Claude extraction
uv run python scripts/generate_data.py     # synthetic inbox, bank.csv, gold extractions -> data/generated/
uv run uvicorn lovelight.server:app --port 8000
```

Open <http://localhost:8000/?tour=1> for the guided walkthrough, or <http://localhost:8000> and press
**Replay demo batch**. `?mock=1` runs the UI with no backend.

```bash
uv sync --group dev
uv run pytest tests/                       # unit, acceptance and repo-quality gates; live-API tests skip without a key
uv run ruff check src tests scripts
uv run python scripts/eval_calibration.py  # confidence calibration report
```

<details>
<summary>Project layout, HTTP API and configuration</summary>

```
src/lovelight/
  models.py      shared pydantic contract
  extract.py     Claude extraction → strict schema; gold-cache fallback
  knowledge/     vendors.yaml, activities.yaml, accounts.yaml + loader and retrieval (kb.py)
  classify.py    corrections > activity policy > model account choice, with rationale
  confidence.py  named checks, weights, gates (documents and bank matches)
  ledger.py      vouchers, VAT, P&L, balance sheet, VAT return (pure)
  matching.py    bank ↔ document scoring, 1:N payments
  anomalies.py   deterministic fraud / data-quality rules
  audit.py       hash-chained audit log + verification
  sie.py         SIE4 writer (PC8)
  pipeline.py    concurrent ingest, ledger lock, SSE event bus
  connectors/    read-only Light client
  server.py      FastAPI routes + static UI
  intake.py      IMAP poller + upload intake
  static/        single-page UI, guided tour, mock backend
scripts/         data generator, calibration report, demo email sender, demo recorder
tests/           unit, acceptance, live-API (opt-in), deploy, repo-quality gate
```

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/state` | Snapshot: documents, bank, matches, vouchers, anomalies, reports, integrity, stats |
| GET | `/api/events` | Server-sent events (`doc.received`, `voucher.posted`, `voucher.corrected`, `match.found`, ...) |
| GET | `/api/health` | Status, version, counts, `extraction_mode` (`live` / `gold-cache`) |
| GET | `/api/metrics` | Per-stage latency (p50/p95/max), counts, concurrency, uptime |
| POST | `/api/upload` | Multipart `files` (≤ 200 files, ≤ 20 MB each, else 413) |
| POST | `/api/demo/replay` | Replay the synthetic inbox (`?live=1` uses real Claude calls) |
| POST | `/api/demo/reset` | Clear documents and vouchers (the audit log is kept) |
| POST | `/api/matches/{id}/approve` | Approve one bank match (409 while any of its documents is unposted) |
| POST | `/api/matches/approve-all` | Approve all unblocked matches with confidence ≥ 0.95 |
| GET | `/api/export/sie4` | SIE4 download (409 if a voucher does not balance) |
| GET | `/api/documents/{id}/file` | Original document, sandboxed (CSP `sandbox`, `nosniff`, text as `text/plain`) |
| GET | `/api/documents/{id}/model-output` | Schema-validated model output as hashed into `doc.extracted` |
| POST | `/api/documents/{id}/approve` | Post the proposed voucher of a document in review |
| POST | `/api/documents/{id}/reject` | Reject a document in review or quarantine (`reason` required) |
| POST | `/api/documents/{id}/correct` | Re-book to another cost account: reversal + corrected voucher |
| GET | `/api/audit` | Hash-chained audit events (`?entity_id=` filters) |
| GET | `/api/audit/verify` | Recompute the chain and check the books against it |
| GET | `/api/knowledge` | Knowledge base, hit/miss counts, proposals from corrections |

| Variable | Effect |
| --- | --- |
| `ANTHROPIC_API_KEY` | Live Claude extraction. Unset: gold-cache mode, nothing leaves the machine |
| `GMAIL_USER`, `GMAIL_APP_PASSWORD` | Enable the IMAP inbox poller |
| `SENDER_ALLOWLIST` | Comma-separated senders allowed to auto-post |
| `LOVELIGHT_DB` | SQLite path (default `data/lovelight.db`) |
| `LOVELIGHT_MAX_CONCURRENCY` | Parallel extractions per batch (default 4) |
| `LIGHT_API_KEY`, `LIGHT_API_URL` | Enable the read-only Light connector |

</details>

## Credits

Built at the **Light x Lovable x Grant Thornton** finance hackathon in Stockholm (October 2026), then hardened into
this repo. The original brief and prompts are in [docs/hackathon/](docs/hackathon/). Licensed under [MIT](LICENSE).
