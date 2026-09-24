"""Search transport; model access is supplied by server configuration, never request data."""
from threading import Thread,Lock
from pathlib import Path
from fastapi import Depends
from ..contracts import Strict,Packet,Text,Id,Hash
from typing import Literal
from pydantic import Field
from .models import Settings
from .engine import create_search,Search
from .formal import Comparisons
from . import annotations,alignment_review
from .alignment import Correspondence
from ...errors import LegalMathError


class Start(Strict):
    packet: Packet
    settings: Settings


class Execute(Strict):
    at: Text
    domain: dict | None = None


class AnnotationAssignment(Strict):
    reviewers: list[str]


class AnnotationSubmission(Strict):
    annotations: list[annotations.Annotation]
    attests_independent: bool


class AnnotationFreeze(Strict):
    dispositions: dict[str,annotations.Adjudication]
    rationale: Text


class AlignmentSubmission(Strict):
    left_node_id: Id
    right_node_id: Id
    proposal: Correspondence


class AlignmentDecision(Strict):
    proposal_hash: Hash
    decision: Literal['ACCEPT_FOR_CONDITIONAL_ANALYSIS','REJECT','UNRESOLVED']
    rationale: Text
    evidence_refs: list[Id] = Field(min_length=1,max_length=500)


def install(app,service,caller,key,jdk,provider,run_jobs):
    threads={};lock=Lock()

    @app.post('/v1/interpretation-search',status_code=201)
    def create(body:Start,c=Depends(caller),k=Depends(key)):
        return create_search(service,c,k,body.packet.model_dump(),body.settings)

    @app.post('/v1/interpretation-search/{run_id}/execute',status_code=202)
    def execute(run_id:str,body:Execute,c=Depends(caller),k=Depends(key)):
        if provider is None or jdk is None:raise LegalMathError('E_DEPENDENCY',details='Server has not authorized model access/toolchain')
        from ...domain import timestamp
        timestamp(body.at)
        def op(con):
            service._owner(con,c,run_id);service._run(con,run_id,True)
            service._get(con,run_id,'search-config','config')
            existing=service._list(con,run_id,'search-start')
            value={'run_id':run_id,'at':body.at,'domain':body.domain,'status':'QUEUED'}
            if existing and existing[0]!=value:raise LegalMathError('E_JOB_STATE')
            service._save(con,'search-start',value,'start');return value
        value=service.db.mutate(c,k,{'op':'search.execute','run_id':run_id,**body.model_dump()},op)
        if run_jobs:
            with lock:
                if run_id not in threads or not threads[run_id].is_alive():
                    checker=Comparisons(service.db.root/'search-java'/run_id,jdk,body.at,body.domain)
                    search=Search(service,c,run_id,provider,checker)
                    t=Thread(target=search.drive,daemon=True,name='search-'+run_id);threads[run_id]=t;t.start()
        return value

    @app.post('/v1/interpretation-search/{run_id}/annotation-assignment')
    def assign(run_id:str,body:AnnotationAssignment,c=Depends(caller),k=Depends(key)):
        return annotations.assign(service,c,k,run_id,body.reviewers)

    @app.get('/v1/interpretation-search/{run_id}/annotation-packet')
    def packet(run_id:str,c=Depends(caller)):
        return annotations.reviewer_packet(service,c,run_id)

    @app.post('/v1/interpretation-search/{run_id}/annotations')
    def submit(run_id:str,body:AnnotationSubmission,c=Depends(caller),k=Depends(key)):
        return annotations.submit(service,c,k,run_id,[a.model_dump() for a in body.annotations],body.attests_independent)

    @app.post('/v1/interpretation-search/{run_id}/reference-freeze')
    def freeze(run_id:str,body:AnnotationFreeze,c=Depends(caller),k=Depends(key)):
        return annotations.freeze(service,c,k,run_id,
            {unit:value.model_dump() for unit,value in body.dispositions.items()},body.rationale)

    @app.get('/v1/interpretation-search/{run_id}/fact-correspondence')
    def correspondence_packet(run_id:str,left_node_id:str,right_node_id:str,c=Depends(caller)):
        return alignment_review.packet(service,c,run_id,left_node_id,right_node_id)

    @app.post('/v1/interpretation-search/{run_id}/alignments',status_code=201)
    def propose_alignment(run_id:str,body:AlignmentSubmission,c=Depends(caller),k=Depends(key)):
        return alignment_review.propose(service,c,k,run_id,body.left_node_id,body.right_node_id,body.proposal.model_dump())

    @app.get('/v1/interpretation-search/{run_id}/alignments/{alignment_id}')
    def read_alignment(run_id:str,alignment_id:str,c=Depends(caller)):
        return alignment_review.read(service,c,run_id,alignment_id)

    @app.post('/v1/interpretation-search/{run_id}/alignments/{alignment_id}/analyze')
    def analyze_alignment(run_id:str,alignment_id:str,body:Execute,c=Depends(caller),k=Depends(key)):
        return alignment_review.analyze(service,c,k,run_id,alignment_id,body.at,body.domain,jdk)

    @app.post('/v1/interpretation-search/{run_id}/alignments/{alignment_id}/review')
    def review_alignment(run_id:str,alignment_id:str,body:AlignmentDecision,c=Depends(caller),k=Depends(key)):
        return alignment_review.review(service,c,k,run_id,alignment_id,body.proposal_hash,
            body.decision,body.rationale,body.evidence_refs)
