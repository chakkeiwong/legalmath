"""Retain orchestration failure and complete the unchanged role candidate."""
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import signal
import sys
import time
from scripts import prospectus_definition_roles as prior
from scripts import prospectus_definition_role_oracle as oracle
from legalmath.prospectus.execution_authority import Authority, CODE, digest as adigest
from legalmath.prospectus.successor.contracts import digest

ROOT, AUTH, engine = prior.ROOT, prior.AUTH, prior.engine
PREP = AUTH / 'reviews/definition-role-recovery-328'
HERE = AUTH / 'attempts/basf-references/attempt-067'
PLAN = 'docs/plans/prospectus-definition-role-recovery-2026-10-19.md'
METHOD = 'scripts/prospectus_definition_role_recovery.py'
WORKER = 'scripts/prospectus_definition_role_recovery_installed.py'
STAGES = ('verify', 'controls', 'package', 'installed', 'seal')
read, save, sha, rel = prior.read, prior.save, prior.sha, prior.rel
PRODUCTS = prior.PRODUCTS


def retain():
    prior.bind_runner()
    engine.frozen()
    assert not (prior.HERE / 'outputs.json').exists()
    observed = Path('/tmp/definition-debug.json')
    answer = read(observed)
    assert answer['report_sha256'] == 'fb47974140a7f1e2fd0621f9393aa693224076679d1b6c8b76d405e5f1b7fa05'
    raw = observed.read_bytes()
    with gzip.open(prior.HERE / 'diagnostic-answer.json.gz', 'xb') as stream:
        stream.write(raw)
    assert gzip.decompress((prior.HERE / 'diagnostic-answer.json.gz').read_bytes()) == raw
    measured = prior.costs()
    save(prior.HERE / 'interruption.json', {
        'status': 'INTERRUPTED_BY_AGENT', 'tool_session': 21724, 'tool_exit': 130,
        'reason': 'Incorrect liveness inference from separate sandbox process namespace',
        'original_driver_had_correct_import_path': True, 'elapsed_seconds': None,
        'charged_upper_seconds': 360, 'original_stage_receipt_preserved': True})
    base = read(prior.HERE / 'commands/ordinary-cli.json')['command']
    command = list(base)
    command[command.index('--output') + 1] = str(observed)
    save(prior.HERE / 'diagnostics.json', {'ordinary_command': command,
        'working_directory': str(ROOT), 'PYTHONPATH': str(ROOT / 'src') + ':' + str(ROOT),
        'unreviewed_probes_retained_as_observed': True,
        'observations': [{'kind': 'wrong-checkout-cli', 'exit': 2, 'bound': 30},
                         {'kind': 'pinned-cli-short', 'exit': 124, 'bound': 40, 'tool_session': 89182},
                         {'kind': 'pinned-cli-complete', 'exit': 0, 'bound': 300, 'tool_session': 68769}],
        'raw_file_sha256': sha(observed), 'report_sha256': answer['report_sha256'],
        'probe_wall_seconds': None, 'conservative_extra_seconds': 705,
        'charge_components': {'interruption': 360, 'timeout_probe': 40, 'complete_probe': 300, 'short_probes': 5},
        'known_measured_before_retention': measured, 'promotion_pending_review': True})
    observed.unlink()  # Exact lossless copy and raw-file digest retained above.
    save(prior.HERE / 'result.json', {'status': 'INCOMPLETE', 'task': 'basf-references',
        'original_task_complete': False, 'result_kind': 'AGENT_INTERRUPTED_TRIAL',
        'tests': 1761, 'candidate_failure_established': False, 'package_failure_established': False,
        'ordinary_diagnostic_retained': True, 'installed_consumer_checked': False,
        'next_action': 'Review exact retained answer and finish isolated package verification under recovery admission'})
    (prior.HERE / 'RESULT.md').write_text('''# Interrupted current-role trial

The source candidate installed and1761tests passed. The agent incorrectly
interpreted a separate sandbox process listing and interrupted the ordinary
consumer. The subsequent diagnostics were not a clean admitted stage retry:
the unpinned command loaded the wrong checkout, a40second pinned probe timed
out, and a300second pinned probe completed. Its exact output is retained for
review, not accepted here. The original driver already had the correct import
path. No candidate or package defect is established. Full stage receipts and
all diagnostic costs are retained. Recovery must independently check the full
answer and run the installed consumer before promotion.
''')
    save(prior.HERE / 'outputs.json', {str(p.relative_to(prior.HERE)): sha(p)
         for p in prior.HERE.rglob('*') if p.is_file()})
    return {'status': 'PASS', 'retained_incomplete_attempt': rel(prior.HERE), 'conservative_extra_seconds': 705}


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    measured = start['prior']['combined_measured_seconds'] + extra
    for folder in (PREP, HERE):
        for pattern in ('stages/*/result.json', 'stages/*/failure.json'):
            measured += sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    charged = start['conservative_extra_seconds']
    paths = {p for folder in (PREP, HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / n for n in (PLAN, METHOD, WORKER))
    paths.add(AUTH / 'revisions/0328.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = start['prior']['combined_bytes'] + sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    assert measured + charged < 16200 and size < 2428 * 1024**2, 'Cumulative recovery resource bound'
    return {'combined_measured_seconds': measured, 'conservative_extra_seconds': charged,
        'combined_accounted_seconds': measured + charged, 'combined_bytes': size,
        'seconds_bound': 16200, 'bytes_bound_with_4MiB_reserve': 2432 * 1024**2, 'prior_costs_reset': False,
        'unmeasured_authoring_and_older_office_time': 'UNKNOWN; never treated as zero'}


def prepare():
    program = read(AUTH / 'program.json')
    assert program['revision'] == 327
    events = Authority(ROOT).events()
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 66 and any(e['kind'] == 'REJECT' and e.get('attempt') == rel(prior.HERE)
        and e.get('reason') == 'Worker result failed or belongs to another task' for e in events)
    assert read(prior.HERE / 'result.json')['status'] == 'INCOMPLETE'
    for name, checksum in read(prior.HERE / 'outputs.json').items():
        assert sha(prior.HERE / name) == checksum
    bindings = deepcopy(read(prior.PREP / 'freeze.json')['bindings'])
    bindings.update({n: sha(ROOT / n) for n in (*CODE, PLAN, METHOD, WORKER)})
    bindings.update({rel(p): sha(p) for p in prior.HERE.rglob('*') if p.is_file()})
    for row in read(prior.PREP / 'installation.json'):
        assert sha(ROOT / row['target']) == row['after']
        bindings[row['target']] = row['after']
    for n in (prior.PREP / 'profiles.json', prior.PREP / 'profile.json', PREP / 'METHOD-REVIEW.md'):
        bindings[rel(n)] = sha(n)
    bindings.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    save(PREP / 'freeze.json', {'bindings': bindings})
    save(PREP / 'installation.json', [])
    proposal = deepcopy(program)
    proposal['revision'] = 328
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=rel(PREP / 'METHOD-REVIEW.md'),
        reason='Recover agent-interrupted trial using exact independently checked retained output and fresh isolated package execution',
        definition_role_recovery={'review': rel(PREP), 'original_task_complete': False,
            'accounted_seconds_include_conservative_charges': True, 'prior_attempt': rel(prior.HERE)})
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [rel(PREP / 'freeze.json'), rel(PREP / 'installation.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 67
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 328
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                next_action='Verify retained full-answer delta and isolated installed execution; then return to original scope analysis',
                stop_condition='67admissions;360s stages;16200accounted seconds/2432MiB including705conservative seconds;no unchanged retry')
    save(PREP / 'routes.json', routes)
    proposal['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN),
        rel(PREP / 'routes.json'): sha(PREP / 'routes.json'), rel(PREP / 'freeze.json'): sha(PREP / 'freeze.json')})
    forecast = {'seconds': costs()['combined_accounted_seconds'] + 600,
                'bytes': costs()['combined_bytes'] + 100 * 1024**2, 'estimate_only': True}
    assert forecast['seconds'] < 16200 and forecast['bytes'] < 2428 * 1024**2
    review = {'baseline': adigest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Retain orchestration failure; verify existing diagnostic under original pre-candidate oracle and fresh installed execution'],
        'skeptical_audit': {'verdict': 'PASS', 'review': rel(PREP / 'METHOD-REVIEW.md'), 'forecast': forecast},
        'evidence_contract': {'primary': 'Exact48role full-answer delta from065 plus actual installed equality and source misuse refusals',
            'promotion_veto': ['Unexpected delta', 'Missing history', 'Wrong import', 'Permissive forgery'],
            'continuation_veto': ['Frozen drift', 'Corruption', 'Resource exhaustion', 'New execution failure'],
            'explanatory_only': ['Runtime', 'Counts'], 'not_concluded': ['Scope completion', 'External package defect', 'Whole build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 66, 'new_maximum': 67,
            'retained_attempts': attempts, 'reason': 'Agent interruption invalidated orderly trial completion; candidate and predeclared expectations unchanged',
            'next_discriminating_check': 'Independent retained-answer verification and fresh package/installed-origin equality',
            'stop_condition': 'Existing16200accounted seconds/2432MiB;705additional conservative charge;no unchanged retry',
            'same_scope_authorization': 'Continue authorized internally established general build and repair execution problems'}}
    save(PREP / 'proposal.json', proposal)
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 328, 'forecast': forecast}


def cli_arguments(output):
    args = prior.cli_arguments(output)
    args[args.index('--output') + 1] = str(HERE / output)
    return args


def verify():
    from legalmath.prospectus.successor import definition_roles as module
    products, ordinary = prior.baseline()
    actual = read(prior.HERE / 'diagnostic-answer.json.gz')
    profile = read(prior.PREP / 'profile.json')
    result = module.verify_answer(actual, ordinary, profile, products, ROOT, expected_profile_sha256=digest(profile))
    independent = oracle.verify(actual, ordinary, products, profile,
                               read(prior.PREP / 'cases.json')['expected_original_changes'])
    save(HERE / 'verification.json', result)
    save(HERE / 'independent-verification.json', independent)
    tests = read(prior.HERE / 'stages/tests/result.json')
    assert tests['tests'] == 1761 and tests['failures'] == tests['errors'] == tests['skipped'] == 0
    raw = gzip.decompress((prior.HERE / 'diagnostic-answer.json.gz').read_bytes())
    with gzip.open(HERE / 'ordinary-answer.json.gz', 'xb') as stream:
        stream.write(raw)
    assert gzip.decompress((HERE / 'ordinary-answer.json.gz').read_bytes()) == raw
    return {'status': 'PASS', 'ordinary_output_from_retained_diagnostic': True,
            'prior_tests_retained': 1761, 'independent': independent, 'answer_sha256': digest(actual)}


def controls():
    # The frozen066method applies identical controls to the recovered answer.
    # Temporarily redirect only its output directory; restore even on failure.
    saved = prior.HERE
    try:
        prior.HERE = HERE
        return prior.controls()
    finally:
        prior.HERE = saved


def installed():
    engine.execute('installed-cli', [read(HERE / 'package.json')['python'], '-I', '-B', str(ROOT / WORKER), str(ROOT), str(HERE)], 330)
    result = read(HERE / 'installed-result.json')
    result.update(engine.compress_output('installed-answer.json'))
    return result


def seal():
    result = {'status': 'PASS', 'task': 'basf-references', 'original_task_complete': False,
        'result_kind': 'RECOVERED_CURRENT_DEFINITION_ROLES', 'only_reviewed_role_delta': True,
        'ordinary_output_from_retained_diagnostic': True, 'installed_cli_equal': True,
        'legal_truth_established': False, 'resources': costs(),
        'next_action': 'Continue original governing-scope and unquoted/morphological-use analysis'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(HERE / 'stages' / s / 'started.json')['command'] for s in STAGES],
        'ordinary_command_record': rel(prior.HERE / 'diagnostics.json'),
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU; no GPU use',
        'seeds': 'N/A deterministic', 'data_version': sha(prior.PREP / 'cases.json'),
        'wall_time': costs(), 'plan': PLAN, 'result': rel(HERE / 'result.json')})
    (HERE / 'RESULT.md').write_text('''# Verified current definition roles after execution recovery

The retained ordinary CLI output and the fresh isolated installed output agree
completely. The independent expectation from audit065permits exactly48role
updates across44source units, plus the explicit projection history. All source
text,610definition-use associations, legal uncertainty and unrelated results
are preserved. The1761tests from066remain valid because no candidate changed;
eleven actual source/profile/result forgeries refuse here.

|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain optional current-role correction|Independent complete-answer delta and real installed equality|Mappings/source/result forgeries refused|Source scope and unseen sources|Substantive scope/use analysis|Whole task or build|

The interrupted066run and unreviewed probes remain recorded. Recovery uses the
actual diagnostic answer, verified against preexisting expectations, and a new
installed execution; it does not rewrite the interrupted run as successful.
Our incorrect process-namespace inference caused the interruption. Our source
metadata adaptation caused the stale roles. Neither supports a fundamental
external-package limitation. An incorrect original heading classification is
the strongest remaining alternative explanation; only a new source review
could justify changing that separate authority.
''')
    return result


