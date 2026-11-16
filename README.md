# Veritas

A medical-report standardisation pipeline with an operations dashboard. It ingests clinic JSON files, normalises supported test names and units, validates results, and retains source evidence for review.

**Stack:** Python, SQLite, Next.js, TypeScript, Tailwind CSS, and shadcn-style UI components.

## Run locally

Requires Node.js 20.9+ and Python 3.10+. No Docker is needed. Cloud services and API keys are optional for local processing.

```bash
git clone https://github.com/not-nag/veritas-data-engg.git
cd veritas-data-engg
npm run setup
npm run dev
```

Open [localhost:3000](http://localhost:3000) and select **Upload reports → Use sample data**. You can also upload JSON files or place them in `data/inbox/` for automatic ingestion. Ports 3000 and 8000 must be available. Stop both services with Ctrl+C.

Select **More → Help & walkthrough** for a guided tour. It highlights controls, prepares examples, and waits for your actions; progress can be paused and resumed.

## Features

- Configurable clinic schemas, test dictionaries, unit conversions, and medicine mappings.
- Duplicate suppression, result validation, review flags, and raw/transformed record inspection.
- Daily ingestion metrics, clinic quality summaries, failed-file retries, and local alerts.
- SQLite persistence, output version history, and canonical CSV export.
- Optional Gemini test-name suggestions with human approval and an audit trail.
- Generation-aware GCS ingestion and optional Firebase sign-in for write access.

## Checks

```bash
npm test
npm run build
```

The sample dataset produces 8 unique records and 398 observations. Raw name resolution is 92.6%; it is 96.0% excluding identified non-test rows. The 98% target remains unmet. Medical dictionaries are partial; production scale and clinical correctness are not established.

## Documentation

- [Cloud, Gemini and sign-in setup](docs/cloud-setup.md)
- [Architecture and drawings](docs/architecture.md)
- [Non-functional design](docs/non-functional-design.md)
- [Assumptions and limitations](docs/assumptions.md)
- [Requirement coverage](docs/coverage.md)
- [Operations and configuration](docs/operations.md)
- [Validation](docs/validation.md) · [References](docs/references.md)
