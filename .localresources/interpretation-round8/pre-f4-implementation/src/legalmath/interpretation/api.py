"""Authenticated asynchronous transport; requests cannot provide executable adapters or authority."""
from importlib.resources import files
from pathlib import Path
from threading import Thread, Lock
from fastapi import Depends
from fastapi.responses import HTMLResponse, Response
from pydantic import Field
from .contracts import Strict, Packet, Proposal, Id, Hash, Text, TERMINAL
from .controller import Controller
from .service import Interpretations
from .reports import Reports
from .review import MeaningReview
from ..errors import LegalMathError

class Create(Strict):
    packet: Packet
    policy: dict | None = None
    predecessor: Id | None = None

class Configure(Strict):
    members: dict
    repairs: list[dict] = Field(default_factory=list,max_length=3)
    verification_hashes: list[Hash] = Field(default_factory=list,max_length=24)

class IssueDecision(Strict):
    revision: int = Field(ge=0)
    candidate_id: Id
    decision: str
    rationale: Text
    objection: Text
    evidence_refs: list[Id] = Field(min_length=1,max_length=500)

class Review(IssueDecision):
    candidate_hash: Hash
    report_hash: Hash
    source_packet_hash: Hash

class Invalidate(Strict):
    replacement: Packet
    reason: Text

class Supersede(Strict):
    predecessor_id: Id
    predecessor_report_hash: Hash
    reason: Text

class InventoryReview(Strict):
    source_packet_hash: Hash
    unit_ids: list[Id] = Field(min_length=1,max_length=500)
    rationale: Text

class Supervisor:
    """Single-host prototype recovery with persisted PID/start identity and finite leases."""
    def __init__(self, service): self.s=service;self.lock=Lock();self.threads={}

    def recover(self):
        from .contracts import TERMINAL
        with self.s.db.transaction() as con:
            for row in con.execute('SELECT * FROM interpretation_workers').fetchall():
                parts=row['owner'].split('.')
                stat=Path('/proc')/parts[1]/'stat' if len(parts)>3 else None
                alive=stat and stat.exists() and stat.read_text().split()[21]==parts[2]
                if alive: continue
                for a in self.s._list(con,row['run_id'],'action'):
                    if a['state']=='DISPATCHED':
                        a.update(state='RESULT_UNKNOWN',substantive_outcome='UNAVAILABLE',fencing_token=a['fencing_token']+1);self.s._save(con,'action',a)
                    elif a['state']=='RESERVED': con.execute('UPDATE interpretation_outbox SET lease_until=NULL WHERE action_id=?',(a['action_id'],))
                con.execute('DELETE FROM interpretation_workers WHERE run_id=?',(row['run_id'],))
            pending=[r[0] for r in con.execute("SELECT run_id FROM interpretation_records WHERE kind='start'") if self.s._run(con,r[0])['status'] not in TERMINAL]
        for rid in pending: self.start(rid)

    def start(self, run_id):
        with self.lock:
            if run_id in self.threads and self.threads[run_id].is_alive(): return
            def target():
                try: Controller(self.s).drive(run_id)
                except LegalMathError as exc:
                    if exc.code!='E_JOB_STATE': Reports(self.s).finish(run_id,'INTEGRITY_FAILURE')
            t=Thread(target=target,daemon=True,name='interpretation-'+run_id);self.threads[run_id]=t;t.start()


def install(app,db,caller,key,run_jobs):
    service=Interpretations(db);supervisor=Supervisor(service)
    app.state.interpretations=service;app.state.interpretation_jobs=supervisor
    if run_jobs: supervisor.recover()

    @app.post('/v1/interpretations',status_code=201)
    def create(body:Create,c=Depends(caller),k=Depends(key)):
        return service.create(c,k,body.packet.model_dump(),body.policy,body.predecessor)

    @app.get('/v1/interpretations/{run_id}')
    def read(run_id:str,c=Depends(caller)): return service.read(c,run_id)

    @app.post('/v1/interpretations/{run_id}/configuration')
    def configure(run_id:str,body:Configure,c=Depends(caller),k=Depends(key)):
        return Controller(service).configure(c,k,run_id,body.members,body.repairs,body.verification_hashes)

    @app.post('/v1/interpretations/{run_id}/candidates',status_code=201)
    def propose(run_id:str,body:Proposal,c=Depends(caller),k=Depends(key)):
        return service.propose(c,k,run_id,body.model_dump())

    @app.post('/v1/interpretations/{run_id}/execute',status_code=202)
    def execute(run_id:str,c=Depends(caller),k=Depends(key)):
        def op(con):
            service._owner(con,c,run_id);run=service._run(con,run_id,True)
            service._get(con,run_id,'configuration','configuration')
            value=dict(run_id=run_id,status='QUEUED',authority='LOCAL_SYNTHETIC')
            service._save(con,'start',value,'start');return value
        result=db.mutate(c,k,dict(op='interpretation.execute',run_id=run_id),op)
        if run_jobs: supervisor.start(run_id)
        return result

    @app.post('/v1/interpretations/{run_id}/cancel')
    def cancel(run_id:str,c=Depends(caller),k=Depends(key)):
        return Reports(service).cancel(c,k,run_id)

    @app.post('/v1/interpretations/{run_id}/issues/{issue_id}/decision')
    def decide_issue(run_id:str,issue_id:str,body:IssueDecision,c=Depends(caller),k=Depends(key)):
        return service.decide_issue(c,k,run_id,issue_id,**body.model_dump())

    @app.post('/v1/interpretations/{run_id}/review')
    def review(run_id:str,body:Review,c=Depends(caller),k=Depends(key)):
        data=body.model_dump();data.pop('revision')
        return MeaningReview(service).decide(c,k,run_id,**data)

    @app.post('/v1/interpretations/{run_id}/inventory-review')
    def inventory_review(run_id:str,body:InventoryReview,c=Depends(caller),k=Depends(key)):
        return service.review_inventory(c,k,run_id,**body.model_dump())

    @app.post('/v1/interpretations/{run_id}/supersede')
    def supersede(run_id:str,body:Supersede,c=Depends(caller),k=Depends(key)):
        return MeaningReview(service).supersede(c,k,run_id,**body.model_dump())

    @app.post('/v1/interpretation-sources/{source_key}/invalidate')
    def invalidate(source_key:str,body:Invalidate,c=Depends(caller),k=Depends(key)):
        return service.invalidate_source(c,k,source_key,body.replacement.model_dump(),body.reason)

    @app.get('/interpretations',response_class=HTMLResponse,include_in_schema=False)
    def page(): return HTMLResponse(files('legalmath').joinpath('web/templates/interpretations.html').read_text())

    @app.get('/static/interpretations.js',include_in_schema=False)
    def script(): return Response(files('legalmath').joinpath('web/static/interpretations.js').read_text(),media_type='application/javascript')
