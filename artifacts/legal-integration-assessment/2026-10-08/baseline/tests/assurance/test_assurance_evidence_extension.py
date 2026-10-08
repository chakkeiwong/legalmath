from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
import assurance_evidence_extension as ex
import assurance_evidence_continuation as old
import assurance_evidence_core as c
import assurance_evidence_protocol as p
from legalmath.canonical import digest, raw_digest
from legalmath.errors import LegalMathError

def code_error(code):
    class Check:
        def __enter__(self):
            self.cm=pytest.raises(LegalMathError); self.value=self.cm.__enter__(); return self
        def __exit__(self,*args):
            ok=self.cm.__exit__(*args); assert self.value.value.code==code; return ok
    return Check()


@pytest.fixture
def root(tmp_path):
    prior = tmp_path/'prior-ledger.json'
    prior.write_text('95 charged, five unused, never rewritten')
    now = datetime.now(timezone.utc)
    c.save(tmp_path/ex.RUN/'authorization.json', {
        'baseline_used':95,'maximum':100,'repair_maximum':20,'issue_limit':4,'final_issue_limit':20,
        'attempts_per_task':2,'old_unused_calls_carried':0,
        'starts_at':(now-timedelta(minutes=1)).isoformat(),'ends_at':(now+timedelta(hours=1)).isoformat(),
        'baseline_issue_spending':{'issue.0':4},'allowed_issues':['issue.'+str(i) for i in range(110)]+['final.dispositions.structure-reader'],
        'protected_checkpoint':[c.receipt(prior,tmp_path)]})
    c.save(tmp_path/ex.RUN/'baseline-accepted.json',[])
    return tmp_path


def task(i=0):
    return p.make_task('propagation','structure-reader',['issue.'+str(i)],{
        'kind':'review','source_packet':{'units':[{'unit_id':'source','text':'Retained complete source.'}]},
        'questions':[{'id':'question','missing':'What is established?'}]})


def reserve(root,i,repair=False):
    return ex.Allowance(root,task(i),correction=repair).reserve(digest(i))


def test_separate_100_calls_preserve_95_and_old_unused(root):
    before = (root/'prior-ledger.json').read_bytes()
    for i in range(100):
        assert reserve(root,i)==96+i
    s = ex.Allowance(root).verify()
    assert s['used']==100 and s['combined_used']==195 and s['old_unused_calls_carried']==0
    assert (root/'prior-ledger.json').read_bytes()==before
    with code_error('E_RESOURCE_LIMIT'):
        reserve(root,101)


def test_twenty_repairs_are_subset_of_total(root):
    for i in range(20):
        reserve(root,i,True)
    with code_error('E_RESOURCE_LIMIT'):
        reserve(root,21,True)
    reserve(root,22)
    s=ex.Allowance(root).verify()
    assert s['used']==21 and s['repair_calls']==20 and s['remaining']==79


def test_canonical_identity_survives_task_rename(root):
    for i in range(4):
        t=task(); t['id']+=str(i)
        ex.Allowance(root,t,True).reserve(digest(i))
    t=task(); t['id']='renamed-again'
    with code_error('E_RESOURCE_LIMIT'):
        ex.Allowance(root,t,True).reserve(digest(5))
    assert ex.Allowance(root).verify()['combined_issue_spending']['issue.0']==8


def test_per_task_limit_and_duplicate_request(root):
    a=ex.Allowance(root,task())
    a.reserve('1'*64)
    with code_error('E_INTEGRITY'):
        a.reserve('1'*64)
    ex.Allowance(root,task(),True).reserve('2'*64)
    with code_error('E_RESOURCE_LIMIT'):
        ex.Allowance(root,task(),True).reserve('3'*64)


def test_crash_projection_recovery_never_refunds(root):
    reserve(root,0)
    (root/ex.RUN/'allowance.json').unlink()
    assert ex.Allowance(root).verify()['used']==1
    reserve(root,1)
    assert ex.Allowance(root).verify()['combined_used']==97


