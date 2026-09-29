from copy import deepcopy
import pytest

from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.controls import routing_plan
from legalmath.interpretation.assurance.fidelity_batches import FidelityBatches
from legalmath.interpretation.assurance.lowering import lower


def packet():
    return {'source_key': 'fixture.str', 'authority': 'RETAINED_SOURCE', 'selected_slice': 'str',
            'family_ids': ['fixture'], 'dependencies': [], 'units': [
                {'unit_id': 'u0', 'locator': 'p1', 'text': 'An e-Cert is required for this submission.',
                 'normative': True, 'span': None},
                {'unit_id': 'u1', 'locator': 'p2', 'text': 'A report submitted through another channel must be resubmitted.',
                 'normative': True, 'span': None}]}


def quote(unit, text):
    return [{'unit_id': unit, 'quote': text}]


def controls():
    return [
        {'control_id': 'ecert.applicability', 'question': 'Is an e-Cert required?',
         'unit_of_assessment': 'submission method', 'actor': 'licensed firm',
         'temporal_basis': 'submission time', 'result_kind': 'REQUIREMENT_APPLIES',
         'true_means': 'the e-Cert requirement applies', 'false_means': 'the requirement does not apply',
         'source_evidence': quote('u0', 'An e-Cert is required for this submission.')},
        {'control_id': 'resubmission.trigger', 'question': 'Is resubmission triggered?',
         'unit_of_assessment': 'original report event', 'actor': 'licensed firm',
         'temporal_basis': 'after implementation', 'result_kind': 'DUTY_TRIGGER',
         'true_means': 'the resubmission duty is triggered', 'false_means': 'the duty is not triggered',
         'source_evidence': quote('u1', 'A report submitted through another channel must be resubmitted.')},
    ]


def reading(local_id, statement, meaning, formal=None):
    return {'local_id': local_id, 'family': 'dependencies', 'subject': 'submission',
            'statement': '[' + meaning + '] ' + statement, 'distinction': 'typed',
            'citations': quote('u0', 'An e-Cert is required for this submission.'),
            'assumptions': [], 'questions': [], 'formalization': formal}


def assignment(item, control, status='ASSIGNED'):
    return {'item_id': item, 'control_ids': [control] if status == 'ASSIGNED' else [],
            'status': status, 'evidence': quote('u0', 'An e-Cert is required for this submission.'),
            'reason': 'typed control assignment'}


def test_routing_keeps_distinct_controls_and_unresolved_candidate():
    p = packet(); cs = controls()
    claims = [{'claim_id': 'claim.ecert', 'kind': 'OBLIGATION', 'actor': 'firm', 'action': 'submit',
               'modality': 'MUST', 'conditions': [], 'exceptions': [], 'temporal': [],
               'statement': 'e-Cert required', 'relevance': 'CONTROL', 'evidence': quote('u0', 'An e-Cert is required for this submission.'), 'uncertainty': []},
              {'claim_id': 'claim.resubmit', 'kind': 'OBLIGATION', 'actor': 'firm', 'action': 'resubmit',
               'modality': 'MUST', 'conditions': [], 'exceptions': [], 'temporal': [],
               'statement': 'resubmit', 'relevance': 'CONTROL', 'evidence': quote('u1', 'A report submitted through another channel must be resubmitted.'), 'uncertainty': []}]
    candidates = {
        'cand.ecert': reading('cand.ecert', 'e-Cert requirement applies.', 'TRUE_IS_SATISFIED'),
        'cand.mixed': reading('cand.mixed', 'both e-Cert and resubmission.', 'TRUE_IS_SATISFIED'),
    }
    route = {'candidates': [assignment('cand.ecert', 'ecert.applicability'), assignment('cand.mixed', 'ecert.applicability')],
             'claims': [assignment('claim.ecert', 'ecert.applicability'), assignment('claim.resubmit', 'resubmission.trigger')],
             'missing_questions': []}
    other = deepcopy(route)
    other['candidates'][1] = assignment('cand.mixed', 'resubmission.trigger')
    plan = routing_plan(p, claims, candidates, cs, [route, other])
    assert plan['bindings']['candidates']['cand.mixed']['status'] == 'UNRESOLVED'
    assert ['claim.ecert', 'cand.mixed'] in plan['required_pairs']
    assert plan['legal_completeness_established'] is False


def test_fidelity_batches_split_and_never_drop_pairs(tmp_path):
    ledger = FidelityBatches(tmp_path / 'batches.json', [('c1', 'r1'), ('c1', 'r2'), ('c2', 'r1')], batch_size=2)
    first = ledger.batches()[0]
    assert len(first) == 2
    ledger.record('b0', first, status='FAILED')
    halves = ledger.split(first)
    ledger.record('b1', halves[0]); ledger.record('b2', halves[1])
    ledger.record('b3', [('c2', 'r1')])
    assert ledger.report()['status'] == 'COMPLETE'
    with pytest.raises(LegalMathError):
        ledger.record('duplicate', [('c1', 'r1')])


def test_syntax_lowering_retains_original_uncertainty():
    formal = {'facts': [{'name': 'ecert', 'type': 'bool', 'meaning': 'e-Cert exists', 'unit': 'submission',
                         'source_unit_ids': ['u0'], 'requires_judgment': True}], 'scope': 'true',
              'result': 'ecert', 'result_type': 'bool'}
    original = reading('r1', 'e-Cert requirement is unresolved.', 'TRUE_IS_SATISFIED', formal)
    original['questions'] = ['whether the method is one covered by footnote 3']
    record = lower(original, {'original_hash': digest(original), 'scope': 'true', 'result': 'ecert',
                              'explanation': 'grammar only', 'additional_uncertainty': []}, packet(), '2026-02-03T00:00:00.000000Z')
    assert record['original']['questions'] == original['questions']
    assert record['reading']['formalization']['facts'] == original['formalization']['facts']
