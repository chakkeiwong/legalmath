"""Bounded reproduction and repair evidence for complete default(f) verification."""
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
from legalmath.prospectus import basf_default_f_current as current
from legalmath.prospectus import default_f_certificates as independent
from legalmath.prospectus.successor.contracts import digest

AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
PREP = AUTH / 'reviews/current-default-verifier-258'
HERE = AUTH / 'attempts/basf-meanings/attempt-021'
PRIOR = AUTH / 'attempts/basf-meanings/attempt-020'
INPUTS = AUTH / 'reviews/current-default-alternatives-257'
PLAN = 'docs/plans/prospectus-current-default-verifier-2026-10-18.md'
ROUTES = 'docs/implementation/prospectus-execution-authority/closure-routes-2026-10-18-default-verifier-258.json'
PROPOSAL = AUTH / 'proposals/default-verifier-258.json'
REVIEW = AUTH / 'proposals/default-verifier-258-review.json'
OLD_SECONDS = 1378.8234869297594
OLD_BYTES = 451875495
STAGES = {'diagnose': (), 'freeze': ('diagnose',), 'propose': ('freeze',),
          'tests': ('propose',), 'verify': ('tests',), 'consumers': ('verify',),
          'seal': ('consumers',)}
PREPARATION = {'diagnose', 'freeze', 'propose'}


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2).encode()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(encoded(value))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def relative(path):
    return str(Path(path).relative_to(ROOT))


def methods():
    return sorted((ROOT / 'src/legalmath/prospectus').rglob('*.py')) + [
        Path(__file__), ROOT / PLAN, ROOT / 'tests/prospectus/test_current_default_f.py',
        ROOT / 'tests/prospectus/test_basf_default_f.py',
        ROOT / 'tests/prospectus/test_reasoning_certificates.py',
        ROOT / 'tests/prospectus_successor/test_basf_initial_agents.py',
        ROOT / 'scripts/prospectus_current_default_controls.py']


def costs(*, enforce=True):
    receipts = [p for base in (PREP, HERE) if base.exists() for p in base.glob('stages/*/result.json')]
    elapsed = sum(read(p)['wall_seconds'] for p in receipts)
    size = sum(p.stat().st_size for base in (PREP, HERE) if base.exists()
               for p in base.rglob('*') if p.is_file())
    for p in (Path(__file__), ROOT / PLAN, ROOT / 'src/legalmath/prospectus/basf_default_f_current.py',
              ROOT / 'tests/prospectus/test_current_default_f.py'):
        size += p.stat().st_size
        size += sum(c.stat().st_size for c in (p.parent / '__pycache__').glob(p.stem + '.*.pyc'))
    for p in (PROPOSAL, REVIEW, AUTH / 'revisions/0258.json', ROOT / ROUTES):
        if p.exists(): size += p.stat().st_size
    if read(AUTH / 'program.json')['revision'] >= 258:
        size += (AUTH / 'program.json').stat().st_size
    if enforce:
        assert elapsed < 240 and OLD_SECONDS + elapsed < 1800, 'Time ceiling exhausted'
        assert size < 47 * 1024**2 and OLD_BYTES + size < 500 * 1024**2, 'Storage reserve exhausted'
    return {'known015020_seconds': OLD_SECONDS, 'new_measured_seconds': elapsed,
            'known015plus_seconds': OLD_SECONDS + elapsed, 'new_bytes': size,
            'known015plus_bytes': OLD_BYTES + size, 'earlier_timing': 'UNKNOWN'}