def test_concurrent_reservations_are_unique(root):
    with ThreadPoolExecutor(max_workers=4) as pool:
        slots=list(pool.map(lambda i:reserve(root,i),range(4)))
    assert sorted(slots)==[96,97,98,99]


def test_old_ledger_tampering_is_veto(root):
    reserve(root,0)
    (root/'prior-ledger.json').write_text('reset')
    with code_error('E_INTEGRITY'):
        ex.Allowance(root)


def test_expiry_blocks_dispatch(root,monkeypatch):
    monkeypatch.setattr(c,'now',lambda:'2100-01-01T00:00:00+00:00')
    with code_error('E_RESOURCE_LIMIT'):
        reserve(root,0)


def test_engine_isolation():
    rt=ex.engine()
    assert rt.RUN==ex.RUN and old.RUN!=ex.RUN and old.Allowance is not ex.Allowance


def retained(root,t):
    wire,schema,_=p.transport(t)
    slot=ex.Allowance(root,t).reserve(digest(wire))
    folder=root/ex.RUN/'provider-evidence'/f'{slot:04}-{digest(wire)[:16]}'
    result={'binding_hash':wire['binding_hash'],'findings':[{
        'question_id':wire['questions'][0]['id'],'status':'UNRESOLVED','answer':'Missing case facts.',
        'evidence':[],'qualifications':['Conditional only.'],'needed_evidence':['Case facts.'],
        'original_question_answered':False}],'legal_correctness':'NOT_ESTABLISHED'}
    for name,value in [('request.json',wire),('schema.json',schema),('result.json',result)]:
        c.save(folder/name,value)
    c.save(folder/'manifest.json',{'allowance_slot':slot,'request_hash':digest(wire),
        'files':{name:{'retained_sha256':raw_digest((folder/name).read_bytes())} for name in ('request.json','schema.json','result.json')}})
    return folder


def test_saved_provider_result_replays_without_spending(root):
    t=task(); retained(root,t)
    forbidden=lambda **kw:pytest.fail('No live replay')
    rt=ex.engine()
    assert rt.attempt(root,t,provider_factory=forbidden)['status']=='VALIDATED'
    assert rt.attempt(root,t,provider_factory=forbidden)['status']=='VALIDATED'
    assert ex.Allowance(root).verify()['used']==1


def test_interrupted_request_stays_charged(root):
    t=task(); wire,_,_=p.transport(t)
    ex.Allowance(root,t).reserve(digest(wire))
    r=ex.engine().attempt(root,t,provider_factory=lambda **kw:pytest.fail('No blind replay'))
    assert r['error']=='E_DEPENDENCY' and ex.Allowance(root).verify()['used']==1


def test_changed_provider_output_fails_closed(root):
    t=task(); folder=retained(root,t)
    ex.engine().attempt(root,t)
    c.save(folder/'result.json',{})
    with code_error('E_INTEGRITY'):
        ex.engine().attempt(root,t)


def test_missing_and_duplicate_coverage_cannot_pass(root,monkeypatch):
    monkeypatch.setattr(ex.phases,'context',lambda r:{'candidates':{'reading':{}}})
    assert len(ex.coverage(root)[1])==2
    row={'task':'t','phase':'propagation','role':'structure-reader','value':{'reading_updates':[{'reading_id':'reading'}]}}
    c.save(root/ex.RUN/'baseline-accepted.json',[row])
    assert ex.coverage(root)[1]==[('exception-challenger','reading')]
    c.save(root/ex.RUN/'baseline-accepted.json',[row,{**row,'task':'another'}])
    with code_error('E_INTEGRITY'):
        ex.coverage(root)


