"""Bounded harness correction, exact baseline reuse, and original CLI trials."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import time

from scripts.prospectus_default_holder import ROOT, AUTH, read, save, sha, rel, digest, adigest, Authority
from scripts import prospectus_reference_consumption_repair as stages
from scripts.prospectus_reference_baseline_compare import FIELDS

PREP = AUTH / 'reviews/reference-validation-373'
HERE = AUTH / 'attempts/basf-references/attempt-106'
PRIOR = AUTH / 'attempts/basf-references/attempt-105'
OLD_PREP = AUTH / 'reviews/reference-consumption-repair-372'
BASE = AUTH / 'attempts/basf-office/attempt-006'
PLAN = 'docs/plans/prospectus-reference-validation-return-2026-10-20.md'
CHANGED_TEST = 'tests/prospectus_successor/test_consumed_reference_closure.py'
FILES = [PLAN, 'scripts/prospectus_reference_validation.py',
         'scripts/prospectus_reference_baseline_compare.py', CHANGED_TEST]


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    paths = list(PREP.glob('*-execution.json'))
    paths += list(HERE.glob('stages/*/result.json')) + list(HERE.glob('stages/*/failure.json'))
    measured = extra + sum(read(p).get('wall_seconds', 0) for p in paths)
    files = {p for d in (PREP, HERE) for p in d.rglob('*') if p.is_file()
             and '__pycache__' not in p.parts and 'installed' not in p.relative_to(d).parts}
    files.update(ROOT / name for name in FILES); files.add(AUTH / 'revisions/0373.json')
    files.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in files if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    total, combined = start['prior_seconds'] + measured + 180, start['prior_bytes'] + size
    assert measured < 1200 and size < 92 * 1024**2, 'Validation increment exhausted'
    assert total < 31000 and combined < 4540 * 1024**2, 'Cumulative limit exhausted'
    return {'combined_accounted_seconds': total, 'combined_bytes': combined,
        'new_measured_seconds': measured, 'new_conservative_other_seconds': 180,
        'new_bytes': size, 'historical_manual_seconds': 'UNKNOWN', 'old_costs_reset': False}


def prepare():
    began = time.monotonic(); program = read(AUTH / 'program.json')
    assert program['revision'] == 372 and not HERE.exists() and not PREP.exists()
    events = Authority(ROOT).events()
    assert any(e['kind'] in ('RECORD', 'REJECT') and e.get('attempt') == rel(PRIOR) for e in events)
    previous = stages.costs()
    assert previous['combined_accounted_seconds'] + 1380 < 31000
    assert previous['combined_bytes'] + 96 * 1024**2 < 4544 * 1024**2
    for folder in (PRIOR, BASE):
        for name, checksum in read(folder / 'outputs.json').items(): assert sha(folder / name) == checksum, name
    old = read(OLD_PREP / 'freeze.json')
    for name, checksum in old['bindings'].items():
        if name != CHANGED_TEST: assert sha(ROOT / name) == checksum, name
    save(PREP / 'accounting-start.json', {'prior_seconds': previous['combined_accounted_seconds'],
        'prior_bytes': previous['combined_bytes'], 'prior_resources': previous,
        'program_bytes': (AUTH / 'program.json').stat().st_size,
        'history_names': [p.name for p in (AUTH / 'history').glob('*.json')]})
    config = read(OLD_PREP / 'config.json'); baseline = read(BASE / 'ordinary-answer.json.gz')
    assert baseline == read(BASE / 'installed-answer.json.gz')
    assert read(BASE / 'installed-verification.json')['complete_installed_equal'] is True
    manifest = read(ROOT / config['products'])
    for row in manifest['products'].values(): assert sha(ROOT / row['path']) == row['sha256']
    products = {k: read(ROOT / row['path']) for k, row in manifest['products'].items()}
    assert baseline['consumed_products'] == {k: p['sha256'] for k, p in products.items()}
    assert baseline['request_sha256'] == digest(products['P1']['payload']['request'])
    assert baseline['source_graph_sha256'] == digest(products['P1']['payload']['graph'])
    baseline_files = read(BASE / 'package.json')['files']
    frozen103 = read(AUTH / 'reviews/election-consumer-370/freeze.json')['production']
    source_names = ['reviewed_references', 'structural_roles', 'occurrences', 'anchors', 'contracts']
    source_names += ['basf_' + name + '_references' for name in FIELDS]
    method_binding = {}
    for name in source_names:
        path = 'prospectus/successor/' + name + '.py'
        assert baseline_files[path] == frozen103['src/legalmath/' + path]
        method_binding[path] = baseline_files[path]
    service_source = (OLD_PREP / 'before/service.py').read_text()
    for name, field in FIELDS.items():
        variable = name + '_references'
        assert "result['" + field + "'] = " + variable in service_source
    save(PREP / 'baseline-binding.json', {'status': 'PASS', 'baseline_digest': digest(baseline),
        'complete_installed_equal': True, 'consumed_products': baseline['consumed_products'],
        'methods_equal_to_frozen103': method_binding, 'field_mapping': FIELDS,
        'production_unchanged_from105': True, 'failed105_preserved': True})
    save(PREP / 'config.json', config)
    for name in ('profile.json', 'expected.json'): shutil.copyfile(OLD_PREP / name, PREP / name)
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 105
    bindings = dict(old['bindings']); bindings.update({name: sha(ROOT / name) for name in FILES})
    bindings.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file()})
    bindings.update({rel(PRIOR / name): sha(PRIOR / name) for name in ('outputs.json', 'result.json', 'RESULT.md', 'package.json')})
    save(PREP / 'freeze.json', {'bindings': bindings, 'production': old['production']})
    new = deepcopy(program); new['revision'] = 373
    task = next(t for t in new['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=PLAN,
        reason='Correct retained validation-harness failures; compare exact complete baseline and finish election consumers',
        reference_validation_return={'review': rel(PREP), 'prior_attempt': rel(PRIOR),
            'new_measured_seconds': 1200, 'new_other_seconds': 180, 'new_bytes': 96 * 1024**2,
            'cumulative_seconds': 31000, 'cumulative_bytes': 4544 * 1024**2}, build_criteria_scope=[])
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [rel(PREP / 'freeze.json')]))
    new['budgets']['basf-references']['maximum_new_attempts'] = 106
    routes = read(ROOT / program['continuation_review']['routes']); routes['baseline_revision'] = 373
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                next_action='Validate fresh complete reference reports against exact office006 baseline; correct stale assertions; run original election CLI checks',
                stop_condition='106 admissions;1200+180seconds/96MiB new;31000seconds/4544MiB cumulative;one run per formal stage')
    save(PREP / 'routes.json', routes)
    new['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    new['continuation_review']['bindings'].update({name: sha(ROOT / name)
        for name in (PLAN, rel(PREP / 'routes.json'), rel(PREP / 'freeze.json'))})
    review = {'baseline': adigest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Correct stale validation assertions without changing production',
            'Use exact verified complete report baseline instead of rerunning timed-out old comparator',
            'Reuse byte-identical105 package, then finish original ordinary/installed trials'],
        'skeptical_audit': {'verdict': 'PASS', 'review': PLAN, 'baseline_binding': rel(PREP / 'baseline-binding.json')},
        'evidence_contract': {'primary': 'Complete source-bound report and answer equality with corruption refusals',
            'promotion_veto': ['Incorrect comparison', 'Missing output', 'Wrong imports', 'Package drift', 'Timeout'],
            'continuation_veto': ['Corrupt shared evidence', 'Invalid authority', 'Exhausted retained bounds'],
            'explanatory_only': ['Runtime', 'Test and admission counts'],
            'not_concluded': ['Legal truth from baseline', 'Package defect', 'Whole build', 'Historical applicability']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 105, 'new_maximum': 106,
            'retained_attempts': attempts, 'reason': 'Retained105 demonstrates stale assertions and incomplete comparator; production unchanged',
            'next_discriminating_check': 'Exact archived baseline comparison and original full CLI trials',
            'stop_condition': '1200+180seconds/96MiB increment;unchanged31000seconds/4544MiB cumulative;one run per stage',
            'same_scope_authorization': 'Continue authorized local general build without external calls or branch actions',
            'all_prior_costs_retained': True, 'cumulative_limits_unchanged': True}}
    save(PREP / 'proposal.json', new); save(PREP / 'review.json', review)
    save(PREP / 'preparation-execution.json', {'status': 'PASS', 'wall_seconds': time.monotonic() - began})
    return {'status': 'PASS', 'revision': 373, 'resources': costs()}


def compare():
    stages.harness.execute('compare', [str(ROOT / '.venv/bin/python'), '-B',
        str(ROOT / 'scripts/prospectus_reference_baseline_compare.py'), str(ROOT), str(PREP), str(HERE)], 120)
    return {'status': 'PASS', **read(HERE / 'comparison.json')}


def package():
    expected = {str(Path(name).relative_to('src/legalmath')): checksum
                for name, checksum in read(PREP / 'freeze.json')['production'].items()}
    source = PRIOR / 'installed/legalmath'
    assert {str(p.relative_to(source)): sha(p) for p in source.rglob('*') if p.is_file()} == expected
    prior = read(PRIOR / 'package.json'); assert prior['files'] == expected
    wheels = list((PRIOR / 'wheel').glob('*.whl')); assert len(wheels) == 1 and sha(wheels[0]) == prior['wheel_sha256']
    (HERE / 'installed').symlink_to((PRIOR / 'installed').resolve(), target_is_directory=True)
    save(HERE / 'package.json', {**prior, 'reused_from': rel(PRIOR), 'source_verified_exact': True})
    return {'status': 'PASS', 'source_matched_files': len(expected), 'install_reused': True}


def main():
    if sys.argv[1] == 'prepare': return prepare()
    # Reuse only the immutable runner's stage mechanics, with process-local paths.
    stages.PREP, stages.HERE, stages.PLAN = PREP, HERE, PLAN
    stages.harness.PREP, stages.harness.HERE = PREP, HERE
    stages.costs, stages.compare, stages.package = costs, compare, package
    stages.LIMITS = {**stages.LIMITS, 'compare': 120, 'package': 10}
    return stages.main()


if __name__ == '__main__': print(json.dumps(main()))
