"""Required-field quality contracts and source-entry coverage use explicit denominators."""
from collections import Counter
from .standardize import path, normalize_name
from .extraction import resolve_test


def missing(value):
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip() or 'redacted' in value.lower() or value.strip().lower() in {'n/a','na','unknown','null','none'}
    return False


def required_quality(patient, kind, profile):
    fields = profile.get('required_fields', {}).get(kind, [])
    absent = [field for field in fields if missing(path({'patient':patient}, field))]
    return {'expected':len(fields), 'missing':len(absent), 'missing_fields':absent, 'contract':fields}


def source_coverage(tests, fields, config):
    counts = Counter()
    unresolved = Counter()
    non_tests = Counter()
    for test in tests:
        original = path(test, fields['name'], '')
        canonical, _, _ = resolve_test(test, fields, config)
        category = test.get('__interpretation', {}).get('category')
        if category and category != 'test':
            non_tests[str(original)] += 1
        if canonical:
            counts[config['tests'][canonical]['kind']] += 1
        else:
            unresolved[str(original)] += 1
    eligible = len(tests)-sum(non_tests.values())
    return {'total':len(tests), 'resolved':sum(counts.values()), 'kinds':dict(counts), 'unresolved_names':dict(unresolved), 'non_test_entries':sum(non_tests.values()), 'non_test_names':dict(non_tests), 'eligible_entries':eligible}
