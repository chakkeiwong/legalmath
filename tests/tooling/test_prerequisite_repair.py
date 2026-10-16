from copy import deepcopy
from pathlib import Path
import json
import pytest

from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_provider import CampaignAllowance, BoundedCodexProvider
from legalmath.interpretation.search.providers import TerminalServiceFailure, CodexProvider
from legalmath.interpretation.search.models import Settings
from scripts.legal_mission_execution import save,ref
from scripts.legal_integration_prerequisites import POLICY
from scripts.legal_integration_source_ownership import normalized,paragraph_text,TAG
from xml.etree import ElementTree as ET


def test_source_normalization_preserves_material_digits_and_signs():
    assert normalized('clause 7.3.1\n')=='clause7.3.1'
    assert normalized('USD -2108.149557')!='USD2108.149557'
    assert normalized('13/1/2018')!=normalized('13/1/2019')
    p=ET.Element(TAG+'p');r=ET.SubElement(p,TAG+'r');ET.SubElement(r,TAG+'t').text='7.3.1'
    ET.SubElement(r,TAG+'footnoteReference',{TAG+'id':'30'})
    ET.SubElement(r,TAG+'t').text=' applies.'
    assert paragraph_text(p,{'30':'30'})=='7.3.130 applies.'


def test_new_recovery_policy_is_bound_and_finite(tmp_path):
    import hashlib
    stage=tmp_path/'stages/semantic-preflight/stage.json'
    save(stage,{'name':'semantic-preflight','terminal_recovery_maximum':12,'terminal_recovery_policy':POLICY})
    save(tmp_path/'current-stage.json',ref(tmp_path,stage))
    save(tmp_path/'current-binding.json',{'terminal_recovery_policy':POLICY})
    allowance=CampaignAllowance(tmp_path,{},root=tmp_path)
    def failed(slot):
        rh=digest({'slot':slot});e=tmp_path/'provider-evidence'/f'{slot:04}-{rh[:16]}'
        e.mkdir(parents=True);events=json.dumps({'type':'error','message':'stream disconnected before completion'})+'\n'
        (e/'events.jsonl').write_text(events)
        save(e/'manifest.json',{'allowance_slot':slot,'request_hash':rh,'complete_output_present':False,
            'files':{'events.jsonl':{'retained_sha256':hashlib.sha256(events.encode()).hexdigest()}}})
        return TerminalServiceFailure('stream disconnected before completion',allowance_slot=slot,request_hash=rh)
    assert allowance.terminal_recovery_attempts()==1
    for slot in range(1,13):assert allowance.reserve_terminal_recovery(failed(slot))==slot
    with pytest.raises(LegalMathError):allowance.reserve_terminal_recovery(failed(13))
    assert len(json.loads((stage.parent/'terminal-recovery.json').read_text())['charges'])==12
    save(tmp_path/'current-binding.json',{'terminal_recovery_policy':{**POLICY,'maximum_replacements':13}})
    with pytest.raises(LegalMathError):allowance.reserve_terminal_recovery(failed(14))


def test_one_replacement_per_logical_request_even_after_second_terminal_failure(tmp_path,monkeypatch):
    from types import SimpleNamespace
    provider=object.__new__(BoundedCodexProvider);calls=[]
    provider.check=lambda:None;provider.measure=lambda *a:{};provider.encode=list
    provider.limits=SimpleNamespace(output_tokens=1000)
    provider.allowance=SimpleNamespace(expected=None,terminal_recovery_enabled=lambda:True,
        terminal_recovery_attempts=lambda:1,reserve_terminal_recovery=lambda failure:calls.append('replacement'))
    def respond(self,request,schema,settings):
        calls.append('call')
        raise TerminalServiceFailure('stream disconnected before completion',allowance_slot=len(calls),request_hash=digest(request))
    monkeypatch.setattr(CodexProvider,'complete',respond)
    with pytest.raises(TerminalServiceFailure):provider.complete({'x':1},{},Settings())
    assert calls==['call','replacement','call']


def test_preserved_tables_and_repeated_body_text_pass_full_comparison(tmp_path):
    from scripts.legal_integration_source_ownership import judgment_fidelity, ROOT
    output=ROOT/'artifacts/legal-mission-control/2026-10-14/prerequisite-repair/test-source'
    for name in ('gatecoin-2023','gatecoin-2025'):
        result=judgment_fidelity(name,output/name)
        assert result['_node_status']=='SUCCEEDED'
        assert result['components_verified']==result['components_total']
        evidence=json.loads((output/name/'ownership.json').read_text())
        assert all(t['qualified'] for t in evidence['tables'])
        assert all(r['owner'] for r in evidence['full_components'] if r['container']=='table')
        assert all(r['owners'] for r in evidence['full_footnotes'])
        table_notes=[o for r in evidence['full_footnotes'] for o in r['owners'] if o['container']=='table']
        assert len(table_notes)==(1 if name=='gatecoin-2023' else 2)
        assert all(o['main_owner']==('P24' if name=='gatecoin-2023' else 'P52') for o in table_notes)


