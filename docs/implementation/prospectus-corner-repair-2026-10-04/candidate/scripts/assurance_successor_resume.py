"""Exact prior response reuse across a reviewed method repair, with spent limits."""
from copy import deepcopy
from pathlib import Path
import time
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.providers import CodexProvider,Completion
from assurance_successor_audit import journal_receipt
from run_assurance_successor import read,sha


def inventory_issue(request):
    if request.get('original_task',request.get('task'))!='SOURCE_INVENTORY':return None
    return digest({'task':'SOURCE_INVENTORY','role':request.get('role'),
                   'source_packet':request.get('source_packet')})


def inventory_units(request):
    if inventory_issue(request) is None:return []
    packet=request.get('source_packet') or {}
    return [digest({'role':request.get('role'),'source_key':packet.get('source_key'),
        'selected_slice':packet.get('selected_slice'),'unit':unit}) for unit in packet.get('units',[])]


def scoped_issues(request):
    if request.get('task')!='SCOPED_SOURCE_FIDELITY':return []
    claims={r['claim_id']:r for r in request['claims']}
    candidates={r['candidate_id']:r for r in request['candidates']}
    return [digest({'source_packet':request['source_packet'],
        'locators':request.get('source_packet_document_locators'),
        'claim':claims[p['claim_id']],'candidate':candidates[p['candidate_id']],
        'perspective':request['investigation']['perspective']}) for p in request['required_pairs']]


def fidelity_issues(request):
    if request.get('original_task',request.get('task'))!='SOURCE_FIDELITY':return []
    claims={r['claim_id']:r for r in request['claims']}
    candidates={r['candidate_id']:r for r in request['candidates']}
    return [digest({'source_packet':request['source_packet'],
        'locators':request.get('source_packet_document_locators'),
        'claim':claims[p['claim_id']],'candidate':candidates[p['candidate_id']]}) for p in request['required_pairs']]


def retained_transport(allowance,slot,ledger):
    if type(slot)is not int or not 1<=slot<=len(ledger):raise LegalMathError('E_INTEGRITY')
    entry=ledger[slot-1];directory=allowance.path.parent/'provider-evidence'/f"{slot:04}-{entry['request_hash'][:16]}"
    manifest=read(directory/'manifest.json')
    if manifest['allowance_slot']!=slot or manifest['request_hash']!=entry['request_hash']:
        raise LegalMathError('E_INTEGRITY')
    for name,row in manifest['files'].items():
        if Path(name).name!=name or sha(directory/name)!=row['retained_sha256']:raise LegalMathError('E_INTEGRITY')
    request=read(directory/'request.json')
    if digest(request)!=entry['request_hash']:raise LegalMathError('E_INTEGRITY')
    return request,read(directory/'schema.json')


def verify_interruption(path):
    marker=path.parent/'verified-interruption.json'
    if not marker.exists():raise LegalMathError('E_JOB_STATE',details='Prior worker may still be active')
    receipt=read(marker)
    if (receipt['journal_sha256']!=sha(path) or
        sha(receipt['failed_phase_manifest'])!=receipt['failed_phase_sha256'] or
        read(receipt['failed_phase_manifest'])['status']!='FAILED'):
        raise LegalMathError('E_INTEGRITY')


