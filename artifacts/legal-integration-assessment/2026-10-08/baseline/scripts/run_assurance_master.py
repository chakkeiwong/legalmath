"""Round-11 fixed-command executor with executed repair and successor refresh.

The network installation is a separate exact command. No arbitrary argv, shell
text, package name, subprocess cwd, model or output path is accepted from CLI.
"""
from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import hashlib
import json
import os
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT/'docs/implementation/interpretation-round11'
OUT = ROOT/'artifacts/interpretation/round11'
PY = ROOT/'.venv/bin/python'
DOC_PY = Path('/home/chakwong/miniconda3/envs/tfgpu/bin/python')
TOOL = ROOT/'.localresources/assurance-tools'
TOOLPY = TOOL/'venv/bin/python'
PHASES = tuple(f'M{i}' for i in range(6))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n'); tmp.replace(path)


def now():
    return datetime.now(timezone.utc).isoformat()


def state():
    return read(OUT/'state.json', {'version':1, 'phases':{p:{'status':'PLANNED','attempts':[], 'repairs':[]} for p in PHASES}})


def document_dependencies():
    return [ROOT/'scripts'/n for n in ('check_monograph.py','check_monograph_citations.py',
            'check_monograph_mathematics.py')]+[
            ROOT/'docs/monograph/review/revision/math-obligations/MonographLogic.lean',
            Path('/home/chakwong/python/MathDevMCP/src/mathdevmcp/lean_check.py'),
            Path('/home/chakwong/python/MathDevMCP/src/mathdevmcp/backend_env.py'),
            Path('/home/chakwong/.elan/toolchains/leanprover--lean4---v4.29.1/bin/lean')]


def inputs(phase):
    paths = []
    for base in ('src','tests','scripts','docs/implementation/interpretation-round11'):
        paths += [p for p in (ROOT/base).rglob('*') if p.is_file() and '__pycache__' not in p.parts
                  and p.suffix in ('.py','.java','.json','.in','.rules','.md') and 'repair-notes' not in p.parts]
    paths += [p for p in (ROOT/'docs/monograph').rglob('*') if p.is_file() and 'review' not in p.parts
              and p.suffix in ('.tex','.bib')]
    paths += list((ROOT/'.localresources/sfc').glob('*.pdf'))
    paths += [ROOT/'pyproject.toml',ROOT/'docs/plans/assurance-round11-execution.md']
    paths += document_dependencies()
    paths += list((Path('/home/chakwong/python/ResearchAssistant/src/research_assistant/ingest')).glob('*.py'))
    if phase not in ('M0','M1'):
        paths += [p for p in (TOOL/'tool-lock.json',TOOL/'model-lock.json',TOOL/'requirements.lock') if p.is_file()]
    files = {str(p):sha(p) for p in sorted(set(paths))}
    return {'files':files,'digest':hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()}


def capture_baseline():
    path = OUT/'protected-baseline.json'
    if path.exists():
        return
    protected = [p for p in (ROOT/'artifacts/interpretation/round10').rglob('*') if p.is_file() and 'work' not in p.parts and p.name!='.lock']
    allowance = ROOT/'artifacts/interpretation/round2/live-allowance.json'
    if allowance.exists(): protected.append(allowance)
    write(path, {'files':{str(p):sha(p) for p in protected}, 'new_model_calls':0})


