"""Source-bound STR contact witness and exact-decimal Java demonstrations."""
from copy import deepcopy
from run_assurance_successor import ROOT,read,save,sha,rel
from assurance_successor_phases import JDK,tests
from legalmath.canonical import digest
from legalmath.interpretation.assurance.duty_performance import project_contact,duty_state
from legalmath.interpretation.search.formal import bundle,RULE,project
from legalmath.java.manifest import build_candidate,run_java
from legalmath.ir.evaluate import evaluate


def run(work):
    from decision_live import load_case
    from assurance_round16_checks import decimal_fixtures
    from legalmath.java import decimal_boundary
    data=load_case('26ec2');packet=data['packet']
    needles=['will cease accepting STR submissions via STREAMS at','requiring urgent submission during']
    quotes=[]
    for needle in needles:
        matches=[u for u in packet['units'] if needle in u['text']]
        if not matches:raise RuntimeError('Retained operative source clause absent')
        quotes.extend({'unit_id':u['unit_id'],'quote':u['text']} for u in matches)
    start='2026-01-27T16:00:00.000000Z';end='2026-02-02T01:00:00.000000Z';at='2026-01-29T04:00:00.000000Z'
    assumptions=['Interpret the stated local clock times in Asia/Hong_Kong (UTC+08:00); this timezone is an explicit interpretation premise.',
       'Assess one named licensed firm and one named STR at a time; urgency is a supplied classification.',
       'A contact witness establishes the specified factual event only; filing, adequate communication and overall compliance remain separate.',
       'Completeness of all listed contact channels is a supplied evidence assertion, never inferred from an empty log.']
    policy={'policy_id':'sfc.26ec2.blackout.contact','source_packet_hash':digest(packet),'source_evidence':quotes,
        'counterparty_id':'jfiu','channels':['EMAIL','PHONE','FAX'],'from_inclusive':start,'until_exclusive':end,
        'time_interpretation':assumptions[0],'conditions':assumptions}
    def reading(ident,facts,result,description):
        return {'local_id':ident,'family':'time','subject':'One licensed firm and one STR',
         'statement':'[TRUE_IS_SATISFIED] '+description,'distinction':'Trigger and observed performance are separate questions',
         'citations':quotes,'assumptions':assumptions,'questions':['Does the observed communication substantively satisfy the required contact?'],
         'formalization':{'facts':[{'name':n,'type':'bool','meaning':meaning,'unit':'truth value',
             'source_unit_ids':[q['unit_id'] for q in quotes],'requires_judgment':True} for n,meaning in facts],
             'scope':'true','result':result,'result_type':'bool'}}
    readings={'trigger':reading('contact.trigger',[('licensed','Named actor is a licensed firm'),
        ('urgent','This STR requires urgent submission at the assessment instant'),('in_window','Assessment is within the declared blackout')],
        '(and licensed urgent in_window)','The conditional urgent-contact trigger holds.'),
       'performance':reading('contact.performance',[('contact_observed','Attributed JFIU contact for this STR through a listed channel by assessment, known by cutoff')],
        'contact_observed','The declared contact witness is observed.')}
    bundles={k:bundle(r,packet,start) for k,r in readings.items()}
    builds={k:build_candidate(b,work/k/'java',JDK) for k,b in bundles.items()}
    cover={'actor_id':'firm.a','counterparty_id':'jfiu','channels':['EMAIL','PHONE','FAX'],
        'coverage':{'str_id':'str.a','kinds':['CONTACT'],'from_inclusive':start,'through_inclusive':at,
                    'recorded_at':at,'evidence_ids':['fixture.complete.history']}}
    base={'actor_id':'firm.a','counterparty_id':'jfiu','channel':'EMAIL','event':{'event_id':'contact.a',
        'str_id':'str.a','kind':'CONTACT','related_event_id':None,'occurred_at':'2026-01-29T03:00:00.000000Z',
        'recorded_at':'2026-01-29T03:00:00.000000Z','status':'CONFIRMED','evidence_ids':['fixture.communication']}}
    specifications=[('same_actor_report','TRUE'),('different_actor','FALSE'),('different_recipient','FALSE'),
       ('different_str','FALSE'),('wrong_channel','FALSE'),('contact_after_assessment','FALSE'),
       ('record_not_yet_known','FALSE'),('conflicting_record','CONFLICT'),('missing_history','UNKNOWN'),
       ('partial_channel_history','UNKNOWN')]
    rows=[];requests={k:[] for k in bundles}
    def fact(status,value=None):
        if status=='UNKNOWN':return {'type':'bool','status':'unknown','reason':'MISSING'}
        if status=='CONFLICT':return {'type':'bool','status':'conflict','evidence_ids':['first','second']}
        return {'type':'bool','status':'known','value':value if value is not None else status=='TRUE',
                 'valid_from':start,'valid_until':end,'recorded_at':at,'evidence_ids':['fixture.attributed.projection']}
    for name,expected in specifications:
        c=deepcopy(base);cov=deepcopy(cover);cs=[c];covers=[cov]
        if name=='different_actor':c['actor_id']='firm.b'
        elif name=='different_recipient':c['counterparty_id']='other'
        elif name=='different_str':c['event']['str_id']='str.b'
        elif name=='wrong_channel':c['channel']='OTHER'
        elif name=='contact_after_assessment':c['event'].update(occurred_at='2026-01-29T05:00:00.000000Z',recorded_at='2026-01-29T05:00:00.000000Z')
        elif name=='record_not_yet_known':c['event']['recorded_at']='2026-01-29T05:00:00.000000Z'
        elif name=='conflicting_record':c['event']['status']='DISPUTED'
        elif name=='missing_history':cs=[];covers=[]
        elif name=='partial_channel_history':cs=[];cov['channels']=['EMAIL']
        inputs={'actor_id':'firm.a','str_id':'str.a','assessment_at':at,'known_at':at}
        projection=project_contact(packet,policy,cs,covers,**inputs)
        assert projection['status']==expected
        for k,b in bundles.items():
            facts={n:fact('TRUE') for n in ('licensed','urgent','in_window')} if k=='trigger' else {'contact_observed':fact(expected)}
            requests[k].append({'bundle':b,'snapshot':{'subject_id':'str.a','facts':facts},'rule_id':RULE,
                                'valid_at':at,'known_at':at,'mode':'draft'})
        rows.append({'case_id':name,'events':cs,'coverage':covers,'expected':expected,'projection':projection,
                     'assessment':inputs})
    java={k:run_java(builds[k]['jar'],reqs,JDK,builds[k]['class_name']) for k,reqs in requests.items()}
    for i,row in enumerate(rows):
        for k in bundles:
            q=requests[k][i];p=evaluate(q['bundle'],q['snapshot'],RULE,at,at)
            assert project(p)==project(java[k][i])
        assert java['trigger'][i]['status']=='TRUE' and java['performance'][i]['status']==row['expected']
        row['java']={k:java[k][i] for k in bundles};row['duty']=duty_state(java['trigger'][i],java['performance'][i])
    save(work/'contact-policy.json',policy);save(work/'readings.json',readings);save(work/'bundles.json',bundles)
    save(work/'requests.json',requests);save(work/'contact-results.json',rows);save(work/'java-builds.json',builds)
    from legalmath.java import contact_boundary
    host=contact_boundary.build(bundles['trigger'],bundles['performance'],policy,work/'contact-host',JDK)
    external=[{'profile':contact_boundary.PROFILE,**row['assessment'],'licensed':'TRUE','urgent':'TRUE',
               'contacts':row['events'],'coverage':row['coverage']} for row in rows]
    host_results=contact_boundary.run(host,external,JDK)
    for row,j in zip(rows,host_results):
        assert j['boundary_status']=='ACCEPTED' and j['projected_status']==row['expected']
        assert j['performance']['status']==row['java']['performance']['status']
        assert j['trigger']['status']==row['java']['trigger']['status']
        assert j['policy_hash']==digest(policy)
    save(work/'contact-host-results.json',{'build':host,'requests':external,'results':host_results})
    old=read(ROOT/'artifacts/interpretation/round15/phase-results.json')['P5']['result']['rational_extension']
    numeric=old['cases'][0]['bundle'];cases=decimal_fixtures()
    built=decimal_boundary.build(numeric,work/'decimal-java',JDK,profile=decimal_boundary.PROFILE)
    actual=decimal_boundary.run(built,[c['request'] for c in cases],JDK)
    for c,a in zip(cases,actual):
        assert a['boundary_status']==c['expected']['boundary_status']
        if a['boundary_status']=='ACCEPTED':assert a['result']['status']==c['expected']['status']
    save(work/'decimal-results.json',{'build':built,'cases':cases,'results':actual})
    counts=tests(work,['tests/assurance/test_successor_duties.py','tests/assurance/test_successor_contact_java.py','tests/assurance/test_round16.py'])
    return {'status':'ATTRIBUTED_CONTACT_AND_EXTERNAL_JAVA_DEMONSTRATED','contact_java_cases':2*len(rows),
        'decimal_java_cases':len(cases),'tests':counts,
        'parent':'node.c8e005eb37a38e37e6a09f74','parent_remains_retained':True,
        'contact_projection_runtime':'Independent Python and packaged Java both ingest the attributed raw contact history',
        'contact_host_java_cases':len(host_results),'contact_host_jar':host['jar'],
        'open_evidence':assumptions+['Other event kinds and complete parent satisfaction remain open.'],
        'release_eligible':False}