def test_complete_handbook_supplement_preserves_original_items_and_closes_edges():
    from scripts.legal_integration_prerequisites import SOURCE,ROOT
    from scripts.legal_integration_accounts import SOURCE as old
    from scripts.legal_integration_source_ownership import handbook_fidelity
    new=json.loads((ROOT/SOURCE).read_text()); prior=json.loads((ROOT/old).read_text())
    assert new['original_questions']==prior['original_questions']
    for f in ('acceptance_obligations','original_readings','cases'):
        assert new['answer_acceptance'][f]==prior['answer_acceptance'][f]
    assert len(new['source_packet']['units'])==99
    result=handbook_fidelity(new,ROOT/'artifacts/legal-mission-control/2026-10-14/prerequisite-repair/test-source/handbook')
    assert result['_node_status']=='SUCCEEDED' and not result['cross_page_delivery_gaps']


def test_altered_handbook_page_blocks_source_qualification():
    from scripts.legal_integration_prerequisites import SOURCE,ROOT,WORK
    from scripts.legal_integration_source_ownership import handbook_fidelity
    envelope=json.loads((ROOT/SOURCE).read_text())
    page=next(u for u in envelope['source_packet']['units'] if u['unit_id'].startswith('handbook.'))
    page['text'] += '\nAdded legal condition.'
    result=handbook_fidelity(envelope,ROOT/WORK/'test-source/corrupt-handbook')
    assert result['_node_status']=='BLOCKED' and page['unit_id'] in result['page_mismatches']


def test_changed_judgment_amount_cannot_pass_rendered_fidelity(monkeypatch):
    from scripts import legal_integration_source_ownership as source
    from scripts.legal_integration_prerequisites import ROOT,WORK
    original=source.rendered_streams
    def corrupt(pdf,directory):
        streams,positions=original(pdf,directory)
        assert '10,958.27' in streams['body']
        streams['body']=streams['body'].replace('10,958.27','10,958.28')
        # Table verification reads retained PDF coordinates independently.
        tree=ET.parse(directory/'rendered-positions.xhtml')
        ns={'h':'http://www.w3.org/1999/xhtml'}
        for word in tree.findall('.//h:word',ns):
            if word.text=='10,958.27':word.text='10,958.28'
        tree.write(directory/'rendered-positions.xhtml')
        return streams,positions
    monkeypatch.setattr(source,'rendered_streams',corrupt)
    result=source.judgment_fidelity('gatecoin-2025',ROOT/WORK/'test-source/corrupt-judgment')
    assert result['_node_status']=='BLOCKED'
    assert result['components_verified']<result['components_total']


def test_warrant_wire_round_trip_retains_issue_scope_and_exact_support(tmp_path):
    from legalmath.interpretation.assurance.bounded_product import WARRANT
    from legalmath.interpretation.assurance.bounded_references import prepare,resolve
    request={'records':[{'id':'source.rule','kind':'source','normative':True,
        'locator':'synthetic','text':'Emergency transfers remain subject to the reconciliation block.'}],
        'question_scope':{'mode':'SUPPLIED_RULES_ONLY'},'required_considered':['review-3']}
    prepared=prepare(request,WARRANT)
    alias=prepared['schema']['properties']['considered']['properties']['c0']['enum'][0]
    value={'decisions':[{'issue_id':'issue-0','disposition':'UNWARRANTED','basis':'QUESTION_SCOPE',
        'reason':'The requested supplied-rule determination needs no hypothetical outside rule.',
        'support':[{'span_id':'s0'}]}],'considered':{'c0':alias},'source_gaps':[],'assertion_bindings':[]}
    expanded=resolve(value,prepared,maximum_bytes=24000)
    assert expanded['considered']==['review-3']
    assert expanded['decisions'][0]['issue_id']=='issue-0'
    assert expanded['decisions'][0]['support'][0]['quote']==request['records'][0]['text']
    assert prepared['request']['question_scope']==request['question_scope']


