-- Inspect the live schema with: sqlite3 data/veritas.sqlite '.schema'
-- Canonical laboratory fields are queryable without JSON extraction.
SELECT r.clinic, r.document_id, r.record_type,
       o.canonical AS test_name_canonical, o.original_name AS test_name_original,
       o.result_value, o.result_text, o.unit_canonical, o.unit_original,
       o.range_low, o.range_high, o.range_text, o.analytics AS test_analytics,
       o.normalization_method, o.normalization_confidence,
       r.source_file, r.ingested_at, r.config_version
FROM observations o JOIN records r ON r.id = o.record_id;

-- Five columns per configured test; occurrence_index preserves repeats.
SELECT record_id, occurrence_index,
       "Haemoglobin_Result", "Haemoglobin_Range", "Haemoglobin_Unit", "Haemoglobin_Analytics"
FROM canonical_wide;

-- Retry evidence and alert transitions are independently inspectable.
SELECT d.id, d.source, d.status, d.retry_count, a.started_at, a.outcome, a.run_id
FROM dead_letters d LEFT JOIN retry_attempts a ON a.dead_letter_id = d.id;
SELECT code, status, message, created_at FROM alert_events ORDER BY id;
