"""Catalog-bound public examples; factor assignments remain defeasible proposals."""
from copy import deepcopy
from pathlib import Path
from typing import Literal
from pydantic import Field
from ...canonical import digest, loads
from ...errors import LegalMathError
from ...sources.anchors import make_span
from ..contracts import Strict, Id, Hash, Text, parse
from ..search.models import Quote, DIMENSIONS
from .authorities import Anchor, iso_date
from .arguments import Proposition, case_moves
from .semantics import check_quotes


class Factor(Strict):
    factor_id: Id
    description: Text
    evidence: list[Anchor] = Field(min_length=1,max_length=12)


class Example(Strict):
    example_id: Id
    kind: Literal['OFFICIAL_EXAMPLE', 'CASE_LAW', 'HYPOTHETICAL']
    provision_id: Id
    issue_id: Id
    issue_description: Text
    factors: list[Factor] = Field(min_length=1,max_length=30)
    outcome: Proposition
    outcome_description: Text
    outcome_evidence: list[Anchor] = Field(min_length=1,max_length=12)
    derivation: Text


class Registry(Strict):
    version: Literal['example-registry.v1']
    authority_catalog_hash: Hash
    examples: list[Example] = Field(max_length=100)


class ExampleScope(Strict):
    issuer: Text
    jurisdiction: Text
    issue_ids: list[Id] = Field(min_length=1,max_length=20)


class Target(Strict):
    candidate_id: Id
    issue_id: Id
    factors: list[Id] = Field(min_length=1,max_length=30)
    outcome: Proposition
    evidence: list[Quote] = Field(min_length=1,max_length=12)


class ExampleQueries(Strict):
    queries: list[Target] = Field(max_length=20)
    questions: list[Text] = Field(max_length=30)


