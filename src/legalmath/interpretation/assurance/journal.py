"""Reserve and retain every model action, including invalid output and failures."""
from pathlib import Path
import time
from ...canonical import canonical, digest, loads, raw_digest
from ...errors import LegalMathError
from .monitor import save


class JournalProvider:
    def __init__(self, provider, directory, *, maximum=18, deadline_seconds=2400):
        self.provider, self.directory = provider, Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.provider_id, self.live = provider.provider_id, provider.live
        self.maximum, self.deadline = maximum, time.monotonic() + deadline_seconds

    @property
    def calls(self):
        return len(list(self.directory.glob('call-*')))

    def complete(self, request, schema, settings):
        remaining=int(self.deadline-time.monotonic())
        if self.calls >= self.maximum or remaining<1:
            raise LegalMathError('E_RESOURCE_LIMIT', details='Assurance call/deadline limit')
        settings=settings.model_copy(update={'timeout_seconds':min(settings.timeout_seconds,remaining)})
        if len(canonical(request)) > settings.max_input_bytes:
            raise LegalMathError('E_RESOURCE_LIMIT', details='Assurance request byte cap')
        sequence = self.calls
        directory = self.directory / f'call-{sequence:03}'
        directory.mkdir(exist_ok=False)
        save(directory / 'request.json', request); save(directory / 'schema.json', schema)
        status = {'sequence': sequence, 'status': 'DISPATCHED', 'request_hash': digest(request),
                  'task': request['task'], 'provider': self.provider_id}
        save(directory / 'status.json', status)
        try:
            answer = self.provider.complete(request, schema, settings)
            if len(canonical(answer.value)) > settings.max_output_bytes:
                raise LegalMathError('E_RESOURCE_LIMIT', details='Assurance response byte cap')
            save(directory / 'response.json', {'value': answer.value, 'provenance': answer.provenance})
            status.update(status='RETURNED_UNVALIDATED', response_hash=digest(answer.value))
            save(directory / 'status.json', status)
            return answer
        except Exception as exc:
            status.update(status='FAILED', error=getattr(exc, 'code', type(exc).__name__),
                          details=getattr(exc,'details',None))
            save(directory / 'status.json', status)
            raise


class RetainedProvider:
    """Exact, manifest-verified replay with an explicit narrow live repair path."""
    def __init__(self,provider,directory,allowance,*,new_tasks=(),exclude_tasks=()):
        self.provider=provider;self.provider_id=provider.provider_id;self.live=provider.live
        self.routing=getattr(provider,'routing',provider.provider_id)
        self.directory=Path(directory).resolve();self.new_tasks=set(new_tasks);self.records={}
        manifest=loads((self.directory/'manifest.json').read_bytes())
        for name,expected in manifest['files'].items():
            path=(self.directory/name).resolve()
            if not path.is_relative_to(self.directory) or raw_digest(path.read_bytes())!=expected:
                raise LegalMathError('E_INTEGRITY',details='Retained investigation manifest mismatch')
        if digest(loads((self.directory/'report.json').read_bytes()))!=manifest['report_hash']:
            raise LegalMathError('E_INTEGRITY')
        ledger=loads(Path(allowance).read_bytes())
        for path in sorted((self.directory/'calls').glob('call-*')):
            for name in ('status.json','request.json','schema.json'):
                if str((path/name).relative_to(self.directory)) not in manifest['files']:
                    raise LegalMathError('E_INTEGRITY',details='Unmanifested replay record')
            status=loads((path/'status.json').read_bytes());request=loads((path/'request.json').read_bytes())
            schema=loads((path/'schema.json').read_bytes());rh=digest(request)
            if status['request_hash']!=rh:raise LegalMathError('E_INTEGRITY')
            # Task-specific routing may select another verified manifest for this
            # task. Verify all file bytes above, but do not load an unused call
            # or infer its reservation from an ambiguous repeated request hash.
            if request.get('original_task',request['task']) in exclude_tasks:continue
            slots=[i+1 for i,c in enumerate(ledger['calls']) if c['request_hash']==rh]
            if status['request_hash']!=rh or not slots:raise LegalMathError('E_INTEGRITY')
            record={'status':status,'origin':str(path),
                    'source_manifest_hash':digest(manifest)}
            if (path/'response.json').exists():
                if str((path/'response.json').relative_to(self.directory)) not in manifest['files']:
                    raise LegalMathError('E_INTEGRITY')
                record['response']=loads((path/'response.json').read_bytes())
                if digest(record['response']['value'])!=status.get('response_hash'):
                    raise LegalMathError('E_INTEGRITY')
                slot=record['response']['provenance'].get('allowance_slot')
                if slot not in slots:raise LegalMathError('E_INTEGRITY',details='Missing original live reservation identity')
                record['allowance_slot']=slot
            elif status['status']!='FAILED':
                raise LegalMathError('E_JOB_STATE',details='Cannot replay an unresolved dispatch')
            elif len(slots)==1:record['allowance_slot']=slots[0]
            else:raise LegalMathError('E_REFERENCE',details='Ambiguous original failed-call reservation')
            self.records.setdefault(digest({'request':request,'schema':schema}),[]).append(record)

    def complete(self,request,schema,settings):
        key=digest({'request':request,'schema':schema});records=self.records.get(key,[])
        if records:
            record=records.pop(0)
            provenance={k:record[k] for k in ('origin','allowance_slot','source_manifest_hash')}
            provenance.update(evidence_class='RETAINED_PREVIOUSLY_COUNTED_LIVE_ACTION',new_live_invocation=False)
            if 'response' not in record:
                raise LegalMathError(record['status']['error'],details={'retained_failure':provenance,
                    'original_details':record['status'].get('details')})
            from ..search.providers import Completion
            prior=record['response']
            return Completion(prior['value'],{**prior['provenance'],**provenance,'original_provenance':prior['provenance']})
        task=request.get('original_task',request['task'])
        if task not in self.new_tasks:
            raise LegalMathError('E_IDEMPOTENCY',details='Unexpected replay miss outside the reviewed live repair tasks: '+task)
        return self.provider.complete(request,schema,settings)
