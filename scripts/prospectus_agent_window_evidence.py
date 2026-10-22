"""Conditional source-backed BASF notice-window evidence, not actual events."""
from copy import deepcopy
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import VERSION
from legalmath.prospectus.successor.occurrences import anchor
from scripts.prospectus_calendar_evidence import load,save,require
from scripts.prospectus_calendar_oracle import expected as minimum
from scripts.prospectus_explanation_oracle import check_row
from scripts.prospectus_agent_window_prepare import REVIEW,ORIGINAL,PRIOR

NOW='2026-10-17T00:00:00Z'
LATER='2026-10-18T00:00:00Z'
VALUES=['2024-01-01','2024-01-30','2024-01-31','2024-02-15','2024-02-16',
    '2024-01-01T00:00:00Z','2024-01-30T23:59:59.999999Z',
    '2024-01-31T00:00:00Z','2024-02-15T00:00:00Z','2024-02-15T00:00:00.000001Z',
    'insolvency=True; hypothetical only','insolvency=False; hypothetical only',
    'section13_notice=True; hypothetical only','section13_notice=False; hypothetical only']


def independent(calculation):
    result=minimum(calculation['start']['value'],calculation['end']['value'],
                   calculation['convention'],calculation['days'])
    operator=calculation.get('operator','GE')
    require(operator in {'GE','LE'},'Unknown independent comparison')
    comparison=result['exact_comparison']
    comparison['operator']=operator
    left,right=int(comparison['left']),int(comparison['right'])
    result['status']='YES' if (left<=right if operator=='LE' else left>=right) else 'NO'
    require(calculation['status']==result['status'] and calculation['exact_comparison']==comparison,
            'Independent notice interval disagrees')
    return result


def setup(root,folder):
    source=load(root/REVIEW/'selected-source.json')
    original=next(x for x in load(root/ORIGINAL/'agent-source-readings.json') if x['id']==source['id'])
    require(source==original,'Selected source altered')
    rule=folder/'selected-contract.txt'
    rule.write_text(source['quote'])
    observations=folder/'hypothetical-events.txt'
    observations.write_text(chr(12).join(VALUES))
    bundle={'instrument_id':'basf-agent-notice-precondition-diagnostic','purpose':'review','issue_date':NOW,
        'effective_at':NOW,'known_at':NOW,'dependencies':[],'documents':[
            {'id':'contract','path':str(rule.relative_to(root)),'sha256':service.digest(rule.read_bytes()),'format':'text',
             'language':'de','authority':'Exact selected original BASF source sentence; partial derivative, not full contract',
             'known_from':NOW,'document_date':NOW},
            {'id':'hypotheses','path':str(observations.relative_to(root)),'sha256':service.digest(observations.read_bytes()),
             'format':'text','language':'en','authority':'Explicit synthetic dates and events, not observed holder/agent facts',
             'known_from':NOW,'document_date':NOW}]}
    request={'version':VERSION,'bundle':bundle}
    p1=service.source_product(request,root);p2=service.construction_product(p1,root);p3=service.interpretation_product(p1,p2)
    ps={'P1':p1,'P2':p2,'P3':p3,'P5':service.financial_product(p1,p2,p3)}
    def src(value):
        unit=next(u for u in p1['payload']['graph']['units'] if u['raw']==value)
        return anchor(unit,0,len(value))
    basis={'id':'notice_precondition','authority':'Conditional contractual notice precondition only; not a finding of legally effective change',
        'jurisdiction':'Supplied BASF contract reading; applicable historical law unresolved','edition':'Selected September2022 clause; no currentness claim',
        'source':src(source['quote']),'valid_from':NOW,'known_from':NOW,'instrument_id':bundle['instrument_id'],
        'premises':{'any':['insolvency',{'all':['section13_notice','at_least30','at_most45']}]}}
    times={'valid_from':NOW,'known_from':NOW,'observed_at':NOW}
    identity={'instrument_id':bundle['instrument_id'],'jurisdiction':basis['jurisdiction'],'event_id':'hypothetical-agent-change'}
    def operand(value,role):return {**identity,**times,'value':value,'role':role,'source':src(value)}
    calculations=[]
    for name,days,operator in [('at_least30',30,'GE'),('at_most45',45,'LE')]:
        calculations.append({**identity,**times,'id':name+'-dates','basis_id':basis['id'],'name':name,
            'source':basis['source'],'rule_reading':'Supplied inclusive30-to45-day notice interval; necessary precondition only',
            'convention':'CIVIL_DATE_GAP','days':days,'operator':operator,
            'start':operand('2024-01-01','holders_informed'), 'end':operand('2024-01-31','proposed_change')})
    def fact(name,value):return {**times,'name':name,'basis_id':basis['id'],'instrument_id':bundle['instrument_id'],
        'jurisdiction':basis['jurisdiction'],'value':value,'source':src(name+'='+str(value)+'; hypothetical only')}
    data={'law_bases':[basis],'facts':[fact('insolvency',False),fact('section13_notice',True)],
        'calendar_facts':calculations,'law_explanation':'subset-minimal.v1'}
    save(folder/'source-provenance.json',{'original_review':REVIEW+'/selected-source.json','original_sources':source['source_uses'],
        'original_images':load(root/REVIEW/'review.json')['original_images'],'derivative_text_equal':True,
        'selected_source_only':True,'actual_event_established':False,'calculation_agent_office':'UNRESOLVED'})
    return ps,data,operand,fact


