"""SQLite persistence. A file transaction atomically commits records and run outcomes."""
import sqlite3
from pathlib import Path


class Connection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def connect(db):
    Path(db).parent.mkdir(parents=True,exist_ok=True)
    c = sqlite3.connect(db,timeout=30,factory=Connection)
    c.row_factory = sqlite3.Row
    c.executescript('''
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, started_at TEXT, finished_at TEXT, summary TEXT);
    CREATE TABLE IF NOT EXISTS files(id INTEGER PRIMARY KEY, run_id TEXT, name TEXT, clinic TEXT, status TEXT, reason TEXT, records INTEGER, duplicates INTEGER, flagged INTEGER, ingested_at TEXT);
    CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY, clinic TEXT, document_id TEXT, record_type TEXT, source_file TEXT, ingested_at TEXT, config_version TEXT, raw_json TEXT, output_json TEXT, flagged INTEGER);
    CREATE TABLE IF NOT EXISTS observations(id TEXT PRIMARY KEY, record_id TEXT, canonical TEXT, analytics TEXT, output_json TEXT);
    CREATE TABLE IF NOT EXISTS reviews(record_id TEXT PRIMARY KEY, status TEXT, updated_at TEXT);
    CREATE TABLE IF NOT EXISTS record_versions(id INTEGER PRIMARY KEY, record_id TEXT, config_version TEXT, archived_at TEXT, output_json TEXT, review_json TEXT);
    CREATE TABLE IF NOT EXISTS ai_suggestions(id TEXT PRIMARY KEY,label TEXT,canonical TEXT,reason TEXT,model TEXT,status TEXT,requested_by TEXT,created_at TEXT,reviewed_by TEXT,reviewed_at TEXT);
    CREATE TABLE IF NOT EXISTS approved_aliases(alias_key TEXT PRIMARY KEY,label TEXT,canonical TEXT,suggestion_id TEXT,reviewed_by TEXT,reviewed_at TEXT);
    CREATE TABLE IF NOT EXISTS ai_calls(id TEXT PRIMARY KEY,requested_by TEXT,created_at TEXT,status TEXT);
    CREATE TABLE IF NOT EXISTS cloud_objects(id TEXT PRIMARY KEY,bucket TEXT,name TEXT,generation TEXT,status TEXT,retained_path TEXT,run_id TEXT,error TEXT,updated_at TEXT);
    CREATE TABLE IF NOT EXISTS settings(name TEXT PRIMARY KEY,value TEXT);
    CREATE TABLE IF NOT EXISTS dead_letters(id TEXT PRIMARY KEY,source TEXT,content TEXT,reason TEXT,created_at TEXT,updated_at TEXT,status TEXT,retry_count INTEGER DEFAULT 0,last_run_id TEXT);
    CREATE TABLE IF NOT EXISTS retry_attempts(id INTEGER PRIMARY KEY,dead_letter_id TEXT,content TEXT,started_at TEXT,run_id TEXT,outcome TEXT);
    CREATE TABLE IF NOT EXISTS inbox_files(id TEXT PRIMARY KEY,source TEXT,fingerprint TEXT,seen_at TEXT,stable_since TEXT,status TEXT,retained_path TEXT,reason TEXT,run_id TEXT,updated_at TEXT);
    CREATE TABLE IF NOT EXISTS alerts(code TEXT PRIMARY KEY,status TEXT,message TEXT,opened_at TEXT,updated_at TEXT,acknowledged_at TEXT);
    CREATE TABLE IF NOT EXISTS alert_events(id INTEGER PRIMARY KEY,code TEXT,status TEXT,message TEXT,created_at TEXT);
    CREATE INDEX IF NOT EXISTS versions_record ON record_versions(record_id);
    CREATE INDEX IF NOT EXISTS records_clinic ON records(clinic);
    CREATE INDEX IF NOT EXISTS observations_record ON observations(record_id);
    ''')
    # Add queryable canonical fields when opening an earlier prototype database.
    columns = {r[1] for r in c.execute('PRAGMA table_info(observations)')}
    for name, kind in {'original_name':'TEXT','result_value':'REAL','result_text':'TEXT','unit_canonical':'TEXT','unit_original':'TEXT','range_low':'REAL','range_high':'REAL','range_text':'TEXT','normalization_method':'TEXT','normalization_confidence':'REAL'}.items():
        if name not in columns:
            c.execute(f'ALTER TABLE observations ADD COLUMN {name} {kind}')
    file_columns = {r[1] for r in c.execute('PRAGMA table_info(files)')}
    for name in ['updated_records', 'record_occurrences', 'missing_fields', 'expected_fields','duration_seconds','latency_seconds']:
        if name not in file_columns:
            c.execute(f'ALTER TABLE files ADD COLUMN {name} '+('REAL' if name.endswith('_seconds') else 'INTEGER'))
    if 'latency_basis' not in file_columns:
        c.execute('ALTER TABLE files ADD COLUMN latency_basis TEXT')
    c.commit()
    return c
