"""Verify successful retained consumer outputs while preserving campaign failure."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zipfile

from scripts.prospectus_default_holder import ROOT, AUTH, read, save, sha, rel, adigest, Authority
from scripts import prospectus_shell_source_chain_verify as evidence

PREP = AUTH / 'reviews/source-chain-retained-383'
HERE = AUTH / 'attempts/source-authority/attempt-012'
OLD = AUTH / 'attempts/source-authority/attempt-011'
OLD_PREP = AUTH / 'reviews/shell-source-chain-repair-381'
BES = AUTH / 'attempts/source-bes-dep-01/attempt-006'
PLAN = 'docs/plans/prospectus-source-chain-retained-verification-2026-10-21.md'
SELF = rel(Path(__file__))


def authenticated(folder):
    rows = [e for e in Authority(ROOT).events() if e.get('attempt') == rel(folder) and 'outputs_sha256' in e]
    assert rows and rows[-1]['outputs_sha256'] == sha(folder / 'outputs.json')
    for name, checksum in read(folder / 'outputs.json').items():
        assert sha(folder / name) == checksum, rel(folder / name)


def resources(reserve=0):
    start = read(PREP / 'accounting-start.json')
    paths = {p for folder in (PREP, HERE) for p in folder.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / n for n in (PLAN, SELF))
    paths.add(AUTH / 'revisions/0383.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    measured = sum(read(p)['wall_seconds'] for p in HERE.glob('commands/*.json'))
    return {'new_bytes': size, 'reserved_bytes': reserve, 'new_measured_seconds': measured,
        'new_conservative_control_seconds': 60,
        'known006plus_bytes': start['prior_bytes'] + size,
        'known006plus_accounted_seconds': start['prior_seconds'] + measured + 60,
        'old_storage_ceiling': 384 * 1024**2, 'new_storage_ceiling': 448 * 1024**2,
        'previous_ceiling_failure_preserved': True, 'earlier_and_manual_costs': 'UNKNOWN', 'old_costs_reset': False,
        'execution_allowed': size + reserve < 30 * 1024**2
            and start['prior_bytes'] + size + reserve < 446 * 1024**2
            and measured < 30 and start['prior_seconds'] + measured + 60 < 1900}


def prepare():
    old = read(AUTH / 'program.json')
    assert old['revision'] == 382 and not PREP.exists() and not HERE.exists()
    authenticated(OLD)
    authenticated(BES)
    assert read(OLD / 'result.json')['status'] == 'FAIL'
    assert read(BES / 'result.json')['status'] == 'PASS'
    old_resources = read(OLD / 'result.json')['resources']
    # These files were all absent at the before-failure-bookkeeping snapshot.
    additions = ['failure-completion-method.json', 'original-requirements.json', 'RESULT.md',
        'result.json', 'run-manifest.json', 'stages/reconcile/result.json', 'stages/seal/result.json', 'outputs.json']
    bookkeeping = sum((OLD / n).stat().st_size for n in additions)
    bookkeeping += sum((ROOT / n).stat().st_size for n in (
        'docs/plans/prospectus-source-chain-storage-failure-2026-10-21.md', 'scripts/prospectus_source_chain_failure_record.py'))
    historical = []
    for path in (AUTH / 'history').glob('*.json'):
        event = read(path)
        if event['seq'] in (2462, 2463):
            historical.append(path)
    assert len(historical) == 2
    bookkeeping += sum(p.stat().st_size for p in historical)
    save(PREP / 'accounting-start.json', {
        'prior_seconds': old_resources['known006plus_accounted_seconds'],
        'prior_bytes': old_resources['known006plus_bytes_before_failure_bookkeeping'] + bookkeeping,
        'added_failure_bookkeeping_bytes': bookkeeping,
        'previous_failed_bounds': {'incremental': 128 * 1024**2, 'cumulative': 384 * 1024**2},
        'program_bytes': (AUTH / 'program.json').stat().st_size,
        'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
        'earlier_and_manual_costs': 'UNKNOWN'})
    prior_freeze = read(OLD_PREP / 'freeze.json')
    for name, checksum in prior_freeze['bindings'].items():
        assert sha(ROOT / name) == checksum, name
    bindings = {n: sha(ROOT / n) for n in (PLAN, SELF, 'scripts/prospectus_shell_source_chain_verify.py',
        rel(OLD_PREP / 'freeze.json'), rel(OLD / 'outputs.json'), rel(OLD / 'result.json'),
        rel(BES / 'outputs.json'), rel(BES / 'result.json'), rel(PREP / 'accounting-start.json'))}
    bindings.update({'src/legalmath/' + n: checksum for n, checksum in prior_freeze['production'].items()})
    save(PREP / 'freeze.json', {'bindings': bindings, 'retained_failed_campaign': rel(OLD),
        'production': prior_freeze['production'], 'production_unchanged_since011': True})
    attempts = [e['attempt'] for e in Authority(ROOT).events() if e['kind'] == 'ADMIT' and e['budget_key'] == 'source-authority']
    assert len(attempts) == old['budgets']['source-authority']['maximum_new_attempts'] == 11
    new = deepcopy(old)
    new['revision'] = 383
    task = next(t for t in new['tasks'] if t['id'] == 'source-authority')
    task.update(dossier=PLAN, pre_admission_review=PLAN, build_criteria_scope=[],
        reason='Independently verify existing011 successful consumer outputs under explicit increased cumulative storage allowance, preserving failed011')
    bounds = {'new_measured_seconds': 30, 'conservative_control_seconds': 60,
        'known006plus_seconds': 1900, 'new_bytes': 32 * 1024**2,
        'known006plus_bytes': 448 * 1024**2, 'previous_known006plus_bytes': 384 * 1024**2,
        'failure_reserve_bytes': 2 * 1024**2, 'consumer_reruns': 0, 'builds': 0, 'installs': 0}
    task['retained_consumer_verification'] = {'review': rel(PREP), 'freeze': rel(PREP / 'freeze.json'),
        'failed_attempt_preserved': rel(OLD), 'bounds': bounds, 'retained_admissions': attempts,
        'cumulative_storage_increased_not_reset': True, 'whole_task_complete': False,
        'success_dependencies': {'verify': []}, 'completion_dependencies': {'reconcile': ['verify']}}
    task['inputs'] = sorted(set(task['inputs']) | set(bindings) | {rel(PREP / 'freeze.json')})
    new['budgets']['source-authority']['maximum_new_attempts'] = 12
    routes = read(ROOT / old['continuation_review']['routes'])
    routes['baseline_revision'] = 383
    row = next(r for r in routes['tasks'] if r['task'] == 'source-authority')
    row.update(task_sha256=adigest(task), dossier=PLAN, phase=0,
        remaining='011 campaign failed storage; its successful unchanged consumer outputs await independent verification. Prior384MiB failure is retained.',
        next_action='Run012 retained-evidence verifier once, reconcile/record/refresh and continue original requirements; do not repeat consumers or builds.',
        stop_condition='12 admissions;30+60s/32MiB new;known006+1900s/448MiB explicitly increased storage;old384MiB failure preserved.')
    row = next(r for r in routes['tasks'] if r['task'] == 'source-bes-dep-01')
    row.update(phase=4, remaining='006 source-map/current-consumer requirements review recorded PASS:203cells,304units,9reading refusals and5consumer refusals. Original authenticity/publication/full incorporation unresolved.',
        next_action='Preserve current006; address distinct original historical/incorporation evidence, not another unchanged table or consumer run.')
    save(PREP / 'routes.json', routes)
    new['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    new['continuation_review']['bindings'].update({n: sha(ROOT / n) for n in (PLAN, rel(PREP / 'routes.json'), rel(PREP / 'freeze.json'))})
    assert old['obligations'] == new['obligations'] and old['build_contract'] == new['build_contract']
    proposal = (json.dumps(new, ensure_ascii=False, indent=2) + '\n').encode()
    forecast = resources()['new_bytes'] + 2 * len(proposal) + 3 * 1024**2
    assert forecast < 30 * 1024**2
    assert read(PREP / 'accounting-start.json')['prior_bytes'] + forecast < 446 * 1024**2
    save(PREP / 'proposal.json', new)
    save(PREP / 'review.json', {'baseline': adigest(old), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Independent verification of retained successful011 outputs; no experimental repeat',
            'Explicit cumulative storage amendment384to448MiB with old failed ceiling and all evidence retained',
            'Source01/006 current conditional review recorded; original missing facts remain'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN, 'forecast_new_bytes': forecast,
            'old_failure_not_relabelled': True, 'current_production_unchanged': True},
        'evidence_contract': {'question': 'Do retained011 repaired outputs pass independent substantive checks?',
            'baseline': 'finance013 complete answers/P5, source380reading and original011 package/products',
            'primary': 'Complete source-qualified consumer comparisons and authentic package/test/command evidence',
            'promotion_veto': ['Changed input', 'Lost qualifier', 'Actual worker failed', 'Wrong installed origin', 'Different complete answer'],
            'continuation_veto': ['Corrupt originals', 'Invalid authority', 'New cumulative bound spent'],
            'not_concluded': ['Old campaign compliance', 'Authenticity', 'Succession', 'Whole task/build']},
        'budget_revision': {'budget_key': 'source-authority', 'previous_maximum': 11, 'new_maximum': 12,
            'retained_attempts': attempts, 'reason': 'Changed verification-only recovery; explicit cumulative storage increase preserves prior exceeded bound',
            'next_discriminating_check': 'Independent verification of already executed successful current consumers, no execution repeat',
            'stop_condition': bounds, 'same_scope_authorization': 'User recover and continue with reviewed bounded repairs'}})
    return {'status': 'PREPARED', 'revision': 383, 'resources': resources()}


def verify_outputs():
    authenticated(OLD)
    freeze = read(OLD_PREP / 'freeze.json')
    for name, checksum in freeze['bindings'].items():
        assert sha(ROOT / name) == checksum, name
    for name, checksum in read(evidence.BASE / 'outputs.json').items():
        assert sha(evidence.BASE / name) == checksum, name
    assert read(OLD / 'result.json')['status'] == 'FAIL'
    assert read(OLD / 'stages/installed/failure.json')['reason'] == 'Recovery cumulative storage exhausted'
    assert not (OLD / 'stages/verify/result.json').exists()
    for name in ('tests', 'ordinary', 'package'):
        assert read(OLD / 'stages' / name / 'result.json')['status'] == 'PASS'
    for name in ('tests', 'ordinary', 'wheel', 'install', 'installed'):
        command = read(OLD / 'commands' / (name + '.json'))
        assert command['exit_code'] == 0 and command['failure'] is None
    cases = ET.parse(OLD / 'tests.xml').getroot().findall('.//testcase')
    assert len(cases) == 97 and all(not list(c) for c in cases)
    assert sum(c.attrib['name'].startswith('test_actual_consumer') for c in cases) == 10
    package = read(OLD / 'package.json')
    evidence.same(package['files'], freeze['production'])
    wheel, = (OLD / 'wheel').glob('*.whl')
    assert sha(wheel) == package['wheel_sha256']
    with zipfile.ZipFile(wheel) as archive:
        evidence.same({n.removeprefix('legalmath/'): evidence.hashed(archive.read(n)) for n in archive.namelist()
            if n.startswith('legalmath/') and not n.endswith('/')}, package['files'])
    installed = OLD / 'installed/legalmath'
    evidence.same({str(p.relative_to(installed)): sha(p) for p in installed.rglob('*') if p.is_file()}, package['files'])
    stable = lambda a: {k: v for k, v in a.items() if k not in (
        'contract_source_chain', 'report_sha256', 'consumed_products', 'request_sha256')}
    for mode in ('ordinary', 'installed'):
        summary = read(OLD / (mode + '-summary.json'))
        assert summary['status'] == 'PASS' and summary['whole_task_complete'] is False
        assert [r['id'] for r in summary['cases']] == list(evidence.CASES)
        origins = read(OLD / (mode + '-imports.json'))
        base = ROOT / 'src' if mode == 'ordinary' else OLD / 'installed'
        assert 'legalmath.prospectus.successor.shell_source_chain' in origins
        assert all(Path(p).resolve().is_relative_to(base.resolve()) for p in origins.values())
        for name in evidence.CASES:
            folder = OLD / mode
            products = read(folder / (name + '-products.json.gz'))
            legacy = read(folder / (name + '-legacy-products.json.gz'))
            answer = read(folder / (name + '-answer.json.gz'))
            before = read(folder / (name + '-legacy-answer.json.gz'))
            evidence.same(before, read(evidence.BASE / 'ordinary' / (name + '-answer.json.gz')))
            evidence.same(legacy['P5'], read(evidence.BASE / 'ordinary' / (name + '-P5.json.gz')))
            evidence.same(stable(answer), stable(before))
            evidence.same(answer['questions'], before['questions'])
            evidence.same(products['P5']['payload'], legacy['P5']['payload'])
            evidence.same(products['P2']['payload']['assembly'], legacy['P2']['payload']['assembly'])
            evidence.same(products['P1']['payload']['graph'], legacy['P1']['payload']['graph'])
            evidence.same(answer['contract_source_chain'], products['P2']['payload']['contract_source_chain'])
            evidence.report_check(answer['contract_source_chain'], products['P1']['payload']['graph'])
            assert answer['report_sha256'] == evidence.hashed({k: v for k, v in answer.items() if k != 'report_sha256'})
            assert answer['may_execute_transaction'] is False
            for key, product in products.items():
                assert product['sha256'] == evidence.hashed({k: v for k, v in product.items() if k != 'sha256'})
                assert answer['consumed_products'][key] == product['sha256']
            if mode == 'installed':
                evidence.same(answer, read(OLD / 'ordinary' / (name + '-answer.json.gz')))
                evidence.same(products, read(OLD / 'ordinary' / (name + '-products.json.gz')))
        refusals = summary['cases'][0]['refusals']
        assert [r['id'] for r in refusals] == list(evidence.ADVERSE)
        assert not any(r['refusals'] for r in summary['cases'][1:])
        for row in refusals:
            bad = read(OLD / mode / 'adverse' / (row['id'] + '.json.gz'))
            assert row['input_sha256'] == evidence.hashed(bad) and row['reason']
            if 'P2' in bad:
                assert 'source-chain' in row['reason']
                assert bad['P2']['sha256'] == evidence.hashed({k: v for k, v in bad['P2'].items() if k != 'sha256'})
                assert bad['P3']['inputs']['P2'] == bad['P2']['sha256']
    return {'status': 'PASS', 'cases_per_runtime': 3, 'refusals_per_runtime': 10,
        'tests': 97, 'package_files': len(package['files']), 'source_groups': 8,
        'whole_task_complete': False, 'prior_campaign_status': 'FAIL',
        'functional_evidence_verified': True, 'consumer_reruns': 0, 'package_builds': 0}


def frozen():
    admission = read(HERE / 'admission.json')
    assert adigest(read(AUTH / 'program.json')) == admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec']) == admission['binding']
    for name, checksum in read(PREP / 'freeze.json')['bindings'].items():
        assert sha(ROOT / name) == checksum, name


def run():
    frozen()
    assert resources(1024**2)['execution_allowed']
    assert not (HERE / 'started.json').exists()
    save(HERE / 'started.json', {'pid': os.getpid(), 'time': datetime.now(timezone.utc).isoformat()})
    tick = time.monotonic()
    command = [str(ROOT / '.venv/bin/python'), '-B', '-m',
        'scripts.prospectus_source_chain_retained_verification', 'worker']
    result = None
    error = None
    (HERE / 'commands').mkdir()
    try:
        with (HERE / 'commands/verify.log').open('x') as stream:
            result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                timeout=30, env={**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONDONTWRITEBYTECODE': '1'})
        assert result.returncode == 0, 'Independent evidence verifier failed; inspect retained log'
        frozen()
    except Exception as exc:
        error = {'type': type(exc).__name__, 'reason': str(exc)}
    save(HERE / 'commands/verify.json', {'command': command, 'wall_seconds': time.monotonic() - tick,
        'exit_code': None if result is None else result.returncode, 'error': error})
    if not resources()['execution_allowed'] and error is None:
        error = {'type': 'ResourceLimit', 'reason': 'New explicit bound failed'}
    save(HERE / 'stage-result.json', {'status': 'FAIL' if error else 'PASS', 'error': error})
    return {'status': 'FAIL' if error else 'PASS', 'resources': resources()}


def seal():
    status = read(HERE / 'stage-result.json')['status']
    save(HERE / 'result.json', {'status': status, 'task': 'source-authority',
        'classification': 'RETAINED_REPAIRED_CONSUMER_VERIFICATION', 'prior_campaign_status': 'FAIL',
        'whole_task_complete': False, 'whole_program_complete': False, 'build_criteria_claimed': [],
        'resources': resources()})
    with (HERE / 'RESULT.md').open('x') as stream:
        stream.write(f'''# Retained repaired-consumer evidence: {status}

The independent verifier returned{status}for source011's already executed
ordinary/installed outputs. This new result does not change011's failed storage
campaign or010's wiring failure. No test, consumer, build or installation was
repeated. Production matches011's549-file frozen map.

The required evidence covers97regressions, three complete Shell cases per
runtime, ten actual refusals per runtime, whole legacy finance013answers/P5,
eight contextual source groups, full package/installed bytes and import origins.
See verification.json and the retained command outcome for the actual result.
Printed references, restricted agreement priority and dated trustee contexts
remain distinct from authenticity, first publication or proof of succession.
UNKNOWN source roles and conditional financial answers are preserved.

The cumulative storage allowance was explicitly increased from384to448MiB.
The old exceeded ceiling is retained, not retrospectively passed. New evidence
uses exact original references and small receipts. The1900second cumulative
ceiling remains. Actual resources and earlier unknown costs are in result.json.

| Decision | Primary criterion | Veto | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| {'Retain verified consumer repair' if status == 'PASS' else 'Retain verifier failure'} | Complete independent evidence verification:{status} | Original011storage failure retained; new check recorded | Source authenticity and complete legal applicability | Record/refresh and continue distinct original work | Whole task/build or old campaign compliance |

Post-run red-team: independent structural checking can still share a mistaken
source interpretation. Original contextual anchors permit that reading to be
challenged. This is evidence of a repaired integration error in our code; there
is no established fundamental third-party package defect or stochastic ranking.
''')
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'command': read(HERE / 'commands/verify.json'), 'environment': str(ROOT / '.venv/bin/python'),
        'cpu_gpu': 'CPU; GPU intentionally hidden', 'seeds': 'N/A deterministic',
        'data_version': sha(OLD / 'outputs.json'), 'plan': PLAN, 'result': rel(HERE / 'RESULT.md'),
        'resources': resources()})
    save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*')
        if p.is_file() and '__pycache__' not in p.parts})
    return {'status': 'SEALED', 'candidate_status': status, 'resources': resources()}


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'worker':
        output = verify_outputs()
        save(HERE / 'verification.json', output)
    else:
        output = {'prepare': prepare, 'run': run, 'seal': seal}[action]()
    print(json.dumps(output))
