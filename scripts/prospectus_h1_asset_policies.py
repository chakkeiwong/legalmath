"""Bounded original offsetting, property, software and lease policy delivery."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import gzip
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import prospectus_h1_associates_storage_repair as prior
from scripts import prospectus_h1_statement_consumer as common
from scripts import prospectus_h1_bounded_consumer as delivery

read, save, sha, digest = prior.read, prior.save, prior.sha, prior.digest
compact_digest, same, require, rel = prior.compact_digest, prior.same, prior.require, prior.rel
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
BASE = AUTH / 'attempts/source-bes-dep-05'
PREP = AUTH / 'reviews/h1-asset-policies-408'
HERE = BASE / 'attempt-045'
SELF = 'scripts/prospectus_h1_asset_policies.py'
PLAN = 'docs/plans/prospectus-h1-asset-policies-2026-10-21.md'
READING = 'reading.json.gz'
PRODUCTION = prior.PRODUCTION
PROFILE = 'bes-h1-2010-statements-asset-policies.v20'
DOCUMENT, PDF = prior.DOCUMENT, prior.PDF
PAGES = (82,83,84,85)
TESTS = prior.TESTS
KEYS={**delivery.KEYS,44:'h1_associates_consumer'}
DEPENDENCIES={'render':[],'source':['render'],'implement':['source'],'tests':['implement'],
    'baseline':['tests'],'ordinary':['tests'],'compare':['baseline','ordinary'],
    'composition':['compare'],'controls':['compare'],'package':['composition','controls'],
    'installed':['package'],'installed-compare':['installed','compare'],
    'installed-composition':['installed-compare','composition'],
    'installed-controls':['installed-compare','controls'],'coverage':[]}


def authority():
    sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
    from legalmath.prospectus.execution_authority import Authority
    return Authority(ROOT)


def costs(reserve=0, seconds_reserve=0):
    start = read(PREP/'accounting-start.json')
    paths = {p for d in (PREP, HERE) if d.exists() for p in d.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in (PLAN, SELF, PRODUCTION))
    paths.add(AUTH/'revisions/0408.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists()) + start.get('temporary_preparation_bytes',0)
    size += max(0, (AUTH/'program.json').stat().st_size-start['program_bytes'])
    seconds = sum(read(p)['wall_seconds'] for d in (PREP, HERE) for p in d.glob('commands/*.json'))
    return {'new_bytes': size, 'new_measured_seconds': seconds, 'new_control_seconds': 60,
        'prior_known_bytes': start['prior_known_bytes'], 'prior_known_seconds': start['prior_known_seconds'],
        'known_cumulative_bytes': start['prior_known_bytes']+size,
        'known_cumulative_seconds': start['prior_known_seconds']+seconds+60,
        'earlier_manual_and_unmeasured_costs': 'UNKNOWN; history retained',
        'execution_allowed': size+reserve < 252*1024**2 and seconds+seconds_reserve < 1200}


def prepare():
    tick=time.monotonic(); auth=authority(); old=read(AUTH/'program.json')
    require(old['revision']==407 and not PREP.exists() and not HERE.exists(),'Fresh407 required')
    events=auth.events()
    attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e['budget_key']=='source-bes-dep-05']
    require(len(attempts)==old['budgets']['source-bes-dep-05']['maximum_new_attempts']==44,'Retain44attempts')
    require(read(delivery.HERE/'result.json')['status']=='PASS','Successful044 required')
    protected={}
    for n in (7,15,16,17,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44):
        folder=BASE/f'attempt-{n:03d}'; manifest=folder/'outputs.json'
        records=[e for e in events if e.get('attempt')==rel(folder) and 'outputs_sha256' in e]
        require(records and sha(manifest)==records[-1]['outputs_sha256'],'Unauthenticated original')
        protected[rel(manifest)]=sha(manifest)
        for name,h in read(manifest).items(): require(sha(folder/name)==h,'Changed original '+name)
    previous=delivery.costs()
    temporary=ROOT/'.localresources/prospectus-preparation/h1-asset-policies-045'
    temporary_bytes=sum(p.stat().st_size for p in temporary.rglob('*') if p.is_file())
    temporary_bytes+=sum(p.stat().st_size for p in (ROOT/'.localresources/prospectus-preparation/h1-asset-policies-044').rglob('*') if p.is_file())
    temporary_bytes+=sum(p.stat().st_size for p in Path('/tmp/prospectus-policy-preparation').rglob('*') if p.is_file())
    save(PREP/'accounting-start.json',{'prior_known_bytes':previous['known_cumulative_bytes'],
        'prior_known_seconds':previous['known_cumulative_seconds'],'prior_cost_receipt':previous,
        'temporary_preparation_bytes':temporary_bytes,
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size})
    preflight=read(temporary/'preflight.json')
    require(preflight['status']=='PASS' and preflight['actual_source_worker_passed'] and
        preflight['retained_source_reading_and_candidate_identical'],'Unchanged actual source-worker preflight required')
    save(PREP/'mapping-preflight.json',preflight)
    save(PREP/'commands/mapping-preflight.json',{'wall_seconds':preflight['seconds'],
        'command':'Actual asset-policy source-worker, gzip storage, original graph and adverse preflight'})
    old_preflight=read(ROOT/'.localresources/prospectus-preparation/h1-asset-policies-044/preflight.json')
    save(PREP/'commands/original-preflight.json',{'wall_seconds':old_preflight['seconds'],
        'command':'Retained original policy source preparation; new preflight verifies unchanged reading and candidate'})
    shutil.copytree(temporary,PREP/'preflight-execution')
    image_prep=Path('/tmp/prospectus-policy-preparation')
    shutil.copytree(image_prep,PREP/'source-preparation')
    images=[]
    for page in PAGES:
        path=PREP/'source-preparation'/f'page-{page}.png'
        images.append({'page':page,'path':rel(path),'sha256':sha(path)})
        save(PREP/'commands'/f'render-{page}.json',read(image_prep/f'render-{page}.json'))
    save(PREP/'source-preparation/images.json',images)
    save(PREP/'commands/inspection.json',read(image_prep/'inspection.json'))
    (PREP/'baseline').mkdir(); shutil.copyfile(ROOT/PRODUCTION,PREP/'baseline/statement_cells.py')
    production=common.production();save(PREP/'baseline/production.json',production)
    protected.update({n:h for n,h in read(delivery.PREP/'freeze.json')['bindings'].items() if n!=PRODUCTION})
    names=[PLAN,SELF,prior.SELF,delivery.SELF,'pyproject.toml',*TESTS,rel(PREP/'mapping-preflight.json'),rel(PREP/'baseline/statement_cells.py'),
        rel(PREP/'baseline/production.json'),rel(delivery.HERE/'ordinary.json.gz'),
        rel(prior.HERE/'source-units.json'),rel(prior.HERE/prior.READING),
        rel(prior.HERE/'image-transcript.json'),rel(BASE/'attempt-028/COVERAGE-CORRECTION.md'),
        rel(prior.HERE/'images.json'),rel(prior.HERE/'registry-entry.json'),rel(BASE/'attempt-028/retained-risk-coverage-correction.json')]
    names.extend(rel(p) for d in ('source-preparation','preflight-execution') for p in (PREP/d).rglob('*') if p.is_file())
    protected.update({n:sha(ROOT/n) for n in names})
    protected.update({n:h for n,h in production.items() if n!=PRODUCTION})
    require(all(sha(ROOT/n)==h for n,h in protected.items()),'Stale inherited binding')
    save(PREP/'freeze.json',{'bindings':protected,'baseline_sha256':sha(ROOT/PRODUCTION),
        'mutable_file':PRODUCTION,'implementation_window':'Once after reviewed source and candidate freeze'})
    config=read(prior.PREP/'config.json'); require(sha(config['package_python'])==config['python_sha256'],'Build interpreter changed')
    save(PREP/'config.json',config)
    new=deepcopy(old);new['revision']=408
    task=next(t for t in new['tasks'] if t['id']=='source-bes-dep-05')
    task.update(dossier=PLAN,pre_admission_review=PLAN,build_criteria_scope=[],
        reason='Deliver original policies 2.10–2.14 with offset rights, property exceptions, useful lives and lease actors; preserve complete 044')
    task['inputs']=sorted((set(task['inputs'])-{PRODUCTION})|set(protected)|{rel(PREP/'freeze.json'),rel(PREP/'config.json')})
    bounds={'measured_seconds':1200,'control_seconds':60,'new_bytes':256*1024**2,'failure_reserve':4*1024**2,'worker_seconds':120,'large_file_bytes':32*1024**2,
        'previous_known_bytes':previous['known_cumulative_bytes'],'previous_known_seconds':previous['known_cumulative_seconds'],'unchanged_retries':0}
    task['asset_policies_evidence']={'version':PROFILE,'freeze':rel(PREP/'freeze.json'),'bounds':bounds,
        'success_dependencies':DEPENDENCIES,'original_task_acceptance':False}
    new['budgets']['source-bes-dep-05']['maximum_new_attempts']=45
    routes=read(ROOT/old['continuation_review']['routes']); routes['baseline_revision']=408
    for row in routes['tasks']:
        if row['task']==task['id']:
            row.update(task_sha256=compact_digest(task),dossier=PLAN,phase=0,
                remaining='Successful 044 retained; policies 2.10–2.14 and remaining policy/note/source-authority obligations remain.',
                next_action='Execute 045 policy source/normal/installed delivery; preserve 044 and all failures; reconcile remaining original requirements.',
                stop_condition='Retain 44 admissions and permit attempt 45; 1200+60 seconds and 256 MiB new; no unchanged retry; retain cumulative costs/failures.')
    save(PREP/'routes.json',routes)
    new['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    new['continuation_review']['bindings'].pop(PRODUCTION,None)
    new['continuation_review']['bindings'].update({n:sha(ROOT/n) for n in
        (PLAN,rel(PREP/'routes.json'),rel(PREP/'freeze.json'),rel(PREP/'baseline/statement_cells.py'))})
    require(old['obligations']==new['obligations'] and old['build_contract']==new['build_contract'],'Scope changed')
    raw=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
    source_bytes=sum(p.stat().st_size for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    forecast=costs()['new_bytes']+2*len(raw)+3*source_bytes+100*1024**2
    require(forecast<252*1024**2,'Forecast exceeds reservation')
    with (PREP/'proposal.json').open('xb') as stream:stream.write(raw)
    from legalmath.prospectus.execution_authority import digest as adigest
    save(PREP/'review.json',{'baseline':adigest(old),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Deliver policies 2.10–2.14 with complete 044 retained','Preserve gzip persistence and actual source-worker preflight','Retain 44 admissions and all original obligations'],
        'skeptical_audit':{'verdict':'PASS','plan':PLAN,'forecast_new_bytes':forecast,
            'no_proxy_promotion':'Original date/column geometry,conditional clauses and actual consumers;hashes and arithmetic do not prove legal or financial truth'},
        'evidence_contract':{'question':'Do original offsetting, acquired property, fixed asset, software and lease policies reach the complete answer with conditions and actors intact?',
            'primary':'Independent image transcript, original geometry/quotes, prior preservation and normal/installed corruption refusals',
            'promotion_veto':['Wrong date/amount/unit','Omitted clause','Lost prior answer','Conflicting duplicate','Wrong import','Accepted corruption'],
            'continuation_veto':['Invalid authority','Corrupt shared originals','Spent resources'],
            'not_concluded':['Automatic extraction','Verified valuation','Holder recovery','Current law','Whole build']},
        'budget_revision':{'budget_key':'source-bes-dep-05','previous_maximum':44,'new_maximum':45,
            'retained_attempts':attempts,'reason':'Remaining original accounting-policy requirements; preserve successful 044, original obligations and actual cumulative costs',
            'next_discriminating_check':'Offset AND/OR structure, property-extension exception, useful-life geometry, greater-of recovery and lessee/lessor distinctions',
            'stop_condition':bounds,'same_scope_authorization':'Recover and continue original build'}})
    save(PREP/'commands/preparation.json',{'wall_seconds':time.monotonic()-tick,
        'command':[sys.executable,'-B','-m','scripts.prospectus_h1_asset_policies','prepare']})
    return {'status':'PREPARED','revision':408,'forecast_new_bytes':forecast,'resources':costs()}


def frozen():
    auth = authority(); admission = read(HERE/'admission.json')
    from legalmath.prospectus.execution_authority import digest as adigest
    require(adigest(read(AUTH/'program.json'))==admission['program_sha256'] and
            auth.binding(admission['task_spec'])==admission['binding'], 'Unchanged admission required')
    f = read(PREP/'freeze.json')
    require(all(sha(ROOT/n)==h for n, h in f['bindings'].items()), 'Frozen input changed')
    expected = read(HERE/'candidate-production.json')[PRODUCTION] if (HERE/'candidate-production.json').exists() else f['baseline_sha256']
    require(sha(ROOT/PRODUCTION)==expected, 'Registry outside implementation window')


def command(name,argv,timeout=120):
    require(costs(32*1024**2,timeout)['execution_allowed'],'Reservation exhausted')
    from legalmath.prospectus.execution_authority import process_identity
    target=HERE/'commands';target.mkdir(exist_ok=True);tick=time.monotonic();process=None;error=None
    try:
        with (target/(name+'.log')).open('x') as stream:
            process=subprocess.Popen(argv,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,
                env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1','PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1',
                     'PYTHONPATH':str(ROOT/'src')+os.pathsep+str(ROOT),'PIP_NO_INDEX':'1','PIP_DISABLE_PIP_VERSION_CHECK':'1'})
            save(target/(name+'-started.json'),{'command':argv,'identity':process_identity(process.pid),
                'at':datetime.now(timezone.utc).isoformat(),'timeout_seconds':timeout,'wall_seconds':0,
                'timing_role':'Identity only; completed command receipt supplies measured wall time'})
            process.wait(timeout=timeout)
        require(process.returncode==0,'Inspect '+name+'.log')
    except Exception as exc:
        if process is not None and process.poll() is None:
            process.kill();process.wait()
        error={'type':type(exc).__name__,'reason':str(exc)}
    save(target/(name+'.json'),{'command':argv,'wall_seconds':time.monotonic()-tick,
        'exit_code':None if process is None else process.returncode,'error':error})
    require(error is None,'Command failed: '+str(error))
    require(costs()['execution_allowed'],'Post-command resource limit')


def render_worker():
    require(sha(BASE/'attempt-001/interim.pdf')==PDF,'Wrong original PDF')
    images=read(PREP/'source-preparation/images.json')
    for item in images:require(sha(ROOT/item['path'])==item['sha256'],'Changed original image')
    save(HERE/'images.json',images)
    for name in ('image-transcript.json','SOURCE-REVIEW.md'):
        shutil.copyfile(PREP/'source-preparation'/name,HERE/name)


def original_units():
    return sorted([u for u in read(BASE/'attempt-007/products.json.gz')['P1']['payload']['graph']['units']
        if u['document']==DOCUMENT and u['page'] in PAGES],key=lambda u:(u['page'],u['order'],u['id']))


def combined_units(units):
    old=prior.combined_units(read(prior.HERE/'source-units.json'))
    require(len(old)==6870,'Wrong 043 baseline')
    by_id={u['id']:u for u in old}
    require(not set(by_id).intersection(u['id'] for u in units),'Unexpected source overlap')
    by_id.update({u['id']:u for u in units})
    require(len(by_id)==7005,'Wrong combined occurrences')
    return sorted(by_id.values(),key=lambda u:(u['page'],u['order'],u['id']))


def normal(value):
    return ''.join(value.split())


def asset_policies_reading(units):
    lookup={(u['page'],u['order']):u for u in units}
    def q(p,i):
        u=lookup[p,i];return {'id':u['id'],'quote':u['raw']}
    specs=[
        ('offsetting',82,1,4,'Offset requires an enforceable right AND intention to settle net or realize the asset and settle the liability simultaneously.'),
        ('held-for-sale',82,5,9,'Non-current assets/disposal groups are held for sale when recovery is principally by sale, available immediately and sale highly probable; preserve the disposal-group definition and assets acquired for disposal.'),
        ('held-for-sale-measurement',82,10,13,'Update measurement under applicable IFRS immediately before classification; subsequently lower of carrying amount and fair value less costs to sell, determined annually as reported.'),
        ('property-regulation',82,14,21,'The report attributes restrictions on acquiring non-operational property to RGICSF article 112 of DL 298/92 and an exception for exchange-for-loan property. It reports disposal within two years, extendable by written Bank of Portugal authorization and its conditions under article 114; historical law is not independently verified.'),
        ('acquired-property',82,22,26,'The Group intends immediate disposal. Initially lower of fair value less selling costs and loan carrying amount; subsequently lower of property carrying amount and fair value less selling costs. No depreciation; subsequent write-downs enter income.'),
        ('valuation-methods',83,1,2,'Choose one valuation methodology for the specific situation of the asset.'),
        ('market-method',83,3,5,'Use transaction values for similar comparable property found in the area.'),
        ('income-method',83,6,8,'Capitalize net income discounted to the present using discounted cash flows.'),
        ('cost-method',83,9,11,'Separate the printed components: Urbane Ground/Urbanity, Construction and Indirect Costs.'),
        ('valuation-review',83,12,14,'The report says independent specialized entities perform valuations and internal review compares sale and revalued amounts; this does not verify valuations.'),
        ('property-cost',83,15,21,'Cost less accumulated depreciation and impairment. Preserve the 1 January 2004 IFRS transition deemed-cost election based on prior revalued amounts and the reported price-index adjustment; include directly attributable acquisition expenditure.'),
        ('subsequent-costs',83,22,25,'Capitalize subsequent costs or a separate asset only when future economic benefits probably flow to the Group; otherwise repairs and maintenance are period expenses.'),
        ('depreciation',83,26,27,'Land is not depreciated; other property/equipment uses straight-line depreciation over the nine reported useful lives on the next page.'),
        ('impairment',84,20,22,'On an impairment indication estimate recoverable amount; recognize income-statement loss when net book value exceeds recoverable amount.'),
        ('recoverable-amount',84,23,25,'Recoverable amount is greater of net selling price and value in use; value in use is the present value of future cash flows from continued use and ultimate disposal.'),
        ('software-costs',84,26,29,'Capitalize acquisition/production/development and bringing specific software to use; straight-line amortization over expected life, usually three to six years.'),
        ('software-development',84,30,33,'Directly associated identifiable specific software development with probable benefits beyond one year is intangible, including directly associated employee costs of Group IT-specialist companies.'),
        ('other-it-costs',84,34,34,'All remaining IT-service costs are expensed as incurred.'),
        ('lease-classification',84,35,39,'Historical IAS 17 classification follows substance: finance leases transfer substantially all ownership risks and rewards; all other leases are operating.'),
        ('operating-leases',85,1,3,'Charge operating lease payments to income in the period to which they relate.'),
        ('finance-lessee',85,4,11,'At inception recognize assets and liabilities at leased-asset cost, reported as present value of outstanding instalments. Separate interest expense from principal reducing liabilities; charge a constant periodic rate on the remaining liability.'),
        ('finance-lessor',85,12,19,'Record leased-out assets as loans equal to net investment. Interest enters income and principal reduces loans; interest reflects a constant periodic return on net outstanding investment.')]
    rows=[]
    for label,value in [(2,4),(3,5),(6,7),(8,9),(10,11),(12,13),(14,15),(16,17),(18,19)]:
        token=normal(q(84,value)['quote']);bounds=[int(x) for x in token.split('to')]
        rows.append({'label_source':q(84,label),'value_source':q(84,value),
            'minimum':bounds[0],'maximum':bounds[-1],'unit':'years'})
    return {'version':'bes-asset-policies-reading.v1','policies':['2.10','2.11','2.12','2.13','2.14'],
        'source_groups':[{'page':p,'sources':[q(p,u['order']) for u in units if u['page']==p]} for p in PAGES],
        'clauses':[{'key':key,'sources':[q(p,i) for i in range(a,b+1)],'interpretation':meaning}
            for key,p,a,b,meaning in specs],
        'useful_lives':{'heading_source':q(84,1),'rows':rows},
        'distinctions':{
            'offsetting_requires':'ENFORCEABLE_RIGHT_AND_INTENT_NET_OR_SIMULTANEOUS_SETTLEMENT',
            'held_for_sale_requires':'PRINCIPALLY_SALE_AND_IMMEDIATELY_AVAILABLE_AND_HIGHLY_PROBABLE_SALE',
            'property_disposal_period_years':2,
            'extension_requires':'WRITTEN_BANK_OF_PORTUGAL_AUTHORIZATION_AND_AUTHORITY_CONDITIONS',
            'regulatory_citations':['RGICSF article 112','DL 298/92 of 31 December','article 114'],
            'property_initial_measurement':'LOWER_FAIR_VALUE_LESS_SELLING_COSTS_AND_LOAN_CARRYING_AMOUNT',
            'property_subsequent_measurement':'LOWER_CARRYING_AMOUNT_AND_FAIR_VALUE_LESS_SELLING_COSTS',
            'acquired_property_depreciated':False,'valuation_method_alternatives':['MARKET','INCOME','COST'],
            'deemed_cost_transition_date':'2004-01-01','land_depreciated':False,
            'depreciation_method':'STRAIGHT_LINE','recoverable_amount_operator':'GREATER_OF_NET_SELLING_PRICE_AND_VALUE_IN_USE',
            'software_usual_life_years':[3,6],'software_development_benefits_beyond_one_year_required':True,
            'all_it_costs_capitalized':False,'lease_classification_basis':'SUBSTANCE_AND_SUBSTANTIALLY_ALL_RISKS_AND_REWARDS',
            'lease_standard_reported':'IAS_17','lessee_recognizes_asset_and_liability':True,
            'lessor_recognizes_net_investment_as_loan':True,'principal_equals_interest_income':False,
            'legal_title_proven_by_accounting':False,'current_law_or_standard_verified':False,
            'policy2_15_fully_delivered_here':False},
        'source_scope':{'origin':'SUPPLIED_DEVELOPMENT_READING','policies2_10_to2_14_delivered':True,
            'policy2_15_context_only':True,'historical_report_assertions_only':True,
            'source_authority_or_incorporation_resolved':False}}


def source_check(reading,units,transcript):
    require(len(units)==len({u['id'] for u in units})==135,'Complete four-page source required')
    lookup={u['id']:u for u in units};s=reading['asset_policies_evidence']
    require(all(u['visible'] and u['source_sha256']==PDF and u['page'] in PAGES for u in units),'Changed original source')
    def refs(value):
        result=[]
        if isinstance(value,dict):
            if 'id' in value and 'quote' in value:
                require(value['id'] in lookup and value['quote']==lookup[value['id']]['raw'],'Changed source quote')
                result.append(value['id'])
            for key,v in value.items():
                if key not in ('id','quote'):result+=refs(v)
        elif isinstance(value,list):
            for v in value:result+=refs(v)
        return result
    refs(s);require(set(refs(s['source_groups']))==set(lookup),'Missing full-page context')
    same(s['policies'],['2.10','2.11','2.12','2.13','2.14'],'Wrong policy scope')
    end={82:26,83:27,84:39,85:19}
    expected={u['id'] for u in units if 1<=u['order']<=end[u['page']]}
    substantive=refs(s['clauses'])+refs(s['useful_lives'])
    require(len(substantive)==len(set(substantive)) and set(substantive)==expected,'Missing or duplicated substantive occurrence')
    require(len(s['clauses'])==22,'Wrong clause count')
    clauses={c['key']:c for c in s['clauses']}
    require({x['key'] for x in transcript['anchors']}==set(clauses) and len(transcript['anchors'])==22,'Missing independent anchors')
    for anchor in transcript['anchors']:
        actual=' '.join(x['quote'] for x in clauses[anchor['key']]['sources'])
        require(normal(anchor['quote']) in normal(actual),'Independent passage mismatch: '+anchor['key'])
    table=s['useful_lives'];same(normal(table['heading_source']['quote']),normal(transcript['table_header']),'Wrong year unit')
    require(len(table['rows'])==len(transcript['useful_lives'])==9,'Missing useful life')
    for index,(row,manual) in enumerate(zip(table['rows'],transcript['useful_lives'])):
        same(normal(row['label_source']['quote']),normal(manual[0]),'Wrong useful-life label '+str(index))
        same(normal(row['value_source']['quote']),normal(manual[1]),'Wrong useful-life quote '+str(index))
        same([row['minimum'],row['maximum']],manual[2:],'Wrong useful-life bounds '+str(index))
        require(row['unit']=='years','Wrong useful-life unit')
        label,value=(lookup[row[key]['id']]['bbox'] for key in ('label_source','value_source'))
        require(label[2]<value[0] and abs(label[1]-value[1])<1,'Wrong useful-life row geometry')
        require(lookup[table['heading_source']['id']]['bbox'][3]<value[1],'Wrong table heading geometry')
    for clause in s['clauses']:
        boxes=[lookup[q['id']]['bbox'] for q in clause['sources']]
        require(all(len(b)==4 and b[0]<b[2] and b[1]<b[3] for b in boxes),'Invalid clause geometry')
        require(all(b[1]>=a[1]-3 for a,b in zip(boxes,boxes[1:])),'Wrong clause order')
    same(s['distinctions'],transcript['distinctions'],'Unreviewed interpretation distinctions')
    same(transcript['pages_reviewed'],list(PAGES),'Incomplete image review')
    old=read(prior.HERE/prior.READING)
    same({k:v for k,v in reading.items() if k!='asset_policies_evidence'},old,'Complete 044 reading changed')
    prior.source_check(old,read(prior.HERE/'source-units.json'),read(prior.HERE/'image-transcript.json'))
    return {'local_occurrences':135,'combined_occurrences':len(combined_units(units)),
        'clause_groups':22,'substantive_occurrences':len(expected),'useful_life_rows':9,
        'independent_passages':22,'complete_prior_fields_preserved':True,
        'financial_or_legal_truth_verified':False}


def full_graph_preflight(candidate,reading,graph):
    namespace={'__name__':'legalmath.prospectus.successor._asset_policies_candidate','__package__':'legalmath.prospectus.successor'}
    exec(compile(candidate,'candidate-statement_cells.py','exec'),namespace)
    packet={'version':'source-statement-cells.v1','profile':PROFILE,'document':DOCUMENT,'graph_sha256':digest(graph),
        'review':{'kind':'DEVELOPMENT','reviewer':'Original source mappings','reason':'Actual full-graph preflight'},'reading':reading}
    admitted=namespace['admit'](graph,packet)
    bad=deepcopy(graph);bad['units']=[u for u in bad['units'] if u['id']!='bes-interim-h1-2010:p82:l0']
    negative=deepcopy(packet);negative['graph_sha256']=digest(bad)
    try:namespace['admit'](bad,negative)
    except ValueError as exc:require('original pages or geometry' in str(exc),'Wrong context refusal')
    else:raise ValueError('Missing source context accepted')
    return {'status':'PASS','actual_graph_admitted':True,'context_loss_refused':True,'admitted_sha256':admitted['sha256']}


def source_worker():
    units=original_units();transcript=read(HERE/'image-transcript.json');review=HERE/'SOURCE-REVIEW.md'
    require(review.is_file() and len(review.read_text())>1000,'Substantive source review required')
    require(transcript['method']=='MANUALLY_TYPED_FROM_ORIGINAL_IMAGES','Independent image transcript required')
    for item in read(HERE/'images.json'):require(sha(ROOT/item['path'])==item['sha256'],'Source image changed')
    reading=deepcopy(read(prior.HERE/prior.READING));reading['asset_policies_evidence']=asset_policies_reading(units)
    checked=source_check(reading,units,transcript);all_units=combined_units(units)
    save(HERE/'source-units.json',units);save(HERE/READING,reading)
    entry={'document':DOCUMENT,'source':PDF,'reading':compact_digest(reading),'pages_digest':compact_digest(all_units),
        'pages':sorted({u['page'] for u in all_units}),'occurrences':len(all_units),
        'reading_fields':list(read(prior.HERE/'registry-entry.json')['reading_fields'])+['asset_policies_evidence']}
    original=(PREP/'baseline/statement_cells.py').read_text()
    require(PROFILE not in original and original.count('PROFILES = {')==1,'Baseline registry changed')
    candidate=original.replace('PROFILES = {\n','PROFILES = {\n    '+repr(PROFILE)+': '+repr(entry)+',\n',1)
    graph=read(BASE/'attempt-007/products.json.gz')['P1']['payload']['graph']
    save(HERE/'full-graph-preflight.json',full_graph_preflight(candidate,reading,graph))
    (HERE/'candidate-statement_cells.py').write_text(candidate);save(HERE/'registry-entry.json',entry)
    names=[READING,'source-units.json','registry-entry.json','candidate-statement_cells.py',
        'image-transcript.json','SOURCE-REVIEW.md','images.json','full-graph-preflight.json']
    save(HERE/'candidate-freeze.json',{'bindings':{n:sha(HERE/n) for n in names},'candidate_sha256':digest(candidate.encode())})
    from legalmath.prospectus.successor import statement_cells as cells
    try:cells.admit({'units':all_units},supplied({'units':all_units}))
    except ValueError as exc:require('Unsupported source statement' in str(exc),'Unexpected baseline refusal')
    else:raise ValueError('New profile already supported')
    save(HERE/'source-check.json',{'status':'PASS',**checked,'baseline_gap':'Policies 2.10–2.14 profile unsupported','source_review':common.ref(review)})



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
            'reason':'Complete 044 plus original policies 2.10–2.14; conditions, historical scope and lessee/lessor distinctions remain explicit'},
        'reading':read(HERE/READING)}


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
    changes={
        'offset-or':lambda s:s['distinctions'].update(offsetting_requires='RIGHT_OR_INTENT'),
        'extension-automatic':lambda s:s['distinctions'].update(extension_requires='AUTOMATIC'),
        'disposal-years':lambda s:s['distinctions'].update(property_disposal_period_years=5),
        'recovery-minimum':lambda s:s['distinctions'].update(recoverable_amount_operator='LOWER'),
        'land-depreciation':lambda s:s['distinctions'].update(land_depreciated=True),
        'all-it-capitalized':lambda s:s['distinctions'].update(all_it_costs_capitalized=True),
        'current-ifrs':lambda s:s['distinctions'].update(lease_standard_reported='IFRS_16'),
        'principal-as-income':lambda s:s['distinctions'].update(principal_equals_interest_income=True),
        'life-years':lambda s:s['useful_lives']['rows'][0].update(maximum=500),
        'life-row-lost':lambda s:s['useful_lives']['rows'].pop(),
        'life-unit':lambda s:s['useful_lives']['rows'][0].update(unit='months'),
        'clause-lost':lambda s:s['clauses'].pop(),
        'actor-swapped':lambda s:s['clauses'][-1].update(interpretation='Lessee receives interest income'),
        'authority-resolved':lambda s:s['source_scope'].update(source_authority_or_incorporation_resolved=True)}
    for name,change in changes.items():
        bad=supplied(graph);change(bad['reading']['asset_policies_evidence'])
        try:cells.admit(graph,bad)
        except ValueError as exc:
            require('reading differs' in str(exc),'Unexpected reading refusal')
            rows.append({'case':name,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else:raise ValueError('Altered reading accepted: '+name)
    for name in ('missing-page','context-occurrence-lost','source-hash','geometry','duplicate-occurrence'):
        g=deepcopy(graph)
        if name=='missing-page':g['units']=[u for u in g['units'] if u['page']!=85]
        elif name=='context-occurrence-lost':g['units']=[u for u in g['units'] if u['id']!='bes-interim-h1-2010:p82:l0']
        elif name=='source-hash':next(u for u in g['units'] if u['page']==84)['source_sha256']='0'*64
        elif name=='geometry':next(u for u in g['units'] if u['id']=='bes-interim-h1-2010:p84:l4')['bbox'][1]+=4
        else:g['units'].append(deepcopy(next(u for u in g['units'] if u['page']==84)))
        bad=supplied(g)
        try:cells.admit(g,bad)
        except ValueError as exc:rows.append({'case':name,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else:raise ValueError('Altered source accepted: '+name)
    return rows

def object_parts(encoded_values):
    """Yield exactly common.encoded's bytes, retaining nested chunk sequences."""
    yield b'{'
    for index,key in enumerate(sorted(encoded_values)):
        if index:yield b', '
        yield common.encoded(key);yield b': '
        value=encoded_values[key]
        if isinstance(value,bytes):yield value
        else:yield from value
    yield b'}'

