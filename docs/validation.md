# Validation results

Verified locally on 15 November 2026 with Python 3.13.3 and Node 22.10.0.

- `npm test`: 47 backend tests pass, covering standardisation, validation, configuration-only onboarding, explicit schema version selection, ambiguity rejection, duplicate suppression, file transaction rollback, replay archives/review reset, and CSV output.
- Additional operational tests cover settling and changing files, persistent pause/resume, idempotent discovery, stale processing-claim recovery after startup, failed retry followed by corrected retry with retained evidence, alert transitions/acknowledgement/recovery, lag and latency metrics, the SQL wide view, and current/historical response masking.
- Medical parser tests include blood-pressure pairs, conflicting units, source-threshold titre comparisons, explicit SpO2 context, demographic reference applicability, source-reference contradictions, medication form/instruction normalization, and formulation safeguards.
- `npm run build`: Next.js production build passes, including TypeScript and static page generation.
- HTTP checks against the production UI proxy verified watcher state, pause/resume, failed-payload inspection, corrected retry with original retained, masked current and archived outputs, and 524-column CSV download. A file placed in the real inbox processed automatically without adding duplicate records. Prometheus metrics include queue age and local p95 timing.

## Reproducible baseline

On a fresh temporary database, the five supplied JSON files yield 8 stored records, 363 original source entries, 398 output observations, and 1 duplicate suppression. Rerunning adds 0 rows and suppresses 9 record occurrences. The dictionary defines 104 canonical entries. The CSV has 4 identity columns plus 520 test columns: 524 total. The `canonical_wide` SQL view has 5 identity columns, including an occurrence index: 525 total and 19 rows for the baseline.

Source-name resolution is 336/363 (92.6%), measured before expansion. Ten source entries expand into 45 derived components. There are 172 classified outputs and 226 invalid outputs; names and safe interpretation are separate metrics. Medication statuses are 28 mapped occurrences, 32 unresolved, 2 treatment categories, and 2 not applicable. See `coverage-report.json` for the breakdown.

## Current browser verification

The production UI was checked in the in-app browser on local port 3001 (port 3000 was occupied and left untouched). Verified the approved burgundy navigation, raw 92.6% metric, additional eligible 96.0% metric, expandable exclusion list, Operations rendering, watcher pause/resume restored to Running, failed-file repair editor, and inspector masking with hidden document/source identifiers. Updated screenshots are `preview.png` and `operations-preview.png`.

Eight new regression tests cover contextual urine glucose, ambiguous labels, retained non-test rows, rejection of uploaded internal annotations, no inferred missing results/units, verified medicine forms/combinations, source reference applicability, and both coverage denominators. Fresh baseline measurement: 336/363 raw, 336/350 eligible, 13 non-test rows, 172 classified and 226 invalid outputs. Medicine statuses: 28 mapped, 32 unresolved, 2 treatment categories, 2 not applicable. The v3 raw baseline was 331/363 (91.2%).

## What these checks do not prove

No production load, privacy compliance, uptime, clinical correctness, or 98% mapping-coverage claim is made. The sample files include corrupted extractions. Configured transformations are deterministic, but medical interpretation and plausibility limits require domain validation. Local p95 starts at discovery/submission, not cloud landing. External cloud delivery and monitoring notification channels remain deployment work.
