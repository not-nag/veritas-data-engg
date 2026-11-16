"""Behavioural regression tests for panels, boundary semantics, replay, and operations rates."""
import json
import tempfile
import unittest
from pathlib import Path
from pipeline.engine import configuration, process_files, read_folder, ROOT
from pipeline.composite import expand_test
from pipeline.validate import observation, reference_range
from pipeline.reporting import dashboard
from pipeline.store import connect
from pipeline.standardize import normalize_name, demographics
from pipeline.quality import required_quality


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.config = configuration()
        self.fields = self.config['clinics']['profiles'][0]['test_fields']

    def obs(self, value, reference, name='Haemoglobin', unit='g/dL'):
        raw = {'test_name':name,'result':value,'range':reference,'unit':unit}
        return observation(raw,self.fields,self.config['tests'],self.config['ranges'],{})

    def test_open_closed_boundaries(self):
        for reference, value, expected in [('<16','16','Above Range'),('<=16','16','Within Range'),('Greater than 12','12','Below Range'),('greater than or equal to 12','12','Within Range'),('0.0 -< 16','16','Above Range'),('12 TO 16','14','Within Range'),('≤16','16','Within Range')]:
            with self.subTest(reference=reference,value=value):
                self.assertEqual(self.obs(value,reference)['analytics'],expected)
        self.assertIsNone(reference_range('16-12'))
        self.assertIsNone(reference_range('12-<12'))

    def test_result_intervals_do_not_become_point_values(self):
        for value, reference, expected in [('12-14','12-16','Within Range'),('10-11','12-16','Below Range'),('17-18','12-16','Above Range'),('11-14','12-16','Invalid'),('<16','<=16','Within Range'),('<=16','<16','Invalid'),('>999','12-16','Outlier')]:
            result = self.obs(value,reference)
            self.assertEqual(result['analytics'],expected,(value,reference))
            self.assertIsNone(result['result_value'])
            self.assertIsNotNone(result['result_interval'])

    def test_units_affine_conversion_and_interval_reference_units(self):
        result = self.obs('98.6 degree F','97-100',name='Body Temperature',unit='degree F')
        self.assertAlmostEqual(result['result_value'],37)
        self.assertEqual(result['analytics'],'Within Range')
        result = self.obs('140 g/L','120-160 g/L',unit='g/L')
        self.assertEqual(result['analytics'],'Within Range')
        self.assertAlmostEqual(result['range_low'],12)
        self.assertEqual(self.obs('14 g/dL','120-160 g/L')['analytics'],'Invalid')
        result = self.obs('2-4 /hpf','0-5',name='Urine Pus Cells',unit='/hpf')
        self.assertEqual(result['analytics'],'Within Range')
        result = self.obs('114/min','60-120',name='Pulse',unit='min')
        self.assertEqual(result['analytics'],'Within Range')

    def test_missing_and_malformed_source_range(self):
        result = self.obs('','12-16')
        self.assertEqual(result['value_status'],'Missing')
        self.assertEqual(result['issues'],['Missing result'])
        result = self.obs('85','bad source range',name='MCV',unit='fL')
        self.assertEqual(result['analytics'],'Invalid')
        self.assertIsNone(result['range_source'])

    def test_aliases_do_not_repair_bad_source_rows(self):
        result = self.obs('9700','4000-10000',name='aemoglobin',unit='cell/cu.mm')
        self.assertEqual(result['test_name_canonical'],'Haemoglobin')
        self.assertEqual(result['analytics'],'Invalid')
        for name in ['DIAGNOSTICS','ABSENT','NEGATIVE','9-11','test_name','BE']:
            self.assertIsNone(normalize_name(name,self.config['tests'])[0],name)
        result = self.obs('13.7 g/dl','13-17',name='COMPLETE BLOOD COUNT (CBC) , WHOLE BLOOD EDTA',unit='g/dL')
        self.assertEqual(result['test_name_canonical'],'Complete Blood Count Panel')
        self.assertEqual(result['analytics'],'Invalid')


