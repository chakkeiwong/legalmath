"""Bounded original AFS balances,gains and impairment delivery."""
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
from scripts import prospectus_h1_income_collateral as prior
from scripts import prospectus_h1_statement_consumer as common

read, save, sha, digest = prior.read, prior.save, prior.sha, prior.digest
compact_digest, same, require, rel = prior.compact_digest, prior.same, prior.require, prior.rel
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
BASE = AUTH / 'attempts/source-bes-dep-05'
PREP = AUTH / 'reviews/h1-afs-disclosures-397'
HERE = BASE / 'attempt-034'
SELF = 'scripts/prospectus_h1_afs_disclosures.py'
PLAN = 'docs/plans/prospectus-h1-afs-disclosures-2026-10-21.md'
PRODUCTION = prior.PRODUCTION
PROFILE = 'bes-h1-2010-statements-afs-disclosures.v12'
DOCUMENT, PDF = prior.DOCUMENT, prior.PDF
PAGES = (94,106,120,121)
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
    paths.add(AUTH/'revisions/0397.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH/'program.json').stat().st_size-start['program_bytes'])
    seconds = sum(read(p)['wall_seconds'] for d in (PREP, HERE) for p in d.glob('commands/*.json'))
    return {'new_bytes': size, 'new_measured_seconds': seconds, 'new_control_seconds': 60,
        'prior_known_bytes': start['prior_known_bytes'], 'prior_known_seconds': start['prior_known_seconds'],
        'known_cumulative_bytes': start['prior_known_bytes']+size,
        'known_cumulative_seconds': start['prior_known_seconds']+seconds+60,
        'earlier_manual_and_unmeasured_costs': 'UNKNOWN; history retained',
        'execution_allowed': size+reserve < 110*1024**2 and seconds < 900}


def prepare():
    tick=time.monotonic(); auth=authority(); old=read(AUTH/'program.json')
    require(old['revision']==396 and not PREP.exists() and not HERE.exists(),'Fresh396 required')
    events=auth.events()
    attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e['budget_key']=='source-bes-dep-05']
    require(len(attempts)==old['budgets']['source-bes-dep-05']['maximum_new_attempts']==33,'Retain33attempts')
    require(read(prior.HERE/'result.json')['status']=='PASS','033 must pass')
    protected={}
    for n in (7,15,16,17,21,22,23,24,25,26,27,28,29,30,31,32,33):
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
    new=deepcopy(old);new['revision']=397
    task=next(t for t in new['tasks'] if t['id']=='source-bes-dep-05')
    task.update(dossier=PLAN,pre_admission_review=PLAN,build_criteria_scope=[],
        reason='Deliver original Notes8/9/19and judgment3.1tables and conditional interpretation;preserve033and all historical failures')
    task['inputs']=sorted((set(task['inputs'])-{PRODUCTION})|set(protected)|{rel(PREP/'freeze.json'),rel(PREP/'config.json')})
    bounds={'measured_seconds':900,'control_seconds':60,'new_bytes':112*1024**2,'failure_reserve':2*1024**2,
        'previous_known_bytes':previous['known_cumulative_bytes'],'previous_known_seconds':previous['known_cumulative_seconds'],'unchanged_retries':0}
    task['afs_disclosures_evidence']={'version':PROFILE,'freeze':rel(PREP/'freeze.json'),'bounds':bounds,
        'success_dependencies':DEPENDENCIES,'original_task_acceptance':False}
    new['budgets']['source-bes-dep-05']['maximum_new_attempts']=34
    routes=read(ROOT/old['continuation_review']['routes']); routes['baseline_revision']=397
    for row in routes['tasks']:
        if row['task']==task['id']:
            row.update(task_sha256=compact_digest(task),dossier=PLAN,phase=0,
                remaining='033income/collateral disclosures retained;Notes8/9/19and judgment3.1and wider source/authority remain.',
                next_action='Execute034Notes8/9/19and judgment3.1source/normal/installed delivery;retain033and reconcile remaining original dependencies.',
                stop_condition='34 retained admissions;900+60seconds and112MiB new;no unchanged retry;retain cumulative costs/failures.')
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
        'changes':['Deliver Notes8/9/19and judgment3.1;preserve complete033','Preserve verified original composition including OCRrisk tables','Retain33admissions and all original obligations'],
        'skeptical_audit':{'verdict':'PASS','plan':PLAN,'forecast_new_bytes':forecast,
            'no_proxy_promotion':'Original date/column geometry,conditional clauses and actual consumers;hashes and arithmetic do not prove legal or financial truth'},
        'evidence_contract':{'question':'Do linked AFS balances,gains and impairment disclosures reach the answer with dates,signs,conditions and source limits intact?',
            'primary':'Independent image transcript, original geometry/quotes, prior preservation and normal/installed corruption refusals',
            'promotion_veto':['Wrong date/amount/unit','Omitted clause','Lost prior answer','Conflicting duplicate','Wrong import','Accepted corruption'],
            'continuation_veto':['Invalid authority','Corrupt shared originals','Spent resources'],
            'not_concluded':['Automatic extraction','Verified valuation','Holder recovery','Current law','Whole build']},
        'budget_revision':{'budget_key':'source-bes-dep-05','previous_maximum':33,'new_maximum':34,
            'retained_attempts':attempts,'reason':'Original Notes8/9/19and judgment3.1dependencies of033;retain031failure,no unchanged retry or historical OCRreplay',
            'next_discriminating_check':'Signed reserves,unknown dashes,cost bases,disposal gains and conditional impairment judgments',
            'stop_condition':bounds,'same_scope_authorization':'Recover and continue original build'}})
    save(PREP/'commands/preparation.json',{'wall_seconds':time.monotonic()-tick,
        'command':[sys.executable,'-B','-m','scripts.prospectus_h1_afs_disclosures','prepare']})
    return {'status':'PREPARED','revision':397,'forecast_new_bytes':forecast,'resources':costs()}


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
    products=read(BASE/'attempt-007/products.json.gz')
    return sorted([u for u in products['P1']['payload']['graph']['units']
        if u['document']==DOCUMENT and u['page'] in PAGES and (u['page']!=94 or 1<=u['order']<=26)],key=lambda u:(u['page'],u['order'],u['id']))



