"""Validate scalar and interval results without inventing point estimates or missing units."""
import re
import math
from .standardize import number, result_unit, path, normalize_name
from .extraction import resolve_test

NUM = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)'


def reference_range(raw):
    """Parse intervals and one-sided limits, keeping open/closed endpoints explicit."""
    text = str(raw or '').strip().replace('−', '-').replace('–', '-').replace('≤', '<=').replace('≥', '>=')
    text = re.sub(r'\bless\s+than\s+or\s+equal\s+to\b', '<=', text, flags=re.I)
    text = re.sub(r'\bgreater\s+than\s+or\s+equal\s+to\b', '>=', text, flags=re.I)
    text = re.sub(r'\bless\s+than\b', '<', text, flags=re.I)
    text = re.sub(r'\bgreater\s+than\b', '>', text, flags=re.I)
    interval = re.fullmatch(rf'\s*({NUM})\s*(?:-|to)\s*(<\s*=?\s*)?({NUM})\s*', text, re.I)
    if interval:
        low, high = float(interval[1]), float(interval[3])
        high_inclusive = interval[2] is None or '=' in interval[2]
        if not all(math.isfinite(v) for v in [low, high]) or low > high or (low == high and not high_inclusive):
            return None
        return {'low':low, 'high':high, 'low_inclusive':True, 'high_inclusive':high_inclusive}
    limit = re.fullmatch(rf'\s*(<=|>=|<|>)\s*({NUM})\s*', text)
    if limit:
        op, value = limit[1], float(limit[2])
        if not math.isfinite(value):
            return None
        return {'low':value if op.startswith('>') else None, 'high':value if op.startswith('<') else None, 'low_inclusive':op == '>=', 'high_inclusive':op == '<='}
    return None


def unit_key(unit):
    return re.sub(r'\s+', '', str(unit).lower().replace('μ', 'u').replace('µ', 'u'))


def transform(rule):
    return (float(rule.get('factor', 1)), float(rule.get('offset', 0))) if isinstance(rule, dict) else (float(rule), 0.0)


def convert_interval(interval, scale, offset):
    return {**interval, 'low':None if interval['low'] is None else interval['low']*scale+offset, 'high':None if interval['high'] is None else interval['high']*scale+offset}


def split_interval_unit(text, units):
    """Only strip a suffix when it is an explicitly configured unit."""
    text = str(text or '').strip()
    for u in sorted(units, key=len, reverse=True):
        if not u:
            continue
        # Allow whitespace in units while comparing their normalised spellings.
        for index in range(len(text)):
            if unit_key(text[index:]) == u:
                prefix = text[:index].strip()
                parsed = reference_range(prefix)
                if parsed:
                    return parsed, u
    return reference_range(text), ''


def entirely_below(result, reference):
    return result['high'] is not None and reference['low'] is not None and (result['high'] < reference['low'] or (result['high'] == reference['low'] and not (result['high_inclusive'] and reference['low_inclusive'])))


def contains(reference, result):
    for side in ['low', 'high']:
        bound, value = reference[side], result[side]
        if bound is None:
            continue
        if value is None or (value < bound if side == 'low' else value > bound):
            return False
        if value == bound and result[side+'_inclusive'] and not reference[side+'_inclusive']:
            return False
    return True


def classify_interval(result, reference):
    if contains(reference, result):
        return 'Within Range'
    if entirely_below(result, reference):
        return 'Below Range'
    if entirely_below(reference, result):
        return 'Above Range'
    return 'Invalid'


