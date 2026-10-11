"""Admit the retained coupon candidate only after committed pledge validation."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[4]
BASE=ROOT/'docs/implementation/prospectus-integration-closure'
PACKAGE=BASE/'coupon-anchor'
CANDIDATE=PACKAGE/'candidate'
PLAN=ROOT/'docs/plans/prospectus-coupon-anchor-repair-2026-10-10.md'
os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.successor import closure_program

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path,record):
    path.write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n')

def main():
    if sys.flags.optimize:
        raise RuntimeError('Admission requires Python assertions enabled')
    assert ROOT.name=='bond-gap-closure', ROOT
    assert subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()=='feature/prospectus-evidence-master'
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(), 'Commit the completed predecessor and preserve any unrelated changes before admission'
    target=PACKAGE/'execution-admission.json'
    assert not target.exists(), 'Inspect existing admission before any retry'
    predecessor=BASE/'basf-status-pledge'
    progress=read(predecessor/'validation-progress.json')
    assert progress['status']=='ENGINEERING_VALIDATION_COMPLETE' and progress['active'] is None
    index=read(predecessor/'execution-manifest.json')
    assert index['decision']=='PASS for bounded engineering validation' and index['program_complete'] is False
    assert index['external_acceptance']=='NOT_ESTABLISHED'
    current=closure_program.status(ROOT)
    assert len(current['phases'])==9
    for row in current['phases']:
        assert row['current'] and row['artifact_valid'] and row['execution']=='COMPLETED' and row['engineering_checks']=='PASS',row
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    committed=subprocess.check_output(['git','show','HEAD:'+str((predecessor/'execution-manifest.json').relative_to(ROOT))],cwd=ROOT)
    assert hashlib.sha256(committed).hexdigest()==sha(predecessor/'execution-manifest.json')
    for entry in index['exercises']:
        folder=ROOT/entry['directory']
        manifest=read(folder/'manifest.json')
        files={str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file() and p.name!='manifest.json'}
        assert files==set(manifest['files'])
        assert all(sha(folder/p)==h for p,h in manifest['files'].items())
        result=read(folder/'result.json')
        assert result['status']=='PASS' and all(sha(ROOT/p)==h for p,h in result['method'].items())
    archive=read(PACKAGE/'archive-manifest.json')
    assert all(sha(PACKAGE/p)==h for p,h in archive['files'].items())
    baseline=read(CANDIDATE/'baseline.json')
    assert all(sha(ROOT/p)==h for p,h in baseline['files'].items()), 'Candidate snapshot changed; review a new diff before integrating'
    diagnostic=PACKAGE/'candidate-diagnostic-001'
    assert all(sha(diagnostic/p)==h for p,h in read(diagnostic/'manifest.json')['files'].items())
    result,started=read(diagnostic/'result.json'),read(diagnostic/'started.json')
    assert result['status']=='PASS' and result['method_unchanged']
    assert result['counts']==dict(tests=59,failures=0,errors=0,skipped=0)
    methods=started['candidate_method']
    expected={*baseline['files'], 'src/legalmath/prospectus/successor/coupon_dates.py',
              'tests/prospectus_successor/test_closure_coupon_anchor.py'}
    assert set(methods)==expected
    for path,h in methods.items():
        assert sha(CANDIDATE/path)==h
        output=ROOT/path
        assert output.resolve().is_relative_to(ROOT.resolve())
        if path not in baseline['files']:
            assert not output.exists(),path
    record=dict(version='coupon-anchor-execution-admission.v1',status='INTEGRATING',
        admitted_at=datetime.now(timezone.utc).isoformat(),baseline_git_commit=head,
        predecessor_execution_index_sha256=sha(predecessor/'execution-manifest.json'),
        predecessor_receipts=[{k:row[k] for k in ('phase','directory','receipt_sha256')} for row in current['phases']],
        candidate_archive_sha256=sha(PACKAGE/'archive-manifest.json'),
        original_files=baseline['files'],candidate_files=methods,
        preliminary_diagnostic=dict(manifest_sha256=sha(diagnostic/'manifest.json'),counts=result['counts'],wall_seconds=result['wall_seconds'],
            scope='Isolated candidate evidence; plan scheduling later revised, no claim of completed worktree or installed validation'),
        plan_file=str(PLAN.relative_to(ROOT)),plan_before_admission_sha256=sha(PLAN),
        cpu_gpu='CPU; GPU intentionally hidden; no new network/model calls',
        decision='Admit explicit versioned anchor repair against the completed committed pledge comparator',
        external_acceptance='NOT_ESTABLISHED',driver_sha256=sha(Path(__file__)))
    save(target,record)
    for path in sorted(methods):
        output=ROOT/path
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_bytes((CANDIDATE/path).read_bytes())
    text=PLAN.read_text()
    assert '## Final execution admission' not in text
    text=text.replace('# Coupon anchor preservation: reviewed design pending execution admission',
                      '# Coupon anchor preservation: admitted execution',1)
    PLAN.write_text(text+f'''
## Final execution admission

The completed status/pledge comparator is committed as `{head}`. Its nine
phase receipts are current, valid engineering PASS; consumer and installed
manifests were freshly verified without rerunning their passing checks.
The protected coupon candidate and its exact source snapshot match the
admitted worktree. Integration copied precisely the nine reviewed files.
`coupon-anchor/execution-admission.json` retains the predecessor receipts,
candidate identities, actual baseline and scope.

The isolated 59-control diagnostic is preliminary, historical evidence under
its recorded plan. The later regression-scheduling revision changes execution
grouping, not its tested implementation. Now verify the actual worktree with
the new coupon file and the existing finance controls under 120 seconds,
then run the installed application with `--basf-status-pledge --coupon-anchor`
under the existing 1,200-second/200-MB limit. Complete the partitioned
regression and serial phase refresh described above. Retain every actual
result and stop only for the declared validity or resource vetoes.

Skeptical admission audit: PASS. Original-anchor evidence, both service routes,
profile pairing, actual date/classification boundaries, independent fractions,
legacy restrictions and conditional entitlement are checked in the candidate.
Worktree and installed execution remain required. Neither independent legal
acceptance nor real-instrument convention support is inferred.
''')
    reset=BASE/'RESET.md'
    reset.write_text(f'''# Active coupon-anchor repair

The status/negative-pledge package is committed as `{head}`; its final evidence
index and all current engineering phase receipts were verified at admission.
The reviewed coupon candidate is integrated under
`docs/plans/prospectus-coupon-anchor-repair-2026-10-10.md`.
See `coupon-anchor/execution-admission.json` for exact baseline and file hashes.
The preliminary isolated diagnostic passed 59 checks; actual worktree and
installed validation are pending. The next commands and partitioned coverage
contract are in the admitted plan. Do not edit bound methods during a run.

The new profile requires a source-bound original anchor and preserves its day
through February. Both service routes and selected-term version pairing are
included. Full selected contracts remain regular-only; direct stub arithmetic
is hypothetical. No real entitlement or independent legal acceptance follows.
Continue through passing checks without requesting routine approval.

'''+reset.read_text())
    run=subprocess.run([str(ROOT/'.venv/bin/python'),'-m','scripts.prospectus_delivery','--program','closure','refresh'],
        cwd=ROOT,env=os.environ.copy(),capture_output=True,text=True,timeout=60)
    (PACKAGE/'admission-refresh.log').write_text(run.stdout+run.stderr)
    assert run.returncode==0,run.stderr
    record.update(status='INTEGRATED_VALIDATION_PENDING',plan_sha256=sha(PLAN))
    save(target,record)
    print(json.dumps({'status':record['status'],'baseline_commit':head,'files':len(methods),'plan':record['plan_file']}))

if __name__=='__main__':
    main()
