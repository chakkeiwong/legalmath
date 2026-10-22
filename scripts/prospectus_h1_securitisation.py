"""Bounded original consolidation policy and securitisation answer delivery."""
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
from scripts import prospectus_h1_cross_note as prior
from scripts import prospectus_h1_statement_consumer as common

read, save, sha, digest = prior.read, prior.save, prior.sha, prior.digest
compact_digest, same, require, rel = prior.compact_digest, prior.same, prior.require, prior.rel
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
BASE = AUTH / 'attempts/source-bes-dep-05'
PREP = AUTH / 'reviews/h1-securitisation-388'
HERE = BASE / 'attempt-025'
SELF = 'scripts/prospectus_h1_securitisation.py'
PLAN = 'docs/plans/prospectus-h1-securitisation-2026-10-21.md'
PRODUCTION = prior.PRODUCTION
PROFILE = 'bes-h1-2010-statements-securitisation.v5'
DOCUMENT, PDF = prior.DOCUMENT, prior.PDF
PAGES = (68, 69, 70, 71, 72, 158, 159)
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
    paths.add(AUTH/'revisions/0388.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH/'program.json').stat().st_size-start['program_bytes'])
    seconds = sum(read(p)['wall_seconds'] for d in (PREP, HERE) for p in d.glob('commands/*.json'))
    return {'new_bytes': size, 'new_measured_seconds': seconds, 'new_control_seconds': 60,
        'prior_known_bytes': start['prior_known_bytes'], 'prior_known_seconds': start['prior_known_seconds'],
        'known_cumulative_bytes': start['prior_known_bytes']+size,
        'known_cumulative_seconds': start['prior_known_seconds']+seconds+60,
        'earlier_manual_and_unmeasured_costs': 'UNKNOWN; history retained',
        'execution_allowed': size+reserve < 118*1024**2 and seconds < 660}


def prepare():
    tick = time.monotonic(); auth = authority(); old = read(AUTH/'program.json')
    require(old['revision'] == 387 and not PREP.exists() and not HERE.exists(), 'Fresh387 required')
    events = auth.events()
    attempts = [e['attempt'] for e in events if e['kind']=='ADMIT' and e['budget_key']=='source-bes-dep-05']
    require(len(attempts)==old['budgets']['source-bes-dep-05']['maximum_new_attempts']==24, 'Retain24attempts')
    require(read(prior.HERE/'result.json')['status']=='PASS', '024 must pass')
    protected = {}
    for n in (7, 15, 16, 17, 21, 22, 23, 24):
        folder = BASE/f'attempt-{n:03d}'; manifest = folder/'outputs.json'
        records = [e for e in events if e.get('attempt')==rel(folder) and 'outputs_sha256' in e]
        require(records and sha(manifest)==records[-1]['outputs_sha256'], 'Unauthenticated original')
        protected[rel(manifest)] = sha(manifest)
        for name, h in read(manifest).items():
            require(sha(folder/name)==h, 'Changed original '+name)
    previous = prior.costs()
    save(PREP/'accounting-start.json', {'prior_known_bytes': previous['known_cumulative_bytes'],
        'prior_known_seconds': previous['known_cumulative_seconds'], 'prior_cost_receipt': previous,
        'history_names': [p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes': (AUTH/'program.json').stat().st_size})
    (PREP/'baseline').mkdir()
    shutil.copyfile(ROOT/PRODUCTION, PREP/'baseline/statement_cells.py')
    production = common.production()
    save(PREP/'baseline/production.json', production)
    names = [PLAN, SELF, prior.SELF, prior.prior.SELF, prior.prior.prior.SELF, common.SELF, 'pyproject.toml', *TESTS,
        rel(BASE/'attempt-001/interim.pdf'), rel(BASE/'attempt-007/products.json.gz'),
        rel(BASE/'attempt-007/scope-consumer.json.gz'), rel(BASE/'attempt-015/source-units.json'),
        rel(BASE/'attempt-015/profile.json'), rel(common.TRANSCRIPT),
        rel(common.PREP/'reading.json'), rel(BASE/'attempt-016/answer-supplement.json.gz'),
        rel(BASE/'attempt-017/composition.json'), rel(BASE/'attempt-017/answer-delta.json.gz'),
        rel(BASE/'attempt-021/ordinary.json.gz'), rel(BASE/'attempt-022/ordinary.json.gz'),
        rel(BASE/'attempt-022/reading.json'), rel(BASE/'attempt-022/source-units.json'),
        rel(BASE/'attempt-022/image-transcript.json'),
        rel(BASE/'attempt-023/ordinary.json.gz'), rel(BASE/'attempt-023/reading.json'),
        rel(BASE/'attempt-023/source-units.json'), rel(BASE/'attempt-023/image-transcript.json'),
        rel(prior.HERE/'ordinary.json.gz'),
        rel(prior.HERE/'reading.json'), rel(prior.HERE/'source-units.json'),
        rel(prior.HERE/'image-transcript.json'), rel(PREP/'baseline/statement_cells.py'),
        rel(PREP/'baseline/production.json')]
    products = read(BASE/'attempt-007/products.json.gz')
    names += [d['path'] for d in products['P1']['payload']['request']['bundle']['documents']]
    protected.update({n: sha(ROOT/n) for n in names})
    protected.update({n: h for n, h in production.items() if n != PRODUCTION})
    save(PREP/'freeze.json', {'bindings': protected, 'baseline_sha256': sha(ROOT/PRODUCTION),
        'mutable_file': PRODUCTION, 'implementation_window': 'Once after reviewed source and candidate freeze'})
    config = read(prior.PREP/'config.json')
    require(sha(config['package_python'])==config['python_sha256'], 'Build interpreter changed')
    save(PREP/'config.json', config)
    new = deepcopy(old); new['revision'] = 388
    task = next(t for t in new['tasks'] if t['id']=='source-bes-dep-05')
    task.update(dossier=PLAN, pre_admission_review=PLAN, build_criteria_scope=[],
        reason='Deliver original policy2.2/Note42 with control,derecognition and consolidation impact kept distinct; preserve024and original limits')
    task['inputs'] = sorted((set(task['inputs'])-{PRODUCTION}) | set(protected) |
                           {rel(PREP/'freeze.json'), rel(PREP/'config.json')})
    bounds = {'measured_seconds': 660, 'control_seconds': 60, 'new_bytes': 120*1024**2,
        'failure_reserve': 2*1024**2, 'previous_known_bytes': previous['known_cumulative_bytes'],
        'previous_known_seconds': previous['known_cumulative_seconds'], 'unchanged_retries': 0}
    task['securitisation_evidence'] = {'version': PROFILE, 'freeze': rel(PREP/'freeze.json'), 'bounds': bounds,
        'success_dependencies': DEPENDENCIES, 'original_task_acceptance': False}
    new['budgets']['source-bes-dep-05']['maximum_new_attempts'] = 25
    routes = read(ROOT/old['continuation_review']['routes']); routes['baseline_revision'] = 388
    for row in routes['tasks']:
        if row['task']==task['id']:
            row.update(task_sha256=compact_digest(task), dossier=PLAN, phase=0,
                remaining='024cross-note integration complete; policy2.2/Note42and wider source coverage/authority remain.',
                next_action='Execute025policy2.2/Note42source review,normal/installed delivery and adverse controls; update original coverage,record,refresh and continue.',
                stop_condition='25retained admissions;660+60seconds and120MiB new; no unchanged retry; retain all costs/failures.')
    save(PREP/'routes.json', routes)
    new['continuation_review'].update(plan=PLAN, routes=rel(PREP/'routes.json'))
    new['continuation_review']['bindings'].pop(PRODUCTION, None)
    new['continuation_review']['bindings'].update({n: sha(ROOT/n) for n in
        (PLAN, rel(PREP/'routes.json'), rel(PREP/'freeze.json'), rel(PREP/'baseline/statement_cells.py'))})
    require(old['obligations']==new['obligations'] and old['build_contract']==new['build_contract'], 'Scope changed')
    raw = (json.dumps(new, ensure_ascii=False, indent=2)+'\n').encode()
    source_bytes = sum(p.stat().st_size for p in (ROOT/'src/legalmath').rglob('*')
                       if p.is_file() and '__pycache__' not in p.parts)
    forecast = costs()['new_bytes']+2*len(raw)+3*source_bytes+24*1024**2
    require(forecast < 118*1024**2, 'Forecast exceeds reservation')
    with (PREP/'proposal.json').open('xb') as stream: stream.write(raw)
    from legalmath.prospectus.execution_authority import digest as adigest
    save(PREP/'review.json', {'baseline': adigest(old), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Complete policy2.2/Note42source-to-answer dependencies; preserve all024content',
                    'Keep control,presumptions,consolidation and asset derecognition distinct',
                    'Retain24admissions and all original requirements'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN, 'forecast_new_bytes': forecast,
            'no_proxy_promotion': 'Source image/geometry and full downstream evidence; identity and arithmetic do not prove rights or financial truth'},
        'evidence_contract': {'question': 'Do policy2.2/Note42reach the answer without unsupported control,ownership or derecognition conclusions?',
            'primary': 'Original image transcript/quotes/geometry,full024preservation and actual normal/installed corruption refusals',
            'promotion_veto': ['Omitted source/footnote','Wrong marker/unit/period/issuer','Unsupported right','Wrong import','Accepted corruption'],
            'continuation_veto': ['Invalid authority','Corrupt shared evidence','Spent resources'],
            'not_concluded': ['Automatic extraction','Financial truth','Actual instrument entitlement','Current law','Whole source/build']},
        'budget_revision': {'budget_key': 'source-bes-dep-05', 'previous_maximum': 24, 'new_maximum': 25,
            'retained_attempts': attempts, 'reason': 'New original policy2.2/Note42dependencies, not replay of024',
            'next_discriminating_check': 'Complete original consolidation policy and ten transactions with source-specific downstream controls',
            'stop_condition': bounds, 'same_scope_authorization': 'Recover and continue original build'}})
    save(PREP/'commands/preparation.json', {'wall_seconds': time.monotonic()-tick,
        'command': [sys.executable, '-B', '-m', 'scripts.prospectus_h1_securitisation', 'prepare']})
    return {'status': 'PREPARED', 'revision': 388, 'forecast_new_bytes': forecast, 'resources': costs()}


def frozen():
    auth = authority(); admission = read(HERE/'admission.json')
    from legalmath.prospectus.execution_authority import digest as adigest
    require(adigest(read(AUTH/'program.json'))==admission['program_sha256'] and
            auth.binding(admission['task_spec'])==admission['binding'], 'Unchanged admission required')
    f = read(PREP/'freeze.json')
    require(all(sha(ROOT/n)==h for n, h in f['bindings'].items()), 'Frozen input changed')
    expected = read(HERE/'candidate-production.json')[PRODUCTION] if (HERE/'candidate-production.json').exists() else f['baseline_sha256']
    require(sha(ROOT/PRODUCTION)==expected, 'Registry outside implementation window')


def command(name, argv, timeout=180):
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
    require(sha(BASE/'attempt-001/interim.pdf')==PDF, 'Wrong original PDF')
    (HERE/'images').mkdir()
    for page in PAGES:
        command('render-'+str(page), ['pdftoppm','-f',str(page),'-l',str(page),'-r','160','-singlefile','-png',
            str(BASE/'attempt-001/interim.pdf'),str(HERE/'images'/f'page-{page}')], 60)
    save(HERE/'images.json', [{'page': p, 'path': rel(HERE/'images'/f'page-{p}.png'),
        'sha256': sha(HERE/'images'/f'page-{p}.png')} for p in PAGES])


def original_units():
    products = read(BASE/'attempt-007/products.json.gz')
    return sorted([u for u in products['P1']['payload']['graph']['units']
        if u['document']==DOCUMENT and u['page'] in PAGES], key=lambda u: (u['page'],u['order'],u['id']))


def securitisation_reading(units, transcript):
    lookup={(u['page'],u['order']):u for u in units}
    def q(page,line):
        u=lookup[page,line];return {'id':u['id'],'quote':u['raw']}
    def qs(page,first,last):return [q(page,i) for i in range(first,last+1)]
    def number(page,line):
        quote=q(page,line);token=''.join(quote['quote'].split())
        value=None if token=='-' else int('-'+token[1:-1] if token.startswith('(') else token)
        return {**quote,'value':value,'status':'DASH_UNKNOWN' if value is None else 'SOURCE_NUMBER','unit':'EUR thousands'}
    policy={
        'scope':{'sources':qs(68,14,18),'entities':'BES and subsidiaries; results attributable to the Group from associates',
            'policies_consistent_claim':'Report states consistent application across Group companies and covered periods'},
        'subsidiaries':{'sources':qs(68,19,25),'control':'More than half of voting rights creates a presumption; power to govern financial and operating policies to obtain benefits can establish control at50percent or less',
            'voting_threshold_necessary':False,'consolidation_period':'Fully consolidated from transfer of control until control ceases'},
        'noncontrolling_losses':{'sources':qs(68,26,30)+qs(69,1,2),
            'through_2009':'Losses exceeding noncontrolling equity attributed to Group and charged to income; later profits recognised by Group until previously attributed losses recovered',
            'from_2010':'Losses attributed proportionally to parent owners and noncontrolling interest even with a noncontrolling deficit'},
        'control_changes':{'sources':qs(69,3,8),'date':'After1January2010',
            'step_acquisition':'Previously held interest remeasured at acquisition-date fair value; gain/loss in income when determining goodwill',
            'loss_of_control':'Any retained interest remeasured at date control is lost; gain/loss in income'},
        'associates':{'sources':qs(69,9,22),'influence':'Significant influence without control; more than20percent voting rights creates a presumption, but policy participation/board representation can establish influence below20percent',
            'threshold_necessary':False,'method':'Equity method while significant influence exists',
            'step_acquisition_from_2010':'Previously held stake remeasured at fair value through income when equity method first applies',
            'loss_limit':'Discontinue when share of losses equals or exceeds interest including long-term interest',
            'loss_limit_exceptions':['Legal or constructive obligation to cover losses','Payments on behalf of associate']},
        'special_purpose_entities':{'sources':qs(69,23,31)+qs(70,1,9),
            'control_basis':'Substance of relationship, independent of equity percentage; report cites SIC12',
            'criteria':[
                {'sources':qs(69,29,31),'meaning':'Activities conducted to meet specific Group needs and confer benefits'},
                {'sources':qs(70,1,3),'meaning':'Decision-making power to obtain majority of benefits'},
                {'sources':qs(70,4,6),'meaning':'Rights to majority of benefits and possible exposure to inherent risks'},
                {'sources':qs(70,7,9),'meaning':'Retains majority of residual or ownership risks to obtain benefits'}],
            'criteria_legal_verification':False},
        'managed_funds':{'sources':qs(70,10,15),'default':'Funds managed for participation-unit holders not consolidated',
            'exception':'Consolidate where activity is controlled under cited SIC12criteria',
            'presumption':'More than50percent of participation units','threshold_necessary':False},
        'goodwill':{'sources':qs(70,16,35)+qs(71,1,5),
            'through_2004_transition':'Combinations until1January2004 offset against reserves under reported IFRS1option',
            '2004_to_2009':'Purchase method; acquisition-date fair value of assets/equity instruments given and liabilities incurred/assumed plus directly attributable costs, less Group share of identifiable net assets/liabilities/contingent liabilities',
            'from_2010':'Fair value of consideration including previously held interest less recognised identifiable assets and liabilities; transaction costs expensed',
            'noncontrolling_measurement':'Proportionate share of identifiable net assets, excluding goodwill; reported goodwill belongs only to Bank equity holders',
            'subsequent':'Asset at cost, not amortised; associate goodwill included in investment carrying amount',
            'negative_goodwill':'Income in period of combination','impairment':'Annual recoverable-amount review regardless of indicators; losses directly in income'},
        'noncontrolling_transactions':{'sources':qs(71,6,15),'date':'From1January2010',
            'acquisition':'Equity-holder transaction, no goodwill; consideration versus acquired carrying amount goes to equity',
            'sale_or_dilution':'When control is retained, equity transaction and no income gain/loss; proceeds versus carrying amount goes to equity',
            'loss_of_control_rule_applied_to_all_sales':False},
        'foreign_currency_translation':{'sources':qs(71,16,35),
            'functional_currency':'Primary economic environment of each entity; consolidated presentation and BES functional currency euro',
            'balance_sheet':'Report describes balance-sheet-date rates for assets/liabilities',
            'income_expenses':'Rates approximating transaction-date rates',
            'reserves':'Opening-equity exchange differences go to reserves net of deferred tax; income/expense translation differences to reserves',
            'disposal':'Exchange differences recognised in income as part of gain/loss on sale',
            'wording_caution':'Source introduces translation into euro but bullet wording says into the functional currency; exact text retained without silently correcting it'},
        'eliminations':{'sources':qs(72,1,8),
            'group':'Intercompany balances/transactions including unrealised gains/losses eliminated, except losses evidencing impairment that should be recognised',
            'associates':'Unrealised gains eliminated to extent of Group interest; losses eliminated unless evidence of impairment'},
        'status':'HISTORICAL_REPORTED_ACCOUNTING_POLICY; standards/current law not independently verified'}
    specs=[(9,10,11,12,13),(14,15,16,17,18),(19,20,21,22,23),(24,25,26,27,28),(29,30,31,32,33),
           (39,34,35,36,37),(40,41,42,43,38),(44,45,46,47,56),(48,49,50,51,57),(55,52,53,54,58)]
    rows=[{'designation':q(158,d),'initial_date':q(158,date),'original_amount':number(158,amount),
           'current_amount':number(158,current),'asset_type':q(158,asset)} for d,date,amount,current,asset in specs]
    treatment={
        'transition':{'sources':qs(158,59,61),'cutoff':'2004-01-01',
            'rule':'Source applies IAS39derecognition requirements to transactions after cutoff; assets previously derecognised not restated under reported IFRS1permission'},
        'mortgages3_4_5':{'sources':qs(158,62,64),'reported_derecognised':True,
            'reason':'Report states substantially all risks and rewards transferred','legal_true_sale_established':False},
        'named_consolidated':{'sources':qs(158,65,70),'vehicles':['Lusitano SME No.1','Lusitano Mortgages No.6','Lusitano Mortgages No.7','Lusitano Project Finance No.1'],
            'reason':'Report states majority of activity risks and rewards retained','effect':'Respective assets and liabilities included in consolidated balance sheet',
            'other_vehicle_wording':'Other vehicles not included because majority risks/rewards not retained; preserve alongside the separately described new transaction'},
        'leverage_finance1':{'sources':qs(158,71,74),'date':'February2010',
            'loan_origins':'BES London Branch,BESI and ES Venetie; preserve exact source spelling in quotes',
            'reported_loans_not_derecognised':True,'reason':'Report says substantially all risks and rewards not transferred',
            'vehicle_consolidated_inferred_from_non_derecognition':False},
        'consolidation_equals_derecognition':False,'actual_legal_ownership_established':False}
    impact={'scope_sources':qs(158,75,76),'headers':qs(159,1,3),'dates':['2010-06-30','2009-12-31'],
        'rows':[{'label':q(159,n),'cells':[number(159,n+1),number(159,n+2)]} for n in (4,7,10,13)],
        'complete_balance_sheet':False,'net_income_annual_period_inferred':False,'asset_liability_equality_required':False}
    old=read(prior.HERE/'reading.json')
    return {'source_groups':{str(p):[q(p,u['order']) for u in units if u['page']==p] for p in PAGES},
        'policy2_2':policy,'transactions':{'headers':qs(158,1,8),'rows':rows,'unit':'EUR thousands',
            'as_of':'2010-06-30','current_amount_capped_at_original':False,'asset_amounts_are_noteholder_cashflows':False},
        'reported_treatment':treatment,'consolidation_impact':impact,
        'note21_comparison':{'note21':deepcopy(old['cross_note_evidence']['securitised_loans']),
            'note42_net_loans_thousands':[4214243,4346416],'note42_debt_thousands':[1307439,1527467],
            'note21_net_loans_millions':['4214.2','4346.4'],'reference_read':True,
            'comparison':'Net-loan disclosures are consistent at displayed0.1million precision; source rounding policy for this comparison not established',
            'loan_asset_equals_debt_liability':False,'financial_accuracy_proved':False},
        'source_context':{'origin':'SUPPLIED_DEVELOPMENT_READING','source_authenticity':'NOT_ESTABLISHED',
            'incorporation_status':'UNRESOLVED','all_notes_read':False,'cashflows_derived':False,
            'outside_new_interpretation':['Page68preceding policy2.1context','Page159Note43and following fair-value methods'],
            'current_law_verified':False,'BES_Finance_standalone_accounts_supplied':False}}


def source_check(reading,units,transcript):
    require(len(units)==361 and len({u['id'] for u in units})==361,'Complete361source occurrences required')
    lookup={u['id']:u for u in units};source=reading['securitisation_evidence']
    require(all(u['source_sha256']==PDF and u['visible'] and u['page'] in PAGES for u in units),'Changed source')
    quoted=[q for group in source['source_groups'].values() for q in group]
    require(len(quoted)==361 and {q['id'] for q in quoted}==set(lookup),'Incomplete source partition')
    require(all(q['quote']==lookup[q['id']]['raw'] for q in quoted),'Changed contextual quote')
    def quoted_ids(value):
        found=[]
        if isinstance(value,dict):
            if 'id' in value and 'quote' in value:
                require(value['id'] in lookup and value['quote']==lookup[value['id']]['raw'],'Changed source quote')
                found.append(value['id'])
            for k,v in value.items():
                if k not in ('id','quote'):found+=quoted_ids(v)
        elif isinstance(value,list):
            for v in value:found+=quoted_ids(v)
        return found
    expected={u['id'] for u in units if (u['page']==68 and 14<=u['order']<=30) or
        (u['page']==69 and 1<=u['order']<=31) or (u['page']==70 and 1<=u['order']<=35) or
        (u['page']==71 and 1<=u['order']<=35) or (u['page']==72 and 1<=u['order']<=8)}
    require(set(quoted_ids(source['policy2_2']))==expected,'Policy2.2source coverage incomplete')
    require(len(source['policy2_2']['special_purpose_entities']['criteria'])==4,'Missing SPEcriterion')
    normalize=lambda text:''.join(text.split())
    def checkrow(cells,values):
        require(len(cells)==len(values),'Transcript width mismatch');xs=[];ys=[]
        for c,v in zip(cells,values):
            u=lookup[c['id']];require(c['quote']==u['raw'],'Changed table quote')
            if 'value' in c:require(c['value']==v and c['unit']=='EUR thousands' and c['status']=='SOURCE_NUMBER','Wrong table amount/unit')
            else:require(normalize(c['quote'])==normalize(v),'Image/text disagreement: '+c['id'])
            xs.append((u['bbox'][0]+u['bbox'][2])/2);ys.append(u['bbox'][1])
        require(xs==sorted(xs) and max(ys)-min(ys)<3,'Wrong row/column association')
    fields=['designation','initial_date','original_amount','current_amount','asset_type']
    rows=source['transactions']['rows'];require(len(rows)==len(transcript['transactions'])==10,'Incomplete transactions')
    for row,t in zip(rows,transcript['transactions']):checkrow([row[k] for k in fields],t)
    impact=source['consolidation_impact'];require(len(impact['rows'])==len(transcript['impact'])==4,'Incomplete impact')
    for row,t in zip(impact['rows'],transcript['impact']):checkrow([row['label']]+row['cells'],t)
    same([normalize(q['quote']) for q in impact['headers']],[normalize(x) for x in transcript['impact_headers']],'Wrong impact headers')
    old=read(prior.HERE/'reading.json')
    same({k:v for k,v in reading.items() if k!='securitisation_evidence'},old,'024reading changed')
    prior.source_check(old,read(prior.HERE/'source-units.json'),read(prior.HERE/'image-transcript.json'))
    comparison=source['note21_comparison']
    same([c['value'] for c in impact['rows'][0]['cells']],comparison['note42_net_loans_thousands'],'Wrong net-loan comparison')
    same([c['value'] for c in impact['rows'][1]['cells']],comparison['note42_debt_thousands'],'Wrong debt comparison')
    from decimal import Decimal
    for thousands,millions in zip(comparison['note42_net_loans_thousands'],comparison['note21_net_loans_millions']):
        require(abs(Decimal(thousands)/1000-Decimal(millions))<=Decimal('0.05'),'Printed precision comparison fails')
    require(rows[-1]['current_amount']['value']>rows[-1]['original_amount']['value'],'Source current/original distinction lost')
    return {'new_occurrences':361,'prior_occurrences':1660,'total_occurrences':2021,'policy_occurrences':len(expected),
        'transaction_rows':10,'transaction_numeric_positions':20,'impact_numeric_positions':8,'policy_sections':11,
        'complete_prior_fields_preserved':True,'comparison_role':'EXPLANATORY_SOURCE_CONSISTENCY_ONLY',
        'consolidation_derecognition_and_legal_ownership_kept_distinct':True}


def source_worker():
    units=original_units(); transcript=read(HERE/'image-transcript.json'); review=HERE/'SOURCE-REVIEW.md'
    require(review.is_file() and len(review.read_text())>1000, 'Substantive source review required')
    for item in read(HERE/'images.json'): require(sha(ROOT/item['path'])==item['sha256'], 'Source image changed')
    reading=deepcopy(read(prior.HERE/'reading.json')); reading['securitisation_evidence']=securitisation_reading(units,transcript)
    checked=source_check(reading,units,transcript)
    all_units=sorted(read(BASE/'attempt-015/source-units.json')+read(BASE/'attempt-022/source-units.json')+read(BASE/'attempt-023/source-units.json')+read(prior.HERE/'source-units.json')+units,
                     key=lambda u:(u['page'],u['order'],u['id']))
    save(HERE/'source-units.json',units); save(HERE/'reading.json',reading)
    entry={'document':DOCUMENT,'source':PDF,'reading':compact_digest(reading),'pages_digest':compact_digest(all_units),
        'pages':sorted({u['page'] for u in all_units}),'occurrences':len(all_units),
        'reading_fields':['source_groups','tables','terms','scope','debt_context','debt_securities','cross_note_evidence','securitisation_evidence']}
    original=(PREP/'baseline/statement_cells.py').read_text()
    require(PROFILE not in original and original.count('PROFILES = {')==1,'Baseline registry changed')
    candidate=original.replace('PROFILES = {\n','PROFILES = {\n    '+repr(PROFILE)+': '+repr(entry)+',\n',1)
    (HERE/'candidate-statement_cells.py').write_text(candidate); save(HERE/'registry-entry.json',entry)
    names=['reading.json','source-units.json','registry-entry.json','candidate-statement_cells.py',
           'image-transcript.json','SOURCE-REVIEW.md','images.json']
    save(HERE/'candidate-freeze.json',{'bindings':{n:sha(HERE/n) for n in names},'candidate_sha256':digest(candidate.encode())})
    from legalmath.prospectus.successor import statement_cells as cells
    try: cells.admit({'units':all_units},supplied({'units':all_units}))
    except ValueError as exc: require('Unsupported source statement' in str(exc),'Unexpected baseline refusal')
    else: raise ValueError('New profile already supported')
    save(HERE/'source-check.json',{'status':'PASS',**checked,'baseline_gap':'Policy2.2/Note42profile unsupported','source_review':common.ref(review)})


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
        'review':{'kind':'DEVELOPMENT','reviewer':'Original page images, exact quotes and independent table transcript',
            'reason':'Complete024plus original policy2.2/Note42; control,derecognition,ownership and prior limits remain distinct'},
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
    graph={'units':read(BASE/'attempt-015/source-units.json')+read(BASE/'attempt-022/source-units.json')+read(BASE/'attempt-023/source-units.json')+read(prior.HERE/'source-units.json')+read(HERE/'source-units.json')}
    changes={
        'voting-necessary':lambda d:d['policy2_2']['subsidiaries'].update(voting_threshold_necessary=True),
        'associate-threshold':lambda d:d['policy2_2']['associates'].update(threshold_necessary=True),
        'associate-exception-lost':lambda d:d['policy2_2']['associates'].update(loss_limit_exceptions=[]),
        'loss-date-changed':lambda d:d['policy2_2']['noncontrolling_losses'].update(from_2010='All losses allocated to parent'),
        'spe-criterion-lost':lambda d:d['policy2_2']['special_purpose_entities']['criteria'].pop(),
        'fund-exception-lost':lambda d:d['policy2_2']['managed_funds'].update(exception='Never consolidate'),
        'goodwill-cost-capitalised':lambda d:d['policy2_2']['goodwill'].update(from_2010='All transaction costs capitalised'),
        'goodwill-annual-review-lost':lambda d:d['policy2_2']['goodwill'].update(impairment='Only if indication exists'),
        'all-sales-income':lambda d:d['policy2_2']['noncontrolling_transactions'].update(loss_of_control_rule_applied_to_all_sales=True),
        'fx-wording-corrected':lambda d:d['policy2_2']['foreign_currency_translation'].update(wording_caution='Unambiguous'),
        'impairment-exception-lost':lambda d:d['policy2_2']['eliminations'].update(group='Eliminate all unrealised losses without exception'),
        'missing-transaction':lambda d:d['transactions']['rows'].pop(),
        'wrong-asset':lambda d:d['transactions']['rows'][5]['asset_type'].update(quote='Mortgage loans'),
        'wrong-unit':lambda d:d['transactions']['rows'][0]['current_amount'].update(unit='EUR million'),
        'original-as-current':lambda d:d['transactions']['rows'][0].update(current_amount=d['transactions']['rows'][0]['original_amount']),
        'amount-capped':lambda d:d['transactions'].update(current_amount_capped_at_original=True),
        'pre2004-restated':lambda d:d['reported_treatment']['transition'].update(rule='All earlier assets restated'),
        'true-sale-assumed':lambda d:d['reported_treatment']['mortgages3_4_5'].update(legal_true_sale_established=True),
        'vehicle-consolidation-assumed':lambda d:d['reported_treatment']['leverage_finance1'].update(vehicle_consolidated_inferred_from_non_derecognition=True),
        'consolidation-is-derecognition':lambda d:d['reported_treatment'].update(consolidation_equals_derecognition=True),
        'partial-table-complete':lambda d:d['consolidation_impact'].update(complete_balance_sheet=True),
        'asset-equals-debt':lambda d:d['note21_comparison'].update(loan_asset_equals_debt_liability=True),
        'current-law-verified':lambda d:d['source_context'].update(current_law_verified=True),
        'incorporation-assumed':lambda d:d['source_context'].update(incorporation_status='CONFIRMED')}
    rows=[]
    for name,change in changes.items():
        bad=supplied(graph); change(bad['reading']['securitisation_evidence'])
        try: cells.admit(graph,bad)
        except ValueError as exc: rows.append({'case':name,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else: raise ValueError('Altered interpretation accepted: '+name)
    for name in ('missing-page','source-hash','geometry'):
        g=deepcopy(graph)
        if name=='missing-page': g['units']=[u for u in g['units'] if u['page']!=158]
        elif name=='source-hash': g['units'][-1]['source_sha256']='0'*64
        else: g['units'][-1]['bbox'][0]+=1
        bad=supplied(g)
        try: cells.admit(g,bad)
        except ValueError as exc: rows.append({'case':name,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else: raise ValueError('Altered source accepted: '+name)
    return rows


def consumer_worker(kind):
    from legalmath.prospectus.successor import service
    candidate_frozen(); original=read(BASE/'attempt-007/products.json.gz')
    baseline=prior.build_products(original); before=service.consume(baseline,ROOT,include_artifacts=True)
    previous=read(prior.HERE/'ordinary.json.gz')
    require(digest(before)==previous['answer_sha256'],'Complete024baseline answer changed')
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
    for key in baseline_reading: same(before['source_statement_cells'][key],after['source_statement_cells'][key],'Lost024field '+key)
    body=after['source_statement_cells']; reading=read(HERE/'reading.json')
    for key in reading: same(body[key],reading[key],'Incomplete delivered field '+key)
    require(body['consumed'] and not body['independent_financial_acceptance'] and body['legal_dependency_resolution']=='UNCHANGED','Scope overclaim')
    checked=source_check(reading,read(HERE/'source-units.json'),read(HERE/'image-transcript.json'))
    cases=registry_controls()
    imported={n:m.__file__ for n,m in sys.modules.items() if n.startswith('legalmath') and getattr(m,'__file__',None)}
    location=HERE/'installed' if kind=='installed' else ROOT/'src'
    require(imported and all(Path(p).resolve().is_relative_to(location) for p in imported.values()),'Wrong import origin')
    del original,baseline,current,left,right
    receipt021=read(BASE/'attempt-021/ordinary.json.gz')
    old_answer={**before,**receipt021['replacements'],'source_statement_cells':receipt021['addition']}
    require(digest(old_answer)==receipt021['answer_sha256'],'Lossless021answer reconstruction failed')
    composed=read(BASE/'attempt-016/answer-supplement.json.gz'); composition=read(BASE/'attempt-017/composition.json')
    require(digest(composed)==composition['previous_content_sha256'],'Original016changed')
    composed.update(read(BASE/'attempt-017/answer-delta.json.gz'))
    require(digest(composed)==composition['complete_composed_sha256'],'Original017changed')
    composed['h1_normal_statement_consumer']=old_answer
    require(digest(composed)==receipt021['full_composed_sha256'],'Complete021composition changed')
    receipt022=read(BASE/'attempt-022/ordinary.json.gz')
    answer022={**before,**receipt022['replacements'],'source_statement_cells':receipt022['addition']}
    require(digest(answer022)==receipt022['answer_sha256'],'Lossless022answer reconstruction failed')
    composed['h1_debt_context_consumer']=answer022
    require(digest(composed)==receipt022['full_composed_sha256'],'Complete022composition changed')
    receipt023=read(BASE/'attempt-023/ordinary.json.gz')
    answer023={**before,**receipt023['replacements'],'source_statement_cells':receipt023['addition']}
    require(digest(answer023)==receipt023['answer_sha256'],'Lossless023answer reconstruction failed')
    composed['h1_debt_securities_consumer']=answer023
    require(digest(composed)==receipt023['full_composed_sha256'],'Complete023composition changed')
    composed['h1_cross_note_consumer']=before
    require(digest(composed)==previous['full_composed_sha256'],'Complete024composition changed')
    composed['h1_securitisation_consumer']=after
    receipt={'status':'PASS','prior_complete_answer_sha256':digest(before),'answer_sha256':digest(after),
        'prior_full_composed_sha256':previous['full_composed_sha256'],'full_composed_sha256':digest(composed),
        'reading_sha256':compact_digest(reading),'replacements':replacements,'addition':body,'controls':cases,
        'source_check':checked,'imports':imported,'whole_task_complete':False,'source_truth_established':False,
        'recipe':'Reconstruct024from007and frozen profile; derive021/022/023from retained receipts and verify; retain016/017/021/022/023/024 and add025as h1_securitisation_consumer'}
    del composed,before,after,old_answer,answer022,answer023
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
        elif change=='changed_p2': p2['source_statement_cells']['reading']['securitisation_evidence']['reported_treatment']['consolidation_equals_derecognition']=True
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
    previous=read(prior.HERE/'requirements.json'); rows=deepcopy(previous['rows'])
    for row in rows:
        if row.get('status','').startswith('THIS_ATTEMPT_MUST_PASS'):
            row.update(status='RETAINED_COMPLETE_FINITE_INTEGRATION',evidence=common.ref(prior.HERE/'result.json'))
    rows.append({'requirement':'Complete policy2.2/Note42control,derecognition,ten transactions and four impact rows',
                 'status':'THIS_ATTEMPT_MUST_PASS; see stage outcomes'})
    original=read(BASE/'attempt-007/products.json.gz')
    units=[u for u in original['P1']['payload']['graph']['units'] if u['document']==DOCUMENT and 61<=u['page']<=171]
    inventory=[]
    for u in units:
        raw=u['raw']
        if not raw.startswith('NOTE '): continue
        token=raw.split()[1]
        if not token.isdigit(): continue
        number=int(token)
        status=('RETAINED_FINITE_INTEGRATION' if number in (10,21,32,35) else
                'THIS_ATTEMPT_SUBJECT_TO_STAGE_RESULTS' if number==42 else
                'RETAINED_SUPPLEMENT_ONLY' if number in (11,12,28,36,37,38) else
                'SOURCE_RETAINED_FULL_INTERPRETATION_NOT_ESTABLISHED')
        inventory.append({'note':number,'page':u['page'],'id':u['id'],'quote':raw,'status':status})
    save(HERE/'note-inventory.json',{'scope':'Native original headings61–171; heading detection alone is not semantic coverage',
        'notes':inventory,'policies':{'2.2':'THIS_ATTEMPT_SUBJECT_TO_STAGE_RESULTS','2.8':'RETAINED_FINITE_INTEGRATION','2.9':'RETAINED_FINITE_INTEGRATION',
        '2.15':'RETAINED_SUPPLEMENT_ONLY','remaining':'NOT_FULLY_INTERPRETED'},
        'task_acceptance':False})
    save(HERE/'requirements.json',{'rows':rows,'original_task_acceptance':False,'external_adviser_opinion_required':False,
        'next_discriminating_work':'Next material disclosure is Note43fair-value measures and assumptions, linked to debt/loan values. Keep Note42reported consolidation separate from controlling edition/incorporation and whole-source acceptance; follow inventory without replaying completed installs.'})


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
        elif name=='tests': command('tests',[str(ROOT/'.venv/bin/python'),'-B','-m','pytest','-q',*TESTS,'--junitxml='+str(HERE/'tests.xml')],180)
        else:
            python=read(PREP/'config.json')['package_python'] if name=='installed' else str(ROOT/'.venv/bin/python')
            command(name,[python,'-I','-B',str(ROOT/SELF),'worker-'+name],180)
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
    (HERE/'RESULT.md').write_text('# Original consolidation and securitisation integration\n\n'+('Finite source/consumer integration passed. ' if passed else 'Campaign did not pass. ')
        +'Actual stages: '+json.dumps(outcomes)+'.\n\n'
        +'The complete policy2.2/Note42reading preserves eleven policy sections,ten transactions and the four-row consolidation-impact table. '
        +'Control presumptions,policy transition dates,exceptions and reported derecognition treatments remain explicit. '
        +'Consolidation,asset derecognition and legal ownership remain distinct; the partial impact table is not balanced as a whole balance sheet. '
        +'All024fields and016/017/021/022/023/024compositions are retained through checked lossless recipes.\n\n'
        +'|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|\n|---|---|---|---|---|---|\n'
        +'|'+('Retain finite integration' if passed else 'Retain actual failure')+'|Original images/quotes/geometry and actual full normal/installed answers|See stage records|Remaining notes and authority|Record/refresh; read Note43and remaining coverage|Financial truth,current law,holder entitlement,automatic extraction,whole build|\n\n'
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