def combined_units(units):
    by_id={}
    for n in (15,22,23,24,25,26,28,29,30,32,33):
        for unit in read(BASE/f'attempt-{n:03d}/source-units.json'):
            if unit['id'] in by_id:same(unit,by_id[unit['id']],'Conflicting prior occurrence')
            by_id[unit['id']]=unit
    require(len(by_id)==3386,'Wrong033occurrence count')
    for unit in units:
        require(unit['id'] not in by_id,'Unexpected source overlap');by_id[unit['id']]=unit
    require(len(by_id)==3708,'Wrong combined occurrences')
    return sorted(by_id.values(),key=lambda u:(u['page'],u['order'],u['id']))






def afs_reading(units):
    lookup={(u['page'],u['order']):u for u in units}
    def q(p,i):
        u=lookup[p,i];return {'id':u['id'],'quote':u['raw']}
    def qs(p,a,b):return [q(p,i) for i in range(a,b+1)]
    def cell(p,i):
        x=q(p,i);raw=''.join(x['quote'].split());v=None if raw=='-' else -int(raw[1:-1]) if raw.startswith('(') else int(raw)
        return {**x,'value':v,'unit':'EUR thousands','status':'UNKNOWN' if v is None else 'SOURCE_NUMBER'}
    def row(p,label,indices,inferred=None):
        return {'label_sources':[] if label is None else [q(p,label)],'label':inferred,'cells':[cell(p,i) for i in indices]}
    def span(a,n):return list(range(a,a+n))
    income={'key':'afs-gains-losses','columns':[f'{d}/{c}' for d in ('2010-06-30','2009-06-30') for c in ('Gains','Losses','Total')],
        'headers':qs(106,3,13),'column_sources':[[q(106,5),q(106,i)] for i in (6,7,9)]+[[q(106,8),q(106,i)] for i in (10,11,12)],
        'period_heading':q(106,4),'loss_columns':'POSITIVE_MAGNITUDES','net_formula':'GAINS_MINUS_LOSSES',
        'rows':[row(106,14,[16,18,20,22,24,26]),row(106,15,[17,19,21,23,25,27]),row(106,28,span(29,6)),row(106,47,span(35,6)),row(106,None,span(41,6),'NOTE8 TOTAL (unlabelled source row)')]}
    fx={'key':'fx-gains-losses','columns':income['columns'],'headers':qs(106,55,57)+qs(106,59,65),
        'column_sources':[[q(106,57),q(106,i)] for i in (60,61,62)]+[[q(106,59),q(106,i)] for i in (63,64,65)],
        'period_heading':q(106,56),'loss_columns':'POSITIVE_MAGNITUDES','net_formula':'GAINS_MINUS_LOSSES',
        'rows':[row(106,58,span(66,6)),row(106,None,span(72,6),'NOTE9 TOTAL (unlabelled source row)')]}
    columns=['Cost','Positive fair value reserve','Negative fair value reserve','Impairment losses','Book value']
    colsrc=[[q(120,8)],[q(120,9),q(120,10)],[q(120,9),q(120,11)],qs(120,12,13),qs(120,14,15)]
    afs10={'key':'afs-balance-2010','date':'2010-06-30','date_source':q(120,40),'columns':columns,'headers':qs(120,7,16),
        'column_sources':colsrc,'rows':[row(120,17,[19,21,23,25,27]),row(120,18,[20,22,24,26,28]),row(120,29,span(30,5)),row(120,60,span(35,5)),row(120,40,span(41,5))]}
    afs09={'key':'afs-balance-2009','date':'2009-12-31','date_source':q(120,72),'columns':columns,'headers':qs(120,7,15)+[q(120,46)],
        'column_sources':colsrc,'rows':[row(120,47,[49,51,53,55,57]),row(120,48,[50,52,54,56,58]),row(120,59,span(61,5)),row(120,66,span(67,5)),row(120,72,span(73,5))]}
    movement={'key':'afs-impairment-movement','columns':['2010-06-30','2009-12-31','2009-06-30'],'headers':qs(121,2,6),
        'column_sources':[[q(121,i)] for i in (4,5,6)],'period_heading':q(121,3),'equal_duration_comparison_established':False,
        'footnote_markers':[q(121,11),q(121,22)],'rows':[row(121,7+i,[13+i,18+i,24+i]) for i in range(4)]+[row(121,12,[17,23,28]),row(121,29,[30,31,32])]}
    equities=[]
    for year,start,date in (('2010',0,'2010-06-30'),('2009',40,'2009-12-31')):
        equities.append({'key':'afs-equity-'+year,'date':date,'date_source':q(121,43+start),
            'columns':['Acquisition cost','Positive fair value reserve','Negative fair value reserve','Impairment','Book value'],
            'headers':qs(121,37+start,38+start)+qs(121,43+start,51+start),
            'column_sources':[qs(121,45+start,46+start),[q(121,44+start),q(121,50+start)],[q(121,44+start),q(121,51+start)],[q(121,47+start)],qs(121,48+start,49+start)],
            'all_equity_exposures':False,'rows':[row(121,39+start+i,[52+start+i,56+start+i,60+start+i,64+start+i,68+start+i]) for i in range(4)]+[row(121,None,span(72+start,5),'MAIN EQUITY EXPOSURES TOTAL (unlabelled source row)')]})
    clauses=[
        {'key':'judgment-context','sources':qs(94,1,11),'interpretation':'Reported results depend on accounting choices and estimates;management states the choices and presentation are appropriate. That is a source claim,not an independent finding.'},
        {'key':'impairment-general','sources':qs(94,12,18),'interpretation':'Significant or prolonged decline below cost OR an event affecting estimated future cash flows informs impairment;judgment considers all relevant information,including normal price volatility.'},
        {'key':'equity-criteria','sources':qs(94,19,20),'interpretation':'Reported equity parameters are decline above30percent relative to acquisition cost OR price below cost for longer than12months;neither AND nor inclusive boundaries are substituted.'},
        {'key':'debt-criteria','sources':qs(94,21,22),'interpretation':'Debt criteria concern objective evidence of events affecting estimated future cash flows;equity price thresholds are not applied mechanically to debt.'},
        {'key':'valuation-judgment','sources':qs(94,23,26),'interpretation':'Market quotes or valuation models may require assumptions;alternative methods/estimates could increase impairment and affect reported income.'},
        {'key':'afs-gains-scope','sources':qs(106,1,2),'interpretation':'Note8reports net gains from AFS financial assets for the two stated six-month periods.'},
        {'key':'three-disposals','sources':qs(106,48,51),'interpretation':'The report states market-price exchange sales of22.5million Bradesco,24million Bank of America and129.3million Citigroup ordinary shares and159.6million euro realised net gain. Share quantities are not cash proceeds and the gain is not the whole Note8total.'},
        {'key':'related-parties','sources':[q(106,52)],'interpretation':'Related-party transactions depend on Note41;this phase does not resolve that source dependency.'},
        {'key':'fx-scope','sources':qs(106,53,54),'interpretation':'Note9reports net foreign-exchange differences,distinct from Note8AFS gains.'},
        {'key':'fx-policy','sources':qs(106,78,80),'interpretation':'Translation differences concern monetary assets/liabilities at balance-sheet exchange rates,referencing retained policy2.3;no new accounting policy is inferred.'},
        {'key':'preceding-fvtpl-context','sources':qs(120,1,4),'interpretation':'The page begins with a continuation of Note18:reported FVTPL designation under IAS39/policy2.6 and documented strategy for fair-value management/evaluation and/or embedded derivatives. Note18tables remain unresolved.'},
        {'key':'afs-balance-scope','sources':qs(120,5,6),'interpretation':'Note19balances compare30June2010with31December2009.'},
        {'key':'cost-bases','sources':qs(120,78,79),'interpretation':'Cost is acquisition cost for shares/other variable-income securities and amortised cost for debt;do not use one cost basis for all categories.'},
        {'key':'impairment-policy-link','sources':qs(120,80,82),'interpretation':'Periodic objective-evidence assessment references policy2.6and judgment3.1;the relevant finite readings are preserved,not independent impairment validation.'},
        {'key':'pledge-link','sources':[q(120,83)],'interpretation':'Pledged securities refer to Note39,whose finite source reading is retained in033;incorporation and legal authority remain unresolved.'},
        {'key':'impairment-movement-scope','sources':[q(121,1)],'interpretation':'Movements in impairment losses are separate from the signed deduction in the balance table;retain the printed period heading and do not assume equal durations.'},
        {'key':'securitisation-footnote','sources':qs(121,33,34),'interpretation':'The marked December2009exchange-differences/other entry includes21214thousand euro related to debt securitisation operations;not the entire22445thousand entry.'},
        {'key':'main-equity-scope','sources':qs(121,35,36),'interpretation':'These are main equity exposures contributing to fair-value reserve,not every equity exposure or the complete AFS portfolio.'},
        {'key':'bradesco-disposal','sources':qs(121,117,119),'interpretation':'The report links22.5million Bradesco shares sold to an approximately107.5million euro realised gain and Note8;this component is not equal to all three disposals or total AFS gains.'},
        {'key':'reported-nonimpairment','sources':qs(121,120,124),'interpretation':'The report states unrealised losses on main AFS equities were booked in fair-value reserve because they did not meet the stated impairment criteria. Preserve the claim and judgment context;tables alone do not verify its correctness.'}]
    return {'source_groups':{str(p):[q(p,u['order']) for u in units if u['page']==p] for p in PAGES},
        'selection':{'page94_orders':[1,26],'section3_2_complete':False,'note18_complete':False},
        'tables':[income,fx,afs10,afs09,movement,*equities],'clauses':clauses,
        'amounts':{'sales':{'shares_unit':'million shares','bradesco':'22.5','bank_of_america':'24','citigroup':'129.3','gain_unit':'EUR million','three_disposals_gain':'159.6','bradesco_gain':'107.5','bradesco_gain_approximate':True},
            'securitisation_in_exchange_other':{'date':'2009-12-31','unit':'EUR thousands','amount':21214}},
        'equity_parameters':{'decline_percent':'30','decline_comparator':'STRICTLY_ABOVE','duration_months':12,'duration_comparator':'STRICTLY_LONGER','combiner':'OR','scope':'REPORTED_HISTORICAL_EQUITY_JUDGMENT','mechanical_rule':False},
        'distinctions':{'dash_is_zero':False,'loss_magnitudes_are_signed_negatives':False,'all_cost_is_acquisition_cost':False,
            'reserve_and_impairment_are_same':False,'positive_movement_balance_is_balance_table_sign':False,'all_periods_equal_duration':False,
            'main_equities_are_full_portfolio':False,'sale_quantities_are_cash_proceeds':False,'bradesco_gain_is_total_disposal_gain':False,
            'three_disposals_equal_note8_total':False,'all_unrealised_losses_are_impairment':False,'nonimpairment_independently_verified':False,
            'equity_thresholds_apply_to_debt':False,'criteria_use_and':False,'thresholds_are_inclusive':False,'judgment_unnecessary':False,
            'securitisation_component_equals_exchange_other_total':False,'current_standards_verified':False,'holder_recovery_established':False},
        'dependency_resolution':{'policies2_3_2_6':'RETAINED_FINITE_READINGS','judgment3_1':'FINITE_READING_DELIVERED_HERE','note39':'RETAINED033_FINITE_READING','note41':'UNRESOLVED','note18':'PARTIAL_CONTEXT_ONLY','source_authority_or_incorporation_resolved':False},
        'source_context':{'origin':'SUPPLIED_DEVELOPMENT_READING','source_authenticity':'NOT_ESTABLISHED','incorporation_status':'UNRESOLVED','current_law_or_standard_verified':False,'historical_report_claims_only':True}}