def material_inputs(phase):
    """Phase-specific dependencies; result notes do not invalidate calculations."""
    common=[Path(__file__),DOC/'master-plan.json',DOC/'allowlist.json']
    paths=common+[ROOT/'scripts/assurance_routes.py']
    if phase=='M0':
        paths += document_dependencies()
        paths += [p for p in (ROOT/'docs/monograph').rglob('*') if p.suffix in ('.tex','.bib') and 'review' not in p.parts]
        paths += [ROOT/'scripts'/n for n in ('build_reader_facing_monograph.py','check_reader_facing_monograph.py','bind_monograph_citation_claims.py')]
        paths += [ROOT/'docs/papers/monograph-citation-archive.json',ROOT/'docs/monograph/review/revision/citation-reading.json',
                  ROOT/'docs/monograph/review/reader-facing/citation-occurrence-review.json']
    elif phase=='M1':
        paths += [ROOT/'scripts'/n for n in ('install_assurance_tools.py','prepare_assurance_models.py','assurance_tool_preflight.py')]
        paths += [DOC/'tool-requirements.in']
    else:
        paths += [TOOL/n for n in ('tool-lock.json','model-lock.json','requirements.lock')]
        paths += [ROOT/'src/legalmath/interpretation/assurance/diversity.py']
        if phase=='M2':
            paths += [ROOT/'scripts/assurance_source_routes.py',ROOT/'scripts/assurance_tool_preflight.py']
            paths += list((ROOT/'.localresources/sfc').glob('*.pdf'))
            paths += list(Path('/home/chakwong/python/ResearchAssistant/src/research_assistant/ingest').glob('*.py'))
        elif phase=='M3':
            paths += [ROOT/'scripts/assurance_formal_routes.py',ROOT/'tests/assurance/support.py',ROOT/'tests/search/support.py']
            paths += [p for p in (ROOT/'src').rglob('*') if p.is_file() and p.suffix in ('.py','.java','.json')]
        elif phase=='M4':paths += [ROOT/'scripts/assurance_evaluation_routes.py']
        else:
            paths += document_dependencies()
            paths += [p for base in ('src','tests','scripts') for p in (ROOT/base).rglob('*') if p.is_file() and p.suffix in ('.py','.java','.json')]
    return {str(p):sha(p) for p in sorted(set(paths)) if p.is_file()}


def invalidate_stale(s):
    for phase in PHASES:
        ps=s['phases'][phase]
        if ps['status']!='PASSED':continue
        last=read(ROOT/ps['attempts'][-1]['path'])
        if last.get('material_inputs')!=material_inputs(phase):
            for affected in PHASES[PHASES.index(phase):]:
                row=s['phases'][affected]
                if row['status']=='PASSED':
                    row['status']='STALE';row.setdefault('invalidations',[]).append({'at':now(),'changed_phase':phase})
            write(OUT/'state.json',s);refresh(phase,s)
            if (OUT/'final-report.json').exists():
                prior=read(OUT/'final-report.json')
                prior.update(engineering_status='STALE',invalidated_by=phase,invalidated_at=now())
                write(OUT/'final-report.json',prior)
            print('Invalidated stale phase and successors: '+phase,flush=True)
            return phase
    return None


def protect(s):
    baseline=read(OUT/'protected-baseline.json')
    if baseline is None: raise ValueError('Missing protected baseline')
    for name, expected in baseline['files'].items():
        if not Path(name).exists() or sha(name)!=expected: raise ValueError('Historical evidence changed: '+name)
    for ps in s['phases'].values():
        for entry in ps['attempts']:
            path=ROOT/entry['path']
            if sha(path)!=entry['sha256']: raise ValueError('Attempt manifest changed')
            for name, expected in read(path).get('artifact_sha256',{}).items():
                if not (path.parent/name).is_file() or sha(path.parent/name)!=expected:
                    raise ValueError('Attempt artifact changed: '+str(path.parent/name))


def commands(phase, attempt, install=False):
    def script(name, *args, tool=False):
        return [str(TOOLPY if tool else PY), str(ROOT/'scripts'/name), *map(str,args)]
    if install:
        if phase!='M1': raise ValueError('Installation only belongs to M1')
        return [('install', script('install_assurance_tools.py')),
                ('models', script('prepare_assurance_models.py',tool=True)),
                ('preflight', script('assurance_tool_preflight.py','--out',attempt/'preflight.json','--required',tool=True))]
    if phase=='M0': return [('document',[str(DOC_PY),str(ROOT/'scripts/assurance_routes.py'),'document','--out',str(attempt/'document')])]
    if phase=='M1': return [('preflight',script('assurance_tool_preflight.py','--out',attempt/'preflight.json','--required',tool=True))]
    if phase in ('M2','M3','M4'):
        route={'M2':'sources','M3':'formal','M4':'evaluation'}[phase]
        return [(route,script('assurance_routes.py',route,'--out',attempt/route,tool=True))]
    return [('document-links',[str(DOC_PY),str(ROOT/'scripts/assurance_routes.py'),'document','--out',str(attempt/'document')]),
            ('regression',[str(PY),'-m','pytest','tests','-q','--junitxml='+str(attempt/'tests.xml'),'-o','faulthandler_timeout=60']),
            ('summary',script('assurance_routes.py','summary','--out',attempt/'summary'))]


