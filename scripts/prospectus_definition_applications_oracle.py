"""Independent complete-answer expectations and actual consumer attacks."""
from copy import deepcopy
from functools import lru_cache
import hashlib
import re

from scripts import prospectus_definition_integration as old
from scripts import prospectus_definition_integration_oracle as transport
from scripts.prospectus_typed_delta import equal
from legalmath.prospectus.successor.contracts import digest

PREP=old.AUTH/'reviews/definition-scope-repair-289'
LABELS=('absent','assisted','request-route')
READING_ERROR=transport.READING_ERROR
MODULE=transport.MODULE
CONTROLS=(
    'tax-to-makewhole','makewhole-to-tax','holder-to-issuer','affiliate-facts',
    'custodian-earlier','missed-phrase-drop','split-compound','statutory-referent',
    'normalization-offset','supplement-quote','premise-drop','uncertainty-drop',
    'grossup-drop','law-resolved','input-drop','input-forgery',
    'report-drop','dependency-resolve','q2-hidden','q2-subquestion-drop')
BATCH_SIZE=4


@lru_cache(maxsize=1)
def baseline():
    return old.retained('assisted-answer')


def expected(label):
    assert label in LABELS
    prior,answer=baseline()
    if label=='absent':
        return prior,answer
    supplement=old.read(PREP/'expected-supplement.json.gz')
    p=dict(prior)
    payload=deepcopy(prior['P3']['payload'])
    packet=deepcopy(payload['interpretation_input']['definition_sources'])
    packet['applications']={'profile':supplement['profile'],'profile_sha256':supplement['profile_sha256']}
    if label=='assisted':
        payload['interpretation_input']['definition_sources']=packet
    else:
        del payload['interpretation_input']['definition_sources']
        first=deepcopy(prior['P1']['payload'])
        first['request']['definition_sources']=packet
        p['P1']=transport.independent_seal(prior['P1'],first,{'request':digest(first['request'])})
        p['P2']=transport.independent_seal(prior['P2'],prior['P2']['payload'],{'P1':p['P1']['sha256']})
    payload['definition_sources']['application_supplement']=supplement
    p['P3']=transport.independent_seal(prior['P3'],payload,{'P1':p['P1']['sha256'],'P2':p['P2']['sha256']})
    p['P4']=transport.independent_seal(prior['P4'],prior['P4']['payload'],{'P1':p['P1']['sha256'],'P3':p['P3']['sha256']})
    p['P5']=transport.independent_seal(prior['P5'],prior['P5']['payload'],{'P2':p['P2']['sha256'],'P3':p['P3']['sha256']})
    answer=deepcopy(answer)
    answer['definition_sources']['application_supplement']=supplement
    answer['request_sha256']=digest(p['P1']['payload']['request'])
    answer['consumed_products']={k:v['sha256'] for k,v in p.items()}
    answer['report_sha256']=digest({k:v for k,v in answer.items() if k!='report_sha256'})
    return p,answer


def variants(run):
    from legalmath.prospectus.successor.definition_forms import discover_forms
    cases=old.read(PREP/'variant-cases.json')
    cases+= [{**v,'form':'Alpha Beta','regions':[[0,len(v['text'])]]}
             for v in old.read(PREP/'boundary-cases.json')]
    receipts=[]
    for case in cases:
        text=case['text']
        request={'text':text,'text_sha256':hashlib.sha256(text.encode()).hexdigest(),
                 'forms':[{'id':'case','text':case['form']}],'regions':case['regions']}
        actual=discover_forms(request)
        run.save(run.HERE/('variants/'+case['id']+'.json'),{'request':request,'actual':actual})
        equal([[r['start'],r['end']] for r in actual['uses']],case['expected'],'Whitespace boundary mismatch')
        for row in actual['uses']:
            raw=text[row['start']:row['end']]
            spans=[[row['start']+m.start(),row['start']+m.end()]
                   for m in re.finditer(r'\s+|[^\s]',raw)]
            equal(row['normalization_map'],spans,'Source normalization map differs')
            assert row['raw']==raw and row['governing_scope'] is None and row['meaning'] is None
        receipts.append(case['id'])
    text=(old.SOURCE/'selected-text.txt').read_text()
    request={'text':text,'text_sha256':hashlib.sha256(text.encode()).hexdigest(),
             'forms':old.read(PREP/'candidate-spec.json.gz')['forms'],'regions':[[0,len(text)]]}
    actual=discover_forms(request)
    run.save(run.HERE/'original-source-discovery.json.gz',actual)
    equal(actual,old.read(PREP/'expected-supplement.json.gz')['form_discovery'],'Original source proposals differ')
    gold=old.read(PREP/'original-amount-gold.json')
    equal([[r['start'],r['end']] for r in actual['uses'] if r['normalized_form'] in gold['forms']],
          gold['expected'],'Reproduced missing phrase not repaired')
    bad=[]
    base={'text':'Alpha Beta','text_sha256':hashlib.sha256(b'Alpha Beta').hexdigest(),
          'forms':[{'id':'case','text':'Alpha Beta'}],'regions':[[0,10]]}
    def refusal(label,value,message):
        try:
            discover_forms(value)
        except ValueError as exc:
            assert str(exc)==message,(label,str(exc))
            run.save(run.HERE/('variant-refusals/'+label+'.json'),{'request':value,'message':str(exc)})
            bad.append(label)
        else:
            raise ValueError('Invalid form input accepted: '+label)
    value=deepcopy(base); value['text_sha256']='0'*64
    refusal('changed-source',value,'Changed form source identity')
    value=deepcopy(base); value['forms']*=2
    refusal('duplicate-id',value,'Invalid supplied form identity')
    value=deepcopy(base); value['forms'][0]['text']='Alpha  Beta'
    refusal('noncanonical-form',value,'Form needs canonical single spaces')
    value=deepcopy(base); value['regions']=[[False,10]]
    refusal('boolean-interval',value,'Invalid form region interval')
    value=deepcopy(base); value['regions']=[[0,7],[6,10]]
    refusal('overlap',value,'Overlapping or invalid form region')
    value=deepcopy(base); value['regions']=[[0,11]]
    refusal('outside',value,'Overlapping or invalid form region')
    value={'text':'A '*4097,'forms':[{'id':'a','text':'A'}],'regions':[[0,8194]]}
    value['text_sha256']=hashlib.sha256(value['text'].encode()).hexdigest()
    refusal('proposal-bound',value,'Form proposal bound exceeded')
    value={'text':'A '*4096,'forms':[{'id':str(i),'text':'A'} for i in range(3)],'regions':[[0,8192]]}
    value['text_sha256']=hashlib.sha256(value['text'].encode()).hexdigest()
    refusal('association-bound',value,'Form association bound exceeded')
    return {'status':'PASS','finite_variants':len(receipts),'actual_invalid_refusals':len(bad),
            'exact_original_source_proposals':18,'original_amount_occurrences':5}


