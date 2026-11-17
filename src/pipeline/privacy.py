"""Explicit masked response mode; immutable raw evidence remains in local storage."""
from copy import deepcopy


def masked_output(output):
    value=deepcopy(output)
    value['patient']={'name':'[MASKED]','age':None,'gender':None,'age_structured':None}
    value['document_id']='[MASKED]'
    value['metadata']={}
    value['clinical_summary']={'masked':True}
    value['lineage']={'ingested_at':output.get('lineage',{}).get('ingested_at'),'processed_at':output.get('lineage',{}).get('processed_at')}
    if value.get('source_coverage'):
        value['source_coverage']['unresolved_names']={}
        value['source_coverage']['non_test_names']={}
    for observation in value.get('observations',[]):
        observation.pop('ai_mapping', None)
        for key in ['test_name_original','result_text','range_text','unit_original']:
            observation[key]='[MASKED SOURCE TEXT]'
        if observation.get('derived_from'):
            observation['derived_from']={'rule':observation['derived_from'].get('rule'),'test_name':observation['derived_from'].get('rule'),'result_text':'[MASKED SOURCE TEXT]'}
    for medicine in value.get('medications',[]):
        medicine['original']='[MASKED SOURCE TEXT]'
        medicine['normalised_name']='[MASKED SOURCE TEXT]'
        medicine['dose']=medicine['frequency']=None
        medicine['instructions']=[]
    return value


def masked_record(detail):
    value=deepcopy(detail)
    value['raw']={'masked':True,'message':'Raw medical source is hidden in masked mode.'}
    value['source']='[MASKED SOURCE LOCATION]'
    value['output']=masked_output(value['output'])
    for previous in value.get('versions',[]):
        previous['output']=masked_output(previous['output'])
    return value
