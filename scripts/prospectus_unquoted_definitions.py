"""Reviewed structural reference continuation under the original authority."""
from copy import deepcopy
from datetime import datetime, timezone
import ast
import json
import os
import shutil
import signal
import sys
import time
import xml.etree.ElementTree as ET

from scripts import prospectus_standalone_sections as prior
from scripts import prospectus_unquoted_definitions_oracle as oracle
from legalmath.prospectus.execution_authority import Authority, CODE, digest as adigest
from legalmath.prospectus.successor.contracts import digest

ROOT, AUTH, engine = prior.ROOT, prior.AUTH, prior.engine
PREP = AUTH / 'reviews/unquoted-definitions-349'
HERE = AUTH / 'attempts/basf-references/attempt-088'
PLAN = 'docs/plans/prospectus-unquoted-definitions-2026-10-19.md'
METHOD = 'scripts/prospectus_unquoted_definitions.py'
WORKER = 'scripts/prospectus_unquoted_definitions_installed.py'
TEST = 'tests/prospectus_successor/test_unquoted_definitions.py'
FILES = (PLAN, METHOD, WORKER, TEST, 'scripts/prospectus_unquoted_definitions_oracle.py',
         'scripts/prospectus_unquoted_definitions_cases.py', 'scripts/prospectus_unquoted_definitions_draft.py', 'docs/implementation/prospectus-execution-authority/reviews/unquoted-definitions-349/METHOD-REVIEW.md')
TARGETS = tuple('src/legalmath/prospectus/successor/' + n for n in
                ('unquoted_definitions.py', 'unquoted_definitions_spec.json', 'service.py', 'conditional_profiles.py'))
STAGES = ('install', 'tests', 'consume', 'controls', 'package', 'installed', 'seal')
read, save, sha, rel = prior.read, prior.save, prior.sha, prior.rel
PRODUCTS = prior.PRODUCTS
SECONDS_BOUND = 24000
BYTES_BOUND = 3584 * 1024**2


def baseline():
    products = {k: read(ROOT / r['path']) for k, r in read(PRODUCTS)['products'].items()}
    answer = read(prior.HERE / 'ordinary-answer.json.gz')
    frozen = read(PREP / 'source-freeze.json')
    assert digest(products) == frozen['products_sha256']
    assert digest(answer) == frozen['ordinary_answer_sha256']
    return products, answer


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    base = start['prior']
    seconds = base['combined_measured_seconds'] + read(PREP / 'source-freeze.json')['wall_seconds'] + extra
    for folder in (PREP, HERE):
        for pattern in ('stages/*/result.json', 'stages/*/failure.json'):
            seconds += sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths = {p for folder in (PREP, HERE) for p in folder.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / n for n in FILES)
    paths.add(AUTH / 'revisions/0349.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = base['combined_bytes'] + sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    size += sum(max(0, (ROOT / n).stat().st_size - start['production_bytes'][n])
                for n in TARGETS if (ROOT / n).exists())
    charge = base['conservative_extra_seconds']
    assert seconds + charge < SECONDS_BOUND and size < BYTES_BOUND - 4 * 1024**2, 'Cumulative unquoted definition bound'
    return {'combined_measured_seconds': seconds, 'conservative_extra_seconds': charge,
            'combined_accounted_seconds': seconds + charge, 'combined_bytes': size,
            'seconds_bound': SECONDS_BOUND, 'bytes_bound_with_4MiB_reserve': BYTES_BOUND,
            'prior_costs_reset': False, 'unmeasured_authoring_and_older_office_time': 'UNKNOWN; never treated as zero'}


def testfiles():
    return [TEST, 'tests/prospectus_successor/test_standalone_sections.py',
            'tests/prospectus_successor/test_reference_scope.py',
            'tests/prospectus_successor/test_reference_scope_headers.py',
            'tests/prospectus_successor/test_paragraph_references.py',
            'tests/prospectus_successor/test_conditional_profiles_cli.py']


