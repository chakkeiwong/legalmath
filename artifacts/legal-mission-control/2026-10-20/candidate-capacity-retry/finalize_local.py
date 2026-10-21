"""Validate the saved no-call evidence and preserve this package's run manifest."""
from pathlib import Path
from datetime import datetime,timezone
import os
import sys
import subprocess
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
os.environ['CUDA_VISIBLE_DEVICES']='-1'
from scripts.legal_integration_candidate_retry import WORK,REVIEW,IMPLEMENTATION,QUESTIONS,BASE
from scripts.legal_mission_execution import ref,read,save,require


def main():
    baseline=read(ROOT/WORK/'baseline.json')
    result=read(ROOT/WORK/'checkpoint-replay.json')
    require(result['verdict']=='PASS' and result['provider_calls']==0 and result['ledger_unchanged'],
        'Production-entry replay incomplete')
    actual={}
    for q in QUESTIONS:
        phase=read(ROOT/WORK/'checkpoint-replay/live'/q/'product/phases'/('call-candidates-'+q)/'phase.json')
        require(phase['logical_dispatches']==['candidates-'+q] and not phase['input_blocks']
            and len(phase['measurements'])==1,'Production request does not fit or repeats completed work')
        outcome=read(ROOT/phase['outcome']['path'])
        require(outcome['resource_refusal']['reason']=='DEBUG ONLY: optional dispatch deliberately withheld',
            'Replay failed before deliberate no-network refusal')
        measurement=phase['measurements'][0]['measurement']
        require(measurement['local_tokens']<=70000 and measurement['bytes']<=250000,'Repaired request still too large')
        actual[q]=measurement
    old_ledger=next(r['archive'] for r in baseline['archived'] if r['previous']['path']==str(BASE/'live-calls.json'))
    require(ref(ROOT,BASE/'live-calls.json')['sha256']==old_ledger['sha256'],'Local validation changed charges')
    tests={}
    for filename in ('tests.xml','product-regressions.xml'):
        suite=ET.parse(ROOT/WORK/filename).getroot().find('testsuite')
        require(suite is not None and int(suite.attrib['tests'])>0
            and all(int(suite.attrib[k])==0 for k in ('errors','failures','skipped')),'Focused tests did not pass')
        tests[filename]=dict(suite.attrib)
    now=datetime.now(timezone.utc)
    commands=[
        '.venv-context/bin/python scripts/legal_integration_candidate_retry.py checkpoints',
        '.venv-context/bin/python artifacts/legal-mission-control/2026-10-20/candidate-capacity-retry/replay_candidates.py',
        '.venv-context/bin/python artifacts/legal-mission-control/2026-10-20/candidate-capacity-retry/replay_prepared.py',
        '.venv-context/bin/python artifacts/legal-mission-control/2026-10-20/candidate-capacity-retry/probe_criticism.py',
        '.venv-context/bin/python -m pytest -q tests/assurance/test_prepared_checkpoint.py tests/assurance/test_tool_input_capacity.py tests/assurance/test_preparation_diagnosis.py tests/assurance/test_downstream_capacity.py tests/assurance/test_phased_product.py tests/tooling/test_candidate_retry_registration.py --junitxml=artifacts/legal-mission-control/2026-10-20/candidate-capacity-retry/tests.xml',
        '.venv-context/bin/python -m pytest -q tests/assurance/test_bounded_product.py tests/assurance/test_bounded_references.py tests/assurance/test_phased_phase.py tests/assurance/test_downstream_instructions.py tests/assurance/test_downstream_replay_order.py tests/tooling/test_candidate_retry_registration.py --junitxml=artifacts/legal-mission-control/2026-10-20/candidate-capacity-retry/product-regressions.xml',
    ]
    save(ROOT/WORK/'run-manifest.json',dict(profile='candidate-capacity-local-manifest.v1',
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        implementation={p:ref(ROOT,p) for p in sorted(IMPLEMENTATION)},commands=commands,
        environment=sys.executable,cpu_gpu='CPU only; CUDA_VISIBLE_DEVICES=-1; GPU intentionally hidden',
        random_seeds='N/A: deterministic replay; no model sampling',
        baseline=ref(ROOT,WORK/'baseline.json'),plan=ref(ROOT,REVIEW),
        source_data=ref(ROOT,WORK/'checkpoints/p10.json'),
        completed_at_utc=now.isoformat(),
        package_elapsed_seconds=(now-datetime.fromisoformat(baseline['at_utc'])).total_seconds(),
        duration_scope='Elapsed since frozen baseline, including review, editing and all diagnostics; not a model benchmark',
        tests=tests,provider_calls=0,result=str(WORK/'local-result.json')))
    names=['replay.json','checkpoint-replay.json','criticism-probe.json','run-manifest.json',
        'tests.xml','product-regressions.xml','local-review.md','review.patch',
        'replay_candidates.py','replay_prepared.py','probe_criticism.py','finalize_local.py']
    evidence=[ref(ROOT,WORK/name) for name in names]
    evidence += [ref(ROOT,p) for p in ('tests/assurance/test_prepared_checkpoint.py',
        'tests/assurance/test_tool_input_capacity.py','tests/assurance/test_preparation_diagnosis.py',
        'tests/tooling/test_candidate_retry_registration.py')]
    save(ROOT/WORK/'local-result.json',dict(profile='candidate-capacity-repair-result.v1',verdict='PASS',
        provider_calls=0,ledger_unchanged=True,legal_acceptance=False,evidence=evidence,
        actual_preparation_request_measurements=actual,tests=tests,
        decision='Register one bounded retry using unchanged completed synthesis. Only missing optional tool work and original downstream answers may dispatch.',
        limitations=['Live service acceptance not yet tested','No completed legal-answer or tool-effect claim',
            'Criticism capacity probe used explicitly synthetic candidates; actual candidates remain measured before dispatch',
            'Corpus dated applicability and final source-use qualification remain open']))
    print('Local validation PASS: four completed preparations reused, exact candidate packets fit, paid ledger unchanged.')


if __name__=='__main__':main()
