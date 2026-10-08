"""Optional checks at validated product stages, retained independently of models.

Backends compute diagnostics on supplied inputs. Their output is fallible data;
neither a successful check nor its inclusion in a prompt proves a legal premise.
"""
from copy import deepcopy
from pathlib import Path
import re

from ...canonical import digest, loads
from ...errors import LegalMathError
from ..contracts import parse
from ..search.models import Reading
from .arguments import evaluate_criticism
from .workflow import EvidenceJournal

LEGACY_PROFILE = 'legalmath.optional-product-tools.v1'
PROFILE = 'legalmath.optional-product-tools.v2'
RESERVED_FIELDS = {'kind', 'packet_hash', 'inputs_hash', 'candidate_hashes', 'key', 'result_hash', 'backend', 'profile'}


def candidate_hashes(candidates):
    if not isinstance(candidates, dict) or not candidates:
        raise LegalMathError('E_REFERENCE', details='Optional candidate checks require actual readings')
    return {cid: digest(parse(Reading, r)) for cid, r in candidates.items()}


def request_candidate_hashes(request):
    candidates = request.get('candidates')
    if isinstance(candidates, dict):
        return candidate_hashes(candidates) if candidates else {}
    if isinstance(candidates, list):
        result = {}
        for row in candidates:
            if (not isinstance(row, dict) or not isinstance(row.get('candidate_id'), str)
                    or row['candidate_id'] in result
                    or not re.fullmatch('[a-f0-9]{64}', row.get('reading_hash', ''))):
                raise LegalMathError('E_REFERENCE', details='Tool feedback requires distinct reading-bound candidates')
            result[row['candidate_id']] = row['reading_hash']
        return result
    return {}


def report(directory, *, expected_backend=None):
    """Recompute the summary from retained checks, including artifact hashes."""
    path = Path(directory)/'journal.json'
    if not path.exists():
        if expected_backend is not None:
            raise LegalMathError('E_REFERENCE', details='Required optional-tool journal missing')
        return {'profile': PROFILE, 'checks': [], 'prepared_requests': 0,
                'execution_complete': False, 'legal_premises_established': False}
    binding = loads(path.read_bytes())['value']['binding']
    profile = binding['inputs'].get('profile')
    if profile not in (LEGACY_PROFILE, PROFILE) or not isinstance(binding['inputs'].get('backend'), dict):
        raise LegalMathError('E_INTEGRITY', details='Unrecognized optional-tool method binding')
    if expected_backend is not None and binding['inputs']['backend'] != expected_backend:
        raise LegalMathError('E_INTEGRITY', details='Optional backend differs from the bound investigation method')
    journal = EvidenceJournal(directory, binding['inputs'],
        **{k: binding[k] for k in ('maximum_actions', 'maximum_per_issue', 'deadline_seconds')})
    state = journal.report()
    checks = []
    for a in state['actions']:
        if a['spec']['stage'] != 'tool-check':
            continue
        if a['status'] == 'EXECUTED':
            value = loads((journal.directory/a['result_file']).read_bytes())
            if profile == PROFILE:
                expected = a['spec']['inputs']
                if (any(value.get(k) != v for k, v in expected.items())
                        or value.get('status') not in ('PASS', 'UNSUPPORTED', 'FAILED')
                        or not isinstance(expected.get('candidate_hashes'), dict)
                        or any(k in value for k in ('key', 'result_hash', 'backend', 'profile'))):
                    raise LegalMathError('E_INTEGRITY', details='Optional result changed authoritative check bindings')
            checks.append({'key': a['key'], 'result_hash': a['result_hash'], **value})
        else:
            checks.append({'key': a['key'], 'status': a['status'],
                           'inputs': a['spec']['inputs']})
    return {'profile': profile, **({'backend': deepcopy(binding['inputs']['backend'])} if profile == PROFILE else {}),
            'checks': checks,
            'prepared_requests': sum(a['spec']['stage'] == 'prepare-request' for a in state['actions']),
            'execution_complete': bool(checks) and all(c['status'] in ('PASS', 'UNSUPPORTED') for c in checks)
                and (profile == LEGACY_PROFILE or all(a['status'] == 'EXECUTED' for a in state['actions'])),
            'legal_premises_established': False}


