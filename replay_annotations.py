"""Explicit reference-only review of four Gatecoin responses; no legal promotion."""
from copy import deepcopy
import sys
from pathlib import Path
sys.path[:0]=[str(Path(__file__).parent/'src'),str(Path(__file__).parent)]
from replay_baselines import product, read, ref, save, outcome, assert_request
from legalmath.interpretation.assurance import bounded_references as refs
from legalmath.interpretation.assurance.phased import context_references, context_disposition, group_review
from legalmath.interpretation.assurance.bounded_context import require

def main():
    p,base=product('gatecoin')
    folder=base/'calls/audit-context-disposition-gatecoin-32ac9ac15b66bae6e6868d04'
    request=read(folder/'request.json'); shape=read(folder/'schema.json')
    original=read(folder/'wire-response.json')['value']; wire=deepcopy(original)
    request[context_references.FIELD]=context_references.PROFILE
    prior=request['payload']['prior_needs'][0]['original_need']
    new=wire['context_needs'][0]
    require(len(wire['context_needs'])==1 and new['query']==prior['query']
        and new['record_ids']==prior['record_ids']
        and [r['locator'] for r in new['locators']]==[r['locator'] for r in prior['locators']],
        'Reviewed Gatecoin need identity changed')
    edits=[]
    for i,(row,old) in enumerate(zip(new['locators'],prior['locators'])):
        edits.append({'path':f'/context_needs/0/locators/{i}/index_hash',
            'before':row['index_hash'],'after':old['index_hash'],
            'basis':'Exact same prior query, source record and ordered legal locators.'})
        row['index_hash']=old['index_hash']
    for d in wire['need_dispositions']:d['answer_evidence']={'answer_field':d['answer_evidence']['path']}
    value=refs.resolve(wire,refs.prepare(request,shape),maximum_bytes=p.route.limits.decoded_output_bytes)
    raw=read(folder/'raw.json')['value']
    for field in ('verdict','reason','issues','support','source_gaps','considered'):
        require(value[field]==raw[field],'Substantive Gatecoin context change')
    def check_context(candidate):
        v=request['payload']; assert_request(p,request,'gatecoin')
        return context_disposition.validate(p,'gatecoin',candidate,v['answer'],v['item'],v['prior_needs'],
            request['records'],v['source_delivery_failures'])
    result=outcome(lambda:check_context(value))
    controls=[]
    for damage in ('accept_missing_need','unknown_document','lost_need'):
        bad=deepcopy(value)
        if damage=='accept_missing_need':bad['verdict']='ACCEPT'
        elif damage=='unknown_document':bad['context_needs'][-1]['locators'][0]['index_hash']='0'*64
        else:bad['context_needs']=[n for n in bad['context_needs'] if n!=prior]
        test=outcome(lambda:check_context(bad)); require(test['status']=='FAILED','Adverse context passed')
        controls.append({'damage':damage,**test})
    save('gatecoin-context-reviewed-selection.json',{'request':ref(folder/'request.json'),'raw':ref(folder/'raw.json'),
        'edits':edits,'result':result,'adverse_controls':controls,'raw_verdict':raw['verdict'],
        'provider_calls':0,'legal_acceptance':False})
    print('Gatecoin reviewed context',result,flush=True)
    rows=[]
    for key in ('repair-review-gatecoin-91d56081c52518c503f13a46',
                'repair-review-gatecoin-9b6c6a293c8e32858f928438',
                'repair-review-gatecoin-7fc8d0834f100b742504e381'):
        folder=base/'calls'/key; request=read(folder/'request.json'); original=read(folder/'raw.json')['value']
        assert_request(p,request,'gatecoin'); value=deepcopy(original); edits=[]
        decision=value['analyses'][0]['decision']
        if key.endswith(('91d56081c52518c503f13a46','9b6c6a293c8e32858f928438')):
            from legalmath.interpretation.assurance.answer_acceptance import MENTION,BRACKET_NUMBER
            require(not MENTION.search(decision['reason']) and not BRACKET_NUMBER.search(decision['reason'])
                and all(b['path']=='/reason' for b in decision['assertion_bindings']),
                'Reviewed unnumbered reason changed')
            edits.append({'path':'/analyses/0/decision/assertion_bindings',
                'before':deepcopy(decision['assertion_bindings']),'after':[],
                'basis':'Reason has no numbered proposition; ordinary support quotations remain unchanged.'})
            decision['assertion_bindings']=[]
        else:
            for i,need in enumerate(decision['context_needs']):
                invalid=[rid for rid in need['record_ids'] if rid not in p.route.records]
                if invalid:
                    require(need['kind']=='SOURCE_TEXT' and need['query'].strip() and need['locators'],
                        'No complete identification survives foreign-ID removal')
                    kept=[rid for rid in need['record_ids'] if rid in p.route.records]
                    edits.append({'path':f'/analyses/0/decision/context_needs/{i}/record_ids',
                        'before':deepcopy(need['record_ids']),'after':kept,
                        'basis':'Remove nonexistent IDs only; exact query, locators and need are retained.'})
                    need['record_ids']=kept
        def check(candidate):
            return group_review.validate(p,'gatecoin',candidate,request['required_considered'],request['records'])
        before=outcome(lambda:check(original)); after=outcome(lambda:check(value))
        # Retain all ordinary citations and substantive fields, and every need.
        for k in ('verdict','reason','issues','support','source_gaps'):
            require(decision[k]==original['analyses'][0]['decision'][k],'Changed substantive field '+k)
        rows.append({'call':key,'request':ref(folder/'request.json'),'raw':ref(folder/'raw.json'),
            'baseline':{k:v for k,v in before.items() if k!='value'},
            'simulation':{k:v for k,v in after.items() if k!='value'},'edits':edits,
            'raw_verdict':decision['verdict'],'provider_calls':0,'legal_acceptance':False})
    save('gatecoin-individual-reviewed-annotations.json',{'rows':rows,'provider_calls':0,'legal_acceptance':False})
    print('Gatecoin individuals',[(r['call'],r['simulation']) for r in rows],flush=True)

if __name__=='__main__':main()
