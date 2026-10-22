"""Bounded original investment and risk-management derivative delivery."""
from copy import deepcopy
from datetime import datetime, timezone
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
from scripts import prospectus_h1_financial_policies as prior
from scripts import prospectus_h1_statement_consumer as common

read, save, sha, digest = prior.read, prior.save, prior.sha, prior.digest
compact_digest, same, require, rel = prior.compact_digest, prior.same, prior.require, prior.rel
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
BASE = AUTH / 'attempts/source-bes-dep-05'
PREP = AUTH / 'reviews/h1-investment-hedges-394'
HERE = BASE / 'attempt-031'
SELF = 'scripts/prospectus_h1_investment_hedges.py'
PLAN = 'docs/plans/prospectus-h1-investment-hedges-2026-10-21.md'
PRODUCTION = prior.PRODUCTION
PROFILE = 'bes-h1-2010-statements-investment-hedges.v10'
DOCUMENT, PDF = prior.DOCUMENT, prior.PDF
PAGES = (126,127)
TESTS = prior.TESTS
DEPENDENCIES = {'render': [], 'source': ['render'], 'implement': ['source'],
    'tests': ['implement'], 'ordinary': ['tests'], 'controls': ['ordinary'],
    'package': ['controls'], 'installed': ['package'], 'coverage': []}


def authority():
    sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
    from legalmath.prospectus.execution_authority import Authority
    return Authority(ROOT)


