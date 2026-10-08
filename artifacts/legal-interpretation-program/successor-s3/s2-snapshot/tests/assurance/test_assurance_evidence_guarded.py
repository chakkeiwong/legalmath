from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
import assurance_evidence_guarded as g
import assurance_evidence_operations as ops
from legalmath.canonical import digest
from legalmath.errors import LegalMathError

FORMAL = {'facts': [{'name': n, 'type': 'bool'} for n in ('scope', 'responsibility_retained', 'arrangement_sound', 'ownership_records_proper')],
    'scope': 'scope', 'result': '(and responsibility_retained arrangement_sound ownership_records_proper)', 'result_type': 'bool'}
CID = 'deferred.744c4b5d99bc07afffce029b'
EVIDENCE = {'synthetic.case-basis': {'path': 'test-fixture', 'sha256': '0'*64}}


def evaluate(case, role='structure-reader'):
    return g.evaluate(FORMAL, case, role=role, reading_id=CID, evidence=EVIDENCE, check_reference=lambda r: None)


def test_complete_judgments_preserve_value_but_not_a_compliance_claim():
    value = evaluate(g.synthetic_case(FORMAL, CID))
    assert value['status'] == 'CONDITIONAL_PREDICATE_TRUE' and value['value'] is True
    assert value['modality'] == 'SHOULD' and value['program_hash'] == digest(FORMAL)
    assert value['legal_correctness'] == 'NOT_ESTABLISHED' and not value['release_eligible']


@pytest.mark.parametrize('state', ['unknown', 'conflict'])
def test_incomplete_classification_never_becomes_false_or_true(state):
    case = g.synthetic_case(FORMAL, CID)
    case['facts']['ownership_records_proper'] = {'status': state}
    value = evaluate(case)
    assert value['status'] == 'UNRESOLVED' and value['value'] is None and not value['evaluated']


def test_partial_false_is_bound_to_the_one_reviewed_identity():
    case = g.synthetic_case(FORMAL, CID)
    case['facts']['responsibility_retained']['value'] = False
    case['facts']['arrangement_sound'] = {'status': 'unknown'}
    assert evaluate(case)['status'] == 'UNRESOLVED'
    assert evaluate(case, 'exception-challenger')['status'] == 'CONDITIONAL_PREDICATE_FALSE'
    case['facts']['responsibility_retained']['evidence_ids'] = []
    assert evaluate(case, 'exception-challenger')['status'] == 'UNRESOLVED'


def test_ownership_conflict_blocks_dependent_classification_only():
    case = g.synthetic_case(FORMAL, CID)
    case['ownership_inventory']['reconciliation'] = {'status': 'conflict'}
    assert evaluate(case)['status'] == 'UNRESOLVED'
    case['facts']['responsibility_retained']['value'] = False
    result = evaluate(case, 'exception-challenger')
    assert result['value'] is False and result['unresolved_classifications']


def test_scope_false_prevents_vacuous_satisfaction_even_with_missing_body():
    case = g.synthetic_case(FORMAL, CID)
    case['facts']['scope']['value'] = False
    case['facts']['arrangement_sound'] = {'status': 'unknown'}
    value = evaluate(case)
    assert value['status'] == 'OUT_OF_SCOPE' and value['value'] is None and not value['evaluated']


@pytest.mark.parametrize('change', ['period', 'basis', 'context', 'applicability', 'hypothesis', 'missing-receipt'])
def test_missing_prerequisite_prevents_evaluation(change):
    case = g.synthetic_case(FORMAL, CID)
    if change == 'period': case['context']['start'] = ''
    if change == 'basis': case['facts']['responsibility_retained']['basis'] = ''
    if change == 'context': case['facts']['responsibility_retained']['context_hash'] = 'foreign'
    if change == 'applicability': case['applicability'] = {'status': 'unknown'}
    if change == 'hypothesis': case['interpretation'] = None
    if change == 'missing-receipt': case['facts']['responsibility_retained']['evidence_ids'] = ['missing']
    assert evaluate(case)['status'] == 'UNRESOLVED'


def test_receipt_tampering_stops_instead_of_creating_a_classification():
    def changed(ref): raise LegalMathError('E_INTEGRITY')
    with pytest.raises(LegalMathError) as error:
        g.evaluate(FORMAL, g.synthetic_case(FORMAL, CID), role='structure-reader', reading_id=CID,
            evidence=EVIDENCE, check_reference=changed)
    assert error.value.code == 'E_INTEGRITY'


def test_requests_approval_performance_and_remediation_do_not_substitute_for_retention():
    case = g.synthetic_case(FORMAL, CID)
    case['facts']['responsibility_retained']['value'] = False
    case['auxiliary'].update(sfc_request=False, approval=True, record_performance=True, remediation=True)
    assert evaluate(case)['value'] is False
    case['facts']['responsibility_retained'] = {'status': 'unknown'}
    assert evaluate(case)['status'] == 'UNRESOLVED'


def test_false_and_missing_evidence_are_distinct_and_schema_is_strict():
    case = g.synthetic_case(FORMAL, CID)
    case['facts']['responsibility_retained'] = {'status': 'unknown', 'value': False}
    with pytest.raises(LegalMathError) as error:
        evaluate(case)
    assert error.value.code == 'E_SCHEMA'


def test_contrary_case_suite_covers_every_fact_and_total_valuation():
    checks = g.program_checks(FORMAL, role='exception-challenger', reading_id=CID,
        evidence=EVIDENCE, check_reference=lambda r: None)
    assert len([x for x in checks if x['case_id'].startswith('total-valuation-')]) == 16
    assert all(any(x['case_id'] == f['name']+'-conflict' for x in checks) for f in FORMAL['facts'])


def test_operations_rejects_unknown_action_before_any_execution(tmp_path):
    with pytest.raises(LegalMathError) as error:
        ops.entry(tmp_path, tmp_path, 'arbitrary-command')
    assert error.value.code == 'E_AUTHORITY'


def test_operations_policy_passes_exact_master_command_gate():
    root = Path('/home/chakwong/python/legalmath')
    policy = {'commands': ops.expected_commands(root), 'requested_prefix': ops.ex.PREFIX}
    assert ops.ex.master.check_command(policy, ops.ex.PREFIX+['ops-run'])
    with pytest.raises(LegalMathError) as error:
        ops.ex.master.check_command(policy, ops.ex.PREFIX+['ops-run', 'arbitrary-extra'])
    assert error.value.code == 'E_AUTHORITY'


def test_foreign_guarded_receipt_is_rejected_even_with_matching_hash(tmp_path):
    import assurance_evidence_core as c
    path = tmp_path/'elsewhere/completion-receipt.json'
    c.save(path, {'files': [], 'inputs': []})
    with pytest.raises(LegalMathError) as error:
        g.verify(tmp_path, c.receipt(path, tmp_path))
    assert error.value.code == 'E_INTEGRITY'
