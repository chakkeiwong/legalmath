"""Independent regression preparation and final documentary delivery checks."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
import fcntl
import shutil
import sys
from zipfile import ZipFile,ZIP_DEFLATED
from run_assurance_gap_master import ROOT,OUT,GRANT,PYTHON,save,read,sha,receipt,command,state,checked,allowance,phase_status


def unchanged(snapshot,*,code_only=False,permit_concurrent_prospectus=False):
    target=Path(snapshot['path']);concurrent=[]
    permitted={'src/legalmath/prospectus/loss_absorption_reader.py','src/legalmath/prospectus/loss_absorption_witnesses.py'}
    for name,expected in snapshot['inputs'].items():
        if code_only and not name.startswith(('src/','tests/')) and name!='pyproject.toml':continue
        if sha(target/name)!=expected:raise RuntimeError('Frozen source changed: '+name)
        if code_only and sha(ROOT/name)!=expected:
            if not permit_concurrent_prospectus or name not in permitted:
                raise RuntimeError('Live implementation differs from tested source: '+name)
            concurrent.append({'path':name,'tested_sha256':expected,'current_sha256':sha(ROOT/name)})
    return concurrent


def regression():
    from assurance_gap_checks import tests
    snapshots=sorted((OUT/'G7r').glob('attempt-*/snapshot.json')) or sorted((OUT/'G7').glob('attempt-*/snapshot.json'))
    if not snapshots:raise RuntimeError('Wait for the G7 snapshot before regression preparation')
    frozen=read(snapshots[-1]);unchanged(frozen,code_only=True)
    base=OUT/'regression';base.mkdir(exist_ok=True)
    with (base/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        attempts=sorted(base.glob('attempt-*'))
        if attempts:
            previous=read(attempts[-1]/'result.json')
            if previous['status']=='PASSED' and previous['snapshot']==receipt(snapshots[-1]):return previous
            repair=read(base/f'repair-{len(attempts)}.json')
            if repair['prior']!=receipt(attempts[-1]/'result.json') or not repair['cause'] or not repair['change']:
                raise RuntimeError('Failed regression requires a causal repair')
            check=ROOT/repair['focused_check']['path']
            if sha(check)!=repair['focused_check']['sha256'] or read(check)['exit_code']!=0:
                raise RuntimeError('Execute the focused repair before another full regression')
        if len(attempts)>=3:raise RuntimeError('Regression preparation attempts exhausted')
        work=base/f'attempt-{len(attempts)+1:02d}';work.mkdir()
        result={'status':'RUNNING','snapshot':receipt(snapshots[-1]),'plan':receipt(ROOT/'docs/plans/systematic-challenges-execution.md'),
            'grant_before':allowance(),'cpu_only':True,'seed':'N/A; regression properties and explicit deterministic fixtures',
            'commit':frozen['commit'],'environment':str(PYTHON),'started_at':datetime.now(timezone.utc).isoformat()}
        save(work/'result.json',result)
        try:
            result['tests']=tests(work,[],cwd=Path(frozen['path']),timeout=3600)
            unchanged(frozen,code_only=True);result['status']='PASSED'
        except BaseException as exc:result.update(status='FAILED',error=type(exc).__name__,details=str(exc))
        result['finished_at']=datetime.now(timezone.utc).isoformat()
        result['grant_after']=allowance();save(work/'result.json',result)
        if result['status']!='PASSED':raise RuntimeError('Regression failed; inspect retained result')
        return result


def protected_content():
    baseline=read(OUT/'manuscript-baseline.json')
    if sha(OUT/'manuscript-baseline.zip')!=baseline['archive_sha256']:raise RuntimeError('Protected manuscript changed')
    with ZipFile(OUT/'manuscript-baseline.zip') as archive:
        for name in archive.namelist():
            old=archive.read(name).decode().splitlines();current=iter((ROOT/name).read_text().splitlines())
            if not all(any(line==candidate for candidate in current) for line in old):
                raise RuntimeError('Protected content removed: '+name)
    return len(baseline['files'])


def verify(work):
    prior=sorted((OUT/'regression').glob('attempt-*/result.json'))[-1]
    result=read(prior)
    if result['status']!='PASSED':raise RuntimeError('Full regression must pass before G8')
    frozen=read(ROOT/result['snapshot']['path'])
    concurrent=unchanged(frozen,code_only=True,permit_concurrent_prospectus=True)
    protected=protected_content();target=Path(frozen['path'])
    # Documentation is refreshed after the live result. Tested code is immutable.
    for p in (ROOT/'docs/monograph').rglob('*'):
        if p.is_file() and p.suffix in ('.tex','.bib') and 'review' not in p.relative_to(ROOT/'docs/monograph').parts:
            dest=target/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
    doc_inputs={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'docs/monograph').rglob('*')
                if p.is_file() and p.suffix in ('.tex','.bib') and 'review' not in p.relative_to(ROOT/'docs/monograph').parts}
    command(['/home/chakwong/miniconda3/envs/tfgpu/bin/python3','scripts/build_reader_facing_monograph.py'],
            work,'documents',cwd=target,timeout=300)
    if any(sha(ROOT/n)!=h or sha(target/n)!=h for n,h in doc_inputs.items()):raise RuntimeError('Document inputs changed during build')
    files=['docs/monograph/monograph.pdf','docs/monograph/technical-companion.pdf',
           'docs/monograph/process-guide.pdf','docs/proposal/proposal.pdf','docs/proposal/monograph.pdf',
           'docs/proposal/technical-companion.pdf']
    # The process exporter supplies its actual output filename in the inventory.
    missing=[n for n in files if not (target/n).exists()]
    if missing:raise RuntimeError('Expected document missing: '+str(missing))
    output={'status':'REGRESSION_AND_DOCUMENT_BUILD_CHECKED','regression':receipt(prior),
        'snapshot':frozen['path'],'document_inputs':doc_inputs,'protected_files':protected,
        'generated_review_outputs':{str(p.relative_to(target)):sha(p) for p in (target/'docs/monograph/review/reader-facing').glob('*-expanded.tex')},
        'pdfs':{n:sha(target/n) for n in files},'tests':result['tests'],
        'rendered_inspection':'PENDING','legal_correctness':'NOT_ESTABLISHED',
        'concurrent_prospectus_changes':concurrent,
        'regression_scope':'Exact archived snapshot; current independent prospectus changes are not covered by this regression'}
    with ZipFile(work/'delivered-inputs.zip','w',ZIP_DEFLATED) as archive:
        current_helpers={'scripts/assurance_gap_delivery.py','scripts/run_assurance_gap_master.py','docs/plans/systematic-challenges-execution.md'}
        for name in sorted((set(frozen['inputs'])|set(doc_inputs))-current_helpers):
            if (target/name).is_file():archive.write(target/name,name)
        for name in sorted(current_helpers):
            archive.write(ROOT/name,name)
    save(work/'result.json',output);return output


def freeze_worker(repo,target,verification):
    from legalmath.interpretation.assurance.grants import GrantSlice
    from legalmath.interpretation.assurance import investigation_observations as observations
    from legalmath.qualification import prospective
    from assurance_gap_live import runner
    repo=Path(repo);target=Path(target)
    grant=repo/'artifacts/assurance-new-grant/2026-09-29/grant.json'
    instance=runner(repo,repo/'artifacts/assurance-gap-closure/2026-09-30/future-investigations',
        GrantSlice(grant,grant.parent/'future-pilot-allowance.json',120))
    old=read(grant.parent/'whole-method-window/freeze.json')
    development=[*old['development_sources'],read(repo/'artifacts/assurance-gap-closure/2026-09-30/G5r/attempt-01/result.json')['26ec22']['source']['sha256']]
    source_manifest=read(repo/'examples/multi-circular-2026/source-freeze.json')
    for values in source_manifest.values():
        if isinstance(values,list):
            for item in values:
                if isinstance(item,dict):
                    development.extend(item[k] for k in ('raw_sha256','text_sha256') if k in item)
    end=(datetime.now(timezone.utc)+timedelta(days=30)).isoformat().replace('+00:00','Z')
    spec=observations.freeze(target,instance,old['families'],ends_at=end,development_sources=development)
    save(target/'execution-configuration.json',{'verified_phase':verification,'snapshot_code':str(ROOT),
        'method':observations.method(instance),'old_window_preserved':str(grant.parent/'whole-method-window'),
        'uses_original_future_arm':str(grant.parent/'future-pilot-allowance.json')})
    return prospective.report(target,spec['window_hash'])


def deliver():
    phases=state()['phases']
    for name in ('G0','G1','G2','G3','G4','G5','G5r','G6','G7','G7r','G8'):
        if phase_status(phases[name][-1]) not in ('PASSED','PARTIAL_VERIFIED'):raise RuntimeError('Incomplete phase: '+name)
    phase=checked(phases['G8'][-1]);value=phase['result'];target=Path(value['snapshot'])
    visual=read(OUT/'rendered-inspection.json')
    if visual.get('pdfs')!=value['pdfs'] or visual.get('status')!='INSPECTED':raise RuntimeError('Inspect the actual rendered new pages before delivery')
    if any(sha(ROOT/n)!=h for n,h in value['document_inputs'].items()):raise RuntimeError('Manuscript changed after verification')
    for name,h in value['pdfs'].items():
        if sha(target/name)!=h:raise RuntimeError('Verified PDF changed')
        shutil.copyfile(target/name,ROOT/name)
    window=OUT/'whole-method-window'
    if not window.exists():
        # Import and execute the frozen method, never the mutable live checkout.
        shutil.copyfile(ROOT/'scripts/assurance_gap_delivery.py',target/'scripts/assurance_gap_delivery.py')
        command([PYTHON,'scripts/assurance_gap_delivery.py','freeze-worker',ROOT,window,
            phases['G8'][-1]['sha256']],OUT,'freeze-window',cwd=target,timeout=180)
    result={'status':'DELIVERED','verification':phases['G8'][-1],'rendered_inspection':receipt(OUT/'rendered-inspection.json'),
        'pdfs':value['pdfs'],'tests':value['tests'],'future_window':receipt(window/'freeze.json'),
        'grant':allowance(),'legal_correctness':'NOT_ESTABLISHED'}
    save(OUT/'delivery.json',result);return result


if __name__=='__main__':
    if len(sys.argv)==5 and sys.argv[1]=='freeze-worker':
        save(Path(sys.argv[3]).parent/'future-window-result.json',freeze_worker(sys.argv[2],sys.argv[3],sys.argv[4]))
    else:raise SystemExit('Use the reviewed master wrapper')
