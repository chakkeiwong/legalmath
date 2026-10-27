"""Install only the reviewed candidate, preserving unrelated work and old bytes."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path('/home/chakwong/python/legalmath')
CANDIDATE=Path('/tmp/legalmath-p14-repair-20261023')
HERE=Path('artifacts/legal-mission-control/2026-10-23/p14-deployment')
sys.path.insert(0,str(ROOT))
from scripts.legal_mission_execution import read,save,ref,verify,require


def run():
    check=read(ROOT/HERE/'context-preflight.json')
    imported=read(ROOT/HERE/'product-preflight.json')
    require(check['verdict']=='PASS' and check['assignments']==672
        and check['preparation_failures']==0 and not check['capacity_failures']
        and check['provider_calls']==0, 'Full context preparation did not pass')
    require(imported['verdict']=='PASS' and imported['provider_calls']==0
        and imported['imported']['validated_individuals']==1699
        and imported['imported']['failed_continuations']==52
        and imported['imported']['checkpoint']==ref(ROOT,HERE/'individual-reviews.json')
        and imported.get('authority_checked') is False, 'Actual product import did not pass on current checkpoint')
    suites=[]
    for name in ('local-tests.xml','admission-tests.xml'):
        suite=ET.parse(ROOT/HERE/name).getroot()
        leaves=list(suite.iter('testsuite'))
        require(leaves and all(int(r.attrib.get('errors',0))==int(r.attrib.get('failures',0))==0
            for r in leaves), 'Local tests failed: '+name)
        suites.append(dict(file=ref(ROOT,HERE/name),tests=sum(int(r.attrib['tests']) for r in leaves),
            seconds=sum(float(r.attrib['time']) for r in leaves)))
    baseline=read(ROOT/HERE/'baseline.json')
    rows=baseline['archived']+read(ROOT/HERE/'additional-before.json')['archived']
    held={r['previous']['path']:r for r in rows}
    implementation=read(ROOT/HERE/'implementation-files.json')
    for relative in implementation:
        require(relative.startswith(('src/','scripts/','tests/')) and '..' not in Path(relative).parts,
            'Unexpected implementation path')
        destination=ROOT/relative
        require(destination.resolve().is_relative_to(ROOT) and not destination.is_symlink(),
            'Protected implementation destination')
        source=CANDIDATE/relative
        require(source.is_file() and not source.is_symlink(),'Missing candidate')
        if relative in held:
            row=held[relative];verify(ROOT,row['archive'])
            require(ref(ROOT,relative)['sha256'] in (row['previous']['sha256'],
                sha256(source.read_bytes()).hexdigest()), 'Unrelated local edit: '+relative)
        else:
            require(not destination.exists() or destination.read_bytes()==source.read_bytes(),
                'Unarchived existing file: '+relative)
    # All conflict checks precede the first replacement. Per-file replacement
    # is atomic and rerunnable; registration remains a separate transaction.
    installed=[]
    for relative in implementation:
        source=CANDIDATE/relative;destination=ROOT/relative
        destination.parent.mkdir(parents=True,exist_ok=True)
        temporary=destination.with_name(destination.name+'.p14-deploy.tmp')
        with temporary.open('xb') as stream: stream.write(source.read_bytes())
        temporary.chmod(source.stat().st_mode & 0o777)
        os.replace(temporary,destination)
        installed.append(ref(ROOT,relative))
    manifest=dict(profile='p14-reviewed-local-deployment.v1',
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        candidate_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=CANDIDATE,text=True).strip(),
        environment=str(ROOT/'.venv-context/bin/python'),devices='CPU; CUDA_VISIBLE_DEVICES=-1 for checks',
        random_seeds='N/A: deterministic engineering checks; no stochastic comparison',
        data_version=read(ROOT/'artifacts/legal-mission-control/2026-10-23/p14-decisions/summary.json')['original'],
        plan=ref(ROOT,'docs/plans/p14-deployment-and-decisions-2026-10-23.md'),
        decision_plan=ref(ROOT,'docs/plans/p14-decision-followup-2026-10-23.md'),
        commands=['.venv-context/bin/python artifacts/legal-mission-control/2026-10-23/p14-deployment/prepare.py',
            'Focused pytest commands recorded in local-tests.xml and admission-tests.xml; candidate imports via run_local_tests.py',
            '.venv-context/bin/python artifacts/legal-mission-control/2026-10-23/p14-deployment/context_preflight.py',
            '.venv-context/bin/python artifacts/legal-mission-control/2026-10-23/p14-deployment/product_preflight.py',
            '.venv-context/bin/python artifacts/legal-mission-control/2026-10-23/p14-deployment/deploy_local.py'],
        suites=suites,context_preparation_seconds=check['seconds'],import_preparation_seconds=imported['seconds'],
        installed=installed,completed_at_utc=datetime.now(timezone.utc).isoformat(),provider_calls=0,
        legal_acceptance=False,registration_pending=True,
        result_path=str(HERE/'local-result.json'))
    save(ROOT/HERE/'deployment-manifest.json',manifest)
    evidence=[HERE/name for name in ('local-tests.xml','admission-tests.xml','context-preflight.json',
        'context-preflight-population.json','product-preflight.json','deployment-manifest.json','final-audit.md')]
    evidence += [Path('artifacts/legal-mission-control/2026-10-23/p14-decisions')/name for name in (
        'summary.json','decisions.json','mapping-only-needs.json','retained-source-needs.json',
        'reject-issue-remedies.json','unresolved-remedies.json')]
    evidence += [Path('docs/implementation/legal-mission-control/results/p14-decisions-2026-10-23.md')]
    result=dict(verdict='PASS',provider_calls=0,legal_acceptance=False,
        scope='Local engineering deployment only; staged registration and live legal review still required.',
        evidence=[ref(ROOT,p) for p in evidence],installed_files=len(installed),
        historical_calls=4027,historical_recoveries=88,successor_recovery_ceiling=288,
        attempts_reset=False,registration_pending=True)
    save(ROOT/HERE/'local-result.json',result)
    print(json.dumps(dict(verdict='PASS',installed_files=len(installed),provider_calls=0,
        registration_pending=True,legal_acceptance=False)))


if __name__=='__main__': run()
