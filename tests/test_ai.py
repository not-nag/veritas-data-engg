"""AI suggestion review controls and deterministic reprocessing."""
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from pipeline import ai
from pipeline.engine import configuration, process_files, ROOT
from pipeline.store import connect
from pipeline.standardize import normalize_name


class IntegrationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root/'test.sqlite'
        self.config = configuration()['tests']
        self.env = patch.dict(os.environ, {'GEMINI_API_KEY':'test-key'})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.addCleanup(self.temp.cleanup)

    def suggestion(self, label='HGB concentration', canonical='Haemoglobin'):
        return ai.suggest(label, self.db, copy.deepcopy(self.config), 'reviewer-1',
                          generator=lambda *_:(canonical, 'Equivalent analyte.'))['suggestions'][0]

    def test_suggestion_changes_nothing_until_accepted_and_is_audited(self):
        suggestion = self.suggestion()
        config = copy.deepcopy(self.config)
        ai.apply_aliases(config, self.db)
        self.assertIsNone(normalize_name(suggestion['label'], config)[0])
        ai.decide(suggestion['id'], 'Accepted', self.db, self.config, 'reviewer-2')
        ai.apply_aliases(config, self.db)
        self.assertEqual(normalize_name(suggestion['label'], config)[0], 'Haemoglobin')
        state = ai.snapshot(self.db)
        self.assertEqual(state['suggestions'][0]['reviewed_by'], 'reviewer-2')
        with self.assertRaises(ValueError):
            ai.decide(suggestion['id'], 'Accepted', self.db, self.config, 'reviewer-3')
        with self.assertRaises(ValueError):
            self.suggestion()

    def test_accepted_alias_changes_explicit_reprocess_and_preserves_previous_version(self):
        data = json.loads((ROOT/'examples/clinic-v2.json').read_text())
        data['reports'][0]['payload']['measurements'][0]['name'] = 'HGB concentration'
        files = [('synthetic.json', json.dumps(data))]
        process_files(files, self.db)
        with connect(self.db) as c:
            before = json.loads(c.execute('SELECT output_json FROM records').fetchone()[0])
        self.assertIsNone(before['observations'][0]['test_name_canonical'])
        suggestion = self.suggestion()
        ai.decide(suggestion['id'], 'Accepted', self.db, self.config, 'reviewer')
        self.assertEqual(process_files(files, self.db)['duplicates'], 1)
        result = process_files(files, self.db, reprocess=True)
        self.assertEqual(result['updated_records'], 1)
        with connect(self.db) as c:
            after = json.loads(c.execute('SELECT output_json FROM records').fetchone()[0])
            archived = json.loads(c.execute('SELECT output_json FROM record_versions').fetchone()[0])
        self.assertEqual(after['observations'][0]['test_name_canonical'], 'Haemoglobin')
        self.assertEqual(after['observations'][0]['result_value'], 13.5)
        self.assertIsNone(archived['observations'][0]['test_name_canonical'])
        self.assertNotEqual(before['config_version'], after['config_version'])

    def test_rejected_and_unresolved_suggestions_never_become_aliases(self):
        suggestion = self.suggestion()
        ai.decide(suggestion['id'], 'Rejected', self.db, self.config, 'reviewer')
        self.suggestion('unclear label', None)
        self.assertEqual(ai.snapshot(self.db)['aliases'], [])

    def test_cross_test_alias_conflict_cannot_be_accepted(self):
        suggestion = self.suggestion()
        config = copy.deepcopy(self.config)
        config['tests']['White Blood Cell Count']['aliases'].append(suggestion['label'])
        with self.assertRaisesRegex(ValueError, 'conflict'):
            ai.decide(suggestion['id'], 'Accepted', self.db, config, 'reviewer')

    def test_daily_call_cap_and_failed_calls_consume_quota(self):
        def failure(*_): raise ValueError('upstream failed')
        for _ in range(10):
            with self.assertRaisesRegex(ValueError, 'upstream'):
                ai.suggest('Unknown assay', self.db, copy.deepcopy(self.config), 'reviewer', failure)
        with self.assertRaisesRegex(ValueError, '10 Gemini calls'):
            self.suggestion()
        self.assertEqual(ai.snapshot(self.db)['calls_today'], 10)

    def test_generation_response_must_match_schema(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = json.dumps({'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps({'canonical':'Invented test','reason':'bad'})}]}}]}).encode()
        with patch('urllib.request.urlopen', return_value=response):
            with self.assertRaisesRegex(ValueError, 'invalid'):
                ai.generate('unknown', self.config['tests'], 'key', 'gemini-3.5-flash-lite')

if __name__ == '__main__': unittest.main()
