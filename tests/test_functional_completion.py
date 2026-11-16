import copy
import json
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
from pipeline.engine import ROOT,configuration,process_files,read_folder
from pipeline.store import connect
from pipeline.schema import select_profile
from pipeline.standardize import medication
from pipeline.validate import observation
from pipeline.composite import expand_test
from pipeline.operations import FolderWatcher,retry_dead_letter,evaluate_health,health,acknowledge_alert
from pipeline.privacy import masked_record


class ResultAndReferenceTests(unittest.TestCase):
    def setUp(self):
        self.c=configuration();self.fields=self.c['clinics']['profiles'][0]['test_fields']
    def obs(self,name,value,unit='',reference='',patient=None):
        return observation({'test_name':name,'result':value,'unit':unit,'range':reference},self.fields,self.c['tests'],self.c['ranges'],patient or {})
    def test_blood_pressure_pair_preserves_both_values(self):
        raw={'test_name':'BP','result':'120/80 mmHg','unit':'mmHg','range':''}
        parts=expand_test(raw,self.fields,self.c['tests'])
        self.assertEqual([x[0]['test_name'] for x in parts],['Systolic Blood Pressure','Diastolic Blood Pressure'])
        self.assertEqual([x[0]['result'] for x in parts],['120','80'])
        self.assertTrue(all(x[1]['derived_from']['result_text']=='120/80 mmHg' for x in parts))
        raw['unit']='kPa'
        self.assertIn('Conflicting',expand_test(raw,self.fields,self.c['tests'])[0][1]['expansion_error'])
    def test_titres_require_explicit_source_reference(self):
        result=self.obs('Typhi O Titre','1:40',reference='Less than 1:80')
        self.assertEqual(result['analytics'],'Within Range')
        self.assertEqual(result['result_value'],40)
        self.assertEqual(self.obs('Typhi O Titre','1:80',reference='Less than 1:80')['analytics'],'Above Range')
        self.assertEqual(self.obs('Typhi O Titre','1:40')['analytics'],'Invalid')
        self.assertEqual(self.obs('Typhi O Titre','1:0',reference='<1:80')['analytics'],'Invalid')
    def test_explicit_oxygen_context_is_retained(self):
        result=self.obs('SpO2','99% On Room Air','%','94-100')
        self.assertEqual(result['result_value'],99)
        self.assertEqual(result['result_context'],'On room air')
        self.assertEqual(result['analytics'],'Within Range')
        self.assertEqual(result['result_text'],'99% On Room Air')
    def test_population_specific_sourced_fallbacks(self):
        adult={'age_structured':{'years':30},'gender':'Female'}
        child={'age_structured':{'years':5},'gender':'Female'}
        for name,value,unit in [('Platelet Count','200000','cells/cu.mm'),('White Blood Cell Count','8000','cells/cu.mm'),('Creatinine','0.7','mg/dL'),('Red Blood Cell Count','4.5','million/cu.mm')]:
            result=self.obs(name,value,unit,patient=adult)
            self.assertEqual(result['analytics'],'Within Range',name)
            self.assertIn('medlineplus.gov',result['range_source'])
            self.assertEqual(self.obs(name,value,unit,patient=child)['analytics'],'Invalid')
            self.assertEqual(self.obs(name,value,unit)['analytics'],'Invalid')
    def test_contradictory_source_reference_not_used_as_normal(self):
        result=self.obs('Body Temperature','98.6 degree F','degree F','36.7-37.2')
        self.assertEqual(result['analytics'],'Invalid')
        self.assertTrue(any('contradiction' in issue for issue in result['issues']))
    def test_medicine_normalisation_and_combination_safety(self):
        fields={'name':'medicine','dose':'dose','frequency':'frequency'}
        for name,expected in [('TAB. CEFTAS- 400 (after food)','Cefixime'),('TAB. DOLO - 650 mg(in case of fever)','Paracetamol'),('Inj. Pantocid 40 mg','Pantoprazole'),('TAB. AZITHRAL 500 mg','Azithromycin'),('Inj. Emeset','Ondansetron'),('SYP DUPHALAC','Lactulose'),('TAB. ULTRACET','Tramadol + Paracetamol')]:
            result=medication({'medicine':name},fields,self.c['medicines'])
            self.assertEqual(result['generic'],expected,name)
            self.assertTrue(result['mapping_source'])
        for name in ['Pan','DOLO 650 PLUS','CEFTAS CV 400','mystery drug']:
            self.assertIsNone(medication({'medicine':name},fields,self.c['medicines'])['generic'],name)
        self.assertEqual(medication({'medicine':'N/A'},fields,self.c['medicines'])['status'],'Not applicable')


