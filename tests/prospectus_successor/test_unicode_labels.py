from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pytest
from legalmath.prospectus.successor.unicode_labels import discover
from legalmath.prospectus.successor.definition_discovery import discover as legacy
from scripts.prospectus_unicode_oracle import verify

ROOT=Path(__file__).resolve().parents[2]
PREP=ROOT/'docs/implementation/prospectus-execution-authority/reviews/unicode-labels-322'
CASES=json.loads((PREP/'cases.json').read_text())['cases']


def request(case):
    return {k:deepcopy(case[k]) for k in ('text','text_sha256','language','regions','quotation_convention')}


@pytest.mark.parametrize('case',CASES,ids=lambda r:r['id'])
def test_frozen_source_and_grammar_cases(case):
    verify(case,discover(request(case)))


def test_legacy_source_misses_are_preserved():
    baseline=json.loads((PREP/'baseline.json').read_text())
    for case in CASES[:2]:
        r=request(case);r.pop('quotation_convention')
        old=legacy(r)
        assert {k:old[k] for k in ('names','uses','issues')}=={k:baseline[case['id']][k] for k in ('names','uses','issues')}


def test_page_header_is_not_silently_removed():
    result=discover(request(CASES[0]))
    contaminated=next(n for n in result['names'] if n['label'].startswith('Ordem dos'))
    assert 'Annual Report BES Group 190' in contaminated['label']
    assert contaminated['raw']=='Ordem dos\nAnnual Report BES Group\n190 Revisores Oficiais de Contas'


def test_quote_does_not_become_definition_or_authority():
    result=discover(request(CASES[1]))
    assert result['names'][0]['label']=='gross capital inflow'
    assert result['scope_admitted'] is False and result['meaning_admitted'] is False
    assert all(r['governing_scope'] is None for r in result['uses'])


@pytest.mark.parametrize('kind',('identity','partition','convention','selection-type','unknown-field','duplicate-region'))
def test_malformed_requests_are_refused(kind):
    r=request(CASES[2])
    if kind=='identity':r['text']+='x'
    elif kind=='partition':r['regions'][0]['start']=1
    elif kind=='convention':r['quotation_convention']='guess'
    elif kind=='selection-type':r['regions'][0]['selected']=1
    elif kind=='unknown-field':r['scope_admitted']=True
    else:r['regions'].append(deepcopy(r['regions'][0]))
    with pytest.raises(ValueError):discover(r)


@pytest.mark.parametrize('text,error',(
    ('a'*100001,'source size'),
    ('“A” '*2049,'candidate bound'),
    ('“A”'+' A'*20000,'use bound'),
))
def test_resource_bounds(text,error):
    r={'text':text,'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'language':'en',
        'quotation_convention':'english','regions':[{'id':'all','start':0,'end':len(text),'selected':True,'language':'en'}]}
    with pytest.raises(ValueError,match=error):discover(r)