def parts_digest(parts):
    hasher=hashlib.sha256()
    for part in parts:hasher.update(part)
    return hasher.hexdigest()

def equivalence():
    cases=[{}, {'z':[1,-2,3.25,None,False],'á':'Espírito\nSanto','a':{'é':'\u0000"\\','x':[]}},
           {'source_statement_cells':{'nested':[{'b':2,'a':1}]},'artifacts':{'k':'value'}},
           {'0':-0.0,'max':12345678901234567890}]
    for value in cases:
        encoded={k:common.encoded(v) for k,v in value.items()}
        chunks=tuple(object_parts(encoded))
        require(b''.join(chunks)==common.encoded(value),'Changed JSON representation')
        require(parts_digest(chunks)==digest(value),'Changed dictionary digest')
        nested={'outer':chunks,'unicode':common.encoded('Ó €')}
        whole={'outer':value,'unicode':'Ó €'}
        require(b''.join(object_parts(nested))==common.encoded(whole),'Changed nested representation')
        require(parts_digest(object_parts(nested))==digest(whole),'Changed nested digest')
    return {'status':'PASS','cases':len(cases),'nested_cases':len(cases),'byte_identity':True}

def progress(label):
    print(json.dumps({'at':datetime.now(timezone.utc).isoformat(),'progress':label}),flush=True)