@pytest.fixture(scope='module')
def actual_revision_candidate():
    from scripts.legal_integration_prerequisites import (
        ROOT,WORK,REVIEW,SOURCE,PROGRAM,STATE,BASE,REOPEN,USER,CASE_CALLS,STAGE_CALLS,expected_program)
    from scripts.legal_integration_acceptance_revision import historical_projection
    from scripts.legal_mission_execution import read
    baseline=read(ROOT/WORK/'baseline.json')
    archives={(r['previous']['path'],r['previous']['sha256']):r['archive'] for r in baseline['archived']}
    refs={r['previous']['path']:r['archive'] for r in baseline['archived']}
    directory=WORK/'test-registration';local=directory/'local-review-candidate.json'
    save(ROOT/local,{'verdict':'PASS','provider_calls':0,'evidence':[ref(ROOT,REVIEW)],
        'scope':'Diagnostic only; this candidate never registers or grants authority.'})
    revision={'profile':'integration-prerequisites.v1','prior_detours':29,
        'additional_consolidated_revision':1,'live_calls_added':0,'attempts_reset':False,
        'user_instruction':USER,'review':ref(ROOT,REVIEW),'baseline':ref(ROOT,WORK/'baseline.json'),
        'local_review':ref(ROOT,local),'source':ref(ROOT,SOURCE),
        'prior_program':refs[str(PROGRAM)],'prior_state':refs[str(STATE)],
        'prior_binding':refs[str(BASE/'current-binding.json')],'prior_ledger':refs[str(BASE/'live-calls.json')],
        'reopened_nodes':list(REOPEN),'semantic_stage_maximum':STAGE_CALLS,
        'semantic_case_maximum':CASE_CALLS,'terminal_recovery_policy':POLICY}
    before=read(ROOT/revision['prior_state']['path'])
    program=expected_program(historical_projection(read(ROOT/revision['prior_program']['path']),archives),
        before,revision,ROOT)
    state=deepcopy(before)
    for tid in REOPEN:
        state['tasks'][tid].update(status='PENDING',reason='Diagnostic candidate, never executed')
        state['tasks'][tid].pop('result',None)
    state['program_hash']=digest(program)
    return ROOT,directory,program,state,before


def test_actual_revision_preserves_history_and_independent_failure_frontiers(actual_revision_candidate):
    from scripts.legal_mission_execution import validate_program
    from scripts.legal_integration_master import MasterExecution
    root,directory,program,state,before=actual_revision_candidate
    validate_program(program,root)
    save(root/directory/'program.json',program);save(root/directory/'state.json',state)
    execution=MasterExecution(root,directory/'program.json',directory/'state.json')
    with execution.locked() as locked:
        assert all(locked['tasks'][t]['attempts']==r['attempts'] for t,r in before['tasks'].items())
    frontier=execution.classify(state)
    assert not any(r['status']=='INVALID' for r in frontier.values())
    owners=('ownership-2023','ownership-2025','ownership-handbook')
    assert all(frontier[t]['status']=='READY' for t in (*owners,'current-binding'))
    failed=deepcopy(state)
    failed['tasks']['current-binding']['status']='BLOCKED'
    frontier=execution.classify(failed)
    assert all(frontier[t]['status']=='READY' for t in owners)
    assert frontier['semantic-preflight']['status']=='DEPENDENCY_BLOCKED'
    assert frontier['continuation-review']['status']=='WAITING'
    for tid in owners:failed['tasks'][tid]['status']='BLOCKED'
    frontier=execution.classify(failed)
    assert frontier['continuation-review']['status']=='READY'


@pytest.mark.parametrize('fault',['deadline','acquisition','semantic','policy','unrelated','charge_grant'])
def test_actual_revision_rejects_unreviewed_extensions(actual_revision_candidate,fault):
    from scripts.legal_mission_execution import validate_program,Refused
    root,_,original,_,_=actual_revision_candidate;program=deepcopy(original)
    tasks={t['id']:t for t in program['tasks']}
    if fault=='deadline':program['deadline_utc']='2100-01-01T00:00:00+00:00'
    elif fault=='acquisition':tasks['acquire-p10']['maximum_attempts']+=1
    elif fault=='semantic':tasks['semantic-preflight']['maximum_attempts']+=1
    elif fault=='policy':program['prerequisite_repair']['terminal_recovery_policy']['maximum_replacements']+=1
    elif fault=='charge_grant':program['prerequisite_repair']['live_calls_added']=1
    else:tasks['inventory-p10']['acceptance']='Accept a smaller population.'
    with pytest.raises(Refused):validate_program(program,root)


def test_current_scope_supports_pre_revision_and_repaired_program(monkeypatch):
    from scripts import legal_integration_current_live as live
    from scripts.legal_integration_prerequisites import WORK,REVIEW,CASE_CALLS,STAGE_CALLS
    monkeypatch.setattr(live,'read',lambda path:{'execution_refresh':{}})
    assert live.current_scope()==(live.WORK/'live',live.REVIEW,62,128,0)
    monkeypatch.setattr(live,'read',lambda path:{'prerequisite_repair':True})
    assert live.current_scope()==(WORK/'live',REVIEW,CASE_CALLS,STAGE_CALLS,1)
