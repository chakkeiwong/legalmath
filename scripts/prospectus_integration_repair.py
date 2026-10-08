"""Fixed, bounded prospectus integration repair commands; no shell/URL arguments."""
import argparse
import fcntl
import hashlib
import inspect
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT/'src') not in sys.path:
    sys.path.insert(0,str(ROOT/'src'))
OUT = ROOT / 'docs/implementation/prospectus-integration-repair'
PLAN = ROOT / 'docs/plans/prospectus-integration-repair-2026-10-08.md'
SIDECAR = Path('/tmp/prospectus-adoption-tools/bin/python')
PHASES = ('preflight', 'check', 'layout', 'authoring', 'feasibility', 'analyze')


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


def command(folder, name, argv, timeout=180):
    try:
        run = subprocess.run(argv, cwd=ROOT, env={**os.environ, 'CUDA_VISIBLE_DEVICES': '-1',
                             'PYTHONPATH': str(ROOT/'src'), 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1'},
                             capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        def decoded(value):
            return value.decode(errors='replace') if isinstance(value,bytes) else value or ''
        (folder/(name+'.log')).write_text(decoded(exc.stdout)+decoded(exc.stderr))
        save(folder/(name+'-command.json'), {'argv':argv,'returncode':None,'timeout_seconds':timeout})
        raise
    (folder/(name+'.log')).write_text(run.stdout + run.stderr)
    save(folder/(name+'-command.json'), {'argv': argv, 'returncode': run.returncode})
    if run.returncode:
        raise RuntimeError(f'{name} failed: see {folder/name}.log')
    return run.stdout


def methods(phase):
    paths = [Path(__file__), PLAN]
    patterns={
        'preflight': ['scripts/prospectus_inception.py'],
        'layout': ['scripts/prospectus_adoption_sidecar.py','src/legalmath/prospectus/successor/layout_adapter.py',
                   'src/legalmath/prospectus/successor/anchors.py'],
        'authoring': ['scripts/prospectus_inception.py','scripts/prospectus_integration_authoring.py',
                     'scripts/prospectus_integration_codec.py','src/legalmath/prospectus/successor/annotation*.py'],
        'feasibility': ['scripts/prospectus_tool_feasibility.py','scripts/prospectus_adoption_sidecar.py',
                        'src/legalmath/prospectus/successor/fixed_coupon.py','src/legalmath/prospectus/successor/adoption_trials.py'],
        'check': ['src/legalmath/**/*.py','src/legalmath/**/*.json','src/legalmath/**/*.java','src/legalmath/**/*.lean',
                  'tests/prospectus_successor/*.py','tests/prospectus_integration/*.py','tests/prospectus_inception/*.py',
                  'scripts/prospectus*.py','scripts/verify_prospectus_adoption.py','pyproject.toml'],
        'analyze': ['scripts/prospectus_integration_jobs.py'],
    }
    for pattern in [*patterns[phase],'src/legalmath/prospectus/successor/contracts.py']:
        paths.extend(ROOT.glob(pattern))
    result={str(p.relative_to(ROOT)): sha(p) for p in sorted(set(paths)) if '__pycache__' not in p.parts}
    if phase not in ('preflight','check'):
        from scripts import prospectus_integration_jobs as jobs
        result['function:jobs.'+phase]=hashlib.sha256(inspect.getsource(getattr(jobs,phase)).encode()).hexdigest()
    return result


def tree_sha(path):
    if not path.is_dir():raise ValueError('Missing runtime distribution tree: '+str(path))
    entries={str(p.relative_to(path)):sha(p) for p in sorted(path.rglob('*'))
             if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    return hashlib.sha256(json.dumps(entries,sort_keys=True).encode()).hexdigest()


def inputs(phase):
    # Bind executable/runtime bytes, including changed code under unchanged versions.
    result={'application_python':sha(sys.executable),'sidecar_python':sha(SIDECAR),
        'application_site':tree_sha(ROOT/'.venv/lib/python3.11/site-packages'),
        'sidecar_site':tree_sha(SIDECAR.parent.parent/'lib/python3.11/site-packages')}
    paths=[]
    if phase in ('preflight','authoring'):
        from scripts.prospectus_inception import runtime_identity,OUT as inception_out
        result['inception_runtime']=runtime_identity()
        paths += [inception_out/n for n in ('toolchain.json','template.zip','template-provenance.json')]
    if phase in ('preflight','layout'):
        base=ROOT/'docs/implementation/prospectus-adoption'
        paths += [base/'phases/A0/attempt-007/raw-units.json',base/'phases/A3/attempt-005/layout-input.json',
                  base/'phases/A3/attempt-005/critical-spans-before-prediction.json',OUT/'margin-review.json']
        data=json.loads((base/'phases/A3/attempt-005/layout-input.json').read_text())
        paths += [ROOT/r['path'] for r in data['pages']]
        receipt=base/'tool-setup/layout-model/receipt.json';paths.append(receipt)
        for row in json.loads(receipt.read_text())['files']:
            if sha(row['file'])!=row['sha256']:raise ValueError('Pinned model bytes changed')
            result[row['file']]=row['sha256']
        margin=json.loads((OUT/'margin-review.json').read_text())
        paths.append(ROOT/margin['image'])
    if phase=='feasibility':
        paths += [p for p in (ROOT/'docs/research/prospectus-adoption-2026-10-07/sources').rglob('*')
                  if p.is_file() and (p.parent.name.startswith(('actus','cdm','quantlib')))]
        paths += [p for p in (OUT/'official-sources').glob('*') if p.is_file()]
    if phase=='check':
        from legalmath.prospectus.successor.adoption_jobs import bindings
        result['adoption_declared_inputs']=hashlib.sha256(json.dumps(bindings(ROOT,'A0'),sort_keys=True).encode()).hexdigest()
        paths.append(OUT/'margin-review.json')
    if phase=='analyze':
        for parent in PHASES[:-1]:
            candidates=sorted(OUT.glob(parent+'-*/manifest.json'))
            if candidates:paths.append(candidates[-1])
    result['files']={str(p.relative_to(ROOT)):sha(p) for p in sorted(set(paths))}
    return result


def verify_outputs(path,receipt):
    actual={str(p.relative_to(path.parent)):sha(p) for p in path.parent.rglob('*')
            if p.is_file() and p!=path}
    if actual!=receipt['outputs']:
        raise ValueError('Changed, missing or added evidence in '+str(path.parent))


def current(phase):
    prior=sorted(OUT.glob(phase+'-*/manifest.json'))
    if not prior:return None
    path=prior[-1];receipt=json.loads(path.read_text())
    if receipt['status']=='RUNNING':return None  # Interrupted attempt is retained, never reused.
    verify_outputs(path,receipt)
    if receipt['status']!='PASS' or receipt.get('method')!=methods(phase) or receipt.get('inputs')!=inputs(phase):
        return None
    if phase=='analyze' and any(current(parent) is None for parent in PHASES[:-1]):
        return None
    return path


def refresh(phase,folder,status,reused=False):
    save(OUT/'next-phase.json',{'parent':str(folder.relative_to(ROOT)),
         'parent_sha256':sha(folder/'manifest.json'),'status':status,'reused':reused,
         'next':'Repair this phase before its dependents; independent phases may continue' if status!='PASS'
         else list(PHASES[PHASES.index(phase)+1:]),'legal_acceptance':'PENDING'})


def execute(phase):
    OUT.mkdir(parents=True, exist_ok=True)
    # Acquisition has separate immutable receipts; freeze its completed inputs
    # before the feasibility comparison, rather than treating downloads as drift.
    if phase=='feasibility':
        from scripts.prospectus_tool_feasibility import refresh as acquire_sources
        acquire_sources()
    prior = sorted(OUT.glob(f'{phase}-*/manifest.json'))
    reusable=current(phase)
    if reusable:
        refresh(phase,reusable.parent,'PASS',True)
        print(json.dumps({'phase':phase,'status':'PASS','execution':'REUSED','folder':str(reusable.parent.relative_to(ROOT))}),flush=True)
        return json.loads((reusable.parent/'result.json').read_text())
    identity = methods(phase)
    if sum(json.loads(p.read_text()).get('method') == identity for p in prior) >= 3:
        raise RuntimeError('Three unchanged-method attempts exhausted; repair before retry')
    if phase == 'authoring' and len(prior) >= 12:
        raise RuntimeError('Twelve authoring attempts exhausted')
    def storage_bytes():
        roots=[OUT,*list((ROOT/'.localresources/prospectus-inception').glob('authoring-*'))]
        return sum(p.stat().st_size for root in roots for p in root.rglob('*') if p.is_file())
    if storage_bytes() > 2_000_000_000:
        raise RuntimeError('New evidence exceeds 2 GB limit')
    index=max((int(p.name.rsplit('-',1)[1]) for p in OUT.glob(phase+'-*') if p.is_dir()),default=0)+1
    folder = OUT / f'{phase}-{index:03d}'
    folder.mkdir()
    start = time.monotonic()
    manifest = {'phase': phase, 'plan': str(PLAN.relative_to(ROOT)), 'method': identity,
                'command': ['python3', '-m', 'scripts.prospectus_integration_repair', phase],
                'git_commit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                'environment': sys.executable, 'cpu_gpu': 'CPU; CUDA_VISIBLE_DEVICES=-1',
                'random_seeds': 'Deterministic assertions; pretrained layout weights unchanged',
                'inputs':inputs(phase),'result_file':str((folder/'result.json').relative_to(ROOT)),
                'status': 'RUNNING'}
    save(folder/'manifest.json',manifest)
    def expired(signum, frame):
        raise TimeoutError('Phase exceeded 1500-second bound')
    previous = signal.signal(signal.SIGALRM, expired)
    signal.alarm(1500)
    try:
        if phase == 'preflight':
            from scripts.prospectus_inception import runtime_identity
            result = {'status':'PASS', 'runtime':runtime_identity(), 'sidecar':str(SIDECAR),
                      'baseline':'4dfd34071', 'scope':'Runtime identity only; workflow tested in separate authoring phase'}
        elif phase == 'check':
            command(folder,'application',[sys.executable,'-m','pytest','-q','tests/prospectus_successor',
                     'tests/prospectus_integration','--junitxml='+str(folder/'application.xml')],300)
            command(folder,'cassis',[str(SIDECAR),'-m','unittest','discover','-s','tests/prospectus_inception'],120)
            command(folder,'authoring-codec',[str(SIDECAR),'-m','unittest','discover','-s','tests/prospectus_integration',
                    '-p','test_authoring.py'],120)
            command(folder,'adoption-installed',[sys.executable,'-m','scripts.verify_prospectus_adoption'],600)
            base=ROOT/'docs/implementation/prospectus-adoption/verification'
            record=sorted(base.glob('attempt-*/manifest.json'))[-1]
            save(folder/'adoption-verification.json',{'manifest':str(record.relative_to(ROOT)),
                'sha256':sha(record),'receipt':json.loads(record.read_text())})
            result={'status':'PASS','scope':'Regression, adversarial integration, installed checks and seven-phase adoption replay'}
        else:
            from scripts import prospectus_integration_jobs as jobs
            result=getattr(jobs,phase)(folder)
        if methods(phase)!=identity or inputs(phase)!=manifest['inputs']:
            raise ValueError('Method or input/runtime changed during execution; fresh attempt required')
        if storage_bytes()>2_000_000_000:raise ValueError('New evidence/runtime exceeds 2 GB limit')
        save(folder/'result.json',result)
        manifest['status']=result['status']
    except Exception:
        manifest['status']='FAILED'
        (folder/'failure.txt').write_text(traceback.format_exc())
        raise
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)
        manifest['wall_seconds']=time.monotonic()-start
        manifest['outputs']={str(p.relative_to(folder)):sha(p) for p in sorted(folder.rglob('*'))
                             if p.is_file() and p!=folder/'manifest.json'}
        save(folder/'manifest.json',manifest)
        refresh(phase,folder,manifest['status'])
        print(json.dumps({'phase':phase,'status':manifest['status'],'folder':str(folder.relative_to(ROOT))}),flush=True)
    return result


def main():
    os.environ['CUDA_VISIBLE_DEVICES']='-1'
    if Path.cwd().resolve()!=ROOT:
        raise ValueError('Run from the bound prospectus worktree')
    application = ROOT/'.venv/bin/python'
    if Path(sys.executable).absolute()!=application.absolute():
        os.execv(str(application),[str(application),'-m','scripts.prospectus_integration_repair',*sys.argv[1:]])
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=[*PHASES,'run','status','authorize'])
    action=parser.parse_args().action
    OUT.mkdir(parents=True,exist_ok=True)
    lock=(OUT/'.runner.lock').open('a+')
    if action!='status':
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise SystemExit('Another integration phase is active; retry after it completes')
    if action=='authorize':
        # Only this explicit action writes outside the worktree, after platform approval.
        source=OUT/'allow.rules'
        destination=Path('/home/chakwong/.codex/rules/legalmath-prospectus-integration-repair.rules')
        content=source.read_bytes()
        if destination.exists() and destination.read_bytes()!=content:
            raise ValueError('Existing rule differs; inspect before replacing')
        destination.write_bytes(content)
        save(OUT/'rule-installation.json',{'source':str(source),'destination':str(destination),
             'sha256':sha(destination),'policy_change':'NARROW_FIXED_COMMANDS_ONLY'})
        print('Installed narrow integration-repair rules')
    elif action=='status':
        print(json.dumps({'phases':[{ 'phase':p,'current':bool(current(p))} for p in PHASES],
            'next':json.loads((OUT/'next-phase.json').read_text()) if (OUT/'next-phase.json').exists() else None},indent=2))
    elif action=='run':
        failures=[]
        for phase in PHASES:
            try:
                outcome=execute(phase)
                if outcome['status']!='PASS':failures.append({'phase':phase,'reason':outcome['status']})
            except Exception as exc:
                failures.append({'phase':phase,'reason':str(exc)})
                if phase=='preflight':break
        if failures:
            print(json.dumps({'failures':failures}),flush=True)
            raise SystemExit(1)
    else:
        if execute(action)['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':
    main()