def large_save(path,value):
    require(path.name in {'baseline-answer.json.gz','ordinary-answer.json.gz','installed-answer.json.gz'},'Unreviewed large output')
    require(not path.exists(),'Output already exists')
    raw=gzip.compress(common.encoded(value),compresslevel=1,mtime=0)
    require(len(raw)<32*1024**2,'Large output cap exceeded')
    with path.open('xb') as stream:stream.write(raw)
    return {'path':rel(path),'sha256':sha(path),'bytes':len(raw)}

def imports(kind):
    location=HERE/'installed' if kind.startswith('installed') else ROOT/'src'
    modules={n:m.__file__ for n,m in sys.modules.items() if n.startswith('legalmath') and getattr(m,'__file__',None)}
    require(modules and all(Path(p).resolve().is_relative_to(location) for p in modules.values()),'Wrong import origin')
    return modules

def checked_answer(kind):
    path=HERE/(kind+'-answer.json.gz');receipt=read(HERE/(kind+'.json'))
    require(sha(path)==receipt['answer_file']['sha256'],'Changed saved answer')
    value=read(path);require(digest(value)==receipt['answer_sha256'],'Changed decoded answer')
    return value

def answer_worker(kind):
    from legalmath.prospectus.successor import service
    tick=time.monotonic();progress(kind+':load-original')
    original=read(BASE/'attempt-007/products.json.gz')
    progress(kind+':build-products')
    products=prior.build_products(original) if kind=='baseline' else build_products(original)
    del original
    phase_hashes={}
    for phase,product in products.items():
        payload=deepcopy(product['payload'])
        if phase=='P1':
            payload['request'].pop('source_statement_cells');phase_hashes['graph']=digest(payload['graph'])
        elif phase=='P2':payload.pop('source_statement_cells')
        elif phase=='P3':payload.pop('source_statement_cells_sha256')
        phase_hashes[phase]=digest(payload)
    progress(kind+':consume')
    answer=service.consume(products,ROOT,include_artifacts=True)
    del products
    progress(kind+':save')
    answer_hash=digest(answer)
    if kind=='baseline':require(answer_hash==read(delivery.HERE/'ordinary.json.gz')['answer_sha256'],'Complete044baseline changed')
    artifact=large_save(HERE/(kind+'-answer.json.gz'),answer)
    save(HERE/(kind+'.json'),{'status':'PASS','answer_sha256':answer_hash,'answer_file':artifact,
        'phase_hashes_without_statement':phase_hashes,'imports':imports(kind),
        'worker_seconds':time.monotonic()-tick,'actual_service_consumer':True})
    progress(kind+':complete')

