"""Reconcile source09 scope and test changed English report applicability."""
from copy import deepcopy
import gzip
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT), str(ROOT / 'tests/prospectus_successor')]
sys.dont_write_bytecode = True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.prospectus.successor import service, report_scope, statement_cells
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.execution_authority import Authority, file_hash
from scripts.prospectus_2010_capital_product_cases import read, original, configure
from test_successor import request
from test_report_scope import products

AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
SOURCE = AUTH / 'attempts/source-bes-dep-09'
FAILED = ROOT / '.localresources/prospectus-preparation/annual-scope-review'
OUT = ROOT / '.localresources/prospectus-preparation/annual-scope-review-recovery'
SELF = 'scripts/prospectus_annual_scope_probe.py'
PLAN = 'docs/plans/prospectus-annual-scope-review-2026-10-22.md'
PRIOR_BYTES = 224145462
PRIOR_SECONDS = 1576.1191290449352
LIMIT_BYTES = min(32 * 1024**2, 220 * 1024**2 - PRIOR_BYTES - 512 * 1024)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def save(name, value):
    data = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()
    if name.endswith('.gz'):
        data = gzip.compress(data, mtime=0)
    used = sum(p.stat().st_size for folder in (FAILED, OUT) for p in folder.rglob('*') if p.is_file())
    used += sum((ROOT / n).stat().st_size for n in (SELF, PLAN))
    require(used + len(data) + 1024**2 < LIMIT_BYTES, 'Review cumulative storage reserve')
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


def scope_check(required, selected, covered, source_available, all_notes_read):
    require(required == set([92, 94, 96, 190, 191]) | set(range(97, 188)), 'Original96page requirement changed')
    require(len(required) == 96 and required <= source_available, 'Original selected page unavailable')
    missing = sorted(required - covered)
    require(not all_notes_read or not missing, 'Missing notes cannot be called complete')
    return {'check': 'annual2010-original-scope.v1', 'required_pages': sorted(required),
            'profile_pages': sorted(selected), 'report_pages': [190, 191],
            'uninterpreted_required_pages': missing, 'all_notes_read': all_notes_read,
            'task_complete': not missing and all_notes_read,
            'page_presence_is_interpretation': False}


def changed_values(before, after, path=()):
    if before == after:
        return []
    if isinstance(before, dict) and isinstance(after, dict) and before.keys() == after.keys():
        return [row for key in before for row in changed_values(before[key], after[key], path + (key,))]
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        return [row for i, value in enumerate(before) for row in changed_values(value, after[i], path + (i,))]
    return [{'path': list(path), 'value': after}]


def retain_actual_answer(answer, baseline, expected, old):
    changes = changed_values(baseline, answer)
    reconstructed = deepcopy(baseline)
    for row in changes:
        require(row['path'], 'Whole answer replacement exceeds reviewed storage representation')
        target = reconstructed
        for key in row['path'][:-1]:
            target = target[key]
        target[row['path'][-1]] = row['value']
    require(reconstructed == answer, 'Actual answer delta does not reconstruct completely')
    save('current-annual-answer-delta.json.gz', {
        'baseline': {'path': str(old.relative_to(ROOT)), 'sha256': file_hash(old)},
        'baseline_replacements': {'path': str((SOURCE / 'attempt-012/answer-delta.json.gz').relative_to(ROOT)),
                                  'sha256': file_hash(SOURCE / 'attempt-012/answer-delta.json.gz')},
        'expected_original_answer_sha256': expected['answer_sha256'],
        'actual_answer_sha256': digest(answer), 'changes': changes,
        'complete_reconstruction_equal': True})