def observation(raw, fields, config, ranges, patient):
    name = str(path(raw, fields['name'], '') or '')
    canonical, method, confidence = resolve_test(raw, fields, config)
    original = path(raw, fields['result'])
    unit = str(path(raw, fields['unit'], '') or '').strip()
    source_range = str(path(raw, fields['range'], '') or '')
    out = {'test_name_original':name, 'test_name_canonical':canonical, 'result_text':original, 'result_value':None, 'result_low':None, 'result_high':None, 'result_interval':None, 'unit_original':unit, 'unit_canonical':None, 'range_text':source_range, 'range_low':None, 'range_high':None, 'range_low_inclusive':True, 'range_high_inclusive':True, 'range_source':None, 'normalization_method':method, 'normalization_confidence':confidence, 'analytics':'Invalid', 'issues':[], 'page':path(raw, fields.get('page', 'page_no'))}
    issues = out['issues']
    if raw.get('__ai_mapping'):
        out['ai_mapping'] = raw['__ai_mapping']
    if raw.get('__interpretation'):
        out['source_interpretation'] = raw['__interpretation']
        if raw['__interpretation']['category'] != 'test':
            issues.append('Non-test source entry retained: '+raw['__interpretation']['category'])
            return out
    if not canonical:
        issues.append('Unresolved test name; review required')
        return out
    spec = config['tests'][canonical]
    out['test_kind'] = spec['kind']
    if original is None or not str(original).strip():
        out['value_status'] = 'Missing'
        issues.append('Missing result')
        return out
    out['value_status'] = 'Present'
    if spec['kind']=='titre':
        return validate_titre(out,spec,source_range)
    if spec['kind'] in ['panel', 'narrative']:
        issues.append({'panel':'Panel or combined value requires supported component mapping; no scalar inferred', 'narrative':'Narrative finding preserved; no numeric classification', 'titre':'Titre preserved; no approved titre interpretation configured'}[spec['kind']])
        return out
    if spec['kind'] == 'qualitative':
        text = str(original).strip().lower()
        if text in spec.get('normal_values', ranges['qualitative_normal']):
            out['analytics'] = 'Within Range'
        elif text in spec.get('abnormal_values', ranges['qualitative_abnormal']):
            out['analytics'] = 'Above Range'
            issues.append('Abnormal qualitative result')
        else:
            issues.append('Unrecognised qualitative result')
        out['range_source'] = 'configured qualitative vocabulary'
        return out
    units = {unit_key(k):v for k, v in spec['units'].items()}
    parsed_original = original
    for context in spec.get('result_context_suffixes',[]):
        text = str(original)
        if text.lower().endswith(context['pattern'].lower()):
            parsed_original = text[:-len(context['pattern'])].strip()+' '+context['unit']
            out['result_context'] = context['context']
            break
    value, error = number(parsed_original)
    interval, interval_unit = split_interval_unit(parsed_original, units) if error else (None, '')
    if error and interval is None:
        issues.append(error)
        return out
    embedded = interval_unit if interval else result_unit(parsed_original)
    rule = units.get(unit_key(unit)) if unit else units.get(unit_key(embedded))
    if unit and embedded and (unit_key(embedded) not in units or transform(units[unit_key(embedded)]) != (transform(rule) if rule is not None else None)):
        issues.append('Embedded unit conflicts with source unit or is unsupported')
        return out
    if rule is None:
        issues.append('Missing, incompatible or unsupported unit for this test')
        return out
    scale, offset = transform(rule)
    if scale <= 0 or not math.isfinite(scale) or not math.isfinite(offset):
        raise ValueError('Unit conversion factor must be positive')
    out['unit_canonical'] = spec['unit']
    if interval:
        result = convert_interval(interval, scale, offset)
        out['result_interval'] = result
        out['result_low'], out['result_high'] = result['low'], result['high']
    else:
        out['result_value'] = value*scale+offset
        result = {'low':out['result_value'], 'high':out['result_value'], 'low_inclusive':True, 'high_inclusive':True}
    if any(bound is not None and not math.isfinite(bound) for bound in [result['low'],result['high']]):
        out['result_value'] = None
        out['result_interval'] = None
        out['result_low'] = out['result_high'] = None
        issues.append('Converted result is not finite')
        return out
    limits, range_unit = split_interval_unit(source_range, units)
    if range_unit and transform(units[range_unit]) != (scale, offset):
        issues.append('Reference unit conflicts with result unit')
        return out
    if limits:
        limits = convert_interval(limits, scale, offset)
        if any(bound is not None and not math.isfinite(bound) for bound in [limits['low'],limits['high']]):
            issues.append('Converted reference range is not finite')
            return out
        out['range_source'] = 'source report (not independently verified)'
    elif source_range.strip() and source_range.strip().lower() not in ['n/a', 'na']:
        issues.append('Unsupported or malformed source reference range; no fallback applied')
    elif spec.get('reference'):
        limits = {'low':spec['reference'][0], 'high':spec['reference'][1], 'low_inclusive':True, 'high_inclusive':True}
        out['range_source'] = 'MedlinePlus configured reference'
    else:
        age = patient.get('age_structured')
        if age and age['years'] >= 18:
            configured = ranges['adult_gender_ranges'].get(canonical, {}).get(patient.get('gender'))
            if configured:
                limits = {'low':configured[0], 'high':configured[1], 'low_inclusive':True, 'high_inclusive':True}
                out['range_source'] = ranges.get('gender_reference_sources',{}).get(canonical,'MedlinePlus adult demographic reference')
    if limits is None and source_range.strip().lower() in ['', 'n/a', 'na']:
        age = patient.get('age_structured')
        if age or any(r.get('all_ages') for r in ranges.get('reference_rules',[])):
            years = age['years'] + age.get('months',0)/12 + age.get('days',0)/365.25 if age else None
            for reference in ranges.get('reference_rules',[]):
                if reference['test']!=canonical or reference['unit']!=spec['unit']:
                    continue
                if not reference.get('all_ages') and (years is None or years < reference.get('min_age_years',0) or years >= reference.get('max_age_years',float('inf'))):
                    continue
                if reference.get('gender') and reference['gender']!=patient.get('gender'):
                    continue
                limits={'low':reference['low'],'high':reference['high'],'low_inclusive':reference.get('low_inclusive',True),'high_inclusive':reference.get('high_inclusive',True)}
                out['range_source']=reference['source']
                if reference.get('policy'):
                    out['reference_policy']=reference['policy']
                if reference.get('note'):
                    out['reference_note']=reference['note']
                break
    if limits:
        out.update({'range_low':limits['low'], 'range_high':limits['high'], 'range_low_inclusive':limits['low_inclusive'], 'range_high_inclusive':limits['high_inclusive']})
    plausible = spec.get('plausible')
    quality_bounds = {'low':plausible[0], 'high':plausible[1], 'low_inclusive':True, 'high_inclusive':True} if plausible else None
    if limits and quality_bounds and (entirely_below(limits,quality_bounds) or entirely_below(quality_bounds,limits)):
        issues.append('Reference interval lies outside configured plausibility bounds; source contradiction requires review')
        limits=None
    if quality_bounds and (entirely_below(result, quality_bounds) or entirely_below(quality_bounds, result)):
        out['analytics'] = 'Outlier'
        issues.append('Outside configured demonstration plausibility limits')
    elif limits:
        out['analytics'] = classify_interval(result, limits)
        if out['analytics'] == 'Invalid':
            issues.append('Result interval overlaps a reference boundary; classification is uncertain')
        elif out['analytics'] != 'Within Range':
            issues.append('Outside reference range')
    else:
        issues.append('No applicable reference range; cannot classify')
    return out


