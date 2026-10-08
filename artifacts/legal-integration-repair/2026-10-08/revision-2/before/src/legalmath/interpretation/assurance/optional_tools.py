"""Optional checks at validated product stages, retained independently of models.

Backends compute diagnostics on supplied inputs. Their output is fallible data;
neither a successful check nor its inclusion in a prompt proves a legal premise.
"""
from copy import deepcopy
from pathlib import Path

from ...canonical import digest, loads
from ...errors import LegalMathError
from ..contracts import parse
from ..search.models import Reading
from .arguments import evaluate_criticism
from .workflow import EvidenceJournal

PROFILE = 'legalmath.optional-product-tools.v1'


def report(directory):
    """Recompute the summary from retained checks, including artifact hashes."""
    path = Path(directory)/'journal.json'
    if not path.exists():
        return {'profile': PROFILE, 'checks': [], 'prepared_requests': 0,
                'execution_complete': False, 'legal_premises_established': False}
    binding = loads(path.read_bytes())['value']['binding']
    journal = EvidenceJournal(directory, binding['inputs'],
        **{k: binding[k] for k in ('maximum_actions', 'maximum_per_issue', 'deadline_seconds')})
    state = journal.report()
    checks = []
    for a in state['actions']:
        if a['spec']['stage'] != 'tool-check':
            continue
        if a['status'] == 'EXECUTED':
            value = loads((journal.directory/a['result_file']).read_bytes())
            checks.append({'key': a['key'], 'result_hash': a['result_hash'], **value})
        else:
            checks.append({'key': a['key'], 'status': a['status'],
                           'inputs': a['spec']['inputs']})
    return {'profile': PROFILE, 'checks': checks,
            'prepared_requests': sum(a['spec']['stage'] == 'prepare-request' for a in state['actions']),
            'execution_complete': bool(checks) and all(c['status'] in ('PASS', 'UNSUPPORTED') for c in checks),
            'legal_premises_established': False}


class ToolSession:
    def __init__(self, backend, directory):
        self.backend = backend
        self.identity = deepcopy(backend.identity())
        self.directory = Path(directory)
        self.journal = EvidenceJournal(self.directory, {'profile': PROFILE, 'backend': self.identity},
                                       maximum_actions=200, maximum_per_issue=1, deadline_seconds=86400)
        self.journal.report()

    def _check(self, kind, packet, inputs):
        if self.backend.identity() != self.identity:
            raise LegalMathError('E_STALE_REVIEW', details='Optional tool implementation changed')
        binding = {'kind': kind, 'packet_hash': digest(packet), 'inputs_hash': digest(inputs)}
        # A failed or reserved tool action requires an explicit reviewed
        # successor, even though it costs no provider call.
        for row in self.journal.report()['actions']:
            if row['spec']['inputs'] == binding and row['status'] != 'EXECUTED':
                raise LegalMathError('E_JOB_STATE', details='Interrupted optional check; preserve and review before retry')
        def execute(work):
            value = getattr(self.backend, kind)(packet, inputs, work)
            if value.get('status') not in ('PASS', 'UNSUPPORTED', 'FAILED'):
                raise LegalMathError('E_SCHEMA', details='Optional tool needs an explicit bounded result')
            return {**binding, **value}
        value, _ = self.journal.execute('tool-check', binding, execute,
                                       issue=kind+'.'+digest(binding))
        if value['status'] == 'FAILED':
            raise LegalMathError('E_DEPENDENCY', details={'optional_tool_failure': value})
        return value

    def candidates(self, packet, candidates):
        # Validate product records before a backend sees them. A parsed reading
        # is still a proposal, not an accepted legal interpretation.
        validated = {cid: parse(Reading, r) for cid, r in candidates.items()}
        return self._check('candidates', packet, validated)

    def criticism(self, packet, candidates, proposal):
        evaluation = evaluate_criticism(proposal, packet, candidates)
        return self._check('criticism', packet, {'proposal': proposal, 'evaluation': evaluation})

    def augment(self, request):
        if self.backend.identity() != self.identity:
            raise LegalMathError('E_STALE_REVIEW', details='Optional tool implementation changed')
        packet = request.get('source_packet')
        if not isinstance(packet, dict) or not packet.get('units'):
            return request
        binding = {'request_hash': digest(request), 'packet_hash': digest(packet)}
        # Freeze each logical request's context once. Later checks must not
        # change an already-issued request on restart and defeat exact caching.
        previous = next((a for a in self.journal.report()['actions']
                         if a['spec']['stage'] == 'prepare-request' and a['spec']['inputs'] == binding
                         and a['status'] == 'EXECUTED'), None)
        if previous is not None:
            return loads((self.journal.directory/previous['result_file']).read_bytes())
        query = request.get('question')
        if not isinstance(query, str) or not query.strip():
            query = packet.get('selected_slice')
        if isinstance(query, str) and query.strip():
            self._check('retrieval', packet, {'question': query})
        def prepare(work):
            checks = [r for r in report(self.directory)['checks']
                      if r.get('packet_hash') == binding['packet_hash']]
            context = {'profile': PROFILE, 'packet_hash': binding['packet_hash'],
                'checks': checks,
                'limit': 'Fallible tool evidence for this exact packet. Structural agreement establishes no legal premise; preserve missing facts, rival readings and unsupported profiles.'}
            return {**deepcopy(request), 'external_tool_context': context}
        value, _ = self.journal.execute('prepare-request', binding, prepare,
                                       issue='request.'+binding['request_hash'])
        return value

    def report(self):
        return report(self.directory)