def prepare():
    program = read(AUTH / 'program.json')
    assert program['revision'] == 348
    events = Authority(ROOT).events()
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 87
    assert any(e['kind'] == 'RECORD' and e.get('attempt') == rel(prior.HERE) for e in events)
    for n, v in read(prior.HERE / 'outputs.json').items():
        assert sha(prior.HERE / n) == v, n
    for n, v in read(prior.PREP / 'freeze.json')['bindings'].items():
        assert sha(ROOT / n) == v, n
    for r in read(prior.PREP / 'installation.json'):
        assert sha(ROOT / r['target']) == r['after']
    frozen = read(PREP / 'source-freeze.json')
    assert frozen['candidate_absent'] is True
    assert sha(PREP / 'expected.json') == frozen['expected_sha256'] and sha(ROOT / PLAN) == frozen['plan_sha256']
    spec = {'version': 'unquoted-definitions.v1', 'products_sha256': frozen['products_sha256'],
            'ordinary_answer_sha256': frozen['ordinary_answer_sha256'],
            'target_claim': 'Exact syntactic unquoted naming events with printed restrictions; no legal meaning admission',
            'legal_truth_established': False}
    save(PREP / 'candidate/unquoted_definitions_spec.json', spec)
    path = PREP / 'candidate/unquoted_definitions.py'
    text = path.read_text()
    assert text.count('SPEC_SHA256 = None') == 1
    path.write_text(text.replace('SPEC_SHA256 = None', 'SPEC_SHA256 = ' + repr(digest(spec))))
    service = (ROOT / TARGETS[2]).read_text()
    signature = 'standalone_sections_profile=None, expected_standalone_sections_profile_sha256=None):'
    assert service.count(signature) == 1
    service = service.replace(signature, 'standalone_sections_profile=None, expected_standalone_sections_profile_sha256=None,\n'
                              '            unquoted_definitions_profile=None, expected_unquoted_definitions_profile_sha256=None):')
    marker = '    return {**result, "report_sha256": digest(result)}\n'
    assert service.count(marker) == 1
    block = """    if unquoted_definitions_profile is not None:
        from .unquoted_definitions import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, unquoted_definitions_profile, root,
            expected_profile_sha256=expected_unquoted_definitions_profile_sha256))
    elif expected_unquoted_definitions_profile_sha256 is not None:
        raise ValueError('Unquoted-definition profile pin supplied without a profile')
"""
    service = service.replace(marker, block + marker)
    (PREP / 'candidate/service.py').write_text(service)
    profiles = (ROOT / TARGETS[3]).read_text()
    old = "'reference_addresses', 'standalone_sections')"
    assert profiles.count(old) == 1
    (PREP / 'candidate/conditional_profiles.py').write_text(profiles.replace(
        old, "'reference_addresses', 'standalone_sections', 'unquoted_definitions')"))
    profile = {k: spec[k] for k in ('version', 'products_sha256', 'ordinary_answer_sha256')}
    profile.update(specification_sha256=digest(spec), whole_task_complete=False, legal_truth_established=False)
    save(PREP / 'profile.json', profile)
    manifest = read(prior.PREP / 'profiles.json')
    manifest['profiles'].append({'name': 'unquoted_definitions', 'path': rel(PREP / 'profile.json'),
        'file_sha256': sha(PREP / 'profile.json'), 'profile_sha256': digest(profile)})
    save(PREP / 'profiles.json', manifest)
    (PREP / 'baseline').mkdir()
    installation = []
    for target in TARGETS:
        path = ROOT / target
        candidate = PREP / 'candidate' / path.name
        if candidate.suffix == '.py':
            ast.parse(candidate.read_text())
        if path.exists():
            shutil.copyfile(path, PREP / 'baseline' / path.name)
        installation.append({'target': target, 'before': sha(path) if path.exists() else None,
                             'candidate': rel(candidate), 'after': sha(candidate)})
    save(PREP / 'installation.json', installation)
    bindings = {n: sha(ROOT / n) for n in (*CODE, *FILES, *testfiles(), 'pyproject.toml', 'scripts/prospectus_standalone_sections.py',
                                          'scripts/prospectus_residual_coverage.py')}
    bindings.update({rel(p): sha(p) for p in (ROOT / 'src/legalmath').rglob('*') if p.is_file()
                     and '__pycache__' not in p.parts and p.suffix != '.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for p in (prior.HERE / 'outputs.json', prior.HERE / 'ordinary-answer.json.gz', PRODUCTS):
        bindings[rel(p)] = sha(p)
    for r in read(PRODUCTS)['products'].values():
        bindings[r['path']] = r['sha256']
    for r in manifest['profiles']:
        bindings[r['path']] = r['file_sha256']
    save(PREP / 'freeze.json', {'bindings': bindings, 'candidate_evaluated': False})
    proposal = deepcopy(program)
    proposal['revision'] = 349
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=rel(PREP / 'METHOD-REVIEW.md'),
        reason='Discover explicit unquoted naming events from selected source text without supplied vocabulary; retain legal uncertainty',
        unquoted_definition_review={'review': rel(PREP), 'original_task_complete': False,
            'accounted_seconds_bound': SECONDS_BOUND, 'bytes_bound_with_4MiB_reserve': BYTES_BOUND})
    task['inputs'] = list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS] + list(bindings) + [rel(PREP / 'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 88
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 349
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                next_action='Verify seven exact naming/scope/value readings without vocabulary; continue original scope,implicit-reference and historical-law requirements',
                stop_condition='88 admissions; 24000 accounted seconds and 3584 MiB including 4 MiB reserve; no unchanged retry')
    save(PREP / 'routes.json', routes)
    proposal['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    for n in TARGETS:
        proposal['continuation_review']['bindings'].pop(n, None)
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN),
        rel(PREP / 'routes.json'): sha(PREP / 'routes.json'), rel(PREP / 'freeze.json'): sha(PREP / 'freeze.json')})
    snapshot = costs()
    forecast = {'seconds': snapshot['combined_accounted_seconds'] + 1000,
                'bytes': snapshot['combined_bytes'] + 96 * 1024**2, 'estimate_only': True}
    assert forecast['seconds'] < SECONDS_BOUND and forecast['bytes'] < BYTES_BOUND - 4 * 1024**2
    review = {'baseline': adigest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Discover source naming events without supplied terms and preserve separate printed restrictions',
                    'Retain user direction, original obligations, current source mappings and all prior results'],
        'skeptical_audit': {'verdict': 'PASS', 'review': rel(PREP / 'METHOD-REVIEW.md'), 'forecast': forecast},
        'evidence_contract': {'primary': 'Seven independent exact naming/scope/value intervals,unfamiliar-term controls,and complete ordinary/installed equality',
            'promotion_veto': ['Wrong naming/value/restriction/source', 'Invented legal acceptance', 'Changed old answer', 'Wrong installed import'],
            'continuation_veto': ['Corrupt baseline', 'Frozen method drift', 'Cumulative resource bound'],
            'explanatory_only': ['Counts', 'Runtime'],
            'not_concluded': ['General discovery', 'Legal interpretation', 'Statutory validity', 'Whole build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 87, 'new_maximum': 88,
            'retained_attempts': attempts, 'reason': 'Quoted discovery and supplied-vocabulary forms do not discover explicit unquoted naming events',
            'next_discriminating_check': 'Seven source naming events,separate amount restrictions,unfamiliar terms and complete installed equality',
            'stop_condition': '24000 seconds / 3584 MiB cumulative with 4 MiB reserve; no unchanged retry',
            'same_scope_authorization': 'User requested internally proven whole general build and reviewed continued execution'},
        'resource_accounting': {'retained_costs': snapshot, 'limits_extended': True,
            'previous_seconds_bound': 24000, 'previous_bytes_bound': 3456 * 1024**2,
            'seconds_bound': SECONDS_BOUND, 'bytes_with_reserve': BYTES_BOUND,
            'reason': 'Extend only storage3456to3584MiB for paired answers and package; retain24000seconds and all prior costs'}}
    with (PREP / 'proposal.json').open('x') as stream:
        json.dump(proposal, stream, ensure_ascii=False, separators=(',', ':'))
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 349, 'candidate_evaluated': False, 'forecast': forecast}


