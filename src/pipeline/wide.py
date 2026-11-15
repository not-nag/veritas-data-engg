"""Generate a relational wide view without dropping repeated test observations."""
import hashlib
import json


def literal(value):
    return "'"+str(value).replace("'","''")+"'"


def identifier(value):
    return '"'+str(value).replace('"','""')+'"'


def interval_expression(prefix):
    low=f"json_extract(output_json,'$.{prefix}_low')"
    high=f"json_extract(output_json,'$.{prefix}_high')"
    if prefix=='result':
        low="json_extract(output_json,'$.result_interval.low')"
        high="json_extract(output_json,'$.result_interval.high')"
        low_inc="json_extract(output_json,'$.result_interval.low_inclusive')"
        high_inc="json_extract(output_json,'$.result_interval.high_inclusive')"
    else:
        low_inc="coalesce(json_extract(output_json,'$.range_low_inclusive'),1)"
        high_inc="coalesce(json_extract(output_json,'$.range_high_inclusive'),1)"
    return f"CASE WHEN {low} IS NULL THEN (CASE WHEN {high_inc} THEN '<=' ELSE '<' END)||{high} WHEN {high} IS NULL THEN (CASE WHEN {low_inc} THEN '>=' ELSE '>' END)||{low} ELSE (CASE WHEN {low_inc} THEN '[' ELSE '(' END)||{low}||', '||{high}||(CASE WHEN {high_inc} THEN ']' ELSE ')' END) END"


def ensure_wide_view(connection,tests):
    names=list(tests['tests'])
    signature=hashlib.sha256(json.dumps({'names':names,'view_version':1}).encode()).hexdigest()
    stored=connection.execute("SELECT value FROM settings WHERE name='wide_view_signature'").fetchone()
    if stored and stored[0]==signature:
        return
    if len(names)>350:
        raise ValueError('SQLite wide view supports up to 350 configured entries in this prototype')
    result=f"CASE WHEN result_value IS NOT NULL AND unit_canonical IS NOT NULL THEN result_value WHEN json_extract(output_json,'$.result_interval') IS NOT NULL THEN {interval_expression('result')} ELSE result_text END"
    reference=f"CASE WHEN range_low IS NOT NULL OR range_high IS NOT NULL THEN {interval_expression('range')} ELSE range_text END"
    fields=[]
    for name in names:
        for suffix,expression in [('', 'canonical'),('_Result',result),('_Range',reference),('_Unit','coalesce(unit_canonical,unit_original)'),('_Analytics','analytics')]:
            fields.append(f'MAX(CASE WHEN canonical={literal(name)} THEN {expression} END) AS {identifier(name+suffix)}')
    query='''WITH ranked AS (
        SELECT *,row_number() OVER (PARTITION BY record_id,canonical ORDER BY CAST(substr(id,66) AS INTEGER)) occurrence_index
        FROM observations WHERE canonical IS NOT NULL
    ), positions AS (
        SELECT record_id,occurrence_index FROM ranked GROUP BY record_id,occurrence_index
        UNION SELECT r.id,1 FROM records r WHERE NOT EXISTS(SELECT 1 FROM ranked o WHERE o.record_id=r.id)
    ) SELECT r.id record_id,r.document_id,r.clinic,r.record_type,p.occurrence_index,'''+','.join(fields)+'''
        FROM positions p JOIN records r ON r.id=p.record_id
        LEFT JOIN ranked o ON o.record_id=p.record_id AND o.occurrence_index=p.occurrence_index
        GROUP BY r.id,p.occurrence_index'''
    connection.execute('DROP VIEW IF EXISTS canonical_wide')
    connection.execute('CREATE VIEW canonical_wide AS '+query.replace('json_extract(output_json','json_extract(o.output_json'))
    connection.execute("INSERT OR REPLACE INTO settings VALUES('wide_view_signature',?)",(signature,))
