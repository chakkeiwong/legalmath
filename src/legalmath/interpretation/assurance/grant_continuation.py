"""Cross-grant spending preserves an immutable predecessor and original issues."""
from copy import deepcopy
from pathlib import Path
import fcntl

from ...canonical import canonical, digest, loads, raw_digest
from ...errors import LegalMathError
from ..search.providers import CodexProvider
from .grants import GrantSlice
from .issue_limits import IssueLimits


class CarriedSlice(GrantSlice):
    """Only the unspent balance of a prior arm is available in the new grant."""

    def __init__(self, grant_path, slice_path, prior_slice, prior_hash):
        self.prior_slice = Path(prior_slice).resolve()
        self.prior_hash = prior_hash
        prior = loads(self.prior_slice.read_bytes())
        if raw_digest(self.prior_slice.read_bytes()) != prior_hash:
            raise LegalMathError('E_INTEGRITY', details='Prior arm changed')
        if (type(prior.get('maximum')) is not int or
                not isinstance(prior.get('reservations'), list)):
            raise LegalMathError('E_SCHEMA')
        self.prior_spent = len(prior['reservations'])
        self.arm_maximum = prior['maximum']
        remaining = self.arm_maximum - self.prior_spent
        if remaining < 1:
            raise LegalMathError('E_RESOURCE_LIMIT', details='Original arm exhausted')
        super().__init__(grant_path, slice_path, remaining)
        ledger = loads(self.predecessor.read_bytes())['calls']
        slots = set()
        for row in prior['reservations']:
            slot = row.get('global_slot')
            if row.get('status') == 'RESERVED' and slot is None:
                continue  # An interrupted local reservation is still spent.
            if (row.get('status') != 'GLOBALLY_RESERVED' or type(slot) is not int or
                    not 1 <= slot <= len(ledger) or slot in slots or
                    ledger[slot-1]['request_hash'] != row.get('request_hash')):
                raise LegalMathError('E_INTEGRITY', details='Prior arm detached from exhausted grant')
            slots.add(slot)
        self.carry_path = self.slice_path.with_suffix('.carry.json')
        self.carry = {'prior_slice': str(self.prior_slice), 'prior_sha256': prior_hash,
                      'prior_spent': self.prior_spent, 'arm_maximum': self.arm_maximum,
                      'remaining_ceiling': remaining, 'grant_hash': raw_digest(self.grant_bytes)}
        registry_dir = self.grant_path.parent/'continued-arm-identities'
        registry_dir.mkdir(exist_ok=True)
        self.registry_path = registry_dir/(prior_hash+'.json')
        self.registry = {'prior_sha256': prior_hash, 'grant_hash': raw_digest(self.grant_bytes),
                         'slice_path': str(self.slice_path)}
        with self.registry_path.with_suffix('.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            # Retain any already-created pre-registry carry. A different path
            # cannot claim to be a new arm after an earlier partition spent it.
            for path in self.grant_path.parent.rglob('*.carry.json'):
                prior_carry = loads(path.read_bytes())
                if (prior_carry.get('prior_sha256') == prior_hash and
                        prior_carry.get('grant_hash') == self.registry['grant_hash'] and
                        path != self.carry_path):
                    raise LegalMathError('E_INTEGRITY', details='Original arm already belongs to another continuation path')
            if self.registry_path.exists():
                if self.registry_path.read_bytes() != canonical(self.registry):
                    raise LegalMathError('E_INTEGRITY', details='Another path cannot reset the carried arm')
            else:
                self.registry_path.write_bytes(canonical(self.registry))
        self.slice_path.parent.mkdir(parents=True, exist_ok=True)
        with self.carry_path.with_suffix('.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if self.carry_path.exists():
                if self.carry_path.read_bytes() != canonical(self.carry):
                    raise LegalMathError('E_INTEGRITY', details='Changed carried arm identity')
            else:
                if self.slice_path.exists():
                    raise LegalMathError('E_INTEGRITY', details='Existing slice lacks carried history')
                self.carry_path.write_bytes(canonical(self.carry))

    def reserve(self, request_hash):
        if (raw_digest(self.prior_slice.read_bytes()) != self.prior_hash or
                self.carry_path.read_bytes() != canonical(self.carry) or
                self.registry_path.read_bytes() != canonical(self.registry)):
            raise LegalMathError('E_INTEGRITY', details='Carried history changed')
        return super().reserve(request_hash)


def scoped_issue_keys(request):
    """Ignore only the newly added redundant reading hash, never source or meaning.

    Historical requests predate that hash. Keeping it in a spending identity
    would create fresh attempts for the same representation and question.
    """
    if request.get('task') != 'SCOPED_SOURCE_FIDELITY':
        raise LegalMathError('E_REFERENCE', details='Scoped continuation cannot dispatch another task')
    claims = {r['claim_id']: r for r in request['claims']}
    candidates = {r['candidate_id']: r for r in request['candidates']}
    if len(claims) != len(request['claims']) or len(candidates) != len(request['candidates']):
        raise LegalMathError('E_DUPLICATE_ID')
    role = request['investigation']['perspective']
    if role not in ('source-first', 'qualification-first'):
        raise LegalMathError('E_REFERENCE')
    keys = []
    for pair in request['required_pairs']:
        candidate = deepcopy(candidates[pair['candidate_id']])
        candidate.pop('reading_hash', None)
        keys.append(digest({'source_packet': request['source_packet'],
            'locators': request.get('source_packet_document_locators'),
            'claim': claims[pair['claim_id']], 'candidate': candidate, 'perspective': role}))
    if not keys or len(keys) != len(set(keys)):
        raise LegalMathError('E_REFERENCE')
    return keys


def scoped_history(ledger_path, evidence_directory, *, expected_hash, fallback_requests=None):
    """Replay successful and failed reservations using retained request bytes."""
    ledger_path = Path(ledger_path)
    if raw_digest(ledger_path.read_bytes()) != expected_hash:
        raise LegalMathError('E_INTEGRITY')
    ledger = loads(ledger_path.read_bytes())
    history = {}; missing = []; requests = 0
    for slot, row in enumerate(ledger['calls'], 1):
        directory = Path(evidence_directory) / f"{slot:04}-{row['request_hash'][:16]}"
        manifest = directory/'manifest.json'
        if not manifest.exists():
            request = (fallback_requests or {}).get(slot)
            if request is None:
                missing.append(slot)
                continue
        else:
            record = loads(manifest.read_bytes())
            if record['allowance_slot'] != slot or record['request_hash'] != row['request_hash']:
                raise LegalMathError('E_INTEGRITY')
            for name in ('request.json', 'schema.json'):
                if (name not in record['files'] or
                        raw_digest((directory/name).read_bytes()) != record['files'][name]['retained_sha256']):
                    raise LegalMathError('E_INTEGRITY')
            request = loads((directory/'request.json').read_bytes())
        if digest(request) != row['request_hash']:
            raise LegalMathError('E_INTEGRITY')
        if request.get('task') != 'SCOPED_SOURCE_FIDELITY':
            continue
        requests += 1
        for key in scoped_issue_keys(request):
            started = int(row['issued_at_ns']) // 1000000
            item = history.setdefault(key, {'spent': 0, 'started_ms': started,
                                           'evidence_hash': expected_hash})
            item['spent'] += 1
            item['started_ms'] = min(item['started_ms'], started)
    if missing:
        raise LegalMathError('E_INTEGRITY', details={'unattributed_reservations': missing})
    return {'issues': history, 'scoped_requests': requests,
            'ledger_hash': expected_hash, 'reservations': len(ledger['calls'])}


class ScopedContinuationProvider(CodexProvider):
    """A new global grant cannot reset durable original pair/perspective limits."""

    def __init__(self, *, allowance, issue_limits, allowed_issues, routing_file=None):
        if not isinstance(allowance, CarriedSlice) or not isinstance(issue_limits, IssueLimits):
            raise LegalMathError('E_AUTHORITY')
        super().__init__(allowance=allowance, routing_file=routing_file)
        self.issue_limits = issue_limits
        self.allowed_issues = frozenset(allowed_issues)

    def complete(self, request, schema, settings):
        keys = scoped_issue_keys(request)
        if not set(keys) <= self.allowed_issues:
            raise LegalMathError('E_AUTHORITY', details='Issue outside reviewed continuation')
        self.issue_limits.reserve(keys, digest(request))
        return super().complete(request, schema, settings)
