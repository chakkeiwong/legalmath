"""Independently frozen source grammar and invalid context controls."""
from pathlib import Path
import gzip,json,pytest
from legalmath.prospectus.successor import reference_scope as module
from legalmath.prospectus.successor.paragraph_references import discover
from legalmath.prospectus.successor.contracts import digest
ROOT=Path(__file__).resolve().parents[2]
PREP=ROOT/'docs/implementation/prospectus-execution-authority/reviews/reference-scope-343'
EXPECTED=json.loads((PREP/'expected.json').read_text())

@pytest.mark.parametrize('case',EXPECTED['cases'],ids=lambda c:c['id'])
def test_frozen_context_grammar(case):
    candidates=discover(case['text'],text_sha256=digest(case['text'].encode()))['candidates']
    assert len(candidates)==1
    result=module.qualify(case['text'],candidates[0],[case['header']] if 'header' in case else [])
    assert result['raw']==case['raw']
    assert result['explicit_section']==case['section'] and result['statute']==case['law']
    assert result['target'] is None and result['target_resolution_established'] is False
    assert result['review_required'] is True
    assert result['issues']==([case['issue']] if 'issue' in case else [])

@pytest.mark.parametrize('change',['start','end','raw','bool-start'])
def test_changed_candidate_source_refused(change):
    text='§ 5 Absatz (2)'
    c=discover(text,text_sha256=digest(text.encode()))['candidates'][0]
    if change=='start':c['start']+=1
    elif change=='end':c['end']+=1
    elif change=='raw':c['raw']='Absatz (3)'
    else:c['start']=True
    with pytest.raises(ValueError):module.qualify(text,c)

def test_equal_paragraph_labels_do_not_resolve_target():
    for text,section in [('§ 7 Absatz (2)','7'),('§ 9 Absatz (2)','9')]:
        c=discover(text,text_sha256=digest(text.encode()))['candidates'][0]
        r=module.qualify(text,c)
        assert r['explicit_section']==section and r['target'] is None

def test_frozen_source_context_before_full_consumer():
    from scripts import prospectus_reference_scope_oracle as oracle
    authority=ROOT/'docs/implementation/prospectus-execution-authority'
    manifest=json.loads((authority/'reviews/conditional-cli-311/products.json').read_text())
    products={k:json.loads((ROOT/r['path']).read_text()) for k,r in manifest['products'].items()}
    ordinary=json.loads(gzip.decompress((authority/'attempts/basf-references/attempt-081/ordinary-answer.json.gz').read_bytes()))
    profile=json.loads((PREP/'profile.json').read_text())
    actual={**ordinary,**module.evaluate(products,ordinary,profile,ROOT,expected_profile_sha256=digest(profile))}
    actual['report_sha256']=digest({k:v for k,v in actual.items() if k!='report_sha256'})
    assert oracle.verify(actual,ordinary,products,EXPECTED)['status']=='PASS'
