"""Correct ordinary-answer verification; preserve the frozen279 oracle helpers."""
from copy import deepcopy

from scripts.prospectus_internal_reference_oracle import (
    KEY, expected, independent_closures, questions, retained)
from scripts.prospectus_typed_delta import equal
from legalmath.prospectus.successor.contracts import digest


def ordinary_schema(answer, baseline, *, expected_additions=()):
    assert set(expected_additions) <= {'internal_references'}, 'Unreviewed ordinary schema addition'
    equal(sorted(answer), sorted(set(baseline) | set(expected_additions)),
          'Ordinary answer schema differs from real comparator and reviewed report addition')
    assert not {'source_map', 'assembly', 'selected_contract', 'clause_graph', 'dependencies'} & set(answer), (
        'Ordinary artifact export is disabled')
    equal(answer['report_sha256'], digest({k: v for k, v in answer.items() if k != 'report_sha256'}),
          'Ordinary report hash differs from complete answer')


def verify(p, answer=None, *, missing=()):
    before, old_answer = retained('candidate-answer')
    for stage in ('P1', 'P2'):
        equal(p[stage], before[stage], 'Protected source/construction changed')
    old, got = before['P3']['payload'], p['P3']['payload']
    extra, rows, review = expected(p, missing)
    replaced = {identity + '@' + r['from_use'] for r in rows if r['id'] not in missing
                for identity in r['discovery_ids']}
    wanted = deepcopy([d for d in old['dependencies'] if d['id'] not in replaced
                       and not d['id'].startswith('reference-closure:')]) + extra
    closures = independent_closures(p, wanted)
    wanted += closures
    equal(sorted(got['dependencies'], key=lambda d: d['id']), sorted(wanted, key=lambda d: d['id']),
          'Complete original-source dependencies differ')
    equal(got['questions'], questions(old['questions'], extra, replaced), 'Unexpected semantic question change')
    value = deepcopy(old['interpretation_input'])
    value['reference_admission']['references'].extend(r for r in rows if r['id'] not in missing)
    equal(got['interpretation_input'], value, 'Unexpected internal interpretation input')
    omit = {'dependencies', 'questions', 'interpretation_input'}
    equal({k: v for k, v in got.items() if k not in omit}, {k: v for k, v in old.items() if k not in omit},
          'Unrelated existing meaning changed')
    old_closures = {d['id']: d for d in old['dependencies'] if d['id'].startswith('reference-closure:')}
    closure_delta = {d['id']: {
        'removed': sorted(set(old_closures[d['id']]['unresolved']) - set(d['unresolved'])),
        'added': sorted(set(d['unresolved']) - set(old_closures[d['id']]['unresolved']))} for d in closures}
    for d in closures:
        for field in ('roots', 'reachable'):
            equal(d[field], old_closures[d['id']][field], 'Source roots/reachability changed')
        for entry in closure_delta[d['id']]['removed']:
            assert entry.startswith('Unsupported reference cycle:') or entry in {
                'Unresolved reference: ' + key for key in replaced}
        for entry in closure_delta[d['id']]['added']:
            assert entry.startswith('Unsupported reference cycle:') or entry in {
                'Unresolved reference: ' + e['id'] for e in extra if e['status'] == 'UNRESOLVED'}
    if answer is not None:
        ordinary_schema(answer, old_answer, expected_additions=('internal_references',))
        for stage in ('P4', 'P5'):
            equal(p[stage]['payload'], before[stage]['payload'], 'Legal/financial content changed')
        equal(answer['questions'], questions(old_answer['questions'], extra, replaced), 'Unexpected ordinary questions')
        omit = {'questions', 'consumed_products', 'report_sha256', 'internal_references'}
        equal({k: v for k, v in answer.items() if k not in omit},
              {k: v for k, v in old_answer.items() if k not in omit}, 'Unrelated whole answer changed')
        equal(answer['internal_references'], {
            'status': 'UNREVIEWED' if missing else 'REVIEWED', 'references': rows, 'missing': list(missing),
            'source_documents': review['sources'], 'source_images': review['images'],
            'specification_sha256': digest(review), 'automatic_discovery': False,
            'conservative_cycle_policy': True, 'actual_tax_and_event_application': 'UNKNOWN',
            'complete_reference_graph': False,
            'unknown_target_uses': [KEY + ':p125:l1', KEY + ':p125:l2']}, 'Internal report differs from originals')
        equal(answer['consumed_products'], {k: v['sha256'] for k, v in p.items()}, 'Wrong consumed products')
    return {'status': 'PASS', 'independent_links': 10,
        'target_intervals': [23, 43, 43, 32, 66, 32, 46, 41, 2, 30],
        'closure_diagnostic_delta': closure_delta, 'unknown_target_uses': 2,
        'missing': list(missing), 'complete_answer_checked': answer is not None,
        'ordinary_schema_checked': answer is not None, 'original_task_complete': False}
