from copy import deepcopy
from types import SimpleNamespace
import pytest
from legalmath.canonical import canonical, digest, loads, raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.composition import compose, execute
from legalmath.ir.evaluate import evaluate
from .support import packet, reading, inventory, fidelity
from tests.search.test_formal import AT


def fixture():
    p = packet(); p['units'].append({**deepcopy(p['units'][0]),'unit_id':'p2',
        'text':'A distributor must disclose charges when selling a fund.'})
    claims = inventory()['claims']; disclosure = deepcopy(claims[0])
    disclosure.update(claim_id='disclose',kind='OBLIGATION',modality='MUST',action='disclose charges',
        conditions=['when selling a fund'],exceptions=[],statement=p['units'][1]['text'],
        evidence=[{'unit_id':'p2','quote':p['units'][1]['text']}])
    claims.append(disclosure)
    r = reading(); r.update(local_id='disclosure',statement='[TRUE_IS_COMPLIANT] Required disclosure is present.',
                            citations=disclosure['evidence'])
    r['formalization']={'scope':'selling','result':'disclosed','result_type':'bool','facts':[
        {'name':name,'type':'bool','meaning':meaning,'unit':'truth value','source_unit_ids':['p2'],
         'requires_judgment':False} for name,meaning in [('selling','A fund is sold'),('disclosed','Charges are disclosed')]]}
    candidates={'gift.correct':reading(),'gift.rival':reading(True),'disclosure':r}
    matrix=fidelity(claims,candidates)
    for row in matrix['checks']:
        supported=(row['claim_id']=='gift') == (row['candidate_id']!='disclosure')
        if row['candidate_id']=='gift.rival': supported=False
        if not supported:row.update(label='NOT_ESTABLISHED',representation_quotes=[],failing_stage='FORMALIZATION',
                                     question='Missing claim in this selected control')
    spec={'version':'composition.v1','source_packet_hash':digest(p),'claims_hash':digest(claims),
        'candidates_hash':digest(candidates),'components':[
            {'component_id':'gifts','question':'Is the gift prohibited?','claim_ids':['gift'],
             'candidate_ids':['gift.correct','gift.rival'],'output_meaning':'TRUE_IS_PROHIBITED','assignment_basis':'Explicit fixture grouping'},
            {'component_id':'disclosure','question':'Were required charges disclosed?','claim_ids':['disclose'],
             'candidate_ids':['disclosure'],'output_meaning':'TRUE_IS_COMPLIANT','assignment_basis':'Distinct fixture obligation'}],
        'excluded_candidates':[],'max_combinations':16}
    return p,claims,candidates,matrix,spec


def run(data, **kwargs):
    p,claims,candidates,matrix,spec=data
    return compose(spec,p,claims,candidates,matrix,AT,**kwargs)


def test_complementary_obligation_is_not_a_missing_gift_claim():
    data=fixture(); result=run(data)
    assert result['total_combinations']==2 and len(result['combinations'])==2
    assert result['findings']==[{'kind':'COMPONENT_SUPPORT_UNRESOLVED','component_id':'gifts','candidate_id':'gift.rival'}]
    assert all(len(c['bundle']['rules'])==2 for c in result['combinations'])
    assert result['components'][0]['source_claims'][0]['exceptions']==['a discount of fees or charges']
    assert result['components'][1]['source_claims'][0]['modality']=='MUST'
    assert not result['release_eligible'] and not result['component_compatibility_proved']


def test_missing_claim_unassigned_reading_and_limit_are_visible():
    data=fixture();spec=data[-1];spec['components']=spec['components'][:1];spec['max_combinations']=1
    result=run(data);kinds={f['kind'] for f in result['findings']}
    assert {'UNCOVERED_SOURCE_CLAIM','UNASSIGNED_CANDIDATE','COMBINATION_LIMIT'}<=kinds
    assert result['deferred_combinations']==1 and result['status']=='INCOMPLETE'