def comparison_worker(kind):
    after_kind='installed' if kind.startswith('installed') else 'ordinary'
    before=checked_answer('baseline');after=checked_answer(after_kind)
    same(read(HERE/'baseline.json')['phase_hashes_without_statement'],
         read(HERE/(after_kind+'.json'))['phase_hashes_without_statement'],'Unrelated phase payload changed')
    replacements={k:after[k] for k in ('request_sha256','consumed_products','report_sha256')}
    same({**before,**replacements,'source_statement_cells':after['source_statement_cells']},after,'Unrelated answer changed')
    same(before['questions'],after['questions'],'Original questions changed')
    require(after['questions']['Q3']['status']=='PARTIAL' and not after['may_execute_transaction'] and
        not after['independent_legal_acceptance'],'Original limits changed')
    for key in read(prior.HERE/prior.READING):
        same(before['source_statement_cells'][key],after['source_statement_cells'][key],'Lost044field '+key)
    reading=read(HERE/READING);body=after['source_statement_cells']
    for key in reading:same(body[key],reading[key],'Incomplete reading '+key)
    require(body['consumed'] and not body['independent_financial_acceptance'] and body['legal_dependency_resolution']=='UNCHANGED','Scope overclaim')
    if after_kind=='installed':same(after,checked_answer('ordinary'),'Installed answer differs')
    save(HERE/(kind+'.json.gz'),{'status':'PASS','prior_complete_answer_sha256':digest(before),
        'answer_sha256':digest(after),'reading_sha256':compact_digest(reading),
        'replacements':replacements,'addition':body,'whole_task_complete':False})

