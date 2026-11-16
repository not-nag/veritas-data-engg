"""Sourced fallback applicability, medicine forms and safe AI inputs."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pipeline import ai
from pipeline.engine import configuration
from pipeline.standardize import medication, normalize_name
from pipeline.validate import observation

class ReferenceExpansionTests(unittest.TestCase):
    def setUp(self):
        self.c = configuration()
        self.f = self.c['clinics']['profiles'][0]['test_fields']
        self.adult = {'age_structured':{'years':35}, 'gender':'Female'}

    def test_new_fallbacks_apply_only_to_supported_adults_and_units(self):
        for name, value, unit in [('Calcium','9.5','mg/dL'),('Chloride','103','mmol/L'),('Albumin','4','g/dL'),('Total Protein','7','g/dL'),('ALT','20','U/L'),('AST','20','U/L'),('Bilirubin Total','.5','mg/dL'),('Blood Urea Nitrogen','10','mg/dL')]:
            raw={'test_name':name,'result':value,'unit':unit}
            o=observation(raw,self.f,self.c['tests'],self.c['ranges'],self.adult)
            self.assertEqual(o['analytics'],'Within Range',name)
            self.assertIn('medlineplus.gov',o['range_source'])
            for patient in [{},{'age_structured':{'years':5}}]:
                self.assertIsNone(observation(raw,self.f,self.c['tests'],self.c['ranges'],patient)['range_source'])
            raw['unit']='unknown'
            self.assertIsNone(observation(raw,self.f,self.c['tests'],self.c['ranges'],self.adult)['range_source'])

    def test_source_ranges_win_and_malformed_ranges_are_not_replaced(self):
        raw={'test_name':'Calcium','result':'9.5','unit':'mg/dL','range':'9.6-10.5'}
        o=observation(raw,self.f,self.c['tests'],self.c['ranges'],self.adult)
        self.assertEqual(o['analytics'],'Below Range')
        self.assertIn('source report',o['range_source'])
        raw['range']='unreadable'
        self.assertEqual(observation(raw,self.f,self.c['tests'],self.c['ranges'],self.adult)['analytics'],'Invalid')

    def test_new_medicine_matches_keep_form_and_strength_distinctions(self):
        f={'name':'name','dose':'dose','frequency':'frequency'}
        for label, expected in [('Inj. Dynapar','Diclofenac sodium'),('Econorm Sachet','Saccharomyces boulardii'),('ECO NORM SACHET','Saccharomyces boulardii'),('Inj. Buscopan','Hyoscine butylbromide')]:
            o=medication({'name':label},f,self.c['medicines'])
            self.assertEqual(o['generic'],expected)
            self.assertTrue(o['mapping_source'])
            self.assertIsNone(o['dose'])
        for label in ['Tab. Dynapar','Dynapar Gel','Econorm Z Sachet','Econorm','Buscopan Plus']:
            self.assertIsNone(medication({'name':label},f,self.c['medicines'])['generic'])

    def test_aliases_are_exact_and_ambiguous_labels_stay_unresolved(self):
        self.assertEqual(normalize_name('mean corpuscular haemoglobin',self.c['tests'])[0],'MCH')
        for label in ['ABSENT','9-11','ET','BE']:
            self.assertIsNone(normalize_name(label,self.c['tests'])[0])

    def test_result_only_labels_do_not_consume_an_ai_call(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'GEMINI_API_KEY':'test-key'}):
            db=Path(temp)/'test.sqlite'
            for label in ['ABSENT','NEGATIVE','9-11','Comment']:
                with self.assertRaisesRegex(ValueError,'original report'):
                    ai.suggest(label,db,self.c['tests'],'local-user',generator=lambda *_:self.fail('No AI call expected'))
            self.assertEqual(ai.snapshot(db)['calls_today'],0)
