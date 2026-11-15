"""Declarative schema selection with explicit versions and ambiguity rejection."""
from .standardize import path

MISSING = object()


def predicate(data, rule):
    value = path(data, rule['path'], MISSING)
    if 'exists' in rule and (value is not MISSING) != rule['exists']:
        return False
    if 'equals' in rule and (value is MISSING or value != rule['equals']):
        return False
    if 'in' in rule and (value is MISSING or value not in rule['in']):
        return False
    return value is not MISSING or rule.get('exists') is False


def select_profile(data, profiles):
    matches = []
    rejected_versions = []
    for profile in profiles:
        rule = profile['match']
        if path(data,rule['path'],MISSING) is MISSING:
            continue
        if not all(predicate(data,p) for p in rule.get('all',[])):
            continue
        if rule.get('any') and not any(predicate(data,p) for p in rule['any']):
            continue
        version = path(data,profile.get('schema_version_path'),None) if profile.get('schema_version_path') else None
        if 'schema_versions' in profile and version not in profile['schema_versions']:
            rejected_versions.append(str(version))
            continue
        specificity = profile.get('priority',0)*100 + len(rule.get('all',[])) + bool(rule.get('any')) + bool(profile.get('schema_versions'))
        matches.append((specificity,profile,version))
    if not matches:
        if rejected_versions:
            raise ValueError('Unsupported schema version: '+', '.join(sorted(set(rejected_versions))))
        raise ValueError('No configured clinic schema matches this document')
    matches.sort(key=lambda row:row[0],reverse=True)
    if len(matches)>1 and matches[0][0]==matches[1][0]:
        raise ValueError('Ambiguous clinic profiles: '+matches[0][1]['id']+' / '+matches[1][1]['id'])
    return matches[0][1], matches[0][2]
