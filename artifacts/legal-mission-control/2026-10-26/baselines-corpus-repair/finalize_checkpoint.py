"""Record local evidence without deploying or modifying live execution bindings."""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import fcntl
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path('/home/chakwong/python/legalmath')
OUT = Path(__file__).resolve().parent
ISOLATED = Path('/tmp/legalmath-baselines-corpus-repair')
PLAN = ROOT / 'docs/plans/legal-failed-baselines-corpus-repair-2026-10-26.md'
RESULT = ROOT / 'docs/implementation/legal-mission-control/results/failed-baselines-corpus-repair-2026-10-26.md'
EVENT_ID = 'failed-baselines-corpus-local-repair-2026-10-26'

def read(p):
    return json.loads(p.read_text())

def digest(p):
    return sha256(p.read_bytes()).hexdigest()

def ref(p):
    return {'path': str(p.relative_to(ROOT)), 'sha256': digest(p)}

def save_new(p, value):
    if p.exists():
        if read(p) != value:
            raise RuntimeError('Refuse changed retained receipt: ' + str(p))
        return
    p.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

def walk_refs(value):
    if isinstance(value, dict):
        if set(('path', 'sha256')) <= value.keys():
            yield value
        for child in value.values():
            yield from walk_refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_refs(child)

candidate = read(OUT / 'candidate-manifest.json')
assert candidate['deployment'] == 'NOT_DEPLOYED'
assert digest(OUT / 'candidate.patch') == candidate['patch_sha256']
for row in candidate['files']:
    assert digest(ROOT / row['artifact']) == row['candidate_sha256'], row['path']
    assert digest(ISOLATED / row['path']) == row['candidate_sha256'], row['path']
    live = ROOT / row['path']
    assert (digest(live) if live.exists() else None) == row['live_sha256'], row['path']
protected_path = ROOT / 'artifacts/legal-mission-control/2026-10-25/offline-unblock/protected-before.json'
protected = read(protected_path)['files']
assert len(protected) == 364
for name, expected in protected.items():
    assert digest(ROOT / name) == expected, name
replays = [OUT / name for name in (
    'p14-warrant-replay-final.json', 'p14-warrant-semantic-reassessment.json',
    'gatecoin-context-reviewed-selection.json',
    'gatecoin-individual-reviewed-annotations.json',
    'gatecoin-correction-capacity.json', 'corpus-missing-duties.json')]
checked_refs = set()
for receipt in replays:
    for item in walk_refs(read(receipt)):
        path = Path(item['path'])
        path = path if path.is_absolute() else ROOT / path
        assert path.is_file(), str(path)
        assert digest(path) == item['sha256'], str(path)
        checked_refs.add((str(path), item['sha256']))
