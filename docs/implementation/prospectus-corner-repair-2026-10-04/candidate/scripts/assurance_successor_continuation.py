"""A reviewed interrupted investigation can continue without erasing its history."""
from pathlib import Path
import xml.etree.ElementTree as ET
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.integration_contract import read_evidence
from run_assurance_successor import read, sha


LIMITS = {'grant_calls': 500, 'study_stop': 460, 'arm_calls': 120,
          'scoped_rounds': 2, 'pair_perspective_calls': 6,
          'inventory_unit_calls': 3, 'legacy_pair_calls': 4,
          'original_question_deadline_seconds': 86400}


def reviewed_continuation(directory, root, grant, scheduling):
    path = Path(directory) / 'continuation-amendment-001.json'
    if not path.exists():
        return scheduling
    if not scheduling:
        raise LegalMathError('E_AUTHORITY', details='A continuation needs its reviewed scheduling basis')
    value = read(path)
    if (value.get('profile') != 'bounded-investigation-continuation.v1' or
            value.get('limits') != LIMITS or value.get('refund_reservations') is not False or
            value.get('grant_sha256') != sha(grant) or
            value.get('scheduling_receipt') != scheduling.get('receipt')):
        raise LegalMathError('E_AUTHORITY', details='Changed continuation authority or limits')
    read_evidence(value['review'], root, json_value=False)
    xml = read_evidence(value['focused_tests'], root, json_value=False)
    tree = ET.fromstring(xml)
    suites = [tree] if tree.tag == 'testsuite' else list(tree)
    if not sum(int(s.get('tests', '0')) for s in suites) or any(
            int(s.get(k, '0')) for s in suites for k in ('failures', 'errors', 'skipped')):
        raise LegalMathError('E_AUTHORITY', details='Continuation checks did not pass')
    failed = read_evidence(value['failed_phase'], root)
    if failed.get('phase') != 'S8' or failed.get('status') != 'FAILED':
        raise LegalMathError('E_JOB_STATE', details='Continuation requires a terminal failed study')
    frozen = read_evidence(value['source_freeze'], root)
    allocation = read_evidence(value['allocation'], root)
    if allocation['shared_source_freeze_sha256'] != value['source_freeze']['sha256']:
        raise LegalMathError('E_INTEGRITY', details='Original shared source freeze changed')
    if value.get('study_result'):
        result = read_evidence(value['study_result'], root)
        if (result.get('execution_complete') is not False or
                failed.get('outputs', {}).get(value['study_result']['path']) != value['study_result']['sha256'] or
                result['allocation']['shared_source_freeze_sha256'] != value['source_freeze']['sha256'] or
                {t['task_id'] for t in result['tasks']} != {t['task_id'] for t in frozen['tasks']} or
                len(result['tasks']) != len(frozen['tasks'])):
            raise LegalMathError('E_INTEGRITY', details='Terminal study result or denominator changed')
    elif failed.get('error') != 'CONTROLLED_IMPLEMENTATION_REPAIR_HALT':
        raise LegalMathError('E_JOB_STATE', details='An incomplete stop needs the owned-worker halt receipt')
    receipt = {'path': str(path), 'sha256': sha(path)}
    return {**scheduling, 'prior_continuation_id': scheduling['continuation_id'],
            'continuation_id': 'reviewed-repair.' + receipt['sha256'],
            'continuation_amendment': receipt, 'study_promotion': False}