class ExampleRegistry:
    def __init__(self,value,catalog):
        self.value=parse(Registry,value);self.catalog=catalog;self.hash=digest(self.value)
        if self.value['authority_catalog_hash']!=catalog.hash:raise LegalMathError('E_STALE_REVIEW')
        self.records={e['example_id']:e for e in self.value['examples']}
        if len(self.records)!=len(self.value['examples']):raise LegalMathError('E_DUPLICATE_ID')
        meanings={}
        for example in self.records.values():
            p=catalog.provisions.get(example['provision_id'])
            if p is None:raise LegalMathError('E_REFERENCE')
            a=catalog.authorities[p['authority_id']]
            if example['kind']=='CASE_LAW' and a['kind']!='CASE_LAW':
                raise LegalMathError('E_AUTHORITY',details='A regulator FAQ is not a court decision')
            if example['kind']=='OFFICIAL_EXAMPLE' and a['kind'] not in ('FAQ','OFFICIAL_EXAMPLE','CIRCULAR'):
                raise LegalMathError('E_AUTHORITY',details='Register actual sourced examples, not arbitrary Code clauses')
            ids=[f['factor_id'] for f in example['factors']]
            if len(ids)!=len(set(ids)):raise LegalMathError('E_DUPLICATE_ID')
            for factor in example['factors']:
                key=(example['issue_id'],factor['factor_id'])
                if key in meanings and meanings[key]!=factor['description']:raise LegalMathError('E_REFERENCE')
                meanings[key]=factor['description']
            anchors=[*example['outcome_evidence'],*[anchor for factor in example['factors'] for anchor in factor['evidence']]]
            catalog._verify_anchors(anchors)
            for anchor in anchors:
                if anchor['edition_id']!=p['edition_id'] or not any(
                        r['anchor']['start']<=anchor['start']<anchor['end']<=r['anchor']['end'] for r in p['regions']):
                    raise LegalMathError('E_REFERENCE',details='Example evidence must lie in its named retained provision')

    @classmethod
    def load(cls,path,catalog):return cls(loads(Path(path).read_bytes()),catalog)

    def retrieve(self,scope,at,*,maximum=20):
        scope=parse(ExampleScope,scope);when=str(iso_date(at[:10]));rows=[];excluded=[]
        if type(maximum)is not int or not 0<=maximum<=100:raise LegalMathError('E_RESOURCE_LIMIT')
        for e in self.records.values():
            p=self.catalog.provisions[e['provision_id']];edition=self.catalog.editions[p['edition_id']]
            a=self.catalog.authorities[p['authority_id']]
            reason=None
            if e['issue_id'] not in scope['issue_ids']:reason='DIFFERENT_ISSUE'
            elif a['issuer']!=scope['issuer'] or a['jurisdiction']!=scope['jurisdiction']:reason='DIFFERENT_AUTHORITY_SCOPE'
            elif e['kind']=='HYPOTHETICAL':reason='HYPOTHETICAL_NOT_AUTHORITY'
            elif p['edition_id'] not in self.catalog.documents or not self.catalog._available_evidence(a['identity_evidence']):reason='MISSING_SOURCE'
            elif edition['temporal_status']=='DOCUMENTED_INTERVAL' and (when<edition['effective_from'] or
                    (edition['effective_until'] and when>=edition['effective_until'])):reason='WRONG_EDITION'
            elif len(rows)>=maximum:reason='EXAMPLE_LIMIT'
            if reason:
                excluded.append({'example_id':e['example_id'],'reason':reason});continue
            status='UNKNOWN_VERSION' if edition['temporal_status']=='UNKNOWN' else 'PUBLISHER_INTERVAL_MATCH'
            rows.append({'example':deepcopy(e),'authority':deepcopy(a),'edition':deepcopy(edition),
                'temporal_status':status,'context_status':p['context_status'],
                'unresolved_references':p['unresolved_references'],
                'legal_applicability_proved':False,'factor_materiality_proved':False})
        result={'registry_hash':self.hash,'catalog_hash':self.catalog.hash,'scope':scope,'at':at,
            'examples':rows,'excluded':excluded,'maximum':maximum,'candidate_pruning_authorized':False}
        return {**result,'retrieval_hash':digest(result)}

    def packet(self,retrieval,target_packet):
        # The complete retained provision accompanies each derived factor; preserve
        # target and example evidence as distinct units, with original byte hashes.
        result=deepcopy(target_packet);present={u['unit_id'] for u in result['units']}
        for row in retrieval['examples']:
            p=self.catalog.provisions[row['example']['provision_id']];doc=self.catalog.documents[p['edition_id']]
            for region in p['regions']:
                a=region['anchor'];uid='example.'+digest(a)[:24]
                if uid in present:continue
                present.add(uid)
                result['units'].append({'unit_id':uid,'locator':p['locator']+' / '+region['region_id'],
                    'text':a['quote'],'normative':True,
                    'span':make_span('s.'+uid,p['edition_id'],doc['data'],doc['text'],a['start'],a['end'])})
        if len(result['units'])>500 or sum(len(u['text'].encode()) for u in result['units'])>200000:
            raise LegalMathError('E_RESOURCE_LIMIT')
        return result

    def reason(self,retrieval,queries,target_packet,candidate_ids):
        if retrieval!=self.retrieve(retrieval['scope'],retrieval['at'],maximum=retrieval['maximum']):
            raise LegalMathError('E_STALE_REVIEW',details='Changed registry retrieval')
        queries=parse(ExampleQueries,queries);packet=self.packet(retrieval,target_packet);cases=[];questions=list(queries['questions'])
        for cid in set(candidate_ids)-{q['candidate_id'] for q in queries['queries']}:
            questions.append('No sourced example-factor comparison covers candidate '+cid)
        for row in retrieval['examples']:
            e=row['example'];evidence=[]
            for a in [*e['outcome_evidence'],*[a for f in e['factors'] for a in f['evidence']]]:
                p=self.catalog.provisions[e['provision_id']]
                region=next(r for r in p['regions'] if r['anchor']['start']<=a['start'] and a['end']<=r['anchor']['end'])
                evidence.append({'unit_id':'example.'+digest(region['anchor'])[:24],'quote':a['quote']})
            evidence=list({digest(x):x for x in evidence}.values())
            case={'case_id':e['example_id'],'authority':e['kind'],'outcome':e['outcome'],
                'factors':[f['factor_id'] for f in e['factors']],'evidence':evidence,'rationale':e['derivation']}
            check_quotes(evidence,packet);cases.append((row,case))
        moves=[]
        for query in queries['queries']:
            if query['candidate_id'] not in candidate_ids or query['issue_id'] not in retrieval['scope']['issue_ids']:
                raise LegalMathError('E_REFERENCE')
            if len(set(query['factors']))!=len(query['factors']):raise LegalMathError('E_DUPLICATE_ID')
            check_quotes(query['evidence'],target_packet)
            selected=[(row,case) for row,case in cases if row['example']['issue_id']==query['issue_id']]
            vocabulary={f for _,case in selected for f in case['factors']}
            atoms={case['outcome']['atom'] for _,case in selected}
            if not set(query['factors'])<=vocabulary or query['outcome']['atom'] not in atoms:
                raise LegalMathError('E_REFERENCE',details='Use declared issue factor and outcome identifiers')
            for row,case in selected:
                for move in case_moves(case,query['factors'],query['outcome'],packet,countercases=[c for _,c in selected]):
                    moves.append({**move,'candidate_id':query['candidate_id'],'query_evidence':query['evidence'],
                        'registry_hash':self.hash,'retrieval_hash':retrieval['retrieval_hash'],
                        'temporal_status':row['temporal_status'],'status':'CONDITIONAL_PROPOSED_ANALOGY',
                        'source_factor_mapping_proved':False,'outcome_interpretation_proved':False})
                questions.append('Check target-factor materiality and outcome meaning for '+case['case_id'])
                if row['temporal_status']=='UNKNOWN_VERSION':questions.append('Establish applicable edition for '+case['case_id'])
                questions.extend(row['unresolved_references'])
        return {'status':'UNRESOLVED' if questions or moves else 'NO_APPLICABLE_EXAMPLE',
            'retrieval':retrieval,'queries':queries,'moves':moves,'questions':sorted(set(questions)),
            'evidence_packet':packet,'release_eligible':False,'candidate_pruning_authorized':False}

    def dependencies(self,scope,at):
        retrieval=self.retrieve(scope,at)
        relevant={e['example_id'] for e in self.records.values() if e['issue_id'] in scope['issue_ids']}
        body={k:retrieval[k] for k in ('scope','at','examples')}
        body['excluded']=[e for e in retrieval['excluded'] if e['example_id'] in relevant]
        return {'example-registry.'+digest(scope)[:24]:digest(body)}
