"""Independent026/027 expectations and actual ordinary-consumer controls.

Preparation inspects source and syntax only. Candidate admission, membership and
verification are evaluated only after the authority admits the frozen method.
"""
import ast
from copy import deepcopy
from functools import lru_cache
import hashlib
from pathlib import Path
import subprocess
import sys

from scripts import prospectus_definition_integration as run
from scripts.prospectus_typed_delta import equal
from legalmath.prospectus.successor.contracts import digest

PREPARATION = ('prepare', 'stage-candidate', 'preflight', 'resource-audit', 'propose')
LABELS = ('absent', 'assisted', 'request-route')
PREFIX = 'definition-source:'
MODULE = 'legalmath.prospectus.successor.definition_scopes'
SERVICE = 'legalmath.prospectus.successor.service'
IDS = tuple(r['id'] for r in run.read(run.PREP/'expected-spec.json.gz')['records'])
READING_ERROR = 'Consumed definition source differs from reconstruction'
PROFILE_ERROR = 'Definition source requires the exact registered profile'
SHAPE_ERROR = 'Consumed definition question shape differs from declared questions'
HIDDEN_ERROR = 'Consumed definition question hides or invents uncertainty'
RESOLVE_ERROR = 'Consumed definition question resolves uncertainty'
CONTROLS = {**{'reading-'+key:(READING_ERROR,'verify_consumed',MODULE) for key in IDS},
    **{key:(READING_ERROR,'verify_consumed',MODULE) for key in (
        'report-drop','record-drop','record-resolve','alternative-drop','alternative-extent',
        'alternative-reason','interval-quote','interval-offset','source-piece',
        'provenance-gap','lexical-drop','lexical-meaning','binding-graph','governing-meaning')},
    'input-drop':('Consumed definition source lacks supplied evidence','verify_consumed',MODULE),
    'input-forgery':(PROFILE_ERROR,'admit',MODULE),
    **{key:('Consumed definition dependencies differ from reconstruction','verify_consumed',MODULE)
       for key in ('dependency-drop','dependency-resolve')},
    **{key:(HIDDEN_ERROR,'verify_consumed',MODULE) for key in (
        'q1-hidden','q2-hidden','q2-compulsory_common-hidden','q2-possible_common-hidden','q2-common_only-hidden')},
    **{key:(RESOLVE_ERROR,'verify_consumed',MODULE) for key in ('q1-resolve','q2-resolve')},
    **{key:(SHAPE_ERROR,'verify_consumed',MODULE) for key in (
        'q2-compulsory_common-drop','q2-possible_common-drop','q2-common_only-drop','q2-subquestions-drop','q1-invented-subquestion')},
    'q3-complete':('Consumed semantic completeness differs from question uncertainty',
                   '_verify_consumed_dependencies',SERVICE)}
BATCH_SIZE = 4
BATCHES = (len(CONTROLS)+BATCH_SIZE-1)//BATCH_SIZE
STAGES = ('install','tests','membership',
          *sum((('build-'+v,'downstream-'+v,'consume-'+v,'verify-'+v) for v in LABELS),()),
          'upstream',*('controls-'+str(i) for i in range(BATCHES)),'reconcile','seal')


def prerequisites(stage):
    if stage not in (*PREPARATION,*STAGES):
        raise ValueError('Unregistered definition integration stage')
    if stage == 'prepare':
        return ()
    if stage in PREPARATION[1:]:
        return (PREPARATION[PREPARATION.index(stage)-1],)
    if stage == 'install':
        return ('propose',)
    if stage in ('tests','membership'):
        return ('install',)
    if stage.startswith('build-'):
        return ('tests','membership')
    for prefix, previous in (('downstream-','build-'),('consume-','downstream-'),('verify-','consume-')):
        if stage.startswith(prefix):
            return (previous+stage.removeprefix(prefix),)
    if stage == 'upstream' or stage.startswith('controls-'):
        return tuple('verify-'+v for v in LABELS)
    if stage == 'reconcile':
        return ('tests','membership','upstream',*('verify-'+v for v in LABELS),
                *('controls-'+str(i) for i in range(BATCHES)))
    return ('reconcile',)