def test_actual_recovery_preserves_omitted_question_and_complete_sources():
    root=Path('/home/chakwong/python/legalmath')
    tasks=ex.initial_tasks(root)
    assert len(tasks)==3
    propagation=[t for t in tasks if t['phase']=='propagation']
    assert len(propagation)==2 and all(len(t['request']['selected'])==1 for t in propagation)
    original=next(t for t in c.read(root/old.RUN/'initial-tasks.json') if t['id']=='propagation.exception-challenger.007205b81b17778be99277e7')
    expected={(q['reading_id'],q['question_id']) for q in original['request']['question_inventory']}
    actual=[(q['reading_id'],q['question_id']) for t in propagation for q in t['request']['question_inventory']]
    assert len(actual)==len(set(actual))==31 and set(actual)==expected
    assert any(q[1]=='question.95e00194141d4296a2fafa32d75218b880113d2f3e305ffeab2784d47e08adcb' for q in actual)
    for t in propagation:
        assert t['request']['source_packet']==original['request']['source_packet']
        assert t['counted_repair'] and 'response_schema' in t['request']


def test_two_provider_failures_block_before_any_call(root,monkeypatch):
    class RT:
        def consecutive_failures(self,r): return 2
        def attempt(self,*a,**kw): pytest.fail('Must not dispatch')
    monkeypatch.setattr(ex,'engine',lambda:RT())
    with code_error('E_DEPENDENCY'):
        ex.run_task(root,task())


def test_program_scheduler_skips_unformalized_and_hard_binds_batches():
    root=Path('/home/chakwong/python/legalmath')
    tasks=ex.program_tasks(root)
    assert tasks
    assert all(1 <= len(t['request']['selected']) <= 3 for t in tasks)
    assert all(all(t['request']['prior_assessments'][cid]['formalization'] is not None for cid in t['request']['selected']) for t in tasks)
    for t in tasks:
        schema=t['request']['response_schema']
        allowed=set(schema['$defs']['Assessment']['properties']['related_readings']['items']['enum'])
        assert allowed == set(t['request']['selected'])
        assert schema['properties']['newly_proposed_readings']['maxItems'] == 0
        assert set(t['request']['reading_hashes']) == set(t['request']['selected'])
        from legalmath.interpretation.search.models import commitment
        for cid in t['request']['selected']:
            assert t['request']['reading_hashes'][cid] == commitment(t['request']['readings'][cid])
    skipped=c.read(Path('/home/chakwong/python/legalmath')/ex.RUN/'programs/skipped.json')
    assert skipped and all(row['status']=='RETAIN_UNFORMALIZED' for row in skipped)


def test_orphan_reservation_is_recorded_without_replay(tmp_path):
    prior=tmp_path/'prior'; prior.write_text('checkpoint')
    now=datetime.now(timezone.utc)
    c.save(tmp_path/ex.RUN/'authorization.json',{
        'baseline_used':95,'maximum':100,'repair_maximum':20,'issue_limit':4,'final_issue_limit':20,
        'attempts_per_task':2,'old_unused_calls_carried':0,'starts_at':(now-timedelta(minutes=1)).isoformat(),
        'ends_at':(now+timedelta(hours=1)).isoformat(),'baseline_issue_spending':{},
        'allowed_issues':['issue.0'],'protected_checkpoint':[c.receipt(prior,tmp_path)]})
    t=task(); wire,schema,_=p.transport(t)
    slot=ex.Allowance(tmp_path,t,True).reserve(digest(wire))
    directory=tmp_path/ex.RUN/'tasks'/t['id']/'attempt-01'
    for name,value in [('task.json',t),('request.json',wire),('schema.json',schema)]:
        c.save(directory/name,value)
    recovered=ex.recover_orphan_reservations(tmp_path)
    assert recovered==[{'slot':slot,'task':t['id'],'status':'RECOVERED_INTERRUPTED'}]
    row=c.read(directory/'result.json')
    assert row['status']=='FAILED' and row['interrupted_reservation']
    assert ex.Allowance(tmp_path).verify()['used']==1


