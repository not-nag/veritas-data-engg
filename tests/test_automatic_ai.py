"""Pre-storage AI fallback, provenance, failure isolation and unchanged source evidence."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pipeline import ai
from pipeline.engine import ROOT, process_files
from pipeline.store import connect

class AutomaticAITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name)/'test.sqlite'
        self.env = patch.dict(os.environ, {'GEMINI_API_KEY':'test-key', 'GEMINI_AUTO_MAPPING':'true'})
        self.env.start(); self.addCleanup(self.env.stop)
        self.data = json.loads((ROOT/'examples/clinic-v2.json').read_text())
        self.data['reports'][0]['payload']['measurements'] = [{'name':'HGB concentration','value':'13.5 g/dL','units':'g/dL','reference':'12-16'}]

    def process(self):
        return process_files([('synthetic.json',json.dumps(self.data))], self.db)

    def output(self):
        with connect(self.db) as c:
            row = c.execute('SELECT raw_json,output_json FROM records').fetchone()
        return json.loads(row[0]),json.loads(row[1])

    def test_maps_before_storage_preserves_source_and_does_not_approve_alias(self):
        def generate(*args, **kwargs):
            # The network fallback must not hold the file's write transaction.
            with connect(self.db) as c:
                c.execute('BEGIN IMMEDIATE')
                self.assertEqual(c.execute('SELECT count(*) FROM records').fetchone()[0],0)
            self.assertEqual(args[0],'HGB concentration')
            return 'Haemoglobin','Same analyte.'
        with patch.object(ai,'generate',side_effect=generate) as call:
            self.assertEqual(self.process()['records'],1)
            self.assertEqual(self.process()['duplicates'],1)
            self.assertEqual(call.call_count,1)
        raw,out = self.output();o=out['observations'][0]
        self.assertEqual(raw,self.data['reports'][0])
        self.assertEqual(o['test_name_original'],'HGB concentration')
        self.assertEqual(o['test_name_canonical'],'Haemoglobin')
        self.assertEqual(o['normalization_method'],'gemini')
        self.assertIsNone(o['normalization_confidence'])
        self.assertEqual(o['result_value'],13.5)
        self.assertEqual(o['analytics'],'Within Range')
        self.assertEqual(ai.snapshot(self.db)['aliases'],[])
        self.assertEqual(ai.snapshot(self.db)['automatic'][0]['status'],'Mapped')

    def test_failure_unresolved_and_invalid_response_do_not_fail_file(self):
        for result in [ValueError('timeout'),(None,'Ambiguous label.'),('Invented test','Bad mapping.')]:
            with self.subTest(result=str(result)), patch.object(ai,'generate') as call:
                if isinstance(result,Exception):call.side_effect=result
                else:call.return_value=result
                self.data['documentId'] += 'X'
                self.assertEqual(self.process()['failed'],0)
        with connect(self.db) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM observations WHERE canonical IS NULL').fetchone()[0],3)

    def test_exact_fuzzy_headings_and_numeric_labels_do_not_call_gemini(self):
        names=['Hb','Haemoglobinn','ABSENT','Comment','9-11']
        self.data['reports'][0]['payload']['measurements']=[{'name':n,'value':'13.5','units':'g/dL','reference':'12-16'} for n in names]
        with patch.object(ai,'generate') as call:
            self.process();call.assert_not_called()

    def test_repeated_unknown_labels_use_one_call_per_run(self):
        self.data['reports'][0]['payload']['measurements'] *= 2
        with patch.object(ai,'generate',return_value=('Haemoglobin','Same analyte.')) as call:
            self.process();self.assertEqual(call.call_count,1)
        self.assertEqual(len(self.output()[1]['observations']),2)

    def test_disabled_or_missing_key_does_not_call(self):
        for env in [{'GEMINI_AUTO_MAPPING':'false'},{'GEMINI_API_KEY':''}]:
            with patch.dict(os.environ,env),patch.object(ai,'generate') as call:
                self.data['documentId'] += 'X';self.process();call.assert_not_called()

    def test_quota_exhaustion_saves_unresolved_without_call(self):
        with connect(self.db) as c:
            for n in range(10):c.execute('INSERT INTO ai_calls VALUES (?,?,?,?)',(str(n),'test',ai.stamp(),'failed'))
        with patch.object(ai,'generate') as call:
            self.assertEqual(self.process()['failed'],0);call.assert_not_called()
        self.assertIsNone(self.output()[1]['observations'][0]['test_name_canonical'])
        self.assertEqual(ai.snapshot(self.db)['automatic'][0]['status'],'Skipped')

    def test_user_cannot_inject_an_ai_mapping(self):
        test=self.data['reports'][0]['payload']['measurements'][0]
        test['__ai_mapping']={'canonical':'Haemoglobin'}
        test['__interpretation']={'canonical':'Haemoglobin','category':'test','method':'gemini'}
        with patch.dict(os.environ,{'GEMINI_AUTO_MAPPING':'false'}):self.process()
        o=self.output()[1]['observations'][0]
        self.assertIsNone(o['test_name_canonical']);self.assertNotIn('ai_mapping',o)

    def test_explicit_replay_retries_failed_ai_with_unchanged_config_and_archives_output(self):
        with patch.object(ai,'generate',side_effect=ValueError('Gemini could not be reached. Try later.')):
            self.process()
        before=self.output()[1]
        self.assertEqual(before['observations'][0]['ai_mapping']['reason'],'Gemini could not be reached. Try later.')
        with patch.object(ai,'generate',return_value=('Haemoglobin','Same analyte.')) as call:
            self.assertEqual(self.process()['duplicates'],1)
            call.assert_not_called()
            result=process_files([('synthetic.json',json.dumps(self.data))],self.db,reprocess=True)
            self.assertEqual(result['updated_records'],1)
            call.assert_called_once()
        after=self.output()[1]
        self.assertEqual(after['config_version'],before['config_version'])
        self.assertEqual(after['observations'][0]['normalization_method'],'gemini')
        with connect(self.db) as c:
            old=json.loads(c.execute('SELECT output_json FROM record_versions').fetchone()[0])
        self.assertEqual(old['observations'][0]['ai_mapping']['status'],'Failed')

    def test_successful_ai_is_not_repeated_by_unchanged_replay(self):
        with patch.object(ai,'generate',return_value=('Haemoglobin','Same analyte.')) as call:
            self.process()
            result=process_files([('synthetic.json',json.dumps(self.data))],self.db,reprocess=True)
            self.assertEqual(result['duplicates'],1)
            self.assertEqual(call.call_count,1)