class SchemaTests(unittest.TestCase):
    def test_explicit_versions_and_predicates(self):
        config=configuration()['clinics']
        example=json.loads((ROOT/'examples/clinic-v2.json').read_text())
        profile,version=select_profile(example,config['profiles'])
        self.assertEqual((profile['id'],version),('clinic-v2','2.0'))
        example['schemaVersion']='3.0'
        with self.assertRaisesRegex(ValueError,'Unsupported schema version'):select_profile(example,config['profiles'])
        example['schemaVersion']='2.0'
        with self.assertRaisesRegex(ValueError,'Ambiguous'):select_profile(example,config['profiles']+[copy.deepcopy(config['profiles'][1])])
    def test_v2_ingestion_works_without_pipeline_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            db=Path(directory)/'db.sqlite'
            result=process_files([('v2.json',(ROOT/'examples/clinic-v2.json').read_text())],db)
            self.assertEqual(result['records'],1)
            with connect(db) as c:
                record=json.loads(c.execute('SELECT output_json FROM records').fetchone()[0])
            self.assertEqual(record['schema_version'],'2.0')
            self.assertEqual(len(record['observations']),3)


class OperationalTests(unittest.TestCase):
    def test_watcher_settles_and_does_not_reingest_unchanged_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);db=root/'db.sqlite';inbox=root/'inbox';inbox.mkdir()
            source=inbox/'report.json';source.write_text((ROOT/'sample-data/Sample_JSON_file1.json').read_text())
            watcher=FolderWatcher(db,folder=inbox);watcher.enabled=True
            watcher.config['settle_seconds']=600
            watcher.tick()
            with connect(db) as c:self.assertEqual(c.execute('SELECT status FROM inbox_files').fetchone()[0],'Settling')
            watcher.config['settle_seconds']=0
            watcher.tick();watcher.tick()
            with connect(db) as c:
                self.assertEqual(c.execute('SELECT count(*) FROM runs').fetchone()[0],1)
                self.assertEqual(c.execute('SELECT status FROM inbox_files').fetchone()[0],'Processed')
                self.assertEqual(c.execute('SELECT count(*) FROM records').fetchone()[0],1)
            watcher.set_enabled(False)
            self.assertFalse(FolderWatcher(db,folder=inbox).enabled)
    def test_watcher_partial_input_change_supersedes_settling_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);db=root/'db.sqlite';inbox=root/'inbox';inbox.mkdir()
            source=inbox/'report.json';source.write_text('{')
            watcher=FolderWatcher(db,folder=inbox);watcher.enabled=True;watcher.config['settle_seconds']=600
            watcher.scan()
            source.write_text((ROOT/'sample-data/Sample_JSON_file1.json').read_text())
            watcher.scan();watcher.config['settle_seconds']=0;watcher.tick()
            with connect(db) as c:
                statuses=[row[0] for row in c.execute('SELECT status FROM inbox_files')]
                self.assertEqual(sorted(statuses),['Processed','Superseded'])
                self.assertEqual(c.execute('SELECT count(*) FROM dead_letters').fetchone()[0],0)
    def test_failed_input_can_be_repaired_with_retry_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            db=Path(directory)/'db.sqlite'
            process_files([('bad.json','{')],db)
            with connect(db) as c:identifier=c.execute('SELECT id FROM dead_letters').fetchone()[0]
            self.assertEqual(retry_dead_letter(identifier,db=db)['failed'],1)
            corrected=(ROOT/'sample-data/Sample_JSON_file1.json').read_text()
            self.assertEqual(retry_dead_letter(identifier,corrected,db=db)['records'],1)
            with connect(db) as c:
                original=c.execute('SELECT * FROM dead_letters WHERE id=?',(identifier,)).fetchone()
                self.assertEqual((original['status'],original['retry_count'],original['content']),('Resolved',2,'{'))
                self.assertEqual(c.execute('SELECT count(*) FROM retry_attempts').fetchone()[0],2)
                self.assertEqual(c.execute("SELECT count(*) FROM dead_letters WHERE status='Open'").fetchone()[0],0)
    def test_watcher_recovers_stale_claim_after_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);db=root/'db.sqlite';inbox=root/'inbox';inbox.mkdir()
            source=inbox/'report.json';source.write_text((ROOT/'sample-data/Sample_JSON_file1.json').read_text())
            watcher=FolderWatcher(db,folder=inbox);watcher.enabled=True;watcher.config['settle_seconds']=0
            watcher.scan();watcher.scan()
            with connect(db) as c:
                c.execute("UPDATE inbox_files SET status='Processing',updated_at=?",((datetime.now(timezone.utc)-timedelta(minutes=6)).isoformat(),))
            watcher.process_pending()
            with connect(db) as c:
                self.assertEqual(c.execute('SELECT status FROM inbox_files').fetchone()[0],'Processed')
    def test_alerts_fire_once_acknowledge_and_recover(self):
        with tempfile.TemporaryDirectory() as directory:
            db=Path(directory)/'db.sqlite'
            process_files([('bad.json','{')],db)
            metrics,alerts=evaluate_health(db)
            self.assertEqual(metrics['error_rate'],1)
            self.assertEqual(alerts[0]['status'],'Active')
            acknowledge_alert('processing_error_rate',db)
            evaluate_health(db)
            with connect(db) as c:
                self.assertEqual(c.execute('SELECT count(*) FROM alert_events').fetchone()[0],1)
                self.assertIsNotNone(c.execute('SELECT acknowledged_at FROM alerts').fetchone()[0])
                c.execute('UPDATE files SET ingested_at=?',((datetime.now(timezone.utc)-timedelta(days=2)).isoformat(),))
            _,alerts=evaluate_health(db)
            self.assertEqual(alerts[0]['status'],'Resolved')
            with connect(db) as c:self.assertEqual(c.execute('SELECT count(*) FROM alert_events').fetchone()[0],2)
    def test_lag_and_latency_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            db=Path(directory)/'db.sqlite'
            past=(datetime.now(timezone.utc)-timedelta(seconds=1000)).isoformat()
            with connect(db) as c:
                c.execute('INSERT INTO inbox_files(id,source,seen_at,status,updated_at) VALUES(?,?,?,?,?)',('queued','x.json',past,'Pending',past))
            metrics,alerts=evaluate_health(db)
            self.assertGreater(metrics['oldest_pending_seconds'],900)
            self.assertTrue(any(a['code']=='processing_lag' and a['status']=='Active' for a in alerts))
            process_files([('sample.json',(ROOT/'sample-data/Sample_JSON_file1.json').read_text())],db)
            self.assertIsNotNone(health(db)['p95_file_latency_seconds'])
            self.assertGreater(health(db)['throughput_files_per_second'],0)