def composition_worker(kind):
    after_kind='installed' if kind.startswith('installed') else 'ordinary'
    comparison=read(HERE/('installed-compare.json.gz' if after_kind=='installed' else 'compare.json.gz'))
    before=checked_answer('baseline')
    encoded={k:common.encoded(v) for k,v in before.items()};del before
    def answer_parts(receipt):
        changed={**encoded,**{k:common.encoded(v) for k,v in receipt['replacements'].items()},
                 'source_statement_cells':common.encoded(receipt['addition'])}
        return tuple(object_parts(changed))
    supplement=read(BASE/'attempt-016/answer-supplement.json.gz')
    composed={k:common.encoded(v) for k,v in supplement.items()};del supplement
    c17=read(BASE/'attempt-017/composition.json')
    require(parts_digest(object_parts(composed))==c17['previous_content_sha256'],'Original016changed')
    composed.update({k:common.encoded(v) for k,v in read(BASE/'attempt-017/answer-delta.json.gz').items()})
    require(parts_digest(object_parts(composed))==c17['complete_composed_sha256'],'Original017changed')
    rows=[]
    for n,key in KEYS.items():
        receipt=read(BASE/f'attempt-{n:03d}/ordinary.json.gz');parts=answer_parts(receipt)
        require(parts_digest(parts)==receipt['answer_sha256'],'Prior answer differs: '+str(n))
        composed[key]=parts;value=parts_digest(object_parts(composed))
        require(value==receipt['full_composed_sha256'],'Prior composition differs: '+str(n))
        rows.append({'attempt':n,'answer_and_complete_composition_matched':True})
        progress(kind+':preserved-'+str(n))
    previous=read(delivery.HERE/'ordinary.json.gz')
    require(parts_digest(object_parts(composed))==previous['full_composed_sha256'],'Prior full composition changed')
    parts=answer_parts(comparison);require(parts_digest(parts)==comparison['answer_sha256'],'Candidate answer differs')
    composed['h1_asset_policies_consumer']=parts
    receipt={'status':'PASS','prior_full_composed_sha256':previous['full_composed_sha256'],
        'full_composed_sha256':parts_digest(object_parts(composed)),'preserved':rows,
        'exact_sorted_json_encoding':True}
    if after_kind=='installed':same(receipt,read(HERE/'composition.json'),'Installed composition differs')
    save(HERE/(kind+'.json'),receipt)


