"""Batch orchestration shared by the CLI and local API."""
import hashlib
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from . import settings
from .standardize import path, demographics, medication
from .validate import observation
from .composite import expand_test
from .quality import required_quality, source_coverage
from .store import connect
from .schema import select_profile
from .wide import ensure_wide_view
from .extraction import prepare_tests

ROOT = Path(__file__).resolve().parents[2]
DB = Path(os.environ.get('VERITAS_DB', ROOT / 'data/veritas.sqlite'))
PIPELINE_VERSION = '4.0'
log = logging.getLogger('veritas')


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def configuration(root=ROOT / 'config'):
    return {name:json.loads((Path(root) / (name+'.json')).read_text()) for name in ['clinics','tests','ranges','medicines']}


def reject_constant(value):
    raise ValueError('Non-standard JSON constant: '+value)


def build_observations(tests, fields, config, patient):
    observations = []
    for source_index, test in enumerate(tests):
        for child, provenance in expand_test(test, fields, config['tests']):
            result = observation(child, fields, config['tests'], config['ranges'], patient)
            result.update(provenance)
            result['source_index'] = source_index
            if provenance.get('expansion_error'):
                result['issues'].append(provenance['expansion_error'])
            observations.append(result)
    groups = {}
    for result in observations:
        if result['test_name_canonical']:
            groups.setdefault(result['test_name_canonical'], []).append(result)
    for group in groups.values():
        if len(group) > 1:
            values = {str(o['result_value'])+'|'+str(o['result_text']) for o in group}
            reason = 'Multiple conflicting observations; retained for review' if len(values)>1 else 'Repeated observation across source pages; retained'
            for result in group:
                result['issues'].append(reason)
    return observations