class CompositeTests(unittest.TestCase):
    def setUp(self):
        self.config = configuration()
        self.fields = self.config['clinics']['profiles'][0]['test_fields']

    def expand(self,name,value,unit='',reference=''):
        return expand_test({'test_name':name,'result':value,'unit':unit,'range':reference,'page_no':9},self.fields,self.config['tests'])

    def test_ordered_bilirubin_and_reference_alignment(self):
        parts = self.expand('Serum Bilirubin (Total, Direct & Indirect)','0.4 mg/dl, 0.1 mg/dl, 0.3 mg/dl','mg/dl','0.0 -< 1.0, 0.0-0.3, 0.0-1.1')
        self.assertEqual([part['test_name'] for part,_ in parts],['Bilirubin Total','Bilirubin Direct','Bilirubin Indirect'])
        for part,provenance in parts:
            result = observation(part,self.fields,self.config['tests'],self.config['ranges'],{})
            self.assertEqual(result['analytics'],'Within Range')
            self.assertEqual(provenance['derived_from']['range'],'0.0 -< 1.0, 0.0-0.3, 0.0-1.1')
        self.assertFalse(observation(parts[0][0],self.fields,self.config['tests'],self.config['ranges'],{})['range_high_inclusive'])

    def test_named_components_and_sum_validation(self):
        parts = self.expand('Differential Leukocyte Counts','Neutrophil - 72.4, Lymphocyte - 23.5, Eosinophils - 0.7, Monocytes - 3.2, Basophils - 0.2')
        self.assertEqual(len(parts),5)
        self.assertEqual(parts[0][0]['unit'],'%')
        self.assertEqual(parts[0][1]['unit_provenance'],'configured named-panel convention')
        bad = self.expand('Differential Leukocyte Counts','Neutrophils: 90, Lymphocytes: 90')
        self.assertEqual(len(bad),1)
        self.assertIn('sum',bad[0][1]['expansion_error'])
        absolute = self.expand('Absolute Leucocyte Count','NEUTROPHILS 2230.8 cells/cu.mm, LYMPHOCYTES 1716 cells/cu.mm, EOSINOPHILS 42.9 cells/cu.mm, MONOCYTES 300.3 cells/cu.mm','cells/cu.mm')
        self.assertEqual(len(absolute),4)
        self.assertEqual(absolute[0][0]['test_name'],'Absolute Neutrophils')

    def test_ambiguous_panels_remain_intact(self):
        for value,reference in [('0.4,0.1',''),('0.4,0.1,0.3','0-1'),('Bilirubin Total: 0.4, unknown: 9','')]:
            parts = self.expand('Bilirubin Panel',value,reference=reference)
            self.assertEqual(len(parts),1)
            self.assertEqual(parts[0][0]['result'],value)
            self.assertIn('expansion_error',parts[0][1])
        parts = self.expand('Bilirubin Panel','Bilirubin Total: 0.4, Bilirubin Direct: 0.1, Bilirubin Indirect: 0.3')
        self.assertEqual(len(parts),3)
        self.assertTrue(all(part['unit']=='' for part,_ in parts))

    def test_no_components_silently_discarded(self):
        parts = self.expand('Differential Leukocyte Panel','Neutrophils: 70, Lymphocytes: 30, mystery: 10')
        self.assertEqual(len(parts),1)
        self.assertIn('Unmapped',parts[0][1]['expansion_error'])
        parts = self.expand('Bilirubin Panel','Bilirubin Total: 0.4, Bilirubin Total: 0.5')
        self.assertEqual(len(parts),1)
        self.assertIn('Duplicate',parts[0][1]['expansion_error'])


