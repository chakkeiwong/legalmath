"""Read-only exact question coverage diagnosis for the exhausted saved response."""
from collections import Counter
import assurance_evidence_core as c
import assurance_evidence_continuation as run
import assurance_evidence_protocol as protocol


def report(root):
    path = root/run.RUN/'tasks/propagation.exception-challenger.007205b81b17778be99277e7/attempt-01'
    task = c.read(path/'task.json')
    raw = c.read(path/'result.json')['rejected_value']
    _, _, aliases = protocol.transport(task)
    actual = [q for group in raw['questions'] for q in group['ids']]
    counts = Counter(actual)
    return {'calls_used': run.Allowance(root).verify()['used'],
        'expected_questions': len(aliases['questions']), 'returned_ids': len(actual), 'unique_returned_ids': len(counts),
        'missing': [{'alias': q, **v} for q,v in aliases['questions'].items() if q not in counts],
        'duplicate_ids': {q:n for q,n in counts.items() if n != 1},
        'foreign_ids': sorted(set(actual)-set(aliases['questions']))}


def repair(root):
    c.fail('E_AUTHORITY', 'Coverage diagnosis cannot invent omitted dispositions')
