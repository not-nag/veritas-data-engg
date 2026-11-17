export type Patient = {
  name?: string;
  gender?: string;
  age_structured?: { years: number };
  report_date?: string;
};
export type Rec = {
  id: string;
  document_id: string;
  record_type: string;
  clinic: string;
  patient: Patient;
  tests: number;
  issues: number;
  flagged: number;
  review_status: string;
  source_file: string;
};
export type Interval = {
  low: number | null;
  high: number | null;
  low_inclusive: boolean;
  high_inclusive: boolean;
};
export type Obs = {
  result_interval?: Interval | null;
  range_low_inclusive?: boolean;
  range_high_inclusive?: boolean;
  value_status?: string;
  derived_from?: { test_name: string; result_text: string; rule: string };
  unit_provenance?: string;
  test_name_original: string;
  test_name_canonical: string | null;
  result_text: unknown;
  result_value: number | null;
  unit_original: string;
  unit_canonical: string | null;
  range_text: string;
  range_low: number | null;
  range_high: number | null;
  range_source: string;
  reference_policy?: string;
  reference_note?: string;
  analytics: string;
  issues: string[];
  normalization_method: string;
  normalization_confidence: number | null;
  ai_mapping?: { status: string; reason: string; model: string };
  page: number;
};
export type Run = {
  id: string;
  started_at: string;
  summary: {
    received: number;
    processed: number;
    failed: number;
    duplicates: number;
    records: number;
    flagged: number;
    updated_records?: number;
    duration_seconds: number;
  };
};
export type Data = {
  records: Rec[];
  runs: Run[];
  files: {
    id: number;
    name: string;
    status: string;
    reason: string;
    records: number;
    duplicates: number;
    clinic: string;
  }[];
  clinics: {
    clinic: string;
    files: number;
    records: number;
    duplicates: number;
    flagged: number;
    failed: number;
    record_occurrences: number;
    duplicate_rate: number | null;
    error_rate: number | null;
    missing_field_rate: number | null;
    missing_fields: number | null;
    expected_fields: number | null;
  }[];
  analytics: Record<string, number>;
  daily: {
    date: string;
    timezone: string;
    received: number;
    processed: number;
    failed: number;
    flagged_files: number;
  };
  outdated_records: number;
  observation_count: number;
  coverage_kinds: Record<string, number>;
  eligible_test_entries: number;
  non_test_entries: number;
  non_test_names: Record<string, number>;
  unresolved_names: Record<string, number>;
  total_tests: number;
  resolved_tests: number;
  config: { tests: number; profiles: number };
};
export type Detail = {
  versions: {
    config_version: string;
    archived_at: string;
    output: unknown;
    review: unknown;
  }[];
  raw: unknown;
  output: {
    id: string;
    clinic: string;
    document_id: string;
    record_type: string;
    patient: Patient;
    observations: Obs[];
    medications: {
      original: string;
      generic: string;
      dose: string;
      frequency: string;
      status: string;
      mapping_source?: string;
      ingredients?: string[];
    }[];
    issues: string[];
    config_version: string;
  };
  source: string;
  ingested_at: string;
};
