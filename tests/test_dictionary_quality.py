"""Coverage improvements must retain source evidence and respect clinical ambiguity."""
import tempfile
import unittest
from pathlib import Path
from pipeline.engine import configuration, process_files, read_folder, ROOT
from pipeline.extraction import prepare_tests
from pipeline.quality import source_coverage
from pipeline.reporting import dashboard
from pipeline.standardize import medication
from pipeline.validate import observation


class DictionaryQualityTests(unittest.TestCase):
    def setUp(self):
        self.config = configuration()
        self.fields = self.config['clinics']['profiles'][0]['test_fields']

    def test_glucose_requires_explicit_urine_section_and_qualitative_result(self):
        for anchor, value, expected in [('BIOCHEMICAL EXAMINATION','NEGATIVE','Urine Glucose'),('Blood Sugar','NEGATIVE',None),('BIOCHEMICAL EXAMINATION','100',None)]:
            raw=[{'test_name':'SP. GRAVITY'},{'test_name':anchor},{'test_name':'GLUCOSE','result':value}]
            prepared=prepare_tests(raw,self.fields,self.config['tests'])
            result=observation(prepared[2],self.fields,self.config['tests'],self.config['ranges'],{})
            self.assertEqual(result['test_name_canonical'],expected)
            self.assertEqual(raw[2],{'test_name':'GLUCOSE','result':value})

    def test_biochemical_heading_alone_does_not_imply_urine(self):
        raw=[{'test_name':'BIOCHEMICAL EXAMINATION'},{'test_name':'GLUCOSE','result':'NEGATIVE'}]
        prepared=prepare_tests(raw,self.fields,self.config['tests'])
        result=observation(prepared[1],self.fields,self.config['tests'],self.config['ranges'],{})
        self.assertIsNone(result['test_name_canonical'])

    def test_non_test_rows_remain_in_raw_denominator_and_outputs(self):
        raw=[{'test_name':'Comment','result':'Retain this evidence'},{'test_name':'ABSENT','result':'ABSENT'},{'test_name':'Haemoglobin','result':'12','unit':'g/dL','range':'12-16'}]
        prepared=prepare_tests(raw,self.fields,self.config['tests'])
        coverage=source_coverage(prepared,self.fields,self.config['tests'])
        self.assertEqual((coverage['total'],coverage['resolved'],coverage['eligible_entries'],coverage['non_test_entries']),(3,1,2,1))
        result=observation(prepared[0],self.fields,self.config['tests'],self.config['ranges'],{})
        self.assertEqual(result['result_text'],'Retain this evidence')
        self.assertEqual(result['analytics'],'Invalid')

    def test_uploaded_internal_annotations_cannot_override_matching(self):
        raw=[{'test_name':'Mystery','__interpretation':{'canonical':'Haemoglobin','category':'test'}}]
        self.assertNotIn('__interpretation',prepare_tests(raw,self.fields,self.config['tests'])[0])

    def test_label_recovery_never_invents_missing_values_or_units(self):
        raw=[{'test_name':'KFT - sr creatinine - 0.3','result':''}]
        prepared=prepare_tests(raw,self.fields,self.config['tests'])
        result=observation(prepared[0],self.fields,self.config['tests'],self.config['ranges'],{})
        self.assertEqual(result['test_name_canonical'],'Creatinine')
        self.assertIsNone(result['result_value'])
        self.assertEqual(result['analytics'],'Invalid')
        alone=prepare_tests([{'test_name':'FILTRATION RATE','result':'>60'}],self.fields,self.config['tests'])
        self.assertIsNone(observation(alone[0],self.fields,self.config['tests'],self.config['ranges'],{})['test_name_canonical'])

    def test_verified_medicine_variants_and_form_constraints(self):
        fields={'name':'name','dose':'dose','frequency':'frequency'}
        for name,generic in [('TAB. PAN - 40 (before breakfast)','Pantoprazole'),('Cap. Pan D','Pantoprazole + Domperidone'),('Inj. Pan','Pantoprazole'),('Inj. Fortwin','Pentazocine')]:
            result=medication({'name':name},fields,self.config['medicines'])
            self.assertEqual(result['generic'],generic)
            self.assertTrue(result['mapping_source'])
            self.assertIsNone(result['dose'])
        for name in ['Pan','Tab. Pan','PAN D PLUS','PAN 80','Tab. Fortwin']:
            self.assertIsNone(medication({'name':name},fields,self.config['medicines'])['generic'])
        result=medication({'name':'IV Fluids'},fields,self.config['medicines'])
        self.assertEqual(result['status'],'Treatment category')
        self.assertIsNone(result['generic'])

    def test_reference_applicability_is_explicit(self):
        for name,value,unit,expected in [('RDW CV','12','%','Within Range'),('Albumin Globulin Ratio','1.3','ratio','Within Range'),('Neutrophils','50','%','Invalid')]:
            result=observation({'test_name':name,'result':value,'unit':unit},self.fields,self.config['tests'],self.config['ranges'],{})
            self.assertEqual(result['analytics'],expected)
        result=observation({'test_name':'Neutrophils','result':'72','unit':'%'},self.fields,self.config['tests'],self.config['ranges'],{'age_structured':{'years':30}})
        self.assertEqual(result['analytics'],'Above Range')
        self.assertIn('medlineplus.gov',result['range_source'])

    def test_sample_coverage_has_two_visible_denominators(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/'db.sqlite'
            process_files(read_folder(ROOT/'sample-data'),db)
            result=dashboard(db)
            self.assertEqual((result['resolved_tests'],result['total_tests']),(336,363))
            self.assertEqual((result['non_test_entries'],result['eligible_test_entries']),(13,350))
            self.assertEqual(result['observation_count'],398)
