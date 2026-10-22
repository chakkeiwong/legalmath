"""Review/freeze continuation279 without resetting original scope or costs."""
from copy import deepcopy

from scripts.prospectus_internal_references import ROOT, AUTH, DONOR, PREP, SPEC, PLAN, TESTS, costs
from scripts.prospectus_margin_preparation import read, save, sha, relative


def propose():
    from legalmath.prospectus.execution_authority import Authority, CODE, digest as authority_digest
    program = read(AUTH / 'program.json')
    assert program['revision'] == 278
    assert not (PREP / 'freeze.json').exists(), 'Do not overwrite a frozen review'
    assert read(PREP / 'preflight-source-v4-result.json')['status'] == 'PASS'
    assert read(PREP / 'preflight-tests-v3-result.json')['status'] == 'PASS'
    assert read(PREP / 'generic-truncation.json')['actual_generic_admission_accepted']
    assert read(PREP / 'accepted-roots.json')['status'] == 'ACCEPTED_INCONSISTENT_CLOSURE'
    assert read(PREP / 'preparation-failure.json')['type'] == 'TimeoutError'
    assert read(PREP / 'source-review.json') == read(SPEC)
    inputs = {relative(f): sha(f) for f in sorted(PREP.rglob('*'))
              if f.is_file() and '__pycache__' not in f.parts}
    spec = read(PREP / 'source-review.json')
    inputs.update(spec['images'])
    inputs.update({s['path']: s['sha256'] for s in spec['sources']})
    for folder, names in (
        (DONOR, ('outputs.json', 'installed-construct/products.json.gz', 'installed-interpret/semantic.json.gz',
                 'installed-complete/downstream-products.json.gz', 'installed-answer/ordinary-answer.json.gz')),
        (AUTH / 'attempts/basf-references/attempt-019',
         ('outputs.json', 'candidate-answer.json.gz', 'result.json', 'candidate-answer-reconciliation.json.gz'))):
        manifest = read(folder / 'outputs.json')
        for name in names:
            f = folder / name
            if name != 'outputs.json':
                assert sha(f) == manifest[name]
            inputs[relative(f)] = sha(f)
    for name, checksum in inputs.items():
        assert sha(ROOT / name) == checksum
    methods = {relative(f): sha(f) for f in sorted((ROOT / 'src/legalmath/prospectus').rglob('*'))
               if f.suffix in ('.py', '.json')}
    prior = read(AUTH / 'reviews/financial-references-278/freeze.json')
    for name in (*prior['methods'], *CODE, PLAN,
                 'scripts/prospectus_internal_revision.py',
                 'scripts/prospectus_internal_references.py',
                 'scripts/prospectus_internal_reference_preparation.py',
                 'scripts/prospectus_internal_reference_oracle.py', *TESTS):
        methods[name] = sha(ROOT / name)
    attempts = [e['attempt'] for e in Authority(ROOT).events()
                if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 19
    assert len(program['obligations']) == 59 and len(program['tasks']) == 44
    resources = costs()
    save(PREP / 'freeze.json', {'methods': methods, 'inputs': inputs})
    proposal = deepcopy(program)
    proposal['revision'] = 279
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, timeout_seconds=180, build_criteria_scope=[],
        reason='Ten original internal findings require complete selected targets; actual consumer accepted a resealed closure-root mutation before repair',
        internal_reference_review={'version': 'basf-internal-references.v1', 'review': relative(PREP),
            'original_task_complete': False,
            'bounds': {'stage_seconds': 180, 'new_seconds': 1800, 'new_bytes': 192 * 1024**2},
            'further_harness_retry_allowed': False},
        pre_admission_review=relative(PREP / 'PRE-ADMISSION-REVIEW.md'))
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(methods) + list(inputs) + [relative(PREP / 'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 20
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 279
    for row in routes['tasks']:
        if row['task'] == task['id']:
            row.update(dossier=PLAN, task_sha256=authority_digest(task),
                remaining='019 retains37reviewed links; ten original internal scopes and ordinary consumed closure remain unchecked after repair.',
                next_action='Verify complete internal original targets and reconstructed closure through full candidate/omission answers and actual resealed-consumer controls; then continue statutory and defined-term remainder.',
                acceptance='Independent original intervals and full ordinary answers; actual upstream/consumer refusals; all60original records retained; partial evidence only.',
                stop_condition='Twenty cumulative admissions;180s stages;1800s newly measured including all preparation/preflights;192MiB with4MiB reserve;no unchanged/harness retry.')
    save(PREP / 'routes.json', routes)
    proposal['continuation_review'].update(plan=PLAN, routes=relative(PREP / 'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN),
        relative(PREP / 'routes.json'): sha(PREP / 'routes.json'),
        relative(PREP / 'freeze.json'): sha(PREP / 'freeze.json')})
    review = {'baseline': authority_digest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'original_obligations_preserved': True,
        'changes': ['Ten original complete internal source scopes',
                    'Actual ordinary consumer reconstruction of complete dependencies and reference closure',
                    'Preserved source cycles, UNKNOWN roles and whole-answer uncertainty',
                    'Separate adverse controls and all60record reconciliation'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN,
            'source_review': relative(PREP / 'PRE-ADMISSION-REVIEW.md'),
            'reproduced': relative(PREP / 'accepted-roots.json'),
            'failed_preparation_retained': relative(PREP / 'preparation-failure.json'),
            'source_preflight': relative(PREP / 'preflight-source-v4-result.json'),
            'test_preflight': relative(PREP / 'preflight-tests-v3-result.json'),
            'statutory_interpretation_remains_unresolved': True, 'whole_task_acceptance_claimed': False},
        'evidence_contract': {'primary': 'Independent original intervals, complete dependency/closure reconstruction, full ordinary answers and original inventory',
            'veto': ['Truncated or wrong-issuer target', 'Changed source/scalar authority',
                     'Lost discovery or prior link', 'Concealed source cycle or uncertainty',
                     'Changed unrelated meaning', 'Method drift', 'Resource/harness invalidity'],
            'not_concluded': ['Statutory applicability', 'Actual tax/event entitlement',
                             'Generic automatic discovery', 'Universal legal correctness', 'Whole task/build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 19, 'new_maximum': 20,
            'retained_attempts': attempts,
            'reason': 'Ten distinct original unmapped internal findings plus actual accepted resealed closure mutation; all failed preparation/preflights retained, not repeated unchanged',
            'next_discriminating_check': 'Complete-source candidate/omission versus target, closure, dependency and answer-uncertainty mutations through actual consumers',
            'stop_condition': '180s stages;1800s measured including preparation/preflights;192MiB;no unchanged/harness retry',
            'same_scope_authorization': 'User directs general build and internally demonstrated conditional correctness; holdings/reader acceptance after build and no external opinion prerequisite'},
        'resources_before_admission': resources}
    save(PREP / 'proposal.json', proposal)
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 279, 'prior_admissions': 19, 'resources': costs()}
