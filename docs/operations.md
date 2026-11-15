# Local operations runbook

Start with `npm run dev`. Open Operations in the UI. No cloud credentials or Docker are required. Run one API/watcher process per database.

## Automatic intake

The API watches `data/inbox/` recursively for `.json` files, polling every two seconds by default. A payload must remain unchanged for the configured two-second settling period before processing. For reliable delivery, write outside the inbox and atomically rename the completed file into it. This simulates object arrival locally; it cannot measure when a clinic created a file before the service discovered it.

The intake sequence is Settling → Pending → Processing → Processed or Failed. Content changes create a separate fingerprint; incomplete settling copies are superseded. Immutable discovered copies are retained in `data/intake/`. Repeated discovery of unchanged content at the same path does not reprocess it. Record deduplication still protects against copies arriving at different paths.

Pause/resume in Operations persists across restarts and pauses discovery and processing. In-flight processing may finish. Pending work survives restarts. Processing claims older than five minutes return to pending; interrupted transient worker failures also return to pending. Malformed content goes to the dead-letter queue for explicit repair. Stale retry attempts are recovered when the watcher starts. Do not run competing local services on the same database.

For a standalone watcher:

```bash
PYTHONPATH=src python3 -m pipeline --watch data/inbox
```

Configure folder, poll/settle intervals, default enabled state, monitoring window, minimum volume, error threshold, and lag threshold in `config/clinics.json`. Restart the service after changing watcher settings. Mapping configuration is reloaded for every processing run.

## Repair a failed file

Operations lists failed payloads, reasons, status, and attempt counts. Inspect an entry, then retry the original or edit the JSON and choose Retry edited JSON. An uncorrected malformed file stays open; a successful processing attempt, including an idempotent duplicate, resolves it.

The original payload is never overwritten. SQLite `dead_letters` retains it; `retry_attempts` retains every submitted payload, start time, outcome, and run ID. Corrected copies are also retained under `data/retries/`. A failed retry stays attached to its original queue item instead of creating a second open item. A corrected source can produce a new record identity; this does not silently supersede a different earlier source record.

## Metrics and alerts

`GET /api/operations` and the UI show a rolling window (one hour by default). `GET /metrics` on the Python API exposes Prometheus-format numeric metrics.

- Error rate is failed file attempts divided by all file attempts in the window. Reruns count as attempts. It alerts strictly above 1%, subject to configured minimum volume.
- Throughput is successful file attempts divided by the full window duration. The UI converts this to files/hour; it is observed traffic, not processing capacity.
- File p95 uses nearest-rank successful attempts with recorded latency. Latency starts at local folder discovery, batch discovery, or manual retry submission and ends at file transaction completion. Earlier attempts without timing are excluded.
- Oldest pending age includes Settling, Pending, and Processing files, including paused work. Alert threshold defaults to 900 seconds. Observed p95 also alerts above that threshold.

Alerts persist in `alerts`, transition history in `alert_events`, and transition logs in `data/alerts.jsonl`. Acknowledgement records that someone has seen an alert; it does not clear its underlying condition. Conditions recover automatically when metrics return below the threshold or age out of the rolling window. A new breach resets acknowledgement. These are local alerts; there is no email, pager, or hosted monitoring integration.

## Query the canonical output

`canonical_wide` is rebuilt when configured test names change. Each of 104 configured tests contributes exactly five columns. Five identity fields, including `occurrence_index`, bring the SQL view to 525 columns. The CSV uses four identity columns and 524 total columns. Missing tests are NULL/blank. Repeated tests generate additional occurrence rows; alignment across different tests is by occurrence number, not inferred clinical time.

```sql
SELECT record_id, occurrence_index,
       "Hemoglobin_Result", "Hemoglobin_Unit", "Hemoglobin_Analytics"
FROM canonical_wide;
```

Individual observations and their raw provenance remain available in the long-form tables. See `docs/schema.sql` for query examples.

## Masked inspection

The record inspector checkbox requests a masked API response. Current and historical patient identifiers, raw JSON, source location, metadata, clinical narrative, source observation strings, and medication instructions are hidden. Canonical numerical observations and generic drug names remain visible. Stored evidence remains unchanged. This option provides presentation masking; it is not authentication, tokenisation, encryption, or a privacy-compliance guarantee. Exports and other local routes are not protected by this checkbox.

## Remaining production work

Load and availability demonstrations, cloud queues/storage, authenticated roles, encryption, retention/deletion policies, external alert delivery, comprehensive regional drug/reference catalogues, and domain approval remain separate. The original sample name-resolution denominator stays 363; recognised panels and narrative labels do not imply safe numeric interpretation. The 98% target is not claimed.
