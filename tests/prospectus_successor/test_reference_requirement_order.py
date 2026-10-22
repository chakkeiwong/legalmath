"""Question-order controls use original retained question links as comparator."""
from copy import deepcopy
from pathlib import Path
import pytest
from legalmath.prospectus import reference_requirements as module
ROOT=Path(__file__).resolve().parents[2]
PREP=ROOT/'docs/implementation/prospectus-execution-authority/reviews/original-acceptance-338'

@pytest.fixture(scope='module')
def baseline():
    e=module.read(PREP/'evidence.json');d={k:module.read(ROOT/v) for k,v in e['inputs'].items()}
    p={k:module.read(ROOT/r['path']) for k,r in d['products']['products'].items()}
    return d,p,module.read(PREP/'expected.json')

@pytest.mark.parametrize('case',['source-delete','source-duplicate','source-reorder','replacement-delete','replacement-reorder'])
def test_invalid_question_order_refused(baseline,case):
    original,p,e=baseline;d=dict(original);d['answer']=deepcopy(original['answer']);a=d['answer']
    link=a['definition_dependency_review']['question_links'][0]
    if case=='source-delete':link['replaced'].pop()
    elif case=='source-duplicate':link['replaced'][1]=link['replaced'][0]
    elif case=='source-reorder':link['replaced'][0],link['replaced'][1]=link['replaced'][1],link['replaced'][0]
    elif case=='replacement-delete':link['replacement_ids'].pop()
    else:link['replacement_ids'][0],link['replacement_ids'][1]=link['replacement_ids'][1],link['replacement_ids'][0]
    a['report_sha256']=module.digest({k:v for k,v in a.items() if k!='report_sha256'})
    with pytest.raises(ValueError):module.inspect_evidence(d,p,e,ROOT)