def validate_sources():
    run.source_check()
    freeze = run.read(run.PREP/'expected-freeze.json')
    for path, checksum in freeze['bindings'].items():
        assert run.sha(run.ROOT/path) == checksum, 'Frozen expectation changed'
    spec = run.read(run.PREP/'expected-spec.json.gz')
    report = run.read(run.PREP/'expected-report.json.gz')
    inventory = run.read(run.SOURCE/'bound-inventory.json.gz')
    source = run.read(run.SOURCE/'selected-source.json.gz')
    lexical = run.read(run.LEXICAL/'actual-selected-source.json.gz')
    text = source['candidate_text']
    assert hashlib.sha256(text.encode()).hexdigest() == spec['bindings']['selected_text_sha256']
    equal(spec['source_pieces'],source['pieces'],'Source provenance projection changed')
    equal(report['source_pieces'],source['pieces'],'Expected report source pieces changed')
    equal(report['lexical'],lexical,'Expected lexical result differs from sealed027')
    assert spec['source_inventory_sha256'] == run.sha(run.SOURCE/'bound-inventory.json.gz')
    assert spec['retained_lexical_sha256'] == run.sha(run.LEXICAL/'actual-selected-source.json.gz')
    assert report['profile_sha256'] == digest(spec)
    for key in ('preamble_reading','section_readings','known_misses','remaining'):
        equal(spec[key],inventory[key],'Retained source reading changed: '+key)
        equal(report[key],inventory[key],'Expected reading changed: '+key)
    @lru_cache(maxsize=None)
    def excerpt(index):
        value = spec['intervals'][index]
        a,b = value['start'],value['end']
        assert 0 <= a < b <= len(text) and text[a:b] == value['quote'], 'Source interval changed'
        expected = [i for i,p in enumerate(source['pieces']) if p['start'] < b and a < p['end']]
        equal(value['source_piece_indices'],expected,'Source piece intersection changed')
        clipped=[]
        for number in expected:
            p=source['pieces'][number]
            x,y=max(a,p['start']),min(b,p['end'])
            row={'start':x,'end':y,'text':text[x:y],'kind':p['kind']}
            if p['raw_binding'] is not None:
                raw=deepcopy(p['raw_binding'])
                raw['start']+=x-p['start']
                raw.update(end=raw['start']+y-x,quote=text[x:y])
                row['raw_binding']=raw
                row['assembly_uses']=[{**u,'start':u['start']+x-p['start'],
                    'end':u['start']+y-p['start'],'source':{k:raw[k] for k in
                        ('unit','document','source_sha256','start','end','quote')}} for u in p['assembly_uses']]
                row['assembly_use_status']=p['assembly_use_status']
            else:
                row.update(raw_binding=None,basis=p.get('basis'),assembly_uses=[])
            clipped.append(row)
        assert sum(p['end']-p['start'] for p in clipped)==b-a, 'Incomplete clipped provenance'
        return {**{k:value[k] for k in ('start','end','quote')},'source_pieces':clipped}
    assert len(spec['records']) == len(inventory['records']) == len(report['records']) == 62
    for saved,old,enriched in zip(spec['records'],inventory['records'],report['records']):
        for key in ('id','kind','forms','reading','declaring_section'):
            equal(saved[key],old[key],'Source record field changed: '+key)
        equal([excerpt(i) for i in saved['declarations']],old['declarations'],'Declaration projection changed')
        for a,b in zip(saved['scope_alternatives'],old['scope_alternatives']):
            for key in ('scope','reason'):
                equal(a[key],b[key],'Scope reading changed')
            for key in ('extent','source_reasons'):
                equal([excerpt(i) for i in a[key]],b[key],'Scope source projection changed')
        assert len(saved['scope_alternatives']) == len(old['scope_alternatives'])
        assert len(saved['uses']) == len(old['uses']) == len(enriched['uses'])
        for use,original,actual in zip(saved['uses'],old['uses'],enriched['uses']):
            equal(excerpt(use['interval']),{k:original[k] for k in ('start','end','quote','source_pieces')},'Use interval changed')
            for key in ('classification','declaration_candidates','scope_reading'):
                equal(use[key],original[key],'Authored use reading changed')
                equal(actual[key],use[key],'Expected authored use reading changed')
            a,b=original['start'],original['end']
            candidates=[i for i,s in enumerate(old['scope_alternatives'])
                        if any(v['start']<=a and b<=v['end'] for v in s['extent'])]
            exact=[i for i,v in enumerate(lexical['uses']) if (v['start'],v['end'])==(a,b)]
            overlap=[i for i,v in enumerate(lexical['uses']) if v['start']<b and a<v['end']
                     and (v['start'],v['end'])!=(a,b)]
            equal(actual['interval_candidates'],candidates,'Frozen containment expectation changed')
            equal(actual['lexical_exact'],exact,'Frozen exact-link expectation changed')
            equal(actual['lexical_overlap_only'],overlap,'Frozen overlap expectation changed')
            assert actual['governing_scope'] is actual['meaning'] is None
        assert enriched['status']=='UNRESOLVED' and enriched['scope_admitted'] is enriched['meaning_admitted'] is False
    p,answer=run.baseline()
    assert digest(p)==freeze['baseline_products_sha256'] and digest(answer)==freeze['baseline_answer_sha256']
    equal(p['P2']['payload']['assembly']['continuous_text'],text,'Wrong selected text baseline')
    return spec,report