@pytest.mark.parametrize('mutation',['stale','duplicate','opposite','unknown','claimed_context','type','exclusion'])
def test_bad_assignments_cannot_create_coverage(mutation):
    data=fixture();p,claims,candidates,matrix,spec=data
    if mutation=='stale':p['selected_slice']='changed'
    if mutation=='duplicate':spec['components'][1]['candidate_ids']=['gift.correct']
    if mutation=='opposite':spec['components'][0]['output_meaning']='TRUE_IS_COMPLIANT'
    if mutation=='unknown':spec['components'][0]['claim_ids']=['invented']
    if mutation=='claimed_context':
        claims[0]['relevance']='CONTEXT';spec['claims_hash']=digest(claims)
    if mutation=='type':spec['components'][0]['output_meaning']='VALUE'
    if mutation=='exclusion':spec['excluded_candidates']=[{'candidate_id':'gift.correct','reason':'silently exclude selected reading'}]
    with pytest.raises(LegalMathError):run(data)


def test_explicit_exclusion_and_unformalisable_component_preserved():
    data=fixture();spec=data[-1]
    spec['components'][0]['candidate_ids']=['gift.correct']
    spec['excluded_candidates']=[{'candidate_id':'gift.rival','reason':'Developer-selected fixture; no legal elimination'}]
    assert run(data)['status']=='DECLARED_COVERAGE_ACCOUNTED'
    data[2]['disclosure']['formalization']=None;spec['candidates_hash']=digest(data[2]);data=list(data);data[3]=None
    result=run(data)
    assert result['combinations'][0]['status']=='UNSUPPORTED_COMPONENT'
    assert result['status']=='INCOMPLETE' and result['excluded_candidates']==spec['excluded_candidates']


def test_vector_java_preserves_scope_unknown_conflict_exception_and_both_outputs(root,tmp_path):
    data=fixture();result=run(data,jdk=root/'.localresources/java-toolchain/jdk-17.0.20.1+1',out=tmp_path/'java')
    states=set()
    for alternative in result['combinations']:
        assert alternative['status']=='JAVA_VECTOR_CONFORMANCE'
        path=alternative['build']['jar']; rows=loads((__import__('pathlib').Path(path).parent/'verification-results.json').read_bytes())
        states.update(row['java']['status'] for row in rows)
        assert alternative['verification']['passed']
    assert {'TRUE','FALSE','UNKNOWN','CONFLICT','OUT_OF_SCOPE'}<=states
    compiled=result['combinations'][0]['bundle']
    facts={name:{'type':'bool','status':'known','value':value,'evidence_ids':['test'],
           'valid_from':AT,'valid_until':None,'recorded_at':AT} for name,value in
           [('c0.gift',True),('c0.discount',True),('c1.selling',True),('c1.disclosed',False)]}
    snapshot={'subject_id':'fund','facts':facts}
    assert evaluate(compiled,snapshot,'c0.selected.control',AT,AT)['status']=='FALSE'
    assert evaluate(compiled,snapshot,'c1.selected.control',AT,AT)['status']=='FALSE'
    with pytest.raises(LegalMathError):run(data,jdk=root/'.localresources/java-toolchain/jdk-17.0.20.1+1',out=tmp_path/'java')


def test_command_rejects_tampering_and_incomplete_final_universe(tmp_path):
    p,claims,candidates,matrix,spec=fixture(); source=tmp_path/'investigation';source.mkdir()
    records={'packet.json':p,'claims.json':claims,'candidates.json':candidates,
        'search-state.json':{'nodes':[]},'request.json':{'at':AT},
        'report.json':{'candidate_ids':list(candidates),'fidelity':matrix,'status':'UNRESOLVED'}}
    for name,value in records.items():(source/name).write_bytes(canonical(value))
    (source/'manifest.json').write_bytes(canonical({'files':{name:raw_digest((source/name).read_bytes()) for name in records}}))
    specpath=tmp_path/'spec.json';specpath.write_bytes(canonical(spec))
    args=SimpleNamespace(investigation=source,spec=specpath,jdk=None,out=None)
    assert execute(args)['total_combinations']==2
    (source/'claims.json').write_text('[]')
    with pytest.raises(LegalMathError):execute(args)
