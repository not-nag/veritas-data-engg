"""Operational aggregates use a configured calendar timezone and documented rate denominators."""
import json
from collections import Counter
from datetime import date, datetime
from zoneinfo import ZoneInfo
from .engine import ROOT, configuration, digest, stored_coverage, PIPELINE_VERSION
from .store import connect


def rate(numerator, denominator):
    return round(numerator / denominator * 100, 2) if denominator else None


def dashboard(db, day=None, config_dir=ROOT/'config'):
    config = configuration(config_dir)
    version = digest(config)[:12]
    timezone = config['clinics'].get('operations', {}).get('timezone', 'UTC')
    zone = ZoneInfo(timezone)
    selected_day = date.fromisoformat(day) if day else datetime.now(zone).date()
    with connect(db) as connection:
        runs = [dict(r) for r in connection.execute('SELECT * FROM runs ORDER BY started_at DESC LIMIT 20')]
        for run in runs:
            run['summary'] = json.loads(run['summary'])
        records = []
        unresolved, kinds = Counter(), Counter()
        non_test_names = Counter()
        eligible = 0
        outdated = 0
        for row in connection.execute("SELECT r.*,coalesce(v.status,'Open') review_status FROM records r LEFT JOIN reviews v ON r.id=v.record_id ORDER BY ingested_at DESC"):
            record = dict(row)
            output = json.loads(record.pop('output_json'))
            record.pop('raw_json')
            record.update({'patient':output['patient'],'tests':len(output['observations']),'issues':sum(len(o['issues']) for o in output['observations'])+len(output['issues'])})
            records.append(record)
            outdated += int(record['config_version'] != version or output.get('pipeline_version') != PIPELINE_VERSION)
            unresolved.update(output.get('source_coverage', {}).get('unresolved_names', {}))
            kinds.update(output.get('source_coverage', {}).get('kinds', {}))
            coverage = output.get('source_coverage', {})
            non_test_names.update(coverage.get('non_test_names', {}))
            eligible += coverage.get('eligible_entries', coverage.get('total',len(output['observations'])))
        files = [dict(row) for row in connection.execute('SELECT * FROM files ORDER BY id DESC')]
        total, resolved = stored_coverage(connection)
        analytics = {row['analytics']:row['n'] for row in connection.execute('SELECT analytics,count(*) n FROM observations GROUP BY analytics')}
        clinics = [dict(row) for row in connection.execute('''SELECT clinic,count(*) files,sum(records) records,
            sum(coalesce(updated_records,0)) updated_records,sum(duplicates) duplicates,
            sum(coalesce(record_occurrences,records+duplicates)) record_occurrences,
            sum(flagged) flagged,sum(status='Failed') failed,
            sum(missing_fields) missing_fields,sum(expected_fields) expected_fields,
            sum(expected_fields IS NOT NULL) quality_evaluated_files
            FROM files GROUP BY clinic''')]
        observation_count = connection.execute('SELECT count(*) FROM observations').fetchone()[0]
    for clinic in clinics:
        clinic['duplicate_rate'] = rate(clinic['duplicates'], clinic['record_occurrences'])
        clinic['error_rate'] = rate(clinic['failed'], clinic['files'])
        clinic['missing_field_rate'] = rate(clinic['missing_fields'] or 0, clinic['expected_fields'] or 0)
    daily = {'date':selected_day.isoformat(),'timezone':timezone,'received':0,'processed':0,'failed':0,'flagged_files':0,'duplicates':0,'records':0,'updated_records':0}
    for file in files:
        day_of_file = datetime.fromisoformat(file['ingested_at']).astimezone(zone).date()
        if day_of_file != selected_day:
            continue
        daily['received'] += 1
        daily['processed'] += int(file['status']=='Processed')
        daily['failed'] += int(file['status']=='Failed')
        daily['flagged_files'] += int(file['flagged']>0)
        for field in ['duplicates','records','updated_records']:
            daily[field] += file.get(field) or 0
    return {'runs':runs,'records':records,'files':files[:100],'clinics':clinics,'analytics':analytics,
            'total_tests':total,'resolved_tests':resolved,'observation_count':observation_count,
            'coverage_kinds':dict(kinds),'unresolved_names':dict(unresolved.most_common()),
            'eligible_test_entries':eligible,'non_test_entries':sum(non_test_names.values()),'non_test_names':dict(non_test_names),
            'daily':daily,'outdated_records':outdated,
            'config':{'tests':len(config['tests']['tests']),'profiles':len(config['clinics']['profiles']),'version':version}}
