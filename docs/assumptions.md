# Assumptions and scope

## Business assumptions

- This system supports data preparation and operational review. It does not decide claim eligibility, diagnose, or prescribe.
- A claim/document can contain multiple discharge and lab records. Records from different encounters must remain distinct even when patient results match.
- The local source-system field stands in for clinic ID because hospital identifiers are redacted. Production onboarding must supply a stable clinic identity.
- Zero manual intervention describes normal processing, not reliable recovery of irreconcilable source contradictions. Review flags are a deliberate output.
- Operations staff may acknowledge review without changing source evidence. Adjudication and correction approval workflows are excluded.

## Technical assumptions

- Python 3.10+ and Node 20.9+ are available; ports 8000 and 3000 are free. No Docker or cloud credentials are required.
- Python's standard library avoids backend dependency setup. Next.js is a local UI and proxy; SQLite provides transactional, inspectable persistence.
- Schema mappings use dotted dictionary paths and configured list boundaries. Arbitrary transformations and joins across unrelated arrays are outside this grammar.
- Configurations are trusted local files. Each run reloads them and hashes the complete configuration for lineage.
- A rerun is idempotent against the default clinic/document/type/payload key. Source formatting and object-key order do not change payload identity; array order does.
- Configuration changes affect new records immediately. Explicit `--reprocess` or UI refresh recalculates outdated records, archives previous output/review state, and resets review. Stable IDs and first-ingestion timestamps are retained; processor and config versions determine whether refresh is needed.
- A file is the atomic transaction boundary. A bad nested record rejects its containing file, while the batch continues.
- The local API is loopback-only with a 10 MB request limit and no authentication. Production requires a different deployment and access model.

## Data assumptions

- Five source files contain nine record occurrences, of which one discharge payload is an exact duplicate. There are 363 laboratory entries before any observation-level consolidation.
- A known test name alone is insufficient to trust a result. Unknown/incompatible units or embedded-unit conflicts make numerical classification invalid.
- Scalars, bounded intervals, and one-sided inequalities are supported. Interval classifications require the complete reported interval to lie inside, above, or below the reference; overlapping boundaries remain invalid. No midpoint is invented. Exact blood-pressure pairs are decomposed; unsupported composites remain for review. Ten configured combined source entries expand into 45 source-linked components in the sample baseline.
- Methodology text in parentheses can be removed for name lookup, but the complete original label is retained. Fuzzy matching has a high threshold and a runner-up margin; it never applies to medicines.
- Source ranges preserve inclusive/exclusive bounds and convert with the result unit, including temperature offsets. Explicit reference/result unit contradictions remain invalid. Malformed nonempty source ranges never silently fall back to another range. Source ranges remain unverified clinical evidence.
- MedlinePlus provides limited fallback values. Adult-only fallbacks require explicit adult age; hemoglobin, RBC, and creatinine additionally require recognised gender. Applicable fallback units and primary sources are configured. No gender is inferred from clinical narrative.
- Demonstration plausibility limits exist to distinguish extreme data values from ordinary range deviations. They require medical-domain review before production use.
- Missing/redacted demographics remain unknown. Composite ages retain years/months/days rather than converting variable calendar periods into a guessed birthday.
- Dates use day-first formats where applicable. Unparseable dates are retained in original fields and have no standard date.
- Qualitative tests have configured normal/abnormal vocabularies. `Above Range` for a positive qualitative result is an assignment-schema convention, not a numerical comparison.
- Multiple observations for the same canonical test are retained, including identical entries on different pages. Without timestamps, it is unsafe to assume which is authoritative.
- Missing tests appear as blank fields in both the wide SQL view and export. The five exported fields are canonical test name, result, range, unit, and analytics.
- Only verified medicine aliases are mapped after removing configured form prefixes, punctuation, and trailing instructions. Strength and formulation suffixes remain significant. Brand formulation and strength variants are not assumed equivalent. Regional abbreviations such as “Pan” remain unresolved.

## Scope exclusions and production prerequisites

| Exclusion | Reason and next step |
| --- | --- |
| Actual GCS/Pub/Sub/BigQuery deployment | User requested local implementation. Provision IAM, queues, workers, warehouse jobs, and retention policies separately. |
| Proven 200k/day throughput and 15-minute p95 | Needs realistic file sizes, arrival distributions, deployment, and load tests. |
| 98% mapping coverage | Measured source-name resolution is 92.6%, including named panels and narrative findings; result validity is separate. Review unresolved tests with a domain specialist; track resolution precision as well as coverage. |
| Automated correction of shifted rows | Samples show label/value conflicts. Obtain source documents or extraction coordinates and validate a correction strategy. |
| Arbitrary composite recovery | Configured named and ordered panels work. Unmapped text, duplicated labels, bad component counts, or inconsistent differential totals retain the original field. Shifted rows are not repaired. |
| Full medicine catalogue | Requires licensed or approved regional reference data and version management. |
| Automated approval of recalculations | Explicit refresh and version history work. Clinical correction approval, record supersession for changed source documents, and automatic replay approval remain excluded. |
| Full PII compliance | Optional masked responses hide current and historical identifiers, raw evidence, source labels, and free text. Raw data remains stored and other routes remain accessible locally. Production needs jurisdiction-specific review, tokenisation, encryption, access controls, deletion, and audit policies. |
| External alert delivery and cloud ingestion | Local folder watcher, persistent intake queue, and threshold alerts are implemented. Connect a production event source and monitoring notification channels separately. |
| Broad cross-document near-duplicate matching | Redacted patient IDs are unreliable. Define encounter IDs and configurable clinical identity rules first. |
| Broad completeness contracts | Required demographic-field counts and rates are implemented per clinic profile/record type. Expected test panels and longitudinal field-quality history need additional business contracts. |

## Requirement interpretation

The later code-deliverables section is treated as the desired final scope even where earlier tables call features optional. This first implementation prioritises complete ingestion-to-review flow. The supplied long-form schema and five-column-per-test requirement are reconciled with observation storage and a generated wide export. Partial capabilities and exclusions are explicit in `coverage.md`.

## Coverage and metric interpretation

The original 363 source entries remain the coverage denominator even after expansion to 398 outputs. The dictionary resolves 336 original entries; 30 are panels and 7 are narrative findings. Eight sample titres are recognised but lack interpretable source thresholds; only explicit supported source thresholds are compared. ABSENT, NEGATIVE, and numeric artefacts remain unresolved; explicit headings such as DIAGNOSTICS are tagged as non-test rows and remain in raw coverage. The fuzzy threshold has not been lowered.

Daily counts use the configured operations timezone and file-attempt date. Clinic duplicate/error rates include reruns. Missing-field rates use configured required demographic fields, treat redactions as missing, and exclude historical attempts without evaluated contracts. These definitions avoid treating unknown historical quality as a perfect score.

Watcher discovery time starts when the running local service first sees a file, not when an external clinic created it. Settle detection is a practical safeguard, not an atomic object-store guarantee; writers should finish via atomic rename. Queue claims older than five minutes can recover after a crash. One local processing service should own each database. Schema versions are explicit and unknown/ambiguous profiles fail safely. Masked mode is not a compliance claim or permission boundary.

Version 4 adds explicit contextual label rules and tags exact non-test rows without removing evidence. Raw coverage remains 336/363; eligible coverage is 336/350. Recovered names do not authorize inferred results/units. Adult differential fallbacks require known adult age; explicitly all-age laboratory reference examples may apply with unknown age. Manufacturer/regulator evidence now supports PAN variants and injectable Fortwin; incomplete names require configured source-form evidence.