def install():
    for row in read(PREP / 'installation.json'):
        target = ROOT / row['target']
        assert (sha(target) if target.exists() else None) == row['before']
        shutil.copyfile(ROOT / row['candidate'], target)
    return {'status': 'PASS', 'production_files': len(TARGETS)}


def tests():
    engine.execute('pytest', [str(ROOT / '.venv/bin/python'), '-m', 'pytest',
        *[str(ROOT / n) for n in testfiles()], '-q', '--junitxml=' + str(HERE / 'pytest.xml')], 150)
    suites = list(ET.parse(HERE / 'pytest.xml').getroot().iter('testsuite'))
    counts = {k: sum(int(s.attrib.get(k, 0)) for s in suites) for k in ('tests', 'failures', 'errors', 'skipped')}
    assert counts['tests'] and not any(counts[k] for k in ('failures', 'errors', 'skipped'))
    return {'status': 'PASS', **counts}


def cli_arguments(output):
    return ['prospectus', 'consume', '--products', str(PRODUCTS), '--repository', str(ROOT),
            '--output', str(HERE / output), '--mode', 'frozen', '--conditional-profiles', rel(PREP / 'profiles.json'),
            '--conditional-profiles-sha256', sha(PREP / 'profiles.json')]


def consume():
    engine.execute('ordinary-cli', [str(ROOT / '.venv/bin/python'), '-m', 'legalmath.cli',
                                   *cli_arguments('ordinary-answer.json')], 360)
    products, old = baseline()
    actual = read(HERE / 'ordinary-answer.json')
    result = oracle.verify(actual, old, products, read(PREP / 'expected.json'))
    save(HERE / 'independent-verification.json', result)
    return {**result, 'actual_cli': True, 'answer_sha256': digest(actual), **engine.compress_output('ordinary-answer.json')}


