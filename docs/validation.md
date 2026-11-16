# Validation

Validated with Python 3.13.3 and Node.js 22.10.0.

| Check | Result |
| --- | --- |
| `npm test` | 52 backend tests and 7 walkthrough tests pass |
| `npm run build` | Production build and TypeScript checks pass |
| API checks | Processing, retries, masking, metrics, and export verified |
| UI checks | Direct report URLs, Back/Forward, refresh, filter restoration, local tabs, dialogs, export, masking, review, watcher controls, and failed-file repair verified |

## Test coverage

Tests cover numeric and demographic parsing, unit conversion, range boundaries, interval uncertainty, panel decomposition, medicine mapping, schema selection, configuration-only onboarding, duplicate suppression, file rollback, output history, intake recovery, retry auditing, alert transitions, and privacy masking.

Extraction tests verify that context-dependent names require explicit supporting labels, non-test rows remain in source evidence, uploaded annotations cannot override matching, and missing results or units are not invented.

Walkthrough state tests verify action gating, failure handling, completed-step deduplication, saved-progress validation, and pending-step resumption. UI checks cover the complete guided flow from an empty workspace, explicit processing and review actions, synthetic upload, failed-file repair, CSV download, pause/resume, and narrow-screen controls. The guide does not perform writes on start, step selection, or example fill.

Adult blood-pressure tests verify exclusive 120/80 upper thresholds, paired-result provenance, adult-only applicability, source-reference precedence, and rejection of malformed references or unsupported units.

## Sample baseline

The five supplied JSON files produce 8 unique records from 9 record occurrences, 363 original source rows, and 398 output observations. A repeat run inserts no records and suppresses all 9 occurrences.

| Measure | Result |
| --- | --- |
| Raw name resolution | 336/363 (92.6%) |
| Coverage excluding identified non-test rows | 336/350 (96.0%) |
| Identified non-test rows | 13; retained in raw coverage |
| Classified / invalid observations | 172 / 226 |
| Medication occurrences | 28 mapped, 32 unresolved, 2 treatment categories, 2 not applicable |
| Canonical tests | 104 |
| Wide CSV | 524 columns |
| Wide SQL view | 525 columns, 19 occurrence rows |

Reproduce the baseline on a temporary database:

```bash
PYTHONPATH=src python3 scripts/measure_coverage.py
```

Detailed results are in [coverage-report.json](coverage-report.json).

## Limits

These checks do not establish production throughput, uptime, privacy compliance, clinical correctness, or 98% mapping coverage. Local latency starts at discovery or submission. Medical reference examples and plausibility limits require domain validation.