def consumer_controls(output='controls.json'):
    from legalmath.prospectus.successor import service
    original=read(BASE/'attempt-007/products.json.gz'); current=build_products(original); rows=[]
    for change in ('missing_p2','changed_p2','missing_p3','changed_p3','unsupplied'):
        bad=deepcopy(current); request=bad['P1']['payload']['request']; p2,p3=bad['P2']['payload'],bad['P3']['payload']
        if change=='missing_p2': del p2['source_statement_cells']
        elif change=='changed_p2': p2['source_statement_cells']['reading']['asset_policies_evidence']['distinctions']['current_law_or_standard_verified']=True
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


def controls_worker(kind):
    progress(kind+':consumer-negatives')
    consumer_controls(kind+'.json')
    if kind=='installed-controls':same(read(HERE/(kind+'.json')),read(HERE/'controls.json'),'Installed corruption refusals differ')
    progress(kind+':registry-negatives')
    cases=registry_controls()
    if kind=='installed-controls':same(cases,read(HERE/'controls-registry.json')['cases'],'Installed registry refusals differ')
    save(HERE/(kind+'-registry.json'),{'status':'PASS','cases':cases,'imports':imports(kind)})


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
    rows=deepcopy(read(delivery.HERE/'requirements.json')['rows'])
    for row in rows:
        if row.get('status','').startswith('THIS_ATTEMPT_MUST_PASS'):
            row.update(status='RETAINED_COMPLETE_FINITE_INTEGRATION',evidence=common.ref(delivery.HERE/'result.json'))
    rows.append({'requirement':'Original policies 2.10–2.14 conditions, useful lives and lease actors with complete 044 retained',
                 'status':'THIS_ATTEMPT_MUST_PASS; see actual stage results'})
    inventory=deepcopy(read(delivery.HERE/'note-inventory.json'))
    for row in inventory['notes']:
        if row['note']==27:row['status']='RETAINED_FINITE_INTEGRATION'
    for policy in ('2.10','2.11','2.12','2.13','2.14'):
        inventory['policies'][policy]='THIS_ATTEMPT_SUBJECT_TO_STAGE_RESULTS'
    save(HERE/'note-inventory.json',inventory)
    save(HERE/'requirements.json',{'rows':rows,'original_task_acceptance':False,
        'external_adviser_opinion_required':False,
        'next_discriminating_work':'Reconcile remaining accounting policies and uncovered notes with the actual retained full-page/source reading coverage; source authority, controlling edition and incorporation remain.'})

