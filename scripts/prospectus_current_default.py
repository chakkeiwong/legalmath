"""Bounded current BASF default alternatives; no new source extraction."""
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus import basf_default_f as old

AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
PREP = AUTH / 'reviews/current-default-alternatives-257'
HERE = AUTH / 'attempts/basf-meanings/attempt-020'
PREVIOUS = AUTH / 'attempts/basf-meanings/attempt-019'
REFERENCE = AUTH / 'attempts/basf-meanings/attempt-013'
PLAN = 'docs/plans/prospectus-current-default-alternatives-2026-10-18.md'
ROUTES = 'docs/implementation/prospectus-execution-authority/closure-routes-2026-10-18-current-default-257.json'
OLD_SECONDS = 1275.1259347619489
OLD_BYTES = 393177644
STAGES = {'prepare': (), 'propose': ('prepare',), 'tests': ('propose',),
          'consumers': ('tests',), 'validate': ('consumers',), 'seal': ('validate',)}


def read(path):
    data = Path(path).read_bytes()
    return json.loads(gzip.decompress(data) if str(path).endswith('.gz') else data)


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2).encode()
    with path.open('xb') as stream:
        stream.write(gzip.compress(data, mtime=0) if str(path).endswith('.gz') else data)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def relative(path):
    return str(Path(path).relative_to(ROOT))


def costs(*, enforce=True):
    receipts = [p for base in (PREP, HERE) if base.exists() for p in base.glob('stages/*/result.json')]
    elapsed = sum(read(p)['wall_seconds'] for p in receipts)
    size = sum(p.stat().st_size for base in (PREP, HERE) if base.exists() for p in base.rglob('*') if p.is_file())
    for name in ('scripts/prospectus_current_default.py', 'scripts/prospectus_current_default_controls.py',
                 'src/legalmath/prospectus/basf_default_f_current.py',
                 'src/legalmath/prospectus/successor/service.py',
                 'tests/prospectus/test_current_default_f.py', PLAN):
        p = ROOT / name
        if p.exists():
            size += p.stat().st_size
            size += sum(c.stat().st_size for c in (p.parent / '__pycache__').glob(p.stem + '.*.pyc'))
    # Retained proposal, revision and the replacement active copy count too.
    for p in (AUTH / 'proposals/current-default-257.json', AUTH / 'proposals/current-default-257-review.json',
              AUTH / 'revisions/0257.json', ROOT / ROUTES):
        if p.exists(): size += p.stat().st_size
    active = AUTH / 'program.json'
    if read(active)['revision'] >= 257: size += active.stat().st_size
    if enforce:
        assert OLD_SECONDS + elapsed < 1800 and elapsed < 600, 'Cumulative time exhausted'
        assert OLD_BYTES + size < 500 * 1024**2 and size < 64 * 1024**2 - 1024**2, 'Storage reserve exhausted'
    return {'known015019_seconds': OLD_SECONDS, 'new_measured_seconds': elapsed,
            'known015plus_seconds': OLD_SECONDS + elapsed, 'new_bytes': size,
            'known015plus_bytes': OLD_BYTES + size, 'earlier_history': 'Retained, not completely timed'}


def inputs():
    paths = [PREVIOUS / 'installed-construct/products.json.gz',
             PREVIOUS / 'installed-interpret/semantic.json.gz',
             PREVIOUS / 'installed-complete/downstream-products.json.gz',
             PREVIOUS / 'installed-answer/ordinary-answer.json.gz',
             PREVIOUS / 'run-manifest.json', REFERENCE / 'profile.json',
             REFERENCE / 'default-consumer.json.gz']
    profile = read(REFERENCE / 'profile.json')
    for document in profile['sources']:
        for row in (document, *document['images']):
            path = ROOT / row['path']
            assert sha(path) == row['sha256'], 'Original source changed'
            paths.append(path)
    return paths