def costs(reserve=0):
    start = read(PREP/'accounting-start.json')
    paths = {p for d in (PREP, HERE) if d.exists() for p in d.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in (PLAN, SELF, PRODUCTION))
    paths.add(AUTH/'revisions/0394.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH/'program.json').stat().st_size-start['program_bytes'])
    seconds = sum(read(p)['wall_seconds'] for d in (PREP, HERE) for p in d.glob('commands/*.json'))
    return {'new_bytes': size, 'new_measured_seconds': seconds, 'new_control_seconds': 60,
        'prior_known_bytes': start['prior_known_bytes'], 'prior_known_seconds': start['prior_known_seconds'],
        'known_cumulative_bytes': start['prior_known_bytes']+size,
        'known_cumulative_seconds': start['prior_known_seconds']+seconds+60,
        'earlier_manual_and_unmeasured_costs': 'UNKNOWN; history retained',
        'execution_allowed': size+reserve < 110*1024**2 and seconds < 840}


def prepare():
    tick=time.monotonic(); auth=authority(); old=read(AUTH/'program.json')
    require(old['revision']==393 and not PREP.exists() and not HERE.exists(),'Fresh393 required')
    events=auth.events()
    attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e['budget_key']=='source-bes-dep-05']
    require(len(attempts)==old['budgets']['source-bes-dep-05']['maximum_new_attempts']==30,'Retain30attempts')
    require(read(prior.HERE/'result.json')['status']=='PASS','030 must pass')
    protected={}
    for n in (7,15,16,17,21,22,23,24,25,26,27,28,29,30):
        folder=BASE/f'attempt-{n:03d}'; manifest=folder/'outputs.json'
        records=[e for e in events if e.get('attempt')==rel(folder) and 'outputs_sha256' in e]
        require(records and sha(manifest)==records[-1]['outputs_sha256'],'Unauthenticated original')
        protected[rel(manifest)]=sha(manifest)
        for name,h in read(manifest).items(): require(sha(folder/name)==h,'Changed original '+name)
    previous=prior.costs()
    save(PREP/'accounting-start.json',{'prior_known_bytes':previous['known_cumulative_bytes'],
        'prior_known_seconds':previous['known_cumulative_seconds'],'prior_cost_receipt':previous,
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size})
    (PREP/'baseline').mkdir(); shutil.copyfile(ROOT/PRODUCTION,PREP/'baseline/statement_cells.py')
    production=common.production();save(PREP/'baseline/production.json',production)
    protected.update({n:h for n,h in read(prior.PREP/'freeze.json')['bindings'].items() if n!=PRODUCTION})
    names=[PLAN,SELF,prior.SELF,'pyproject.toml',*TESTS,rel(PREP/'baseline/statement_cells.py'),
        rel(PREP/'baseline/production.json'),rel(prior.HERE/'ordinary.json.gz'),
        rel(prior.HERE/'source-units.json'),rel(prior.HERE/'reading.json'),
        rel(prior.HERE/'image-transcript.json'),rel(BASE/'attempt-028/COVERAGE-CORRECTION.md'),
        rel(prior.HERE/'images.json'),rel(prior.HERE/'registry-entry.json'),rel(BASE/'attempt-028/retained-risk-coverage-correction.json')]
    protected.update({n:sha(ROOT/n) for n in names})
    protected.update({n:h for n,h in production.items() if n!=PRODUCTION})
    require(all(sha(ROOT/n)==h for n,h in protected.items()),'Stale inherited binding')
    save(PREP/'freeze.json',{'bindings':protected,'baseline_sha256':sha(ROOT/PRODUCTION),
        'mutable_file':PRODUCTION,'implementation_window':'Once after reviewed source and candidate freeze'})
    config=read(prior.PREP/'config.json'); require(sha(config['package_python'])==config['python_sha256'],'Build interpreter changed')
    save(PREP/'config.json',config)
    new=deepcopy(old);new['revision']=394
    task=next(t for t in new['tasks'] if t['id']=='source-bes-dep-05')
    task.update(dossier=PLAN,pre_admission_review=PLAN,build_criteria_scope=[],
        reason='Deliver original Notes22–23tables and interpretation;preserve030and prior OCRintegration')
    task['inputs']=sorted((set(task['inputs'])-{PRODUCTION})|set(protected)|{rel(PREP/'freeze.json'),rel(PREP/'config.json')})
    bounds={'measured_seconds':840,'control_seconds':60,'new_bytes':112*1024**2,'failure_reserve':2*1024**2,
        'previous_known_bytes':previous['known_cumulative_bytes'],'previous_known_seconds':previous['known_cumulative_seconds'],'unchanged_retries':0}
    task['investment_hedges_evidence']={'version':PROFILE,'freeze':rel(PREP/'freeze.json'),'bounds':bounds,
        'success_dependencies':DEPENDENCIES,'original_task_acceptance':False}
    new['budgets']['source-bes-dep-05']['maximum_new_attempts']=31
    routes=read(ROOT/old['continuation_review']['routes']); routes['baseline_revision']=394
    for row in routes['tasks']:
        if row['task']==task['id']:
            row.update(task_sha256=compact_digest(task),dossier=PLAN,phase=0,
                remaining='030policies and prior OCRintegration retained;Notes22–23and wider source/authority remain.',
                next_action='Execute031Notes22–23through source/normal/installed checks;retain030and reconcile remaining dependencies.',
                stop_condition='31 retained admissions;840+60seconds and112MiB new;no unchanged retry;retain cumulative costs/failures.')
    save(PREP/'routes.json',routes)
    new['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    new['continuation_review']['bindings'].pop(PRODUCTION,None)
    new['continuation_review']['bindings'].update({n:sha(ROOT/n) for n in
        (PLAN,rel(PREP/'routes.json'),rel(PREP/'freeze.json'),rel(PREP/'baseline/statement_cells.py'))})
    require(old['obligations']==new['obligations'] and old['build_contract']==new['build_contract'],'Scope changed')
    raw=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
    source_bytes=sum(p.stat().st_size for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    forecast=costs()['new_bytes']+2*len(raw)+3*source_bytes+10*1024**2
    require(forecast<110*1024**2,'Forecast exceeds reservation')
    with (PREP/'proposal.json').open('xb') as stream:stream.write(raw)
    from legalmath.prospectus.execution_authority import digest as adigest
    save(PREP/'review.json',{'baseline':adigest(old),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Deliver Notes22–23;preserve complete030','Preserve verified original composition including OCRrisk tables','Retain30admissions and all original obligations'],
        'skeptical_audit':{'verdict':'PASS','plan':PLAN,'forecast_new_bytes':forecast,
            'no_proxy_promotion':'Original table associations and actual consumers;hashes and sums do not prove semantic truth or legal standards'},
        'evidence_contract':{'question':'Do original investment and derivative disclosures reach the answer with dates,units,signs,unknowns and distinctions intact?',
            'primary':'Independent image transcript, original geometry/quotes, prior preservation and normal/installed corruption refusals',
            'promotion_veto':['Wrong date/amount/unit','Omitted clause','Lost prior answer','Conflicting duplicate','Wrong import','Accepted corruption'],
            'continuation_veto':['Invalid authority','Corrupt shared originals','Spent resources'],
            'not_concluded':['Automatic extraction','Verified valuation','Holder recovery','Current law','Whole build']},
        'budget_revision':{'budget_key':'source-bes-dep-05','previous_maximum':30,'new_maximum':31,
            'retained_attempts':attempts,'reason':'Original Notes22–23dependency;no replay of030or historical OCRintegration',
            'next_discriminating_check':'Original six-column geometry,unknown dashes,period ambiguity,own-credit amounts and complete downstream delivery',
            'stop_condition':bounds,'same_scope_authorization':'Recover and continue original build'}})
    save(PREP/'commands/preparation.json',{'wall_seconds':time.monotonic()-tick,
        'command':[sys.executable,'-B','-m','scripts.prospectus_h1_investment_hedges','prepare']})
    return {'status':'PREPARED','revision':394,'forecast_new_bytes':forecast,'resources':costs()}


def frozen():
    auth = authority(); admission = read(HERE/'admission.json')
    from legalmath.prospectus.execution_authority import digest as adigest
    require(adigest(read(AUTH/'program.json'))==admission['program_sha256'] and
            auth.binding(admission['task_spec'])==admission['binding'], 'Unchanged admission required')
    f = read(PREP/'freeze.json')
    require(all(sha(ROOT/n)==h for n, h in f['bindings'].items()), 'Frozen input changed')
    expected = read(HERE/'candidate-production.json')[PRODUCTION] if (HERE/'candidate-production.json').exists() else f['baseline_sha256']
    require(sha(ROOT/PRODUCTION)==expected, 'Registry outside implementation window')


def command(name, argv, timeout=240):
    require(costs(1024**2)['execution_allowed'], 'Resource reservation exhausted')
    target = HERE/'commands'; target.mkdir(exist_ok=True); tick = time.monotonic(); result = None; error = None
    try:
        with (target/(name+'.log')).open('x') as stream:
            result = subprocess.run(argv, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout,
                env={**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONDONTWRITEBYTECODE': '1',
                     'PYTHONNOUSERSITE': '1', 'PYTHONPATH': str(ROOT/'src')+os.pathsep+str(ROOT),
                     'PIP_NO_INDEX': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1'})
        require(result.returncode==0, 'Inspect retained '+name+'.log')
    except Exception as exc: error = {'type': type(exc).__name__, 'reason': str(exc)}
    save(target/(name+'.json'), {'command': argv, 'wall_seconds': time.monotonic()-tick,
        'exit_code': None if result is None else result.returncode, 'error': error})
    require(error is None, 'Command failed: '+name+': '+str(error))
    require(costs()['execution_allowed'], 'Post-command resource limit')


def render_worker():
    require(sha(BASE/'attempt-001/interim.pdf')==PDF,'Wrong original PDF')
    (HERE/'images').mkdir()
    for page in PAGES:
        command('render-'+str(page),['pdftoppm','-f',str(page),'-l',str(page),'-r','160','-singlefile','-png',
            str(BASE/'attempt-001/interim.pdf'),str(HERE/'images'/f'page-{page}')],60)
    save(HERE/'images.json',[{'page':p,'path':rel(HERE/'images'/f'page-{p}.png'),'sha256':sha(HERE/'images'/f'page-{p}.png')} for p in PAGES])


def original_units():
    products = read(BASE/'attempt-007/products.json.gz')
    return sorted([u for u in products['P1']['payload']['graph']['units']
        if u['document']==DOCUMENT and u['page'] in PAGES], key=lambda u: (u['page'],u['order'],u['id']))


def combined_units(units):
    by_id={}
    for n in (15,22,23,24,25,26,28,29,30):
        for unit in read(BASE/f'attempt-{n:03d}/source-units.json'):
            if unit['id'] in by_id:same(unit,by_id[unit['id']],'Conflicting prior occurrence')
            by_id[unit['id']]=unit
    require(len(by_id)==2961,'Wrong030occurrence count')
    for unit in units:
        require(unit['id'] not in by_id,'Unexpected source overlap');by_id[unit['id']]=unit
    require(len(by_id)==3133,'Wrong combined occurrences')
    return sorted(by_id.values(),key=lambda u:(u['page'],u['order'],u['id']))




def investment_reading(units):
    lookup={(u['page'],u['order']):u for u in units}
    def q(p,i):
        u=lookup[p,i];return {'id':u['id'],'quote':u['raw']}
    def qs(p,a,b):return [q(p,i) for i in range(a,b+1)]
    def cell(p,i):
        x=q(p,i);raw=''.join(x['quote'].split())
        v=None if raw=='-' else -int(raw[1:-1]) if raw.startswith('(') else int(raw)
        return {**x,'value':v,'unit':'EUR thousands','status':'UNKNOWN' if v is None else 'SOURCE_NUMBER'}
    def row(p,label,indices,inferred=None):
        return {'label_sources':[] if label is None else [q(p,label)],'label':inferred,
                'cells':[cell(p,i) for i in indices]}
    table1={'key':'htm-balances','headers':qs(126,3,5)+[q(126,16)],
        'columns':['2010-06-30','2009-12-31'],'column_sources':[[q(126,4)],[q(126,5)]],
        'rows':[row(126,17,[6,9]),row(126,18,[7,10]),row(126,None,[8,11],'GROSS TOTAL (unlabelled source row)'),
                row(126,19,[12,13]),row(126,None,[14,15],'NET TOTAL (unlabelled source row)')]}
    table2={'key':'htm-impairment-movements','headers':qs(126,24,28),
        'columns':['2010-06-30','2009-12-31','2009-06-30'],
        'column_sources':[[q(126,i)] for i in (26,27,28)],
        'period_heading':q(126,25),'equal_duration_comparison_established':False,
        'rows':[row(126,label,indices) for label,indices in
            [(29,[34,39,44]),(30,[35,40,45]),(31,[36,41,46]),(32,[37,42,47]),(33,[38,43,48]),(49,[50,51,52])]]}
    columns=[f'{d}/{c}' for d in ('2010-06-30','2009-12-31') for c in ('Hedging','Risk management','Total')]
    colrefs=[[q(127,2),q(127,3)],[q(127,2),q(127,4),q(127,5)],[q(127,2),q(127,7)],
             [q(127,6),q(127,8)],[q(127,6),q(127,9),q(127,10)],[q(127,6),q(127,11)]]
    table3={'key':'derivative-fair-values','headers':qs(127,1,12),'columns':columns,'column_sources':colrefs,
        'rows':[row(127,13,[15,18,21,24,27,30]),row(127,14,[16,19,22,25,28,31]),
                row(127,None,[17,20,23,26,29,32],'NET DERIVATIVES (unlabelled source row)')]}
    table4={'key':'hedged-item-fair-value-components','headers':qs(127,1,11)+qs(127,87,89)+[q(127,92)],
        'columns':columns,'column_sources':colrefs,'complete_carrying_values':False,
        'rows':[row(127,90,[33,35,37,39,41,43]),row(127,91,[34,36,38,40,42,44]),
                row(127,None,[45,46,47,48,49,50],'ASSET COMPONENT TOTAL (unlabelled source row)'),
                row(127,93,[51,56,61,66,71,76]),row(127,94,[52,57,62,67,72,77]),
                row(127,95,[53,58,63,68,73,78]),row(127,96,[54,59,64,69,74,79]),
                row(127,None,[55,60,65,70,75,80],'LIABILITY COMPONENT TOTAL (unlabelled source row)'),
                row(127,None,[81,82,83,84,85,86],'NET COMPONENT TOTAL (unlabelled source row)')]}
    clauses=[
        {'key':'htm-no-transfers','sources':qs(126,20,23),'interpretation':'The report states no transfers into HTM in H1 2010 or 2009 and introduces impairment movements at June2010 and December2009; preserve the displayed third June2009 column and period heading without assuming equal flow durations.'},
        {'key':'collateral','sources':[q(126,53)],'interpretation':'Pledged securities are referred to Note39; specific pledged assets and legal collateral rights are not resolved here.'},
        {'key':'derivative-dates','sources':qs(126,54,56),'interpretation':'Note23 presents risk-management derivative fair values at June30,2010 and December31,2009.'},
        {'key':'hedge-categories','sources':qs(127,97,100),'interpretation':'Risk-management purposes include designated hedges AND derivatives managing FVTPL asset/liability risks without hedge designation; preserve the reference to policy2.4.'},
        {'key':'income-recognition','sources':qs(127,101,103),'interpretation':'Fair-value changes of hedged items and corresponding derivatives enter net gains/losses from financial assets at FVTPL; retain Note7 dependency.'},
        {'key':'ineffectiveness','sources':qs(127,104,106),'interpretation':'Reported fair-value-hedge ineffectiveness is EUR0.2million at June30,2010 and EUR15.3million at June30,2009,recognised in income; ongoing effectiveness evaluation is reported. No ratio or causal improvement is inferred.'},
        {'key':'own-credit','sources':qs(127,107,110),'interpretation':'Own-credit fair-value component of FVTPL financial liabilities is EUR129236thousand cumulative profits at June30,2010 versus EUR68755thousand at December31,2009,and EUR60481thousand six-month profits at June30,2010 versus EUR207thousand at June30,2009. These are reported accounting profits,not cash receipts or evidence of improved creditworthiness.'}]
    return {'source_groups':{str(p):[q(p,u['order']) for u in units if u['page']==p] for p in PAGES},
        'tables':[table1,table2,table3,table4],'clauses':clauses,
        'amounts':{'ineffectiveness':{'unit':'EUR million','2010-06-30':'0.2','2009-06-30':'15.3'},
            'own_credit_cumulative':{'unit':'EUR thousands','2010-06-30':129236,'2009-12-31':68755},
            'own_credit_six_month':{'unit':'EUR thousands','2010-06-30':60481,'2009-06-30':207}},
        'distinctions':{'all_risk_management_derivatives_are_hedges':False,
            'hedged_item_components_are_complete_balances':False,'dashes_imputed_zero':False,
            'impairment_flow_equal_duration_established':False,'htm_transfers_reported':False,
            'ineffectiveness_means_hedges_failed':False,'own_credit_profit_is_cash_receipt':False,
            'own_credit_profit_proves_credit_improvement':False,'legal_netting_established':False,
            'holder_recovery_established':False},
        'source_dependencies':{'policy2.4':'RETAINED_030','policy2.6':'RETAINED_030',
            'Note7':'FULL_INTERPRETATION_NOT_ESTABLISHED','Note39':'FULL_INTERPRETATION_NOT_ESTABLISHED'},
        'source_context':{'origin':'SUPPLIED_DEVELOPMENT_READING','source_authenticity':'NOT_ESTABLISHED',
            'incorporation_status':'UNRESOLVED','current_law_or_standard_verified':False,'historical_report_claims_only':True}}




def source_check(reading,units,transcript):
    require(len(units)==172 and len({u['id'] for u in units})==172,'Complete172occurrences required')
    lookup={u['id']:u for u in units};s=reading['investment_hedges_evidence']
    require(all(u['visible'] and u['source_sha256']==PDF and u['page'] in PAGES for u in units),'Changed source')
    def quotes(v):
        ids=[]
        if isinstance(v,dict):
            if 'id' in v and 'quote' in v:
                require(v['id'] in lookup and v['quote']==lookup[v['id']]['raw'],'Changed exact quote');ids.append(v['id'])
            for k,x in v.items():
                if k not in ('id','quote'):ids+=quotes(x)
        elif isinstance(v,list):
            for x in v:ids+=quotes(x)
        return ids
    quotes(s);same(set(quotes(s['source_groups'])),set(lookup),'Incomplete source pages')
    expected={u['id'] for u in units if (u['page']==126 and (20<=u['order']<=23 or 53<=u['order']<=56)) or (u['page']==127 and 97<=u['order']<=110)}
    same(set(quotes(s['clauses'])),expected,'Incomplete explanatory clauses')
    require(len(s['tables'])==len(transcript['tables'])==4,'Four independent tables required')
    norm=lambda text:''.join(text.split());cells=[]
    for table,typed in zip(s['tables'],transcript['tables']):
        same(table['key'],typed['key'],'Wrong table identity');same(table['columns'],typed['columns'],'Wrong column identity')
        require(len(table['rows'])==len(typed['rows']),'Wrong row count')
        for row,manual in zip(table['rows'],typed['rows']):
            label=' '.join(q['quote'] for q in row['label_sources']) if row['label_sources'] else row['label']
            same(norm(label),norm(manual[0]),'Wrong row label')
            require(len(row['cells'])==len(manual[1])==len(table['columns']),'Wrong cells per row')
            bboxes=[lookup[c['id']]['bbox'] for c in row['cells']]
            require(all(a[2]<b[0] for a,b in zip(bboxes,bboxes[1:])),'Wrong column geometry')
            require(max(b[1] for b in bboxes)-min(b[1] for b in bboxes)<3,'Wrong row geometry')
            for q in row['label_sources']:
                a=lookup[q['id']]['bbox'];require(a[2]<bboxes[0][0] and abs(a[1]-bboxes[0][1])<3,'Wrong label geometry')
            for c,value in zip(row['cells'],manual[1]):
                token=norm(c['quote']);expected_value=None if token=='-' else -int(token[1:-1]) if token.startswith('(') else int(token)
                require(c['value']==value==expected_value and c['unit']=='EUR thousands','Wrong numeric association')
                require(c['status']==('UNKNOWN' if value is None else 'SOURCE_NUMBER'),'Wrong unknown treatment');cells.append(c)
    require(len(cells)==100 and sum(c['value'] is None for c in cells)==7,'Wrong full numeric/unknown coverage')
    require(len({c['id'] for c in cells})==100,'Duplicate table position')
    same(s['amounts'],transcript['amounts'],'Wrong prose amount,date,period or unit')
    same(s['distinctions'],transcript['distinctions'],'Wrong semantic distinction')
    same(transcript['pages_reviewed'],list(PAGES),'Original images not all reviewed')
    for anchor in transcript['anchors']:
        text=' '.join(x['quote'] for c in s['clauses'] if c['key']==anchor['key'] for x in c['sources'])
        require(' '.join(anchor['quote'].split()) in ' '.join(text.split()),'Independent prose anchor mismatch')
    same(norm(s['tables'][1]['period_heading']['quote']),norm(transcript['impairment_period_heading']),'Period heading changed')
    require(not s['tables'][1]['equal_duration_comparison_established'] and not s['tables'][3]['complete_carrying_values'],'Unsupported scope')
    old=read(prior.HERE/'reading.json');same({k:v for k,v in reading.items() if k!='investment_hedges_evidence'},old,'030reading changed')
    prior.source_check(old,read(prior.HERE/'source-units.json'),read(prior.HERE/'image-transcript.json'))
    return {'local_occurrences':172,'total_occurrences':len(combined_units(units)),'tables':4,'table_rows':23,
        'numeric_or_unknown_positions':100,'unknown_dashes':7,'substantive_occurrences':len(expected),
        'complete_prior_fields_preserved':True,'source_truth_or_general_parser_proof':False}




def source_worker():
    units=original_units();transcript=read(HERE/'image-transcript.json');review=HERE/'SOURCE-REVIEW.md'
    require(review.is_file() and len(review.read_text())>1000,'Substantive source review required')
    for item in read(HERE/'images.json'):require(sha(ROOT/item['path'])==item['sha256'],'Source image changed')
    reading=deepcopy(read(prior.HERE/'reading.json'));reading['investment_hedges_evidence']=investment_reading(units)
    checked=source_check(reading,units,transcript);all_units=combined_units(units)
    save(HERE/'source-units.json',units);save(HERE/'reading.json',reading)
    entry={'document':DOCUMENT,'source':PDF,'reading':compact_digest(reading),'pages_digest':compact_digest(all_units),
        'pages':sorted({u['page'] for u in all_units}),'occurrences':len(all_units),
        'reading_fields':list(read(prior.HERE/'registry-entry.json')['reading_fields'])+['investment_hedges_evidence']}
    original=(PREP/'baseline/statement_cells.py').read_text()
    require(PROFILE not in original and original.count('PROFILES = {')==1,'Baseline registry changed')
    candidate=original.replace('PROFILES = {\n','PROFILES = {\n    '+repr(PROFILE)+': '+repr(entry)+',\n',1)
    (HERE/'candidate-statement_cells.py').write_text(candidate);save(HERE/'registry-entry.json',entry)
    names=['reading.json','source-units.json','registry-entry.json','candidate-statement_cells.py','image-transcript.json','SOURCE-REVIEW.md','images.json']
    save(HERE/'candidate-freeze.json',{'bindings':{n:sha(HERE/n) for n in names},'candidate_sha256':digest(candidate.encode())})
    from legalmath.prospectus.successor import statement_cells as cells
    try:cells.admit({'units':all_units},supplied({'units':all_units}))
    except ValueError as exc:require('Unsupported source statement' in str(exc),'Unexpected baseline refusal')
    else:raise ValueError('New profile already supported')
    save(HERE/'source-check.json',{'status':'PASS',**checked,'baseline_gap':'Notes22–23profile unsupported','source_review':common.ref(review)})


def candidate_frozen():
    f=read(HERE/'candidate-freeze.json')
    require(all(sha(HERE/n)==h for n,h in f['bindings'].items()),'Candidate interpretation changed')
    return f


def implement_worker():
    f=candidate_frozen(); require(sha(ROOT/PRODUCTION)==read(PREP/'freeze.json')['baseline_sha256'],'Baseline changed')
    shutil.copyfile(HERE/'candidate-statement_cells.py',ROOT/PRODUCTION)
    require(sha(ROOT/PRODUCTION)==f['candidate_sha256'],'Registry write failed')
    save(HERE/'candidate-production.json',common.production())


def supplied(graph):
    return {'version':'source-statement-cells.v1','profile':PROFILE,'document':DOCUMENT,'graph_sha256':digest(graph),
        'review':{'kind':'DEVELOPMENT','reviewer':'Original page images,exact clauses and independently transcribed tables',
            'reason':'Complete030plus Notes22–23;dates,signs,unknowns and historical scope remain explicit'},
        'reading':read(HERE/'reading.json')}


def build_products(original):
    from legalmath.prospectus.successor import service
    p1=deepcopy(original['P1']); request=p1['payload']['request']; request['source_statement_cells']=supplied(p1['payload']['graph'])
    p1=service.seal('P1',request['bundle'],{'request':digest(request)},p1['payload'])
    p2=service.construction_product(p1,ROOT); p3=service.interpretation_product(p1,p2,original['P3']['payload'].get('interpretation_input'))
    l,f=original['P4']['payload'],original['P5']['payload']
    return {'P1':p1,'P2':p2,'P3':p3,'P4':service.law_product(p1,p3,l.get('cases'),l.get('law_input')),
            'P5':service.financial_product(p1,p2,p3,f.get('cases'),f.get('scenario_input'))}


def registry_controls():
    from legalmath.prospectus.successor import statement_cells as cells
    graph={'units':combined_units(read(HERE/'source-units.json'))};rows=[]
    changes={key:(lambda s,k=key:s['distinctions'].update({k:True}))
        for key in read(HERE/'reading.json')['investment_hedges_evidence']['distinctions']}
    changes.update({
        'date-reversed':lambda s:s['tables'][0]['columns'].reverse(),
        'hedge-categories-reversed':lambda s:s['tables'][2]['columns'].reverse(),
        'unknown-to-zero':lambda s:s['tables'][1]['rows'][0]['cells'][2].update(value=0,status='SOURCE_NUMBER'),
        'liability-sign':lambda s:s['tables'][2]['rows'][1]['cells'][0].update(value=84400),
        'wrong-unit':lambda s:s['tables'][0]['rows'][0]['cells'][0].update(unit='EUR million'),
        'period-heading-lost':lambda s:s['tables'][1].pop('period_heading'),
        'row-lost':lambda s:s['tables'][3]['rows'].pop(),
        'clause-lost':lambda s:s['clauses'].pop(),
        'own-credit-period':lambda s:s['amounts']['own_credit_six_month'].update({'2009-12-31':207}),
        'own-credit-unit':lambda s:s['amounts']['own_credit_cumulative'].update(unit='EUR million'),
        'ineffectiveness-amount':lambda s:s['amounts']['ineffectiveness'].update({'2010-06-30':'15.3'}),
        'current-law':lambda s:s['source_context'].update(current_law_or_standard_verified=True),
        'incorporation':lambda s:s['source_context'].update(incorporation_status='CONFIRMED')})
    for name,change in changes.items():
        bad=supplied(graph);change(bad['reading']['investment_hedges_evidence'])
        try:cells.admit(graph,bad)
        except ValueError as exc:rows.append({'case':name,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else:raise ValueError('Altered reading accepted: '+name)
    for name in ('missing-page','source-hash','geometry','duplicate-occurrence'):
        g=deepcopy(graph)
        if name=='missing-page':g['units']=[u for u in g['units'] if u['page']!=127]
        elif name=='source-hash':next(u for u in g['units'] if u['page']==126)['source_sha256']='0'*64
        elif name=='geometry':next(u for u in g['units'] if u['page']==126)['bbox'][0]+=1
        else:g['units'].append(deepcopy(next(u for u in g['units'] if u['page']==127)))
        bad=supplied(g)
        try:cells.admit(g,bad)
        except ValueError as exc:rows.append({'case':name,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else:raise ValueError('Altered source accepted: '+name)
    return rows




def consumer_worker(kind):
    from legalmath.prospectus.successor import service
    candidate_frozen(); original=read(BASE/'attempt-007/products.json.gz')
    baseline=prior.build_products(original); before=service.consume(baseline,ROOT,include_artifacts=True)
    previous=read(prior.HERE/'ordinary.json.gz')
    require(digest(before)==previous['answer_sha256'],'Complete030baseline answer changed')
    current=build_products(original); after=service.consume(current,ROOT,include_artifacts=True)
    for phase in ('P2','P3','P4','P5'):
        left,right=deepcopy(baseline[phase]['payload']),deepcopy(current[phase]['payload'])
        if phase=='P2': left.pop('source_statement_cells'); right.pop('source_statement_cells')
        if phase=='P3': left.pop('source_statement_cells_sha256'); right.pop('source_statement_cells_sha256')
        same(left,right,'Unexpected phase payload change: '+phase)
    same(current['P1']['payload']['graph'],baseline['P1']['payload']['graph'],'Source graph changed')
    left,right=deepcopy(baseline['P1']['payload']['request']),deepcopy(current['P1']['payload']['request'])
    left.pop('source_statement_cells'); right.pop('source_statement_cells'); same(left,right,'Unrelated request changed')
    replacements={k:after[k] for k in ('request_sha256','consumed_products','report_sha256')}
    same({**before,**replacements,'source_statement_cells':after['source_statement_cells']},after,'Unrelated answer change')
    same(before['questions'],after['questions'],'Original questions changed')
    require(after['questions']['Q3']['status']=='PARTIAL' and not after['may_execute_transaction'] and
            not after['independent_legal_acceptance'],'Original limits changed')
    baseline_reading=read(prior.HERE/'reading.json')
    for key in baseline_reading: same(before['source_statement_cells'][key],after['source_statement_cells'][key],'Lost030field '+key)
    body=after['source_statement_cells']; reading=read(HERE/'reading.json')
    for key in reading: same(body[key],reading[key],'Incomplete delivered field '+key)
    require(body['consumed'] and not body['independent_financial_acceptance'] and body['legal_dependency_resolution']=='UNCHANGED','Scope overclaim')
    checked=source_check(reading,read(HERE/'source-units.json'),read(HERE/'image-transcript.json'))
    cases=registry_controls()
    imported={n:m.__file__ for n,m in sys.modules.items() if n.startswith('legalmath') and getattr(m,'__file__',None)}
    location=HERE/'installed' if kind=='installed' else ROOT/'src'
    require(imported and all(Path(p).resolve().is_relative_to(location) for p in imported.values()),'Wrong import origin')
    del original,baseline,current,left,right
    composed=read(BASE/'attempt-016/answer-supplement.json.gz'); composition=read(BASE/'attempt-017/composition.json')
    require(digest(composed)==composition['previous_content_sha256'],'Original016changed')
    composed.update(read(BASE/'attempt-017/answer-delta.json.gz'))
    require(digest(composed)==composition['complete_composed_sha256'],'Original017changed')
    keys={21:'h1_normal_statement_consumer',22:'h1_debt_context_consumer',23:'h1_debt_securities_consumer',
          24:'h1_cross_note_consumer',25:'h1_securitisation_consumer',26:'h1_fair_value_consumer',28:'h1_risk_native_consumer',29:'h1_events_consumer',30:'h1_financial_policies_consumer'}
    for n,key in keys.items():
        receipt=read(BASE/f'attempt-{n:03d}/ordinary.json.gz')
        answer={**before,**receipt['replacements'],'source_statement_cells':receipt['addition']}
        require(digest(answer)==receipt['answer_sha256'],'Complete prior answer changed: '+str(n))
        composed[key]=answer
        require(digest(composed)==receipt['full_composed_sha256'],'Complete prior composition changed: '+str(n))
    composed['h1_investment_hedges_consumer']=after
    receipt={'status':'PASS','prior_complete_answer_sha256':digest(before),'answer_sha256':digest(after),
        'prior_full_composed_sha256':previous['full_composed_sha256'],'full_composed_sha256':digest(composed),
        'reading_sha256':compact_digest(reading),'replacements':replacements,'addition':body,'controls':cases,
        'source_check':checked,'imports':imported,'whole_task_complete':False,'source_truth_established':False,
        'recipe':'Reconstruct030from007;preserve016/017and021/022/023/024/025/026/028/029/030compositions;add031as h1_investment_hedges_consumer'}
    del composed,before,after,answer
    if kind=='installed':
        ordinary=read(HERE/'ordinary.json.gz')
        for key in receipt:
            if key!='imports': same(receipt[key],ordinary[key],'Installed mismatch: '+key)
        controls_worker('installed-controls.json')
        same(read(HERE/'installed-controls.json'),read(HERE/'controls.json'),'Installed corruption refusals differ')
    save(HERE/(kind+'.json.gz'),receipt)


def controls_worker(output='controls.json'):
    from legalmath.prospectus.successor import service
    original=read(BASE/'attempt-007/products.json.gz'); current=build_products(original); rows=[]
    for change in ('missing_p2','changed_p2','missing_p3','changed_p3','unsupplied'):
        bad=deepcopy(current); request=bad['P1']['payload']['request']; p2,p3=bad['P2']['payload'],bad['P3']['payload']
        if change=='missing_p2': del p2['source_statement_cells']
        elif change=='changed_p2': p2['source_statement_cells']['reading']['investment_hedges_evidence']['distinctions']['all_risk_management_derivatives_are_hedges']=True
        elif change=='missing_p3': del p3['source_statement_cells_sha256']
        elif change=='changed_p3': p3['source_statement_cells_sha256']='0'*64
        else: del request['source_statement_cells']
        b=request['bundle']; bad['P1']=service.seal('P1',b,{'request':digest(request)},bad['P1']['payload'])
        for phase,parents in [('P2',['P1']),('P3',['P1','P2']),('P4',['P1','P3']),('P5',['P2','P3'])]:
            bad[phase]=service.seal(phase,b,{p:bad[p]['sha256'] for p in parents},bad[phase]['payload'])
        try: service.consume(bad,ROOT,include_artifacts=True)
        except ValueError as exc:
            require('Consumed statement cells' in str(exc),'Unexpected refusal')
            rows.append({'case':change,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else: raise ValueError('Forged rehashed product accepted: '+change)
    save(HERE/output,{'status':'PASS','actual_consumer_refusals':rows})


def package_worker():
    candidate_frozen(); source=HERE/'package-source'; source.mkdir()
    shutil.copyfile(ROOT/'pyproject.toml',source/'pyproject.toml')
    shutil.copytree(ROOT/'src',source/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.pyo','*.egg-info'))
    config=read(PREP/'config.json'); python=config['package_python']
    require(sha(python)==config['python_sha256'],'Build interpreter changed')
    command('wheel',[python,'-I','-B','-m','pip','wheel','--no-deps','--no-build-isolation','--no-index',
        '--wheel-dir',str(HERE/'wheel'),str(source)],60)
    wheels=list((HERE/'wheel').glob('*.whl')); require(len(wheels)==1,'Exactly one wheel required')
    expected={n.removeprefix('src/legalmath/'):h for n,h in read(HERE/'candidate-production.json').items()}
    with zipfile.ZipFile(wheels[0]) as archive:
        actual={n.removeprefix('legalmath/'):digest(archive.read(n)) for n in archive.namelist()
                if n.startswith('legalmath/') and not n.endswith('/')}
    same(actual,expected,'Wheel differs from candidate')
    command('install',[python,'-I','-B','-m','pip','install','--no-index','--no-deps','--no-compile',
        '--target',str(HERE/'installed'),str(wheels[0])],60)
    folder=HERE/'installed/legalmath'
    same({str(p.relative_to(folder)):sha(p) for p in folder.rglob('*') if p.is_file()},expected,'Installed bytes differ')
    save(HERE/'package.json',{'python':python,'wheel':common.ref(wheels[0]),'files':expected})


def coverage_worker():
    rows=deepcopy(read(prior.HERE/'requirements.json')['rows'])
    for row in rows:
        if row.get('status','').startswith('THIS_ATTEMPT_MUST_PASS'):
            row.update(status='RETAINED_COMPLETE_FINITE_INTEGRATION',evidence=common.ref(prior.HERE/'result.json'))
    rows.append({'requirement':'Original Notes22–23with dates,amounts,unknowns and derivative categories;preserve030and earlier OCRrisk integration',
        'status':'THIS_ATTEMPT_MUST_PASS;see actual stage results'})
    inventory=deepcopy(read(prior.HERE/'note-inventory.json'))
    for p in ('2.3','2.4','2.5','2.6','2.7'):inventory['policies'][p]='RETAINED_FINITE_INTEGRATION'
    for row in inventory['notes']:
        if row['note'] in (22,23):row['status']='THIS_ATTEMPT_SUBJECT_TO_STAGE_RESULTS'
    save(HERE/'note-inventory.json',inventory)
    save(HERE/'requirements.json',{'rows':rows,'original_task_acceptance':False,'external_adviser_opinion_required':False,
        'next_discriminating_work':'Inspect Note7income and Note39collateral references against existing interpretations before refining. Broader notes,controlling edition,source authority and incorporation remain.'})




def stage(name):
    require(name in DEPENDENCIES and not (HERE/'stages'/name).exists(),'Stage already started or unknown')
    for parent in DEPENDENCIES[name]: require(read(HERE/'stages'/parent/'result.json')['status']=='PASS','Failed predecessor '+parent)
    frozen(); require(costs(46*1024**2 if name=='package' else 4*1024**2)['execution_allowed'],'Stage reservation exhausted')
    from legalmath.prospectus.execution_authority import process_identity
    save(HERE/'stages'/name/'started.json',{'identity':process_identity(os.getpid()),'at':datetime.now(timezone.utc).isoformat(),'stage':name})
    error=None
    try:
        if name=='render': render_worker()
        elif name=='package': package_worker()
        elif name=='tests': command('tests',[str(ROOT/'.venv/bin/python'),'-B','-m','pytest','-q',*TESTS,'--junitxml='+str(HERE/'tests.xml')],240)
        else:
            python=read(PREP/'config.json')['package_python'] if name=='installed' else str(ROOT/'.venv/bin/python')
            command(name,[python,'-I','-B',str(ROOT/SELF),'worker-'+name],240)
        frozen()
    except Exception as exc: error={'type':type(exc).__name__,'reason':str(exc)}
    save(HERE/'stages'/name/'result.json',{'status':'FAIL' if error else 'PASS','error':error})
    return {'stage':name,'status':'FAIL' if error else 'PASS','error':error,'resources':costs()}


def finalize():
    require(not (HERE/'outputs.json').exists(),'Already sealed')
    outcomes={n:read(HERE/'stages'/n/'result.json')['status'] if (HERE/'stages'/n/'result.json').exists() else 'BLOCKED' for n in DEPENDENCIES}
    passed=all(v=='PASS' for v in outcomes.values())
    save(HERE/'result.json',{'task':'source-bes-dep-05','status':'PASS' if passed else 'FAIL','stages':outcomes,
        'task_complete':False,'whole_program_complete':False,'build_criteria_claimed':[],'resources':costs()})
    (HERE/'RESULT.md').write_text('# Original investment and risk-management derivative disclosures\n\n'+('Finite source/consumer integration passed. ' if passed else 'Campaign did not pass. ')
        +'Actual stages: '+json.dumps(outcomes)+'.\n\n'
        +'Notes22–23retain HTM assets and impairment,derivative categories,hedged-item fair-value components,ineffectiveness and own-credit profits with dates,signs and unknown cells. '
        +'The full030answer and all original compositions including supplied OCRrisk tables remain preserved. '
        +'Historical report claims do not establish current standards,rights,valuation or whole-source acceptance.\n\n'
        +'|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|\n|---|---|---|---|---|---|\n'
        +'|'+('Retain finite integration' if passed else 'Retain actual failure')+'|Original images/quotes/geometry and actual full normal/installed answers|See stage records|Remaining notes and authority|Record/refresh;review Note7and Note39dependencies and remaining original coverage|Financial truth,current law,holder entitlement,automatic extraction,whole build|\n\n'
        +'Post-run review: exact profiles preserve supplied readings; a shared wrong interpretation remains the strongest alternative explanation. '
        +'The independent image transcript and full quote/geometry review address source association and omissions. '
        +'They do not prove external financial or legal truth. Remaining coverage is an implementation/evidence gap,not evidence that a package is fundamentally unsuitable.\n')
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(p) for p in sorted((HERE/'commands').glob('*.json'))],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU_ONLY;CUDA_VISIBLE_DEVICES=-1;GPU intentionally hidden',
        'random_seeds':'N/A deterministic','plan':PLAN,'result':rel(HERE/'RESULT.md'),
        'data_version':common.ref(PREP/'freeze.json'),'resources':costs()})
    save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    return {'status':'SEALED','candidate_passed':passed,'resources':costs()}


if __name__=='__main__':
    sys.dont_write_bytecode=True
    os.environ.update(CUDA_VISIBLE_DEVICES='-1',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
    action=sys.argv[1]
    if action.startswith('worker-'):
        kind=action.removeprefix('worker-'); sys.path.insert(0,str(HERE/'installed') if kind=='installed' else str(ROOT/'src'))
        def forbidden(*args,**kwargs): raise RuntimeError('No native/network child in source/consumer worker')
        subprocess.Popen=forbidden
        if kind in ('ordinary','installed'): consumer_worker(kind)
        else: {'source':source_worker,'implement':implement_worker,'controls':controls_worker,'coverage':coverage_worker}[kind]()
        result={'status':'PASS','worker':kind}
    elif action=='prepare': result=prepare()
    elif action=='finalize': result=finalize()
    else: result=stage(action)
    print(json.dumps(result))