def cases():
    return [
        ('unresolved-status', ['unresolved_default_f', 'status'], 'RESOLVED'),
        ('unresolved-evidence', ['unresolved_default_f', 'evidence'], []),
        ('reviewer-independence', ['reviewer', 'independent'], True),
        ('reviewer-basis', ['reviewer', 'basis'], 'LEGAL_ACCEPTANCE'),
        ('products-label', ['products_sha256'], '0' * 64),
        ('ordinary-label', ['ordinary_answer_sha256'], '0' * 64),
        ('temporal-text', ['temporal_rule'], 'Receipt alone establishes exercise.'),
        ('causal-text', ['causal_rule'], 'All causal alternatives are equivalent.'),
        ('next-evidence', ['next_evidence'], 'No further evidence is required.'),
        ('version', ['version'], 'unreviewed.v2'),
        ('extra-review-assertion', ['unconditional_legal_approval'], True),
        ('missing-explanation', ['next_evidence'], None),
        ('extra-scenario-assertion', ['scenarios', 0, 'unconditional_legal_approval'], True),
        ('scenario-interpretation', ['scenarios', 0, 'interpretation'], 'Governing meaning adjudicated.'),
        ('scenario-bc-scope', ['scenarios', 0, 'bc_result_scope'], 'All requirements established.'),
        ('numeric-scenario-flag', ['scenarios', 0, 'actual_event_established'], 0),
        ('extra-comparison-assertion', ['scenarios', 0, 'comparison', 'approval'], 'YES'),
    ]


def recertified(answer, ordinary, profile, name, path, value):
    changed = deepcopy(answer)
    target = changed['default_f_review']
    for key in path[:-1]: target = target[key]
    if name == 'missing-explanation': del target[path[-1]]
    else: target[path[-1]] = deepcopy(value)
    body = {k: v for k, v in ordinary.items() if k != 'report_sha256'}
    body['default_f_review'] = changed['default_f_review']
    subject = {**body, 'report_sha256': digest(body)}
    context = {'products_sha256': profile['products_sha256'],
        'ordinary_answer_sha256': profile['ordinary_answer_sha256'],
        'profile_sha256': digest(profile), 'sources': profile['sources'],
        'complete_consumer_sha256': digest(subject)}
    certificate = independent.certificate(subject, profile, expected_context=context)
    verification = independent.verify_consumer({**subject, 'reasoning_certificate': certificate},
                                               profile, expected_context=context)
    changed['default_f_reasoning_certificate'] = certificate
    changed['default_f_reasoning_verification'] = verification
    changed['report_sha256'] = digest({k: v for k, v in changed.items() if k != 'report_sha256'})
    return changed


def baseline():
    return read(PRIOR / 'current-answer.json.gz'), read(PRIOR / 'ordinary-answer.json.gz'), read(INPUTS / 'profile.json')


