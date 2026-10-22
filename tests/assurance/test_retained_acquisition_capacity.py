"""Retained source evidence must survive rebatching without losing duties."""
from copy import deepcopy
from dataclasses import replace
import os
import json

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

import pytest
from jsonschema import ValidationError
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_product import BoundedProduct, PROFILE
from legalmath.interpretation.assurance.phased import retained_acquisition, capacity_policy
from legalmath.interpretation.assurance.monitor import save
from scripts.legal_mission_execution import ref
from scripts.legal_product_completion import run_product
from tests.assurance.test_bounded_product import Scripted, envelope, limits


class NoCalls:
    live = False

    def complete(self, *args, **kwargs):
        raise AssertionError('Retained acquisition must not dispatch')


def setup(root, question='p14'):
    value = envelope()
    value['original_questions'][0]['question_id'] = question
    value['answer_acceptance']['original_questions'] = deepcopy(value['original_questions'])
    value['answer_acceptance']['acceptance_obligations'][0]['question_ids'] = [question]
    value['source_packet']['units'] += [dict(unit_id='source.'+str(i), locator=str(i),
        text='Independent source condition '+str(i)+'.', normative=True, span={}) for i in range(6)]
    bounds = replace(limits(), records_per_request=8, input_tokens=100000, output_tokens=3000)
    old = BoundedProduct(root, root/'old', Scripted(), value, list, limits=bounds)
    acquired = old.investigate()
    assert acquired['question_acquisition_complete'][question]
    product = BoundedProduct(root, root/'new', NoCalls(), value, list, limits=bounds,
        common_capacity_profile=capacity_policy.PROFILE)
    assert len(product.reading_packets()[0]) > len(old.reading_packets()[0])
    return value, bounds, old, product, acquired


def load(root, product, acquired):
    save(root/'acquired.json', acquired)
    return retained_acquisition.load(product, ref(root, 'acquired.json'))


@pytest.mark.parametrize('question', ['p10', 'p14', 'evidence', 'gatecoin'])
def test_actual_entry_accepts_completed_larger_batches_without_dispatch(tmp_path, question):
    value, bounds, old, product, acquired = setup(tmp_path, question)
    save(tmp_path/'acquired.json', acquired)
    result = run_product(tmp_path, tmp_path/'entry', NoCalls(), tmp_path/'jdk',
        '2026-10-21T00:00:00+08:00', sources=[], questions=value['original_questions'],
        acceptance_ref=None, qualification={}, required={'maximum_calls':100},
        deadline_utc='2030-01-01T00:00:00+00:00', selected_tools=[], settings=None,
        consumer_profile=PROFILE, bounded_envelope=value, bounded_encode=list,
        bounded_limits=bounds, bounded_phase='acquire', bounded_execution='phased',
        bounded_acquisition_ref=ref(tmp_path, 'acquired.json'), bounded_phase_admit=lambda *a: {},
        bounded_phase_identity='test', bounded_common_capacity_profile=capacity_policy.PROFILE)
    assert result == acquired
    receipt = json.loads((tmp_path/'entry/retained-acquisition-validation.json').read_text())
    assert receipt['capacity_rebatching']
    assert all(set(row) == {'planned_packet', 'retained_parent'} for row in receipt['capacity_rebatching'])


@pytest.mark.parametrize('mutation', ['missing_reader', 'missing_record', 'source',
    'question_scope', 'duplicate', 'response', 'failure', 'unsettled', 'complete_flag'])
def test_incomplete_or_changed_evidence_is_still_refused(tmp_path, mutation):
    _, _, old, product, acquired = setup(tmp_path)
    row = acquired['outputs'][0]
    if mutation == 'missing_reader':
        acquired['outputs'] = [r for r in acquired['outputs'] if r['request']['reader'] != 'reader-2']
    elif mutation == 'missing_record':
        r = row['request']
        packet = old.route.make_packet(r['task'], [s['id'] for s in r['records'][1:]],
            reader=r['reader'], question_ids=[q['question_id'] for q in r['original_questions']])
        row.update(packet_hash=packet['packet_hash'], request=packet['request'])
        row['result']['value']['records'].pop(0)
    elif mutation == 'source':
        row['request']['records'][0]['text'] += ' Changed.'
    elif mutation == 'question_scope':
        row['request']['original_questions'][0]['text'] += ' Different question.'
    elif mutation == 'duplicate':
        acquired['outputs'].append(deepcopy(row))
    elif mutation == 'response':
        row['result']['value']['records'].pop()
    elif mutation == 'failure':
        row['result'] = dict(status='FAILED', error='E_PROVIDER', reason='Original failure retained')
    elif mutation == 'unsettled':
        row['result'] = dict(status='RESERVED')
    else:
        acquired['question_acquisition_complete']['p14'] = False
    with pytest.raises((LegalMathError, ValidationError)):
        load(tmp_path, product, acquired)


def test_rebatched_failed_parent_still_requires_all_recovery_children(tmp_path):
    _, _, old, product, acquired = setup(tmp_path)
    parent = acquired['outputs'][0]
    original_result = deepcopy(parent['result'])
    parent['result'] = dict(status='FAILED', error='E_PROVIDER', reason='Parent failed')
    request = parent['request']
    records = request['records']
    for group in (records[:4], records[4:]):
        packet = old.route.make_packet(request['task'], [r['id'] for r in group],
            reader=request['reader'], question_ids=[q['question_id'] for q in request['original_questions']])
        result = deepcopy(original_result)
        result['value']['records'] = [r for r in result['value']['records'] if r['id'] in {s['id'] for s in group}]
        acquired['outputs'].append(dict(request=packet['request'], packet_hash=packet['packet_hash'],
            result=result, recovery_of=0))
    assert load(tmp_path, product, acquired) == acquired
    acquired['outputs'].pop()
    with pytest.raises(LegalMathError):
        load(tmp_path, product, acquired)


def test_joint_bridge_cannot_be_replaced_by_separate_record_readings(tmp_path, monkeypatch):
    _, _, old, product, acquired = setup(tmp_path)
    sources = [r['id'] for r in old.route.records.values() if r['kind'] == 'source'][:2]
    bridge = old.route.make_packet('REVIEW_SOURCE_DEPENDENCY', sources,
        dependency={'id':'distant-exception', 'reason':'Interpret the rule and exception jointly.'})
    planned, blocked = product.reading_packets()
    monkeypatch.setattr(product, 'reading_packets', lambda: (planned+[bridge], blocked))
    with pytest.raises(LegalMathError):
        load(tmp_path, product, acquired)
    acquired['outputs'].append(dict(packet_hash=bridge['packet_hash'], request=bridge['request'],
        result=dict(status='VALIDATED', value=Scripted().complete(bridge['request'], bridge['schema'], None).value)))
    assert load(tmp_path, product, acquired) == acquired

