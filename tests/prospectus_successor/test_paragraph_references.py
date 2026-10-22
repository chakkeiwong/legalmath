"""Frozen source and adverse syntax checks for literal paragraph discovery."""
from pathlib import Path
import json,pytest
from legalmath.prospectus.successor import paragraph_references as module
from legalmath.prospectus.successor.contracts import digest
ROOT=Path(__file__).resolve().parents[2]
PREP=ROOT/'docs/implementation/prospectus-execution-authority/reviews/paragraph-discovery-342'
EXPECTED=json.loads((PREP/'expected.json').read_text())

@pytest.mark.parametrize('case',EXPECTED['cases'],ids=lambda c:c['id'])
def test_frozen_grammar(case):
    result=module.discover(case['text'],text_sha256=digest(case['text'].encode()))
    if case.get('absent'):assert result['candidates']==[] and result['issues']==[]
    elif 'issue' in case:
        assert any(r['kind']==case['issue'] for r in result['issues'])
        assert not any(r['syntax_complete'] for r in result['candidates'])
    else:
        assert result['issues']==[] and len(result['candidates'])==1
        row=result['candidates'][0]
        assert all(row[k]==case[k] for k in ('raw','paths','connectors'))
        assert row['syntax_complete'] is True and row['target'] is None and row['review_required'] is True
        assert case['text'][row['start']:row['end']]==case['raw']

def test_complete_frozen_source_inventory():
    manifest=json.loads((ROOT/'docs/implementation/prospectus-execution-authority/reviews/conditional-cli-311/products.json').read_text())
    p2=json.loads((ROOT/manifest['products']['P2']['path']).read_text());text=p2['payload']['assembly']['continuous_text']
    result=module.discover(text,text_sha256=digest(text.encode()))
    assert [{k:r[k] for k in ('start','end','raw','paths','connectors')} for r in result['candidates']]==EXPECTED['source_expressions']
    assert result['issues']==[] and all(r['syntax_complete'] for r in result['candidates'])

@pytest.mark.parametrize('text,checksum',[('',digest(b'')),('a'*100001,digest(b'a'*100001)),('Absatz (1)','0'*64),(None,'0'*64)])
def test_invalid_input_refused(text,checksum):
    with pytest.raises(ValueError):module.discover(text,text_sha256=checksum)

def test_component_bound_refused():
    text='Absatz '+'(1)'*65
    with pytest.raises(ValueError,match='component'):module.discover(text,text_sha256=digest(text.encode()))

def test_candidate_bound_refused():
    text='Absatz (1). '*2049
    with pytest.raises(ValueError,match='candidate'):module.discover(text,text_sha256=digest(text.encode()))
