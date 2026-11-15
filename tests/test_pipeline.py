import json
import tempfile
import unittest
from pathlib import Path
from pipeline.engine import configuration, process_files, ROOT
from pipeline.standardize import number, normalize_name, demographics, medication
from pipeline.validate import observation
from pipeline.store import connect


class StandardisationTests(unittest.TestCase):
    def setUp(self):
        self.c = configuration()
        self.fields = {'name':'test_name','result':'result','unit':'unit','range':'range','page':'page_no'}

    def obs(self,result='14',unit='g/dL',name='Haemoglobin',range='12-16',patient=None):
        return observation({'test_name':name,'result':result,'unit':unit,'range':range},self.fields,self.c['tests'],self.c['ranges'],patient or {})

    def test_numeric_units_thousands_and_flags(self):
        self.assertEqual(number('120,000 cells/cu.mm')[0],120000)
        self.assertEqual(number('L 3.8 million/cumm')[0],3.8)
        self.assertEqual(number(0)[0],0)
        for value in [None,True,'NEGATIVE','100/60 mmHg','0.4 mg/dl, 0.1 mg/dl','1-4','<10 /hp','NaN','1e999']:
            self.assertIsNone(number(value)[0],value)

    def test_alias_and_unit_conversion(self):
        self.assertEqual(normalize_name('aemoglobin',self.c['tests'])[0],'Hemoglobin')
        r = self.obs('140 g/L','g/L')
        self.assertEqual(r['result_value'],14)
        self.assertAlmostEqual(r['range_low'],1.2) # source range converted with its stated units
        self.assertEqual(self.obs('14 g/dL','cells/cumm')['analytics'],'Invalid')
        self.assertEqual(self.obs('14 g/L','g/dL')['analytics'],'Invalid')
        r = self.obs('1.5','lac/cmm','Platelet Count','1.5-4.5')
        self.assertEqual(r['result_value'],150000)
        self.assertEqual(r['range_high'],450000)

    def test_validation_boundaries_and_outlier(self):
        for v,expected in [('12','Within Range'),('16','Within Range'),('17','Above Range'),('11','Below Range'),('999','Outlier'),('0.1','Outlier'),('POSITIVE','Invalid')]:
            self.assertEqual(self.obs(v)['analytics'],expected)
        self.assertEqual(self.obs(name='unknown test')['analytics'],'Invalid')
        self.assertEqual(self.obs(range='')['analytics'],'Invalid')
        self.assertEqual(self.obs(name='Dengue NS1',result='NEGATIVE',unit='')['analytics'],'Within Range')

    def test_demographics(self):
        p = demographics({'age':'33Y11M265D','gender':'M','date':'07-Oct-2025'},{'age':['age'],'gender':['gender'],'report_date':['date']})
        self.assertEqual(p['age_structured'],{'years':33,'months':11,'days':265})
        self.assertEqual(p['gender'],'Male')
        self.assertEqual(p['report_date'],'2025-10-07')
        self.assertIsNone(demographics({'age':'[AGE REDACTED]'},{'age':['age']})['age_structured'])

    def test_medicine_does_not_guess(self):
        fields={'name':'medicine','dose':'dose','frequency':'frequency'}
        self.assertEqual(medication({'medicine':'acetaminophen'},fields,self.c['medicines'])['generic'],'Paracetamol')
        self.assertIsNone(medication({'medicine':'Inj. mystery'},fields,self.c['medicines'])['generic'])
        self.assertEqual(medication({'medicine':'TAB DOLO 650'},fields,self.c['medicines'])['generic'],'Paracetamol')


class IntegrationTests(unittest.TestCase):
    def test_samples_idempotency_and_fault_isolation(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder)/'test.sqlite'
            files = [(str(p),p.read_text()) for p in sorted((ROOT/'sample-data').glob('*.json'))]
            r = process_files([('broken.json','{'),*files],db)
            self.assertEqual((r['failed'],r['processed'],r['records'],r['duplicates']),(1,5,8,1))
            self.assertTrue(list((Path(folder)/'dead-letter').glob('*.json')))
            r2 = process_files(files,db)
            self.assertEqual(r2['records'],0)
            self.assertEqual(r2['duplicates'],9)
            with connect(db) as c:
                self.assertEqual(c.execute('SELECT count(*) FROM records').fetchone()[0],8)
                self.assertEqual(c.execute('SELECT count(*) FROM observations').fetchone()[0],398)
                self.assertTrue(all(row[0] for row in c.execute('SELECT config_version FROM records')))

    def test_file_rollback(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder)/'test.sqlite'
            data = json.loads((ROOT/'sample-data/Sample_JSON_file1.json').read_text())
            data['data']['responseDetails'].append({'classifier':'unknown','data':{}})
            r = process_files([('partial.json',json.dumps(data))],db)
            self.assertEqual(r['failed'],1)
            with connect(db) as c:
                self.assertEqual(c.execute('SELECT count(*) FROM records').fetchone()[0],0)

    def test_config_only_new_schema_and_test(self):
        with tempfile.TemporaryDirectory() as folder:
            c = configuration()
            profile = dict(c['clinics']['profiles'][0])
            profile.update({'id':'new-clinic','match':{'path':'reports'},'records_path':'reports','document_id_path':'id','metadata_path':'meta','clinic_path':'clinic','patient_path':'patient','tests_path':'measurements'})
            profile['test_fields']={'name':'label','result':'value','unit':'units','range':'limits','page':'page'}
            c['clinics']['profiles'].append(profile)
            c['tests']['tests']['New Test']={'aliases':['new variant'],'kind':'numeric','unit':'mg/L','units':{'mg/l':1},'plausible':[0,100],'reference':None}
            config = Path(folder)/'config';config.mkdir()
            for n,v in c.items(): (config/(n+'.json')).write_text(json.dumps(v))
            data={'id':'new-001','clinic':'Clinic B','meta':{},'reports':[{'classifier':'lab_report','data':{'patient':{},'measurements':[{'label':'new variant','value':'5','units':'mg/L','limits':'1-10'}]}}]}
            db = Path(folder)/'test.sqlite'
            self.assertEqual(process_files([('new.json',json.dumps(data))],db,config)['records'],1)
            with connect(db) as conn:
                o=json.loads(conn.execute('SELECT output_json FROM observations').fetchone()[0])
            self.assertEqual(o['analytics'],'Within Range')
            self.assertEqual(o['test_name_canonical'],'New Test')

class ExportTests(unittest.TestCase):
    def test_wide_columns_absent_tests_and_repeat_preservation(self):
        import csv
        import io
        from unittest.mock import patch
        from pipeline.api import export_csv
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/'test.sqlite'
            files=[('sample.json',(ROOT/'sample-data/Sample_JSON_file4.json').read_text())]
            process_files(files,db)
            with patch('pipeline.api.DB',db):
                reader=csv.DictReader(io.StringIO(export_csv()))
                rows=list(reader)
            expected=4+5*len(configuration()['tests']['tests'])
            self.assertEqual(len(reader.fieldnames),expected)
            self.assertTrue(all(len(row)==expected for row in rows))
            discharge=next(r for r in rows if r['record_type']=='discharge_summary')
            self.assertEqual(discharge['Hemoglobin_Result'],'')
            self.assertGreater(len(rows),2) # repeated tests are not overwritten

if __name__=='__main__': unittest.main()
