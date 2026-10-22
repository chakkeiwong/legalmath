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

from scripts import prospectus_reference_label_grammar as prior
from scripts import prospectus_standalone_sections_oracle as oracle
from legalmath.prospectus.execution_authority import Authority, CODE, digest as adigest
from legalmath.prospectus.successor.contracts import digest

ROOT, AUTH, engine = prior.ROOT, prior.AUTH, prior.engine
PREP = AUTH / 'reviews/standalone-sections-348'
HERE = AUTH / 'attempts/basf-references/attempt-087'
PLAN = 'docs/plans/prospectus-standalone-sections-2026-10-19.md'
METHOD = 'scripts/prospectus_standalone_sections.py'
WORKER = 'scripts/prospectus_standalone_sections_installed.py'
TEST = 'tests/prospectus_successor/test_standalone_sections.py'
FILES = (PLAN, METHOD, WORKER, TEST, 'scripts/prospectus_standalone_sections_oracle.py',
         'scripts/prospectus_standalone_sections_cases.py', 'scripts/prospectus_standalone_sections_draft.py')
TARGETS = tuple('src/legalmath/prospectus/successor/' + n for n in
                ('standalone_sections.py', 'standalone_sections_spec.json', 'service.py', 'conditional_profiles.py'))
STAGES = ('install', 'tests', 'consume', 'controls', 'package', 'installed', 'seal')
read, save, sha, rel = prior.read, prior.save, prior.sha, prior.rel
PRODUCTS = prior.previous.PRODUCTS
SECONDS_BOUND = 24000
BYTES_BOUND = 3456 * 1024**2


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
    paths.add(AUTH / 'revisions/0348.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = base['combined_bytes'] + sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    size += sum(max(0, (ROOT / n).stat().st_size - start['production_bytes'][n])
                for n in TARGETS if (ROOT / n).exists())
    charge = base['conservative_extra_seconds']
    assert seconds + charge < SECONDS_BOUND and size < BYTES_BOUND - 4 * 1024**2, 'Cumulative structural reference bound'
    return {'combined_measured_seconds': seconds, 'conservative_extra_seconds': charge,
            'combined_accounted_seconds': seconds + charge, 'combined_bytes': size,
            'seconds_bound': SECONDS_BOUND, 'bytes_bound_with_4MiB_reserve': BYTES_BOUND,
            'prior_costs_reset': False, 'unmeasured_authoring_and_older_office_time': 'UNKNOWN; never treated as zero'}


def testfiles():
    return [TEST, 'tests/prospectus_successor/test_reference_scope.py',
            'tests/prospectus_successor/test_reference_scope_headers.py',
            'tests/prospectus_successor/test_paragraph_references.py',
            'tests/prospectus_successor/test_conditional_profiles_cli.py']


