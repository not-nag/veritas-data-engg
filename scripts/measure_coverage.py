"""Recompute sample metrics on a fresh database: PYTHONPATH=src python3 scripts/measure_coverage.py."""
import json
import tempfile
from collections import Counter
from pathlib import Path
from pipeline.engine import ROOT, configuration, process_files, read_folder
from pipeline.reporting import dashboard
from pipeline.store import connect

with tempfile.TemporaryDirectory() as folder:
    db = Path(folder) / 'baseline.sqlite'
    process_files(read_folder(ROOT / 'sample-data'), db)
    report = dashboard(db)
    with connect(db) as connection:
        outputs = [json.loads(row[0]) for row in connection.execute('SELECT output_json FROM records')]
        columns = len(connection.execute('PRAGMA table_info(canonical_wide)').fetchall())
        rows = connection.execute('SELECT count(*) FROM canonical_wide').fetchone()[0]
    observations = [o for record in outputs for o in record['observations']]
    derived = [o for o in observations if o.get('derived_from')]
    data = {
        'baseline_source_entries':report['total_tests'],
        'resolved_source_entries':report['resolved_tests'],
        'name_resolution_percent':round(100*report['resolved_tests']/report['total_tests'],1),
        'coverage_denominator':'All original source rows before expansion; includes non-test rows and damaged extractions',
        'eligible_entries':report['eligible_test_entries'], 'non_test_entries':report['non_test_entries'],
        'eligible_name_resolution_percent':round(100*report['resolved_tests']/report['eligible_test_entries'],1),
        'non_test_names':report['non_test_names'], 'resolved_kinds':report['coverage_kinds'],
        'unresolved_source_entries':report['total_tests']-report['resolved_tests'],
        'eligible_unresolved_entries':report['eligible_test_entries']-report['resolved_tests'],
        'unresolved_names':report['unresolved_names'], 'output_observations':len(observations),
        'derived_components':len(derived),
        'expanded_source_entries':len({(i,o['source_index']) for i,r in enumerate(outputs) for o in r['observations'] if o.get('derived_from')}),
        'classifications':dict(sorted(Counter(o['analytics'] for o in observations).items())),
        'medication_statuses':dict(Counter(m['status'] for r in outputs for m in r['medications'])),
        'canonical_tests':len(configuration()['tests']['tests']), 'wide_csv_columns':columns-1,
        'wide_sql_columns':columns, 'wide_rows':rows,
        'interpretation':'Raw and eligible coverage are distinct. Non-test rows remain stored and invalid. Unknown rows stay eligible. Name matching does not prove safe numerical or clinical interpretation.'
    }
    (ROOT/'docs/coverage-report.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps({k:data[k] for k in ['name_resolution_percent','eligible_name_resolution_percent','classifications','medication_statuses']},indent=2))