def preflight():
    spec,report=validate_sources()
    def functions(path):
        tree=ast.parse(path.read_text())
        return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.FunctionDef)}
    for name,changed in (('service.py',{'dependencies','_verify_consumed_dependencies','interpretation_product','consume'}),
                         ('contracts.py',{'validate_request'})):
        before,after=functions(run.PREP/'baseline'/name),functions(run.PREP/'candidate'/name)
        assert set(before)==set(after), 'Unexpected function addition/removal'
        assert {k for k in before if before[k]!=after[k]}==changed, 'Unexpected modified function set'
    service=(run.PREP/'candidate/service.py').read_text()
    assert service.index('definition_scopes.verify_consumed(')<service.index('statutory_references.verify_consumed(')
    assert run.sha(run.PREP/'candidate/definition_discovery.py') == run.sha(run.AUTH/'reviews/definition-discovery-286/candidate.py')
    equal(run.read(run.PREP/'candidate/definition_scopes_spec.json.gz'),spec,'Staged source profile changed')
    assert run.sha(run.PREP/'candidate/definition_scopes_spec.json.gz')==run.sha(run.PREP/'expected-spec.json.gz')
    assert not (run.ROOT/(run.DEST+'definition_scopes.py')).exists()
    for name,module in tuple(sys.modules.items()):
        if not name.startswith(('legalmath.','scripts.')) or not getattr(module,'__file__',None):
            continue
        expected=run.ROOT/('src' if name.startswith('legalmath.') else 'scripts')
        assert Path(module.__file__).resolve().is_relative_to(expected), 'Cross-worktree import'
        assert name!=MODULE, 'Candidate evaluated before admission'
    run.save(run.PREP/'preflight-audit.json',{'status':'PASS','records':len(spec['records']),
        'authored_use_associations':sum(len(r['uses']) for r in spec['records']),
        'independent_expected_projection_sha256':run.sha(run.PREP/'expected-report.json.gz'),
        'candidate_evaluated':False,'production_installed':False,'ordinary_answers_run':0,
        'changed_service_functions':['dependencies','_verify_consumed_dependencies','interpretation_product','consume'],
        'baseline':'Complete025 reconstructed over complete021 candidate; storage donor excluded',
        'source_reasoning_correctness_proved':False})
    return {'status':'PASS','preparation_only':True,'candidate_evaluated':False,'records':len(spec['records'])}


def tests():
    command=[sys.executable,'-m','pytest','-q',
        'tests/prospectus_successor/test_reference_consumer_integrity.py',
        'tests/prospectus_successor/test_law_assistance_mode.py',
        'tests/prospectus_successor/test_unavailable_references.py']
    actual=subprocess.run(command,cwd=run.ROOT,capture_output=True,text=True,timeout=150)
    run.save(run.HERE/'checks/targeted-tests.json',{'command':command,'returncode':actual.returncode,
        'stdout':actual.stdout,'stderr':actual.stderr,'pythonpath':str(run.ROOT/'src')+':'+str(run.ROOT)})
    assert actual.returncode==0, 'Focused regressions failed; inspect retained test output'
    return {'status':'PASS','tests':actual.stdout.strip()[-250:],'role':'ENGINEERING_REGRESSION_ONLY'}