def allowed(argv, phase, attempt, install=False):
    policy=read(DOC/'allowlist.json')
    if argv not in [cmd for _,cmd in commands(phase,attempt,install)]: return False
    if len(argv)<2: return False
    if argv[1]=='-m':
        return argv[2:5]==['pytest','tests','-q'] and policy['allowed_pytest_targets']==['tests']
    rel=str(Path(argv[1]).relative_to(ROOT))
    return rel in policy['allowed_scripts'] and (rel not in ('scripts/install_assurance_tools.py','scripts/prepare_assurance_models.py') or install)


def audit():
    plan=read(DOC/'master-plan.json'); policy=read(DOC/'allowlist.json')
    if tuple(p['id'] for p in plan['phases'])!=PHASES: raise ValueError('Phase ordering differs')
    if not 1<=plan['max_failed_attempts_per_phase']<=3: raise ValueError('Repair budget invalid')
    if policy['model_calls'] or plan['release_eligible']: raise ValueError('Unreviewed live/release authority')
    for p in plan['phases']:
        if not p['tasks'] or not p['acceptance'] or not 1<=p['timeout']<=2400: raise ValueError('Incomplete phase')
        for install in ([False,True] if p['id']=='M1' else [False]):
            for _,argv in commands(p['id'],OUT/p['id']/'attempt-audit',install):
                if not allowed(argv,p['id'],OUT/p['id']/'attempt-audit',install): raise ValueError('Command not allowlisted: '+str(argv))
    review=read(DOC/'design-review.json')
    if review['verdict']!='PASS_WITH_LIMITS' or len(review['findings'])<7: raise ValueError('Skeptical review absent')
    return {'status':'PASS_WITH_LIMITS','plan_sha256':sha(DOC/'master-plan.json'),'review_sha256':sha(DOC/'design-review.json'),
            'checks':['baseline','proxy metrics','stop conditions','shared dependencies','environment isolation','fixed argv','artifact scope'],
            'independent_review':False,'release_eligible':False}


def refresh(phase,s):
    p=read(DOC/'master-plan.json')['phases'][PHASES.index(phase)]
    record={'phase':phase,'created_at':now(),'source':inputs(phase),'master_plan_sha256':sha(DOC/'master-plan.json'),
            'tasks':p['tasks'],'acceptance':p['acceptance'],'predecessors':{k:s['phases'][k] for k in PHASES[:PHASES.index(phase)]},
            'repairs':s['phases'][phase]['repairs'],'unresolved_evidence':'Semantic findings do not disappear on engineering pass.',
            'audit':audit(),'review_kind':'current-input author review; not independent legal acceptance'}
    write(OUT/phase/'next-plan.json',record)
    return record


