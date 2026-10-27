"""Reviewed local deployment driver; never dispatches a provider request."""
from pathlib import Path
from contextlib import ExitStack
from copy import deepcopy
import argparse
import hashlib
import json
import os
import shutil
import sys

ROOT = Path('/home/chakwong/python/legalmath')
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from scripts import legal_baseline_corpus_deployment as deploy
from scripts.legal_mission_execution import read, save, ref, verify, require, digest
from scripts.legal_integration_master import BASE, DOC, PROGRAM, STATE, PLAN
WORK = deploy.WORK
TREE = Path('/tmp/legalmath-baselines-corpus-deployment')
SELF = 'scripts/legal_baseline_corpus_deployment.py'
TEST = 'tests/tooling/test_baseline_corpus_deployment.py'
EXECUTION = 'scripts/legal_mission_execution.py'
CONTROL = 'scripts/legal_mission_control.py'
PROVIDER = 'src/legalmath/interpretation/assurance/bounded_provider.py'

def replace_once(body, old, new):
    require(body.count(old) == 1, 'Deployment anchor missing or repeated: ' + old[:100])
    return body.replace(old, new, 1)

def prepare():
    require(not (ROOT / WORK / 'preparation.json').exists(), 'Preparation already retained')
    results = read(ROOT / WORK / 'admission-command-results.json')
    require(all(x['exit_code'] == 0 for x in results), 'Admission failed')
    manifest = read(ROOT / deploy.CANDIDATE / 'candidate-hardened-manifest.json')
    outputs = {}
    for row in manifest['files']:
        source = ROOT / row['artifact']
        require(hashlib.sha256(source.read_bytes()).hexdigest() == row['candidate_sha256'],
            'Candidate changed: ' + row['path'])
        target = ROOT / row['path']
        actual = hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
        require(actual == row['live_sha256'], 'Live candidate baseline changed: ' + row['path'])
        outputs[row['path']] = source.read_text()
    body = (ROOT / EXECUTION).read_text()
    anchor = "    if program.get('window_continuation'):\n"
    body = replace_once(body, anchor,
        "    if program.get('baseline_corpus_repair'):\n"
        "        from scripts.legal_baseline_corpus_deployment import validate\n"
        "        reviewed = validate(program, root, program['protected_evidence'][-1])\n"
        "        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=41)\n" + anchor)
    anchor = "            if self.program.get('window_continuation'):\n"
    body = replace_once(body, anchor,
        "            if self.program.get('baseline_corpus_repair'):\n"
        "                from scripts.legal_baseline_corpus_deployment import validate_history\n"
        "                validate_history(self.program, state, self.root)\n"
        "            elif self.program.get('window_continuation'):\n")
    outputs[EXECUTION] = body
    body = (ROOT / CONTROL).read_text()
    anchor = "    else:\n        master_state = None\n"
    hook = """        baseline_corpus = master.get('baseline_corpus_repair')
        if baseline_corpus:
            require(baseline_corpus.get('profile') == 'reviewed-baseline-corpus-repair.v1'
                and baseline_corpus.get('prior_detours') == detours == 66
                and baseline_corpus.get('additional_consolidated_revision') == 1
                and baseline_corpus.get('calls_added') == baseline_corpus.get('attempts_added')
                    == baseline_corpus.get('replacements_added') == 0
                and baseline_corpus.get('attempts_reset') is False
                and baseline_corpus.get('reopened_nodes') == []
                and program.get('baseline_corpus_repair') == baseline_corpus,
                'Unreviewed baseline/corpus deployment')
            require(any(r['id'] == 'baseline-corpus-local-deployment-2026-10-26'
                and baseline_corpus['review'] in r['result_evidence'] for r in history),
                'Missing baseline/corpus deployment history')
            verify_refs(root, baseline_corpus)
            detours += 1
"""
    outputs[CONTROL] = replace_once(body, anchor, hook + anchor)
    phased = 'scripts/legal_integration_phased_live.py'
    outputs[phased] = replace_once(outputs[phased], 'def active_live(program):\n',
        "def active_live(program):\n    if program.get('baseline_corpus_repair'):\n"
        "        return Path(program['baseline_corpus_repair']['runtime'])\n")
    body = (ROOT / PROVIDER).read_text()
    anchor = '            state = self.check()\n'
    hook = """            current_path = self.grant_path.with_name('current-binding.json')
            if current_path.exists():
                current = json.loads(current_path.read_text())
                require(not current.get('baseline_corpus_repair_hold'),
                    'Baseline/corpus repair is installed; reviewed live continuation is required', 'E_AUTHORITY')
"""
    outputs[PROVIDER] = replace_once(body, anchor, anchor + hook)
    outputs[SELF] = (ROOT / SELF).read_text()
    outputs[TEST] = (ROOT / TEST).read_text()
    plan = (ROOT / PLAN).read_text() + '''
## October 26 baseline/corpus local deployment

The service-inheritance run ended at 04:42 Hong Kong on October 26 without
completing integration. The hardened baseline/corpus repair is governed by
docs/plans/legal-baseline-corpus-local-deployment-2026-10-26.md. This is one
zero-call local deployment; all spent attempts, 6,471 calls, 288 service
replacements, the open circuit and the existing deadline remain. Repaired
profiles use a fresh runtime identity. Live activation remains held pending
finite reviewed authority and checkpoint migration. P14/Gatecoin judgments
and missing corpus evidence remain open; local tests do not settle them.
'''
    staged = WORK / 'source'
    for path, body in {**outputs, str(PLAN): plan}.items():
        if path.endswith('.py'):
            compile(body, path, 'exec')
        target = ROOT / staged / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)
    binding = read(ROOT / BASE / 'current-binding.json')
    service = Path(binding['phase_service_scope']['path']).parent
    journals = [p.relative_to(ROOT).as_posix() for p in sorted((ROOT / deploy.OLD_WORK / 'live').rglob('dispatch.json'))]
    watched = [PROGRAM, STATE, DOC / 'mission.json', BASE / 'current-binding.json',
        BASE / 'live-calls.json', BASE / 'live-grant.json', BASE / 'current-stage.json',
        service / 'service-circuit.json', service / 'service-recovery.json', PLAN, *map(Path, outputs),
        *map(Path, journals)]
    with ExitStack() as stack:
        deploy.acquire_locks(ROOT, stack, deploy.lock_paths(ROOT, binding, journals))
        worker, finished = deploy.stopped(ROOT)
        state = read(ROOT / STATE)
        for tid, row in state['tasks'].items():
            if row['status'] == 'RUNNING':
                from scripts.legal_review_service_checkpoint import checked
                checked(ROOT, tid, row)
                require(not deploy.process_alive(row.get('live_supervisor')), 'Active owner: ' + tid)
        census = {}
        for path in journals:
            calls = read(ROOT / path)['calls']
            require(all(r['status'] in ('FAILED', 'VALIDATED') for r in calls.values()), 'Unsettled dispatch: ' + path)
            census[path] = {s: sum(r['status'] == s for r in calls.values()) for s in ('FAILED', 'VALIDATED')}
        archived, absent = [], []
        for path in dict.fromkeys(watched):
            source = ROOT / path
            if source.exists():
                target = WORK / 'before' / path
                (ROOT / target).parent.mkdir(parents=True, exist_ok=True)
                (ROOT / target).write_bytes(source.read_bytes())
                archived.append(dict(previous=ref(ROOT, path), archive=ref(ROOT, target)))
            else:
                absent.append(str(path))
        ledger = read(ROOT / BASE / 'live-calls.json')
        recovery = read(ROOT / service / 'service-recovery.json')
        require(len(ledger['calls']) == 6471 and ledger['maximum'] == 8100
            and len(recovery['charges']) == recovery['maximum'] == 288, 'Unexpected spent allowance')
        baseline = dict(archived=archived, absent_paths=absent, changed_paths=sorted(outputs),
            calls=len(ledger['calls']), service_replacements=len(recovery['charges']),
            dispatch_census=census, prior_detours=66, at_utc=deploy.now())
        save(ROOT / WORK / 'baseline.json', baseline)
        save(ROOT / WORK / 'handover.json', dict(settled=True, supervisor_ended=True,
            reserved_dispatches=0, calls=6471, worker=worker, finished=finished,
            paused_owners=[k for k, v in state['tasks'].items() if v['status'] == 'RUNNING'],
            terminal_receipt=ref(ROOT, deploy.OLD_WORK / 'finished.json'),
            census=census, at_utc=deploy.now()))
    save(ROOT / WORK / 'preparation.json', dict(sources={p: ref(ROOT, staged / p) for p in outputs},
        plan=ref(ROOT, staged / PLAN), baseline=ref(ROOT, WORK / 'baseline.json'),
        candidate=ref(ROOT, deploy.CANDIDATE / 'candidate-hardened-manifest.json')))
    require(not TREE.exists(), 'Test tree already exists')
    for folder in ('src', 'scripts', 'tests'):
        shutil.copytree(ROOT / folder, TREE / folder, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for path in outputs:
        target = TREE / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / staged / path).read_bytes())
    return dict(prepared=True, source_files=len(outputs), provider_calls=0)

