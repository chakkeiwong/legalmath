"""Retain per-item decisions while sharing an explicitly returned rationale.

This is a candidate output representation, not automatic semantic clustering.
The model chooses each item's rationale. Distinct issues may need distinct
rationales; the validator never infers equivalence from the source text.
"""
from copy import deepcopy
from jsonschema import validate
from legalmath.interpretation.assurance.bounded_context import require
from legalmath.interpretation.assurance.bounded_product import obj,array,TEXT
from .grouping import decision_schema as expanded_schema


def schema(ids):
    original=expanded_schema(ids)
    decision=deepcopy(original['properties']['decisions']['properties'][ids[0]])
    analysis=obj({'analysis_id':TEXT,'decision':{'$ref':'#/$defs/Decision'}})
    result=obj({'analyses':{**array(analysis),'minItems':1,'maxItems':len(ids)},
        'assignments':obj({identity:obj({'analysis_id':TEXT}) for identity in ids})})
    result['$defs']={'Decision':decision}
    return result


def decisions(product,value,ids,records):
    validate(value,schema(ids))
    rows=value['analyses']
    require(len({r['analysis_id'] for r in rows})==len(rows),'Duplicate rationale identity')
    table={r['analysis_id']:r['decision'] for r in rows}
    used={r['analysis_id'] for r in value['assignments'].values()}
    require(used==set(table),'Missing or unassigned rationale')
    for decision in table.values():
        product.citations(decision,records)
        require(decision['verdict']!='ACCEPT' or (decision['support'] and
            not decision['issues'] and not decision['source_gaps']),
            'Accepted rationale lacks support or retains defects')
    # Keep the explicit link as well as a copy so later review/correction can
    # identify which items share a warrant and reject just the affected items.
    return {identity:{'decision':deepcopy(table[value['assignments'][identity]['analysis_id']]),
        'analysis_id':value['assignments'][identity]['analysis_id']} for identity in ids}
