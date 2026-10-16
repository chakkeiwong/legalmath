"""Bounded read-only diagnosis of the saved group-recovery candidate."""
import assurance_evidence_core as c
import assurance_evidence_continuation as run
import assurance_evidence_protocol as protocol
from assurance_evidence_group_recovery import repair


def report(root):
    work = root/run.RUN
    path = work/'tasks/propagation.exception-challenger.007205b81b17778be99277e7/attempt-01'
    task = c.read(path/'task.json')
    row = c.read(path/'result.json')
    raw = row['rejected_value']
    wire, schema, aliases = protocol.transport(task)
    value = {'calls_used': run.Allowance(root).verify()['used'], 'response_keys': list(raw),
             'obligations_required': len(task['request']['obligations'])}
    try:
        result = protocol.validate(raw, task, aliases)
        value.update(validation='PASS', reading_reviews=len(result['reading_updates']))
    except c.LegalMathError as exc:
        value.update(validation='FAILED', error=exc.code, details=exc.details)
    return value
