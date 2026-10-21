"""Authenticate completed preparation without reconstructing paid model requests."""
from copy import deepcopy
from legalmath.canonical import digest
from ..bounded_context import require
from ..integration_contract import read_evidence
from . import synthesis

PROFILE = 'complete-preparation-checkpoint.v1'


def load(product, reference):
    value = read_evidence(reference, product.root)
    require(value['profile'] == PROFILE and value['input_hash'] == product.route.input_hash,
        'Prepared checkpoint has a different input', 'E_INTEGRITY')
    require(read_evidence(value['source_store'],product.root) == product.route.records,
        'Prepared source records changed', 'E_INTEGRITY')
    result = read_evidence(value['result'],product.root)
    require(result['input_hash'] == product.route.input_hash and result['preparation_only'] is True,
        'Checkpoint is not original preparation', 'E_INTEGRITY')
    q = value['question']
    require(result['answers'][q]['status'] == 'PREPARED'
        and q in product.active_questions, 'Question has no prepared finding', 'E_DEPENDENCY')
    details = read_evidence(value['details'],product.root)
    require(all(r['result']['status']=='VALIDATED' for r in details), 'Incomplete retained accounts')
    journal = read_evidence(value['journal'],product.root)
    require(journal['input_hash']==product.route.input_hash and set(journal['calls'])==set(value['call_results']),
        'Prepared dispatch population changed', 'E_INTEGRITY')
    for key,row in journal['calls'].items():
        saved=read_evidence(value['call_results'][key],product.root)
        require(row['status']==saved['status'] and digest(saved)==row['result_hash'],
            'Prepared dispatch result changed', 'E_INTEGRITY')
        optional_failure = key in ('candidates-'+q, 'criticism-'+q) and saved['status']=='FAILED' \
            and saved.get('error') not in ('E_AUTHORITY', 'E_INTEGRITY')
        require(saved['status']=='VALIDATED' or optional_failure,
            'Prepared checkpoint has an incomplete required call', 'E_INTEGRITY')
    return value, result['answers'][q], details


def findings(product, qid, question, checkpoint):
    value, answer, details = checkpoint
    require(qid==value['question'], 'Prepared checkpoint question mismatch', 'E_INTEGRITY')
    rows, receipt = synthesis.prepare(product,qid,product.retained_acquisition,details)
    require(receipt==read_evidence(value['representation'],product.root),
        'Prepared synthesis origin changed', 'E_INTEGRITY')
    for level in value['levels']:
        membership=read_evidence(level['membership'],product.root)
        require(membership['input_hashes']=={r['id']:digest(r) for r in rows},
            'Prepared synthesis input membership changed','E_INTEGRITY')
        groups=membership['groups']
        ids=[key for group in groups for key in group]
        require(len(ids)==len(set(ids)) and set(ids)=={r['id'] for r in rows},
            'Prepared synthesis lost input members','E_INTEGRITY')
        after=read_evidence(level['result'],product.root)
        require(len(after)==len(groups),'Prepared synthesis group count changed','E_INTEGRITY')
        before={r['id']:r for r in rows}
        for output,group in zip(after,groups):
            if len(group)==1 and output==before[group[0]]:
                continue
            require(output['children']==group and output['id'] in value['call_results'],
                'Prepared synthesis lineage changed','E_INTEGRITY')
            saved=read_evidence(value['call_results'][output['id']],product.root)
            require(output['value']==saved['value'],'Prepared synthesis value changed','E_INTEGRITY')
            product.citations(output['value'],product.source_records(output['value']))
        rows=after
    require(rows==answer['findings'] and len(rows)==1,
        'Prepared final finding differs from completed synthesis','E_INTEGRITY')
    return deepcopy(rows)