def mutate(case,p):
    semantic=deepcopy(p['P3']['payload'])
    report=semantic['definition_sources']
    supplement=report['application_supplement']
    rows={r['id']:r for r in supplement['applications']}
    if case=='tax-to-makewhole':
        rows['amount:11831']['meaning']=deepcopy(rows['amount:19119']['meaning'])
    elif case=='makewhole-to-tax':
        rows['amount:21547']['meaning']=deepcopy(rows['amount:21403']['meaning'])
    elif case=='holder-to-issuer':
        rows['holder:18238'].update(rule='holder',meaning=deepcopy(rows['holder:14004']['meaning']))
    elif case=='affiliate-facts':
        rows['affiliate:32403']['meaning']['affiliation_established']=True
    elif case=='custodian-earlier':
        rows['custodian:26168'].update(rule='custodian',meaning=deepcopy(rows['custodian:44711']['meaning']))
    elif case=='missed-phrase-drop':
        supplement['applications'].remove(rows['amount:21547'])
    elif case=='split-compound':
        rows['holder:17433'].update(rule='holder',meaning=deepcopy(rows['holder:14004']['meaning']))
    elif case=='statutory-referent':
        rows['affiliate:34069'].update(rule='affiliate',meaning=deepcopy(rows['affiliate:32403']['meaning']))
    elif case=='normalization-offset':
        supplement['form_discovery']['uses'][0]['normalization_map'][0][0]+=1
    elif case=='supplement-quote':
        supplement['source_supplement']['new_occurrence']['quote']+=' invented'
    elif case=='premise-drop':
        supplement['rules'][0]['premises']=[]
    elif case=='uncertainty-drop':
        record=next(r for r in report['records'] if r['id']=='M01-interest-period')
        record.update(status='RESOLVED',meaning_admitted=True)
    elif case=='grossup-drop':
        record=next(r for r in report['records'] if 'gross-up' in r['reading'].lower())
        record['reading']='Gross-up applies without exceptions.'
    elif case=='law-resolved':
        supplement['historical_law_resolved']=True
    elif case=='input-drop':
        del semantic['interpretation_input']['definition_sources']['applications']
    elif case=='input-forgery':
        semantic['interpretation_input']['definition_sources']['applications']['profile_sha256']='0'*64
    elif case=='report-drop':
        del report['application_supplement']
    elif case=='dependency-resolve':
        next(d for d in semantic['dependencies'] if d['id'].startswith(transport.PREFIX))['status']='RESOLVED'
    elif case=='q2-hidden':
        q=semantic['questions']['Q2']['subquestions']['possible_common']
        q['unresolved'].remove(transport.PREFIX+'M01-interest-period')
    elif case=='q2-subquestion-drop':
        del semantic['questions']['Q2']['subquestions']['common_only']
    else:
        raise ValueError('Unknown application control: '+case)
    return semantic


def refusal_expectation(case):
    if case=='input-forgery':
        return ('Definition application requires the exact reviewed profile','require',
                'legalmath.prospectus.successor.definition_applications')
    if case=='dependency-resolve':
        return ('Consumed definition dependencies differ from reconstruction','verify_consumed',MODULE)
    if case=='q2-hidden':
        return (transport.HIDDEN_ERROR,'verify_consumed',MODULE)
    if case=='q2-subquestion-drop':
        return (transport.SHAPE_ERROR,'verify_consumed',MODULE)
    return (READING_ERROR,'verify_consumed',MODULE)