def refusal(exc,expected,function,module=MODULE):
    frames=[]
    tb=exc.__traceback__
    while tb:
        frames.append({'module':tb.tb_frame.f_globals.get('__name__'),
                       'function':tb.tb_frame.f_code.co_name,'line':tb.tb_lineno})
        tb=tb.tb_next
    assert type(exc) is ValueError and str(exc)==expected, 'Unexpected actual refusal; inspect retained failure'
    assert (frames[-1]['module'],frames[-1]['function'])==(module,function), 'Wrong refusal origin'
    return {'type':type(exc).__name__,'message':str(exc),'origin':frames[-1],'traceback':frames}


def membership():
    from legalmath.prospectus.successor import definition_scopes as candidate
    rows=[]
    for case in run.read(run.PREP/'membership-cases.json'):
        actual=candidate.interval_candidates(case['use'],case['alternatives'])
        run.save(run.HERE/('membership/'+case['label']+'.json'),{'case':case,'actual':actual})
        equal(actual,case['expected'],'Membership differs from independently authored case')
        rows.append(case['label'])
    bad=[([True,2],[]),([0,0],[]),([-1,2],[]),([2,1],[]),([0,1.0],[]),
         ([0,1],None),([0,1],[[[1,1]]]),([0,1],[(0,2)]),([0,1,2],[])]
    for i,(use,alternatives) in enumerate(bad):
        try:
            candidate.interval_candidates(use,alternatives)
        except ValueError as exc:
            receipt=refusal(exc,'Invalid definition membership interval','interval_candidates')
            run.save(run.HERE/f'membership/invalid-{i}.json',{'use':use,'alternatives':alternatives,**receipt})
        else:
            raise ValueError('Malformed membership interval accepted')
    return {'status':'PASS','authored_arithmetic_cases':len(rows),'actual_invalid_refusals':len(bad),
            'legal_scope_or_meaning_proved':False}


def questions(previous,ids):
    result=deepcopy(previous)
    for key in ('Q1','Q2'):
        for q in (result[key],*result[key].get('subquestions',{}).values()):
            q.update(status='CONFLICT' if q['status']=='CONFLICT' else 'UNKNOWN',value=None,
                     unresolved=sorted(set(q['unresolved'])|set(ids)))
        q3=result['Q3']['value']
        if key in q3:
            q3[key].update(complete=False,unresolved=result[key]['unresolved'])
    result['Q3']['status']='PARTIAL'
    return result


def independent_seal(previous,payload,inputs=None):
    body={k:deepcopy(v) for k,v in previous.items() if k not in ('sha256','payload')}
    body['payload']=payload
    if inputs is not None:
        body['inputs']=inputs
    return {**body,'sha256':digest(body)}


@lru_cache(maxsize=3)
def expected(label):
    assert label in LABELS
    old,old_answer=run.baseline()
    if label=='absent':
        return old,old_answer
    report=run.read(run.PREP/'expected-report.json.gz')
    packet={'profile':report['profile'],'profile_sha256':report['profile_sha256']}
    deps=[{'id':PREFIX+r['id'],'kind':'DEFINITION_SOURCE','questions':['Q1','Q2'],'status':'UNRESOLVED',
           'profile_sha256':report['profile_sha256'],'record_sha256':digest(r),
           'uncertainties':['GOVERNING_SCOPE_NOT_ADMITTED','MEANING_NOT_ADMITTED']} for r in report['records']]
    p=dict(old)
    if label=='request-route':
        payload=deepcopy(old['P1']['payload'])
        payload['request']['definition_sources']=packet
        p['P1']=independent_seal(old['P1'],payload,{'request':digest(payload['request'])})
        p['P2']=independent_seal(old['P2'],old['P2']['payload'],{'P1':p['P1']['sha256']})
    payload=deepcopy(old['P3']['payload'])
    if label=='assisted':
        payload['interpretation_input']['definition_sources']=packet
    bundle_deps=len(old['P1']['payload']['request']['bundle'].get('dependencies',[]))
    statutory_deps=sum(d['id'].startswith('statutory-reference:') for d in payload['dependencies'])
    index=bundle_deps+statutory_deps
    assert all(d['id'].startswith('statutory-reference:') for d in payload['dependencies'][bundle_deps:index])
    payload['dependencies'][index:index]=deps
    payload['definition_sources']=report
    payload['questions']=questions(payload['questions'],[d['id'] for d in deps])
    p['P3']=independent_seal(old['P3'],payload,{'P1':p['P1']['sha256'],'P2':p['P2']['sha256']})
    p['P4']=independent_seal(old['P4'],old['P4']['payload'],{'P1':p['P1']['sha256'],'P3':p['P3']['sha256']})
    p['P5']=independent_seal(old['P5'],old['P5']['payload'],{'P2':p['P2']['sha256'],'P3':p['P3']['sha256']})
    answer=deepcopy(old_answer)
    answer['definition_sources']=report
    answer['questions']=questions(answer['questions'],[d['id'] for d in deps])
    answer['request_sha256']=digest(p['P1']['payload']['request'])
    answer['consumed_products']={key:p[key]['sha256'] for key in p}
    answer['mode']='ASSISTED'
    answer['report_sha256']=digest({k:v for k,v in answer.items() if k!='report_sha256'})
    return p,answer


