"""Review and freeze continuation278, preserving all original obligations."""
from copy import deepcopy
from scripts.prospectus_financial_references import ROOT, AUTH, DONOR, PREP, SPEC, PLAN, TESTS, costs
from scripts.prospectus_margin_preparation import read, save, sha, relative


def propose():
    from legalmath.prospectus.execution_authority import Authority, CODE, digest as authority_digest
    program = read(AUTH / 'program.json')
    assert program['revision'] == 277
    assert read(PREP / 'preflight-result.json')['status'] == 'PASS'
    inputs = {relative(f): sha(f) for f in sorted(PREP.rglob('*'))
              if f.is_file() and '__pycache__' not in f.parts}
    spec = read(PREP / 'source-review.json')
    inputs.update(spec['images'])
    inputs.update({s['path']: s['sha256'] for s in spec['sources']})
    for folder, names in (
        (DONOR, ('outputs.json', 'installed-construct/products.json.gz', 'installed-interpret/semantic.json.gz',
                 'installed-complete/downstream-products.json.gz', 'installed-answer/ordinary-answer.json.gz')),
        (AUTH / 'attempts/basf-references/attempt-018',
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
    for name in (*CODE, PLAN, 'scripts/prospectus_financial_revision.py',
        'scripts/prospectus_financial_references.py', 'scripts/prospectus_financial_reference_preparation.py',
        'scripts/prospectus_financial_reference_oracle.py', 'scripts/prospectus_substitution_references.py',
        'scripts/prospectus_substitution_reference_preparation.py', 'scripts/prospectus_default_references.py',
        'scripts/prospectus_default_reference_preparation.py', 'scripts/prospectus_governance_references.py',
        'scripts/prospectus_governance_reference_preparation.py', 'scripts/prospectus_reference_integrity.py',
        'scripts/prospectus_reference_integrity_preparation.py', 'scripts/prospectus_reference_integrity_oracle.py',
        'scripts/prospectus_payment_references.py', 'scripts/prospectus_payment_reference_preparation.py',
        'scripts/prospectus_relative_notices.py', 'scripts/prospectus_margin_preparation.py',
        'scripts/prospectus_typed_delta.py', *TESTS):
        methods[name] = sha(ROOT / name)
    save(PREP / 'freeze.json', {'methods': methods, 'inputs': inputs})
    attempts = [e['attempt'] for e in Authority(ROOT).events()
                if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 18
    proposal = deepcopy(program)
    proposal['revision'] = 278
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, timeout_seconds=180, build_criteria_scope=[],
        reason='Five original financial reference findings require complete selected definitions; generic admission accepts truncated targets and an unpaired maturity citation',
        financial_reference_review={'version': 'basf-financial-references.v1', 'review': relative(PREP),
            'original_task_complete': False, 'bounds': {'stage_seconds': 180, 'new_seconds': 1200, 'new_bytes': 160 * 1024**2},
            'further_harness_retry_allowed': False},
        pre_admission_review=relative(PREP / 'PRE-ADMISSION-REVIEW.md'))
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(methods) + list(inputs) + [relative(PREP / 'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 19
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 278
    for row in routes['tasks']:
        if row['task'] == task['id']:
            row.update(dossier=PLAN, task_sha256=authority_digest(task),
                remaining='018 preserves32links; original split maturity, coupon date, annual day-count and tax-amount references remain unmapped.',
                next_action='Bind five original records to complete selected targets with exact scalar maps and paired maturity context; preserve UNKNOWN coupon heading and continue original remainder.',
                acceptance='Independent original endpoints/maps and full candidate/omission answers; actual admission and consumer refusals; all60original records retained; partial evidence only.',
                stop_condition='Nineteen cumulative admissions;90s preparation;180s stages;1200s measured;160MiB with4MiB reserve;no unchanged/harness retry.')
    save(PREP / 'routes.json', routes)
    proposal['continuation_review'].update(plan=PLAN, routes=relative(PREP / 'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN),
        relative(PREP / 'routes.json'): sha(PREP / 'routes.json'), relative(PREP / 'freeze.json'): sha(PREP / 'freeze.json')})
    review = {'baseline': authority_digest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'original_obligations_preserved': True,
        'changes': ['Five original financial source links', 'Complete paired targets with selected final-term scalar authority',
                    'Preserved unresolved coupon heading and prior unknowns', 'Actual ordinary consumer controls and60record reconciliation'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN, 'reproduced': relative(PREP / 'pre-repair.json'),
            'source_review': relative(PREP / 'PRE-ADMISSION-REVIEW.md'),
            'independent_endpoints': '118:17,18,20-23;111:24,33-37,58;112:1-3,18-19;123:35-37',
            'statutory_interpretation_remains_unresolved': True, 'whole_task_acceptance_claimed': False},
        'evidence_contract': {'primary': 'Independent original endpoints and scalar maps, full ordinary answers and original inventory',
            'veto': ['Truncated target', 'Unpaired maturity citation', 'Wrong tax branch', 'Changed scalar authority',
                     'Promoted UNKNOWN meaning', 'Changed unrelated answer', 'Method drift', 'Resource/harness invalidity'],
            'not_concluded': ['Actual payments or tax call', 'Legal application', 'Generic automatic interpretation', 'Whole reference task', 'Whole build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 18, 'new_maximum': 19,
            'retained_attempts': attempts,
            'reason': 'Five distinct original unmapped financial records with reproduced generic truncation and unpaired-citation acceptance; no repeat of old packages',
            'next_discriminating_check': 'Complete original target and scalar maps versus truncation, pair omission and false resolution through actual consumer',
            'stop_condition': '180s stages;1200s measured;160MiB;no unchanged/harness retry',
            'same_scope_authorization': 'User directs general build and internal conditional correctness, deferring actual holdings and reader acceptance'}}
    save(PREP / 'proposal.json', proposal)
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 278, 'prior_admissions': 18, 'resources': costs()}
