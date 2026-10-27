"""Repair the missing service inheritance link in the October 24 amendment."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import json
import os
import signal
import subprocess
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from scripts.legal_integration_master import BASE, DOC, PROGRAM, STATE, PLAN
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, historical_evidence, process_alive, process_identity
from scripts.legal_integration_acceptance_revision import historical_projection

KEY = 'service_inheritance'
OLD_WORK = Path('artifacts/legal-mission-control/2026-10-24/window-continuation')
WORK = OLD_WORK/'service-inheritance'
RUNTIME = WORK/'live'
REVIEW = Path('docs/plans/legal-window-service-inheritance-correction-2026-10-24.md')
REASON = 'Service scope changed authority'
SELF = 'scripts/legal_window_service_correction.py'
TEST = 'tests/tooling/test_window_service_correction.py'
CHANGED = ('scripts/legal_window_continuation.py', 'scripts/legal_integration_phased_live.py',
           'scripts/legal_mission_control.py')
IMPLEMENTATION = (*CHANGED, SELF, TEST)
OWNER_ATTEMPTS = {'baseline-p14':6, 'baseline-gatecoin':4, 'tool-gatecoin-bm25':2}

def now():
    return datetime.now(timezone.utc).isoformat()

def lock_owner(path, pid):
    stat=Path(path).stat()
    wanted=f'{os.major(stat.st_dev):02x}:{os.minor(stat.st_dev):02x}:{stat.st_ino}'
    return any(len(row)>5 and row[1]=='FLOCK' and row[3]=='WRITE' and row[4]==str(pid)
        and row[5]==wanted for row in (line.split() for line in Path('/proc/locks').read_text().splitlines()))

def mapping(rows, mission=False):
    allowed = set(CHANGED) | {str(PLAN)} | ({str(PROGRAM)} if mission else set())
    return {(r['previous']['path'],r['previous']['sha256']):r['archive']
            for r in rows if r['previous']['path'] in allowed}

def corrected_binding(binding):
    """Use the existing supported chain, without changing its scope or grant."""
    value=deepcopy(binding)
    require(value.get('predecessor') and not value.get('phase_service_predecessor'),
        'Different service inheritance baseline')
    require(value['predecessor']==value['window_continuation']['prior_binding'],
        'Service predecessor differs from reviewed window predecessor')
    value['phase_service_predecessor']=value['predecessor']
    return value

def expected_program(old, correction, root, plan_reference):
    rows=read(Path(root)/correction['baseline']['path'])['archived']
    value=historical_projection(old,mapping(rows))
    value['window_continuation'][KEY]=correction
    for tid,addition in correction['attempt_additions'].items():
        row=next(t for t in value['tasks'] if t['id']==tid)
        require(addition==1 and row['maximum_attempts']==OWNER_ATTEMPTS[tid],'Different owner attempt baseline')
        number=OWNER_ATTEMPTS[tid]+1
        row.update(maximum_attempts=number,deliverable=str(BASE/tid/('attempt-'+str(number))/'result.json'))
        row['inputs'] += [correction['review'],correction['result']]
    value['protected_evidence'] += [correction[k] for k in ('review','result','baseline','handover')]
    value['protected_evidence'] += list(correction['implementation'].values())+[plan_reference]
    return value

def project_state(before, program, timestamp):
    correction=program['window_continuation'][KEY]
    state=deepcopy(before)
    targets=[v for v in before.get('continuation_vetoes',[]) if v['code']=='E_AUTHORITY' and v['reason']==REASON]
    require(targets==correction['resolved_vetoes'] and len(targets)==len(correction['attempt_additions']),
        'Changed target vetoes')
    for tid,addition in correction['attempt_additions'].items():
        row=state['tasks'][tid]
        require(tid in OWNER_ATTEMPTS and addition==1 and row['status']=='FAILED'
            and len(row['attempts'])==OWNER_ATTEMPTS[tid],'Different failed owner')
        row.update(status='PENDING',reason='Repair explicit service inheritance; preserve every prior attempt')
        row.pop('result',None)
    for veto in targets:
        state['continuation_vetoes'].remove(veto)
        state.setdefault('resolved_continuation_vetoes',[]).append(dict(veto=veto,
            resolution=correction['result'],review=correction['review'],at_utc=timestamp))
    state['program_hash']=digest(program)
    state['events'].append(dict(task_id='baseline-p14',action='SERVICE_INHERITANCE_CORRECTION',
        at_utc=timestamp,review=correction['review'],attempt_additions=correction['attempt_additions'],calls_added=0,detours_added=0))
    return state

def validate(program, root, plan_reference):
    from scripts.legal_mission_execution import validate_program
    root=Path(root); c=program['window_continuation'][KEY]
    require(c['profile']=='window-service-inheritance-correction.v1' and c['work']==str(WORK)
        and c['runtime']==str(RUNTIME) and c['calls_added']==c['replacements_added']==c['detours_added']==0
        and 'baseline-p14' in c['attempt_additions'] and set(c['attempt_additions'])<=set(OWNER_ATTEMPTS)
        and all(v==1 for v in c['attempt_additions'].values()) and set(c['implementation'])==set(IMPLEMENTATION),
        'Unreviewed service correction scope')
    for key in ('review','result','baseline','handover','prior_program','prior_state','prior_binding'):
        verify(root,c[key])
    for pointer in c['implementation'].values(): verify(root,pointer)
    baseline=read(root/c['baseline']['path']); held={r['previous']['path']:r['archive'] for r in baseline['archived']}
    require(baseline['calls']==4872 and baseline['service_replacements']==195,'Wrong service correction baseline')
    for row in baseline['archived']:
        require(row['previous']['sha256']==row['archive']['sha256'],'Changed retained historical bytes')
        verify(root,row['archive'])
    for key,path in (('prior_program',PROGRAM),('prior_state',STATE),('prior_binding',BASE/'current-binding.json')):
        require(c[key]==held[str(path)],'Wrong service correction predecessor')
    handover=read(root/c['handover']['path'])
    require(handover['settled'] and handover['supervisor_ended'] and handover['reserved_dispatches']==0
        and handover['calls']==4872,'Unsettled service correction handover')
    old=read(root/c['prior_program']['path'])
    require(KEY not in old['window_continuation'],'Repeated service correction')
    with historical_evidence(root,mapping(baseline['archived'])): validate_program(old,root)
    result=read(root/c['result']['path'])
    require(result['verdict']=='PASS' and result['provider_calls']==0 and not result['legal_acceptance'],
        'Service correction tests did not pass')
    for pointer in result['evidence']: verify(root,pointer)
    before=read(root/c['prior_state']['path'])
    require(len(c['resolved_vetoes'])==len(c['attempt_additions']),'Wrong veto population')
    expected_evidence=[]
    for tid in c['attempt_additions']:
        path=BASE/tid/('attempt-'+str(OWNER_ATTEMPTS[tid]))/'evidence.json'
        evidence=read(root/path)
        require(evidence==dict(error='E_AUTHORITY',reason=REASON,continuation_veto=True),'Different failure evidence')
        expected_evidence.append([ref(root,path)])
    require(all(v in before['continuation_vetoes'] and v['code']=='E_AUTHORITY' and v['reason']==REASON
        and v['evidence'] in expected_evidence for v in c['resolved_vetoes']),'Wrong authority veto')
    require(program==expected_program(old,c,root,plan_reference),'Changed graph, budget or unrelated content')
    return {t['id']:t['maximum_attempts'] for t in program['tasks']}

def validate_history(program,state,root):
    from scripts.legal_window_continuation import validate_state_history
    previous=deepcopy(program); previous['window_continuation'].pop(KEY)
    validate_state_history(previous,state,root)
    c=program['window_continuation'][KEY]; before=read(Path(root)/c['prior_state']['path'])
    require(set(state['tasks'])==set(before['tasks']) and state['events'][:len(before['events'])]==before['events'],
        'Lost prior state or events')
    for tid,row in before['tasks'].items():
        current=state['tasks'][tid]
        require(len(current['attempts'])>=len(row['attempts']),'Lost prior attempts')
        for a,b in zip(row['attempts'],current['attempts']):
            require(all(b.get(k)==v for k,v in a.items()),'Changed prior attempt '+tid)
        if row['status']=='SUCCEEDED': require(current==row,'Changed successful owner')
        elif tid not in c['attempt_additions'] and row['status'] not in ('PENDING','RUNNING'):
            require(current==row,'Reopened unrelated settled owner')
    prior=before.get('resolved_continuation_vetoes',[])
    require(state.get('resolved_continuation_vetoes',[])[:len(prior)]==prior,'Lost prior veto resolutions')
    for veto in before.get('continuation_vetoes',[]):
        require(veto in state.get('continuation_vetoes',[]) or (veto in c['resolved_vetoes'] and any(
            r.get('veto')==veto and r.get('resolution')==c['result'] and r.get('review')==c['review']
            for r in state.get('resolved_continuation_vetoes',[]))),'Lost unresolved veto')

def prepare():
    require(not (ROOT/WORK/'preparation.json').exists(),'Correction already prepared')
    outputs={p:(ROOT/p).read_text() for p in CHANGED}
    def patch(path,old,new):
        require(outputs[path].count(old)==1,'Nonunique correction anchor: '+path)
        outputs[path]=outputs[path].replace(old,new)
    path=CHANGED[0]
    old='def validate_revision(program, root, plan_reference=None):\n'
    patch(path,old,old+"    if program['window_continuation'].get('service_inheritance'):\n        from scripts.legal_window_service_correction import validate\n        return validate(program, root, plan_reference)\n")
    old='def validate_state_history(program,state,root):\n'
    patch(path,old,old+"    if program['window_continuation'].get('service_inheritance'):\n        from scripts.legal_window_service_correction import validate_history\n        return validate_history(program, state, root)\n")
    patch(path,"        binding.update(program=pointer,review=revision['review'],user_instruction=USER,predecessor=revision['prior_binding'],\n",
        "        binding.update(program=pointer,review=revision['review'],user_instruction=USER,predecessor=revision['prior_binding'],\n            phase_service_predecessor=revision['prior_binding'],\n")
    start=outputs[path].index('def worker():');end=outputs[path].index('\ndef arm():',start)
    body=outputs[path][start:end].replace("ROOT/WORK/","ROOT/work/")
    body=body.replace('def worker():\n',"def worker():\n    work=Path(read(ROOT/PROGRAM)['window_continuation'].get('service_inheritance',{}).get('work',str(WORK)))\n")
    outputs[path]=outputs[path][:start]+body+outputs[path][end:]
    patch(path,'def arm():\n',"def arm():\n    if read(ROOT/PROGRAM)['window_continuation'].get('service_inheritance'):\n        from scripts.legal_window_service_correction import arm as corrected_arm\n        return corrected_arm()\n")
    path=CHANGED[1]
    patch(path,"    if program.get('window_continuation'):\n        return Path(program['window_continuation']['runtime'])\n",
        "    if program.get('window_continuation'):\n        return Path(program['window_continuation'].get('service_inheritance',program['window_continuation'])['runtime'])\n")
    path=CHANGED[2]
    old="            verify_refs(root, window)\n            detours += 1\n"
    patch(path,old,old+"            correction=window.get('service_inheritance')\n            if correction:\n                require(correction.get('profile')=='window-service-inheritance-correction.v1'\n                    and correction.get('calls_added')==correction.get('replacements_added')==correction.get('detours_added')==0\n                    and correction.get('attempt_additions')=={'baseline-p14':1}, 'Unreviewed service inheritance correction')\n                require(any(r['id']=='window-service-inheritance-correction-2026-10-24'\n                    and correction['review'] in r['result_evidence'] for r in history),'Missing service inheritance correction history')\n")
    for path,body in outputs.items():
        target=ROOT/WORK/'candidate'/path;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('x') as f:f.write(body)
        compile(body,str(target),'exec')
    plan=(ROOT/PLAN).read_text()+('\n## October 24 service-inheritance correction\n\n'
        'Attempt 6 stopped before its first new dispatch because the time amendment omitted\n'
        'the explicit service-predecessor link. The reviewed correction is in\n'
        '`docs/plans/legal-window-service-inheritance-correction-2026-10-24.md`.\n'
        'Retain all six attempts and 4,872 calls; one corrected continuation is attempt 7.\n'
        'No call/replacement ceiling or deadline changes. Reuse exact checkpoints and\n'
        'preserve invalid responses. Gatecoin and other ready owners remain independent.\n')
    target=ROOT/WORK/'candidate'/PLAN;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(plan)
    value=dict(at_utc=now(),program=ref(ROOT,PROGRAM),binding=ref(ROOT,BASE/'current-binding.json'),
        review=ref(ROOT,REVIEW),current_files=[ref(ROOT,p) for p in (*CHANGED,str(PLAN))],
        candidates=[ref(ROOT,WORK/'candidate'/p) for p in (*CHANGED,str(PLAN))],provider_calls=0)
    save(ROOT/WORK/'preparation.json',value);return dict(prepared=len(outputs),provider_calls=0)

def revise_preparation():
    preparation=read(ROOT/WORK/'preparation.json')
    for pointer in preparation['current_files']+[preparation['program'],preparation['binding']]:verify(ROOT,pointer)
    path=ROOT/WORK/'candidate/scripts/legal_window_continuation.py'
    text=path.read_text()
    anchor="                    save(ROOT/work/(tid+'.result.json'),dict(value=value,at_utc=now()))\n"
    require(text.count(anchor)==1,'Missing worker result boundary')
    text=text.replace(anchor,anchor+"                    require(not isinstance(value,dict) or not value.get('continuation_veto'),\n                        'Shared authority veto; no further live owners')\n")
    path.write_text(text)
    path=ROOT/WORK/'candidate/scripts/legal_mission_control.py';text=path.read_text()
    anchor="and correction.get('attempt_additions')=={'baseline-p14':1}, 'Unreviewed service inheritance correction')"
    replacement="and 'baseline-p14' in correction.get('attempt_additions',{})\n                    and set(correction['attempt_additions']) <= {'baseline-p14','baseline-gatecoin','tool-gatecoin-bm25'}\n                    and all(v==1 for v in correction['attempt_additions'].values()), 'Unreviewed service inheritance correction')"
    require(text.count(anchor)==1,'Missing correction scope');path.write_text(text.replace(anchor,replacement))
    path=ROOT/WORK/'candidate'/PLAN
    with path.open('a') as stream:stream.write('\nGatecoin owners that the old worker finalized with this same pre-dispatch defect\nretain those failed outcomes and receive one corrected continuation each. The\ncorrected supervisor stops further live dispatch on a shared authority veto;\nordinary branch failures still permit independent work.\n')
    preparation['candidates']=[ref(ROOT,WORK/'candidate'/p) for p in (*CHANGED,str(PLAN))]
    preparation['review']=ref(ROOT,REVIEW)
    for path in CHANGED:compile((ROOT/WORK/'candidate'/path).read_text(),path,'exec')
    save(ROOT/WORK/'preparation.json',preparation)
    return dict(revised=True,provider_calls=0)

def verify_local():
    from unittest.mock import patch
    from xml.etree import ElementTree as ET
    from legalmath.interpretation.assurance.bounded_provider import CampaignAllowance
    from legalmath.errors import LegalMathError
    path=ROOT/BASE/'current-binding.json';prior=read(path)
    allowance=CampaignAllowance(ROOT/BASE,{},root=ROOT)
    failure=None
    try:allowance.service_scope()
    except LegalMathError as exc:failure=dict(code=exc.code,reason=exc.details)
    require(failure==dict(code='E_AUTHORITY',reason=REASON),'Failure not reproduced')
    fixed=corrected_binding(prior);original=Path.read_text
    with patch.object(Path,'read_text',lambda p,*a,**k:json.dumps(fixed) if p==path else original(p,*a,**k)):
        inherited=allowance.service_scope()
    require(inherited[0]==prior['phase_service_scope'],'Wrong inherited scope')
    suite=ET.parse(ROOT/WORK/'tests-focused.xml').getroot();cases=list(suite.iter('testcase'))
    require(len(cases)==62 and not list(suite.iter('failure')) and not list(suite.iter('error')),'Focused checks failed')
    save(ROOT/WORK/'scope-reproduction.json',dict(baseline=failure,corrected='PASS',scope=inherited[0],provider_calls=0))
    value=dict(verdict='PASS',provider_calls=0,legal_acceptance=False,focused_tests=62,
        baseline_test_limitations='Two pre-existing product-route tests fail before deployment because their mocked campaign lacks effective_deadline; retained in tests.xml. One new exception-detail assertion was corrected.',
        evidence=[ref(ROOT,WORK/p) for p in ('tests-focused.xml','tests.xml','scope-reproduction.json')])
    save(ROOT/WORK/'local-result.json',value)
    preparation=read(ROOT/WORK/'preparation.json');preparation['review']=ref(ROOT,REVIEW)
    save(ROOT/WORK/'preparation.json',preparation)
    return dict(scope_reproduction='PASS',focused_tests=62,provider_calls=0)

def settle():
    from scripts.legal_optional_quote_validation import owner_children,owner_state
    result=ROOT/WORK/'handover.json'
    if result.exists():
        value=read(result);require(value['supervisor_ended'] and not process_alive(value['process']),'Incomplete handover');return value
    preparation=read(ROOT/WORK/'preparation.json')
    for pointer in preparation['current_files']+preparation['candidates']+[preparation['program'],preparation['binding']]:verify(ROOT,pointer)
    tests=read(ROOT/WORK/'local-result.json');require(tests['verdict']=='PASS' and tests['provider_calls']==0,'Local tests pending')
    owner=read(ROOT/OLD_WORK/'worker.json')['process']
    binding=read(ROOT/BASE/'current-binding.json'); service=Path(binding['phase_service_scope']['path']).parent
    with ExitStack() as stack:
        journals=sorted((ROOT/OLD_WORK/'live').rglob('calls/dispatch.json'))
        paths=[STATE.with_suffix('.lock'),service/'service-worker.lock',
            service/'service-circuit.lock',(BASE/'live-calls.json').with_suffix('.lock')]
        paths += [p.relative_to(ROOT).with_name('dispatch.lock') for p in journals]
        for path in paths:
            handle=stack.enter_context((ROOT/path).open('a'));fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        state=read(ROOT/STATE)
        require(state['tasks']['baseline-p14']['status']=='FAILED' and len(state['tasks']['baseline-p14']['attempts'])==6,
            'P14 failure not settled')
        require(all(not process_alive(r.get('live_supervisor')) for r in state['tasks'].values() if r['status']=='RUNNING'),
            'Another live owner remains')
        require(not any(read(p)['calls'] for p in journals),'New dispatch exists; review required')
        ledger=ref(ROOT,BASE/'live-calls.json');circuit=read(ROOT/service/'service-circuit.json')
        require(len(read(ROOT/BASE/'live-calls.json')['calls'])==4872 and not circuit['open']
            and not circuit.get('half_open_reserved'),'Unsettled provider state')
        stopped=False;mission_lock=stack.enter_context((ROOT/DOC/'mission.execution.lock').open('a'))
        mission_locked=False
        try:
            fcntl.flock(mission_lock,fcntl.LOCK_EX|fcntl.LOCK_NB);mission_locked=True
        except BlockingIOError:
            require(lock_owner(ROOT/DOC/'mission.execution.lock',owner['pid']),
                'Mission checkpoint lock belongs to another process')
        try:
            if process_alive(owner):
                require(process_identity(owner['pid'])==owner and not owner_children(owner),'Worker identity or children changed')
                os.kill(owner['pid'],signal.SIGSTOP);stopped=True
                for _ in range(100):
                    if owner_state(owner) in ('T','t'):break
                    time.sleep(.01)
                require(owner_state(owner) in ('T','t') and process_identity(owner['pid'])==owner
                    and not owner_children(owner) and ref(ROOT,BASE/'live-calls.json')==ledger,'Worker boundary changed')
                require(not (ROOT/DOC/'mission.json.writing').exists()
                    and not (ROOT/STATE.with_name(STATE.name+'.writing')).exists(),'Atomic checkpoint write in progress')
                os.kill(owner['pid'],signal.SIGTERM);os.kill(owner['pid'],signal.SIGCONT);stopped=False
                for _ in range(100):
                    if not process_alive(owner):break
                    time.sleep(.05)
            require(not process_alive(owner),'Failed worker did not end')
            if not mission_locked:fcntl.flock(mission_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            value=dict(settled=True,supervisor_ended=True,process=owner,at_utc=now(),ledger=ledger,calls=4872,
                reserved_dispatches=0,dispatches=[ref(ROOT,p) for p in journals],service=str(service),
                checkpoint_refresh_interrupted=not mission_locked,mission=ref(ROOT,DOC/'mission.json'),state=ref(ROOT,STATE))
            save(result,value);return value
        finally:
            if stopped:os.kill(owner['pid'],signal.SIGCONT)

def deploy():
    handover=read(ROOT/WORK/'handover.json');require(handover['supervisor_ended'],'Handover pending')
    preparation=read(ROOT/WORK/'preparation.json')
    with ExitStack() as stack:
        for path in (OLD_WORK/'worker.lock',STATE.with_suffix('.run.lock'),DOC/'mission.execution.lock',STATE.with_suffix('.lock')):
            handle=stack.enter_context((ROOT/path).open('a'));fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        require(not (ROOT/WORK/'baseline.json').exists(),'Correction already deployed')
        for pointer in preparation['current_files']+preparation['candidates']+[preparation['program'],preparation['binding']]:verify(ROOT,pointer)
        binding=read(ROOT/BASE/'current-binding.json');service=Path(binding['phase_service_scope']['path']).parent
        paths=[PROGRAM,STATE,DOC/'mission.json',BASE/'current-binding.json',BASE/'live-calls.json',BASE/'live-grant.json',
            *map(Path,CHANGED),PLAN,service/'service-circuit.json',service/'service-recovery.json']
        rows=[]
        for path in paths:
            target=ROOT/WORK/'before'/path;target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as stream:stream.write((ROOT/path).read_bytes())
            rows.append(dict(previous=ref(ROOT,path),archive=ref(ROOT,target)))
        recovery=read(ROOT/service/'service-recovery.json')
        replacements=len(recovery['charges'])
        require(replacements==195,'Replacement census changed')
        save(ROOT/WORK/'baseline.json',dict(archived=rows,calls=4872,service_replacements=replacements,settled=True))
        for path in (*CHANGED,str(PLAN)):(ROOT/path).write_bytes((ROOT/WORK/'candidate'/path).read_bytes())
    return dict(deployed=True,provider_calls=0)

def register():
    from scripts.legal_integration_post_review import finish_transaction
    from scripts.legal_integration_repair_execution import validate_staged_mission
    from scripts.legal_integration_campaign import provider
    from unittest.mock import patch
    journal=WORK/'registration.json'
    with ExitStack() as stack:
        for path in (OLD_WORK/'worker.lock',WORK/'worker.lock',STATE.with_suffix('.run.lock'),DOC/'mission.execution.lock',STATE.with_suffix('.lock')):
            handle=stack.enter_context((ROOT/path).open('a'));fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (ROOT/journal).exists():finish_transaction(ROOT,journal);return dict(registered=True,resumed=True)
        baseline=read(ROOT/WORK/'baseline.json');rows=baseline['archived'];held={r['previous']['path']:r['archive'] for r in rows}
        for path in (PROGRAM,STATE,DOC/'mission.json',BASE/'current-binding.json',BASE/'live-calls.json',BASE/'live-grant.json'):
            require(ref(ROOT,path)['sha256']==held[str(path)]['sha256'],'Correction predecessor changed: '+str(path))
        old,before,binding=read(ROOT/PROGRAM),read(ROOT/STATE),read(ROOT/BASE/'current-binding.json')
        targets=[v for v in before['continuation_vetoes'] if v['code']=='E_AUTHORITY' and v['reason']==REASON]
        additions={tid:1 for tid in OWNER_ATTEMPTS if before['tasks'][tid]['status']=='FAILED'
            and before['tasks'][tid].get('reason')==tid+' failed: '+REASON}
        require(len(targets)==len(additions) and 'baseline-p14' in additions,'Exact service veto missing')
        c=dict(profile='window-service-inheritance-correction.v1',work=str(WORK),runtime=str(RUNTIME),calls_added=0,
            replacements_added=0,detours_added=0,attempt_additions=additions,resolved_vetoes=targets,
            review=ref(ROOT,REVIEW),result=ref(ROOT,WORK/'local-result.json'),baseline=ref(ROOT,WORK/'baseline.json'),
            handover=ref(ROOT,WORK/'handover.json'),prior_program=held[str(PROGRAM)],prior_state=held[str(STATE)],
            prior_binding=held[str(BASE/'current-binding.json')],implementation={p:ref(ROOT,p) for p in IMPLEMENTATION})
        program=expected_program(old,c,ROOT,ref(ROOT,PLAN));state=project_state(before,program,now())
        stage=WORK/'registration-stage';save(ROOT/stage/'program.json',program);save(ROOT/stage/'state.json',state)
        pointer=dict(path=str(PROGRAM),sha256=ref(ROOT,stage/'program.json')['sha256'])
        binding=corrected_binding(binding)
        binding['bindings']=historical_projection(binding['bindings'],mapping(rows,True))
        binding.update(program=pointer,service_inheritance_correction=c)
        binding['bindings'] += [pointer,ref(ROOT,PLAN),c['review'],c['result'],c['baseline'],c['handover'],*c['implementation'].values()]
        known={(r['previous']['path'],r['previous']['sha256']) for r in binding['historical_archives']}
        binding['historical_archives'] += [r for r in rows if (r['previous']['path'],r['previous']['sha256']) not in known]
        save(ROOT/stage/'binding.json',binding)
        mission=historical_projection(read(ROOT/DOC/'mission.json'),mapping(rows,True));master=mission['integration_master']
        recorded={(r.get('master_node'),r.get('master_attempt')) for r in mission['history']}
        completed=[(tid,a) for tid,row in before['tasks'].items() for a in row['attempts'] if 'result' in a]
        for tid,attempt in sorted(completed,key=lambda pair:pair[1]['finished_at_utc']):
            if (tid,attempt['number']) in recorded:continue
            outcome=read(ROOT/attempt['result']['path'])
            mission['history'].append(dict(id=f"master-{tid}-{attempt['number']}",task_id='product-contribution',
                kind='product_evaluation',outcome='no_advance',master_node=tid,master_attempt=attempt['number'],
                decision=outcome['conclusion'],next_task='product-contribution',
                next_task_reason='Retain completed owner outcome across interrupted checkpoint refresh.',
                recorded_at_utc=attempt['finished_at_utc'],result_evidence=[c['prior_program'],attempt['result']]))
        for key in master:
            if key in program and isinstance(program[key],dict) and program[key].get('profile'):master[key]=deepcopy(program[key])
        master.update(program=pointer,plan=ref(ROOT,PLAN),window_continuation=program['window_continuation'])
        reason='Correct the omitted service inheritance link; continue unsent P14 work and independent Gatecoin/acquisition/tool owners with all historical outcomes and ceilings preserved.'
        mission['next_task_reason']=reason
        mission['history'].append(dict(id='window-service-inheritance-correction-2026-10-24',task_id='product-contribution',
            kind='product_evaluation',outcome='no_advance',decision=reason,next_task='product-contribution',
            next_task_reason=reason,recorded_at_utc=now(),result_evidence=[pointer,c['review'],c['result']]))
        save(ROOT/stage/'mission.json',mission)
        save(ROOT/WORK/'registration-check.json',validate_staged_mission(ROOT,stage,mission,66))
        overrides={ROOT/PROGRAM:ROOT/stage/'program.json',ROOT/BASE/'current-binding.json':ROOT/stage/'binding.json'}
        rt,rb=Path.read_text,Path.read_bytes
        watched=[BASE/'live-calls.json',Path(binding['phase_service_scope']['path']).parent/'service-circuit.json',
                 Path(binding['phase_service_scope']['path']).parent/'service-recovery.json']
        before_bytes={str(p):(ROOT/p).read_bytes() for p in watched}
        with patch.object(Path,'read_text',lambda p,*a,**k:rt(overrides.get(p,p),*a,**k)), \
             patch.object(Path,'read_bytes',lambda p,*a,**k:rb(overrides.get(p,p),*a,**k)):
            service=provider();require(len(service.check()['calls'])==4872,'Service preflight changed charges')
            require(service.allowance.service_scope()[0]==binding['phase_service_scope'],'Wrong inherited scope')
            service.check_service({'diagnostic':'authority-only-no-dispatch'},{'type':'object'})
        require(all((ROOT/p).read_bytes()==b for p,b in before_bytes.items()),'Preflight mutated spending or service state')
        save(ROOT/WORK/'service-preflight.json',dict(verdict='PASS',provider_calls=0,calls=4872,
            unchanged=[ref(ROOT,p) for p in watched],scope=binding['phase_service_scope'],at_utc=now()))
        writes=[dict(path=str(path),before=ref(ROOT,path),replacement=ref(ROOT,stage/name)) for path,name in (
            (PROGRAM,'program.json'),(STATE,'state.json'),(BASE/'current-binding.json','binding.json'),(DOC/'mission.json','mission.json'))]
        save(ROOT/journal,dict(profile='legal-master-registration-transaction.v1',status='PREPARED',writes=writes))
        finish_transaction(ROOT,journal)
    return dict(registered=True,calls_added=0,attempt_additions=additions,service_preflight='PASS')

def arm():
    from scripts.legal_integration_campaign import provider
    require(read(ROOT/WORK/'registration.json')['status']=='COMMITTED','Correction registration incomplete')
    with (ROOT/WORK/'arm.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        path=ROOT/WORK/'armed.json'
        if path.exists():
            value=read(path);require(process_alive(value['process']),'Ended corrected worker requires review');return value
        provider().check()
        with (ROOT/WORK/'worker.log').open('a') as log:
            process=subprocess.Popen([str(ROOT/'.venv-context/bin/python'),str(ROOT/SELF),'worker'],cwd=ROOT,
                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        value=dict(process=process_identity(process.pid),at_utc=now())
        require(value['process'] is not None,'Corrected worker ended at startup');save(path,value);return value

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','revise_preparation','verify_local','settle','deploy','register','arm','worker'])
    action=parser.parse_args().action
    if action=='worker':
        from scripts.legal_window_continuation import worker
        value=worker()
    else:value=globals()[action]()
    print(json.dumps(value,indent=2))