class ReplayAndReportingTests(unittest.TestCase):
    def test_coverage_uses_original_denominator(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder)/'test.sqlite'
            result = process_files(read_folder(ROOT/'sample-data'),db)
            self.assertEqual((result['total_tests'],result['resolved_tests']),(363,336))
            self.assertEqual(result['observation_count'],398)
            self.assertEqual(result['flagged'],8)
            report = dashboard(db)
            self.assertEqual(report['total_tests'],363)
            self.assertGreater(report['resolved_tests']/report['total_tests'],0.9)
            self.assertEqual(sum(report['unresolved_names'].values()),27)
            self.assertEqual(report['coverage_kinds']['panel'],30)

    def test_replay_archives_previous_output_and_review(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder)/'test.sqlite'
            configs = Path(folder)/'config';configs.mkdir()
            config = configuration()
            for name,data in config.items(): (configs/(name+'.json')).write_text(json.dumps(data))
            files = [('original.json',(ROOT/'sample-data/Sample_JSON_file1.json').read_text())]
            process_files(files,db,configs)
            with connect(db) as connection:
                old = dict(connection.execute('SELECT * FROM records').fetchone())
                connection.execute('INSERT INTO reviews VALUES (?,?,?)',(old['id'],'Reviewed','2026-01-01T00:00:00+00:00'))
            config['tests']['version'] = 'new-reviewed-config'
            (configs/'tests.json').write_text(json.dumps(config['tests']))
            self.assertEqual(process_files(files,db,configs)['updated_records'],0)
            result = process_files(files,db,configs,reprocess=True)
            self.assertEqual((result['records'],result['updated_records']),(0,1))
            with connect(db) as connection:
                new = dict(connection.execute('SELECT * FROM records').fetchone())
                previous = dict(connection.execute('SELECT * FROM record_versions').fetchone())
                self.assertEqual(connection.execute('SELECT count(*) FROM reviews').fetchone()[0],0)
                self.assertEqual(new['id'],old['id'])
                self.assertEqual(new['ingested_at'],old['ingested_at'])
                self.assertNotEqual(new['config_version'],old['config_version'])
                self.assertEqual(previous['output_json'],old['output_json'])
                self.assertEqual(json.loads(previous['review_json'])['status'],'Reviewed')
            self.assertEqual(process_files(files,db,configs,reprocess=True)['updated_records'],0)
            with connect(db) as connection:
                self.assertEqual(connection.execute('SELECT count(*) FROM record_versions').fetchone()[0],1)

    def test_daily_timezone_and_rate_denominators(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder)/'test.sqlite'
            with connect(db) as connection:
                for name,status,records,duplicates,flagged,occurrences,miss,expected,stamp in [
                    ('a','Processed',2,1,1,3,2,12,'2026-11-12T20:00:00+00:00'),
                    ('b','Failed',0,0,0,0,None,None,'2026-11-13T01:00:00+00:00'),
                    ('c','Processed',1,0,0,1,0,4,'2026-11-13T20:00:00+00:00')]:
                    connection.execute('INSERT INTO files(name,clinic,status,records,duplicates,flagged,record_occurrences,missing_fields,expected_fields,ingested_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(name,'Clinic A',status,records,duplicates,flagged,occurrences,miss,expected,stamp))
            report = dashboard(db,'2026-11-13')
            self.assertEqual(report['daily']['received'],2) # 20:00 UTC on Nov 12 is Nov 13 IST
            self.assertEqual(report['daily']['failed'],1)
            self.assertEqual(report['daily']['flagged_files'],1)
            clinic = report['clinics'][0]
            self.assertEqual(clinic['duplicate_rate'],25)
            self.assertEqual(clinic['error_rate'],33.33)
            self.assertEqual(clinic['missing_field_rate'],12.5)
            self.assertEqual(dashboard(db,'2026-11-14')['daily']['received'],1)
            self.assertEqual(dashboard(db,'2026-11-01')['daily']['received'],0)
            with self.assertRaises(ValueError): dashboard(db,'not-a-date')

    def test_required_contract_treats_redacted_fields_as_missing(self):
        config = configuration()
        profile = config['clinics']['profiles'][0]
        patient = demographics({'patient_name':'[PATIENT NAME REDACTED]','age':'[AGE REDACTED]','gender':'M','reports_date':'04-10-2025'},profile['patient_fields'])
        quality = required_quality(patient,'lab_report',profile)
        self.assertEqual((quality['missing'],quality['expected']),(2,4))
        self.assertEqual(quality['missing_fields'],['patient.name','patient.age_structured'])

class ReplayRollbackTests(unittest.TestCase):
    def test_failed_replay_rolls_back_archives_and_review_reset(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder)/'test.sqlite'
            configs = Path(folder)/'config';configs.mkdir()
            config = configuration()
            for name,data in config.items(): (configs/(name+'.json')).write_text(json.dumps(data))
            source = json.loads((ROOT/'sample-data/Sample_JSON_file1.json').read_text())
            process_files([('source.json',json.dumps(source))],db,configs)
            with connect(db) as c:
                old = dict(c.execute('SELECT * FROM records').fetchone())
                c.execute('INSERT INTO reviews VALUES (?,?,?)',(old['id'],'Reviewed','2026-01-01'))
            config['tests']['version']='revised'
            (configs/'tests.json').write_text(json.dumps(config['tests']))
            source['data']['responseDetails'].append({'classifier':'unsupported','data':{}})
            result=process_files([('source.json',json.dumps(source))],db,configs,reprocess=True)
            self.assertEqual(result['failed'],1)
            with connect(db) as c:
                self.assertEqual(dict(c.execute('SELECT * FROM records').fetchone()),old)
                self.assertEqual(c.execute('SELECT count(*) FROM record_versions').fetchone()[0],0)
                self.assertEqual(c.execute('SELECT status FROM reviews').fetchone()[0],'Reviewed')