class ResumingCodex(CodexProvider):
    def __init__(self,*,allowance,prior_directory,additional_scoped_journals=()):
        super().__init__(allowance=allowance)
        self.records={};self.inventory_spent={};seen_slots=set()
        self.scoped_spent={};self.scoped_started={};self.scoped_slots=set()
        self.inventory_unit_spent={};self.inventory_unit_started={};self.inventory_unit_slots=set()
        self.fidelity_spent={};self.fidelity_started={};self.fidelity_slots=set()
        ledger=read(self.allowance.path)['calls'] if self.allowance.path.exists() else []
        def spent(slot,request):
            if slot not in self.fidelity_slots:
                self.fidelity_slots.add(slot)
                for key in fidelity_issues(request):
                    self.fidelity_spent[key]=self.fidelity_spent.get(key,0)+1
                    started=int(ledger[slot-1]['issued_at_ns'])/1e9
                    self.fidelity_started[key]=min(self.fidelity_started.get(key,started),started)
            if slot not in self.inventory_unit_slots:
                self.inventory_unit_slots.add(slot)
                for key in inventory_units(request):
                    self.inventory_unit_spent[key]=self.inventory_unit_spent.get(key,0)+1
                    started=int(ledger[slot-1]['issued_at_ns'])/1e9
                    self.inventory_unit_started[key]=min(self.inventory_unit_started.get(key,started),started)
            if slot in self.scoped_slots:return
            keys=scoped_issues(request)
            if not keys:return
            self.scoped_slots.add(slot)
            for key in keys:
                self.scoped_spent[key]=self.scoped_spent.get(key,0)+1
                started=int(ledger[slot-1]['issued_at_ns'])/1e9
                self.scoped_started[key]=min(self.scoped_started.get(key,started),started)
        for path in sorted(Path(prior_directory).glob('revisions/*/core/model-evidence/journal.json')):
            journal,state=journal_receipt(path)
            if state['binding']['inputs'].get('route')!=self.routing:raise LegalMathError('E_AUTHORITY')
            for action in state['actions']:
                request=action['spec']['inputs']['request'];request_hash=digest(request)
                for slot,row in enumerate(ledger,1):
                    if row['request_hash']==request_hash:spent(slot,request)
                if action['status']!='EXECUTED':
                    if action['status']=='RESERVED':verify_interruption(path)
                    issue=inventory_issue(action['spec']['inputs']['request'])
                    if issue:self.inventory_spent[issue]=self.inventory_spent.get(issue,0)+1
                    continue
                inputs=action['spec']['inputs'];response=read(path.parent/action['result_file'])
                request=inputs['request'];provenance=response['provenance']
                # Reused actions keep the original reservation, never a new vote.
                slot=provenance.get('allowance_slot')
                if type(slot)is not int or not 1<=slot<=len(ledger) or ledger[slot-1]['request_hash']!=digest(request):
                    raise LegalMathError('E_INTEGRITY',details='Prior response has no matching live reservation')
                if slot not in seen_slots:
                    issue=inventory_issue(request)
                    if issue:self.inventory_spent[issue]=self.inventory_spent.get(issue,0)+1
                    seen_slots.add(slot)
                key=digest({'request':request,'schema':inputs['schema']})
                self.records.setdefault(key,{'response':response,'prior_journal':str(path.resolve()),
                    'prior_journal_sha256':sha(path),'sequence':action['sequence'],'result_hash':action['result_hash']})
        scoped_paths=set(Path(prior_directory).glob('revisions/*/scoped/model/journal.json'))
        scoped_paths.update(Path(p) for p in additional_scoped_journals)
        for path in sorted(scoped_paths):
            _,state=journal_receipt(path)
            if state['binding']['inputs'].get('route')!=self.routing:raise LegalMathError('E_AUTHORITY')
            for action in state['actions']:
                work=path.parent/f"action-{action['sequence']:04}"
                wire=work/'wire-request.json'
                span_transport=work/'source-references'
                if (span_transport/'wire-request.json').exists():wire=span_transport/'wire-request.json'
                if not wire.exists():continue  # Local pre-dispatch failure; no live reservation.
                request=read(wire);request_hash=digest(request)
                slots=[i+1 for i,row in enumerate(ledger) if row['request_hash']==request_hash]
                if action['status']=='RESERVED':
                    verify_interruption(path)
                for slot in slots:spent(slot,request)
                if action['status']!='EXECUTED':continue
                response=read((span_transport if span_transport.exists() else work)/'raw-response.json');provenance=response['provenance']
                slot=provenance.get('allowance_slot')
                if slot not in slots or provenance.get('provider_route_hash')!=digest(self.routing):
                    raise LegalMathError('E_INTEGRITY',details='Scoped response lacks its original route/reservation')
                schema=read(span_transport/'wire-schema.json') if span_transport.exists() else action['spec']['inputs']['schema']
                key=digest({'request':request,'schema':schema})
                self.records.setdefault(key,{'response':response,'prior_journal':str(path.resolve()),
                    'prior_journal_sha256':sha(path),'sequence':action['sequence'],'result_hash':action['result_hash']})
        # Outer question proposals are also immutable model evidence. Their
        # original wire request/schema come from the bound transport receipt.
        for path in sorted(Path(prior_directory).glob('revisions/*/actions/journal.json')):
            _,state=journal_receipt(path)
            for action in state['actions']:
                if action['status']!='EXECUTED' or action['spec']['stage']!='question-proposal':continue
                raw=path.parent/f"action-{action['sequence']:04}"/'raw.json'
                response=read(raw);provenance=response['provenance']
                if provenance.get('provider_route_hash')!=digest(self.routing):raise LegalMathError('E_AUTHORITY')
                request,schema=retained_transport(allowance,provenance.get('allowance_slot'),ledger)
                if request.get('task')!='DEFINE_EXACT_QUESTIONS':raise LegalMathError('E_INTEGRITY')
                key=digest({'request':request,'schema':schema})
                self.records.setdefault(key,{'response':response,'prior_journal':str(path.resolve()),
                    'prior_journal_sha256':sha(path),'sequence':action['sequence'],'result_hash':action['result_hash']})
        # Count completed AND timed-out requests across every old partition.
        # Transport receipts, not successful-answer counts, bind expenditure.
        for directory in sorted((allowance.path.parent/'provider-evidence').glob('*')):
            if not directory.is_dir() or not (directory/'manifest.json').is_file():continue
            slot=read(directory/'manifest.json')['allowance_slot']
            if slot>len(ledger):continue  # Another task may finish after this snapshot.
            request,_=retained_transport(allowance,slot,ledger)
            spent(slot,request)

    def complete(self,request,schema,settings):
        key=digest({'request':request,'schema':schema});record=self.records.get(key)
        if record:
            if sha(record['prior_journal'])!=record['prior_journal_sha256']:raise LegalMathError('E_INTEGRITY')
            response=deepcopy(record['response'])
            return Completion(response['value'],{**response['provenance'],
                'evidence_reused':True,'new_live_invocation':False,
                'prior_revision_receipt':{k:v for k,v in record.items() if k!='response'}})
        issue=inventory_issue(request)
        if issue:
            if self.inventory_spent.get(issue,0)>=3:
                raise LegalMathError('E_RESOURCE_LIMIT',details='Original inventory plus repairs exhausted three nonrefundable requests')
            for unit in inventory_units(request):
                if (self.inventory_unit_spent.get(unit,0)>=3 or
                    time.time()-self.inventory_unit_started.get(unit,time.time())>=86400):
                    raise LegalMathError('E_RESOURCE_LIMIT',details='Original source unit/reader request or deadline limit; repartition cannot reset it')
            self.inventory_spent[issue]=self.inventory_spent.get(issue,0)+1
            for unit in inventory_units(request):
                self.inventory_unit_spent[unit]=self.inventory_unit_spent.get(unit,0)+1
                self.inventory_unit_started.setdefault(unit,time.time())
        keys=scoped_issues(request)
        for key in keys:
            if self.scoped_spent.get(key,0)>=6 or time.time()-self.scoped_started.get(key,time.time())>=86400:
                raise LegalMathError('E_RESOURCE_LIMIT',details='Original scoped pair/perspective request or deadline limit')
        for key in keys:
            self.scoped_spent[key]=self.scoped_spent.get(key,0)+1
            self.scoped_started.setdefault(key,time.time())
        # One response repair and one transport retry per request: at most four
        # reservations for an unchanged legacy fidelity pair, across partitions.
        for key in fidelity_issues(request):
            if self.fidelity_spent.get(key,0)>=4 or time.time()-self.fidelity_started.get(key,time.time())>=86400:
                raise LegalMathError('E_RESOURCE_LIMIT',details='Original fidelity pair request or deadline limit')
        for key in fidelity_issues(request):
            self.fidelity_spent[key]=self.fidelity_spent.get(key,0)+1
            self.fidelity_started.setdefault(key,time.time())
        return super().complete(request,schema,settings)
