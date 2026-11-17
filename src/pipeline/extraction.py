"""Interpret explicit label context without shifting rows or inventing missing values."""
from copy import deepcopy
import re
from .standardize import key, path, normalize_name


def prepare_tests(tests, fields, config):
    prepared = []
    rules = config.get('extraction', {})
    for index, original in enumerate(tests):
        test = deepcopy(original)
        # Never accept internal annotations supplied by an uploaded document.
        test.pop('__interpretation', None)
        test.pop('__ai_mapping', None)
        name = str(path(test, fields['name'], '') or '')
        category = rules.get('non_test_labels', {}).get(key(name))
        if category:
            test['__interpretation'] = {'category':category, 'reason':'Exact configured non-test label; source retained'}
        elif not normalize_name(name, config)[0]:
            for rule in rules.get('context_rules', []):
                if key(name) != key(rule['label']):
                    continue
                preceding = tests[max(0,index-rule.get('window',1)):index]
                anchors = {key(label) for label in rule['preceding_labels']}
                if not any(key(path(p,fields['name'],'')) in anchors for p in preceding):
                    continue
                required = {key(label) for label in rule.get('required_preceding_labels',[])}
                context = tests[max(0,index-rule.get('context_window',8)):index]
                if required and not any(key(path(p,fields['name'],'')) in required for p in context):
                    continue
                if rule.get('result_values') and key(path(test,fields['result'],'')) not in {key(v) for v in rule['result_values']}:
                    continue
                if rule['canonical'] in config['tests']:
                    test['__interpretation'] = {'canonical':rule['canonical'], 'category':'test', 'reason':rule['reason'], 'rule':rule['id']}
                    break
            if '__interpretation' not in test:
                for rule in rules.get('label_patterns', []):
                    if re.fullmatch(rule['pattern'], name, re.I) and rule['canonical'] in config['tests']:
                        test['__interpretation'] = {'canonical':rule['canonical'], 'category':'test', 'reason':rule['reason'], 'rule':rule['id']}
                        break
        prepared.append(test)
    return prepared


def resolve_test(test, fields, config):
    interpretation = test.get('__interpretation', {})
    if interpretation.get('canonical') in config['tests']:
        return interpretation['canonical'], interpretation.get('method', 'configured context'), None if interpretation.get('method') == 'gemini' else 1.0
    return normalize_name(path(test, fields['name'], ''), config)
