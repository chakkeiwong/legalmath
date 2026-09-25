"""Retained compact transport and a circuit breaker for provider availability."""
from pathlib import Path
from ...canonical import canonical,digest
from ...errors import LegalMathError
from ..search.providers import Completion
from .decomposition import compact_request
from .monitor import save


def transient_service_failure(exc):
    """Narrow retry eligibility; permanent and application failures stop dispatch."""
    code=getattr(exc,'code',None);details=str(getattr(exc,'details','')).lower()
    if code=='E_RESOURCE_LIMIT':return 'call deadline' in details
    return code=='E_DEPENDENCY' and any(message in details for message in (
        'overloaded','temporarily unavailable','timed out','stream disconnected',
        'connection reset'))


class CompactProvider:
    def __init__(self,provider,directory):
        self.provider=provider;self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True)
        self.provider_id=provider.provider_id+'.compact.v1';self.live=provider.live
        self.routing={'provider':getattr(provider,'routing',provider.provider_id),'transport':'exact-source-text.compact.v1'}
        self.allowance=getattr(provider,'allowance',None);self.blocked=None

    def complete(self,request,schema,settings):
        if self.blocked:
            raise LegalMathError('E_DEPENDENCY',details={'provider_circuit_open':self.blocked,'new_live_call':False})
        out=self.directory/f'call-{len(list(self.directory.glob("call-*"))):03}'
        out.mkdir(exist_ok=False);wire=compact_request(request)
        save(out/'request.json',wire);save(out/'original-request.json',request);save(out/'schema.json',schema)
        record={'original_request_hash':digest(request),'wire_request_hash':digest(wire),
                'original_bytes':len(canonical(request)),'wire_bytes':len(canonical(wire)),'status':'DISPATCHED'}
        save(out/'status.json',record)
        try:
            answer=self.provider.complete(wire,schema,settings)
            provenance={**answer.provenance,'original_request_hash':digest(request),
                'wire_request_hash':digest(wire),'compact_request':wire,
                'transport_profile':'exact-source-text.compact.v1'}
            save(out/'response.json',{'value':answer.value,'provenance':provenance})
            record.update(status='RETURNED_UNVALIDATED',response_hash=digest(answer.value))
            save(out/'status.json',record)
            return Completion(answer.value,provenance)
        except Exception as exc:
            error=getattr(exc,'code',type(exc).__name__);details=getattr(exc,'details',str(exc))
            record.update(status='FAILED',error=error,details=details);save(out/'status.json',record)
            if error=='E_DEPENDENCY' or (error=='E_RESOURCE_LIMIT' and 'deadline' in str(details).lower()):
                self.blocked={'error':error,'details':details,'wire_request_hash':digest(wire)}
            raise