def verify_answer(label):
    p,answer=run.retained(label+'-answer')
    predicted,predicted_answer=expected(label)
    equal(p,predicted,'Complete products differ from independent025/026/027 expectation: '+label)
    equal(answer,predicted_answer,'Complete ordinary answer differs from independent expectation: '+label)
    run.save(run.HERE/(label+'-comparison.json'),{'complete_products_equal':True,'complete_answer_equal':True,
        'expected_products_sha256':digest(predicted),'actual_products_sha256':digest(p),
        'expected_answer_sha256':digest(predicted_answer),'actual_answer_sha256':digest(answer),
        'expected_from_production_admit_or_verify':False,'original_task_complete':False})
    return {'status':'PASS','label':label,'complete_products_equal':True,'complete_answer_equal':True,
            'protected_financial_and_statutory_payloads_equal':True,'original_task_complete':False}


def resource_audit():
    """Source-only retention sizing; never evaluates installed or staged code."""
    import gzip
    import json
    from scripts.prospectus_typed_delta import changes, apply
    def size(value):
        data=(json.dumps(value,ensure_ascii=False,allow_nan=False,indent=2)+'\n').encode()
        return len(gzip.compress(data,mtime=0))
    old,old_answer=run.baseline()
    p,answer=expected('assisted')
    product_delta=changes(old,p)
    answer_delta=changes(old_answer,answer)
    equal(apply(old,product_delta),p,'Resource projection product delta is lossy')
    equal(apply(old_answer,answer_delta),answer,'Resource projection answer delta is lossy')
    product_bytes=size({'products_delta':product_delta,'products_sha256':digest(p)})
    answer_bytes=size({'answer_delta':answer_delta,'answer_sha256':digest(answer)})
    samples={}
    for case in ('reading-'+IDS[0],'record-drop','lexical-drop','dependency-drop',
                 'q1-hidden','q1-invented-subquestion','alternative-drop'):
        altered=mutation(case,p)
        delta=changes(p['P3']['payload'],altered)
        assert delta, 'Resource sample makes no change: '+case
        equal(apply(p['P3']['payload'],delta),altered,'Resource sample delta is lossy')
        samples[case]=size(delta)
    # Twelve controls may replace a list/object; the others change/delete scalar
    # fields. Include generous hash/manifest overhead and three program copies.
    control_estimate=12*(max(samples.values())+4096)+(len(CONTROLS)-12)*65536
    current=run.costs()
    forecast=(current['cumulative026_028_bytes']+3*(run.AUTH/'program.json').stat().st_size
              +6*product_bytes+2*answer_bytes+control_estimate+2*1024**2)
    result={'status':'PASS','candidate_evaluated':False,'ordinary_answers_run':0,
        'product_delta_compressed_bytes':product_bytes,'answer_delta_compressed_bytes':answer_bytes,
        'sample_control_delta_bytes':samples,'control_bytes_estimate':control_estimate,
        'projected_cumulative_bytes':forecast,'working_ceiling_bytes':124*1024**2,
        'storage_projection_is_estimate':True,'actual_storage_and_time_limits_unchanged':True,
        'retention':'Controls use checked typed deltas against hash-bound assisted-products',
        'measured_time_allowance_added':0}
    run.save(run.PREP/'resource-audit.json',result)
    assert forecast < 124*1024**2, 'Source-only forecast exceeds reviewed working storage'
    assert 'legalmath.prospectus.successor.definition_scopes' not in sys.modules
    return {k:result[k] for k in ('status','candidate_evaluated','projected_cumulative_bytes',
                                 'working_ceiling_bytes','measured_time_allowance_added')}