def main():
    stage = sys.argv[1]
    assert stage in ('retain', 'prepare', 'prepare_reviewed', *STAGES)
    folder = (PREP if stage in ('retain', 'prepare', 'prepare_reviewed') else HERE) / 'stages' / stage
    assert not (folder / 'started.json').exists(), 'Unchanged retry refused'
    if stage == 'prepare':
        save(PREP / 'accounting-start.json', {'prior': prior.costs(), 'conservative_extra_seconds': 705,
            'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
            'program_bytes': (AUTH / 'program.json').stat().st_size})
    elif stage == 'prepare_reviewed':
        assert read(PREP / 'stages/prepare/failure.json')['type'] == 'AssertionError'
        assert (PREP / 'PREPARATION-REPAIR.md').exists()
    if stage in STAGES:
        for before in STAGES[:STAGES.index(stage)]:
            assert read(HERE / 'stages' / before / 'result.json')['status'] == 'PASS'
        engine.PREP, engine.HERE, engine.PLAN = PREP, HERE, PLAN
        engine.METHOD, engine.WORKER, engine.TARGETS = METHOD, WORKER, ()
        engine.costs, engine.cli_arguments = costs, cli_arguments
        engine.frozen()
    bound = 90 if stage in ('retain', 'prepare', 'prepare_reviewed') else 360
    save(folder / 'started.json', {'command': ['.venv/bin/python', '-m', 'scripts.prospectus_definition_role_recovery', stage],
        'started_at': datetime.now(timezone.utc).isoformat(), 'seconds_bound': bound})
    start = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Definition recovery bound')))
    signal.alarm(bound)
    try:
        result = (prepare if stage == 'prepare_reviewed' else globals().get(stage) or getattr(engine, stage))()
        if stage in STAGES:
            engine.frozen()
        if stage != 'retain':
            costs(time.monotonic() - start)
        result['wall_seconds'] = time.monotonic() - start
        save(folder / 'result.json', result)
        if stage == 'seal':
            save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as error:
        save(folder / 'failure.json', {'type': type(error).__name__, 'message': str(error), 'wall_seconds': time.monotonic() - start})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