def tests():
    sys.path[:0] = [str(TREE / 'src'), str(TREE)]
    for name in list(sys.modules):
        if name == 'scripts' or name.startswith('scripts.') or name == 'legalmath' or name.startswith('legalmath.'):
            del sys.modules[name]
    os.chdir(TREE)
    import scripts
    scripts.__path__ = [str(TREE / 'scripts')]
    from scripts import legal_integration_master, legal_mission_execution
    legal_integration_master.ROOT = ROOT
    legal_mission_execution.ROOT = ROOT
    import pytest
    from legalmath.interpretation.assurance import corpus_review
    assert Path(corpus_review.__file__).resolve().is_relative_to(TREE)
    names = ['tests/assurance/test_baseline_corpus_repairs.py',
        'tests/assurance/test_corpus_passage_attribution.py', 'tests/assurance/test_context_exact_references.py',
        'tests/assurance/test_context_need_disposition.py', 'tests/assurance/test_downstream_capacity.py',
        'tests/assurance/test_requirement_correction.py', 'tests/assurance/test_source_review_repair.py', TEST]
    raise SystemExit(pytest.main([*names, '-q', '--junitxml=' + str(ROOT / WORK / 'tests-staged-final.xml')]))

def stage():
    from xml.etree import ElementTree as ET
    from scripts.legal_integration_acceptance_revision import historical_projection
    suite = ET.parse(ROOT / WORK / 'tests-staged-final.xml').getroot()
    require(len(list(suite.iter('testcase'))) == 145 and not list(suite.iter('failure'))
        and not list(suite.iter('error')), 'Staged suite failed')
    preparation = read(ROOT / WORK / 'preparation.json')
    baseline = read(ROOT / WORK / 'baseline.json')
    deploy.assert_unchanged(ROOT, baseline)
    for pointer in preparation['sources'].values(): verify(ROOT, pointer)
    verify(ROOT, preparation['plan'])
    result = dict(verdict='PASS', provider_calls=0, legal_acceptance=False, tests=145,
        evidence=[ref(ROOT, WORK / 'tests-staged-final.xml'), preparation['candidate'],
            ref(ROOT, WORK / 'handover.json')],
        prior_harness_failure='First staged suite had two import-root errors; preserved in tests-staged.xml. Both resolved by explicitly binding candidate imports and real retained evidence.')
    save(ROOT / WORK / 'local-result.json', result)
    held = {r['previous']['path']: r['archive'] for r in baseline['archived']}
    old, before = read(ROOT / PROGRAM), read(ROOT / STATE)
    implementation = {p: dict(path=p, sha256=pointer['sha256']) for p, pointer in preparation['sources'].items()}
    revision = dict(profile=deploy.PROFILE, work=str(WORK), runtime=str(WORK / 'live'),
        activation='HOLD_REQUIRES_REVIEWED_CONTINUATION', prior_detours=66,
        additional_consolidated_revision=1, calls_added=0, attempts_added=0,
        replacements_added=0, attempts_reset=False, reopened_nodes=[],
        review=ref(ROOT, deploy.REVIEW), result=ref(ROOT, WORK / 'local-result.json'),
        baseline=ref(ROOT, WORK / 'baseline.json'), handover=ref(ROOT, WORK / 'handover.json'),
        candidate=preparation['candidate'], implementation=implementation,
        prior_program=held[str(PROGRAM)], prior_state=held[str(STATE)],
        prior_binding=held[str(BASE / 'current-binding.json')], **deploy.PROFILES)
    plan_pointer = dict(path=str(PLAN), sha256=preparation['plan']['sha256'])
    program = deploy.expected_program(old, revision, ROOT, plan_pointer)
    state = deploy.project_state(before, program, deploy.now())
    target = WORK / 'registration-stage'
    save(ROOT / target / 'program.json', program)
    save(ROOT / target / 'state.json', state)
    pointer = dict(path=str(PROGRAM), sha256=ref(ROOT, target / 'program.json')['sha256'])
    binding = read(ROOT / BASE / 'current-binding.json')
    binding['bindings'] = historical_projection(binding['bindings'], deploy.mapping(baseline, mission=True))
    binding.update(program=pointer, baseline_corpus_repair=revision,
        baseline_corpus_repair_hold=True,
        user_instruction='has the run finished? can we deploy the repair?',
        predecessor=revision['prior_binding'], phase_service_predecessor=revision['prior_binding'])
    binding['bindings'] += [pointer, plan_pointer, revision['review'], revision['result'],
        revision['baseline'], revision['handover'], revision['candidate'], *implementation.values()]
    known = {(r['previous']['path'], r['previous']['sha256']) for r in binding['historical_archives']}
    binding['historical_archives'] += [r for r in baseline['archived']
        if (r['previous']['path'], r['previous']['sha256']) not in known]
    save(ROOT / target / 'binding.json', binding)
    mission = historical_projection(read(ROOT / DOC / 'mission.json'), deploy.mapping(baseline, mission=True))
    master = mission['integration_master']
    for key in master:
        if key in program and isinstance(program[key], dict) and program[key].get('profile'):
            master[key] = deepcopy(program[key])
    master.update(program=pointer, plan=plan_pointer, baseline_corpus_repair=revision)
    reason = ('Install hardened reference/encoding/corpus consumer repairs without reopening failed owners. '
        'Preserve all charges and checkpoints. Live continuation needs finite service/attempt authority '
        'and checkpoint migration; P14 target reassessment and actual corpus reviews remain open.')
    mission['next_task_reason'] = reason
    mission['history'].append(dict(id=deploy.EVENT, task_id='product-contribution',
        kind='product_evaluation', outcome='no_advance', decision=reason,
        next_task='product-contribution', next_task_reason=reason, recorded_at_utc=deploy.now(),
        result_evidence=[pointer, revision['review'], revision['result'], revision['handover']]))
    save(ROOT / target / 'mission.json', mission)
    return dict(staged=True, provider_calls=0, attempts_added=0)