def test_completion_retains_literal_prior_assumptions_and_questions():
    from assurance_evidence_completion import preserve_history
    prior={'added_assumptions':['Old qualification','Shared'],'unresolved_questions':['Old specific question?']}
    proposed={'added_assumptions':['Shared','New qualification'],'unresolved_questions':['All historical questions remain open.']}
    merged=preserve_history(prior,proposed)
    assert merged['added_assumptions']==['Old qualification','Shared','New qualification']
    assert merged['unresolved_questions']==['Old specific question?','All historical questions remain open.']
    assert proposed['unresolved_questions']==['All historical questions remain open.']


def test_final_partition_keeps_every_reading_after_packet_limit(monkeypatch):
    from assurance_evidence_completion import partition
    items=[{'reading':{'reading_id':str(i)}} for i in range(7)]
    def build(chunk,number):
        if len(chunk)>2:
            c.fail('E_RESOURCE_LIMIT','bounded packet')
        t=task(number)
        t['request']['reviewed_role']='exception-challenger'
        return t
    monkeypatch.setattr(p,'transport',lambda t: ({},{},{}))
    tasks,coverage=partition(items,build)
    assert len(tasks)==4
    assert [r['reading_id'] for r in coverage]==[str(i) for i in range(7)]
    assert len({r['reading_id'] for r in coverage})==7


def test_single_oversized_final_reading_fails_without_truncation():
    from assurance_evidence_completion import partition
    def build(chunk,number):
        c.fail('E_RESOURCE_LIMIT','Cannot fit whole source')
    with code_error('E_RESOURCE_LIMIT'):
        partition([{'reading':{'reading_id':'required'}}],build)


def test_retained_reading_preserves_large_history_but_keeps_capacity_bound():
    from legalmath.translation.model import RetainedReading, from_reading
    repo=Path('/home/chakwong/python/legalmath')
    ctx=ex.phases.context(repo)
    evidence=c.read(repo/ex.RUN/'checks-current/formal-evidence.json')
    reading=next(e['derived_reading'] for e in evidence if e['derived_reading']['formalization'] is not None and len(e['derived_reading']['questions'])>20)
    typed=RetainedReading.model_validate(reading)
    assert typed.questions==reading['questions']
    assert from_reading(reading,ctx['packet'],'2026-09-30T00:00:00.000000Z')
    reading=deepcopy(reading)
    reading['questions']=[str(i)+' retained question' for i in range(65)]
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        RetainedReading.model_validate(reading)



def saved_diagnostics(root):
    from assurance_evidence_completion import verify_completion
    values = {}
    for version in ('v2', 'v3'):
        work = root/ex.RUN/('checks-current-'+version)
        result = {'runtime': {'qualification_statuses': {'BLOCKED':6, 'QUALIFIED':10}
            if version=='v2' else {'QUALIFIED':16}, 'programs':16,
            'native_java_probe_cases':384, 'executed_target_cases':0},
            'production_release':False, 'original_obligations_open':46}
        for name in ('program-inventory.json','runtime-summary.json','formal-evidence.json',
                'question-dispositions.json','obligation-dispositions.json','conditional-bridge-checks.json'):
            c.save(work/name, [])
        c.save(work/'result.json', result)
        c.save(work/'completion-receipt.json',
            {'files':ex.master.files_in(work,root,('completion-receipt.json',))})
        verify_completion(root,work)
        values[version] = result
    baseline = c.receipt(root/ex.RUN/'checks-current-v2/result.json',root)
    current = c.receipt(root/ex.RUN/'checks-current-v3/result.json',root)
    refs = [baseline, current]
    refs += [c.receipt(root/ex.RUN/('checks-current-'+v)/'completion-receipt.json',root) for v in ('v2','v3')]
    report = {'status':'VERIFIED_EXISTING_V3_ZERO_CALLS', 'references':refs,
        'baseline':baseline, 'current':current,
        'qualification_before':values['v2']['runtime']['qualification_statuses'],
        'qualification_after':values['v3']['runtime']['qualification_statuses'],
        'final_review_scope':'Final reviews cover v2 only.'}
    c.save(root/ex.RUN/'diagnostic-refresh/report.json', report)
    c.save(root/ex.RUN/'current-diagnostic.json',
        {'receipt':c.receipt(root/ex.RUN/'diagnostic-refresh/report.json',root)})
    return values