def reseal(products,semantic):
    from legalmath.prospectus.successor import service
    p=dict(products)
    bundle=p['P1']['payload']['request']['bundle']
    for key in ('P3','P4','P5'):
        inputs=dict(products[key]['inputs'])
        if key!='P3':
            inputs['P3']=p['P3']['sha256']
        p[key]=service.seal(key,bundle,inputs,semantic if key=='P3' else products[key]['payload'])
        service.verify(p[key],key,bundle,inputs)
    return p


def mutation(case,p):
    semantic=deepcopy(p['P3']['payload'])
    report=semantic['definition_sources']
    if case.startswith('reading-'):
        r=next(r for r in report['records'] if r['id']==case.removeprefix('reading-'))
        r['reading']+=' Unsupported unconditional governing reading.'
    elif case=='report-drop':
        del semantic['definition_sources']
    elif case=='input-drop':
        del semantic['interpretation_input']['definition_sources']
    elif case=='input-forgery':
        semantic['interpretation_input']['definition_sources']['profile_sha256']='0'*64
    elif case=='record-drop':
        report['records'].pop()
    elif case=='record-resolve':
        report['records'][0]['status']='RESOLVED'
    elif case.startswith('alternative-'):
        r=next(r for r in report['records'] if r['scope_alternatives'])
        if case=='alternative-drop':
            r['scope_alternatives'].pop()
        elif case=='alternative-extent':
            alternative=next(a for record in report['records'] for a in record['scope_alternatives'] if a['extent'])
            alternative['extent']=[]
        else:
            r['scope_alternatives'][0]['reason']+=' Unsupported scope.'
    elif case=='interval-quote':
        report['intervals'][0]['quote']+=' invented'
    elif case=='interval-offset':
        report['intervals'][0]['start']+=1
    elif case=='source-piece':
        report['source_pieces'][0]['unsupported_source_repair']=True
    elif case=='provenance-gap':
        piece=next(v for v in report['source_pieces'] if v['kind']=='SUPPLIED_OR_TRANSFORMED')
        piece['unsupported_gap_closed']=True
    elif case=='lexical-drop':
        report['lexical']['uses'].pop()
    elif case=='lexical-meaning':
        report['lexical']['meaning_admitted']=True
    elif case=='binding-graph':
        report['bindings']['source_graph_sha256']='0'*64
    elif case=='governing-meaning':
        use=next(u for r in report['records'] for u in r['uses'])
        use.update(governing_scope=0,meaning='Unconditionally governs')
    elif case.startswith('dependency-'):
        d=next(d for d in semantic['dependencies'] if d['id'].startswith(PREFIX))
        if case=='dependency-drop':
            semantic['dependencies'].remove(d)
        else:
            d['status']='RESOLVED'
    elif case=='q3-complete':
        semantic['questions']['Q3']['status']='COMPLETE'
    elif case=='q1-invented-subquestion':
        semantic['questions']['Q1']['subquestions']={'invented':deepcopy(semantic['questions']['Q1'])}
    elif case=='q2-subquestions-drop':
        del semantic['questions']['Q2']['subquestions']
    elif case.startswith(('q1-','q2-')):
        parts=case.split('-')
        q=semantic['questions']['Q1' if parts[0]=='q1' else 'Q2']
        if len(parts)==3:
            if parts[-1]=='drop':
                del q['subquestions'][parts[1]]
                return semantic
            q=q['subquestions'][parts[1]]
        if parts[-1]=='hidden':
            q['unresolved'].remove(PREFIX+IDS[0])
        else:
            q.update(status='YES',value=True)
    else:
        raise ValueError('Unknown integration forgery')
    return semantic