class WideViewAndPrivacyTests(unittest.TestCase):
    def test_relational_wide_view_preserves_occurrences_and_blanks(self):
        with tempfile.TemporaryDirectory() as directory:
            db=Path(directory)/'db.sqlite'
            process_files(read_folder(ROOT/'sample-data'),db)
            with connect(db) as c:
                columns=[r[1] for r in c.execute('PRAGMA table_info(canonical_wide)')]
                self.assertEqual(len(columns),5+5*len(configuration()['tests']['tests']))
                rows=c.execute('SELECT * FROM canonical_wide').fetchall()
                self.assertGreater(len(rows),8)
                discharge=next(row for row in rows if row['record_type']=='discharge_summary')
                self.assertIsNone(discharge['Haemoglobin_Result'])
                self.assertTrue(any(row['Systolic Blood Pressure_Result']==100 and row['Diastolic Blood Pressure_Result']==60 for row in rows))
                self.assertTrue(any(row['Bilirubin Total_Result']==.4 for row in rows))
    def test_masked_response_hides_raw_and_historical_identifiers(self):
        output={'patient':{'name':'Secret Name'},'document_id':'Secret ID','metadata':{'claim_no':'Secret Claim'},'clinical_summary':{'briefHistory':'Secret Name'},'lineage':{'source_file':'/private/Secret Name.json'},'observations':[{'test_name_canonical':None,'test_name_original':'Secret Name','result_text':'Secret Name','range_text':'Secret Name','unit_original':'Secret Name'}],'medications':[]}
        output['source_coverage']={'unresolved_names':{'Secret Name':1}}
        output['observations'].append({'test_name_canonical':'Haemoglobin','test_name_original':'Secret Name','result_text':'Secret Name','range_text':'Secret Name','unit_original':'Secret Name','result_value':12})
        output['medications']=[{'original':'Secret Name','normalised_name':'Secret Name','instructions':['Secret Name'],'dose':'Secret Name','frequency':'Secret Name'}]
        detail={'output':output,'raw':{'patientName':'Secret Name'},'source':'/private/Secret Name.json','versions':[{'output':output}]}
        masked=masked_record(detail)
        self.assertNotIn('Secret',json.dumps(masked))
        self.assertIn('Secret',json.dumps(detail))
