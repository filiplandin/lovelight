# Security

Lovelight is a hackathon prototype that handles financial documents. This page says what is
**implemented** today and what is **roadmap**, so nobody mistakes one for the other.

## Threat model

| Threat | Control | Status |
|---|---|---|
| Prompt injection in a receipt or invoice ("approve this", "change the IBAN") | The model gets no tools; its output is schema-validated; the prompt treats documents as untrusted data; documents the model flags are quarantined, never posted; a deterministic regex rule independently raises an injection anomaly | Implemented |
| Model does the money maths wrong | Code recomputes net + VAT = gross and checks legal Swedish VAT rates; failed checks cap confidence and send the document to review | Implemented |
| Supplier bank-detail fraud (new bankgiro/IBAN for a known vendor) | `iban_change` anomaly (high severity) when a vendor's bankgiro/IBAN differs from earlier documents | Implemented |
| Mail from unknown senders | `SENDER_ALLOWLIST`; mail from other senders is quarantined | Implemented |
| Insider edits or deletes history | Append-only, hash-chained audit log (see Audit trail); corrections post reversal + new vouchers instead of editing | Implemented |
| Attacker with database write access rewrites the whole chain | Not prevented by the chain alone. Mitigation: publish or anchor the head hash externally (e.g. signed daily to object storage) | Roadmap |
| Unauthenticated access to the API | None today (see Auth); the Fly config is a public endpoint and must hold demo data only | Roadmap |
| Malicious HTML/SVG in an uploaded or emailed file | Originals are served with `Content-Security-Policy: sandbox; default-src 'none'`, `X-Content-Type-Options: nosniff`, text as `text/plain`, and previewed in a `sandbox` iframe | Implemented |
| Oversized uploads exhausting memory | Uploads are read in 1 MB chunks; a file above 20 MB or a request with more than 200 files gets HTTP 413 | Implemented |
| Direct edits to the vouchers table | `/api/audit/verify` checks every posted voucher balances and equals its last audited `voucher.posted` event (`ledger_ok`, `first_bad_voucher`); SIE export refuses an unbalanced ledger | Implemented |
| Third-party API writes (Light) | Connector refuses every non-GET request before any network I/O | Implemented |

## Data handling

- Documents are processed on the host running the app and stored in SQLite (`LOVELIGHT_DB`).
- Documents are sent to Anthropic for extraction **only when `ANTHROPIC_API_KEY` is set**. Without it,
  extraction replays a local gold file and no document leaves the machine.
- Real receipts in `data/incoming/` and caches in `data/cache/` are git-ignored and excluded from the
  Docker build context (`.dockerignore`). The repository ships only fictional demo data.
- Hosting plan: Fly.io region `arn` (Stockholm), keeping data in the EU.
- Retention (roadmap): Bokföringslagen requires accounting records to be kept for 7 years. Plan:
  immutable, versioned object storage with a 7-year retention lock for source documents, vouchers and
  the audit log; GDPR erasure requests are handled by restricting access, since legal retention
  overrides erasure for bookkeeping records. Not implemented.

## Secrets

- Read from environment variables only; `.env` is git-ignored, never copied into the image
  (`.dockerignore`), and every variable the code reads is documented in `.env.example`
  (enforced by `tests/test_repo_quality.py`, which also scans the repo for key patterns).
- Production: set secrets with `fly secrets set`, not in `fly.toml`.
- The Light connector authenticates with an API key over HTTPS (Basic auth, key as username) and is
  disabled when `LIGHT_API_KEY` is unset.

## Auth

- **Today there is no authentication.** Anyone who can reach the server can read the books and
  approve matches. User names on corrections (`user:<name>` in the audit log) are self-asserted.
  Run it on localhost or behind a private network only. `fly.toml` exposes a public `http_service`;
  deploy it with fictional demo data only until auth lands.
- Restarts and deploys keep the books: the server bootstraps demo state only into an empty database.
  `POST /api/demo/reset` wipes documents and vouchers (never the audit log) and is unauthenticated.
- Roadmap: OIDC sign-in (the bureau's identity provider) and role-based access control with three
  roles: **preparer** (upload, correct), **reviewer** (approve matches and postings), **partner**
  (close periods, export SIE4). Four-eyes rule: the person who prepares a correction or posting
  cannot approve it. Audit actors then come from the verified token, not the request body.

## Audit trail

- Implemented: every pipeline step (received, extracted, knowledge-base hit/miss, classified,
  posted/quarantined/review, match approved, correction) appends an event to the `audit` table.
  Each event stores `prev_hash` and `hash = sha256(prev_hash + canonical_json(event))`; extraction
  events also carry input, prompt and output hashes.
- SQLite triggers abort any `UPDATE` or `DELETE` on the audit table; `GET /api/audit/verify`
  recomputes the chain and reports the first bad sequence number.
- Limits: the triggers stop accidental or application-level tampering, not someone with raw write
  access to the database file (see Threat model).

## Uptime & backups

- Implemented: container `HEALTHCHECK`, Compose healthcheck and a Fly.io HTTP check on
  `/api/health`; CI builds the image and checks it becomes healthy as a non-root user.
- Deploys: one Fly machine (SQLite has a single writer). A rolling deploy halts when the new release
  fails its health check; rollback is manual (`fly deploy --image <previous>`). Automatic blue-green
  cut-over needs a stateless app, which comes with Postgres.
- Backups (roadmap): Litestream streaming the SQLite file to object storage (point-in-time restore)
  for the single-machine setup; Postgres with point-in-time recovery for production. Restores are tested
  by verifying the audit chain after restore.

## Responsible disclosure

Report vulnerabilities privately through GitHub: **Security → Report a vulnerability** on this
repository (private security advisory). Please do not open public issues for security reports.