def stage(name):
    require(name in DEPENDENCIES and not (HERE/'stages'/name).exists(),'Stage already started or unknown')
    for parent in DEPENDENCIES[name]: require(read(HERE/'stages'/parent/'result.json')['status']=='PASS','Failed predecessor '+parent)
    frozen(); require(costs(46*1024**2 if name=='package' else 32*1024**2)['execution_allowed'],'Stage reservation exhausted')
    from legalmath.prospectus.execution_authority import process_identity
    save(HERE/'stages'/name/'started.json',{'identity':process_identity(os.getpid()),'at':datetime.now(timezone.utc).isoformat(),'stage':name})
    error=None
    try:
        if name=='render': render_worker()
        elif name=='package': package_worker()
        elif name=='tests': command('tests',[str(ROOT/'.venv/bin/python'),'-B','-m','pytest','-q',*TESTS,'--junitxml='+str(HERE/'tests.xml')],120)
        else:
            python=read(PREP/'config.json')['package_python'] if name.startswith('installed') else str(ROOT/'.venv/bin/python')
            command(name,[python,'-I','-B',str(ROOT/SELF),'worker-'+name],120)
        frozen()
    except Exception as exc: error={'type':type(exc).__name__,'reason':str(exc)}
    save(HERE/'stages'/name/'result.json',{'status':'FAIL' if error else 'PASS','error':error})
    return {'stage':name,'status':'FAIL' if error else 'PASS','error':error,'resources':costs()}


