"""Install only the reviewed idle-boundary successor; preserve all other files."""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import os
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[4]
CANDIDATE=Path('/tmp/legalmath-p14-corrected-context-20261023')
sys.path.insert(0,str(ROOT))
from scripts import legal_review_context_isolation as isolation
from scripts.legal_mission_execution import read,save,ref,verify,require,process_alive

candidate=read(ROOT/isolation.HERE/'candidate-source.json')
verify(ROOT,candidate['tests'])
verify(ROOT,candidate['review'])
baseline=read(ROOT/isolation.HERE/'baseline.json')
handover=read(ROOT/baseline['handover']['path'])
require(handover['supervisor_ended'] and not process_alive(handover['process']), 'Supervisor is still active')
require(ref(ROOT,isolation.BASE/'live-calls.json')==handover['ledger'], 'Charges changed after handover')
held={row['previous']['path']:row for row in isolation.archive_rows(ROOT,baseline)}
intermediate=read(ROOT/isolation.HERE/'unpublished-v1/installation-manifest.json')
intermediate_candidate=read(ROOT/isolation.HERE/'unpublished-v1/candidate-source.json')
require(intermediate['candidate']['sha256']==ref(ROOT,isolation.HERE/'unpublished-v1/candidate-source.json')['sha256']
    and intermediate['data_version']==ref(ROOT,isolation.HERE/'baseline.json')
    and intermediate['provider_calls']==0 and intermediate['registration_pending'],
    'Unverified intermediate installation')
intermediate_files={r['path']:r['sha256'] for r in intermediate['installed']}
for entry in intermediate_candidate['files']:
    require(intermediate_files[entry['path']]==entry['sha256'], 'Intermediate candidate differs from manifest')
    if entry['path'] in isolation.CHANGED:
        require(entry['current']==held[entry['path']]['previous'], 'Intermediate predecessor differs')
seed=read(ROOT/isolation.HERE/'seed.json')
require(seed['provider_calls']==0 and seed['historical_decisions_unchanged']
    and seed['failed_results_retained'], 'Settled calls were not authenticated')
require({row['path'] for row in candidate['files']}==set(isolation.CHANGED+isolation.ADDED),
    'Candidate scope changed')
for row in candidate['files']:
    relative=row['path']
    source=(CANDIDATE if relative in isolation.CHANGED else ROOT)/relative
    destination=ROOT/relative
    require(not source.is_symlink() and not destination.is_symlink()
        and destination.resolve().is_relative_to(ROOT), 'Protected installation path')
    require(sha256(source.read_bytes()).hexdigest()==row['sha256'], 'Candidate changed after testing')
    if relative in isolation.CHANGED:
        verify(ROOT,held[relative]['archive'])
        allowed={held[relative]['previous']['sha256']}
        if relative in intermediate_files: allowed.add(intermediate_files[relative])
        require(row['current']['sha256'] in allowed and
            ref(ROOT,relative)==row['current'],
            'Unrelated work changed before installation: '+relative)
    else:
        require(ref(ROOT,relative)==row['current'], 'New implementation changed after review')

for relative in isolation.CHANGED:
    source=CANDIDATE/relative
    destination=ROOT/relative
    temporary=destination.with_name(destination.name+'.context-isolation.tmp')
    with temporary.open('xb') as stream:
        stream.write(source.read_bytes())
    temporary.chmod(source.stat().st_mode & 0o777)
    os.replace(temporary,destination)

manifest=dict(profile='corrected-context-install.v1',
    git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    environment=str(ROOT/'.venv-context/bin/python'),devices='CPU; CUDA_VISIBLE_DEVICES=-1 in checks',
    random_seeds='N/A: deterministic engineering checks',
    data_version=ref(ROOT,isolation.HERE/'baseline.json'),
    plan=ref(ROOT,isolation.REVIEW),result_path=str(isolation.HERE/'local-result.json'),
    commands=['.venv-context/bin/python artifacts/legal-mission-control/2026-10-23/p14-corrected-context/run_deployment_tests.py',
        '.venv-context/bin/python scripts/legal_review_context_isolation.py settle',
        '.venv-context/bin/python scripts/legal_review_context_isolation.py freeze',
        '.venv-context/bin/python scripts/legal_review_context_isolation.py seed',
        '.venv-context/bin/python artifacts/legal-mission-control/2026-10-23/p14-corrected-context/install.py'],
    installed=[ref(ROOT,p) for p in isolation.CHANGED+isolation.ADDED],
    candidate=ref(ROOT,isolation.HERE/'candidate-source.json'),
    intermediate_installation=ref(ROOT,isolation.HERE/'unpublished-v1/installation-manifest.json'),
    completed_at_utc=datetime.now(timezone.utc).isoformat(),provider_calls=0,legal_acceptance=False,
    calls_preserved=baseline['calls'],service_charges_preserved=baseline['service_charges'],
    imported_current_calls=len(seed['imported']),attempts_added=0,registration_pending=True)
save(ROOT/isolation.HERE/'installation-manifest.json',manifest)
evidence=[isolation.HERE/p for p in ('baseline.xml','candidate-complete-fixture.xml','deployment-tests.xml',
    'candidate-source.json','baseline.json','additional-before.json','seed.json',
    'warrant-target-followup.json','installation-manifest.json','deployment-review.md',
    'warrant-fixture-failure.xml','observed-preflight.json')]
evidence += [isolation.DEPLOYMENT/'local-result.json']
result=dict(verdict='PASS',provider_calls=0,legal_acceptance=False,
    evidence=[ref(ROOT,p) for p in evidence],passing_tests=68,attempts_added=0,
    scope='Corrected-context isolation, exact answer pointers, warranted correction targets and history-preserving installation; registration and live continuation pending.')
save(ROOT/isolation.HERE/'local-result.json',result)
print({'installed':len(isolation.CHANGED),'added':len(isolation.ADDED),'provider_calls':0,'registration_pending':True})
