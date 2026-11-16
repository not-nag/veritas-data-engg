"""Adult BP fallback boundaries, source precedence, and applicability."""
import unittest

from pipeline.engine import configuration, build_observations
from pipeline.validate import observation


class BloodPressureReferencesTests(unittest.TestCase):
    def setUp(self):
        self.config = configuration()
        self.fields = self.config['clinics']['profiles'][0]['test_fields']
        self.adult = {'age_structured': {'years': 35}, 'gender': 'Female'}

    def result(self, name, value, patient=None, reference='', unit='mmHg'):
        return observation({'test_name': name, 'result': value, 'unit': unit, 'range': reference}, self.fields, self.config['tests'], self.config['ranges'], self.adult if patient is None else patient)

    def test_adult_pair_gets_sourced_exclusive_thresholds(self):
        rows = build_observations([{'test_name': 'BP', 'result': '120/80 mmHg', 'unit': 'mmHg', 'range': ''}], self.fields, self.config, self.adult)
        self.assertEqual([r['range_high'] for r in rows], [120, 80])
        for row in rows:
            self.assertFalse(row['range_high_inclusive'])
            self.assertIsNone(row['range_low'])
            self.assertEqual(row['analytics'], 'Above Range')
            self.assertEqual(row['reference_policy'], 'adult_bp_upper_threshold')
            self.assertIn('heart.org', row['range_source'])
            self.assertIn('does not assess low blood pressure', row['reference_note'])
            self.assertEqual(row['derived_from']['result_text'], '120/80 mmHg')

    def test_boundary_is_exclusive_for_both_components(self):
        for name, threshold in [('Systolic Blood Pressure', 120), ('Diastolic Blood Pressure', 80)]:
            for delta, expected in [(-1, 'Within Range'), (0, 'Above Range'), (1, 'Above Range')]:
                with self.subTest(name=name, delta=delta):
                    self.assertEqual(self.result(name, str(threshold + delta))['analytics'], expected)

    def test_child_and_unknown_age_do_not_get_adult_reference(self):
        for patient in [{}, {'age_structured': {'years': 17}}, {'age_structured': {'years': 17, 'months': 11}}]:
            row = self.result('Systolic Blood Pressure', '110', patient)
            self.assertIsNone(row['range_source'])
            self.assertNotIn('reference_policy', row)
        self.assertIsNotNone(self.result('Systolic Blood Pressure', '110', {'age_structured': {'years': 18}})['range_source'])

    def test_explicit_source_reference_wins(self):
        row = self.result('Systolic Blood Pressure', '120', reference='90-130')
        self.assertEqual(row['analytics'], 'Within Range')
        self.assertEqual(row['range_high'], 130)
        self.assertEqual(row['range_source'], 'source report (not independently verified)')
        self.assertNotIn('reference_policy', row)

    def test_bad_reference_and_units_are_not_repaired_by_fallback(self):
        for reference, unit in [('unclear', 'mmHg'), ('', 'kPa'), ('', '')]:
            row = self.result('Systolic Blood Pressure', '120', reference=reference, unit=unit)
            self.assertEqual(row['analytics'], 'Invalid')
            self.assertIsNone(row['range_source'])


if __name__ == '__main__':
    unittest.main()
