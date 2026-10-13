# Lovelight — AI bookkeeping for accounting bureaus (hackathon, 13 Oct 2026)

Shoebox (email/batch upload) → Claude extraction → deterministic double-entry ledger (BAS, Swedish VAT) → bank matching → books + SIE4 export → Trust Center (anomalies, prompt-injection quarantine, audit trail).
Principle: **AI proposes, code disposes, accountant approves.** LLM never does money math; gets no tools; output schema-validated.

## Layout (one owner per module)
- `src/lovelight/models.py` — shared contract (pydantic). Do not change field names without coordination.
- `src/lovelight/ledger.py, matching.py, anomalies.py, sie.py, extract.py` — core engine (pure, tested)
- `src/lovelight/knowledge/` — KB as data (vendors/activities/accounts YAML) + `kb.py`; vendor names only here and in tests, never in `.py` logic
- `src/lovelight/classify.py, confidence.py, audit.py` — account choice, explainable confidence (weights/gates), hash-chained audit log
- `src/lovelight/connectors/light.py` — read-only Light client (unverified contract)
- `src/lovelight/intake.py` — Gmail IMAP poller + batch upload → Document
- `src/lovelight/server.py, store.py, pipeline.py` — FastAPI + SQLite + SSE event bus
- `src/lovelight/static/` — single-page UI
- `scripts/generate_data.py` → `data/generated/` (inbox docs, bank.csv, gold.json)
- `data/invoiceReceivables.csv` — Light sandbox export: customer invoices (AR) incl. planted anomalies
- `data/incoming/` — real private receipts: git-ignored, never stage/move/print
- `docs/hackathon/` — original brief + Lovable prompts (reference only)
- `video/` — Remotion demo video (separate node project)

## HTTP contract (server ↔ UI)
- `GET /api/health` → `{status, version, docs, vouchers, extraction_mode: live|gold-cache}`; `GET /api/metrics` → `{stages, counts, concurrency, uptime_s}`
- `GET /api/state` → `{client:{name,org_nr}, documents:[Document], bank:[BankTx], matches:[Match], vouchers:[Voucher], anomalies:[Anomaly], reports:{pnl:{revenue,expenses:{acct:amt},result}, balance_sheet:{assets:{acct:amt},liabilities_equity:{acct:amt}}, vat_return:{"05","10","21","22","30","48","49"}}, integrity:{ledger_ok,first_bad_voucher}, stats:{docs_total,auto_posted_pct (system-posted only),minutes_saved (4 min/doc assumption)}}`
- `GET /api/events` SSE, `data: {type, payload}`; types: `doc.received, doc.extracted, doc.quarantined, doc.needs_review, voucher.proposed, voucher.posted, match.found, match.approved, anomaly.found, voucher.corrected, doc.rejected, state.reset`
- `POST /api/upload` (multipart `files`), `POST /api/demo/replay`, `POST /api/demo/reset`
- `POST /api/matches/{id}/approve` (409 while a document in the match is in review/unposted), `POST /api/matches/approve-all` (confidence ≥ 0.95, unblocked)
- `POST /api/documents/{id}/approve|reject|correct`, `GET /api/documents/{id}/file|model-output`
- `GET /api/export/sie4`, `GET /api/audit`, `GET /api/audit/verify` (`chain_ok`, `ledger_ok`), `GET /api/knowledge`

## Ledger conventions (BAS)
Receipt: D expense(net) + D 2640(vat) / C 1930. Supplier inv: D expense + D 2640 / C 2440; payment D 2440 / C 1930. Customer inv: D 1510 / C 3001(net) + C 2611(vat); payment D 1930 / C 1510. Non-deductible input VAT (`input_vat_deductible` in accounts.yaml: 5820 50 %, 6072 0 %) is booked onto the cost line. 0 % foreign purchase under a `reverse_charge_when_zero` activity: + D 2645 / C 2614 at 25 % (boxes 21 EU / 22 non-EU / 30). Only `type: cost` accounts may be classified or corrected to. Non-SEK amounts converted at a fixed demo rate table in ledger.py.

## Commands
- `uv sync --group dev`
- `uv run pytest tests/` (repo-quality gate included; live-API tests skip without key)
- `uv run ruff check src tests scripts` (config pinned in pyproject; CI: `.github/workflows/ci.yml`)
- `uv run python scripts/generate_data.py`
- `uv run python scripts/eval_calibration.py` (confidence calibration; `--source cache` for cached live extractions)
- `uv run uvicorn lovelight.server:app --reload --port 8000`

## Env (.env, never commit; documented in `.env.example`, a test enforces every read var is listed)
`LOVELIGHT_DB`, `LOVELIGHT_MAX_CONCURRENCY`, `ANTHROPIC_API_KEY` (missing → extraction falls back to `data/generated/gold.json`), `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `SENDER_ALLOWLIST` (comma-separated).
