"""Exact prior reviewer replay and one corrected conditional-reference request."""
from copy import deepcopy
from pathlib import Path
import json
from legalmath.canonical import digest
from legalmath.interpretation.assurance.bounded_product import BoundedProduct, AUDIT
from legalmath.interpretation.assurance.bounded_context import Limits, require
from legalmath.interpretation.assurance.bounded_references import prepare, resolve
from legalmath.interpretation.assurance.phased.group_review import schema, validate
from legalmath.interpretation.assurance.phased.evidence_store import save_exact
from scripts.legal_integration_reopening_live import fixture
from scripts.legal_mission_execution import ref, read, verify


class NoCalls:
    live=False
    reference_transport=True
    def complete(self,*args,**kwargs):
        raise AssertionError('Retained response replay must not dispatch')


def replay(root,prior,directory,encode):
    rows=[];outcomes={};references=[]
    for name,mutation,missing in [('remote-exception',False,False),
        ('changed-exception',True,False),('missing-incorporated-rule',False,True)]:
        value=fixture(mutation,explicit_scope=True,missing_authority=missing)
        product=BoundedProduct(root,directory/name,NoCalls(),value,encode,limits=Limits())
        outcomes[name]={}
        for path in sorted((prior/'qualification'/name/'calls').iterdir()):
            if not path.is_dir():continue
            files={key:read(path/(key+'.json')) for key in
                ('request','schema','wire-response','raw','reference-binding','result')}
            request=files['request'];grouped=request['task']=='AUDIT_SOURCE_DEPENDENCY_ASSIGNMENTS'
            response_schema=schema(request['required_considered']) if grouped else AUDIT
            require(response_schema==files['schema'],'Retained control schema changed')
            prepared=prepare(request,response_schema)
            require(prepared==files['reference-binding'],'Retained control wire binding changed')
            decoded=resolve(files['wire-response']['value'],prepared,maximum_bytes=Limits().decoded_output_bytes)
            original=deepcopy(files['raw']['value'])
            if grouped:
                for row in original['analyses']:
                    for need in row['decision']['context_needs']:
                        need['record_ids']=[prepared['aliases'].get(i,i) for i in need['record_ids']]
                decisions=validate(product,'p14',decoded,request['required_considered'],request['records'])
                verdicts={identity:r['decision']['verdict'] for identity,r in decisions.items()}
            else:
                require(decoded['considered']==request['required_considered'],'Lost context bridge member')
                product.citations(decoded,request['records'])
                verdicts={identity:decoded['verdict'] for identity in decoded['considered']}
            require(decoded==original,'Decoder altered reasoning beyond exact typed IDs')
            for key in files:references.append(ref(root,path/(key+'.json')))
            label='supported' if path.name.startswith('supported-') else 'unsupported' if path.name.startswith('unsupported-') else 'bridge'
            outcomes[name][label]=list(verdicts.values())
            rows.append({'case':name,'call':path.name,'original_result':files['result'],
                'decoded':decoded,'verdicts':verdicts,'provider_calls':0})
    require(all(outcomes[n]['supported'] and all(v=='ACCEPT' for v in outcomes[n]['supported']) and
        any(v in ('REJECT','UNRESOLVED') for v in outcomes[n]['unsupported'])
        for n in ('remote-exception','changed-exception')),'Retained exception control no longer passes')
    require(outcomes['remote-exception']['bridge']==['REJECT'],'Retained explicit context control changed')
    require(any(v=='REJECT' for v in outcomes['missing-incorporated-rule']['supported']) and
        any(v=='REJECT' for v in outcomes['missing-incorporated-rule']['unsupported']),
        'Incomplete reference or unsupported answer lost adverse decision')
    result={'profile':'exact-grouped-control-replay.v1','valid':True,'rows':rows,
        'missing_supported_remains_rejected':True,'unsupported_rejected':True,
        'new_provider_calls':0,'evidence':references,'qualification_complete':False}
    save_exact(directory/'result.json',result)
    return result


def qualify(service):
    from scripts import legal_integration_phased_live as live
    from scripts.legal_integration_master import ROOT,PROGRAM
    from scripts.legal_integration_route_repair import WORK
    from legalmath.interpretation.assurance.phased.controls import control_answers
    revision=read(ROOT/PROGRAM)['route_context_repair']
    verify(ROOT,revision['qualification_replay'])
    retained=read(ROOT/revision['qualification_replay']['path'])
    require(retained['valid'],'Retained grouped controls are invalid')
    for reference in retained['evidence']:verify(ROOT,reference)
    envelope=fixture(False,explicit_scope=True,missing_authority=True)
    product=live.session(ROOT/WORK/'live/qualification/missing-conditional',service,
        owner='qualification-missing-conditional',envelope=envelope,maximum_calls=1)
    records=[r for r in product.route.records.values() if r['kind']=='source']
    answer=dict(control_answers(records,missing=True))['supported']
    reviews=product.audit_answer('p14',envelope['original_questions'][0],answer,[],prefix='supported-')
    passed=bool(reviews) and all(r['status']=='VALIDATED' and r['value']['verdict']=='ACCEPT' for r in reviews)
    result={'qualified':passed,'complete':True,'new_logical_call_ceiling':1,
        'retained_controls':revision['qualification_replay'],'corrected_reference':answer,'reviews':reviews,
        'scope':'Reviewer qualification on fixed synthetic controls; original actual product answers remain required.'}
    save_exact(ROOT/WORK/'live/qualification/result.json',result)
    return {'qualification':ref(ROOT,WORK/'live/qualification/result.json'),
        '_node_status':'SUCCEEDED' if passed else 'BLOCKED',
        '_conclusion':'Corrected missing-authority conditional reference '+('accepted.' if passed else 'not accepted; adverse results retained.')}
