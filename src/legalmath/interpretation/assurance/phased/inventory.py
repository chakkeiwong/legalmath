"""Exact structural inventory; never a model-generated legal assessment."""
from collections import Counter
from copy import deepcopy
from legalmath.canonical import digest
from legalmath.interpretation.assurance.bounded_context import require
from legalmath.interpretation.assurance.question_scope import scopes


def preserve(product):
    route=product.route
    route.check()
    require(route.reconstruct()==route.envelope,'Inventory reconstruction differs')
    records=[]
    for record in route.records.values():
        if record['kind']=='source':continue
        row={'record':deepcopy(record),'record_hash':digest(record)}
        if record['kind'] in ('obligation','reading','case'):
            row['required_question_ids']=list(product.requirement_questions(record))
            row['substantive_account_required']=True
        else:
            require(record['kind']=='metadata','Unknown inventory kind')
            row['substantive_account_required']=False
        records.append(row)
    if getattr(product, 'capacity_manager', None) is not None:
        from .evidence_store import save_exact
        save_exact(product.directory / 'inventory-capacity.json',
            product.capacity_manager.native('metadata-inventory', {}, records))
    return {'profile':'exact-product-inventory.v2','status':'INVENTORY_PRESERVED',
        'input_hash':route.input_hash,'store_hash':route.store_hash,
        'records':records,'counts':dict(Counter(r['record']['kind'] for r in records)),
        'question_scope':scopes(route.envelope),
        'source_qualification':deepcopy(route.envelope['source_qualification']),
        'original_questions':deepcopy(route.envelope['original_questions']),
        'source_packet_hash':digest(route.envelope['source_packet']),
        'provider_calls':0,'legal_analysis_performed':False,
        'scope':'Exact inventory only. Original requirements still require source-grounded accounts.'}


def verify(product,value):
    require(value==preserve(product),'Inventory or authoritative input changed','E_INTEGRITY')
    return True


def require_complete_accounts(product,value,details,qid):
    verify(product,value)
    expected={r['record']['id'] for r in value['records']
        if r['substantive_account_required'] and qid in r['required_question_ids']}
    actual=[r['id'] for r in details]
    require(len(actual)==len(set(actual)) and set(actual)==expected,
        'Substantive requirement account population differs','E_INTEGRITY')
    require(all(r.get('result',{}).get('status')=='VALIDATED' and
        isinstance(r['result'].get('value'),dict) for r in details),
        'Inventory cannot replace source-grounded requirement accounts','E_DEPENDENCY')
    return True