def controls(batch):
    from legalmath.prospectus.successor import service
    assert 0<=batch<BATCHES
    p,_=run.retained('assisted-products')
    original_digest=digest(p)
    cases=list(CONTROLS)[batch*BATCH_SIZE:(batch+1)*BATCH_SIZE]
    for case in cases:
        bad=reseal(p,mutation(case,p))
        assert digest(bad)!=original_digest, 'Adverse control made no change'
        run.retain('control-'+case,bad,base_label='assisted-products',base_products=p)
        expected_error,function,module=CONTROLS[case]
        try:
            service.consume(bad,run.ROOT,mode='frozen')
        except ValueError as exc:
            raw={'type':type(exc).__name__,'message':str(exc)}
            run.save(run.HERE/('controls/'+case+'-actual.json'),raw)
            receipt=refusal(exc,expected_error,function,module)
            run.save(run.HERE/('controls/'+case+'.json'),{'case':case,'validly_resealed':True,
                'forged_products_sha256':digest(bad),'original_products_sha256':original_digest,**receipt})
        else:
            raise ValueError('Validly resealed definition forgery accepted: '+case)
    return {'status':'PASS','batch':batch,'actual_consumer_refusals':len(cases),'validly_resealed':True}


def upstream():
    from legalmath.prospectus.successor import service
    p,_=run.retained('assisted-products')
    cases=('wrong-profile','wrong-profile-digest','changed-graph','changed-assembly','changed-selection','missing-text','changed-text')
    for case in cases:
        first,second=p['P1'],p['P2']
        value=deepcopy(p['P3']['payload']['interpretation_input'])
        error,function=PROFILE_ERROR,'admit'
        if case.startswith('wrong-profile'):
            value['definition_sources']['profile' if case=='wrong-profile' else 'profile_sha256']='unsupported'
        else:
            selected=deepcopy(second['payload'])
            error='Definition source selection differs from retained evidence'
            if case=='changed-graph':
                source=deepcopy(first['payload'])
                source['graph']={**source['graph'],'unsupported_binding_change':True}
                # Keep the earlier report-reading check valid so this control
                # tests the definition binding rather than an unrelated guard.
                if source['request'].get('source_report_readings'):
                    admission=source['request']['source_report_readings']
                    admission['graph_sha256']=digest(source['graph'])
                    selected['source_report_readings'].update(
                        graph_sha256=digest(source['graph']),input_sha256=digest(admission))
                first=service.seal('P1',source['request']['bundle'],
                                   {'request':digest(source['request'])},source)
            elif case=='changed-assembly':
                selected['assembly']['unsupported_binding_change']=True
            elif case=='changed-selection':
                selected['selected_contract']['unsupported_binding_change']=True
            elif case=='missing-text':
                del selected['assembly']['continuous_text']
                error='Definition source requires actual selected continuous text'
            else:
                selected['assembly']['continuous_text']+=' invented'
            second=service.seal('P2',first['payload']['request']['bundle'],{'P1':first['sha256']},selected)
        run.retain('upstream-'+case,{**p,'P1':first,'P2':second},
                   base_label='assisted-products',base_products=p)
        run.save(run.HERE/('upstream/'+case+'-input.json.gz'),value)
        try:
            service.interpretation_product(first,second,value)
        except ValueError as exc:
            run.save(run.HERE/('upstream/'+case+'-actual.json'),{'case':case,**refusal(exc,error,function)})
        else:
            raise ValueError('Altered source/profile admitted: '+case)
    return {'status':'PASS','actual_upstream_refusals':len(cases),'validly_resealed_sources':True}