def staged_imports():
    import importlib
    for name in list(sys.modules):
        if name == 'scripts' or name.startswith('scripts.') or name == 'legalmath' or name.startswith('legalmath.'):
            del sys.modules[name]
    sys.path[:0] = [str(TREE / 'src'), str(TREE)]
    import scripts
    scripts.__path__ = [str(TREE / 'scripts')]
    from scripts import legal_mission_execution, legal_integration_master
    legal_mission_execution.ROOT = legal_integration_master.ROOT = ROOT
    from scripts import legal_mission_control
    legal_mission_control.ROOT = ROOT

def validate():
    from unittest.mock import patch
    import time
    preparation = read(ROOT / WORK / 'preparation.json')
    baseline = read(ROOT / WORK / 'baseline.json')
    deploy.assert_unchanged(ROOT, baseline)
    stage_path = WORK / 'registration-stage'
    overrides = {ROOT / p: ROOT / pointer['path'] for p, pointer in preparation['sources'].items()}
    overrides[ROOT / PLAN] = ROOT / preparation['plan']['path']
    overrides.update({ROOT / PROGRAM: ROOT / stage_path / 'program.json',
        ROOT / STATE: ROOT / stage_path / 'state.json',
        ROOT / BASE / 'current-binding.json': ROOT / stage_path / 'binding.json'})
    read_text, read_bytes, is_file, exists = Path.read_text, Path.read_bytes, Path.is_file, Path.exists
    staged_imports()
    from scripts.legal_integration_repair_execution import validate_staged_mission
    from scripts.legal_integration_campaign import provider
    from scripts.legal_mission_execution import save as stage_save
    started = time.monotonic()
    with patch.object(Path, 'read_text', lambda p, *a, **k: read_text(overrides.get(p, p), *a, **k)), \
         patch.object(Path, 'read_bytes', lambda p, *a, **k: read_bytes(overrides.get(p, p), *a, **k)), \
         patch.object(Path, 'is_file', lambda p: is_file(overrides.get(p, p))), \
         patch.object(Path, 'exists', lambda p: exists(overrides.get(p, p))):
        mission = json.loads(read_text(ROOT / stage_path / 'mission.json'))
        from scripts import legal_mission_control
        legal_mission_control.verify_refs(ROOT, mission)
        print(json.dumps(dict(checkpoint='staged_mission_references', status='PASS')), flush=True)
        checked = validate_staged_mission(ROOT, stage_path, mission, 67)
        print(json.dumps(dict(checkpoint='staged_master_and_mission', status='PASS')), flush=True)
        service = provider()
        ledger = service.check()
        require(len(ledger['calls']) == 6471 and ledger['maximum'] == 8100, 'Preflight changed calls')
        binding = json.loads(read_text(ROOT / stage_path / 'binding.json'))
        scope = service.allowance.service_scope()[0]
        require(scope == binding['phase_service_scope'], 'Changed inherited service scope')
        from legalmath.errors import LegalMathError
        service.allowance.expected = 'deployment-must-not-dispatch'
        try:
            service.allowance.reserve('deployment-must-not-dispatch')
        except LegalMathError as exc:
            require(exc.code == 'E_AUTHORITY' and 'reviewed live continuation' in exc.details,
                'Wrong activation hold')
        else:
            raise RuntimeError('Activation hold failed')
    deploy.assert_unchanged(ROOT, baseline)
    checked.update(provider_calls=0, calls=6471, activation_hold='VERIFIED',
        service_scope=scope, wall_seconds=time.monotonic() - started, at_utc=deploy.now())
    stage_save(ROOT / WORK / 'registration-check.json', checked)
    return checked

