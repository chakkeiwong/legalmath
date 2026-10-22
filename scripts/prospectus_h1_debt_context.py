"""Bounded original H1 debt reading and normal/installed consumer evidence."""
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import prospectus_h1_statement_consumer as prior
read, save, sha, digest = prior.read, prior.save, prior.sha, prior.digest
compact_digest, same, require, rel = prior.compact_digest, prior.same, prior.require, prior.rel
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
BASE = AUTH / 'attempts/source-bes-dep-05'
PREP = AUTH / 'reviews/h1-debt-context-385'
HERE = BASE / 'attempt-022'
SELF = 'scripts/prospectus_h1_debt_context.py'
PLAN = 'docs/plans/prospectus-h1-debt-context-2026-10-21.md'
PRODUCTION = prior.PRODUCTION
PROFILE = 'bes-h1-2010-statements-debt-context.v2'
DOCUMENT, PDF = prior.DOCUMENT, prior.PDF
PAGES = (80,81,144,145)
TESTS = prior.TESTS
DEPENDENCIES = {'render':[], 'source':['render'], 'implement':['source'],
    'tests':['implement'], 'ordinary':['tests'], 'controls':['ordinary'],
    'package':['controls'], 'installed':['package'], 'coverage':[]}

def authority():
    sys.path[:0] = [str(ROOT/'src'),str(ROOT)]
    from legalmath.prospectus.execution_authority import Authority
    return Authority(ROOT)