def controls():
    products, old = baseline()
    actual = read(HERE / 'ordinary-answer.json.gz')
    refused = {}
    for kind in ('delete-name', 'wrong-term', 'swap-scopes', 'drop-scope', 'drop-condition',
                 'wrong-value', 'source-map-delete', 'invent-missing', 'false-meaning',
                 'false-completion', 'source-identity', 'prior-answer'):
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
        else: bad['questions']['Q1']['status'] = 'YES'
        bad['report_sha256'] = digest({k: v for k, v in bad.items() if k != 'report_sha256'})
        try: oracle.verify(bad, old, products, read(PREP / 'expected.json'))
        except AssertionError: refused[kind] = True
        else: raise AssertionError('Accepted ' + kind)
    save(HERE / 'controls.json', {'status': 'PASS', 'refused': refused})
    return {'status': 'PASS', 'refused': len(refused)}


def installed():
    engine.execute('installed-cli', [read(HERE / 'package.json')['python'], '-I', '-B', str(ROOT / WORKER),
                                    str(ROOT), str(HERE), str(PREP)], 360)
    result = read(HERE / 'installed-result.json')
    result.update(engine.compress_output('installed-answer.json'))
    return result


def seal():
    result={'status':'PASS','task':'basf-references','original_task_complete':False,
        'result_kind':'SOURCE_UNQUOTED_DEFINITIONS',**read(HERE/'independent-verification.json'),
        'ordinary_installed_equal':True,'resources':costs(),
        'next_action':'Continue original definition discovery,implicit-reference review and historical-law scope'}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU;GPU intentionally hidden',
        'seeds':'N/A deterministic','data_version':sha(PRODUCTS),'wall_time':costs(),
        'plan':PLAN,'result':rel(HERE/'result.json')})
    (HERE/'RESULT.md').write_text(RESULT_NOTE)
    return result


def main():
    stage = sys.argv[1]
    assert stage == 'prepare' or stage in STAGES
    folder = (PREP if stage == 'prepare' else HERE) / 'stages' / stage
    assert not (folder / 'started.json').exists(), 'Unchanged retry refused'
    if stage == 'prepare':
        save(PREP / 'accounting-start.json', {'prior': prior.costs(),
            'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
            'program_bytes': (AUTH / 'program.json').stat().st_size,
            'production_bytes': {n: (ROOT / n).stat().st_size if (ROOT / n).exists() else 0 for n in TARGETS}})
    else:
        for preceding in STAGES[:STAGES.index(stage)]:
            assert read(HERE / 'stages' / preceding / 'result.json')['status'] == 'PASS'
        costs()
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    engine.PREP, engine.HERE, engine.PLAN, engine.METHOD, engine.WORKER, engine.TARGETS = PREP, HERE, PLAN, METHOD, WORKER, TARGETS
    engine.costs, engine.testfiles, engine.cli_arguments = costs, testfiles, cli_arguments
    bound = 90 if stage == 'prepare' else 420
    save(folder / 'started.json', {'command': ['.venv/bin/python', '-m', 'scripts.prospectus_unquoted_definitions', stage],
                                 'started_at': datetime.now(timezone.utc).isoformat(), 'seconds_bound': bound})
    started = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Unquoted definition stage bound')))
    signal.alarm(bound)
    try:
        if stage != 'prepare': engine.frozen(stage != 'install')
        result = (globals().get(stage) or getattr(engine, stage))()
        if stage != 'prepare': engine.frozen()
        costs(time.monotonic() - started)
        result['wall_seconds'] = time.monotonic() - started
        save(folder / 'result.json', result)
        if stage == 'seal': save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as error:
        save(folder / 'failure.json', {'type': type(error).__name__, 'message': str(error), 'wall_seconds': time.monotonic() - started})
        raise
    finally:
        signal.alarm(0)


RESULT_NOTE = '# Source naming events preserve printed restrictions\n\nSeven explicit unquoted naming events are discovered from selected source text\nwithout a supplied vocabulary or reviewed record IDs. Exact expression, term,\nscope, value and applicability spans agree with the independent source freeze.\nThe two early-redemption amounts remain distinct despite identical names.\nNo definition for Zinsperiode is invented. All pre-existing answer fields remain\nequal, and the fresh installed consumer matches the complete ordinary answer.\n\n|Decision|Primary criterion|Veto status|Main uncertainty|Next action|Not concluded|\n|---|---|---|---|---|---|\n|Retain finite unquoted syntax support|Exact independent spans,unfamiliar terms,complete installed equality|Naming,scope,value,condition,provenance and false-acceptance mutations refused|Unlisted grammar and governing use scope|Continue original reference/definition/statutory requirements|General recall,legal meaning,whole build|\n\nThe strongest alternative explanation is an unlisted naming convention or an\nincorrect independently read span. A source mismatch would require reviewed\nrepair. Success on seven events does not establish exhaustive legal analysis;\nthe original task remains incomplete. No PDF/OCR package conclusion follows.\n'

if __name__ == '__main__':
    main()