def cohort(root,attempt):
    folder=attempt/'notice';folder.mkdir()
    ps,data,operand,fact=setup(root,folder)
    save(folder/'common-products.json.gz',ps)
    trials=[]
    for label,end,expected in [('29-days','2024-01-30','NO'),('30-days','2024-01-31','YES'),
        ('45-days','2024-02-15','YES'),('46-days','2024-02-16','NO')]:
        d=deepcopy(data)
        for c in d['calendar_facts']:c['end']=operand(end,'proposed_change')
        trials.append((label,d,expected))
    for label,end,expected in [('30-minus-microsecond','2024-01-30T23:59:59.999999Z','NO'),
        ('30-elapsed','2024-01-31T00:00:00Z','YES'),('45-elapsed','2024-02-15T00:00:00Z','YES'),
        ('45-plus-microsecond','2024-02-15T00:00:00.000001Z','NO')]:
        d=deepcopy(data)
        for c in d['calendar_facts']:
            c.update(convention='ELAPSED_24_HOUR_DAYS',start=operand('2024-01-01T00:00:00Z','holders_informed'),end=operand(end,'proposed_change'))
        trials.append((label,d,expected))
    d=deepcopy(data)
    for c in d['calendar_facts']:c['convention']='CLEAR_CIVIL_DAYS'
    trials.append(('explicit-clear-days',d,'NO'))
    for part in ('start','end'):
        d=deepcopy(data)
        for c in d['calendar_facts']:c[part]=None
        trials.append(('missing-'+part,d,'UNKNOWN'))
    d=deepcopy(data);d['facts'][1]=fact('section13_notice',False);trials.append(('no-section13-notice',d,'NO'))
    d=deepcopy(data);d['facts']=[];trials.append(('missing-events',d,'UNKNOWN'))
    d=deepcopy(data);d['facts']=[fact('insolvency',True)]
    for c in d['calendar_facts']:c['start']=None;c['end']=None
    trials.append(('insolvency-exception',d,'YES'))
    d=deepcopy(data);d['facts'].append(fact('insolvency',True));trials.append(('conflicting-insolvency',d,'CONFLICT'))
    d=deepcopy(data);d['facts'][0]['observed_at']=LATER;d['facts'][1]=fact('section13_notice',False)
    trials.append(('future-insolvency-not-used',d,'UNKNOWN'))
    d=deepcopy(data);d['law_bases'][0]['known_from']=LATER;trials.append(('inactive-authority',d,'UNKNOWN'))
    d=deepcopy(data);d['calendar_facts'][1]['observed_at']=LATER;trials.append(('future-upper-rule',d,'UNKNOWN'))
    d=deepcopy(data);d['law_bases'].append({**deepcopy(d['law_bases'][0]),'id':'clear-reading'})
    d['facts'] += [{**deepcopy(f),'basis_id':'clear-reading'} for f in d['facts']]
    d['calendar_facts'] += [{**deepcopy(c),'id':c['id']+'-clear','basis_id':'clear-reading','convention':'CLEAR_CIVIL_DAYS'} for c in d['calendar_facts']]
    d['law_relation']='ALTERNATIVE_READINGS';trials.append(('alternative-conventions',d,'UNKNOWN'))
    results=[];comparisons=0
    for label,d,expected in trials:
        p4=service.law_product(ps['P1'],ps['P3'],law_input=d)
        q=p4['payload']['question'];require(q['status']==expected,'Wrong notice-precondition result: '+label)
        proofs=[]
        for row in q['value']:
            for c in row['calendar_calculations']:
                if c['status'] in {'YES','NO'}:independent(c);comparisons+=1
            proofs.append(check_row(row,d,ps['P1']['payload']['request']['bundle'],ps['P1']['payload']['graph']))
        answers={}
        for mode in ('current','frozen'):
            a=service.consume({**ps,'P4':p4},root,mode=mode)
            require(a['questions']['Q4']==q and a['mode']=='ASSISTED' and not a['may_execute_transaction']
                and not a['independent_legal_acceptance'],'Conditional result promoted or lost')
            answers[mode]=a
        save(folder/(label+'.json.gz'),{'input':d,'P4':p4,'answers':answers,'proofs':proofs})
        results.append({'case':label,'status':q['status'],'proofs':proofs})
    controls=[]
    for attack in ('operator','rule-identity','event','subject','source'):
        d=deepcopy(data)
        if attack=='operator':d['calendar_facts'][1]['operator']='LT'
        if attack=='rule-identity':
            c=deepcopy(d['calendar_facts'][1]);c['id']='different-rule';c['operator']='GE';d['calendar_facts'].append(c)
        if attack=='event':d['calendar_facts'][1]['event_id']='different-event'
        if attack=='subject':d['calendar_facts'][1]['instrument_id']='different-bond'
        if attack=='source':d['calendar_facts'][1]['source']['quote']='forged'
        try:service.law_product(ps['P1'],ps['P3'],law_input=d)
        except ValueError as error:controls.append({'attack':attack,'refused':str(error)})
        else:raise ValueError('Notice control accepted: '+attack)
    save(attempt/'notice-evidence.json',{'cases':results,'controls':controls})
    return {'cases':len(results),'actual_current_frozen_answers':len(results)*2,'independent_calculations':comparisons,'actual_refusals':len(controls)}


def regression(root,attempt,cohort):
    from scripts.prospectus_explanation_evidence import ORIGINAL as LAW_ORIGINAL,CALENDAR
    base=LAW_ORIGINAL if cohort=='original' else CALENDAR
    ps=load(root/base/'common-products.json.gz')
    cases=None if cohort=='calendar' else load(root/LAW_ORIGINAL/'favorable-deposit-P4.json.gz')['payload']['cases']
    paths=sorted((root/PRIOR/cohort).glob('*.json.gz'))
    require(len(paths)==(21 if cohort=='original' else 19),'Wrong prior record count')
    checks=[]
    for path in paths:
        expected=load(path)
        p4=service.law_product(ps['P1'],ps['P3'],cases=cases,law_input=expected['input'])
        require(p4==expected['P4'],'Old P4 explanation changed')
        for mode in ('current','frozen'):
            actual=service.consume({**ps,'P4':p4},root,mode=mode)
            require(actual==expected['answers'][mode],'Prior whole explanation answer changed')
        checks.append({'case':path.stem,'P4_equal':True,'current_equal':True,'frozen_equal':True})
    save(attempt/(cohort+'-regression.json'),checks)
    return {'complete_original_records':len(checks),'complete_answers':2*len(checks)}