def reconcile():
    results={s:run.read(run.HERE/'stages'/s/'result.json') for s in prerequisites('reconcile')}
    assert all(v['status']=='PASS' for v in results.values())
    spec,report=validate_sources()
    previous=run.read(run.LEXICAL/'reconciliation.json.gz')
    assert previous['original_reference_records']==60 and previous['original_definition_records']==62
    source=run.read(run.SOURCE/'reconciliation.json.gz')
    assert len(source['original_reference_ledger']['records'])==60
    assert len(source['statutory_updated_reference_ledger']['records'])==60
    total=sum(results['controls-'+str(i)]['actual_consumer_refusals'] for i in range(BATCHES))
    assert total==len(CONTROLS)
    run.save(run.HERE/'reconciliation.json.gz',{'original_reconciliation':previous,
        'original_reconciliation_sha256':run.sha(run.LEXICAL/'reconciliation.json.gz'),
        'source_records':[{**r,'ordinary_dependency':PREFIX+r['id'],'governing_scope_admitted':False,
                           'meaning_admitted':False} for r in spec['records']],
        'original_reference_records':60,'original_definition_records':62,'denominator_replaced':False,
        'remaining':spec['remaining'],'known_misses':spec['known_misses'],'original_task_complete':False})
    return {'status':'PASS','original_reference_records':60,'source_records':62,
        'authored_use_associations':sum(len(r['uses']) for r in spec['records']),
        'complete_ordinary_answers_checked':len(LABELS),'actual_consumer_refusals':total,
        'actual_upstream_refusals':results['upstream']['actual_upstream_refusals'],
        'scope_admitted':False,'meaning_admitted':False,'original_task_complete':False}


def seal():
    result=run.read(run.HERE/'stages/reconcile/result.json')
    result={**result,'task':'basf-references','result_kind':'FINITE_DEFINITION_SOURCE_TO_ANSWER_INTEGRATION',
        'resources':run.costs(),'remaining':['Source-reasoned governing scope and meaning',
        'Missing definitions and provenance gaps','Historical statutory application','Original acceptance and general discovery'],
        'next_action':'Reviewed same-task source reasoning continuation; do not rerun unchanged integration'}
    run.save(run.HERE/'result.json',result)
    run.save(run.HERE/'run-manifest.json',{'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=run.ROOT,text=True).strip(),
        'commands':[run.read(run.HERE/'stages'/s/'started.json')['command'] for s in STAGES],
        'preparation_commands':[run.read(run.PREP/'stages'/s/'started.json')['command'] for s in PREPARATION],
        'environment':str(run.ROOT/'.venv/bin/python'),'cpu_gpu':'CPU; GPU intentionally hidden',
        'data_version':run.sha(run.SOURCE/'bound-inventory.json.gz'),'random_seeds':'N/A deterministic',
        'wall_time':result['resources'],'plan':run.PLAN,'result':run.rel(run.HERE/'result.json'),
        'artifacts':run.rel(run.HERE),'method_freeze':run.sha(run.PREP/'freeze.json')})
    with (run.HERE/'RESULT.md').open('x') as stream:
        stream.write('''# Retained definition readings now participate in ordinary answers

The optional exact-source profile transports all62 retained source records and
610 authored use associations into P3 and the ordinary answer. The unchanged027
lexical mechanism runs on the actual selected continuous text. Arithmetic
containment records alternatives; it supplies no governing scope or meaning.
Every record remains unresolved in Q1/Q2 and all three conversion subquestions.
Missing declarations, lexical misses, provenance gaps and alternative source
readings remain visible. The required subquestion shape is checked at consumption.

Three complete products/ordinary answers were retained before comparison with
independently assembled expectations. Absent input reproduces complete025;
interpretation-side and request-side profiles preserve unrelated answer content,
conditional statutory Q4 and financial P5. Actual upstream and validly resealed
consumer refusals are retained. This is a retained-product integration trial;
it proves no fresh native extraction, model run or general discovery recall.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Retain finite assisted integration | Complete independently expected products/answers and actual adverse refusals pass | No integration veto | Governing legal scope, missing definitions and historical law | Source-reasoned same-task continuation | General recall, legal correctness or whole-build completion |

The repaired defect was our disconnected definition evidence, together with a
consumer check that could omit a whole conversion subquestion. This trial gives
no evidence of an external package limitation. Its strongest alternative
explanation is a shared error in retained source readings. Contrary primary-source
reasoning would overturn those readings without invalidating the transport test.
The weakest evidence remains the unadmitted governing meaning; it is explicitly
unresolved. No external adviser opinion is a prerequisite for the general build.
''')
    return {'status':'PASS','original_task_complete':False,'resources':result['resources']}