def save_observations(connection, record_id, observations):
    for index, result in enumerate(observations):
        connection.execute('''INSERT INTO observations(
            id,record_id,canonical,analytics,output_json,original_name,result_value,result_text,
            unit_canonical,unit_original,range_low,range_high,range_text,normalization_method,normalization_confidence
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
            record_id+':'+str(index), record_id, result['test_name_canonical'], result['analytics'],
            json.dumps(result), result['test_name_original'], result['result_value'],
            str(result['result_text']) if result['result_text'] is not None else None,
            result['unit_canonical'], result['unit_original'], result['range_low'], result['range_high'],
            result['range_text'], result['normalization_method'], result['normalization_confidence']))


def stored_coverage(connection):
    total = resolved = 0
    for row in connection.execute('SELECT output_json FROM records'):
        output = json.loads(row[0])
        coverage = output.get('source_coverage')
        if coverage:
            total += coverage['total']
            resolved += coverage['resolved']
        else:
            # Compatibility with first-version databases; these had one output per source entry.
            total += len(output['observations'])
            resolved += sum(o['test_name_canonical'] is not None for o in output['observations'])
    return total, resolved


def process_files(files, db=DB, config_dir=ROOT / 'config', reprocess=False, arrivals=None, arrival_basis='batch discovery'):
    config = configuration(config_dir)
    from .ai import apply_aliases
    apply_aliases(config['tests'], db)
    version = digest(config)[:12]
    run_id, started, start = str(uuid.uuid4()), now(), time.monotonic()
    summary = {'received':len(files),'processed':0,'failed':0,'duplicates':0,'records':0,'updated_records':0,'flagged':0,'resolved_tests':0,'total_tests':0}
    with connect(db) as connection:
        connection.execute('INSERT INTO runs VALUES (?,?,?,?)', (run_id, started, None, '{}'))
    for name, content in files:
        file_start=time.monotonic()
        arrived_at=(arrivals or {}).get(str(name),started)
        clinic = 'Unknown'
        count = updated = duplicates = flagged = evaluated_flagged = occurrences = missing_fields = expected_fields = 0
        try:
            data = json.loads(content, parse_constant=reject_constant)
            if not isinstance(data, dict):
                raise ValueError('Expected a JSON object')
            profile, schema_version = select_profile(data,config['clinics']['profiles'])
            metadata_raw = path(data, profile['metadata_path'], [])
            metadata = {m['key']:m.get('value') for m in metadata_raw if isinstance(m,dict) and 'key' in m} if isinstance(metadata_raw,list) else metadata_raw
            clinic = str(path(data,profile['clinic_path']) if profile.get('clinic_path') else metadata.get(profile['clinic_fallback_metadata'],'Unknown'))
            document_id = str(path(data,profile['document_id_path']) or digest(data))
            log.info(json.dumps({'event':'schema_selected','correlation_id':run_id,'source':str(name),'profile':profile['id'],'config_version':version}))
            entries = path(data, profile['records_path'])
            if not isinstance(entries, list) or not entries:
                raise ValueError('Configured records path must contain a non-empty list')
            with connect(db) as connection:
                connection.execute('BEGIN IMMEDIATE')
                for entry in entries:
                    kind, raw = path(entry,profile['type_path']), path(entry,profile['payload_path'])
                    if not isinstance(raw,dict):
                        raise ValueError('Record payload must be an object')
                    if kind not in profile['lab_types']+profile['discharge_types']:
                        raise ValueError('Unsupported record type: '+str(kind))
                    occurrences += 1
                    scope = {'clinic':clinic,'document_id':document_id,'record_type':kind}
                    identity = {k:scope[k] for k in config['clinics']['deduplication']['scope_fields']}
                    record_id = digest({'scope':identity,'payload':raw})
                    existing = connection.execute('SELECT * FROM records WHERE id=?',(record_id,)).fetchone()
                    patient_raw = path(raw,profile['patient_path'],{}) if kind in profile['lab_types'] else raw
                    patient = demographics(patient_raw,profile['patient_fields'])
                    quality = required_quality(patient, kind, profile)
                    missing_fields += quality['missing']
                    expected_fields += quality['expected']
                    if existing and (not reprocess or (existing['config_version']==version and json.loads(existing['output_json']).get('pipeline_version')==PIPELINE_VERSION)):
                        duplicates += 1
                        flagged += int(existing['flagged'])
                        continue
                    tests = path(raw,profile['tests_path'],[]) if kind in profile['lab_types'] else []
                    if not isinstance(tests,list) or any(not isinstance(test,dict) for test in tests):
                        raise ValueError('Tests must be a list of objects')
                    tests = prepare_tests(tests,profile['test_fields'],config['tests'])
                    coverage = source_coverage(tests,profile['test_fields'],config['tests'])
                    observations = build_observations(tests,profile['test_fields'],config,patient)
                    log.info(json.dumps({'event':'record_validated','correlation_id':run_id,'record_id':record_id,'source_entries':len(tests),'observations':len(observations),'invalid':sum(o['analytics']=='Invalid' for o in observations)}))
                    medications = [medication(m,profile['medication_fields'],config['medicines']) for m in path(raw,profile['medications_path'],[])]
                    issues = []
                    if quality['missing']:
                        issues.append('Missing required fields: '+', '.join(quality['missing_fields']))
                    if any(m['status']=='Unresolved' for m in medications):
                        issues.append('One or more medicines require dictionary review')
                    is_flagged = bool(issues or any(o['issues'] for o in observations))
                    ingested_at = existing['ingested_at'] if existing else started
                    output = {
                        'id':record_id,'clinic':clinic,'document_id':document_id,'record_type':kind,
                        'patient':patient,'observations':observations,'medications':medications,
                        'issues':issues,'metadata':metadata,'source_coverage':coverage,'required_quality':quality,
                        'clinical_summary':{k:v for k,v in raw.items() if k not in [profile['tests_path'],profile['medications_path'],profile['patient_path']]},
                        'config_version':version,'pipeline_version':PIPELINE_VERSION,'schema_profile':profile['id'],'schema_version':schema_version,'lineage':{'source_file':str(name),'ingested_at':ingested_at,'processed_at':now(),'trace_id':data.get('traceId'),'correlation_id':path(data,'data.correlationId'),'run_id':run_id}}
                    if existing:
                        old_review = connection.execute('SELECT * FROM reviews WHERE record_id=?',(record_id,)).fetchone()
                        connection.execute('INSERT INTO record_versions(record_id,config_version,archived_at,output_json,review_json) VALUES(?,?,?,?,?)', (record_id,existing['config_version'],now(),existing['output_json'],json.dumps(dict(old_review)) if old_review else None))
                        connection.execute('DELETE FROM observations WHERE record_id=?',(record_id,))
                        connection.execute('DELETE FROM reviews WHERE record_id=?',(record_id,))
                        connection.execute('UPDATE records SET source_file=?,config_version=?,output_json=?,flagged=? WHERE id=?',(str(name),version,json.dumps(output),int(is_flagged),record_id))
                        updated += 1
                    else:
                        connection.execute('INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?)',(record_id,clinic,document_id,kind,str(name),ingested_at,version,json.dumps(entry),json.dumps(output),int(is_flagged)))
                        count += 1
                    save_observations(connection,record_id,observations)
                    flagged += int(is_flagged)
                    evaluated_flagged += int(is_flagged)
                connection.execute('''INSERT INTO files(run_id,name,clinic,status,reason,records,duplicates,flagged,ingested_at,updated_records,record_occurrences,missing_fields,expected_fields)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''', (run_id,str(name),clinic,'Processed',None,count,duplicates,flagged,started,updated,occurrences,missing_fields,expected_fields))
            with connect(db) as telemetry:
                telemetry.execute('UPDATE files SET duration_seconds=?,latency_seconds=?,latency_basis=? WHERE run_id=? AND name=?',(time.monotonic()-file_start,max(0,(datetime.now(timezone.utc)-datetime.fromisoformat(arrived_at)).total_seconds()),arrival_basis,run_id,str(name)))
            summary['processed'] += 1
            summary['records'] += count
            summary['updated_records'] += updated
            summary['duplicates'] += duplicates
            summary['flagged'] += evaluated_flagged
            log.info(json.dumps({'event':'file_processed','correlation_id':run_id,'source':str(name),'records':count,'updated_records':updated,'duplicates':duplicates}))
        except (ValueError,TypeError,KeyError,AttributeError) as exc:
            dead = Path(db).parent / 'dead-letter'
            dead.mkdir(parents=True, exist_ok=True)
            dead_id = digest({'name':str(name),'content':content})
            (dead / (dead_id+'.json')).write_text(json.dumps({'source':str(name),'reason':str(exc),'run_id':run_id,'content':content}))
            with connect(db) as connection:
                connection.execute('INSERT INTO files(run_id,name,clinic,status,reason,records,duplicates,flagged,ingested_at) VALUES(?,?,?,?,?,?,?,?,?)',(run_id,str(name),clinic,'Failed',str(exc),0,0,0,started))
            with connect(db) as telemetry:
                stamp=now()
                telemetry.execute("INSERT INTO dead_letters(id,source,content,reason,created_at,updated_at,status,last_run_id) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET reason=excluded.reason,updated_at=excluded.updated_at,status='Open',last_run_id=excluded.last_run_id",(dead_id,str(name),content,str(exc),stamp,stamp,'Open',run_id))
                telemetry.execute('UPDATE files SET duration_seconds=?,latency_seconds=?,latency_basis=? WHERE run_id=? AND name=?',(time.monotonic()-file_start,max(0,(datetime.now(timezone.utc)-datetime.fromisoformat(arrived_at)).total_seconds()),arrival_basis,run_id,str(name)))
            summary['failed'] += 1
            log.error(json.dumps({'event':'file_failed','correlation_id':run_id,'source':str(name),'reason':str(exc)}))
    summary['duration_seconds'] = round(time.monotonic()-start,3)
    summary['error_rate'] = summary['failed']/max(summary['received'],1)
    if summary['error_rate']>0.01:
        log.warning(json.dumps({'event':'error_rate_threshold_exceeded','correlation_id':run_id,'error_rate':summary['error_rate'],'threshold':0.01}))
    with connect(db) as connection:
        ensure_wide_view(connection,config['tests'])
        summary['total_tests'], summary['resolved_tests'] = stored_coverage(connection)
        summary['observation_count'] = connection.execute('SELECT count(*) FROM observations').fetchone()[0]
        connection.execute('UPDATE runs SET finished_at=?,summary=? WHERE id=?',(now(),json.dumps(summary),run_id))
    return {'id':run_id,'started_at':started,**summary}


def read_folder(folder):
    return [(str(p),p.read_text(errors='replace')) for p in sorted(Path(folder).rglob('*.json'))]