def finalize():
    require(not (HERE/'outputs.json').exists(),'Already sealed')
    for started in (HERE/'stages').glob('*/started.json'):
        require((started.parent/'result.json').exists(),'Unresolved started stage; recover recorded processes first')
    outcomes={n:read(HERE/'stages'/n/'result.json')['status'] if (HERE/'stages'/n/'result.json').exists() else 'BLOCKED' for n in DEPENDENCIES}
    passed=all(v=='PASS' for v in outcomes.values())
    if passed:
        receipt=read(HERE/'compare.json.gz');receipt.update(read(HERE/'composition.json'))
        receipt.update(reading=common.ref(HERE/READING),controls=read(HERE/'controls-registry.json')['cases'],
            source_check=read(HERE/'source-check.json'),imports=read(HERE/'ordinary.json')['imports'],
            source_truth_established=False,recipe='Reconstruct044from007;preserve016/017andallsuccessful021–044compositions;add045as h1_asset_policies_consumer')
        save(HERE/'ordinary.json.gz',receipt)
        installed=deepcopy(receipt);installed['imports']=read(HERE/'installed.json')['imports']
        save(HERE/'installed.json.gz',installed)
    save(HERE/'result.json',{'task':'source-bes-dep-05','status':'PASS' if passed else 'FAIL','stages':outcomes,
        'task_complete':False,'whole_program_complete':False,'build_criteria_claimed':[],'resources':costs()})
    (HERE/'RESULT.md').write_text('# Original offsetting, property, software and lease policies\n\n'+('Finite source/consumer integration passed. ' if passed else 'Campaign did not pass. ')
        +'Actual stages: '+json.dumps(outcomes)+'.\n\n'
        +'Policies 2.10–2.14 retain original conditions, property-disposal exceptions, useful lives, software costs and lessee/lessor accounting. '
        +'Historical regulatory and accounting statements remain attributed to the report; no current rule or legal title is inferred. '
        +('The full 044 answer and all original compositions including supplied OCR risk tables are preserved. ' if passed else
          'Complete 044 and historical composition preservation is required; consult actual stage failures before claiming delivery. ')
        +'Historical report claims do not establish current standards,rights,valuation or whole-source acceptance.\n\n'
        +'|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|\n|---|---|---|---|---|---|\n'
        +'|'+('Retain finite integration' if passed else 'Retain actual failure')+'|Original images/quotes/geometry and actual full normal/installed answers|See stage records|Remaining notes and authority|Record/refresh;reconcile remaining source obligations with actual current coverage|Financial truth,current law,holder entitlement,automatic extraction,whole build|\n\n'
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
        kind=action.removeprefix('worker-')
        sys.path.insert(0,str(HERE/'installed') if kind.startswith('installed') else str(ROOT/'src'))
        def forbidden(*args,**kwargs):raise RuntimeError('No native/network child in source/consumer worker')
        subprocess.Popen=forbidden
        if kind in ('baseline','ordinary','installed'):answer_worker(kind)
        elif kind in ('compare','installed-compare'):comparison_worker(kind)
        elif kind in ('composition','installed-composition'):composition_worker(kind)
        elif kind in ('controls','installed-controls'):controls_worker(kind)
        else:{'source':source_worker,'implement':implement_worker,'coverage':coverage_worker}[kind]()
        result={'status':'PASS','worker':kind}
    elif action=='prepare':result=prepare()
    elif action=='finalize':result=finalize()
    elif action=='equivalence':result=equivalence()
    else:result=stage(action)
    print(json.dumps(result))