def invoke(argv, log, timeout):
    env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1','PYTHONPATH':str(ROOT/'src')+os.pathsep+str(ROOT),
         'HF_HUB_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','OMP_NUM_THREADS':'2','TOKENIZERS_PARALLELISM':'false',
         'XDG_DATA_HOME':str(TOOL/'runtime-data'),'XDG_CACHE_HOME':str(TOOL/'runtime-cache')}
    if 'install_assurance_tools.py' in argv[1] or 'prepare_assurance_models.py' in argv[1]:
        env['HF_HUB_OFFLINE']='0'
    with log.open('w') as stream:
        process=subprocess.Popen(argv,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        write(log.with_suffix('.process.json'),{'pid':process.pid,'start':Path(f'/proc/{process.pid}/stat').read_text().split()[21]})
        try: return process.wait(timeout=timeout)
        except BaseException:
            os.killpg(process.pid,signal.SIGKILL); process.wait(); raise


def run_phase(phase,s,install=False):
    ps=s['phases'][phase]
    if ps['status']=='PASSED': raise ValueError('Completed phase cannot be overwritten')
    if ps['status'] in ('REPAIR_REQUIRED','RUNNING'): raise ValueError('Execute repair/recovery before retry')
    if len([a for a in ps['attempts'] if a['status']!='PASSED'])>=read(DOC/'master-plan.json')['max_failed_attempts_per_phase']:
        raise ValueError('Repair budget exhausted; revise the plan with a new explicit budget')
    if any(s['phases'][p]['status']!='PASSED' for p in PHASES[:PHASES.index(phase)]): raise ValueError('Predecessor incomplete')
    protect(s); reviewed=refresh(phase,s)
    if phase=='M1' and not install and not (TOOL/'tool-lock.json').exists(): raise ValueError('INSTALL_REQUIRED: exact approved install M1 command')
    attempt=OUT/phase/f"attempt-{len(ps['attempts'])+1:02}"
    attempt.mkdir(parents=True,exist_ok=False)
    write(attempt/'reviewed-plan.json',reviewed)
    record={'phase':phase,'status':'RUNNING','started_at':now(),'input':reviewed['source'],
            'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'environment':{'python':sys.version,'cpu_only':True,'gpu':'intentionally hidden','model_calls':0},
            'commands':[],'plan_file':str(DOC/'master-plan.json'),'random_seed':'N/A: deterministic engineering checks',
            'result_file':str(attempt/'run-manifest.json'),'authority':'ENGINEERING_ONLY','release_eligible':False}
    ps['status']='RUNNING'; write(OUT/'state.json',s); write(attempt/'run-manifest.json',record)
    start=time.monotonic()
    try:
        for name,argv in commands(phase,attempt,install):
            if not allowed(argv,phase,attempt,install): raise ValueError('Command denied by allowlist')
            print(phase+': '+name,flush=True)
            began=time.monotonic(); cmd={'name':name,'argv':argv,'started_at':now()}
            record['commands'].append(cmd);write(attempt/'run-manifest.json',record)
            code=invoke(argv,attempt/(name+'.log'),read(DOC/'master-plan.json')['phases'][PHASES.index(phase)]['timeout'])
            cmd.update(exit_code=code,wall_seconds=round(time.monotonic()-began,3))
            write(attempt/'run-manifest.json',record)
            if code:
                print((attempt/(name+'.log')).read_text()[-7000:],flush=True)
                raise ValueError(f'{name} failed: exit {code}')
        if inputs(phase)['digest']!=reviewed['source']['digest']: raise ValueError('Inputs changed during execution')
        protect(s);record['status']='PASSED'
    except (Exception,KeyboardInterrupt) as exc:
        record.update(status='FAILED',failure=str(exc) or type(exc).__name__)
    record.update(finished_at=now(),wall_seconds=round(time.monotonic()-start,3))
    record['material_inputs']=material_inputs(phase)
    record['artifact_sha256']={str(p.relative_to(attempt)):sha(p) for p in attempt.rglob('*') if p.is_file()
                               and p.name!='run-manifest.json' and 'work' not in p.relative_to(attempt).parts}
    write(attempt/'run-manifest.json',record)
    ps['attempts'].append({'path':str(attempt/'run-manifest.json'),'sha256':sha(attempt/'run-manifest.json'),'status':record['status']})
    ps['status']='PASSED' if record['status']=='PASSED' else 'REPAIR_REQUIRED';write(OUT/'state.json',s)
    if ps['status']!='PASSED':
        write(OUT/phase/'repair-request.json',{'phase':phase,'failure':record['failure'],'may_advance':False,
              'next_action':'Diagnose, execute repair and focused regression; repair command records verified execution before retry.'})
        raise ValueError(record['failure'])
    ix=PHASES.index(phase)
    if ix+1<len(PHASES):refresh(PHASES[ix+1],s)
    print(json.dumps({'phase':phase,'status':'PASSED','next_plan_refreshed':PHASES[ix+1] if ix+1<len(PHASES) else None}),flush=True)


def repair(phase,s,note):
    ps=s['phases'][phase]
    if ps['status']!='REPAIR_REQUIRED': raise ValueError('No failed phase')
    p=Path(note).resolve()
    if not p.is_relative_to(DOC) or not p.is_file(): raise ValueError('Repair note must be round-local JSON')
    n=read(p)
    if not n.get('changes') or not n.get('regression') or not n.get('summary'): raise ValueError('Executed repair and regression must be documented')
    target=OUT/phase/f"repair-{len(ps['repairs'])+1:02}";target.mkdir(parents=True,exist_ok=False)
    # The regression command is fixed; the note is evidence, never executable text.
    argv=[str(PY),'-m','pytest','tests/assurance/test_diverse_methods.py','-q']
    code=invoke(argv,target/'regression.log',180)
    evidence={'note':n,'note_sha256':sha(p),'source':inputs(phase),'argv':argv,'exit_code':code,'log_sha256':sha(target/'regression.log')}
    write(target/'repair.json',evidence)
    if code: raise ValueError('Repair regression failed')
    ps['repairs'].append({'path':str(target/'repair.json'),'sha256':sha(target/'repair.json')})
    ps['status']='REPAIRED_PENDING_REVIEW';write(OUT/'state.json',s);refresh(phase,s)


def recover(phase,s):
    ps=s['phases'][phase]
    if ps['status']!='RUNNING':raise ValueError('No interrupted phase')
    attempt=OUT/phase/f"attempt-{len(ps['attempts'])+1:02}"
    for p in attempt.glob('*.process.json'):
        record=read(p);stat=Path(f"/proc/{record['pid']}/stat")
        if stat.exists() and stat.read_text().split()[21]==record['start']:
            os.killpg(record['pid'],signal.SIGKILL)
    record=read(attempt/'run-manifest.json');record.update(status='FAILED',failure='SUPERVISOR_INTERRUPTED',finished_at=now())
    record['artifact_sha256']={str(p.relative_to(attempt)):sha(p) for p in attempt.rglob('*') if p.is_file() and p.name!='run-manifest.json' and 'work' not in p.relative_to(attempt).parts}
    write(attempt/'run-manifest.json',record)
    ps['attempts'].append({'path':str(attempt/'run-manifest.json'),'sha256':sha(attempt/'run-manifest.json'),'status':'FAILED'})
    ps['status']='REPAIR_REQUIRED';write(OUT/'state.json',s)


def finalize(s):
    """Bind the completed final phase without a self-referential manifest hash."""
    if any(s['phases'][p]['status']!='PASSED' for p in PHASES):
        raise ValueError('Cannot finalize incomplete phases')
    protect(s)
    evidence={}
    for phase in PHASES:
        entry=s['phases'][phase]['attempts'][-1];manifest=Path(entry['path'])
        data=read(manifest)
        if data.get('status')!='PASSED' or data.get('material_inputs')!=material_inputs(phase):
            raise ValueError('Cannot finalize stale phase: '+phase)
        evidence[phase]={'manifest':str(manifest),'sha256':sha(manifest),'status':'PASSED'}
    m5=Path(evidence['M5']['manifest'])
    result=read(m5.parent/'summary/result.json')
    if not result or result.get('engineering_status')!='PASS':
        raise ValueError('Final synthesis missing or failed')
    result.update(phase_evidence=evidence,finalized_at=now(),
                  state_sha256=sha(OUT/'state.json'),summary_sha256=sha(m5.parent/'summary/result.json'))
    result['next_phase_plan']['refresh_from']=evidence
    write(OUT/'final-report.json',result)
    write(OUT/'next-phase-plan.json',result['next_phase_plan'])
    print(json.dumps({'engineering_status':'PASS','report':str(OUT/'final-report.json'),
                      'assurance_status':result['assurance_status'],'release_eligible':False}),flush=True)


def main():
    ap=ArgumentParser(description=__doc__)
    ap.add_argument('operation',choices=['audit','preflight','status','refresh','run','execute','install','repair','recover'])
    ap.add_argument('phase',nargs='?',choices=PHASES);ap.add_argument('--note')
    args=ap.parse_args()
    if args.operation in ('execute','audit','preflight','status') and (args.phase or args.note): ap.error('No additional arguments accepted')
    if args.operation=='install' and (args.phase!='M1' or args.note):ap.error('Exact install M1 command required')
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);s=state();capture_baseline()
        if args.operation=='status':print(json.dumps(s,indent=2));return
        result=audit();protect(s)
        if args.operation in ('audit','preflight'):
            result.update(toolchain_installed=(TOOL/'tool-lock.json').exists(),phases=list(PHASES))
            write(OUT/(args.operation+'.json'),result);print(json.dumps(result,indent=2));return
        if args.operation in ('execute','run','install'):
            invalidate_stale(s)
        if args.operation=='execute':
            for p in PHASES:
                if s['phases'][p]['status']!='PASSED':run_phase(p,s)
            finalize(s)
            return
        if not args.phase:ap.error('Phase required')
        if args.operation=='refresh':refresh(args.phase,s)
        elif args.operation=='repair':repair(args.phase,s,args.note or '')
        elif args.operation=='recover':recover(args.phase,s)
        else:run_phase(args.phase,s,install=args.operation=='install')


if __name__=='__main__':
    main()
