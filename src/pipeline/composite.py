"""Expand explicitly configured panels; retain the complete source when parsing is uncertain."""
from copy import deepcopy
import re
from .standardize import key, normalize_name, number, path, result_unit

NUM = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)'


def assign(obj, dotted, value):
    parts = dotted.split('.')
    for part in parts[:-1]:
        obj = obj.setdefault(part, {})
    obj[parts[-1]] = value


def expand_test(raw, fields, config):
    canonical, _, _ = normalize_name(path(raw, fields['name'], ''), config)
    rule = config.get('panels', {}).get(canonical)
    text = str(path(raw, fields['result'], '') or '').strip()
    if not rule or not text:
        return [(raw, {})]
    if rule['mode'] == 'ratio_pair':
        match = re.fullmatch(rf'\s*({NUM})\s*/\s*({NUM})\s*([a-zA-Z]+)?\s*',text)
        if not match:
            return [(raw,{'expansion_error':'Paired result requires exactly systolic/diastolic values'})]
        explicit = match[3] or str(path(raw,fields['unit'],'') or '')
        if match[3] and path(raw,fields['unit']) and match[3].lower()!=str(path(raw,fields['unit'])).lower():
            return [(raw,{'expansion_error':'Conflicting blood-pressure units'})]
        children=[]
        for index,component in enumerate(rule['components']):
            child=deepcopy(raw)
            assign(child,fields['name'],component['test'])
            assign(child,fields['result'],match[index+1])
            assign(child,fields['unit'],explicit)
            assign(child,fields['range'],'')
            children.append((child,{'derived_from':{'test_name':path(raw,fields['name']),'result_text':text,'unit':explicit,'range':path(raw,fields['range']),'component_index':index,'rule':canonical},'unit_provenance':'explicit source pair unit'}))
        return children
    found = []
    spans = []
    for component in rule['components']:
        labels = '|'.join(re.escape(a) for a in sorted(component['aliases'], key=len, reverse=True))
        pattern = rf'(?:^|,\s*)(?:{labels})(?:\s*(?:-|:)\s*|\s+)({NUM})([^,]*)(?=,|$)'
        matches = list(re.finditer(pattern, text, re.I))
        if len(matches) > 1:
            return [(raw, {'expansion_error':'Duplicate component labels in combined result'})]
        if matches:
            match = matches[0]
            found.append((component, match[1]+match[2], ''))
            spans.append(match.span())
    if found:
        remainder = text
        for low, high in sorted(spans, reverse=True):
            remainder = remainder[:low] + remainder[high:]
        if remainder.strip(' ,;\t\n'):
            return [(raw, {'expansion_error':'Unmapped text or component in combined result; retained without partial splitting'})]
    elif rule['mode'] == 'named_or_ordered':
        values = text.split(rule['separator'])
        source_ranges = str(path(raw, fields['range'], '') or '').split(rule['separator'])
        if len(values) != len(rule['components']):
            return [(raw, {'expansion_error':'Combined result count does not match configured component order'})]
        if any(number(v)[1] for v in values):
            return [(raw, {'expansion_error':'Combined result contains a non-scalar component'})]
        if len(source_ranges) not in [1, len(values)] or (len(source_ranges)==1 and source_ranges[0].strip()):
            return [(raw, {'expansion_error':'Combined reference ranges do not match component count'})]
        found = [(component, value.strip(), source_ranges[i].strip() if len(source_ranges)==len(values) else '') for i, (component, value) in enumerate(zip(rule['components'], values))]
    else:
        return [(raw, {'expansion_error':'Combined panel requires explicit component labels'})]
    if not found:
        return [(raw, {})]
    if 'sum_expected' in rule:
        values = [number(v)[0] for _, v, _ in found]
        if any(v is None for v in values) or abs(sum(values)-rule['sum_expected']) > rule['sum_tolerance']:
            return [(raw, {'expansion_error':'Differential percentages do not sum to configured total'})]
    results = []
    for index, (component, value, reference) in enumerate(found):
        child = deepcopy(raw)
        explicit_unit = result_unit(value) or str(path(raw, fields['unit'], '') or '').strip()
        unit = explicit_unit
        provenance = 'source component or panel'
        if not unit and component['unit_policy'] == 'configured panel convention':
            unit = component['unit']
            provenance = 'configured named-panel convention'
        assign(child, fields['name'], component['test'])
        assign(child, fields['result'], value)
        assign(child, fields['unit'], unit)
        assign(child, fields['range'], reference)
        results.append((child, {'derived_from':{'test_name':path(raw, fields['name']), 'result_text':path(raw, fields['result']), 'unit':path(raw, fields['unit']), 'range':path(raw, fields['range']), 'component_index':index, 'rule':canonical}, 'unit_provenance':provenance}))
    return results
