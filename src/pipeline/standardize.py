"""Deterministic parsing. Ambiguous source data is retained, never repaired by guessing."""
import difflib
import math
import re
from datetime import datetime


def key(value):
    return re.sub(r'[^a-z0-9+]', '', str(value).lower())


def path(data, dotted, default=None):
    if not dotted:
        return data
    for part in dotted.split('.'):
        if not isinstance(data, dict) or part not in data:
            return default
        data = data[part]
    return data


def number(raw):
    """Parse one scalar with optional H/L prefix and textual units; reject composites."""
    if raw is None or isinstance(raw, bool):
        return None, 'missing or non-numeric result'
    s = str(raw).strip()
    s = re.sub(r'(?<=\d),(?=\d{3}(?:\D|$))', '', s)
    m = re.fullmatch(r'(?:[HL]\s+)?([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)(?:\s*([a-zA-Z%µμ°º/][^,;]*))?', s)
    if not m:
        return None, 'non-scalar or non-numeric result'
    # Text suffix may include unit exponents but must not conceal another result.
    suffix = m[2] or ''
    if re.match(r'/\s*\d', suffix) or re.search(r'\d\s*[-,;]\s*\d', suffix):
        return None, 'combined result requires explicit component mapping'
    value = float(m[1])
    return (value, None) if math.isfinite(value) else (None, 'non-finite result')


def result_unit(raw):
    s = re.sub(r'(?<=\d),(?=\d{3}(?:\D|$))', '', str(raw or '').strip())
    m = re.fullmatch(r'(?:[HL]\s+)?[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?\s*(.*)', s)
    return m[1].strip() if m else ''


def normalize_name(raw, config):
    q = key(raw)
    # Remove methodology annotations only after retaining original name.
    base = key(re.split(r'\(', str(raw))[0])
    aliases = {}
    for canonical, spec in config['tests'].items():
        for alias in [canonical] + spec['aliases']:
            aliases[key(alias)] = canonical
    if q in aliases or base in aliases:
        return aliases.get(q, aliases.get(base)), 'dictionary', 1.0
    scores = sorted(((max(difflib.SequenceMatcher(None, base, a).ratio() for a in [key(n)] + [key(a) for a in spec['aliases']]), n) for n, spec in config['tests'].items()), reverse=True)
    if base and scores and scores[0][0] >= config['fuzzy_threshold'] and (len(scores) == 1 or scores[0][0]-scores[1][0] >= config['fuzzy_margin']):
        return scores[0][1], 'fuzzy', round(scores[0][0], 3)
    return None, 'unresolved', 0.0


def demographics(raw, fields):
    output = {}
    for canonical, candidates in fields.items():
        output[canonical] = next((path(raw, p) for p in candidates if path(raw, p) is not None), None)
    gender = str(output.get('gender') or '').lower()
    output['gender'] = {'m':'Male','male':'Male','f':'Female','female':'Female','other':'Other'}.get(gender)
    age = str(output.get('age') or '')
    m = re.fullmatch(r'(?:(\d+)\s*[Yy])?\s*(?:(\d+)\s*[Mm])?\s*(?:(\d+)\s*[Dd])?', age.strip())
    output['age_structured'] = {'years':int(m[1] or 0),'months':int(m[2] or 0),'days':int(m[3] or 0)} if m and age.strip() else ({'years':int(age),'months':0,'days':0} if age.isdigit() else None)
    for field in ['report_date','admission_date','discharge_date']:
        original = output.get(field)
        output[field+'_original'] = original
        output[field] = None
        for fmt in ['%d-%m-%Y','%d-%b-%Y','%Y-%m-%d','%d/%m/%Y','%d/%b/%Y','%Y-%m-%dT%H:%M:%S']:
            try:
                output[field] = datetime.strptime(str(original),fmt).isoformat()[:10]
                break
            except ValueError:
                pass
    return output


def medicine_key(name, config):
    text = re.sub(r'^(?:tab\.?|tablet|cap\.?|capsule|inj\.?|injection|syp\.?|syrup|powder)\s*', '', str(name), flags=re.I).strip()
    notes = []
    for match in list(re.finditer(r'\(([^)]*)\)',text)):
        if any(match[1].strip().lower().startswith(prefix) for prefix in config.get('normalization',{}).get('instruction_prefixes',[])):
            notes.append(match[1])
            text = text.replace(match[0],' ')
    # Normalise spelling/punctuation, but retain every product suffix and strength digit.
    text = re.sub(r'(?<=\d)\s*mg\b', '', text, flags=re.I)
    text = re.sub(r'[-_.]+',' ',text)
    return re.sub(r'\s+',' ',text).strip().lower(), notes


def medication(raw, fields, config):
    name = str(path(raw, fields['name'], '') or '')
    cleaned, instructions = medicine_key(name,config)
    form_match = re.match(r'^(inj\.?|injection|tab\.?|tablet|cap\.?|capsule|syp\.?|syrup|powder)\s+', name, re.I)
    form = {'inj':'injection','injection':'injection','tab':'tablet','tablet':'tablet','cap':'capsule','capsule':'capsule','syp':'syrup','syrup':'syrup','powder':'powder'}.get(form_match[1].lower().rstrip('.')) if form_match else None
    empty = cleaned in config.get('normalization',{}).get('empty_values',['','n/a','na'])
    product = next((p for p in config.get('products',[]) if medicine_key(p['name'],config)[0]==cleaned and (not p.get('forms') or form in p['forms'])),None)
    generic = (product['generic'] if product else None) or config['aliases'].get(cleaned) or config['brand_mappings'].get(cleaned)
    treatment = config.get('treatment_categories',{}).get(cleaned)
    return {'original':name,'normalised_name':cleaned,'generic':generic,'ingredients':product.get('ingredients',[]) if product else ([generic] if generic else []),'mapping_source':product.get('source') if product else None,'instructions':instructions,'dose':path(raw,fields['dose']),'frequency':path(raw,fields['frequency']),'status':'Not applicable' if empty else 'Mapped' if generic else 'Treatment category' if treatment else 'Unresolved','reason':treatment if treatment else None if generic or empty else 'No exact verified formulation match; retained for dictionary review'}