class ToolSession:
    def __init__(self, backend, directory):
        self.backend = backend
        self.identity = deepcopy(backend.identity())
        self.directory = Path(directory)
        self.journal = EvidenceJournal(self.directory, {'profile': PROFILE, 'backend': self.identity},
                                       maximum_actions=200, maximum_per_issue=1, deadline_seconds=86400)
        self.journal.report()

    def _check(self, kind, packet, inputs, *, candidates=None):
        if self.backend.identity() != self.identity:
            raise LegalMathError('E_STALE_REVIEW', details='Optional tool implementation changed')
        binding = {'kind': kind, 'packet_hash': digest(packet), 'inputs_hash': digest(inputs),
                   'candidate_hashes': candidate_hashes(candidates) if candidates is not None else {}}
        # A failed or reserved tool action requires an explicit reviewed
        # successor, even though it costs no provider call.
        for row in self.journal.report()['actions']:
            if row['spec']['inputs'] == binding and row['status'] != 'EXECUTED':
                raise LegalMathError('E_JOB_STATE', details='Interrupted optional check; preserve and review before retry')
        def execute(work):
            # A backend is fallible and must not mutate caller-held evidence.
            value = getattr(self.backend, kind)(deepcopy(packet), deepcopy(inputs), work)
            if not isinstance(value, dict) or value.get('status') not in ('PASS', 'UNSUPPORTED', 'FAILED'):
                raise LegalMathError('E_SCHEMA', details='Optional tool needs an explicit bounded result')
            if RESERVED_FIELDS & value.keys():
                raise LegalMathError('E_INTEGRITY', details='Backend attempted to overwrite authoritative check bindings')
            if self.backend.identity() != self.identity:
                raise LegalMathError('E_STALE_REVIEW', details='Optional tool implementation changed during execution')
            return {**value, **binding}
        value, _ = self.journal.execute('tool-check', binding, execute,
                                       issue=kind+'.'+digest(binding))
        if value['status'] == 'FAILED':
            raise LegalMathError('E_DEPENDENCY', details={'optional_tool_failure': value})
        return value

    def candidates(self, packet, candidates):
        # Validate product records before a backend sees them. A parsed reading
        # is still a proposal, not an accepted legal interpretation.
        validated = {cid: parse(Reading, r) for cid, r in candidates.items()}
        return self._check('candidates', packet, validated, candidates=validated)

    def criticism(self, packet, candidates, proposal):
        candidate_hashes(candidates)
        evaluation = evaluate_criticism(proposal, packet, candidates)
        return self._check('criticism', packet, {'proposal': proposal, 'evaluation': evaluation}, candidates=candidates)

    def augment(self, request):
        if self.backend.identity() != self.identity:
            raise LegalMathError('E_STALE_REVIEW', details='Optional tool implementation changed')
        packet = request.get('source_packet')
        if not isinstance(packet, dict) or not packet.get('units'):
            return request
        current = request_candidate_hashes(request)
        binding = {'request_hash': digest(request), 'packet_hash': digest(packet)}
        # Freeze each logical request's context once. Later checks must not
        # change an already-issued request on restart and defeat exact caching.
        previous = next((a for a in self.journal.report()['actions']
                         if a['spec']['stage'] == 'prepare-request' and a['spec']['inputs'] == binding
                         and a['status'] == 'EXECUTED'), None)
        if previous is not None:
            return loads((self.journal.directory/previous['result_file']).read_bytes())
        typed = request.get('task') == 'SCOPED_SOURCE_FIDELITY'
        targets=[]
        if typed:
            for row in request.get('candidates',[]):
                question=row.get('question')
                if (not isinstance(question,dict) or not isinstance(question.get('question'),str)
                        or row.get('question_hash')!=digest(question)):
                    raise LegalMathError('E_REFERENCE',details='Scoped retrieval requires the exact typed candidate question')
                targets.append({'question':question['question'],'question_hash':digest(question),
                                'candidate_id':row['candidate_id']})
        else:
            query = request.get('question')
            if not isinstance(query, str) or not query.strip():
                query = packet.get('selected_slice')
            if isinstance(query, str) and query.strip():targets=[{'question':query}]
        retrieval=[]
        for target in targets:
            retrieval.append(self._check('retrieval',packet,target)['inputs_hash'])
        def prepare(work):
            checks = [r for r in report(self.directory)['checks']
                      if r.get('packet_hash') == binding['packet_hash']
                      and ((r.get('kind') == 'retrieval' and r.get('inputs_hash') in retrieval)
                           or (r.get('kind') in ('candidates', 'criticism') and r.get('candidate_hashes')
                               and all(current.get(cid) == hashed for cid, hashed in r['candidate_hashes'].items())))]
            context = {'profile': PROFILE, 'packet_hash': binding['packet_hash'],
                'candidate_hashes': current,
                'checks': checks, 'retrieval_targets':targets,
                'limit': 'Fallible tool evidence for this exact packet and candidate revisions. Atomic multi-candidate checks are omitted unless every checked reading is present and unchanged. For each scoped pair assess candidates[].question; the parent source_packet.selected_slice is context, not a replacement question. Retrieval queries only locate evidence. Structural agreement establishes no legal premise; preserve missing facts, rival readings and unsupported profiles.'}
            return {**deepcopy(request), 'external_tool_context': context}
        value, _ = self.journal.execute('prepare-request', binding, prepare,
                                       issue='request.'+binding['request_hash'])
        return value

    def report(self):
        return report(self.directory, expected_backend=self.identity)
