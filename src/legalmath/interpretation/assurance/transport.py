"""Retained compact transport and a circuit breaker for provider availability."""
from pathlib import Path
from ...canonical import canonical,digest
from ...errors import LegalMathError
from ..search.providers import Completion
from .decomposition import compact_request
from .monitor import save
from . import source_references


def transient_service_failure(exc):
    """Narrow retry eligibility; permanent and application failures stop dispatch."""
    code=getattr(exc,'code',None);details=str(getattr(exc,'details','')).lower()
    if code=='E_RESOURCE_LIMIT':return 'call deadline' in details
    return code=='E_DEPENDENCY' and any(message in details for message in (
        'overloaded','temporarily unavailable','timed out','stream disconnected',
        'connection reset'))


class CompactProvider:
    def __init__(self,provider,directory,*,reference_protocol='literal',input_profile='literal',optional_tools=None,
                 original_questions=None):
        if reference_protocol not in ('literal',source_references.PROTOCOL):raise LegalMathError('E_SCHEMA')
        if input_profile not in ('literal','readable-tables.v1','shared-evidence.v1'):raise LegalMathError('E_SCHEMA')
        self.input_profile=input_profile
        self.reference_protocol=reference_protocol
        self.provider=provider;self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True)
        self.provider_id=provider.provider_id+'.compact.v2';self.live=provider.live
        self.routing={'provider':getattr(provider,'routing',provider.provider_id),'transport':'exact-source-text.compact.v2'}
        if reference_protocol!='literal':self.routing['source_reference_protocol']=reference_protocol
        if input_profile!='literal':self.routing['input_profile']=input_profile
        self.allowance=getattr(provider,'allowance',None);self.blocked=None
        self.optional_tools=optional_tools
        from .original_questions import validate as validate_original_questions
        self.original_questions=validate_original_questions(original_questions) if original_questions is not None else None
        self._original_question_binding=digest(self.original_questions)
        if self.original_questions is not None:
            self.routing['original_question_binding']=digest(self.original_questions)
        self.source_context=getattr(provider,'source_context',None)
        self.source_context_root=getattr(provider,'source_context_root',None)

    def complete(self,request,schema,settings):
        if digest(self.original_questions) != self._original_question_binding:
            raise LegalMathError('E_STALE_REVIEW',details='Original question context changed')
        if self.blocked:
            raise LegalMathError('E_DEPENDENCY',details={'provider_circuit_open':self.blocked,'new_live_call':False})
        from .source_context import augment
        from .original_questions import attach as attach_original_questions
        request=attach_original_questions(request,self.original_questions)
        request=augment(request,self.source_context)
        if self.optional_tools is not None:
            request=self.optional_tools.augment(request)
        out=self.directory/f'call-{len(list(self.directory.glob("call-*"))):03}'
        out.mkdir(exist_ok=False);wire=compact_request(request,profile='v2')
        save(out/'request.json',wire);save(out/'original-request.json',request);save(out/'schema.json',schema)
        record={'original_request_hash':digest(request),'wire_request_hash':digest(wire),
                'original_bytes':len(canonical(request)),'wire_bytes':len(canonical(wire)),'status':'DISPATCHED'}
        save(out/'status.json',record)
        try:
            if self.input_profile=='literal' and len(canonical(wire)) > settings.max_input_bytes:
                raise LegalMathError('E_RESOURCE_LIMIT',details='Compact wire request exceeds input cap')
            if (self.reference_protocol!='literal' and 'Quote' in schema.get('$defs',{})) or self.input_profile!='literal':
                answer=source_references.complete(self.provider,wire,schema,settings,out/'source-references',input_profile=self.input_profile)
            else:answer=self.provider.complete(wire,schema,settings)
            provenance={**answer.provenance,'original_request_hash':digest(request),
                'wire_request_hash':digest(wire),'compact_request':wire,
                'transport_profile':'exact-source-text.compact.v2'}
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
