# Decisions

- **Persona: accounting bureau serving Fortnox/Visma SMEs.** Concentrated buyers, quantifiable pain (min/client/month), recognisable to Grant Thornton judges.
- **Feed Fortnox/Visma via SIE4, don't replace them.** Removes switching cost; the moat is ingestion + judgment, not the ledger UI.
- **LLM proposes, deterministic code posts.** Balanced-by-construction vouchers, VAT ∈ {25,12,6,0}, net+VAT=gross. Trust is the product for AI-native finance.
- **Claude-native PDF/vision extraction, no Docling.** One call handles PDFs, photos, HTML emails; one fewer dependency.
- **Email is untrusted input.** No tools for the model, sender allowlist, injection → quarantine, never auto-post.
- **Append-only ledger.** Corrections = reversal vouchers.
- **Local FastAPI + SQLite + SSE (not Supabase).** 1h left at build start; zero-setup, no tunnel, live updates via SSE. Prod: EU-hosted Postgres.
- **Synthetic bank CSV, not open banking.** Matching intelligence is the moat; Tink is a connector.
- **Out of scope (roadmap):** period close, accruals, VAT return filing, FX revaluation, live bank feed.
- **Public portfolio repo, MIT.** Verification layer = `tests/test_repo_quality.py` (secret/path scan, env docs, README paths, lint, JS parse) so hygiene is enforced, not remembered.
- **Ruff pinned in pyproject (E,F,I,UP,B; E501 ignored).** Overrides strict global config; long lines are prompts/fixtures where wrapping hurts. Lint-only, no reformat churn.
- **Hackathon artefacts in `docs/hackathon/`, not deleted.** Provenance for the story; out of the root.
