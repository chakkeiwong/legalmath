"""Retain090's failure, then run a separately frozen one-file spelling repair."""
from copy import deepcopy
from datetime import datetime, timezone
import ast
import json
import os
import re
import shutil
import signal
import sys
import time
import xml.etree.ElementTree as ET

from scripts import prospectus_purpose_uses as prior
from legalmath.prospectus.execution_authority import Authority, CODE, digest as adigest
from legalmath.prospectus.successor.contracts import digest

ROOT, AUTH, engine = prior.ROOT, prior.AUTH, prior.engine
PREP = AUTH / 'reviews/purpose-use-spelling-repair-352'
HERE = AUTH / 'attempts/basf-references/attempt-091'
PLAN = 'docs/plans/prospectus-purpose-use-spelling-repair-2026-10-19.md'
METHOD = 'scripts/prospectus_purpose_use_spelling_repair.py'
WORKER = prior.WORKER
TEST = 'tests/prospectus_successor/test_purpose_use_spelling_repair.py'
REVIEW = str((PREP / 'METHOD-REVIEW.md').relative_to(ROOT))
FILES = (PLAN, METHOD, TEST, REVIEW)
TARGETS = (prior.TARGETS[0],)
STAGES = prior.STAGES
ORIGINAL_TESTFILES = tuple(prior.testfiles())
read, save, sha, rel = prior.read, prior.save, prior.sha, prior.rel
PRODUCTS = prior.PRODUCTS
SECONDS_BOUND, BYTES_BOUND = prior.SECONDS_BOUND, prior.BYTES_BOUND


def xml_counts(path):
    suites = list(ET.parse(path).getroot().iter('testsuite'))
    return {k: sum(int(s.attrib.get(k, 0)) for s in suites)
            for k in ('tests', 'failures', 'errors', 'skipped')}