def source_check(reading,units,transcript):
    require(len(units)==322 and len({u['id'] for u in units})==322,'Complete322selected occurrences required')
    lookup={u['id']:u for u in units};s=reading['afs_disclosures_evidence'];norm=lambda text:''.join(text.split())
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
    quotes(s);require(set(quotes(s['source_groups']))==set(lookup),'Incomplete selected source')
    expected={u['id'] for u in units if u['page']==94 or u['page']==106 and (1<=u['order']<=2 or 48<=u['order']<=54 or 78<=u['order']<=80)
        or u['page']==120 and (1<=u['order']<=6 or 78<=u['order']<=83) or u['page']==121 and (u['order']==1 or 33<=u['order']<=36 or 117<=u['order']<=124)}
    refs=quotes(s['clauses']);require(set(refs)==expected and len(refs)==len(expected)==63,'Incomplete or duplicated explanatory clauses')
    require(len(s['tables'])==len(transcript['tables'])==7,'Seven independently typed tables required')
    cells=[]
    for table,typed in zip(s['tables'],transcript['tables']):
        same(table['key'],typed['key'],'Wrong table');same(table['columns'],typed['columns'],'Wrong columns')
        same(table.get('date'),typed.get('date'),'Wrong balance date');require(len(table['rows'])==len(typed['rows']),'Wrong rows')
        for row,manual in zip(table['rows'],typed['rows']):
            label=' '.join(q['quote'] for q in row['label_sources']) if row['label_sources'] else row['label']
            same(norm(label),norm(manual[0]),'Wrong row label')
            require(len(row['cells'])==len(manual[1])==len(table['columns']),'Wrong numeric columns')
            boxes=[lookup[c['id']]['bbox'] for c in row['cells']]
            require(all(a[2]<b[0] for a,b in zip(boxes,boxes[1:])),'Wrong column geometry')
            require(max(b[1] for b in boxes)-min(b[1] for b in boxes)<3,'Wrong row geometry')
            for q in row['label_sources']:
                a=lookup[q['id']]['bbox'];require(a[2]<boxes[0][0] and abs(a[1]-boxes[0][1])<3,'Wrong label geometry')
            for c,value in zip(row['cells'],manual[1]):
                token=norm(c['quote']);number=None if token=='-' else -int(token[1:-1]) if token.startswith('(') else int(token)
                require(c['value']==value==number and c['unit']=='EUR thousands' and c['status']==('UNKNOWN' if number is None else 'SOURCE_NUMBER'),'Wrong signed number or unknown')
                cells.append(c)
        same([norm(' '.join(q['quote'] for q in col)) for col in table['column_sources']],
             [norm(x) for x in typed['header_quotes']],'Wrong exact column headings')
        if 'date_source' in table:same(norm(table['date_source']['quote']),norm(typed['date_quote']),'Wrong source date')
    require(len(cells)==160 and len({c['id'] for c in cells})==160 and sum(c['value'] is None for c in cells)==17,'Wrong table/unknown coverage')
    same(s['amounts'],transcript['amounts'],'Wrong prose quantity');same(s['equity_parameters'],transcript['equity_parameters'],'Wrong judgment criteria')
    same(s['distinctions'],transcript['distinctions'],'Wrong semantic distinctions');same(transcript['pages_reviewed'],list(PAGES),'Missing page review')
    require(len(transcript['anchors'])>=12,'Independent exact clause anchors required')
    for anchor in transcript['anchors']:
        text=' '.join(x['quote'] for c in s['clauses'] if c['key']==anchor['key'] for x in c['sources'])
        require(' '.join(anchor['quote'].split()) in ' '.join(text.split()),'Independent prose anchor mismatch')
    for table in (s['tables'][0],s['tables'][1]):
        require(norm(table['period_heading']['quote'])=='Sixmonthperiodended' and table['loss_columns']=='POSITIVE_MAGNITUDES' and table['net_formula']=='GAINS_MINUS_LOSSES','Wrong income convention')
    movement=s['tables'][4];require(norm(movement['period_heading']['quote'])=='Sixmonthperiodended' and not movement['equal_duration_comparison_established'],'Wrong movement heading interpretation')
    require(not s['selection']['section3_2_complete'] and not s['selection']['note18_complete'],'Clipped section promoted')
    old=read(prior.HERE/'reading.json');same({k:v for k,v in reading.items() if k!='afs_disclosures_evidence'},old,'033reading changed')
    prior.source_check(old,read(prior.HERE/'source-units.json'),read(prior.HERE/'image-transcript.json'))
    arithmetic=[]
    for table in s['tables']:
        if table['key']=='afs-impairment-movement':continue
        for i,row in enumerate(table['rows']):
            vals=[c['value'] for c in row['cells']]
            groups=[vals[:3],vals[3:]] if len(vals)==6 else [vals]
            for j,v in enumerate(groups):
                arithmetic.append({'table':table['key'],'row':i,'group':j,'residual':None if None in v else (v[0]-v[1]-v[2] if len(v)==3 else sum(v[:-1])-v[-1]),'unknown_skipped':None in v})
    return {'local_occurrences':322,'total_occurrences':len(combined_units(units)),'tables':7,'table_rows':33,'numeric_or_unknown_positions':160,'unknown_dashes':17,'substantive_occurrences':len(expected),
        'complete_prior_fields_preserved':True,'arithmetic_role':'EXPLANATORY_ONLY','row_residuals':arithmetic,'financial_truth_or_general_parser_proof':False}






