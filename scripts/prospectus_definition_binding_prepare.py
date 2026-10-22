"""Freeze the binding profile and authority proposal before candidate execution."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import shutil
import time

from scripts import prospectus_definition_semantics as semantic
from scripts import prospectus_definition_binding_oracle as oracle
from legalmath.prospectus.execution_authority import Authority, CODE, digest as adigest

ROOT, AUTH = semantic.ROOT, semantic.AUTH
PREP = AUTH / 'reviews/definition-bindings-331'
PLAN = 'docs/plans/prospectus-definition-use-bindings-2026-10-19.md'
CASES = PREP / 'expected-content.json'
METHOD = 'scripts/prospectus_definition_binding.py'
MODULE = 'src/legalmath/prospectus/successor/definition_bindings.py'
TARGETS = (MODULE, 'src/legalmath/prospectus/successor/service.py',
           'src/legalmath/prospectus/successor/conditional_profiles.py')


def main():
    start = time.monotonic()
    freeze = semantic.read(PREP / 'cases-freeze.json')
    assert freeze['candidate_absent'] is True
    assert semantic.sha(PREP / 'expected-content.json') == freeze['expected_content_sha256']
    assert semantic.sha(ROOT / PLAN) == freeze['plan_sha256']
    products, ordinary, _, _, _ = semantic.baseline()
    content = semantic.read(CASES)
    profile = {
        'version': 'definition-use-bindings.v1',
        'products_sha256': oracle.digest(products),
        'ordinary_answer_sha256': oracle.digest(ordinary),
        'semantic_matrix_sha256': semantic.sha(semantic.HERE / 'coverage.json'),
        'expected_content_sha256': semantic.sha(CASES),
        'record_rules': {
            'D31-holder-redemption-day': 'holder',
            'D41-affiliate': 'affiliate',
            'D45-custodian': 'custodian',
            'U06-tax-early-amount': 'tax',
            'U07-makewhole-early-amount': 'makewhole',
        },
        'supplemental_occurrence': {'start': 21547, 'end': 21576,
                                    'quote': 'vorzeitige\nRückzahlungsbetrag'},
        'supplemental_records': ['U06-tax-early-amount', 'U07-makewhole-early-amount'],
        'legal_truth_established': False,
        'whole_task_complete': False,
    }
    semantic.save(PREP / 'profile.json', profile)
    manifest = semantic.read(AUTH / 'reviews/definition-roles-327/profiles.json')
    manifest['profiles'] = [row for row in manifest['profiles'] if row['name'] != 'definition_bindings']
    manifest['profiles'].append({'name': 'definition_bindings', 'path': semantic.rel(PREP / 'profile.json'),
        'file_sha256': semantic.sha(PREP / 'profile.json'), 'profile_sha256': oracle.digest(profile)})
    semantic.save(PREP / 'profiles.json', manifest)
    # Capture candidate files after the independent source matrix was frozen.
    candidate = PREP / 'candidate'
    candidate.mkdir(exist_ok=True)
    for target in TARGETS:
        path = ROOT / target
        shutil.copyfile(path, candidate / path.name)
    semantic.save(PREP / 'candidate-manifest.json', {
        'targets': [{'target': target, 'candidate': semantic.rel(candidate / (ROOT / target).name),
                     'candidate_sha256': semantic.sha(candidate / (ROOT / target).name),
                     'current_sha256': semantic.sha(ROOT / target)} for target in TARGETS],
        'candidate_created_after_cases': True,
    })
    program = semantic.read(AUTH / 'program.json')
    assert program['revision'] == 330
    events = Authority(ROOT).events()
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 69
    bindings = {n: semantic.sha(ROOT / n) for n in (*CODE, PLAN, semantic.METHOD, semantic.LINKS,
                                                      semantic.rel(semantic.HERE / 'outputs.json'),
                                                      semantic.rel(PREP / 'METHOD-REVIEW.md'),
                                                      semantic.rel(PREP / 'PREPARATION-REVIEW.md'),
                                                      semantic.rel(PREP / 'cases-freeze.json'),
                                                      semantic.rel(PREP / 'expected-content.json'),
                                                      semantic.rel(PREP / 'profile.json'),
                                                      semantic.rel(PREP / 'profiles.json'),
                                                      semantic.rel(PREP / 'candidate-manifest.json'),
                                                      semantic.rel(ROOT / MODULE), semantic.rel(ROOT / METHOD))}
    bindings.update({semantic.rel(p): semantic.sha(p) for p in candidate.glob('*')})
    # Bind all current package source files for the installed verification.
    bindings.update({semantic.rel(p): semantic.sha(p) for p in (ROOT / 'src/legalmath').rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'})
    semantic.save(PREP / 'freeze.json', {'bindings': bindings, 'candidate_evaluated': False,
                                          'cases_sha256': semantic.sha(CASES)})
    task = next(t for t in program['tasks'] if t['id'] == 'basf-references')
    proposal = deepcopy(program)
    proposal['revision'] = 331
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=semantic.rel(PREP / 'METHOD-REVIEW.md'),
        reason='Bind reviewed conditional definition rules to exact original uses and preserve all unresolved scope',
        definition_binding_repair={'review': semantic.rel(PREP), 'candidate': semantic.rel(PREP / 'candidate'),
            'original_task_complete': False, 'candidate_evaluated': False,
            'accounted_seconds_bound': 18000, 'bytes_bound_with_4MiB_reserve': 2688 * 1024**2})
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [semantic.rel(PREP / 'freeze.json'), semantic.rel(PREP / 'profiles.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 70
    routes = semantic.read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 331
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                next_action='Execute exact purpose-aware definition binding through ordinary and installed consumers, then register original-task acceptance validator',
                stop_condition='70admissions;900s package forecast;18000 accounted seconds/2688MiB with4MiB reserve;no unchanged retry')
    semantic.save(PREP / 'routes.json', routes)
    proposal['continuation_review'].update(plan=PLAN, routes=semantic.rel(PREP / 'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN: semantic.sha(ROOT / PLAN),
        semantic.rel(PREP / 'routes.json'): semantic.sha(PREP / 'routes.json'),
        semantic.rel(PREP / 'freeze.json'): semantic.sha(PREP / 'freeze.json')})
    review = {'baseline': adigest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Add exact purpose-aware bindings as an additive answer report',
                    'Retain all610original and2supplemental associations and all question uncertainty',
                    'Extend cumulative package bound to18000seconds/2688MiB with4MiB reserve'],
        'skeptical_audit': {'verdict': 'PASS', 'review': semantic.rel(PREP / 'METHOD-REVIEW.md'),
            'preparation_review': semantic.rel(PREP / 'PREPARATION-REVIEW.md'),
            'cases_frozen_before_candidate': True, 'forecast': {'seconds': 900, 'bytes': 160 * 1024**2, 'estimate_only': True}},
        'evidence_contract': {'primary': 'Independent whole-answer expected content, exact rule/source checks and fresh installed equality',
            'promotion_veto': ['Dropped or invented use', 'Wrong purpose rule', 'Changed original report', 'Wrong import', 'Installed mismatch'],
            'continuation_veto': ['Corrupt comparator', 'Frozen drift', 'Cumulative bound'],
            'explanatory_only': ['Counts', 'Runtime', 'Regression totals'],
            'not_concluded': ['Remaining582governing uses', 'General recall', 'Historical law', 'Actual events', 'Whole build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 69, 'new_maximum': 70,
            'retained_attempts': attempts, 'reason': '069 semantic reconciliation reproduced a specific purpose-aware binding gap requiring one installed consumer trial',
            'next_discriminating_check': 'Independent complete binding matrix and ordinary/installed equality',
            'stop_condition': '900s package forecast;18000accounted seconds/2688MiB with4MiB reserve;no unchanged retry',
            'same_scope_authorization': 'Continue internally established general build after user requested refreshed master program'},
        'resource_revision': {'prior_accounted_seconds': 16200, 'new_accounted_seconds': 18000,
            'prior_bytes': 2432 * 1024**2, 'new_bytes': 2688 * 1024**2,
            'reserve_bytes': 4 * 1024**2, 'prior_costs_retained': True}}
    semantic.save(PREP / 'proposal.json', proposal)
    semantic.save(PREP / 'review.json', review)
    semantic.save(PREP / 'preparation-result.json', {'status': 'PASS', 'revision': 331,
        'candidate_evaluated': False, 'records': 62, 'original_associations': 610,
        'supplemental_associations': 2, 'wall_seconds': time.monotonic() - start})
    print(json.dumps({'status': 'PASS', 'revision': 331, 'forecast_seconds': 900,
                      'forecast_bytes': 160 * 1024**2, 'candidate_evaluated': False}))


if __name__ == '__main__':
    main()