def costs(reserve=0):
    start=read(PREP/'accounting-start.json')
    paths={p for d in (PREP,HERE) if d.exists() for p in d.rglob('*')
           if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in (PLAN,SELF,PRODUCTION))
    paths.add(AUTH/'revisions/0385.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    seconds=sum(read(p)['wall_seconds'] for d in (PREP,HERE) for p in d.glob('commands/*.json'))
    return {'new_bytes':size,'new_measured_seconds':seconds,'new_control_seconds':60,
      'prior_known_bytes':start['prior_known_bytes'],'prior_known_seconds':start['prior_known_seconds'],
      'known_cumulative_bytes':start['prior_known_bytes']+size,
      'known_cumulative_seconds':start['prior_known_seconds']+seconds+60,
      'earlier_manual_and_unmeasured_costs':'UNKNOWN; history retained',
      'execution_allowed':size+reserve<94*1024**2 and seconds<540}

def prepare():
    tick=time.monotonic(); auth=authority(); old=read(AUTH/'program.json')
    require(old['revision']==384 and not PREP.exists() and not HERE.exists(),'Fresh384 required')
    events=auth.events(); attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e['budget_key']=='source-bes-dep-05']
    require(len(attempts)==old['budgets']['source-bes-dep-05']['maximum_new_attempts']==21,'Retain21attempts')
    protected={}
    for n in (7,15,16,17,21):
        folder=BASE/f'attempt-{n:03d}'; manifest=folder/'outputs.json'
        records=[e for e in events if e.get('attempt')==rel(folder) and 'outputs_sha256' in e]
        require(records and sha(manifest)==records[-1]['outputs_sha256'],'Unauthenticated original')
        protected[rel(manifest)]=sha(manifest)
        for name,h in read(manifest).items():
            require(sha(folder/name)==h,'Changed original '+name)
    previous=prior.costs()
    save(PREP/'accounting-start.json',{'prior_known_bytes':previous['known_cumulative_bytes'],
        'prior_known_seconds':previous['known_cumulative_seconds'], 'prior_cost_receipt':previous,
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size})
    (PREP/'baseline').mkdir(); shutil.copyfile(ROOT/PRODUCTION,PREP/'baseline/statement_cells.py')
    save(PREP/'baseline/production.json',prior.production())
    names=[PLAN,SELF,prior.SELF,'pyproject.toml',*TESTS,rel(BASE/'attempt-001/interim.pdf'),
      rel(BASE/'attempt-007/products.json.gz'),rel(BASE/'attempt-007/scope-consumer.json.gz'),
      rel(BASE/'attempt-015/source-units.json'),rel(BASE/'attempt-015/profile.json'),rel(prior.TRANSCRIPT),
      rel(BASE/'attempt-016/answer-supplement.json.gz'),rel(BASE/'attempt-017/composition.json'),
      rel(BASE/'attempt-017/answer-delta.json.gz'),rel(BASE/'attempt-021/ordinary.json.gz'),
      rel(prior.PREP/'reading.json'),rel(PREP/'baseline/statement_cells.py'),rel(PREP/'baseline/production.json')]
    products=read(BASE/'attempt-007/products.json.gz')
    names += [d['path'] for d in products['P1']['payload']['request']['bundle']['documents']]
    protected.update({n:sha(ROOT/n) for n in names})
    protected.update({n:h for n,h in prior.production().items() if n!=PRODUCTION})
    save(PREP/'freeze.json',{'bindings':protected,'baseline_sha256':sha(ROOT/PRODUCTION),
        'mutable_file':PRODUCTION,'implementation_window':'After admitted source review and candidate freeze, once'})
    config=read(prior.PREP/'config.json');require(sha(config['package_python'])==config['python_sha256'],'Build runtime changed')
    save(PREP/'config.json',config)
    new=deepcopy(old); new['revision']=385
    task=next(t for t in new['tasks'] if t['id']=='source-bes-dep-05')
    task.update(dossier=PLAN,pre_admission_review=PLAN,build_criteria_scope=[],
        reason='Read original Note35 and policies2.8/2.9; preserve call-date, currency, carrying-amount and accounting conditions through the actual answer')
    task['inputs']=sorted((set(task['inputs'])-{PRODUCTION})|set(protected)|{rel(PREP/'freeze.json'),rel(PREP/'config.json')})
    bounds={'measured_seconds':540,'control_seconds':60,'new_bytes':96*1024**2,'failure_reserve':2*1024**2,
        'previous_known_bytes':previous['known_cumulative_bytes'],'previous_known_seconds':previous['known_cumulative_seconds'],'unchanged_retries':0}
    task['debt_context']={'version':PROFILE,'freeze':rel(PREP/'freeze.json'),'bounds':bounds,
        'success_dependencies':DEPENDENCIES,'original_task_acceptance':False}
    new['budgets']['source-bes-dep-05']['maximum_new_attempts']=22
    routes=read(ROOT/old['continuation_review']['routes']);routes['baseline_revision']=385
    for row in routes['tasks']:
        if row['task']==task['id']:
            row.update(task_sha256=compact_digest(task),dossier=PLAN,phase=0,
                remaining='021 primary statement consumer complete; debt-note/policy context remains separate from answer; original wider note/source authority gaps remain.',
                next_action='Execute022 render, source review, debt context consumer, controls and installed evidence; reconcile remaining original coverage, record and refresh.',
                stop_condition='22 retained admissions;540+60seconds and96MiB new; no unchanged retry; all old costs/failures retained.')
    save(PREP/'routes.json',routes)
    new['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    new['continuation_review']['bindings'].pop(PRODUCTION,None)
    new['continuation_review']['bindings'].update({n:sha(ROOT/n) for n in (PLAN,rel(PREP/'routes.json'),rel(PREP/'freeze.json'),rel(PREP/'baseline/statement_cells.py'))})
    require(old['obligations']==new['obligations'] and old['build_contract']==new['build_contract'],'Scope changed')
    raw=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
    source_bytes=sum(p.stat().st_size for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    forecast=costs()['new_bytes']+2*len(raw)+3*source_bytes+14*1024**2
    require(forecast<94*1024**2,'Forecast exceeds reservation')
    with (PREP/'proposal.json').open('xb') as stream:stream.write(raw)
    from legalmath.prospectus.execution_authority import digest as adigest
    save(PREP/'review.json',{'baseline':adigest(old),'scope_unchanged':True,'budget_unchanged':False,
      'changes':['Integrate original Note35 and policy2.8/2.9 with all021fields retained','Correct unverified call-marker and gain-period assumptions before source interpretation','Retain21attempts and all original obligations'],
      'skeptical_audit':{'verdict':'PASS','plan':PLAN,'forecast_new_bytes':forecast,
          'source_risks':['p145:l146 marker association requires image','p145:l193 comparison period remains source-qualified'],
          'no_proxy_promotion':'Hashes/tests bind and deliver supplied reading; they do not establish financial/legal truth'},
      'evidence_contract':{'question':'Does full debt context reach the normal and installed answer without an unsupported repayment inference?',
          'primary':'Original image/quote/geometry checks, prior answer preservation and actual corruption refusals',
          'promotion_veto':['Omitted source','Wrong marker/unit/issuer/period','Unsupported right','Wrong import','Accepted corruption'],
          'continuation_veto':['Invalid authority','Corrupt original','Spent resources'],
          'not_concluded':['Automatic extraction','Financial truth','Instrument entitlement','Whole source task/build']},
      'budget_revision':{'budget_key':'source-bes-dep-05','previous_maximum':21,'new_maximum':22,'retained_attempts':attempts,
          'reason':'New original debt disclosure dependency, not repeat statement validation','next_discriminating_check':'Original marker/amount/policy interpretation and matched actual downstream answer',
          'stop_condition':bounds,'same_scope_authorization':'Recover and continue original build'}})
    save(PREP/'commands/preparation.json',{'wall_seconds':time.monotonic()-tick,'command':[sys.executable,'-m',SELF,'prepare']})
    return {'status':'PREPARED','revision':385,'forecast_new_bytes':forecast,'resources':costs()}

def frozen():
    auth=authority();admission=read(HERE/'admission.json')
    from legalmath.prospectus.execution_authority import digest as adigest
    require(adigest(read(AUTH/'program.json'))==admission['program_sha256'] and auth.binding(admission['task_spec'])==admission['binding'],'Unchanged admission required')
    f=read(PREP/'freeze.json');require(all(sha(ROOT/n)==h for n,h in f['bindings'].items()),'Frozen input changed')
    expected=f['baseline_sha256']
    if (HERE/'candidate-production.json').exists():expected=read(HERE/'candidate-production.json')[PRODUCTION]
    require(sha(ROOT/PRODUCTION)==expected,'Registry outside implementation window')

def command(name,argv,timeout=120):
    require(costs(1024**2)['execution_allowed'],'Resource reservation exhausted')
    target=HERE/'commands';target.mkdir(exist_ok=True);tick=time.monotonic();result=None;error=None
    try:
        with (target/(name+'.log')).open('x') as stream:
            result=subprocess.run(argv,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout,
                env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1','PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1',
                     'PYTHONPATH':str(ROOT/'src')+os.pathsep+str(ROOT),'PIP_NO_INDEX':'1','PIP_DISABLE_PIP_VERSION_CHECK':'1'})
        require(result.returncode==0,'Inspect retained '+name+'.log')
    except Exception as exc:error={'type':type(exc).__name__,'reason':str(exc)}
    save(target/(name+'.json'),{'command':argv,'wall_seconds':time.monotonic()-tick,'exit_code':None if result is None else result.returncode,'error':error})
    require(error is None,'Command failed: '+name+': '+str(error));require(costs()['execution_allowed'],'Post-command resource limit')

def render_worker():
    require(sha(BASE/'attempt-001/interim.pdf')==PDF,'Wrong original PDF')
    (HERE/'images').mkdir()
    for page in PAGES:
        command('render-'+str(page),['pdftoppm','-f',str(page),'-l',str(page),'-r','160','-singlefile','-png',str(BASE/'attempt-001/interim.pdf'),str(HERE/'images'/f'page-{page}')],60)
    save(HERE/'images.json',[{'page':p,'path':rel(HERE/'images'/f'page-{p}.png'),'sha256':sha(HERE/'images'/f'page-{p}.png')} for p in PAGES])

def original_units():
    products=read(BASE/'attempt-007/products.json.gz')
    return sorted([u for u in products['P1']['payload']['graph']['units']
        if u['document']==DOCUMENT and u['page'] in PAGES],key=lambda u:(u['page'],u['order'],u['id']))

def debt_reading(units, transcript):
    lookup={(u['page'],u['order']):u for u in units}
    def q(page,line):
        u=lookup[page,line];return {'id':u['id'],'quote':u['raw']}
    def qs(page,first,last):return [q(page,i) for i in range(first,last+1)]
    def number(page,line):
        quote=q(page,line);token=''.join(quote['quote'].split())
        value=None if token=='-' else int('-'+token[1:-1] if token.startswith('(') else token)
        return {**quote,'value':value,'status':'DASH_UNKNOWN' if value is None else 'SOURCE_NUMBER','unit':'EUR thousands'}
    groups={str(p):[q(p,u['order']) for u in units if u['page']==p] for p in PAGES}
    summary={'date_headers':qs(144,79,80),'unit_source':q(144,75),'periods':['2010-06-30','2009-12-31'],
        'rows':[{'label':q(144,76+i),'cells':[number(144,81+i),number(144,84+i)]} for i in range(3)],
        'totals':[number(144,87),number(144,88)]}
    starts=[14,22,30,39,48,56,64,72,80,88,96,104,112,120,128,136]
    issues=[]
    for first,t in zip(starts,transcript['issues']):
        marker=t['marker_line'];issues.append({'issuer':q(145,first),'designation':q(145,first+1),
            'issue_currency':q(145,first+2),'issue_year':q(145,first+3),
            'amount_issued':number(145,first+4),'carrying_amount':number(145,first+5),
            'interest_rate':q(145,first+6),'printed_date':q(145,first+7),
            'date_marker':q(145,marker) if marker is not None else None,
            'date_role':'CALL_OPTION_DATE' if marker is not None else 'PRINTED_MATURITY_COLUMN_ONLY',
            'compulsory_redemption_established':False,'call_exercise_established':False})
    issue_table={'as_of':q(145,3),'unit_source':q(145,2),'headers':qs(145,4,13),
        'rows':issues,'totals':[number(145,144),number(145,145)],'call_footnote':q(145,147),
        'amount_basis':'Both numeric columns use the table header EUR thousands; issue currency is a separate descriptor',
        'contract_terms_complete':False}
    movements={'headers':qs(145,150,161),'columns':['2009-12-31','issues','repayments','net_repurchase','other_movements','2010-06-30'],
        'rows':[{'label':q(145,151+i),'cells':[number(145,n+i) for n in (162,165,168,171,174,177)]} for i in range(3)],
        'totals':[number(145,n) for n in range(180,186)],'footnotes':qs(145,186,189),
        'dash_imputed_zero':False,'other_movements':['accrued interest','fair value adjustments','foreign exchange differences'],
        'issues_include_replacement_of_previously_repurchased_debt':True}
    policies={
        'financial_liability':{'sources':qs(80,24,29),'classification':'Contractual transfer of cash or another financial asset, independent of legal form',
            'preference_share_conditions':'Obligation of reimbursement and/or dividends'},
        'measurement':{'sources':qs(81,1,14),'initial':'Fair value less transaction costs',
            'subsequent':'Amortised cost using effective interest, except short sales and liabilities designated fair value through profit or loss',
            'designation_time':'at inception','designation_alternatives':['economic hedge eliminating an accounting mismatch','embedded derivatives'],
            'structured_products':'Source reports the conditions are met and classification at fair value through profit or loss',
            'quoted_fair_value':'Current price','unquoted_fair_value':'Valuation techniques using market information including issuer own credit risk'},
        'repurchase':{'sources':qs(81,15,17),'treatment':'Repurchased issued debt derecognised; carrying amount minus acquisition cost recognised in income',
            'contractual_rights_inferred':False},
        'equity':{'sources':qs(81,18,28),'classification':'No contractual cash/asset delivery obligation; residual assets after all liabilities, independent of legal form',
            'issue_costs':'Directly attributable issue costs deducted from equity proceeds',
            'own_equity_transactions':'Acquisitions/sales recognised in equity net of transaction costs',
            'distributions':'Debited directly to equity as dividends when declared',
            'preference_share_conditions':['No contractual redemption obligation','Noncumulative dividends paid only if and when declared']},
        'status':'HISTORICAL_SOURCE_ACCOUNTING_STATEMENTS; referenced standards/current law not independently verified'}
    return {'source_groups':groups,'summary':summary,'issues':issue_table,'movements':movements,'policies':policies,
        'buyback_gains':{'sources':qs(145,190,194),'values_million_eur':['4.2','110.5'],
            'period_wording':q(145,193),'comparison_period':'PRESERVE_SOURCE_WORDING; full-year versus six-month comparative not resolved',
            'note10_reference_resolved':False,'contractual_repayment_right_inferred':False},
        'source_context':{'reading_kind':'SUPPLIED_DEVELOPMENT_READING','incorporation_status':'UNRESOLVED',
            'source_authenticity':'NOT_ESTABLISHED','financial_accuracy_proved':False,'automatic_extraction':False,
            'all_notes_read':False,'BES_Finance_standalone_accounts_supplied':False,'cashflows_derived':False,
            'outside_new_interpretation':['p80 policy2.6 continuation and policy2.7','p144 tax-note context'],
            'date_cautions':transcript['date_cautions']}}

def source_check(reading, units, transcript):
    require(len(units)==351 and len({u['id'] for u in units})==351,'Complete351source occurrences required')
    lookup={u['id']:u for u in units}
    require(all(u['source_sha256']==PDF and u['visible'] and u['page'] in PAGES for u in units),'Wrong source/visibility')
    source=reading['debt_context'];quoted=[q for group in source['source_groups'].values() for q in group]
    require(len(quoted)==351 and {q['id'] for q in quoted}==set(lookup),'Incomplete context partition')
    require(all(q['quote']==lookup[q['id']]['raw'] for q in quoted),'Changed contextual quote')
    def normalize(s):return ''.join(s.split())
    widths=[(90,155),(160,245),(268,301),(315,350),(365,400),(410,445),(448,520),(527,547)]
    fields=['issuer','designation','issue_currency','issue_year','amount_issued','carrying_amount','interest_rate','printed_date']
    def rowcheck(row, expected, cols):
        ys=[]
        for cell,v,col in zip(row,expected,cols):
            u=lookup[cell['id']];require(cell['quote']==u['raw'],'Changed cell quote')
            if 'value' in cell:
                require(cell['value']==v and cell['unit']=='EUR thousands','Wrong amount or table unit')
                require(cell['status']==('DASH_UNKNOWN' if v is None else 'SOURCE_NUMBER'),'Dash coerced')
            else:require(normalize(cell['quote'])==normalize(v),'Image/text disagreement: '+cell['id'])
            x=(u['bbox'][0]+u['bbox'][2])/2;require(col[0]<=x<col[1],'Wrong column: '+cell['id']);ys.append(u['bbox'][1])
        require(max(ys)-min(ys)<3,'Wrong row association')
    require(len(source['issues']['rows'])==len(transcript['issues'])==16,'Incomplete issue table')
    for row,t in zip(source['issues']['rows'],transcript['issues']):
        rowcheck([row[k] for k in fields],t['values'],widths)
        marker=row['date_marker']
        if marker:
            m=lookup[marker['id']];d=lookup[row['printed_date']['id']]
            require(abs(m['bbox'][1]-d['bbox'][1])<2 and m['bbox'][0]>d['bbox'][2] and normalize(marker['quote'])=='a)','Wrong call marker association')
        require(row['date_role']==('CALL_OPTION_DATE' if marker else 'PRINTED_MATURITY_COLUMN_ONLY') and not row['compulsory_redemption_established'],'Unsupported date inference')
    require([int(r['date_marker']['id'].split(':l')[-1]) if r['date_marker'] else None for r in source['issues']['rows']]==[t['marker_line'] for t in transcript['issues']],'Marker changed')
    require(normalize(source['issues']['call_footnote']['quote'])=='a)Calloptiondate','Wrong call footnote')
    for row,t in zip(source['summary']['rows'],transcript['summary']):
        rowcheck(row['cells'],t,[(385,455),(465,540)])
    require([c['value'] for c in source['summary']['totals']]==transcript['summary_totals'],'Wrong summary total')
    require([c['value'] for c in source['issues']['totals']]==transcript['issue_totals'],'Wrong issue total')
    mwidth=[(210,263),(275,315),(320,370),(370,425),(430,490),(490,540)]
    for row,t in zip(source['movements']['rows'],transcript['movements']):rowcheck(row['cells'],t,mwidth)
    require([c['value'] for c in source['movements']['totals']]==transcript['movement_totals'],'Wrong movement total')
    require(sum(c['value'] is None for r in source['movements']['rows'] for c in r['cells'])==6,'Unknown dash count')
    baseline=read(prior.PREP/'reading.json')
    same({k:v for k,v in reading.items() if k!='debt_context'},baseline,'021reading changed')
    prior.source_check(baseline,read(BASE/'attempt-015/source-units.json'))
    balance=next(r for r in baseline['tables']['liabilities']['rows'] if r['label'] and 'Subordinated debt' in r['label']['quote'])
    same([c['value'] for c in balance['cells']],transcript['summary_totals'],'Note35 differs from statement')
    totals=[c['value'] for c in source['summary']['totals']]
    require([sum(r['cells'][i]['value'] for r in source['summary']['rows']) for i in range(2)]==totals,'Summary arithmetic mismatch')
    issue_sums=[sum(r[k]['value'] for r in source['issues']['rows']) for k in ('amount_issued','carrying_amount')]
    require(issue_sums==transcript['issue_totals'] and issue_sums[1]==totals[0],'Issue/carrying comparison mismatch')
    movement_totals=[c['value'] for c in source['movements']['totals']]
    require(sum(movement_totals[:-1])==movement_totals[-1],'Aggregate movement reconciliation mismatch')
    return {'new_occurrences':351,'prior_occurrences':533,'total_occurrences':884,'issue_rows':16,'summary_values':8,
        'movement_positions':24,'unknown_dashes':6,'table_arithmetic':'EXPLANATORY_ONLY; unknown category dashes not replaced',
        'all_prior_statement_fields_preserved':True,'call_dates_do_not_establish_mandatory_redemption':True}

def source_worker():
    units=original_units();t=read(HERE/'image-transcript.json');review=HERE/'SOURCE-REVIEW.md'
    require(review.is_file() and len(review.read_text())>1000,'Substantive image/source review required')
    for image in read(HERE/'images.json'):require(sha(ROOT/image['path'])==image['sha256'],'Source image changed')
    reading=deepcopy(read(prior.PREP/'reading.json'));reading['debt_context']=debt_reading(units,t)
    checked=source_check(reading,units,t)
    all_units=sorted(read(BASE/'attempt-015/source-units.json')+units,key=lambda u:(u['page'],u['order'],u['id']))
    save(HERE/'source-units.json',units);save(HERE/'reading.json',reading)
    entry={'document':DOCUMENT,'source':PDF,'reading':compact_digest(reading),'pages_digest':compact_digest(all_units),
        'pages':sorted(set(prior.PAGES)|set(PAGES)),'occurrences':len(all_units),
        'reading_fields':['source_groups','tables','terms','scope','debt_context']}
    original=(PREP/'baseline/statement_cells.py').read_text()
    require(PROFILE not in original and original.count('PROFILES = {')==1,'Baseline registry changed')
    candidate=original.replace('PROFILES = {\n','PROFILES = {\n    '+repr(PROFILE)+': '+repr(entry)+',\n',1)
    (HERE/'candidate-statement_cells.py').write_text(candidate);save(HERE/'registry-entry.json',entry)
    names=['reading.json','source-units.json','registry-entry.json','candidate-statement_cells.py','image-transcript.json','SOURCE-REVIEW.md','images.json']
    save(HERE/'candidate-freeze.json',{'bindings':{n:sha(HERE/n) for n in names},'candidate_sha256':digest(candidate.encode())})
    from legalmath.prospectus.successor import statement_cells as cells
    try:cells.admit({'units':all_units},supplied({'units':all_units}))
    except ValueError as exc:require('Unsupported source statement' in str(exc),'Unexpected baseline refusal')
    else:raise ValueError('New debt profile already supported')
    save(HERE/'source-check.json',{'status':'PASS',**checked,'baseline_gap':'New debt profile unsupported','source_review':prior.ref(review)})

def candidate_frozen():
    f=read(HERE/'candidate-freeze.json');require(all(sha(HERE/n)==h for n,h in f['bindings'].items()),'Candidate interpretation changed')
    return f

def implement_worker():
    f=candidate_frozen();require(sha(ROOT/PRODUCTION)==read(PREP/'freeze.json')['baseline_sha256'],'Baseline changed')
    shutil.copyfile(HERE/'candidate-statement_cells.py',ROOT/PRODUCTION)
    require(sha(ROOT/PRODUCTION)==f['candidate_sha256'],'Registry write failed');save(HERE/'candidate-production.json',prior.production())

def supplied(graph):
    return {'version':'source-statement-cells.v1','profile':PROFILE,'document':DOCUMENT,'graph_sha256':digest(graph),
        'review':{'kind':'DEVELOPMENT','reviewer':'Original page images, exact quotes and independent table transcript',
            'reason':'Complete prior H1 statements plus Note35 and policy2.8/2.9; authority and wider notes remain unresolved'},
        'reading':read(HERE/'reading.json')}

def build_products(original):
    from legalmath.prospectus.successor import service
    p1=deepcopy(original['P1']);request=p1['payload']['request'];request['source_statement_cells']=supplied(p1['payload']['graph'])
    p1=service.seal('P1',request['bundle'],{'request':digest(request)},p1['payload'])
    p2=service.construction_product(p1,ROOT);p3=service.interpretation_product(p1,p2,original['P3']['payload'].get('interpretation_input'))
    l,f=original['P4']['payload'],original['P5']['payload']
    return {'P1':p1,'P2':p2,'P3':p3,'P4':service.law_product(p1,p3,l.get('cases'),l.get('law_input')),
        'P5':service.financial_product(p1,p2,p3,f.get('cases'),f.get('scenario_input'))}

def registry_controls():
    from legalmath.prospectus.successor import statement_cells as cells
    graph={'units':read(BASE/'attempt-015/source-units.json')+read(HERE/'source-units.json')}
    rows=[]
    changes={
      'call-as-maturity':lambda d:d['issues']['rows'][2].update(date_role='COMPULSORY_MATURITY'),
      'misplaced-marker':lambda d:d['issues']['rows'][13].update(date_marker=d['issues']['rows'][12]['date_marker']),
      'issuer-changed':lambda d:d['issues']['rows'][0]['issuer'].update(quote='BES Finance'),
      'currency-changed':lambda d:d['issues']['rows'][0]['issue_currency'].update(quote='EUR'),
      'issued-as-carrying':lambda d:d['issues']['rows'][0].update(carrying_amount=d['issues']['rows'][0]['amount_issued']),
      'currency-as-unit':lambda d:d['issues']['rows'][0]['amount_issued'].update(unit='JPY thousands'),
      'dash-zero':lambda d:d['movements']['rows'][0]['cells'][1].update(value=0,status='SOURCE_NUMBER'),
      'measurement-exceptions-lost':lambda d:d['policies']['measurement'].update(subsequent='All liabilities at amortised cost'),
      'designation-or-to-and':lambda d:d['policies']['measurement'].update(designation_alternatives=['Both required']),
      'own-credit-removed':lambda d:d['policies']['measurement'].update(unquoted_fair_value='Excludes issuer credit'),
      'dividend-condition-lost':lambda d:d['policies']['equity'].update(preference_share_conditions=['No contractual redemption obligation']),
      'derecognition-as-right':lambda d:d['policies']['repurchase'].update(contractual_rights_inferred=True),
      'comparative-period-invented':lambda d:d['buyback_gains'].update(comparison_period='Full year2009'),
      'incorporation-assumed':lambda d:d['source_context'].update(incorporation_status='CONFIRMED'),
      'missing-issue':lambda d:d['issues']['rows'].pop(),
      'missing-policy-source':lambda d:d['policies']['equity']['sources'].pop(),
      'cashflows-invented':lambda d:d['source_context'].update(cashflows_derived=True)}
    for name,change in changes.items():
        bad=supplied(graph);change(bad['reading']['debt_context'])
        try:cells.admit(graph,bad)
        except ValueError as exc:rows.append({'case':name,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else:raise ValueError('Altered reading accepted: '+name)
    for name in ('missing-page','source-hash','geometry'):
        g=deepcopy(graph)
        if name=='missing-page':g['units']=[u for u in g['units'] if u['page']!=145]
        elif name=='source-hash':g['units'][-1]['source_sha256']='0'*64
        else:g['units'][-1]['bbox'][0]+=1
        bad=supplied(g)
        try:cells.admit(g,bad)
        except ValueError as exc:rows.append({'case':name,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else:raise ValueError('Altered source accepted: '+name)
    return rows

def consumer_worker(kind):
    from legalmath.prospectus.successor import service
    candidate_frozen();original=read(BASE/'attempt-007/products.json.gz')
    baseline=prior.build_products(original,True);before=service.consume(baseline,ROOT,include_artifacts=True)
    previous=read(BASE/'attempt-021/ordinary.json.gz')
    require(digest(before)==previous['answer_sha256'],'Complete021baseline answer changed')
    current=build_products(original);after=service.consume(current,ROOT,include_artifacts=True)
    for phase in ('P2','P3','P4','P5'):
        left,right=deepcopy(baseline[phase]['payload']),deepcopy(current[phase]['payload'])
        if phase=='P2':left.pop('source_statement_cells');right.pop('source_statement_cells')
        if phase=='P3':left.pop('source_statement_cells_sha256');right.pop('source_statement_cells_sha256')
        same(left,right,'Unexpected phase payload change: '+phase)
    same(current['P1']['payload']['graph'],baseline['P1']['payload']['graph'],'Source graph changed')
    left,right=deepcopy(baseline['P1']['payload']['request']),deepcopy(current['P1']['payload']['request'])
    left.pop('source_statement_cells');right.pop('source_statement_cells');same(left,right,'Unrelated request changed')
    replacements={k:after[k] for k in ('request_sha256','consumed_products','report_sha256')}
    same({**before,**replacements,'source_statement_cells':after['source_statement_cells']},after,'Unrelated answer change')
    same(before['questions'],after['questions'],'Original questions changed')
    require(after['questions']['Q3']['status']=='PARTIAL' and not after['may_execute_transaction'] and not after['independent_legal_acceptance'],'Original limits changed')
    for key in ('source_groups','tables','terms','scope','source_context'):same(before['source_statement_cells'][key],after['source_statement_cells'][key],'Lost021reading field '+key)
    body=after['source_statement_cells'];reading=read(HERE/'reading.json')
    for key in reading:same(body[key],reading[key],'Missing complete reading field '+key)
    require(body['consumed'] and not body['independent_financial_acceptance'] and body['legal_dependency_resolution']=='UNCHANGED','Scope overclaim')
    checked=source_check(reading,read(HERE/'source-units.json'),read(HERE/'image-transcript.json'));cases=registry_controls()
    imported={n:m.__file__ for n,m in sys.modules.items() if n.startswith('legalmath') and getattr(m,'__file__',None)}
    location=HERE/'installed' if kind=='installed' else ROOT/'src'
    require(imported and all(Path(p).resolve().is_relative_to(location) for p in imported.values()),'Wrong import origin')
    del original,baseline,current,left,right
    later=read(BASE/'attempt-016/answer-supplement.json.gz');composition=read(BASE/'attempt-017/composition.json')
    require(digest(later)==composition['previous_content_sha256'],'Original016changed')
    later.update(read(BASE/'attempt-017/answer-delta.json.gz'));require(digest(later)==composition['complete_composed_sha256'],'Original017changed')
    later['h1_normal_statement_consumer']=before
    require(digest(later)==previous['full_composed_sha256'],'Complete021composition changed')
    later['h1_debt_context_consumer']=after
    receipt={'status':'PASS','prior_complete_answer_sha256':digest(before),'answer_sha256':digest(after),
        'prior_full_composed_sha256':previous['full_composed_sha256'],'full_composed_sha256':digest(later),
        'reading_sha256':compact_digest(reading),'replacements':replacements,'addition':body,'controls':cases,
        'source_check':checked,'imports':imported,'whole_task_complete':False,'source_truth_established':False,
        'recipe':'Reconstruct021 from original007 and its frozen profile; verify021receipt, retain016/017and021, add022under h1_debt_context_consumer'}
    del later,before,after
    if kind=='installed':
        ordinary=read(HERE/'ordinary.json.gz')
        for key in receipt:
            if key!='imports':same(receipt[key],ordinary[key],'Installed mismatch: '+key)
        controls_worker('installed-controls.json');same(read(HERE/'installed-controls.json'),read(HERE/'controls.json'),'Installed corruption refusals differ')
    save(HERE/(kind+'.json.gz'),receipt)

def controls_worker(output='controls.json'):
    from legalmath.prospectus.successor import service
    original=read(BASE/'attempt-007/products.json.gz');current=build_products(original);rows=[]
    for change in ('missing_p2','changed_p2','missing_p3','changed_p3','unsupplied'):
        bad=deepcopy(current);request=bad['P1']['payload']['request'];p2,p3=bad['P2']['payload'],bad['P3']['payload']
        if change=='missing_p2':del p2['source_statement_cells']
        elif change=='changed_p2':p2['source_statement_cells']['reading']['debt_context']['issues']['rows'][2]['date_role']='COMPULSORY_MATURITY'
        elif change=='missing_p3':del p3['source_statement_cells_sha256']
        elif change=='changed_p3':p3['source_statement_cells_sha256']='0'*64
        else:del request['source_statement_cells']
        b=request['bundle'];bad['P1']=service.seal('P1',b,{'request':digest(request)},bad['P1']['payload'])
        for phase,parents in [('P2',['P1']),('P3',['P1','P2']),('P4',['P1','P3']),('P5',['P2','P3'])]:
            bad[phase]=service.seal(phase,b,{p:bad[p]['sha256'] for p in parents},bad[phase]['payload'])
        try:service.consume(bad,ROOT,include_artifacts=True)
        except ValueError as exc:
            require('Consumed statement cells' in str(exc),'Unexpected refusal')
            rows.append({'case':change,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else:raise ValueError('Forged rehashed product accepted: '+change)
    save(HERE/output,{'status':'PASS','actual_consumer_refusals':rows})

def package_worker():
    candidate_frozen();source=HERE/'package-source';source.mkdir();shutil.copyfile(ROOT/'pyproject.toml',source/'pyproject.toml')
    shutil.copytree(ROOT/'src',source/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.pyo','*.egg-info'))
    config=read(PREP/'config.json');python=config['package_python'];require(sha(python)==config['python_sha256'],'Build interpreter changed')
    command('wheel',[python,'-I','-B','-m','pip','wheel','--no-deps','--no-build-isolation','--no-index','--wheel-dir',str(HERE/'wheel'),str(source)],60)
    wheels=list((HERE/'wheel').glob('*.whl'));require(len(wheels)==1,'Exactly one wheel required')
    expected={n.removeprefix('src/legalmath/'):h for n,h in read(HERE/'candidate-production.json').items()}
    with zipfile.ZipFile(wheels[0]) as archive:
        actual={n.removeprefix('legalmath/'):digest(archive.read(n)) for n in archive.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    same(actual,expected,'Wheel differs from candidate')
    command('install',[python,'-I','-B','-m','pip','install','--no-index','--no-deps','--no-compile','--target',str(HERE/'installed'),str(wheels[0])],60)
    folder=HERE/'installed/legalmath';same({str(p.relative_to(folder)):sha(p) for p in folder.rglob('*') if p.is_file()},expected,'Installed bytes differ')
    save(HERE/'package.json',{'python':python,'wheel':prior.ref(wheels[0]),'files':expected})

def coverage_worker():
    previous=read(BASE/'attempt-021/requirements.json');rows=deepcopy(previous['rows'])
    for row in rows:
        if row.get('status')=='THIS_ATTEMPT_MUST_PASS':row.update(status='RETAINED_COMPLETE_FINITE_INTEGRATION',evidence=prior.ref(BASE/'attempt-021/result.json'))
    rows.append({'requirement':'Note35debt summary/16issues/movements and policies2.8/2.9','status':'THIS_ATTEMPT_MUST_PASS; see stage outcomes'})
    save(HERE/'requirements.json',{'rows':rows,'original_task_acceptance':False,'external_adviser_opinion_required':False,
        'next_discriminating_work':'Remaining Note32debt securities disclosure and source-authority/incorporation requirements; map coverage before another integration. Note35 alone cannot resolve full source05.'})

def stage(name):
    require(name in DEPENDENCIES and not (HERE/'stages'/name).exists(),'Stage already started or unknown')
    for parent in DEPENDENCIES[name]:require(read(HERE/'stages'/parent/'result.json')['status']=='PASS','Failed predecessor '+parent)
    frozen();reserve=46*1024**2 if name=='package' else 4*1024**2
    require(costs(reserve)['execution_allowed'],'Stage resource reservation exhausted')
    from legalmath.prospectus.execution_authority import process_identity
    save(HERE/'stages'/name/'started.json',{'identity':process_identity(os.getpid()),'at':datetime.now(timezone.utc).isoformat(),'stage':name})
    error=None
    try:
        if name=='render':render_worker()
        elif name=='package':package_worker()
        elif name=='tests':command('tests',[str(ROOT/'.venv/bin/python'),'-B','-m','pytest','-q',*TESTS,'--junitxml='+str(HERE/'tests.xml')],120)
        else:
            python=read(PREP/'config.json')['package_python'] if name=='installed' else str(ROOT/'.venv/bin/python')
            command(name,[python,'-I','-B',str(ROOT/SELF),'worker-'+name],120)
        frozen()
    except Exception as exc:error={'type':type(exc).__name__,'reason':str(exc)}
    save(HERE/'stages'/name/'result.json',{'status':'FAIL' if error else 'PASS','error':error})
    return {'stage':name,'status':'FAIL' if error else 'PASS','error':error,'resources':costs()}

def finalize():
    require(not (HERE/'outputs.json').exists(),'Already sealed')
    outcomes={n:read(HERE/'stages'/n/'result.json')['status'] if (HERE/'stages'/n/'result.json').exists() else 'BLOCKED' for n in DEPENDENCIES}
    passed=all(v=='PASS' for v in outcomes.values())
    save(HERE/'result.json',{'task':'source-bes-dep-05','status':'PASS' if passed else 'FAIL','stages':outcomes,
        'task_complete':False,'whole_program_complete':False,'build_criteria_claimed':[],'resources':costs()})
    (HERE/'RESULT.md').write_text('# H1 debt context continuation\n\n'+('Finite source/consumer integration passed. ' if passed else 'Campaign did not pass. ')
        +'Actual stage results: '+json.dumps(outcomes)+'.\n\n'
        +'Source work covers original Note35 and policies2.8/2.9. Existing021 primary statements and all016/017supplements are preserved by checked lossless composition. '
        +'Call-date markers, currency versus table units, issued versus carrying amounts, unknown dashes and accounting-policy conditions remain distinct. '
        +'The gain-comparison period keeps its exact ambiguous source wording. Accounting derecognition does not establish a particular noteholder repayment right.\n\n'
        +'|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|\n|---|---|---|---|---|---|\n'
        +'|'+('Retain finite integration' if passed else 'Retain actual failure')+'|Original images/quotes/geometry; full normal and installed delivery|See stage records|Remaining notes, controlling edition and incorporation|Record/refresh; follow requirements.json|Financial truth, legal entitlement, automatic extraction, whole build|\n\n'
        +'Post-run review: exact profiles preserve supplied interpretations but cannot prove them. Image checks discriminate row association errors; the absence of a marker on a perpetual row remains a source limitation. '
        +'No source claim is promoted to current law. Missing broader coverage remains an implementation/evidence gap, not evidence against a package.\n')
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(p) for p in sorted((HERE/'commands').glob('*.json'))],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU_ONLY;CUDA_VISIBLE_DEVICES=-1;GPU intentionally hidden',
        'random_seeds':'N/A deterministic','plan':PLAN,'result':rel(HERE/'RESULT.md'),'data_version':prior.ref(PREP/'freeze.json'),'resources':costs()})
    save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    return {'status':'SEALED','candidate_passed':passed,'resources':costs()}

if __name__=='__main__':
    sys.dont_write_bytecode=True
    os.environ.update(CUDA_VISIBLE_DEVICES='-1',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
    action=sys.argv[1]
    if action.startswith('worker-'):
        kind=action.removeprefix('worker-');sys.path.insert(0,str(HERE/'installed') if kind=='installed' else str(ROOT/'src'))
        def forbidden(*args,**kwargs):raise RuntimeError('No native/network child in source/consumer worker')
        subprocess.Popen=forbidden
        if kind in ('ordinary','installed'):consumer_worker(kind)
        else:{'source':source_worker,'implement':implement_worker,'controls':controls_worker,'coverage':coverage_worker}[kind]()
        result={'status':'PASS','worker':kind}
    elif action=='prepare':result=prepare()
    elif action=='finalize':result=finalize()
    else:result=stage(action)
    print(json.dumps(result))
