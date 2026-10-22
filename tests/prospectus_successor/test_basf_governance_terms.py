"""Governance conditions remain source rules rather than findings of validity."""
import pytest
from legalmath.prospectus.successor import service, source_graph
from legalmath.prospectus.successor.basf_governance_terms import RULES, REFERENCES
from legalmath.prospectus.successor.contracts import VERSION, digest

TIME = '2026-01-01T00:00:00Z'


def request(tmp_path):
    path = tmp_path / 'governance.txt'
    path.write_text('\f'.join(rule['reading'] for rule in RULES.values()))
    bundle = {'instrument_id':'synthetic','purpose':'review','issue_date':TIME,
        'effective_at':TIME,'known_at':TIME,'dependencies':[],
        'documents':[{'id':'d','path':str(path),'sha256':digest(path.read_bytes()),
                      'format':'text','language':'en','authority':'Synthetic development source',
                      'document_date':TIME,'known_from':TIME}]}
    graph = source_graph.build(bundle, tmp_path)
    nodes, operations = [], []
    for (kind,rule),unit in zip(RULES.items(),graph['units']):
        operations.append({'unit':unit['id'],'role':'OPERATIVE','reason':'Explicit synthetic governance scope',
                           'source_text_sha256':unit['text_sha256'],'context':'whole'})
        nodes.append({'id':'basf-governance:' + kind,'units':[unit['id']],
            'spans':[{'unit':unit['id'],'start':0,'end':len(unit['raw'])}], 'quote':unit['raw'],
            'effect':'basf_governance_terms','governance_kind':kind,'legal_reading':rule['reading'],
            'rule_scope':rule['scope'],'actor':rule['actor'],'affected':'holder','modality':'statement',
            'election':'none','assets':[],'role':'OPERATIVE','polarity':True,'questions':['Q1','Q2'],
            'conditions':[],'exceptions':[],
            'references':[{'kind':'reference','target':target,'reason':'Required source dependency'}
                          for target in REFERENCES.get(kind,[])]})
    return {'version':VERSION,'bundle':bundle,'assembly':{'operations':operations},
            'clauses':nodes,'scope':{'Q1':{'complete':False},'Q2':{'complete':False}}}


def current(data,root):
    p1 = service.source_product(data,root)
    p2 = service.construction_product(p1,root)
    p3 = service.interpretation_product(p1,p2)
    p4,p5 = service.law_product(p1,p3),service.financial_product(p1,p2,p3)
    return service.consume(dict(P1=p1,P2=p2,P3=p3,P4=p4,P5=p5),root,mode='current')


def test_original_qualifications_reach_answer_without_actual_validity(tmp_path):
    answer = current(request(tmp_path),tmp_path)
    rows = {r['kind']:r for r in answer['basf_governance_terms']}
    assert len(rows) == 20
    assert all('(' + k + ')' in rows['substitution']['reading'] for k in 'abcde')
    assert 'both' in rows['simple_majority']['reading']
    assert 'participating' in rows['qualified_majority']['reading']
    assert 'expressly consent' in rows['unequal_treatment']['reading']
    assert 'non-exclusive' in rows['jurisdiction']['reading']
    assert 'English translation is nonbinding' in rows['language']['reading']
    assert 'delivering evidence' in rows['participation_proof']['reading']
    for row in rows.values():
        assert ' '.join(''.join(s['quote'] for s in g['sources']) for g in row['source_spans']) == row['quote']
        assert row['actual_substitution_vote_or_amendment'] == row['historical_law_applicability'] == 'NOT_ESTABLISHED'
    assert answer['questions']['Q1']['status'] == answer['questions']['Q2']['status'] == 'UNKNOWN'
    assert not answer['may_execute_transaction'] and not answer['independent_legal_acceptance']


@pytest.mark.parametrize('field,value', [
    ('actor','holder'),('affected','issuer'),('election','issuer'),('assets',['principal']),
    ('role','UNKNOWN'),('polarity',False),('modality','performed'),('conditions',['vote']),
    ('exceptions',['consent']),('governance_kind','effective_vote'),('legal_reading','The vote is valid.'),
    ('rule_scope','UNCONDITIONAL'),('actual_vote',True),('effective_amendment',True),
    ('computed_majority',0.75),('appointed_representative',True),('independent_legal_acceptance',True),
])
def test_changed_conditions_and_asserted_events_refused(tmp_path,field,value):
    data = request(tmp_path)
    data['clauses'][0][field] = value
    with pytest.raises(ValueError):
        current(data,tmp_path)


@pytest.mark.parametrize('change',['quote','start','end','excluded'])
def test_changed_source_refused(tmp_path,change):
    data = request(tmp_path)
    node = data['clauses'][0]
    if change == 'quote':
        node['quote'] = 'Different source words.'
    elif change == 'start':
        node['spans'][0]['start'] = 1
    elif change == 'end':
        node['spans'][0]['end'] += 1
    else:
        data['assembly']['operations'][0]['role'] = 'EXCLUDED'
    with pytest.raises(ValueError):
        current(data,tmp_path)


@pytest.mark.parametrize('kind',list(REFERENCES))
def test_required_dependency_retained(tmp_path,kind):
    data = request(tmp_path)
    next(n for n in data['clauses'] if n['governance_kind'] == kind)['references'].pop()
    with pytest.raises(ValueError,match='dependencies'):
        current(data,tmp_path)


def test_missing_unequal_treatment_protection_remains_unknown(tmp_path):
    data = request(tmp_path)
    before = current(data,tmp_path)
    removed = next(n for n in data['clauses'] if n['governance_kind'] == 'unequal_treatment')
    data['clauses'].remove(removed)
    after = current(data,tmp_path)
    assert after['basf_governance_terms'] == [r for r in before['basf_governance_terms'] if r['kind'] != 'unequal_treatment']
    assert removed['units'][0] in after['questions']['Q1']['unresolved']