def diagnose():
    assert read(AUTH / 'program.json')['revision'] == 257
    # Snapshot the actual implementation before any repair, not a reconstructed old verifier.
    identities = {}
    for source in methods():
        identities[relative(source)] = sha(source)
        target = PREP / 'pre-edit' / relative(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    save(PREP / 'pre-edit.json', identities)
    bound = {}
    for folder in (PRIOR,):
        for name, expected in read(folder / 'outputs.json').items():
            assert sha(folder / name) == expected, 'Historical output corrupt: ' + name
            bound[relative(folder / name)] = expected
    frozen = read(INPUTS / 'freeze.json')
    for name, expected in {**frozen['inputs'], **read(INPUTS / 'original-inputs.json')}.items():
        assert sha(ROOT / name) == expected, 'Original input corrupt: ' + name
        bound[name] = expected
    save(PREP / 'original-inputs.json', bound)
    answer, ordinary, profile = baseline()
    assert current.verify_answer(answer, ordinary, profile,
        expected_profile_sha256=digest(profile))['checked_answers'] == 192
    outcomes = []
    for name, path, value in cases():
        try:
            changed = recertified(answer, ordinary, profile, name, path, value)
        except ValueError as error:
            outcomes.append({'name': name, 'path': path, 'value': value,
                'status': 'CERTIFICATE_REFUSED', 'error': str(error)})
            continue
        try:
            current.verify_answer(changed, ordinary, profile, expected_profile_sha256=digest(profile))
        except ValueError as error:
            status, message = 'VERIFIER_REFUSED', str(error)
        else:
            status, message = 'FORGERY_ACCEPTED', None
        outcomes.append({'name': name, 'path': path, 'value': value, 'status': status,
            'error': message, 'regenerated_complete_answer_sha256': digest(changed)})
    save(PREP / 'diagnosis.json', {'status': 'PASS', 'outcomes': outcomes,
        'claim': 'Actual old verifier, regenerated public certificate and outer hash'})
    count = sum(r['status'] == 'FORGERY_ACCEPTED' for r in outcomes)
    assert count, 'Repair hypothesis falsified: no implementation repair authorized'
    return {'status': 'PASS', 'reproduced_forgery_acceptances': count, 'cases': len(outcomes)}


def check_frozen():
    for name, expected in read(PREP / 'original-inputs.json').items():
        assert sha(ROOT / name) == expected, 'Input drift: ' + name
    for name, expected in read(PREP / 'freeze.json')['methods'].items():
        assert sha(ROOT / name) == expected, 'Method drift: ' + name
    if (HERE / 'admission.json').exists():
        for name, expected in read(HERE / 'admission.json')['binding'].items():
            assert sha(ROOT / name) == expected, 'Admission drift: ' + name


def freeze():
    assert any(r['status'] == 'FORGERY_ACCEPTED' for r in read(PREP / 'diagnosis.json')['outcomes'])
    identities = {relative(p): sha(p) for p in methods()}
    for name in identities:
        target = PREP / 'methods' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    save(PREP / 'freeze.json', {'methods': identities, 'audit': 'Reviewed plan and reproduced baseline; complete unchanged comparator and independent formulas retained',
        'production_delta': ['src/legalmath/prospectus/basf_default_f_current.py']})
    return {'status': 'PASS', 'methods': len(identities)}


def propose():
    from legalmath.prospectus.execution_authority import Authority, digest as authority_digest
    check_frozen()
    program = read(AUTH / 'program.json')
    assert program['revision'] == 257
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 258
    for row in routes['tasks']:
        if row['task'] == 'basf-meanings':
            row['remaining'] = '020 integrates all conditional alternatives into the current complete ordinary answer. Regenerated-certificate explanation forgeries reproduced in258 preparation; original legal construction remains unresolved.'
            row['next_action'] = 'Execute frozen021 complete-review verifier repair, then original source-to-answer reconciliation. Preserve020 and192 decisions.'
            row['dossier'] = PLAN
        if row['task'] == 'finance-conventions':
            row['remaining'] = 'Original G15 fixed-rate criterion: schedules, stubs, calendars, entitlement, aggregation, event ordering, rounding, independent calculations and matched QuantLib.003 and008 retained; do not invent floating-rate scope.'
            row['next_action'] = 'Reconcile003/008 with each original G15 requirement; identify a concrete unverified requirement before designing more finance cases.'
    save(ROOT / ROUTES, routes)
    proposal = deepcopy(program)
    proposal['revision'] = 258
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-meanings')
    task['dossier'] = PLAN
    task['reason'] = 'Reproduced accepted recertified explanation forgeries in actual complete-answer verifier; narrow same-task repair, unchanged legal hypotheses, independent formulas and complete020 comparator.'
    paths = [p for p in PREP.rglob('*') if p.is_file()]
    task['inputs'] = list(dict.fromkeys(task['inputs'] + [relative(p) for p in paths] +
        list(read(PREP / 'freeze.json')['methods']) + [ROUTES]))
    proposal['budgets']['basf-meanings']['maximum_new_attempts'] = 21
    proposal['continuation_review'].update(plan=PLAN, routes=ROUTES)
    proposal['continuation_review']['bindings'].update({relative(p): sha(p) for p in paths})
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN), ROUTES: sha(ROOT / ROUTES)})
    attempts = [e['attempt'] for e in Authority(ROOT).events()
                if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-meanings']
    review = {'baseline': authority_digest(program), 'changes': [
        'Reject complete-review explanation tampering even after recertification',
        'Refresh020 route and restore original fixed-rate G15 criterion'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN,
            'baseline': 'Actual old verifier accepts retained metadata forgeries; immutable complete020 comparator',
            'resolved': ['Public recertification, not stale hashes', 'No new legal opinion',
                'Independent Boolean checker preserved', 'Exact complete valid output equality',
                'Original acceptance and cumulative limits preserved']},
        'evidence_contract': {'question': 'Does complete-answer verification constrain every explanatory assertion?',
            'primary': 'All reproduced recertified forgeries refused; complete020 output identical',
            'veto': ['Source/method/comparator drift', 'Changed valid answer', 'Failed adverse check'],
            'not_concluded': ['Exhaustive legal interpretation', 'Actual default', 'Original task/build closure']},
        'scope_unchanged': True, 'budget_unchanged': False,
        'budget_revision': {'budget_key': 'basf-meanings', 'previous_maximum': 20, 'new_maximum': 21,
            'retained_attempts': attempts, 'reason': 'Distinct reproduced verifier defect, not unchanged retry',
            'next_discriminating_check': 'Recertified metadata forgeries and full valid consumer equality',
            'stop_condition': {'known_previous_seconds': OLD_SECONDS, 'cumulative_seconds': 1800,
                'cumulative_bytes': 500 * 1024**2, 'new_seconds': 240, 'new_bytes': 48 * 1024**2,
                'reserve_bytes': 1024**2, 'stage_seconds': 90, 'no_network_native_OCR_model_GPU': True},
            'same_scope_authorization': 'User refresh master program and continue general build'},
        'original_obligations_preserved': True, 'external_opinion_required': False}
    # Proposal, committed revision and replacement active copy all use this serializer.
    forecast = costs()['new_bytes'] + 3 * len(encoded(proposal)) + len(encoded(review))
    assert forecast < 47 * 1024**2 and OLD_BYTES + forecast < 500 * 1024**2
    save(PROPOSAL, proposal)
    save(REVIEW, review)
    return {'status': 'PASS', 'forecast_new_bytes': forecast, 'retained_admissions': len(attempts)}


def tests():
    import pytest
    code = pytest.main(['-q', 'tests/prospectus/test_current_default_f.py',
        'tests/prospectus/test_basf_default_f.py', 'tests/prospectus/test_reasoning_certificates.py',
        'tests/prospectus_successor/test_basf_initial_agents.py', '--junitxml=' + str(HERE / 'tests.xml')])
    assert code == 0
    return {'status': 'PASS', 'focused_regressions': True}


def verify():
    answer, ordinary, profile = baseline()
    valid = current.verify_answer(answer, ordinary, profile, expected_profile_sha256=digest(profile))
    rows = []
    for name, path, value in cases():
        try:
            changed = recertified(answer, ordinary, profile, name, path, value)
            current.verify_answer(changed, ordinary, profile, expected_profile_sha256=digest(profile))
        except ValueError as error:
            rows.append({'name': name, 'status': 'REFUSED', 'error': str(error)})
        else:
            raise AssertionError('Recertified forgery accepted: ' + name)
    save(HERE / 'verification.json', {'status': 'PASS', 'valid': valid, 'adverse': rows,
        'complete_valid_answer_sha256': digest(answer), 'unchanged_baseline': relative(PRIOR)})
    return {'status': 'PASS', 'checked_answers': valid['checked_answers'], 'refusals': len(rows)}


def consumers():
    from legalmath.prospectus.successor import service
    products = read(INPUTS / 'products.json.gz')
    answer, ordinary, profile = baseline()
    observed = service.consume(products, ROOT, mode='frozen', default_f_profile=profile,
        expected_default_f_profile_sha256=digest(profile))
    assert digest(observed) == digest(answer), 'Complete valid answer changed'
    omitted = service.consume(products, ROOT, mode='frozen')
    assert digest(omitted) == digest(ordinary), 'Complete omitted-option answer changed'
    save(HERE / 'comparison.json', {'status': 'PASS', 'complete_answer_equal020': True,
        'omission_equal020': True, 'answer_sha256': digest(observed), 'ordinary_sha256': digest(omitted),
        'immutable_answer': relative(PRIOR / 'current-answer.json.gz'),
        'immutable_ordinary': relative(PRIOR / 'ordinary-answer.json.gz')})
    return {'status': 'PASS', 'complete_answer_equal020': True, 'omission_equal020': True}


def seal():
    check_frozen()
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    save(HERE / 'run-manifest.json', {'git_commit': commit, 'dirty_methods': relative(PREP / 'freeze.json'),
        'command': 'stages/*/started.json', 'environment': sys.executable, 'python': sys.version,
        'module_origins': {'current': current.__file__, 'independent': independent.__file__},
        'cpu_gpu': 'CPU only; CUDA_VISIBLE_DEVICES=-1 before imports', 'random_seeds': 'N/A deterministic',
        'plan': PLAN, 'result': relative(HERE / 'RESULT.md'), 'data': relative(PREP / 'original-inputs.json'),
        'resources_before_seal': costs(), 'network_native_OCR_model_GPU_calls': 0})
    note = '''# Complete current default(f) verification repaired

The pre-edit verifier accepted altered explanatory assertions after public
certificates and the outer report hash were regenerated. The diagnosis retains
each mutation and the actual old verdict. The repair checks complete review and
scenario schemas, profile policy and exact metadata against the pinned inputs.
The independent Boolean formulas remain unchanged. All reproduced forgeries
are now refused; the valid complete answer equals020, including all192 decisions
and certificates. Omitting the option preserves the complete ordinary answer.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain narrow verifier repair | Recertified forgeries refused; complete valid020 equality | No observed input, formula or comparator drift | Disclosed legal readings remain nonexhaustive | Record/refresh, return to original source-to-answer coverage | Legal exhaustiveness, actual default or task/build completion |
| Attribute reproduced gap to our verifier | Actual old verifier accepted changed explanation | Public certificate correctly checked its narrower Boolean subject | Other integration boundaries require their own evidence | Keep inference and explanatory integrity separately tested | Third-party package defect |

The strongest alternative explanation is a shared error in source interpretation.
This repair closes explanatory integrity within the pinned finite contract; it
does not prove that the hypotheses exhaust the governing law. Source corruption,
a valid answer regression or a further accepted assertion forgery would overturn
the engineering verdict. No external adviser opinion or new private fact was used.
'''
    with (HERE / 'RESULT.md').open('x') as stream: stream.write(note)
    save(HERE / 'result.json', {'status': 'PASS', 'task_complete': False, 'build_criteria_scope': [],
        'claim': 'COMPLETE_DEFAULT_F_VERIFIER_REPAIR', 'verification': read(HERE / 'verification.json'),
        'comparison': read(HERE / 'comparison.json'), 'resources_before_seal': costs(),
        'http_calls': 0, 'native_calls': 0})
    return {'status': 'SEALED_PARTIAL', 'task_complete': False}


def main():
    stage = sys.argv[1]
    assert stage in STAGES
    base = PREP if stage in PREPARATION else HERE
    for predecessor in STAGES[stage]:
        folder = PREP if predecessor in PREPARATION else HERE
        assert read(folder / 'stages' / predecessor / 'result.json')['status'] == 'PASS'
    if stage not in PREPARATION:
        assert (HERE / 'admission.json').exists(), 'Reviewed admission required'
        check_frozen()
    before = costs()
    limit = min(90, int(240 - before['new_measured_seconds']), int(1800 - before['known015plus_seconds']))
    assert limit >= 5
    save(base / 'stages' / stage / 'started.json', {'command': ['.venv/bin/python', '-m',
        'scripts.prospectus_default_verifier', stage], 'utc': datetime.now(timezone.utc).isoformat(),
        'timeout_seconds': limit, 'resources_before': before})
    def alarm(*args): raise TimeoutError('Reviewed verifier-stage limit')
    signal.signal(signal.SIGALRM, alarm)
    signal.alarm(limit)
    started = time.monotonic()
    try:
        details = globals()[stage]()
        receipt = {'status': 'PASS', 'details': details, 'wall_seconds': time.monotonic() - started}
    except Exception as error:
        receipt = {'status': 'FAIL', 'error': repr(error), 'wall_seconds': time.monotonic() - started}
        save(base / 'stages' / stage / 'result.json', receipt)
        if base == HERE:
            if not (HERE / 'result.json').exists():
                save(HERE / 'result.json', {'status': 'FAIL', 'task_complete': False,
                    'build_criteria_scope': [], 'failed_stage': stage, 'error': repr(error)})
            save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*')
                if p.is_file() and p.name not in {'admission.json', 'outputs.json'}})
        raise
    finally:
        signal.alarm(0)
    save(base / 'stages' / stage / 'result.json', receipt)
    if stage == 'seal':
        save(HERE / 'resources.json', costs())
        save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*')
            if p.is_file() and p.name not in {'admission.json', 'outputs.json'}})
    print(json.dumps({'stage': stage, **receipt, 'resources': costs()}))


if __name__ == '__main__':
    main()