def annual_reconciliation():
    auth = Authority(ROOT)
    p, _, _ = auth.spec()
    require(p['revision'] == 438, 'Current438required')
    event = next(e for e in reversed(auth.events()) if e.get('attempt') ==
                 str((SOURCE / 'attempt-014').relative_to(ROOT)) and e['kind'] == 'RECORD')
    require(auth.retained_evidence_valid(event), 'Recorded014evidence changed')
    configure(ROOT, SOURCE / 'attempt-012')
    ps = original()
    delta = read(SOURCE / 'attempt-012/after-delta.json.gz')
    for phase, addition in delta['payload_additions'].items():
        target = ps[phase]['payload']['request'] if phase == 'P1' else ps[phase]['payload']
        require(not set(target) & set(addition), 'Existing annual addition')
        target.update(addition)
    from scripts.prospectus_2010_annual_cases import reseal
    reseal(ps)
    require({k: v['sha256'] for k, v in ps.items()} == delta['expected_hashes'], 'Original012product identities changed')
    answer = service.consume(ps, ROOT, mode='frozen', include_artifacts=True)
    expected = read(SOURCE / 'attempt-012/answer-delta.json.gz')
    old = ROOT / expected['baseline']['path']
    require(file_hash(old) == expected['baseline']['file_sha256'], 'Annual baseline bytes changed')
    complete = {**read(old), **expected['replacements']}
    retain_actual_answer(answer, complete, expected, old)
    require(answer == complete and digest(answer) == expected['answer_sha256'], 'Complete original capital answer changed')
    ids = {d['id'] for d in ps['P1']['payload']['request']['bundle']['dependencies']}
    deps = {d['id']: d for d in answer['dependencies']}
    require(len(ids) == 14 and all(deps[k]['status'] == 'UNRESOLVED' for k in ids), 'Original dependencies changed')
    require(answer['questions']['Q3']['status'] == 'PARTIAL' and not answer['may_execute_transaction'] and
            not answer['independent_legal_acceptance'], 'Unsupported original legal promotion')
    cells = answer['source_statement_cells']
    selected = set(cells['source_context']['source_pages'])
    required = set([92, 94, 96, 190, 191]) | set(range(97, 188))
    available = {u['page'] for u in ps['P1']['payload']['graph']['units'] if u['document'] == 'bes-2010-en'}
    proof = scope_check(required, selected, selected | {190, 191}, available, cells['source_context']['all_notes_read'])
    # A page can contain context alongside a reading. This is a lower bound on
    # missing interpretation, never a claim that all content on other pages was read.
    proof['page_coverage_overstates_semantic_coverage'] = True
    proof['whole_original_answer_equal'] = True
    proof['answer_sha256'] = digest(answer)
    proof['original_dependencies_unresolved'] = len(ids)
    proof['report_roles'] = [{'id': r['id'], 'status': r['status'],
                             'identity': r['facts']['identity'].get('value'),
                             'date': r.get('english_report_context', {}).get('normalized_closing_date')}
                            for r in answer['source_reports']]
    caught = []
    for label, args in [
        ('false-all-notes', (required, selected, selected | {190, 191}, available, True)),
        ('weakened-original-range', (required - {100}, selected, selected | {190, 191}, available, False)),
        ('missing-source-page', (required, selected, selected | {190, 191}, available - {100}, False)),
    ]:
        try:
            scope_check(*args)
        except ValueError:
            caught.append(label)
        else:
            raise ValueError('Scope checker accepted: ' + label)
    proof['checker_controls'] = caught
    save('coverage.json', proof)
    reports = ps['P2']['payload']['source_report_readings']['reports']
    return reports, proof


def derivative(body, folder, kind):
    folder.mkdir(parents=True)
    req = request(folder, [body])
    req.pop('assembly')
    req.pop('scope')
    graph = service.source_product(req, folder)['payload']['graph']
    text = '\n'.join(u['raw'] for u in graph['units'])
    review = {'kind': 'DEVELOPMENT', 'reviewer': 'source09 applicability falsification',
              'reason': 'Derivative text input; not an issuer document or independent legal opinion'}
    req['source_report_readings'] = {'version': 'source-report-readings.v1', 'graph_sha256': digest(graph),
        'review': review, 'reports': [{'id': 'report', 'document': 'd',
            'source_sha256': req['bundle']['documents'][0]['sha256'],
            'pages': [{'page': 1, 'mode': 'raw'}], 'text_sha256': digest(text.encode())}]}
    p1 = service.source_product(req, folder)
    p2 = service.construction_product(p1, folder)
    selected = p2['payload']['source_report_readings']
    # Exact short spans make the category internally consistent while plainly
    # insufficient as substantive report support. Complete facts are not UNKNOWN.
    first = next(u['raw'] for u in graph['units'] if u['raw'].strip())
    start = text.index(first)
    span = {'start': start, 'end': start + len(first), 'quote': first}
    facts = {k: {'status': 'UNKNOWN', 'reason': 'No external authority supplied'} for k in report_scope.FACTS}
    codes = {'identity': kind, **report_scope.PROFILES[kind]}
    for name in report_scope.FACTS - report_scope.EXTERNAL:
        facts[name] = {'status': 'SUPPLIED', 'spans': [span], **({'value': codes[name]} if name in codes else {})}
    if kind == 'COMMITTEE_REPORT':
        facts['assurance_level'] = {'status': 'UNKNOWN', 'reason': 'Committee assurance not established'}
    if kind == 'UNAUDITED_FINANCIAL_RELEASE':
        facts['conclusion'] = {'status': 'UNKNOWN', 'reason': 'No independent opinion in issuer release'}
    scope = {'version': 'source-report-scope.v1', 'readings_sha256': digest(selected), 'review': review,
             'reports': [{'id': 'report', 'reading_sha256': selected['reports'][0]['sha256'], 'facts': facts}]}
    return p1, p2, scope