def prepare():
    assert read(AUTH / 'program.json')['revision'] == 256
    save(PREP / 'original-inputs.json', {relative(p): sha(p) for p in inputs()})
    save(PREP / 'authority-before.json', {'program_sha256': digest(read(AUTH / 'program.json')),
        'program_file_sha256': sha(AUTH / 'program.json'), 'revision': 256})
    for name in ('successor/service.py', 'basf_default_f.py', 'default_f_certificates.py'):
        src = ROOT / 'src/legalmath/prospectus' / name
        target = PREP / 'pre-edit' / relative(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
    products = read(PREVIOUS / 'installed-construct/products.json.gz')
    products['P3'] = read(PREVIOUS / 'installed-interpret/semantic.json.gz')
    products.update(read(PREVIOUS / 'installed-complete/downstream-products.json.gz'))
    assert set(products) == {'P1', 'P2', 'P3', 'P4', 'P5'}
    try:
        service.consume(products, ROOT, default_f_profile={}, expected_default_f_profile_sha256='0' * 64)
    except TypeError as error:
        assert 'default_f_profile' in str(error)
        save(PREP / 'unsupported.json', {'status': 'REPRODUCED_UNSUPPORTED_CURRENT_INTERFACE',
            'type': type(error).__name__, 'message': str(error), 'native_calls': 0})
    else:
        raise AssertionError('Expected current integration gap was not reproduced')
    baseline = service.consume(products, ROOT, mode='frozen')
    assert baseline == read(PREVIOUS / 'installed-answer/ordinary-answer.json.gz'), 'Current ordinary comparator drift'
    groups = old.source_groups(products)
    original = read(REFERENCE / 'profile.json')
    assert groups == original['groups'], 'Source groups differ from reviewed hypotheses'
    save(PREP / 'products.json.gz', products)
    save(PREP / 'ordinary-answer.json.gz', baseline)
    save(PREP / 'source-comparison.json', {'status': 'PASS', 'all_groups_equal013': True,
        'groups': groups, 'source_pdfs_images': original['sources'],
        'inspected_pages': ['German127', 'final7'],
        'remaining_original_pages': 'Reviewed in retained013 evidence; hash verified here'})
    return {'status': 'PASS', 'current_baseline_equal019': True, 'source_groups_equal013': True,
            'unsupported_interface_reproduced': True, 'native_calls': 0}


def method_paths():
    return sorted((ROOT / 'src/legalmath/prospectus').rglob('*.py')) + [
        Path(__file__), ROOT / PLAN, ROOT / 'tests/prospectus/test_current_default_f.py',
        ROOT / 'tests/prospectus/test_basf_default_f.py',
        ROOT / 'tests/prospectus/test_reasoning_certificates.py',
        ROOT / 'tests/prospectus_successor/test_basf_initial_agents.py',
        ROOT / 'scripts/prospectus_current_default_controls.py',
        ROOT / 'scripts/prospectus_default_f_scenarios.py']


def check_frozen():
    for p, h in read(PREP / 'freeze.json')['methods'].items():
        assert sha(ROOT / p) == h, 'Frozen method changed: ' + p
    for p, h in read(PREP / 'original-inputs.json').items():
        assert sha(ROOT / p) == h, 'Retained input changed: ' + p
    for p, h in read(PREP / 'freeze.json').get('inputs', {}).items():
        assert sha(ROOT / p) == h, 'Prepared comparator/profile changed: ' + p
    if (HERE / 'admission.json').exists():
        for p, h in read(HERE / 'admission.json')['binding'].items():
            assert sha(ROOT / p) == h, 'Admitted binding changed: ' + p


def propose():
    from legalmath.prospectus import basf_default_f_current as current
    program = read(AUTH / 'program.json')
    assert program['revision'] == 256
    profile = read(REFERENCE / 'profile.json')
    profile['version'] = current.VERSION
    profile.pop('prior_sha256')
    profile['products_sha256'] = digest(read(PREP / 'products.json.gz'))
    profile['ordinary_answer_sha256'] = digest(read(PREP / 'ordinary-answer.json.gz'))
    save(PREP / 'profile.json', profile)
    methods = {relative(p): sha(p) for p in method_paths()}
    for name in methods:
        target = PREP / 'methods' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    frozen_inputs = {relative(p): sha(p) for p in
        (PREP / 'products.json.gz', PREP / 'ordinary-answer.json.gz', PREP / 'profile.json',
         PREP / 'original-inputs.json', PREP / 'source-comparison.json',
         ROOT / 'tests/prospectus_successor/fixtures/basf-agent-source.json')}
    save(PREP / 'freeze.json', {'methods': methods, 'inputs': frozen_inputs,
        'profile_sha256': digest(profile),
        'production_delta': ['src/legalmath/prospectus/basf_default_f_current.py',
                             'src/legalmath/prospectus/successor/service.py'],
        'audit': 'Plan skeptical audit PASS; exact reproduced interface; independent historical and certificate comparators'})
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 257
    for row in routes['tasks']:
        # Preserve original requirements in their historical layer. Current
        # conditional build is governed by the retained user-directed contract.
        row.setdefault('route_before257', {k: deepcopy(row.get(k)) for k in
            ('mode', 'remaining', 'next_action', 'acceptance', 'external_inputs')})
        if row['task'] == 'finance-conventions':
            row['remaining'] = '256/008 complete: six fixed coupons, direct consumers, independent267750 oracle and44 adverse refusals; floating phase and original finance coverage remain.'
            row['next_action'] = 'Preserve fixed-phase evidence; continue distinct unsupported finance requirements, then current installed validation after methods stabilize.'
        if row['task'] == 'entitlement':
            row['remaining'] = '255/011 complete: BBVA/SEB selected registration groups,9 valid and25 adverse cases each; actual holdings and broader source coverage remain.'
            row['next_action'] = 'Preserve registration repair; general conditional build continues without actual holdings.'
        if row['task'] == 'basf-meanings':
            row['remaining'] = '019 current ordinary/financial installation retained; default(f) alternatives remain attached only to historical body consumer.'
            row['next_action'] = 'Execute reviewed257/020 frozen current ordinary-consumer integration; original German construction remains unresolved.'
            row['dossier'] = PLAN
            row['acceptance'] = 'Current conditional build: complete current source-bound ordinary answer, explicit alternatives, independent inference checks and adverse controls. Original task acceptance remains preserved in its historical layer.'
            row['external_inputs'] = ['Authentic appointment/office evidence and dated event/causation facts for actual application after the general build. No outside opinion is a conditional-build prerequisite.']
    save(ROOT / ROUTES, routes)
    proposal = deepcopy(program)
    proposal['revision'] = 257
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-meanings')
    task['dossier'] = PLAN
    task['reason'] = 'Distinct reproduced current-consumer integration gap; reuse unchanged default(f) hypotheses and independently certify current ordinary answer; retain all19 admissions and1800s/500MiB lineage.'
    paths = [p for p in PREP.rglob('*') if p.is_file()]
    extra = [relative(p) for p in paths] + list(methods) + list(frozen_inputs) + [ROUTES]
    task['inputs'] = list(dict.fromkeys(task['inputs'] + extra))
    proposal['budgets']['basf-meanings']['maximum_new_attempts'] = 20
    proposal['continuation_review']['plan'] = PLAN
    proposal['continuation_review']['routes'] = ROUTES
    proposal['continuation_review']['bindings'].update({relative(p): sha(p) for p in paths})
    proposal['continuation_review']['bindings'].update({ROUTES: sha(ROOT / ROUTES), PLAN: sha(ROOT / PLAN)})
    from legalmath.prospectus.execution_authority import Authority
    events = Authority(ROOT).events()
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-meanings']
    review = {'baseline': digest(program), 'changes': ['Refresh completed finance/entitlement routes',
        'Current ordinary-consumer default(f) integration under same task', 'Preserve user-directed conditional build and all original acceptance'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN,
            'baseline': 'Fresh complete019 ordinary answer and original013 groups/decisions',
            'resolved': ['No new truth-table campaign', 'No external opinion prerequisite',
                         'No historical-chain masquerade', 'Freeze before admit', 'No legal/whole-task promotion']},
        'evidence_contract': {'question': 'Current ordinary source-bound conditional alternatives?',
            'primary': 'Complete ordinary preservation;16*3*4 decisions and independent certificates; omission and actual adverse refusals',
            'veto': ['Source/method drift', 'Changed ordinary answer', 'Missing or promoted reading', 'Failed adverse control'],
            'not_concluded': ['Exhaustive legal construction', 'Actual default', 'Installed currentness', 'Whole-build acceptance']},
        'scope_unchanged': True, 'budget_unchanged': False,
        'budget_revision': {'budget_key': 'basf-meanings', 'previous_maximum': 19, 'new_maximum': 20,
            'retained_attempts': attempts, 'reason': 'Distinct reproduced integration gap, not unchanged retry',
            'next_discriminating_check': 'Actual current ordinary consumer and independent certificates',
            'stop_condition': {'known_previous_seconds': OLD_SECONDS, 'cumulative_seconds': 1800,
                'cumulative_bytes': 500 * 1024**2, 'new_seconds': 600, 'new_bytes': 64 * 1024**2,
                'stage_seconds': 120, 'no_new_network_native_OCR_model_GPU': True},
            'same_scope_authorization': 'User directed refresh and continued general build'},
        'original_obligations_preserved': True, 'external_opinion_required': False}
    proposal_path = AUTH / 'proposals/current-default-257.json'
    review_path = AUTH / 'proposals/current-default-257-review.json'
    projected = costs()['new_bytes'] + 3 * len(json.dumps(proposal, ensure_ascii=False, indent=2).encode()) + len(json.dumps(review).encode())
    assert projected < 64 * 1024**2 - 1024**2 and OLD_BYTES + projected < 500 * 1024**2
    save(proposal_path, proposal)
    save(review_path, review)
    return {'status': 'PASS', 'frozen_methods': len(methods), 'projected_new_bytes': projected,
            'retained_admissions': len(attempts), 'no_existing_build_criteria_claimed': True}


def tests():
    import pytest
    code = pytest.main(['-q', 'tests/prospectus/test_current_default_f.py',
        'tests/prospectus/test_basf_default_f.py', 'tests/prospectus/test_reasoning_certificates.py',
        'tests/prospectus_successor/test_basf_initial_agents.py',
        '--junitxml=' + str(HERE / 'tests.xml')])
    assert code == 0
    return {'status': 'PASS', 'selected_regressions_pass': True}


def consumers():
    products = read(PREP / 'products.json.gz')
    profile = read(PREP / 'profile.json')
    baseline = service.consume(products, ROOT, mode='frozen')
    assert baseline == read(PREP / 'ordinary-answer.json.gz')
    candidate = service.consume(products, ROOT, mode='frozen', default_f_profile=profile,
        expected_default_f_profile_sha256=digest(profile))
    added = {'default_f_review', 'default_f_reasoning_certificate', 'default_f_reasoning_verification'}
    assert {k: v for k, v in candidate.items() if k not in added | {'report_sha256'}} == {
        k: v for k, v in baseline.items() if k != 'report_sha256'}
    assert candidate['default_f_reasoning_verification']['checked_answers'] == 192
    original = read(REFERENCE / 'default-consumer.json.gz')['default_f_review']
    assert candidate['default_f_review']['scenarios'] == original['scenarios']
    assert service.consume(products, ROOT, mode='frozen') == baseline
    save(HERE / 'ordinary-answer.json.gz', baseline)
    save(HERE / 'current-answer.json.gz', candidate)
    save(HERE / 'comparison.json', {'status': 'PASS', 'full_ordinary_preserved': True,
        'all_current_scenarios_equal013': True, 'omission_restores_full_ordinary': True,
        'source_groups_equal013': candidate['default_f_review']['groups'] == original['groups'],
        'certificate_verification': candidate['default_f_reasoning_verification']})
    return read(HERE / 'comparison.json')


def validate():
    from legalmath.prospectus import basf_default_f_current as current
    from scripts.prospectus_default_f_scenarios import EXPECTED
    from scripts.prospectus_current_default_controls import adverse_controls
    products, profile = read(PREP / 'products.json.gz'), read(PREP / 'profile.json')
    baseline, candidate = read(HERE / 'ordinary-answer.json.gz'), read(HERE / 'current-answer.json.gz')
    observed = {}
    for row in candidate['default_f_review']['scenarios']:
        statuses = ([v['modeled_f_exercise']['status'] for v in row['readings'].values()],
                    [v['bc_quorum_condition_at_receipt']['status'] for v in row['readings'].values()])
        assert statuses == tuple(EXPECTED[row['id']])
        observed[row['id']] = statuses
    controls = adverse_controls(products, baseline, profile, ROOT)
    assert len(controls) >= 20 and all(r['status'] == 'REFUSED' for r in controls)
    fresh = current.evaluate(products, baseline, profile, ROOT, expected_profile_sha256=digest(profile))
    assert all(candidate[k] == v for k, v in fresh.items())
    verified = current.verify_answer(candidate, baseline, profile,
        expected_profile_sha256=digest(profile))
    assert verified == candidate['default_f_reasoning_verification']
    save(HERE / 'validation.json', {'status': 'PASS', 'scenario_outcomes': observed,
        'adverse_controls': controls, 'fresh_independent_verification': True,
        'complete_retained_answer_verification': verified})
    return {'status': 'PASS', 'scenarios': len(observed), 'adverse_refusals': len(controls), 'checked_answers': 192}


def seal():
    check_frozen()
    comparison, validation = read(HERE / 'comparison.json'), read(HERE / 'validation.json')
    resources = costs()
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    save(HERE / 'run-manifest.json', {'git_commit': commit, 'dirty_methods': relative(PREP / 'freeze.json'),
        'environment': sys.executable, 'python_version': sys.version,
        'module_origins': {'service': service.__file__, 'hypotheses': old.__file__},
        'cpu_gpu': 'CPU only; CUDA_VISIBLE_DEVICES=-1 before imports',
        'random_seeds': 'N/A deterministic', 'plan': PLAN, 'result': relative(HERE / 'RESULT.md'),
        'data': relative(PREP / 'original-inputs.json'), 'commands': 'stages/*/started.json',
        'resources_before_seal': resources, 'native_network_OCR_model_GPU_calls': 0,
        'known_history': '015019 measured; earlier historical admissions retained without invented timings'})
    text = '''# Current ordinary BASF alternatives integrated

The optional current ordinary consumer preserves the complete pre-option answer
and adds all three retained German-source hypotheses across16 hypothetical
scenarios and four temporal/eligibility questions. All192 decisions are checked
by the separate certificate implementation. All complete scenario outputs equal
the original013 comparison. Omitting the option restores the complete ordinary
answer. Required adverse controls refuse changed inputs and promoted conclusions.

The reproduced problem was our integration: the existing comparison was bound
to a historical body/financial answer. It was not evidence of a third-party
package failure. Original default(f) source roles and Q1–Q6 unknowns remain.
No construction is selected, no actual event is established and no external
adviser's opinion is required for this conditional engineering result.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain optional current integration | Complete ordinary preservation, historical scenario equality and independent certificates | No observed source, answer or inference drift | The three legal readings are expressly non-exhaustive | Record/refresh; reconcile remaining source-to-answer coverage | Actual default, exhaustive interpretation or original task completion |
| Attribute gap to our integration | Unsupported current interface reproduced before repair | Existing conditional engine remained usable | Other real sources/environments remain untested | Review exact current method deltas before installed/native validation | Fundamental package defect or universal correctness |

The strongest alternative explanation is a shared error in the disclosed source
hypotheses. Independent Boolean certificates check inference from those formulas;
they do not prove the formulas exhaust the governing law. A conflicting source
reading or failing adverse case would require a new bounded review. New source
extraction, package installation and portability have not been tested here.
'''
    (HERE / 'RESULT.md').write_text(text)
    save(HERE / 'result.json', {'status': 'PASS', 'task_complete': False,
        'build_criteria_scope': [], 'claim': 'CONDITIONAL_CURRENT_DEFAULT_F_INTEGRATION',
        'comparison': comparison, 'adverse_refusals': len(validation['adverse_controls']),
        'resources_before_seal': resources, 'native_calls': 0, 'http_calls': 0})
    return {'status': 'SEALED_PARTIAL', 'task_complete': False, 'checked_answers': 192}


def main():
    stage = sys.argv[1]
    assert stage in STAGES
    base = PREP if stage in {'prepare', 'propose'} else HERE
    for predecessor in STAGES[stage]:
        folder = PREP if predecessor in {'prepare', 'propose'} else HERE
        assert read(folder / 'stages' / predecessor / 'result.json')['status'] == 'PASS'
    if stage not in {'prepare', 'propose'}:
        assert (HERE / 'admission.json').exists(), 'Admission required'
        check_frozen()
    before = costs()
    limit = 120
    limit = min(limit, int(1800 - before['known015plus_seconds']), int(600 - before['new_measured_seconds']))
    assert limit >= 5
    save(base / 'stages' / stage / 'started.json', {'command': ['.venv/bin/python', '-m',
        'scripts.prospectus_current_default', stage], 'utc': datetime.now(timezone.utc).isoformat(),
        'timeout_seconds': limit, 'resources_before': before})
    def alarm(*args): raise TimeoutError('Reviewed current-default stage limit')
    signal.signal(signal.SIGALRM, alarm)
    signal.alarm(limit)
    started = time.monotonic()
    try:
        details = globals()[stage]()
        receipt = {'status': 'PASS', 'details': details, 'wall_seconds': time.monotonic() - started}
    except Exception as error:
        receipt = {'status': 'FAIL', 'error': repr(error), 'wall_seconds': time.monotonic() - started}
        save(base / 'stages' / stage / 'result.json', receipt)
        if base == HERE and (HERE / 'admission.json').exists():
            # Retain an honest failed package, never edit bound methods or retry
            # this stage. Recording it requires a distinct reviewed correction.
            if not (HERE / 'result.json').exists():
                save(HERE / 'result.json', {'status': 'FAIL', 'task_complete': False,
                    'build_criteria_scope': [], 'failed_stage': stage, 'error': repr(error),
                    'resources': costs(enforce=False)})
            if not (HERE / 'outputs.json').exists():
                save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*')
                    if p.is_file() and p.name not in {'admission.json', 'outputs.json'}})
        raise
    finally:
        signal.alarm(0)
    save(base / 'stages' / stage / 'result.json', receipt)
    resources = costs()
    if stage == 'seal':
        save(HERE / 'resources.json', resources)
        save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*')
            if p.is_file() and p.name not in {'admission.json', 'outputs.json'}})
        costs()
    print(json.dumps({'stage': stage, **receipt, 'resources': resources}, ensure_ascii=False))


if __name__ == '__main__':
    main()