def test_restart_keeps_current_diagnostic_and_original_acceptance_limits(root,monkeypatch):
    expected=saved_diagnostics(root)
    monkeypatch.setattr(ex,'coverage',lambda r:([],[]))
    monkeypatch.setattr(ex,'verify',lambda r:{})
    c.save(root/ex.RUN/'state.json',{'phases':{phase:{'status':'COMPLETED'} for phase in ex.PHASES},'halt':None})
    before=ex.Allowance(root).verify()
    first=ex.run(root)
    second=ex.run(root)
    for report in (first,second):
        assert report['checks']==expected['v3']
        assert report['checks_stale_v2']==expected['v2']
        assert report['accepted_program_repair_tasks']==0
        assert report['final_review_acceptance']=='OPEN_OR_UNACCEPTED'
        assert not report['release_eligible'] and report['remaining_original_obligations']==46
    assert ex.Allowance(root).verify()==before
    plan=c.read(root/ex.RUN/'next-phase-plan.json')
    assert plan['current_diagnostic']['result']['path'].endswith('checks-current-v3/result.json')
    assert 'checks-current-v3' in (root/'docs/implementation/assurance-evidence-master/reset-memo.md').read_text()


def test_tampered_current_receipt_never_falls_back_to_stale_result(root):
    from assurance_evidence_completion import adopted_diagnostic
    saved_diagnostics(root)
    c.save(root/ex.RUN/'checks-current-v3/result.json', {'claimed':'changed'})
    with code_error('E_INTEGRITY'):
        adopted_diagnostic(root, ex)


def test_incomplete_receipt_cannot_certify_an_unlisted_result(root):
    from assurance_evidence_completion import verify_completion
    work=root/ex.RUN/'checks-current-v3'
    c.save(work/'result.json', {'status':'unbound'})
    c.save(work/'completion-receipt.json', {'files':[]})
    with code_error('E_INTEGRITY'):
        verify_completion(root,work)


@pytest.mark.parametrize('directory',['../escape','/tmp/foreign','nested/checks','.','..',''])
def test_diagnostic_path_cannot_escape_fixed_campaign(root,directory):
    from assurance_evidence_completion import checked_candidates
    with code_error('E_AUTHORITY'):
        checked_candidates(root,ex,directory)


def test_offline_diagnostic_disables_dispatch_and_reuses_receipt(root,monkeypatch):
    import assurance_evidence_completion as completion
    from legalmath.interpretation.search.providers import CodexProvider
    expected=saved_diagnostics(root)
    reserve(root,0)
    monkeypatch.setattr(ex,'verify',lambda r:{'frozen_root':str(Path(completion.__file__).resolve().parents[1])})
    original=CodexProvider.complete
    def report(r,began):
        with code_error('E_AUTHORITY'):
            CodexProvider.complete(None,None,None,None)
        with code_error('E_AUTHORITY'):
            ex.Allowance(r,task(1)).reserve(digest('forbidden'))
        return {'allowance':ex.Allowance(r).verify(),'checks':expected['v3']}
    monkeypatch.setattr(ex,'result',report)
    before=(root/ex.RUN/'allowance.json').read_bytes()
    assert completion.offline_diagnostic(root,ex)['result']==expected['v3']
    assert completion.offline_diagnostic(root,ex)['allowance']['used']==1
    assert (root/ex.RUN/'allowance.json').read_bytes()==before
    assert CodexProvider.complete is original
