# Requirement coverage

Status reflects working local code, not the proposed cloud deployment.

| Requirement | Status | Evidence or limit |
| --- | --- | --- |
| FR-1.1 ingestion | Implemented locally | Recursive CLI, automatic settling folder watcher, durable intake queue, and UI uploads; cloud trigger documented |
| FR-1.2 duplicates | Implemented | Configurable scope plus payload hash; primary key; integration test |
| FR-1.3 flexible schemas | Implemented within mapping grammar | Config-only onboarding; version predicates, priority/specificity, ambiguity and unknown-version rejection |
| FR-2.1 names | Implemented with partial coverage | 336/363 original source entries (92.6%); same source denominator; includes named panels/findings |
| FR-2.2 five columns per test | Implemented in DB and export | SQL view and CSV generate five columns per dictionary test; repeats preserve occurrences |
| FR-2.3 numeric parsing | Implemented for supported forms | Scalars, intervals, inequalities and configured panel decomposition; ambiguous fields retained |
| FR-2.4 units | Implemented for configured units | Factors convert results and ranges; unsupported units invalid |
| FR-2.5 demographics | Implemented for supported formats | Structured age, gender aliases, ISO dates; redactions unknown |
| FR-2.6 medicines | Partial dictionary | 19 verified products; 28 sample occurrences mapped, 32 unresolved, 2 treatment categories, 2 not applicable |
| FR-3.1 range validation | Implemented with limited reference data | Open/closed and one-sided source ranges, interval certainty, unit consistency; limited demographic fallbacks |
| FR-3.2 outliers | Prototype rules | Separate outlier classification; rules need domain approval |
| FR-3.3 analytics | Implemented | Five requested labels with explanatory issues |
| FR-3.4 invalid values | Implemented | Composite/nonnumeric/unit contradictions flagged |
| FR-4.1 database | Implemented | SQLite records and queryable observation columns |
| FR-4.2 errors | Implemented | Failed-file inspector, original/edited retries, immutable original and retry audit |
| FR-4.3 audit | Implemented locally | Raw record, source file, timestamps, config hash, lineage |
| FR-5.1 dashboard | Implemented | Calendar-day received/processed/failed/flagged files with date filter; latest run and coverage |
| FR-5.2 inspector | Implemented | Search/filter, raw and transformed data |
| FR-5.3 review queue | Implemented | Flags, issues, review acknowledgement; no clinical correction |
| FR-5.4 clinic summary | Implemented locally | Counts and duplicate/error/missing-required-field rates with explicit denominators |
| NFR-1 throughput/latency/scale | Designed, not proven | Cloud queue, autoscaling workers, microbatch warehouse; no load test |
| NFR-2.1 zero-code onboarding | Implemented | New clinic profile and test demonstrated in integration test |
| NFR-2.2 one-day target | Assumption | Depends on documented schema and domain review |
| NFR-2.3 schema versions | Implemented locally | Explicit versions, metadata predicates, and rejection tests |
| NFR-3.1 fault tolerance | Implemented locally | File transaction rollback and dead-letter retention |
| NFR-3.2 idempotency | Implemented | Rerun integration test adds zero rows |
| NFR-3.3 uptime | Architecture only | No laptop availability guarantee |
| NFR-4.1 98% coverage | Not achieved | 92.6% source-name resolution; valid-result classification reported separately |
| NFR-4.2 lineage | Implemented | Source path, clinic, ingest time, source IDs and config hash |
| NFR-4.3 PII | Masked view implemented | Current/history/source text hidden on request; production controls excluded |
| NFR-5.1 monitoring | Implemented locally | Throughput, p95, error rate, queue age; durable alerts, acknowledge/recover events; external delivery excluded |
| NFR-5.2 logs | Implemented | Schema selection, record validation, file success/failure and error-rate threshold events with correlation IDs |

## Validation

`npm test` covers parsing, incompatible units, range boundaries, outliers, demographics, medicine handling, malformed-file isolation, transaction rollback, sample duplicate suppression, rerun idempotency, and config-only schema/test onboarding. `npm run build` validates the Next.js production build and TypeScript. UI and API smoke checks supplement those tests.

## Measured coverage and replay

Explicit mapping refresh archives previous outputs and review state, retains record IDs and ingestion timestamps, and resets review for recalculated records. File-level rollback also protects archives. The inspector exposes prior versions. Identical reruns do not create redundant history.

The sample baseline has 363 original entries, 336 recognised names, 398 output observations, and 172 classifications. Recognised source kinds: 245 numeric, 46 qualitative, 8 titres, 30 panels, 7 narrative findings. Twenty-seven source entries remain unmapped, including 13 identified non-test rows. Derived components never increase the name-coverage numerator or denominator.

Local operations also include persistent pause/resume, settling detection, crash recovery of stale intake claims, source retention, and alert transition history. See [operations](operations.md) for limits and metric definitions. Source reference contradictions remain invalid; supported blood-pressure pairs and source-threshold titres are handled without inventing missing clinical context.

The dashboard also exposes 336/350 eligible coverage (96.0%) after 13 named non-test rows. The full 363-row metric remains primary and visible. All uncertain rows remain eligible; exclusion details are available in the dashboard. No 98% achievement is claimed.