def retain_failure():
    folder = prior.HERE
    assert not (folder / 'result.json').exists(), 'Failure already retained'
    admission = read(folder / 'admission.json')
    assert adigest(read(AUTH / 'program.json')) == admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec']) == admission['binding']
    for name, value in read(prior.PREP / 'freeze.json')['bindings'].items():
        assert sha(ROOT / name) == value, name
    for row in read(prior.PREP / 'installation.json'):
        assert sha(ROOT / row['target']) == row['after'], row['target']
    counts = xml_counts(folder / 'pytest.xml')
    assert counts == {'tests': 175, 'failures': 5, 'errors': 0, 'skipped': 0}
    from legalmath.prospectus.successor.purpose_uses import family
    stem, noun = family('sondermäßige Bonus')
    pattern = re.escape(stem) + r'(?:en|er|es|em|e) ' + re.escape(noun)
    wrong = bool(re.fullmatch(pattern, 'sondermäßigen Bonus', re.I))
    preserved = bool(re.fullmatch(r'sondermäßig(?:en|er|es|em|e) bonus', 'sondermäßigen Bonus', re.I))
    assert stem == 'sondermässig' and wrong is False and preserved is True
    save(folder / 'diagnostic.json', {'classification': 'OUR_IMPLEMENTATION_FAILURE',
        'label': 'sondermäßige Bonus', 'derived_stem': stem, 'actual_match': wrong,
        'spelling_preserving_match': preserved, 'pytest': counts,
        'root_cause': 'Full case folding expands sharp-s; regex simple case matching does not',
        'source_oracle_changed': False, 'complete_consumers_run': False})
    result = {'status': 'FAIL', 'task': 'basf-references', 'original_task_complete': False,
        'result_kind': 'PURPOSE_USE_IMPLEMENTATION_FAILURE', 'pytest': counts,
        'classification': 'OUR_IMPLEMENTATION_FAILURE', 'resources': prior.costs(),
        'next_action': 'Changed one-file spelling repair; preserve original tests and independent source oracle'}
    save(folder / 'result.json', result)
    save(folder / 'run-manifest.json', {'git_commit': admission['git_commit'],
        'commands': [read(folder / 'stages' / stage / 'started.json')['command'] for stage in ('install', 'tests')]
            + [['.venv/bin/python', '-m', 'scripts.prospectus_purpose_use_spelling_repair', 'retain-failure']],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU;GPU intentionally hidden',
        'seeds': 'N/A deterministic', 'data_version': sha(PRODUCTS), 'wall_time': prior.costs(),
        'plan': prior.PLAN, 'result': rel(folder / 'result.json'), 'unrun_stages': list(STAGES[2:])})
    with (folder / 'RESULT.md').open('x') as stream:
        stream.write('# Source-use discovery failed on printed sharp-s spelling\n\n'
            'The test run completed with170 passes and five failures. All five failed '
            'renamed terms using `sondermäßige`. Full case folding expanded `ß` to `ss`, '
            'but the regex retained simple case matching. The resulting family did not '
            'match its own printed source. This is our implementation defect.\n\n'
            'No complete ordinary or installed consumer ran; no source-use integration '
            'success is claimed. Keep the installed candidate, frozen methods, source '
            'readings, log, XML and installation-count corrigendum unchanged. The failure '
            'rejects this candidate and calls for a separately reviewed spelling repair, '
            'not rejection of the source-discovery approach or any package.\n\n'
            '|Decision|Primary criterion|Veto|Uncertainty|Next action|Not concluded|\n'
            '|---|---|---|---|---|---|\n'
            '|Reject090|Five renamed cases fail|Implementation veto|Full supported grammar '
            'still needs repaired tests and consumers|Review changed repair retaining all '
            'costs|General discovery or build closure|\n')
    save(folder / 'outputs.json', {str(p.relative_to(folder)): sha(p) for p in folder.rglob('*') if p.is_file()})
    return result


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    base = start['prior']
    seconds = base['combined_measured_seconds'] + extra
    for folder in (PREP, HERE):
        for pattern in ('stages/*/result.json', 'stages/*/failure.json'):
            seconds += sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths = {p for folder in (PREP, HERE) for p in folder.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / name for name in FILES)
    paths.add(AUTH / 'revisions/0352.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = base['combined_bytes'] + sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    size += sum(max(0, (ROOT / name).stat().st_size - start['production_bytes'][name]) for name in TARGETS)
    charge = base['conservative_extra_seconds']
    assert seconds + charge < SECONDS_BOUND and size < BYTES_BOUND - 4 * 1024**2, 'Cumulative spelling-repair bound'
    return {'combined_measured_seconds': seconds, 'conservative_extra_seconds': charge,
        'combined_accounted_seconds': seconds + charge, 'combined_bytes': size,
        'seconds_bound': SECONDS_BOUND, 'bytes_bound_with_4MiB_reserve': BYTES_BOUND,
        'prior_costs_reset': False, 'unmeasured_authoring_and_older_office_time': 'UNKNOWN; never treated as zero'}


def testfiles():
    return [*ORIGINAL_TESTFILES, TEST]


def prepare():
    program = read(AUTH / 'program.json')
    assert program['revision'] == 351
    events = Authority(ROOT).events()
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 90
    assert any(e['kind'] == 'REJECT' and e.get('attempt') == rel(prior.HERE) for e in events)
    for name, value in read(prior.HERE / 'outputs.json').items():
        assert sha(prior.HERE / name) == value, name
    assert read(prior.HERE / 'result.json')['status'] == 'FAIL'
    for name in ('expected.json', 'source-freeze.json', 'profile.json'):
        shutil.copyfile(prior.PREP / name, PREP / name)
    manifest = read(prior.PREP / 'profiles.json')
    row = next(r for r in manifest['profiles'] if r['name'] == 'purpose_uses')
    row['path'] = rel(PREP / 'profile.json')
    assert row['file_sha256'] == sha(PREP / 'profile.json')
    save(PREP / 'profiles.json', manifest)
    save(PREP / 'retained.json', {'failed_attempt': rel(prior.HERE),
        'failed_outputs_sha256': sha(prior.HERE / 'outputs.json'),
        'source_expectations_from': rel(prior.PREP / 'expected.json'),
        'source_expectations_sha256': sha(prior.PREP / 'expected.json'),
        'source_expectations_changed': False, 'source_oracle_changed': False,
        'normal_answer_available_from_failed_attempt': False})
    (PREP / 'candidate').mkdir()
    source = (ROOT / TARGETS[0]).read_text()
    assert source.count('.casefold()') == 2
    candidate = source.replace('.casefold()', '.lower()').replace(
        "    adjective, noun = words\n", "    adjective, noun = words\n"
        "    # Simple regex case matching preserves sharp-s; full case folding would expand it.\n")
    ast.parse(candidate)
    (PREP / 'candidate/purpose_uses.py').write_text(candidate)
    save(PREP / 'installation.json', [{'target': TARGETS[0], 'before': sha(ROOT / TARGETS[0]),
        'candidate': rel(PREP / 'candidate/purpose_uses.py'), 'after': sha(PREP / 'candidate/purpose_uses.py')}])
    bindings = dict(read(prior.PREP / 'freeze.json')['bindings'])
    bindings.update({name: sha(ROOT / name) for name in (*CODE, *FILES, *testfiles(), prior.METHOD, WORKER)})
    bindings.update({rel(p): sha(p) for p in (ROOT / 'src/legalmath').rglob('*') if p.is_file()
        and '__pycache__' not in p.parts and p.suffix != '.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    bindings.update({rel(prior.HERE / name): value for name, value in read(prior.HERE / 'outputs.json').items()})
    bindings[rel(prior.HERE / 'outputs.json')] = sha(prior.HERE / 'outputs.json')
    bindings[rel(prior.PREP / 'freeze.json')] = sha(prior.PREP / 'freeze.json')
    save(PREP / 'freeze.json', {'bindings': bindings, 'candidate_evaluated': False,
        'source_expectations_reused_unchanged': True, 'production_changes': list(TARGETS)})
    proposal = deepcopy(program)
    proposal['revision'] = 352
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=REVIEW,
        reason='Repair reproduced sharp-s family mismatch, retain failed090 and source oracle, then return to original law/scope gaps',
        purpose_use_spelling_repair={'review': rel(PREP), 'original_task_complete': False,
            'accounted_seconds_bound': SECONDS_BOUND, 'bytes_bound_with_4MiB_reserve': BYTES_BOUND})
    task['inputs'] = list(dict.fromkeys([name for name in task['inputs'] if name not in TARGETS]
        + list(bindings) + [rel(PREP / 'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 91
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 352
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                next_action='Verify spelling repair and complete consumers; reassess seven original classes and return to historical/onward law',
                stop_condition='91 admissions;25200 accounted seconds;3712MiB including4MiB reserve;no unchanged retry')
    save(PREP / 'routes.json', routes)
    proposal['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN),
        rel(PREP / 'routes.json'): sha(PREP / 'routes.json'), rel(PREP / 'freeze.json'): sha(PREP / 'freeze.json')})
    snapshot = costs()
    forecast = {'seconds': snapshot['combined_accounted_seconds'] + 1100,
        'bytes': snapshot['combined_bytes'] + 96 * 1024**2, 'estimate_only': True}
    assert forecast['seconds'] < SECONDS_BOUND and forecast['bytes'] < BYTES_BOUND - 4 * 1024**2, 'Forecast does not fit'
    review = {'baseline': adigest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Preserve printed sharp-s with simple lowercasing instead of full case folding',
            'Retain090 failure,unchanged source expectations and all90 admissions; add spelling/collision tests'],
        'skeptical_audit': {'verdict': 'PASS', 'review': REVIEW, 'forecast': forecast},
        'evidence_contract': {'primary': 'Original and spelling/collision cases,six frozen source readings,all refusals,and full ordinary/installed equality',
            'promotion_veto': ['Wrong spelling/span/role/purpose/source', 'False legal admission', 'Changed old answer', 'Accepted mutation', 'Wrong import'],
            'continuation_veto': ['Corrupt frozen evidence', 'Method drift', 'Cumulative resource bound'],
            'explanatory_only': ['Counts', 'Runtime'],
            'not_concluded': ['General morphology/recall', 'Legal governing scope', 'Historical law', 'Entitlement', 'Whole build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 90, 'new_maximum': 91,
            'retained_attempts': attempts, 'reason': 'Five reproduced sharp-s failures require a changed one-file implementation',
            'next_discriminating_check': 'Original failures and distinct sharp-s/ss terms,then exact source and complete isolated consumers',
            'stop_condition': '25200seconds/3712MiB cumulative including4MiB reserve;no unchanged retry',
            'same_scope_authorization': 'User requested continued reviewed internal evidence for the whole general build'},
        'resource_accounting': {'retained_costs': snapshot, 'limits_extended': False,
            'seconds_bound': SECONDS_BOUND, 'bytes_with_reserve': BYTES_BOUND}}
    with (PREP / 'proposal.json').open('x') as stream:
        json.dump(proposal, stream, ensure_ascii=False, separators=(',', ':'))
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 352, 'candidate_evaluated': False, 'forecast': forecast}


def install():
    rows = read(PREP / 'installation.json')
    for row in rows:
        assert sha(ROOT / row['target']) == row['before']
        shutil.copyfile(ROOT / row['candidate'], ROOT / row['target'])
    return {'status': 'PASS', 'production_files': len(rows), 'manifest_sha256': sha(PREP / 'installation.json')}


def seal():
    result = {'status': 'PASS', 'task': 'basf-references', 'original_task_complete': False,
        'result_kind': 'REPAIRED_SOURCE_PURPOSE_USE_DISCOVERY', **read(HERE / 'independent-verification.json'),
        'ordinary_installed_equal': True, 'tests': read(HERE / 'stages/tests/result.json'),
        'controls': read(HERE / 'stages/controls/result.json'), 'resources': costs(),
        'next_action': 'Reassess seven original source classes and continue historical/onward law and scope evidence'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(HERE / 'stages' / stage / 'started.json')['command'] for stage in STAGES],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU;GPU intentionally hidden',
        'seeds': 'N/A deterministic', 'data_version': sha(PRODUCTS), 'wall_time': costs(),
        'plan': PLAN, 'result': rel(HERE / 'result.json')})
    with (HERE / 'RESULT.md').open('x') as stream:
        stream.write(RESULT_NOTE)
    return result


def configure():
    for module in (prior, engine):
        for name in ('PREP', 'HERE', 'PLAN', 'METHOD', 'WORKER', 'TARGETS', 'costs', 'testfiles'):
            setattr(module, name, globals()[name])


def main():
    stage = sys.argv[1]
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    if stage == 'retain-failure':
        print(json.dumps(retain_failure()))
        return
    assert stage == 'prepare' or stage in STAGES
    folder = (PREP if stage == 'prepare' else HERE) / 'stages' / stage
    assert not (folder / 'started.json').exists(), 'Unchanged retry refused'
    if stage == 'prepare':
        save(PREP / 'accounting-start.json', {'prior': prior.costs(),
            'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
            'program_bytes': (AUTH / 'program.json').stat().st_size,
            'production_bytes': {name: (ROOT / name).stat().st_size for name in TARGETS}})
    else:
        for preceding in STAGES[:STAGES.index(stage)]:
            assert read(HERE / 'stages' / preceding / 'result.json')['status'] == 'PASS'
        costs()
        configure()
    bound = 90 if stage == 'prepare' else 420
    save(folder / 'started.json', {'command': ['.venv/bin/python', '-m', 'scripts.prospectus_purpose_use_spelling_repair', stage],
        'started_at': datetime.now(timezone.utc).isoformat(), 'seconds_bound': bound})
    started = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Spelling-repair stage bound')))
    signal.alarm(bound)
    try:
        if stage != 'prepare': engine.frozen(installed=stage != 'install')
        function = globals().get(stage) or getattr(prior, stage, None) or getattr(engine, stage)
        result = function()
        if stage != 'prepare': engine.frozen()
        costs(time.monotonic() - started)
        result['wall_seconds'] = time.monotonic() - started
        save(folder / 'result.json', result)
        if stage == 'seal':
            save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as error:
        save(folder / 'failure.json', {'type': type(error).__name__, 'message': str(error),
            'wall_seconds': time.monotonic() - started})
        raise
    finally:
        signal.alarm(0)


RESULT_NOTE = '''# Purpose-use discovery preserves printed sharp-s spelling

The changed one-file repair passes the original tests and the added renamed
sharp-s adjective/noun, case and collision cases. Different printed sharp-s and
ss spellings remain distinct. The unchanged independent source readings verify
the six real occurrences and their two printed purposes. The broad reference
and heading select no declaration. This is syntactic discovery reconciled with
existing conditional meanings; it derives no new legal meaning.

The fresh ordinary CLI preserves the complete088 baseline, and the isolated
offline-installed CLI matches the fresh answer in full. All original mutation
controls deliberately refuse.090 remains FAIL with its original evidence.

|Decision|Primary criterion|Veto status|Main uncertainty|Next justified action|Not concluded|
|---|---|---|---|---|---|
|Retain bounded spelling repair and source discovery|Original/added cases,exact source,mutations and complete consumers pass|No remaining source,baseline,refusal or import veto observed|Finite grammar and containment do not prove legal scope|Return to seven original source-gap classes and historical/onward law|General recall,legal applicability,entitlement or build closure|

The failure and repair concern our implementation, not a fundamental package
problem. The strongest alternative explanation is limited success inside a
finite grammar; the spelling/collision cases discriminate that grammar but cannot
establish general language coverage. A wrong quotation or accepted unsupported
meaning would overturn this bounded result. Cumulative costs and all original
obligations remain retained. External opinions are not a build prerequisite.
'''


if __name__ == '__main__':
    main()