def commit():
    baseline = read(ROOT / WORK / 'baseline.json')
    checked = read(ROOT / WORK / 'registration-check.json')
    require(checked['verdict'] == 'PASS' and checked['activation_hold'] == 'VERIFIED', 'Validation not complete')
    for pointer in read(ROOT / WORK / 'final-staged-identities.json'):
        verify(ROOT, pointer)
    require(checked['program'] == ref(ROOT, WORK / 'registration-stage/program.json')
        and checked['state'] == ref(ROOT, WORK / 'registration-stage/state.json'),
        'Validation describes different staged program/state')
    preparation = read(ROOT / WORK / 'preparation.json')
    staged_program = read(ROOT / WORK / 'registration-stage/program.json')
    for path, pointer in preparation['sources'].items():
        verify(ROOT, pointer)
        require(staged_program[deploy.KEY]['implementation'][path]['sha256'] == pointer['sha256'],
            'Staged source changed after validation: ' + path)
    binding = read(ROOT / BASE / 'current-binding.json')
    journal = WORK / 'registration.json'
    with ExitStack() as stack:
        deploy.acquire_locks(ROOT, stack, deploy.lock_paths(ROOT, binding, baseline['dispatch_census']))
        deploy.stopped(ROOT)
        if (ROOT / journal).exists():
            deploy.finish_transaction(ROOT, journal)
        else:
            deploy.assert_unchanged(ROOT, baseline)
            writes = [dict(path=p, before=ref(ROOT, p) if (ROOT / p).exists() else None,
                replacement=pointer) for p, pointer in preparation['sources'].items()]
            writes.append(dict(path=str(PLAN), before=ref(ROOT, PLAN), replacement=preparation['plan']))
            for path, name in ((PROGRAM, 'program.json'), (STATE, 'state.json'),
                    (BASE / 'current-binding.json', 'binding.json'), (DOC / 'mission.json', 'mission.json')):
                writes.append(dict(path=str(path), before=ref(ROOT, path),
                    replacement=ref(ROOT, WORK / 'registration-stage' / name)))
            save(ROOT / journal, dict(profile='baseline-corpus-deployment-transaction.v1',
                status='PREPARED', validation=ref(ROOT, WORK / 'registration-check.json'), writes=writes))
            deploy.finish_transaction(ROOT, journal)
        installed = read(ROOT / journal)
        for row in installed['writes']:
            require(ref(ROOT, row['path'])['sha256'] == row['replacement']['sha256'], 'Installation mismatch')
        mutated = {row['path'] for row in installed['writes']}
        unchanged = []
        for row in baseline['archived']:
            if row['previous']['path'] not in mutated:
                verify(ROOT, row['previous'])
                unchanged.append(row['previous'])
        receipt = dict(status='DEPLOYED_LOCAL', live_activation='HELD', provider_calls=0,
            integration_complete=False, installed_files=len(installed['writes']),
            unchanged=unchanged, transaction=ref(ROOT, journal), at_utc=deploy.now())
        save(ROOT / WORK / 'deployment-result.json', receipt)
    return receipt

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'tests', 'stage', 'validate', 'commit'])
    action = parser.parse_args().action
    print(json.dumps(globals()[action](), indent=2))