def validate_titre(out,spec,source_range):
    """Classify dilution-factor titres only with an explicit source cutoff."""
    match=re.fullmatch(r'\s*1\s*:\s*(\d+)\s*',str(out['result_text']))
    if not match or int(match[1])<=0:
        out['issues'].append('Unsupported titre format; expected 1:positive denominator')
        return out
    out['titre_denominator']=int(match[1])
    out['titre_ratio']=1/int(match[1])
    if spec.get('comparison')!='dilution_factor':
        out['issues'].append('No configured titre comparison policy')
        return out
    # Reference explicitly says less/greater than 1:N; compare dilution factors, not 1/N.
    reference=re.sub(r'1\s*:\s*(\d+)',r'\1',source_range)
    limits=reference_range(reference)
    if not limits or not re.search(r'1\s*:',source_range):
        out['issues'].append('Titre preserved; explicit source dilution reference required')
        return out
    value=float(match[1]);out['result_value']=value;out['unit_canonical']='dilution factor'
    out['range_low'],out['range_high']=limits['low'],limits['high']
    out['range_low_inclusive'],out['range_high_inclusive']=limits['low_inclusive'],limits['high_inclusive']
    out['range_source']='source titre reference (dilution factor; not independently verified)'
    out['analytics']=classify_interval({'low':value,'high':value,'low_inclusive':True,'high_inclusive':True},limits)
    if out['analytics']!='Within Range':out['issues'].append('Outside source titre reference')
    return out