tests = [s.attrib for s in ET.parse(OUT / 'tests-final-wiring.xml').iter('testsuite')]
assert sum(int(x['tests']) for x in tests) == 113
assert all(int(x['errors']) == int(x['failures']) == int(x['skipped']) == 0 for x in tests)
patch_command = ['git', 'apply', '--check', str((OUT / 'candidate.patch').relative_to(ROOT))]
patch_check = subprocess.run(patch_command, cwd=ROOT, capture_output=True, text=True, check=True)
manifest_path = OUT / 'run-manifest.json'
if not manifest_path.exists():
    state = read(ROOT / 'artifacts/legal-mission-control/2026-10-13/master/execution-state.json')
    calls = read(ROOT / 'artifacts/legal-mission-control/2026-10-13/master/live-calls.json')
    service = read(ROOT / 'artifacts/legal-mission-control/2026-10-23/p14-deployment/service/service-recovery.json')
    test_names = sorted({t.attrib['classname'] for t in ET.parse(OUT / 'tests-final-wiring.xml').iter('testcase')})
    test_paths = sorted(str(p.relative_to(ISOLATED)) for p in (ISOLATED / 'tests').rglob('test_*.py') if p.stem in test_names)
    manifest = {
        'profile': 'failed-baselines-corpus-run-manifest.v1',
        'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'baseline': 'Dirty worktree and exact retained input identities; HEAD alone does not identify the live implementation.',
        'environment': str(ROOT / '.venv-context/bin/python'),
        'checkpoint_environment': {'executable': sys.executable, 'version': sys.version},
        'cpu_gpu': 'CPU-only saved-input validation; no GPU libraries or device probes invoked.',
        'seeds': 'N/A: deterministic local checks; no stochastic model invocation.',
        'plan': ref(PLAN), 'result': ref(RESULT),
        'candidate_manifest': ref(OUT / 'candidate-manifest.json'),
        'candidate_patch': ref(OUT / 'candidate.patch'),
        'protected_baseline': ref(protected_path),
        'finalizer': ref(Path(__file__).resolve()),
        'verification_commands': {
            'actual_checkpoint': '.venv/bin/python ' + str(Path(__file__).resolve().relative_to(ROOT)),
            'actual_patch_check': patch_command,
            'prior_admission_commands': ['.venv/bin/python scripts/legal_mission_control.py ' + a for a in ('check', 'status', 'admit')],
            'replay_scripts': [str(ISOLATED / n) for n in ('replay_baselines.py', 'replay_annotations.py', 'check_corpus_and_residuals.py')],
            'reproducible_test_argv': [str(ROOT / '.venv-context/bin/python'), '-m', 'pytest', *test_paths, '-q'],
            'reproducible_test_cwd': str(ISOLATED),
            'command_provenance': 'Test paths reconstructed from retained JUnit report; complete original shell text was not separately retained. Replay scripts and outputs are hashed.'
        },
        'tests': tests,
        'wall_time': {'test_suite_seconds': sum(float(s['time']) for s in tests), 'total_session_seconds': None, 'reason': 'Whole-session wall time was not instrumented; no performance claim.'},
        'data_identities': {q: ref(ROOT / ('artifacts/legal-mission-control/2026-10-24/window-continuation/service-inheritance/live/arms/' + q + '/baseline/identity.json')) for q in ('p14', 'gatecoin')},
        'receipts': [ref(p) for p in replays] + [ref(OUT / n) for n in ('tests-final-wiring.xml', 'mission-check.json', 'mission-status.json', 'mission-admit.json')],
        'archived_files_verified': len(candidate['files']),
        'protected_live_files_verified': len(protected),
        'retained_input_references_verified': len(checked_refs),
        'protected_changes': [], 'provider_calls_by_repair': 0, 'live_attempts_by_repair': 0,
        'deployment': 'NOT_DEPLOYED', 'legal_acceptance': False,
        'frontier_counts': dict(Counter(t['status'] for t in state['tasks'].values())),
        'current_calls_observed': len(calls['calls']), 'maximum_calls': calls['maximum'],
        'service_charges_observed': len(service['charges']), 'service_maximum': service['maximum'],
        'live_observation': 'Host ps verified PID 2726366 alive at 2026-10-25T19:26Z; no terminal receipts. Recheck before any deployment.',
        'outstanding': ['Safe same-master registration and rebind before activation', 'Finite continuation allocation preserving attempts and protected reserves', 'Fresh substantive P14 target assessment', 'Dated corpus applicability/later-treatment evidence', 'Four fixed answers and complete source-use reviews'],
        'followup_receipts': ['mission-checkpoint.json', 'mission-refresh.json', 'master-status.json', 'checkpoint-command-results.json']
    }
    save_new(manifest_path, manifest)
else:
    manifest = read(manifest_path)
    assert manifest['plan'] == ref(PLAN) and manifest['result'] == ref(RESULT)
mission_path = ROOT / 'docs/implementation/legal-mission-control/mission.json'
with mission_path.with_suffix('.execution.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    mission = read(mission_path)
    matches = [e for e in mission['history'] if e['id'] == EVENT_ID]
    if matches:
        assert len(matches) == 1
        event = matches[0]
        assert event['result_evidence'] == [ref(PLAN), ref(RESULT), ref(manifest_path)]
    else:
        reason = ('Retain active independent dispatcher and all existing limits. P14/Gatecoin/corpus local repairs are tested and staged, not deployed or legally accepted. At a safe owner checkpoint, verify the consolidated candidate manifest, register finite same-master continuation, rebind and qualify. P14 target reassessment and corpus applicability reviews remain separate duties; complete source-use review needs fixed P10/evidence answers.')
        event = {
            'id': EVENT_ID, 'task_id': 'product-contribution', 'kind': 'product_evaluation',
            'outcome': 'no_advance', 'decision': 'Reviewed isolated repair executed: 113 tests, exact retained replays and unchanged live bindings; legal acceptance remains open.',
            'next_task': 'product-contribution', 'next_task_reason': reason,
            'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
            'result_evidence': [ref(PLAN), ref(RESULT), ref(manifest_path)],
            'local_repair_accounting': {'scope': 'User-authorized bounded local baseline/corpus repair', 'implementation_cycles': 1, 'corrective_cycles': 1, 'live_calls': 0, 'live_attempts': 0, 'previous_limits_preserved': True}
        }
        mission['history'].append(event)
        mission['next_task_reason'] = reason
        temporary = mission_path.with_name('mission.baseline-corpus-checkpoint.tmp')
        temporary.write_text(json.dumps(mission, indent=2, ensure_ascii=False) + '\n')
        os.replace(temporary, mission_path)
    checkpoint = {'event': event, 'mission_sha256': digest(mission_path), 'budget_or_graph_changed': False}
    if not (OUT / 'mission-checkpoint.json').exists():
        save_new(OUT / 'mission-checkpoint.json', checkpoint)
print(json.dumps({'manifest': ref(manifest_path), 'checkpoint': ref(OUT / 'mission-checkpoint.json'), 'candidate_files': len(candidate['files']), 'protected_files': len(protected), 'input_references': len(checked_refs), 'tests': 113, 'deployment': 'NOT_DEPLOYED'}))
