"""Adverse original-inventory controls; test totals cannot accept the task."""
from copy import deepcopy
from pathlib import Path
import pytest
from legalmath.prospectus import reference_requirements as module

ROOT=Path(__file__).resolve().parents[2]
PREP=ROOT/'docs/implementation/prospectus-execution-authority/reviews/original-acceptance-338'

@pytest.fixture(scope='module')
def baseline():
    evidence=module.read(PREP/'evidence.json')
    data={k:module.read(ROOT/v) for k,v in evidence['inputs'].items()}
    products={k:module.read(ROOT/r['path']) for k,r in data['products']['products'].items()}
    return data,products,module.read(PREP/'expected.json')

def test_original_requirements_remain_partial(baseline):
    d,p,e=baseline;r=module.inspect_evidence(d,p,e,ROOT)
    for k in ('headings','reference_lines','markers','references','definitions','question_paths','gaps'):
        assert r[k]==e[k]
    assert r['task_ready'] is False and r['whole_build_complete'] is False
    assert r['external_adviser_required'] is False

@pytest.mark.parametrize('case',[
    'heading-delete','heading-duplicate','heading-quote','reference-line-delete',
    'marker-delete','marker-renumber','ledger-delete','reference-target-truncate',
    'statute-historical-promote','h43-stale','definition-use-delete',
    'definition-use-reorder','definition-uncertainty-delete','question-discovery-delete',
    'default-residual-delete','gap-delete','false-completion'])
def test_changed_evidence_refused(baseline,case):
    original,p,expected=baseline;d=dict(original);e=deepcopy(expected)
    if case.startswith('heading') or case in ('reference-line-delete','marker-delete'):
        d['inventory']=deepcopy(original['inventory']);v=d['inventory']
        if case=='heading-delete':v['headings'].pop()
        elif case=='heading-duplicate':v['headings'][1]=deepcopy(v['headings'][0])
        elif case=='heading-quote':v['headings'][0]['sources'][0]['quote']+='x'
        elif case=='reference-line-delete':v['reference_candidates'].pop()
        else:v['bracket_roles'].pop('B80')
    elif case=='marker-renumber':
        d['dispositions']=deepcopy(original['dispositions'])
        next(r for r in d['dispositions'] if r['id']=='B80')['text']='[3]'
    elif case=='ledger-delete':
        d['ledger']=deepcopy(original['ledger']);d['ledger']['records'].pop()
    elif case in ('gap-delete','false-completion'):
        if case=='gap-delete':e['gaps'].pop()
        else:e['task_ready']=True
    else:
        d['answer']=deepcopy(original['answer']);a=d['answer']
        if case=='reference-target-truncate':a['original_reference_review']['references'][0]['targets'].pop()
        elif case=='statute-historical-promote':a['statutory_references']['records'][0]['historical_validity']='PROVED'
        elif case=='h43-stale':a['publication_routes_review']['context']['current_source_available']=False
        elif case=='definition-use-delete':a['definition_remainder_review']['uses'].pop()
        elif case=='definition-use-reorder':
            u=a['definition_remainder_review']['uses'];u[1],u[2]=u[2],u[1]
        elif case=='definition-uncertainty-delete':a['definition_remainder_review']['uses'][0]['remaining']=[]
        elif case=='question-discovery-delete':a['questions']['Q1']['unresolved'].remove('definition-discovery:finite-dossier')
        else:a['residual_coverage_review']['substantive_pending'].pop()
        a['report_sha256']=module.digest({k:v for k,v in a.items() if k!='report_sha256'})
    with pytest.raises(ValueError):module.inspect_evidence(d,p,e,ROOT)

def test_source_edition_refused(baseline):
    d,p,e=baseline;p=dict(p);p['P1']=deepcopy(p['P1'])
    identity=d['inventory']['headings'][0]['sources'][0]['unit']
    next(u for u in p['P1']['payload']['graph']['units'] if u['id']==identity)['source_sha256']='0'*64
    with pytest.raises(ValueError,match='edition'):module.inspect_evidence(d,p,e,ROOT)

def test_unreviewed_manifest_refused(tmp_path):
    p=tmp_path/'evidence.json';p.write_text('{}')
    with pytest.raises(ValueError,match='Unreviewed'):module.assess(tmp_path,p.name)

def test_repository_escape_refused(tmp_path):
    with pytest.raises(ValueError,match='escapes'):module.contained(tmp_path,'../outside.json')