def source_worker():
    units=original_units();transcript=read(HERE/'image-transcript.json');review=HERE/'SOURCE-REVIEW.md'
    require(review.is_file() and len(review.read_text())>1000,'Substantive source review required')
    for item in read(HERE/'images.json'):require(sha(ROOT/item['path'])==item['sha256'],'Source image changed')
    reading=deepcopy(read(prior.HERE/'reading.json'));reading['afs_disclosures_evidence']=afs_reading(units)
    checked=source_check(reading,units,transcript);all_units=combined_units(units)
    save(HERE/'source-units.json',units);save(HERE/'reading.json',reading)
    entry={'document':DOCUMENT,'source':PDF,'reading':compact_digest(reading),'pages_digest':compact_digest(all_units),
        'pages':sorted({u['page'] for u in all_units}),'occurrences':len(all_units),
        'reading_fields':list(read(prior.HERE/'registry-entry.json')['reading_fields'])+['afs_disclosures_evidence']}
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
    save(HERE/'source-check.json',{'status':'PASS',**checked,'baseline_gap':'Notes8/9/19and judgment3.1profile unsupported','source_review':common.ref(review)})


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
            'reason':'Complete033plus Notes8/9/19and judgment3.1;dates,signs,conditions and source limits remain explicit'},
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
    changes={key:(lambda s,k=key:s['distinctions'].update({k:True})) for key in read(HERE/'reading.json')['afs_disclosures_evidence']['distinctions']}
    changes.update({'date-columns-reversed':lambda s:s['tables'][0]['columns'].reverse(),
        'unknown-to-zero':lambda s:s['tables'][0]['rows'][0]['cells'][4].update(value=0,status='SOURCE_NUMBER'),
        'wrong-impairment-sign':lambda s:s['tables'][2]['rows'][1]['cells'][3].update(value=27303),
        'wrong-unit':lambda s:s['tables'][2]['rows'][0]['cells'][0].update(unit='EUR million'),
        'row-lost':lambda s:s['tables'][6]['rows'].pop(),'clause-lost':lambda s:s['clauses'].pop(),
        'criteria-and':lambda s:s['equity_parameters'].update(combiner='AND'),
        'criteria-inclusive':lambda s:s['equity_parameters'].update(decline_comparator='AT_LEAST'),
        'criteria-months':lambda s:s['equity_parameters'].update(duration_months=6),
        'gain-as-proceeds':lambda s:s['amounts']['sales'].update(gain_unit='EUR cash proceeds'),
        'footnote-amount':lambda s:s['amounts']['securitisation_in_exchange_other'].update(amount=22445),
        'all-note18-read':lambda s:s['selection'].update(note18_complete=True),
        'authority-resolved':lambda s:s['dependency_resolution'].update(source_authority_or_incorporation_resolved=True),
        'current-law':lambda s:s['source_context'].update(current_law_or_standard_verified=True)})
    for name,change in changes.items():
        bad=supplied(graph);change(bad['reading']['afs_disclosures_evidence'])
        try:cells.admit(graph,bad)
        except ValueError as exc:rows.append({'case':name,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else:raise ValueError('Altered reading accepted: '+name)
    for name in ('missing-page','source-hash','geometry','duplicate-occurrence'):
        g=deepcopy(graph)
        if name=='missing-page':g['units']=[u for u in g['units'] if u['page']!=94]
        elif name=='source-hash':next(u for u in g['units'] if u['page']==106)['source_sha256']='0'*64
        elif name=='geometry':next(u for u in g['units'] if u['page']==120)['bbox'][0]+=1
        else:g['units'].append(deepcopy(next(u for u in g['units'] if u['page']==121)))
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
    require(digest(before)==previous['answer_sha256'],'Complete033baseline answer changed')
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
    for key in baseline_reading: same(before['source_statement_cells'][key],after['source_statement_cells'][key],'Lost033field '+key)
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
          24:'h1_cross_note_consumer',25:'h1_securitisation_consumer',26:'h1_fair_value_consumer',28:'h1_risk_native_consumer',29:'h1_events_consumer',30:'h1_financial_policies_consumer',32:'h1_investment_hedges_consumer',33:'h1_income_collateral_consumer'}
    for n,key in keys.items():
        receipt=read(BASE/f'attempt-{n:03d}/ordinary.json.gz')
        answer={**before,**receipt['replacements'],'source_statement_cells':receipt['addition']}
        require(digest(answer)==receipt['answer_sha256'],'Complete prior answer changed: '+str(n))
        composed[key]=answer
        require(digest(composed)==receipt['full_composed_sha256'],'Complete prior composition changed: '+str(n))
    composed['h1_afs_disclosures_consumer']=after
    receipt={'status':'PASS','prior_complete_answer_sha256':digest(before),'answer_sha256':digest(after),
        'prior_full_composed_sha256':previous['full_composed_sha256'],'full_composed_sha256':digest(composed),
        'reading_sha256':compact_digest(reading),'replacements':replacements,'addition':body,'controls':cases,
        'source_check':checked,'imports':imported,'whole_task_complete':False,'source_truth_established':False,
        'recipe':'Reconstruct033from007;preserve016/017and021/022/023/024/025/026/028/029/030/032/033compositions;add034as h1_afs_disclosures_consumer'}
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
        elif change=='changed_p2': p2['source_statement_cells']['reading']['afs_disclosures_evidence']['distinctions']['all_unrealised_losses_are_impairment']=True
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
        if row.get('status','').startswith('THIS_ATTEMPT_MUST_PASS'):row.update(status='RETAINED_COMPLETE_FINITE_INTEGRATION',evidence=common.ref(prior.HERE/'result.json'))
    rows.append({'requirement':'Original AFS Notes8/9/19and judgment3.1with complete033preserved','status':'THIS_ATTEMPT_MUST_PASS;see actual stage results'})
    inventory=deepcopy(read(prior.HERE/'note-inventory.json'))
    for row in inventory['notes']:
        if row['note'] in (7,39):row['status']='RETAINED_FINITE_INTEGRATION'
        elif row['note'] in (8,9,19):row['status']='THIS_ATTEMPT_SUBJECT_TO_STAGE_RESULTS'
        elif row['note']==3:row['status']='SECTION3_1_THIS_ATTEMPT;OTHER_JUDGMENTS_UNRESOLVED'
        elif row['note']==18:row['status']='CLOSING_PROSE_CONTEXT_ONLY;TABLES_UNRESOLVED'
    save(HERE/'note-inventory.json',inventory)
    save(HERE/'requirements.json',{'rows':rows,'original_task_acceptance':False,'external_adviser_opinion_required':False,
        'next_discriminating_work':'Inspect Notes17/18trading/designated balances and Note41related-party dependency against retained full readings;broader policies,notes,controlling edition and source authority remain.'})






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
    (HERE/'RESULT.md').write_text('# Original AFS balances,gains and impairment disclosures\n\n'+('Finite source/consumer integration passed. ' if passed else 'Campaign did not pass. ')
        +'Actual stages: '+json.dumps(outcomes)+'.\n\n'
        +'Notes8/9/19and judgment3.1retain signed reserves,unknown dashes,cost bases,disposal gains and conditional impairment judgments. '
        +'The full033answer and all original compositions including supplied OCRrisk tables remain preserved. '
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
