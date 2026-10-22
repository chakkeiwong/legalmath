"""Bounded, separately frozen repair of the failed source-definition verifier."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
import shutil
import signal
import sys
import time
import xml.etree.ElementTree as ET

from scripts import prospectus_unquoted_definitions as prior
from scripts import prospectus_unquoted_verifier_oracle as oracle
from legalmath.prospectus.execution_authority import Authority, CODE, digest as adigest
from legalmath.prospectus.successor.contracts import digest

ROOT, AUTH, engine = prior.ROOT, prior.AUTH, prior.engine
PREP = AUTH / 'reviews/unquoted-verifier-repair-350'
HERE = AUTH / 'attempts/basf-references/attempt-089'
PLAN = 'docs/plans/prospectus-unquoted-verifier-repair-2026-10-19.md'
METHOD = 'scripts/prospectus_unquoted_verifier_repair.py'
WORKER = 'scripts/prospectus_unquoted_verifier_repair_installed.py'
TEST = 'tests/prospectus_successor/test_unquoted_verifier_repair.py'
FILES = (PLAN, METHOD, WORKER, TEST, 'scripts/prospectus_unquoted_verifier_oracle.py',
         'docs/implementation/prospectus-execution-authority/reviews/unquoted-verifier-repair-350/METHOD-REVIEW.md')
TARGETS = prior.TARGETS
STAGES = ('tests', 'verify-retained', 'controls', 'package', 'installed', 'seal')
read, save, sha, rel = prior.read, prior.save, prior.sha, prior.rel
PRODUCTS = prior.PRODUCTS
SECONDS_BOUND, BYTES_BOUND = prior.SECONDS_BOUND, prior.BYTES_BOUND


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    base = start['prior']
    seconds = base['combined_measured_seconds'] + extra
    for folder in (PREP, HERE):
        for pattern in ('stages/*/result.json', 'stages/*/failure.json'):
            seconds += sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths = {p for folder in (PREP, HERE) for p in folder.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / n for n in FILES)
    paths.add(AUTH / 'revisions/0350.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = base['combined_bytes'] + sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    charge = base['conservative_extra_seconds']
    assert seconds + charge < SECONDS_BOUND and size < BYTES_BOUND - 4 * 1024**2, 'Cumulative verifier repair bound'
    return {'combined_measured_seconds': seconds, 'conservative_extra_seconds': charge,
            'combined_accounted_seconds': seconds + charge, 'combined_bytes': size,
            'seconds_bound': SECONDS_BOUND, 'bytes_bound_with_4MiB_reserve': BYTES_BOUND,
            'prior_costs_reset': False, 'unmeasured_authoring_and_older_office_time': 'UNKNOWN; never treated as zero'}


def testfiles():
    return [*prior.testfiles(), TEST]


def verify_lineage():
    for n, value in read(prior.HERE / 'outputs.json').items():
        assert sha(prior.HERE / n) == value, n
    for n, value in read(prior.PREP / 'freeze.json')['bindings'].items():
        assert sha(ROOT / n) == value, n
    for row in read(prior.PREP / 'installation.json'):
        assert sha(ROOT / row['target']) == row['after'], row['target']
    assert read(prior.HERE / 'result.json')['status'] == 'FAIL'
    assert read(prior.HERE / 'stages/consume/result.json')['status'] == 'PASS'
    assert read(prior.HERE / 'stages/controls/failure.json')['type'] == 'TypeError'


def prepare():
    program = read(AUTH / 'program.json')
    assert program['revision'] == 349
    events = Authority(ROOT).events()
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 88
    assert any(e['kind'] == 'REJECT' and e.get('attempt') == rel(prior.HERE) for e in events)
    verify_lineage()
    for name in ('expected.json', 'source-freeze.json', 'profile.json', 'profiles.json'):
        shutil.copyfile(prior.PREP / name, PREP / name)
    retained = {'ordinary_answer': rel(prior.HERE / 'ordinary-answer.json.gz'),
                'ordinary_answer_file_sha256': sha(prior.HERE / 'ordinary-answer.json.gz'),
                'ordinary_answer_sha256': read(prior.HERE / 'stages/consume/result.json')['answer_sha256'],
                'ordinary_execution_reused': True, 'prior_attempt_failed_in_controls': True,
                'production_changed': False, 'source_expectations_changed': False}
    save(PREP / 'retained.json', retained)
    save(PREP / 'installation.json', [{'target': n, 'before': sha(ROOT / n), 'after': sha(ROOT / n)} for n in TARGETS])
    bindings = dict(read(prior.PREP / 'freeze.json')['bindings'])
    bindings.update({n: sha(ROOT / n) for n in (*CODE, *FILES, *testfiles(), prior.METHOD, 'scripts/prospectus_residual_coverage.py')})
    bindings.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    bindings.update({rel(prior.HERE / n): value for n, value in read(prior.HERE / 'outputs.json').items()})
    for path in (prior.HERE / 'outputs.json', prior.PREP / 'freeze.json'):
        bindings[rel(path)] = sha(path)
    save(PREP / 'freeze.json', {'bindings': bindings, 'candidate_evaluated': False,
                               'ordinary_execution_reused': True})
    proposal = deepcopy(program)
    proposal['revision'] = 350
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=rel(PREP / 'METHOD-REVIEW.md'),
        reason='Repair reproduced verifier TypeError with explicit schema assertions; preserve production and source readings',
        verifier_repair_review={'review': rel(PREP), 'original_task_complete': False,
            'accounted_seconds_bound': SECONDS_BOUND, 'bytes_bound_with_4MiB_reserve': BYTES_BOUND})
    task['inputs'] = list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS] + list(bindings) + [rel(PREP / 'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 89
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 350
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                next_action='Repair explicit verifier refusals and fresh installed equality, then return to substantive definition/use scope',
                stop_condition='89 admissions; 24000 accounted seconds and 3584 MiB including 4 MiB reserve; no unchanged retry')
    save(PREP / 'routes.json', routes)
    proposal['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN),
        rel(PREP / 'routes.json'): sha(PREP / 'routes.json'), rel(PREP / 'freeze.json'): sha(PREP / 'freeze.json')})
    snapshot = costs()
    forecast = {'seconds': snapshot['combined_accounted_seconds'] + 650,
                'bytes': snapshot['combined_bytes'] + 96 * 1024**2, 'estimate_only': True}
    assert forecast['seconds'] < SECONDS_BOUND and forecast['bytes'] < BYTES_BOUND - 4 * 1024**2, 'Repair forecast does not fit'
    review = {'baseline': adigest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Explicit verifier shape assertions; no production or source-expectation change',
                    'Retain failed attempt088 and reuse ordinary execution with verified complete lineage'],
        'skeptical_audit': {'verdict': 'PASS', 'review': rel(PREP / 'METHOD-REVIEW.md'), 'forecast': forecast},
        'evidence_contract': {'primary': 'All original mutations and malformed reports deliberately refused; exact retained source and fresh complete installed equality',
            'promotion_veto': ['Unexpected verifier exception', 'Wrong source/profile', 'Changed production', 'Changed prior answer', 'Wrong installed import'],
            'continuation_veto': ['Corrupt frozen baseline', 'Method drift', 'Cumulative resource bound'],
            'explanatory_only': ['Counts', 'Runtime'],
            'not_concluded': ['General recall', 'Legal meaning', 'Whole original task or build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 88, 'new_maximum': 89,
            'retained_attempts': attempts, 'reason': 'Reproduced verifier implementation error requires a changed bounded repair',
            'next_discriminating_check': 'Explicit AssertionError refusals and unchanged complete installed answer',
            'stop_condition': '24000 seconds / 3584 MiB cumulative with 4 MiB reserve; no unchanged retry',
            'same_scope_authorization': 'User requested reviewed internally evidenced whole general build and continued execution'},
        'resource_accounting': {'retained_costs': snapshot, 'limits_extended': False,
            'seconds_bound': SECONDS_BOUND, 'bytes_with_reserve': BYTES_BOUND}}
    with (PREP / 'proposal.json').open('x') as stream:
        json.dump(proposal, stream, ensure_ascii=False, separators=(',', ':'))
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 350, 'candidate_evaluated': False, 'forecast': forecast}


def tests():
    engine.execute('pytest', [str(ROOT / '.venv/bin/python'), '-m', 'pytest',
        *[str(ROOT / n) for n in testfiles()], '-q', '--junitxml=' + str(HERE / 'pytest.xml')], 150)
    suites = list(ET.parse(HERE / 'pytest.xml').getroot().iter('testsuite'))
    counts = {k: sum(int(s.attrib.get(k, 0)) for s in suites) for k in ('tests', 'failures', 'errors', 'skipped')}
    assert counts['tests'] and not any(counts[k] for k in ('failures', 'errors', 'skipped'))
    return {'status': 'PASS', **counts}


def verify_retained():
    verify_lineage()
    products, old = prior.baseline()
    actual = read(prior.HERE / 'ordinary-answer.json.gz')
    assert digest(actual) == read(PREP / 'retained.json')['ordinary_answer_sha256']
    result = oracle.verify(actual, old, products, read(PREP / 'expected.json'), read(PREP / 'profile.json'))
    result.update(ordinary_execution_reused=True, original_attempt=rel(prior.HERE), production_changed=False)
    save(HERE / 'independent-verification.json', result)
    return result


def controls():
    products, old = prior.baseline()
    actual = read(prior.HERE / 'ordinary-answer.json.gz')
    refused = {}
    for kind in ('delete-name', 'wrong-term', 'swap-scopes', 'drop-scope', 'drop-condition',
                 'wrong-value', 'source-map-delete', 'invent-missing', 'false-meaning',
                 'false-completion', 'source-identity', 'prior-answer', 'profile-identity',
                 'term-list', 'value-none', 'condition-list', 'missing-span-offset', 'malformed-kind'):
        bad = deepcopy(actual)
        report = bad[oracle.KEY]
        row = report['candidates'][0]
        amounts = [r for r in report['candidates'] if r['kind'] == 'PURPOSE_CONDITIONED_AMOUNT']
        if kind == 'delete-name': report['candidates'].pop()
        elif kind == 'wrong-term': row['term']['start'] += 1
        elif kind == 'swap-scopes': amounts[0]['scope'], amounts[1]['scope'] = amounts[1]['scope'], amounts[0]['scope']
        elif kind == 'drop-scope': amounts[0]['scope'] = None
        elif kind == 'drop-condition': next(r for r in report['candidates'] if r['condition'])['condition'] = None
        elif kind == 'wrong-value': amounts[1]['value'] = deepcopy(amounts[0]['value'])
        elif kind == 'source-map-delete': row['term']['source_projection'].pop()
        elif kind == 'invent-missing': row['label'] = 'Zinsperiode'
        elif kind == 'false-meaning': row['meaning'] = 'A legally admitted definition'
        elif kind == 'false-completion': report['whole_task_complete'] = True
        elif kind == 'source-identity': report['text_sha256'] = '0' * 64
        elif kind == 'prior-answer': bad['questions']['Q1']['status'] = 'YES'
        elif kind == 'profile-identity': report['profile_sha256'] = '0' * 64
        elif kind == 'term-list': row['term'] = []
        elif kind == 'value-none': row['value'] = None
        elif kind == 'condition-list': next(r for r in report['candidates'] if r['condition'])['condition'] = []
        elif kind == 'missing-span-offset': del row['term']['start']
        else: row['kind'] = []
        bad['report_sha256'] = digest({k: v for k, v in bad.items() if k != 'report_sha256'})
        try:
            oracle.verify(bad, old, products, read(PREP / 'expected.json'), read(PREP / 'profile.json'))
        except AssertionError as error:
            refused[kind] = {'exception': 'AssertionError', 'reason': str(error), 'outer_digest_recomputed': True}
        else:
            raise AssertionError('Accepted ' + kind)
    save(HERE / 'controls.json', {'status': 'PASS', 'refused': refused, 'unexpected_exceptions_accepted': False})
    return {'status': 'PASS', 'refused': len(refused), 'original_controls': 12, 'unexpected_exceptions_accepted': False}


def installed():
    engine.execute('installed-cli', [read(HERE / 'package.json')['python'], '-I', '-B', str(ROOT / WORKER),
                                    str(ROOT), str(HERE), str(PREP)], 360)
    result = read(HERE / 'installed-result.json')
    result.update(engine.compress_output('installed-answer.json'))
    return result


def seal():
    result = {'status': 'PASS', 'task': 'basf-references', 'original_task_complete': False,
        'result_kind': 'REPAIRED_UNQUOTED_VERIFIER', **read(HERE / 'independent-verification.json'),
        'ordinary_installed_equal': True, 'controls': read(HERE / 'stages/controls/result.json'),
        'resources': costs(), 'next_action': 'Return to original substantive definition-use scope and historical-law requirements'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(HERE / 'stages' / s / 'started.json')['command'] for s in STAGES],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU; GPU intentionally hidden',
        'seeds': 'N/A deterministic', 'data_version': sha(PRODUCTS), 'wall_time': costs(),
        'ordinary_execution_reused': rel(prior.HERE), 'plan': PLAN, 'result': rel(HERE / 'result.json')})
    with (HERE / 'RESULT.md').open('x') as stream:
        stream.write(RESULT_NOTE)
    return result


def main():
    stage = sys.argv[1]
    assert stage == 'prepare' or stage in STAGES
    folder = (PREP if stage == 'prepare' else HERE) / 'stages' / stage
    assert not (folder / 'started.json').exists(), 'Unchanged retry refused'
    if stage == 'prepare':
        snapshot = prior.costs()
        retained_seconds = read(prior.HERE / 'failure-retention.json')['wall_seconds']
        for key in ('combined_measured_seconds', 'combined_accounted_seconds'):
            snapshot[key] += retained_seconds
        save(PREP / 'accounting-start.json', {'prior': snapshot,
            'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
            'program_bytes': (AUTH / 'program.json').stat().st_size})
    else:
        for preceding in STAGES[:STAGES.index(stage)]:
            assert read(HERE / 'stages' / preceding / 'result.json')['status'] == 'PASS'
        costs()
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    engine.PREP, engine.HERE, engine.PLAN, engine.METHOD, engine.WORKER, engine.TARGETS = PREP, HERE, PLAN, METHOD, WORKER, TARGETS
    engine.costs, engine.testfiles = costs, testfiles
    bound = 90 if stage == 'prepare' else 420
    save(folder / 'started.json', {'command': ['.venv/bin/python', '-m', 'scripts.prospectus_unquoted_verifier_repair', stage],
        'started_at': datetime.now(timezone.utc).isoformat(), 'seconds_bound': bound})
    started = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Verifier repair stage bound')))
    signal.alarm(bound)
    try:
        if stage != 'prepare': engine.frozen()
        function = globals().get(stage.replace('-', '_')) or getattr(engine, stage)
        result = function()
        if stage != 'prepare': engine.frozen()
        costs(time.monotonic() - started)
        result['wall_seconds'] = time.monotonic() - started
        save(folder / 'result.json', result)
        if stage == 'seal':
            save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as error:
        save(folder / 'failure.json', {'type': type(error).__name__, 'message': str(error), 'wall_seconds': time.monotonic() - started})
        raise
    finally:
        signal.alarm(0)


RESULT_NOTE = '''# Verifier repair preserves the source result

Explicit shape assertions repair the reproduced missing-scope crash. All twelve
original mutations and six extra profile/malformed-span controls are deliberately
refused with AssertionError; no unexpected exception counts as a refusal. The
seven source expectations and production files remain unchanged. Attempt088's
actual ordinary execution is reused after checking its complete frozen lineage.
A fresh isolated installed CLI equals that complete answer.

|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain repaired finite verifier|Exact retained source readings, intentional adverse refusals, fresh installed equality|No unexpected exception, production drift, source mismatch or wrong import|Unlisted grammar and governing use scope|Return to original substantive definition/use and historical-law work|General recall, legal truth, original task or whole build closure|

The failure was in our verifier implementation. It supplies no evidence against
an external package. The strongest remaining alternative is an incorrect finite
source reading or unlisted linguistic form; a source mismatch would overturn this
result. Counts describe this check, and do not establish broad legal coverage.
'''

if __name__ == '__main__':
    main()