def main():
    tick = time.monotonic()
    require(not OUT.exists(), 'No unchanged review retry')
    failure = read(FAILED / 'failure.json')
    require(failure['error'] == "ValueError('Review cumulative storage reserve')", 'Expected retained storage failure required')
    OUT.mkdir(parents=True)
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('90second review ceiling')))
    signal.alarm(90)
    reports, proof = annual_reconciliation()
    results = []
    for report in reports:
        text = report['text']
        if report['id'] == 'statutory-2010':
            altered = text.replace('AUDITORS’ REPORT CONSOLIDATED FINANCIAL STATEMENTS',
                                   'STATUTORY AUDITOR REPORT ON CONSOLIDATED FINANCIAL STATEMENTS', 1)
        else:
            altered = text.replace('REPORT OF THE AUDIT COMMITTEE FOR THE YEAR 2010',
                                   'AUDIT COMMITTEE REPORT FOR THE YEAR 2010', 1)
        require(altered != text, 'Title mutation had no effect')
        for label, body in [('exact-title', text), ('paraphrased-title', altered)]:
            for kind in ('STATUTORY_FINANCIAL_AUDIT', 'COMMITTEE_REPORT', 'LIMITED_SUSTAINABILITY_ASSURANCE'):
                name = report['id'] + '-' + label + '-' + kind
                p1, p2, scope = derivative(body, OUT / 'inputs' / name, kind)
                packet = {'P1': p1, 'P2': p2, 'scope': scope, 'original_reading': report['id'],
                          'variant': label, 'category': kind, 'issuer_original': False}
                try:
                    answer = service.consume(products(p1, p2, scope), ROOT, mode='current', include_artifacts=True)
                    packet['answer'] = answer
                    r = answer['source_reports'][0]
                    supported = any(v == 'SUPPLIED_SOURCE_SUPPORT' for v in r['use_assessment'].values())
                    row = {'case': name, 'refused': False, 'status': r['status'], 'false_support': supported,
                           'context_applied': 'english_report_context' in r, 'use_assessment': r['use_assessment']}
                except ValueError as exc:
                    packet['error'] = str(exc)
                    row = {'case': name, 'refused': True, 'reason': str(exc), 'false_support': False}
                save('packets/' + name + '.json.gz', packet)
                results.append(row)
    count = sum(r['false_support'] for r in results)
    save('result.json', {'status': 'DEFECT_REPRODUCED' if count else 'NO_DEFECT_REPRODUCED',
        'false_support_cases': count, 'cases': results, 'coverage': proof,
        'seconds': time.monotonic() - tick, 'previous_stage_seconds': PRIOR_SECONDS,
        'failed_review_seconds': failure['seconds'], 'changed_recovery_consumed': True,
        'previous_bytes': PRIOR_BYTES, 'current_bound_bytes': LIMIT_BYTES,
        'method_sha256': file_hash(ROOT / SELF), 'plan_sha256': file_hash(ROOT / PLAN),
        'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1', 'seeds': 'N/A deterministic'})
    signal.alarm(0)
    print(json.dumps({'status': 'DEFECT_REPRODUCED' if count else 'NO_DEFECT_REPRODUCED',
        'false_support_cases': count, 'missing_required_pages': len(proof['uninterpreted_required_pages']),
        'seconds': time.monotonic() - tick}), flush=True)


if __name__ == '__main__':
    started = time.monotonic()
    try:
        main()
    except Exception as exc:
        save('failure.json', {'status': 'FAIL', 'error': repr(exc), 'seconds': time.monotonic() - started})
        raise