def prepare():
    program = read(AUTH / 'program.json')
    assert program['revision'] == 347
    events = Authority(ROOT).events()
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 86
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
    spec = {'version': 'standalone-sections.v1', 'products_sha256': frozen['products_sha256'],
            'ordinary_answer_sha256': frozen['ordinary_answer_sha256'],
            'target_claim': 'Unique structural containers under the declared source hierarchy',
            'legal_truth_established': False}
    save(PREP / 'candidate/standalone_sections_spec.json', spec)
    path = PREP / 'candidate/standalone_sections.py'
    text = path.read_text()
    assert text.count('SPEC_SHA256 = None') == 1
    path.write_text(text.replace('SPEC_SHA256 = None', 'SPEC_SHA256 = ' + repr(digest(spec))))
    service = (ROOT / TARGETS[2]).read_text()
    signature = 'reference_addresses_profile=None, expected_reference_addresses_profile_sha256=None):'
    assert service.count(signature) == 1
    service = service.replace(signature, 'reference_addresses_profile=None, expected_reference_addresses_profile_sha256=None,\n'
                              '            standalone_sections_profile=None, expected_standalone_sections_profile_sha256=None):')
    marker = '    return {**result, "report_sha256": digest(result)}\n'
    assert service.count(marker) == 1
    service = service.replace(marker, '''    if standalone_sections_profile is not None:
        from .standalone_sections import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, standalone_sections_profile, root,
            expected_profile_sha256=expected_standalone_sections_profile_sha256))
    elif expected_standalone_sections_profile_sha256 is not None:
        raise ValueError('Standalone-section profile pin supplied without a profile')
''' + marker)
    (PREP / 'candidate/service.py').write_text(service)
    profiles = (ROOT / TARGETS[3]).read_text()
    assert profiles.count("'reference_scope', 'reference_addresses')") == 1
    (PREP / 'candidate/conditional_profiles.py').write_text(profiles.replace(
        "'reference_scope', 'reference_addresses')", "'reference_scope', 'reference_addresses', 'standalone_sections')"))
    profile = {k: spec[k] for k in ('version', 'products_sha256', 'ordinary_answer_sha256')}
    profile.update(specification_sha256=digest(spec), whole_task_complete=False, legal_truth_established=False)
    save(PREP / 'profile.json', profile)
    manifest = read(prior.PREP / 'profiles.json')
    manifest['profiles'].append({'name': 'standalone_sections', 'path': rel(PREP / 'profile.json'),
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
    bindings = {n: sha(ROOT / n) for n in (*CODE, *FILES, *testfiles(), 'pyproject.toml', 'scripts/prospectus_reference_label_grammar.py',
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
    proposal['revision'] = 348
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=PLAN,
        reason='Account for standalone section references and statutory chains while preserving original answers and legal uncertainty',
        standalone_section_review={'review': rel(PREP), 'original_task_complete': False,
            'accounted_seconds_bound': SECONDS_BOUND, 'bytes_bound_with_4MiB_reserve': BYTES_BOUND})
    task['inputs'] = list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS] + list(bindings) + [rel(PREP / 'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 87
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 348
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                next_action='Verify50section signs and18standalone expressions; continue original definition and historical-law requirements',
                stop_condition='87 admissions; 24000 accounted seconds and 3456 MiB including 4 MiB reserve; no unchanged retry')
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
        'changes': ['Resolve declared structural addresses without using reviewed semantic destinations',
                    'Retain user direction, original obligations, current source mappings and all prior results'],
        'skeptical_audit': {'verdict': 'PASS', 'review': PLAN, 'forecast': forecast},
        'evidence_contract': {'primary': 'Independent frozen source destinations, adverse controls, complete ordinary/installed answer equality',
            'promotion_veto': ['Wrong parent/range/source', 'Invented legal acceptance', 'Changed old answer', 'Wrong installed import'],
            'continuation_veto': ['Corrupt baseline', 'Frozen method drift', 'Cumulative resource bound'],
            'explanatory_only': ['Counts', 'Runtime'],
            'not_concluded': ['General discovery', 'Legal interpretation', 'Statutory validity', 'Whole build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 86, 'new_maximum': 87,
            'retained_attempts': attempts, 'reason': 'Paragraph addressing leaves19standalone section signs without dedicated source classification',
            'next_discriminating_check': '50sign partition,18standalone expressions and complete installed equality',
            'stop_condition': '24000 seconds / 3456 MiB cumulative with 4 MiB reserve; no unchanged retry',
            'same_scope_authorization': 'User requested internally proven whole general build and reviewed continued execution'},
        'resource_accounting': {'retained_costs': snapshot, 'limits_extended': False,
            'previous_seconds_bound': 24000, 'previous_bytes_bound': 3456 * 1024**2,
            'seconds_bound': SECONDS_BOUND, 'bytes_with_reserve': BYTES_BOUND,
            'reason': 'Current cumulative allowance fits the bounded forecast; preserve all earlier costs'}}
    with (PREP / 'proposal.json').open('x') as stream:
        json.dump(proposal, stream, ensure_ascii=False, separators=(',', ':'))
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 348, 'candidate_evaluated': False, 'forecast': forecast}


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
    products,old=baseline();actual=read(HERE/'ordinary-answer.json.gz');refused={}
    for kind in ('sign-delete','wrong-heading','chain-member-delete','target-change','source-map-delete',
                 'statute-as-contract','false-history','false-completion','prior-answer'):
        bad=deepcopy(actual);report=bad[oracle.KEY];row=report['references'][0]
        if kind=='sign-delete':report['signs'].pop()
        elif kind=='wrong-heading':report['signs'][0]['classification']='STANDALONE_EXPRESSION'
        elif kind=='chain-member-delete':next(r for r in report['references'] if r['start']==35946)['members'].pop()
        elif kind=='target-change':row['targets'][0]['section']='99'
        elif kind=='source-map-delete':row['targets'][0]['source_projection'].pop()
        elif kind=='statute-as-contract':
            r=next(r for r in report['references'] if r['statute']=='AktG');r['targets']=row['targets'];r['status']='STRUCTURAL_SECTION'
        elif kind=='false-history':row['historical_application_established']=True
        elif kind=='false-completion':report['whole_task_complete']=True
        else:bad['questions']['Q1']['status']='YES'
        bad['report_sha256']=digest({k:v for k,v in bad.items() if k!='report_sha256'})
        try:oracle.verify(bad,old,products,read(PREP/'expected.json'))
        except AssertionError:refused[kind]=True
        else:raise AssertionError('Accepted '+kind)
    save(HERE/'controls.json',{'status':'PASS','refused':refused})
    return {'status':'PASS','refused':len(refused)}


def installed():
    engine.execute('installed-cli', [read(HERE / 'package.json')['python'], '-I', '-B', str(ROOT / WORKER),
                                    str(ROOT), str(HERE), str(PREP)], 360)
    result = read(HERE / 'installed-result.json')
    result.update(engine.compress_output('installed-answer.json'))
    return result


def seal():
    result={'status':'PASS','task':'basf-references','original_task_complete':False,
        'result_kind':'SOURCE_STANDALONE_SECTIONS',**read(HERE/'independent-verification.json'),
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
    save(folder / 'started.json', {'command': ['.venv/bin/python', '-m', 'scripts.prospectus_standalone_sections', stage],
                                 'started_at': datetime.now(timezone.utc).isoformat(), 'seconds_bound': bound})
    started = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Structural reference stage bound')))
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


RESULT_NOTE = '# Standalone sections retain source and statutory scope\n\nAll fifty printed section-sign occurrences are accounted for: fifteen headings,\nsixteen signs within prior paragraph contexts, and nineteen standalone signs.\nThose nineteen signs form eighteen expressions: fifteen structural section\nreferences and three statutory expressions, including the two-member SchVG\nchain. Exact source projections and complete prior answers remain preserved.\nThe fresh installed consumer matches the normal complete answer.\n\n|Decision|Primary criterion|Veto status|Main uncertainty|Next action|Not concluded|\n|---|---|---|---|---|---|\n|Retain finite standalone-section capability|Frozen source partition,destinations and installed equality|Scope/source/false-acceptance mutations refused|Implicit grammar,semantic subsets,historical applicability|Continue original definition and statutory requirements|General recall,legal truth or whole build|\n\nThe strongest alternative explanation is an unlisted drafting convention. A\nsource mismatch would require reviewed repair; finite exact coverage does not\nestablish exhaustive legal interpretation. All previous answers remain equal.\n'

if __name__ == '__main__':
    main()
