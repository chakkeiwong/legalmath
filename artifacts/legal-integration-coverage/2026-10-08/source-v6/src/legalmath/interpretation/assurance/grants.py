"""Additional grants preserve historical allowance ceilings and reservations."""
from pathlib import Path
import fcntl
import re

from ...canonical import canonical, loads, raw_digest
from ...errors import LegalMathError
from ..search.providers import Allowance


class GrantedAllowance(Allowance):
    """A new bounded ledger, anchored to an immutable exhausted predecessor.

    This validates a recorded user grant; it cannot infer permission from a
    request, retry, local action budget, elapsed time or model response.
    """
    def __init__(self, grant_path, *, reservation_ceiling=None):
        self.grant_path = Path(grant_path).resolve()
        self.grant_bytes = self.grant_path.read_bytes()
        grant = loads(self.grant_bytes)
        if (set(grant) != {'schema', 'grant_id', 'authorized_calls', 'authorization',
                          'predecessor', 'ledger'} or
                grant['schema'] != 'legalmath.additional-grant.v1' or
                type(grant['authorized_calls']) is not int or
                not 1 <= grant['authorized_calls'] <= 500 or
                not re.fullmatch(r'[A-Za-z0-9_.-]+', grant['grant_id']) or
                not isinstance(grant['authorization'], str) or not grant['authorization'].strip()):
            raise LegalMathError('E_AUTHORITY', details='Invalid additional grant')
        self.grant = grant
        base = self.grant_path.parent
        self.predecessor = (base/grant['predecessor']['path']).resolve()
        ledger = (base/grant['ledger']).resolve()
        if ledger.parent != base or ledger == self.predecessor or ledger == self.grant_path:
            raise LegalMathError('E_AUTHORITY', details='New ledger must be local to grant and distinct')
        super().__init__(ledger, grant['authorized_calls'], reservation_ceiling=reservation_ceiling)
        self.verify()

    def verify(self):
        if self.grant_path.read_bytes() != self.grant_bytes:
            raise LegalMathError('E_INTEGRITY', details='Grant changed during execution')
        old = self.predecessor.read_bytes()
        if raw_digest(old) != self.grant['predecessor']['sha256']:
            raise LegalMathError('E_INTEGRITY', details='Historical allowance changed')
        prior = loads(old)
        if (set(prior) != {'maximum', 'calls'} or type(prior['maximum']) is not int or
                not isinstance(prior['calls'], list) or len(prior['calls']) != prior['maximum']):
            raise LegalMathError('E_INTEGRITY', details='Predecessor is not the exhausted recorded grant')
        if self.path.exists():
            value = loads(self.path.read_bytes())
            if (set(value) != {'maximum', 'calls'} or value['maximum'] != self.maximum or
                    not isinstance(value['calls'], list) or len(value['calls']) > self.maximum):
                raise LegalMathError('E_INTEGRITY', details='Invalid new allowance history')
            for row in value['calls']:
                if (set(row) != {'request_hash', 'issued_at_ns'} or
                        not isinstance(row['request_hash'], str) or
                        not re.fullmatch('[0-9a-f]{64}', row['request_hash']) or
                        not isinstance(row['issued_at_ns'], str) or not row['issued_at_ns'].isdigit()):
                    raise LegalMathError('E_INTEGRITY', details='Invalid reservation')
        return {'grant_id': self.grant['grant_id'], 'maximum': self.maximum,
                'used': len(loads(self.path.read_bytes())['calls']) if self.path.exists() else 0,
                'predecessor_hash': raw_digest(old), 'grant_hash': raw_digest(self.grant_bytes)}

    def reserve(self, request_hash):
        self.verify()
        if not isinstance(request_hash, str) or not re.fullmatch('[0-9a-f]{64}', request_hash):
            raise LegalMathError('E_SCHEMA')
        return super().reserve(request_hash)


class GrantSlice(GrantedAllowance):
    """A nonrefundable arm ceiling within the same authorized global grant.

    Reserve locally first, then globally. Interruption may consume an unused
    local slot, but can never increase either limit or refund a dispatched call.
    """
    def __init__(self,grant_path,slice_path,maximum,*,global_ceiling=None):
        super().__init__(grant_path,reservation_ceiling=global_ceiling)
        if type(maximum)is not int or not 1<=maximum<=500:raise LegalMathError('E_SCHEMA')
        self.slice_path=Path(slice_path).resolve();self.slice_maximum=maximum
        if not self.slice_path.is_relative_to(self.grant_path.parent):raise LegalMathError('E_AUTHORITY')

    def reserve(self,request_hash):
        self.verify();self.slice_path.parent.mkdir(parents=True,exist_ok=True)
        if not isinstance(request_hash,str) or not re.fullmatch('[0-9a-f]{64}',request_hash):raise LegalMathError('E_SCHEMA')
        with self.slice_path.with_suffix('.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            v=loads(self.slice_path.read_bytes()) if self.slice_path.exists() else {
                'grant_hash':raw_digest(self.grant_bytes),'maximum':self.slice_maximum,'reservations':[]}
            if v['grant_hash']!=raw_digest(self.grant_bytes) or v['maximum']!=self.slice_maximum:
                raise LegalMathError('E_INTEGRITY')
            if len(v['reservations'])>=self.slice_maximum:raise LegalMathError('E_RESOURCE_LIMIT',details='Predeclared arm allowance exhausted')
            row={'request_hash':request_hash,'global_slot':None,'status':'RESERVED'};v['reservations'].append(row)
            def persist():
                tmp=self.slice_path.with_suffix('.tmp');tmp.write_bytes(canonical(v));tmp.replace(self.slice_path)
            persist()
            slot=super().reserve(request_hash)
            row.update(global_slot=slot,status='GLOBALLY_RESERVED');persist()
            return slot
