"""Bounded original trading and designated balances delivery."""
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
from scripts import prospectus_h1_critical_judgments as prior
from scripts import prospectus_h1_statement_consumer as common

read, save, sha, digest = prior.read, prior.save, prior.sha, prior.digest
compact_digest, same, require, rel = prior.compact_digest, prior.same, prior.require, prior.rel
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
BASE = AUTH / 'attempts/source-bes-dep-05'
PREP = AUTH / 'reviews/h1-trading-balances-400'
HERE = BASE / 'attempt-037'
SELF = 'scripts/prospectus_h1_trading_balances.py'
PLAN = 'docs/plans/prospectus-h1-trading-balances-2026-10-21.md'
PRODUCTION = prior.PRODUCTION
PROFILE = 'bes-h1-2010-statements-trading-balances.v15'
DOCUMENT, PDF = prior.DOCUMENT, prior.PDF
PAGES = (118,119,120)
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
    paths.add(AUTH/'revisions/0400.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH/'program.json').stat().st_size-start['program_bytes'])
    seconds = sum(read(p)['wall_seconds'] for d in (PREP, HERE) for p in d.glob('commands/*.json'))
    return {'new_bytes': size, 'new_measured_seconds': seconds, 'new_control_seconds': 60,
        'prior_known_bytes': start['prior_known_bytes'], 'prior_known_seconds': start['prior_known_seconds'],
        'known_cumulative_bytes': start['prior_known_bytes']+size,
        'known_cumulative_seconds': start['prior_known_seconds']+seconds+60,
        'earlier_manual_and_unmeasured_costs': 'UNKNOWN; history retained',
        'execution_allowed': size+reserve < 110*1024**2 and seconds < 960}


def prepare():
    tick=time.monotonic(); auth=authority(); old=read(AUTH/'program.json')
    require(old['revision']==399 and not PREP.exists() and not HERE.exists(),'Fresh399 required')
    events=auth.events()
    attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e['budget_key']=='source-bes-dep-05']
    require(len(attempts)==old['budgets']['source-bes-dep-05']['maximum_new_attempts']==36,'Retain36attempts')
    require(read(prior.HERE/'result.json')['status']=='PASS','036 must pass')
    protected={}
    for n in (7,15,16,17,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36):
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
    new=deepcopy(old);new['revision']=400
    task=next(t for t in new['tasks'] if t['id']=='source-bes-dep-05')
    task.update(dossier=PLAN,pre_admission_review=PLAN,build_criteria_scope=[],
        reason='Deliver complete Notes17/18conditional judgments;preserve036and all historical failures')
    task['inputs']=sorted((set(task['inputs'])-{PRODUCTION})|set(protected)|{rel(PREP/'freeze.json'),rel(PREP/'config.json')})
    bounds={'measured_seconds':960,'control_seconds':60,'new_bytes':112*1024**2,'failure_reserve':2*1024**2,
        'previous_known_bytes':previous['known_cumulative_bytes'],'previous_known_seconds':previous['known_cumulative_seconds'],'unchanged_retries':0}
    task['trading_balances_evidence']={'version':PROFILE,'freeze':rel(PREP/'freeze.json'),'bounds':bounds,
        'success_dependencies':DEPENDENCIES,'original_task_acceptance':False}
    new['budgets']['source-bes-dep-05']['maximum_new_attempts']=37
    routes=read(ROOT/old['continuation_review']['routes']); routes['baseline_revision']=400
    for row in routes['tasks']:
        if row['task']==task['id']:
            row.update(task_sha256=compact_digest(task),dossier=PLAN,phase=0,
                remaining='036critical judgments retained;Notes17/18and wider source/authority remain.',
                next_action='Execute037Notes17/18source/normal/installed delivery;retain036and reconcile remaining original dependencies.',
                stop_condition='37 retained admissions;960+60seconds and112MiB new;no unchanged retry;retain cumulative costs/failures.')
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
        'changes':['Deliver Notes17/18;preserve complete036','Preserve verified original composition including OCRrisk tables','Retain36admissions and all original obligations'],
        'skeptical_audit':{'verdict':'PASS','plan':PLAN,'forecast_new_bytes':forecast,
            'no_proxy_promotion':'Original date/column geometry,conditional clauses and actual consumers;hashes and arithmetic do not prove legal or financial truth'},
        'evidence_contract':{'question':'Do linked trading and designated balances disclosures reach the answer with dates,signs,conditions and source limits intact?',
            'primary':'Independent image transcript, original geometry/quotes, prior preservation and normal/installed corruption refusals',
            'promotion_veto':['Wrong date/amount/unit','Omitted clause','Lost prior answer','Conflicting duplicate','Wrong import','Accepted corruption'],
            'continuation_veto':['Invalid authority','Corrupt shared originals','Spent resources'],
            'not_concluded':['Automatic extraction','Verified valuation','Holder recovery','Current law','Whole build']},
        'budget_revision':{'budget_key':'source-bes-dep-05','previous_maximum':36,'new_maximum':37,
            'retained_attempts':attempts,'reason':'Original Notes17/18dependencies of036;retain027/031/034failures,no unchanged retry or historical OCRreplay',
            'next_discriminating_check':'Grouped derivative fair values,notionals,liability magnitudes and unknown dashes',
            'stop_condition':bounds,'same_scope_authorization':'Recover and continue original build'}})
    save(PREP/'commands/preparation.json',{'wall_seconds':time.monotonic()-tick,
        'command':[sys.executable,'-B','-m','scripts.prospectus_h1_trading_balances','prepare']})
    return {'status':'PREPARED','revision':400,'forecast_new_bytes':forecast,'resources':costs()}


def frozen():
    auth = authority(); admission = read(HERE/'admission.json')
    from legalmath.prospectus.execution_authority import digest as adigest
    require(adigest(read(AUTH/'program.json'))==admission['program_sha256'] and
            auth.binding(admission['task_spec'])==admission['binding'], 'Unchanged admission required')
    f = read(PREP/'freeze.json')
    require(all(sha(ROOT/n)==h for n, h in f['bindings'].items()), 'Frozen input changed')
    expected = read(HERE/'candidate-production.json')[PRODUCTION] if (HERE/'candidate-production.json').exists() else f['baseline_sha256']
    require(sha(ROOT/PRODUCTION)==expected, 'Registry outside implementation window')


def command(name, argv, timeout=300):
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
    inherited=next(item for item in read(BASE/'attempt-035/images.json') if item['page']==120)
    require(sha(ROOT/inherited['path'])==inherited['sha256'],'Retained120image changed')
    (HERE/'images').mkdir();images=[]
    for page in (118,119):
        command('render-'+str(page),['pdftoppm','-f',str(page),'-l',str(page),'-r','160','-singlefile','-png',str(BASE/'attempt-001/interim.pdf'),str(HERE/'images'/f'page-{page}')],60)
        images.append({'page':page,'path':rel(HERE/'images'/f'page-{page}.png'),'sha256':sha(HERE/'images'/f'page-{page}.png')})
    images.append(inherited);save(HERE/'images.json',images)




def original_units():
    products=read(BASE/'attempt-007/products.json.gz')
    return sorted([u for u in products['P1']['payload']['graph']['units'] if u['document']==DOCUMENT and u['page'] in PAGES],key=lambda u:(u['page'],u['order'],u['id']))





def combined_units(units):
    by_id={}
    for n in (15,22,23,24,25,26,28,29,30,32,33,35,36):
        for unit in read(BASE/f'attempt-{n:03d}/source-units.json'):
            if unit['id'] in by_id:same(unit,by_id[unit['id']],'Conflicting prior occurrence')
            by_id[unit['id']]=unit
    require(len(by_id)==3773,'Wrong036occurrence count');overlap=0
    for unit in units:
        if unit['id'] in by_id:same(unit,by_id[unit['id']],'Changed retained120occurrence');overlap+=1
        by_id[unit['id']]=unit
    require(overlap==86 and len(by_id)==4006,'Wrong overlap or combined occurrences')
    return sorted(by_id.values(),key=lambda u:(u['page'],u['order'],u['id']))








def trading_reading(units):
    lookup={(u['page'],u['order']):u for u in units}
    def q(p,i):
        u=lookup[p,i];return {'id':u['id'],'quote':u['raw']}
    def qs(p,a,b):return [q(p,i) for i in range(a,b+1)]
    def cell(p,i):
        x=q(p,i);token=''.join(x['quote'].split());v=None if token=='-' else int(token)
        return {**x,'value':v,'unit':'EUR thousands','status':'UNKNOWN' if v is None else 'SOURCE_NUMBER'}
    def row(p,label,indices,category,inferred=None):
        return {'label_sources':[] if label is None else [q(p,label)],'label':inferred,'category':category,'cells':[cell(p,i) for i in indices]}
    def seq(a):return list(range(a,a+6))
    balances={'key':'trading-balances','columns':['2010-06-30','2009-12-31'],'headers':qs(118,3,8)+[q(118,30),q(118,32)],
        'column_sources':[[q(118,4)],[q(118,5)]],'liability_convention':'POSITIVE_MAGNITUDE',
        'rows':[row(118,9,[11,13],'trading-securities'),row(118,10,[12,14],'trading-securities'),row(118,29,[15,16],'trading-securities'),
            row(118,None,[17,18],'trading-securities-subtotal','SECURITIES TOTAL (unlabelled source row)'),
            row(118,31,[19,20],'positive-fair-value-assets'),row(118,None,[21,22],'trading-assets-total','TRADING ASSETS TOTAL (unlabelled source row)'),
            row(118,33,[23,26],'negative-fair-value-liability-magnitude'),row(118,34,[24,27],'short-sales-liability-magnitude'),
            row(118,None,[25,28],'trading-liabilities-total','TRADING LIABILITIES TOTAL (unlabelled source row)')]}
    dcols=[f'{d}/{c}' for d in ('2010-06-30','2009-12-31') for c in ('Notional','Assets fair value','Liabilities fair value')]
    dheaders=[[q(119,3),q(119,4)],[q(119,3),q(119,7),q(119,5)],[q(119,3),q(119,7),q(119,8)],
        [q(119,6),q(119,9)],[q(119,6),q(119,11),q(119,10)],[q(119,6),q(119,11),q(119,12)]]
    normal=[row(119,21,[46,51,52,64,69,70],'exchange-rate'),row(119,25,[55,58,73,76,77,78],'exchange-rate'),
        row(119,None,[59,79,80,81,82,83],'exchange-rate-subtotal','EXCHANGE RATE TOTAL (unlabelled source row)')]
    normal += [row(119,27+i,[84+i,91+i,98+i,105+i,112+i,119+i],'interest-rate') for i in range(7)]
    normal += [row(119,None,seq(126),'interest-rate-subtotal','INTEREST RATE TOTAL (unlabelled source row)')]
    normal += [row(119,35+i,[132+i,136+i,140+i,144+i,148+i,152+i],'equity-index') for i in range(4)]
    normal += [row(119,None,seq(156),'equity-index-subtotal','EQUITY INDEX TOTAL (unlabelled source row)'),
        row(119,40,seq(162),'credit-default'),row(119,41,seq(168),'all-trading-derivatives')]
    derivatives={'key':'trading-derivatives','columns':dcols,'headers':qs(119,2,14)+[q(119,i) for i in (26,34,39)],'column_sources':dheaders,
        'liability_convention':'POSITIVE_MAGNITUDE','notional_is_fair_value':False,'rows':normal}
    paired=[]
    for name,label,legs,notionals,fv in [('forward',15,[16,17],[[42,60],[43,61]],[47,48,65,66]),
        ('currency-swaps',18,[19,20],[[44,62],[45,63]],[49,50,67,68]),
        ('currency-interest-rate-swaps',22,[23,24],[[53,74],[54,75]],[56,57,71,72])]:
        paired.append({'key':name,'label':q(119,label),'category':q(119,14),'dates':['2010-06-30','2009-12-31'],
            'notional_legs':[{'label':q(119,leg),'cells':[cell(119,i) for i in indices]} for leg,indices in zip(legs,notionals)],
            'shared_fair_values':{'columns':[dcols[i] for i in (1,2,4,5)],'cells':[cell(119,i) for i in fv]},
            'scope':'SHARED_GROUP_FAIR_VALUES','allocation_to_buy_sell_legs':'NOT_REPORTED','duplication_allowed':False})
    designated={'key':'designated-fvtpl-balances','columns':balances['columns'],'headers':qs(119,176,179),
        'column_sources':[[q(119,177)],[q(119,178)]],'rows':[row(119,180,[181,182],'bonds-other-entities'),row(119,183,[184,185],'shares'),
            row(119,186,[187,188],'other-securities'),row(119,None,[189,190],'designated-total','DESIGNATED FVTPL TOTAL (unlabelled source row)')]}
    clauses=[{'key':'trading-scope','sources':qs(118,1,2),'interpretation':'Note17trading balances compareJune2010andDecember2009;assets and liability magnitudes are separate.'},
        {'key':'trading-purpose','sources':qs(118,35,36),'interpretation':'Reported trading securities are bought for short-term trading regardless of their maturity,referencing policy2.6;short contractual maturity is not required.'},
        {'key':'collateral-link','sources':[q(118,37)],'interpretation':'Pledged securities refer to retained finite Note39reading;no legal title or recoverability conclusion follows.'},
        {'key':'derivative-scope','sources':[q(119,1)],'interpretation':'Trading derivatives compare two dates with notionals separate from asset and liability fair values. The three buy/sell pairs share fair values across the pair;per-leg fair values are not reported.'},
        {'key':'designated-scope','sources':qs(119,174,175),'interpretation':'Note18designated FVTPL balances are distinct from trading securities and derivatives.'},
        {'key':'designated-basis','sources':qs(120,1,4),'interpretation':'The retained continuation reports historical IAS39/policy2.6designation under documented strategy,with fair-value management/evaluation and/or embedded derivatives. Current accounting correctness is not verified.'}]
    return {'source_groups':{str(p):[q(p,u['order']) for u in units if u['page']==p] for p in PAGES},'tables':[balances,derivatives,designated],'paired_derivative_groups':paired,'clauses':clauses,
        'distinctions':{'notional_equals_fair_value':False,'notional_is_cash_outlay':False,'notional_is_maximum_loss':False,'fair_values_allocated_per_leg':False,
            'shared_fair_values_duplicated_per_leg':False,'asset_liability_netting_authorized':False,'liability_magnitudes_are_signed_losses':False,
            'dash_is_zero':False,'trading_requires_short_contractual_maturity':False,'designated_assets_are_trading_assets':False,
            'designation_requires_both_conditions':False,'current_accounting_verified':False,'collateral_enforceability_verified':False,'holder_recovery_established':False},
        'dependency_resolution':{'note18_closing_prose':'RETAINED035;TABLES_ADDED_HERE','note39':'RETAINED033_FINITE_READING','policy2_6':'RETAINED030_FINITE_READING','source_authority_or_incorporation_resolved':False},
        'source_context':{'origin':'SUPPLIED_DEVELOPMENT_READING','source_authenticity':'NOT_ESTABLISHED','incorporation_status':'UNRESOLVED','historical_report_claims_only':True,'current_law_or_standard_verified':False}}








def source_check(reading,units,transcript):
    require(len(units)==319 and len({u['id'] for u in units})==319,'Complete319occurrences required')
    lookup={u['id']:u for u in units};s=reading['trading_balances_evidence'];norm=lambda x:''.join(x.split())
    require(all(u['visible'] and u['source_sha256']==PDF and u['page'] in PAGES for u in units),'Changed source')
    def quotes(v):
        ids=[]
        if isinstance(v,dict):
            if 'id' in v and 'quote' in v:
                require(v['id'] in lookup and v['quote']==lookup[v['id']]['raw'],'Changed quote');ids.append(v['id'])
            for k,x in v.items():
                if k not in ('id','quote'):ids+=quotes(x)
        elif isinstance(v,list):
            for x in v:ids+=quotes(x)
        return ids
    quotes(s);require(set(quotes(s['source_groups']))==set(lookup),'Incomplete full pages')
    expected={u['id'] for u in units if u['page']==118 and (1<=u['order']<=2 or 35<=u['order']<=37) or u['page']==119 and (u['order']==1 or 174<=u['order']<=175) or u['page']==120 and 1<=u['order']<=4}
    refs=quotes(s['clauses']);require(set(refs)==expected and len(refs)==len(expected)==12,'Incomplete or duplicated clauses')
    allcells=[]
    def values(cells,manual):
        require(len(cells)==len(manual),'Wrong value count')
        for c,v in zip(cells,manual):
            token=norm(c['quote']);n=None if token=='-' else int(token)
            require(c['value']==v==n and c['unit']=='EUR thousands' and c['status']==('UNKNOWN' if n is None else 'SOURCE_NUMBER'),'Wrong cell value/unit/status')
            allcells.append(c)
    require(len(s['tables'])==len(transcript['tables'])==3,'Three normal table blocks required')
    for table,typed in zip(s['tables'],transcript['tables']):
        same(table['key'],typed['key'],'Wrong table');same(table['columns'],typed['columns'],'Wrong columns')
        same([norm(' '.join(q['quote'] for q in group)) for group in table['column_sources']],[norm(v) for v in typed['header_quotes']],'Wrong date/field headings')
        require(len(table['rows'])==len(typed['rows']),'Wrong normal row count')
        for row,manual in zip(table['rows'],typed['rows']):
            label=' '.join(q['quote'] for q in row['label_sources']) if row['label_sources'] else row['label'];same(norm(label),norm(manual[0]),'Wrong row label')
            same(row['category'],manual[2],'Wrong category');values(row['cells'],manual[1])
            boxes=[lookup[c['id']]['bbox'] for c in row['cells']]
            require(all(a[2]<b[0] for a,b in zip(boxes,boxes[1:])) and max(b[1] for b in boxes)-min(b[1] for b in boxes)<3,'Wrong normal geometry')
            for labelref in row['label_sources']:
                box=lookup[labelref['id']]['bbox'];require(box[2]<boxes[0][0] and abs(box[1]-boxes[0][1])<3,'Wrong normal label geometry')
    require(len(s['paired_derivative_groups'])==len(transcript['paired_groups'])==3,'Three paired groups required')
    for group,typed in zip(s['paired_derivative_groups'],transcript['paired_groups']):
        same(group['key'],typed['key'],'Wrong paired group');same(norm(group['label']['quote']),norm(typed['label']),'Wrong group label')
        same(group['dates'],['2010-06-30','2009-12-31'],'Wrong pair dates');require(group['scope']=='SHARED_GROUP_FAIR_VALUES' and group['allocation_to_buy_sell_legs']=='NOT_REPORTED' and not group['duplication_allowed'],'Invented per-leg fair values')
        require(len(group['notional_legs'])==len(typed['legs'])==2,'Two notional legs required')
        ys=[]
        for leg,manual in zip(group['notional_legs'],typed['legs']):
            same(norm(leg['label']['quote']),norm(manual[0]),'Wrong leg label');values(leg['cells'],manual[1]);boxes=[lookup[c['id']]['bbox'] for c in leg['cells']]
            require(boxes[0][2]<boxes[1][0] and abs(boxes[0][1]-boxes[1][1])<1,'Wrong notional association')
            labelbox=lookup[leg['label']['id']]['bbox'];require(labelbox[2]<boxes[0][0] and abs(labelbox[1]-boxes[0][1])<1,'Wrong leg geometry');ys.append(boxes[0][1])
        require(ys[0]<ys[1],'Reversed buy/sell rows')
        shared=group['shared_fair_values'];same(shared['columns'],typed['fair_value_columns'],'Wrong shared fair-value columns');values(shared['cells'],typed['fair_values'])
        boxes=[lookup[c['id']]['bbox'] for c in shared['cells']]
        require(all(a[2]<b[0] for a,b in zip(boxes,boxes[1:])),'Wrong shared fair-value x association')
        require(all(abs(box[1]-sum(ys)/2)<1 for box in boxes),'Shared fair values not centred across both legs')
        require(lookup[group['label']['id']]['bbox'][1]<ys[0],'Group label follows legs')
    numeric_ids={u['id'] for u in units if u['page']==118 and 11<=u['order']<=28 or u['page']==119 and (42<=u['order']<=173 or u['order'] in (181,182,184,185,187,188,189,190))}
    require(len(allcells)==len({c['id'] for c in allcells})==158 and {c['id'] for c in allcells}==numeric_ids,'Numeric positions omitted/duplicated')
    same(s['distinctions'],transcript['distinctions'],'Wrong distinction');same(transcript['pages_reviewed'],list(PAGES),'Incomplete image review')
    require({a['key'] for a in transcript['anchors']}=={c['key'] for c in s['clauses']},'Missing source anchors')
    for a in transcript['anchors']:
        text=' '.join(q['quote'] for c in s['clauses'] if c['key']==a['key'] for q in c['sources']);require(' '.join(a['quote'].split()) in ' '.join(text.split()),'Wrong manual clause anchor')
    old=read(prior.HERE/'reading.json');same({k:v for k,v in reading.items() if k!='trading_balances_evidence'},old,'036reading changed')
    prior.source_check(old,read(prior.HERE/'source-units.json'),read(prior.HERE/'image-transcript.json'))
    total=[c['value'] for c in s['tables'][1]['rows'][-1]['cells']]
    balance_assets=[c['value'] for c in s['tables'][0]['rows'][4]['cells']];balance_liabilities=[c['value'] for c in s['tables'][0]['rows'][6]['cells']]
    return {'local_occurrences':319,'equal_overlap_occurrences':86,'new_occurrences':233,'combined_occurrences':len(combined_units(units)),
        'normal_rows':31,'paired_groups':3,'notional_legs':6,'numeric_or_unknown_positions':158,'unknown_dashes':sum(c['value'] is None for c in allcells),
        'clause_groups':6,'substantive_occurrences':12,'complete_prior_fields_preserved':True,
        'cross_note_diagnostic':{'role':'EXPLANATORY_ONLY','asset_totals_match':[total[1],total[4]]==balance_assets,'liability_magnitudes_match':[total[2],total[5]]==balance_liabilities},'financial_truth_or_current_law_verified':False}








def full_graph_preflight(candidate,reading,graph):
    namespace={'__name__':'legalmath.prospectus.successor._trading_candidate','__package__':'legalmath.prospectus.successor'}
    exec(compile(candidate,'candidate-statement_cells.py','exec'),namespace)
    packet={'version':'source-statement-cells.v1','profile':PROFILE,'document':DOCUMENT,'graph_sha256':digest(graph),
        'review':{'kind':'DEVELOPMENT','reviewer':'Manual original geometry and complete source clauses','reason':'Full actual graph before production'},'reading':reading}
    admitted=namespace['admit'](graph,packet)
    bad=deepcopy(graph);bad['units']=[u for u in bad['units'] if u['id']!='bes-interim-h1-2010:p118:l0']
    negative=deepcopy(packet);negative['graph_sha256']=digest(bad)
    try:namespace['admit'](bad,negative)
    except ValueError as exc:require('original pages or geometry' in str(exc),'Wrong context refusal')
    else:raise ValueError('Missing context accepted')
    return {'status':'PASS','actual_graph_admitted':True,'context_loss_refused':True,'admitted_sha256':admitted['sha256']}



def source_worker():
    units=original_units();transcript=read(HERE/'image-transcript.json');review=HERE/'SOURCE-REVIEW.md'
    require(review.is_file() and len(review.read_text())>1000,'Substantive source review required')
    for item in read(HERE/'images.json'):require(sha(ROOT/item['path'])==item['sha256'],'Source image changed')
    reading=deepcopy(read(prior.HERE/'reading.json'));reading['trading_balances_evidence']=trading_reading(units)
    checked=source_check(reading,units,transcript);all_units=combined_units(units)
    save(HERE/'source-units.json',units);save(HERE/'reading.json',reading)
    entry={'document':DOCUMENT,'source':PDF,'reading':compact_digest(reading),'pages_digest':compact_digest(all_units),
        'pages':sorted({u['page'] for u in all_units}),'occurrences':len(all_units),
        'reading_fields':list(read(prior.HERE/'registry-entry.json')['reading_fields'])+['trading_balances_evidence']}
    original=(PREP/'baseline/statement_cells.py').read_text()
    require(PROFILE not in original and original.count('PROFILES = {')==1,'Baseline registry changed')
    candidate=original.replace('PROFILES = {\n','PROFILES = {\n    '+repr(PROFILE)+': '+repr(entry)+',\n',1)
    actual_graph=read(BASE/'attempt-007/products.json.gz')['P1']['payload']['graph']
    save(HERE/'full-graph-preflight.json',full_graph_preflight(candidate,reading,actual_graph))
    (HERE/'candidate-statement_cells.py').write_text(candidate);save(HERE/'registry-entry.json',entry)
    names=['reading.json','source-units.json','registry-entry.json','candidate-statement_cells.py','image-transcript.json','SOURCE-REVIEW.md','images.json','full-graph-preflight.json']
    save(HERE/'candidate-freeze.json',{'bindings':{n:sha(HERE/n) for n in names},'candidate_sha256':digest(candidate.encode())})
    from legalmath.prospectus.successor import statement_cells as cells
    try:cells.admit({'units':all_units},supplied({'units':all_units}))
    except ValueError as exc:require('Unsupported source statement' in str(exc),'Unexpected baseline refusal')
    else:raise ValueError('New profile already supported')
    save(HERE/'source-check.json',{'status':'PASS',**checked,'baseline_gap':'Notes17/18profile unsupported','source_review':common.ref(review)})


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
            'reason':'Complete036plus Notes17/18;dates,signs,conditions and source limits remain explicit'},
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
    changes={k:(lambda s,k=k:s['distinctions'].update({k:True})) for k in read(HERE/'reading.json')['trading_balances_evidence']['distinctions']}
    changes.update({'leg-reversal':lambda s:s['paired_derivative_groups'][0]['notional_legs'].reverse(),
        'shared-split':lambda s:s['paired_derivative_groups'][0].update(allocation_to_buy_sell_legs='HALF_EACH'),
        'shared-duplication':lambda s:s['paired_derivative_groups'][1]['shared_fair_values']['cells'].append(deepcopy(s['paired_derivative_groups'][1]['shared_fair_values']['cells'][0])),
        'shared-missing':lambda s:s['paired_derivative_groups'][2]['shared_fair_values']['cells'].pop(),
        'notional-as-fv':lambda s:s['tables'][1]['columns'].__setitem__(0,'2010-06-30/Assets fair value'),
        'unknown-to-zero':lambda s:s['tables'][0]['rows'][7]['cells'][1].update(value=0,status='SOURCE_NUMBER'),
        'liability-sign':lambda s:s['tables'][0]['rows'][6]['cells'][0].update(value=-2168651),
        'wrong-unit':lambda s:s['tables'][2]['rows'][0]['cells'][0].update(unit='EUR million'),
        'row-lost':lambda s:s['tables'][1]['rows'].pop(),'clause-lost':lambda s:s['clauses'].pop(),
        'authority-resolved':lambda s:s['dependency_resolution'].update(source_authority_or_incorporation_resolved=True),
        'current-law':lambda s:s['source_context'].update(current_law_or_standard_verified=True)})
    for name,change in changes.items():
        bad=supplied(graph);change(bad['reading']['trading_balances_evidence'])
        try:cells.admit(graph,bad)
        except ValueError as exc:rows.append({'case':name,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else:raise ValueError('Altered reading accepted: '+name)
    for name in ('missing-page','context-occurrence-lost','source-hash','geometry','duplicate-occurrence'):
        g=deepcopy(graph)
        if name=='missing-page':g['units']=[u for u in g['units'] if u['page']!=119]
        elif name=='context-occurrence-lost':g['units']=[u for u in g['units'] if u['id']!='bes-interim-h1-2010:p118:l0']
        elif name=='source-hash':next(u for u in g['units'] if u['page']==118)['source_sha256']='0'*64
        elif name=='geometry':next(u for u in g['units'] if u['id']=='bes-interim-h1-2010:p119:l47')['bbox'][1]+=4
        else:g['units'].append(deepcopy(next(u for u in g['units'] if u['page']==119)))
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
    require(digest(before)==previous['answer_sha256'],'Complete036baseline answer changed')
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
    for key in baseline_reading: same(before['source_statement_cells'][key],after['source_statement_cells'][key],'Lost036field '+key)
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
          24:'h1_cross_note_consumer',25:'h1_securitisation_consumer',26:'h1_fair_value_consumer',28:'h1_risk_native_consumer',29:'h1_events_consumer',30:'h1_financial_policies_consumer',32:'h1_investment_hedges_consumer',33:'h1_income_collateral_consumer',35:'h1_afs_disclosures_consumer',36:'h1_critical_judgments_consumer'}
    for n,key in keys.items():
        receipt=read(BASE/f'attempt-{n:03d}/ordinary.json.gz')
        answer={**before,**receipt['replacements'],'source_statement_cells':receipt['addition']}
        require(digest(answer)==receipt['answer_sha256'],'Complete prior answer changed: '+str(n))
        composed[key]=answer
        require(digest(composed)==receipt['full_composed_sha256'],'Complete prior composition changed: '+str(n))
    composed['h1_trading_balances_consumer']=after
    receipt={'status':'PASS','prior_complete_answer_sha256':digest(before),'answer_sha256':digest(after),
        'prior_full_composed_sha256':previous['full_composed_sha256'],'full_composed_sha256':digest(composed),
        'reading_sha256':compact_digest(reading),'replacements':replacements,'addition':body,'controls':cases,
        'source_check':checked,'imports':imported,'whole_task_complete':False,'source_truth_established':False,
        'recipe':'Reconstruct036from007;preserve016/017and021/022/023/024/025/026/028/029/030/032/033/035/036compositions;add037as h1_trading_balances_consumer'}
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
        elif change=='changed_p2': p2['source_statement_cells']['reading']['trading_balances_evidence']['distinctions']['notional_equals_fair_value']=True
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
    rows.append({'requirement':'Original Notes17/18with grouped derivative fair values and complete036retained','status':'THIS_ATTEMPT_MUST_PASS;see actual stage results'})
    inventory=deepcopy(read(prior.HERE/'note-inventory.json'))
    for row in inventory['notes']:
        if row['note']==3:row['status']='RETAINED_FINITE_INTEGRATION'
        elif row['note'] in (17,18):row['status']='THIS_ATTEMPT_SUBJECT_TO_STAGE_RESULTS'
    save(HERE/'note-inventory.json',inventory)
    save(HERE/'requirements.json',{'rows':rows,'original_task_acceptance':False,'external_adviser_opinion_required':False,
        'next_discriminating_work':'Inspect Note41related-party disclosures against original requirement and retained debt/equity readings;remaining policies,notes,controlling edition and source authority remain.'})








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
        elif name=='tests': command('tests',[str(ROOT/'.venv/bin/python'),'-B','-m','pytest','-q',*TESTS,'--junitxml='+str(HERE/'tests.xml')],300)
        else:
            python=read(PREP/'config.json')['package_python'] if name=='installed' else str(ROOT/'.venv/bin/python')
            command(name,[python,'-I','-B',str(ROOT/SELF),'worker-'+name],300)
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
    (HERE/'RESULT.md').write_text('# Original trading and designated balances disclosures\n\n'+('Finite source/consumer integration passed. ' if passed else 'Campaign did not pass. ')
        +'Actual stages: '+json.dumps(outcomes)+'.\n\n'
        +'Notes17/18retain grouped derivative rows,notional/fair-value distinctions and designated balances. '
        +'The full036answer and all original compositions including supplied OCRrisk tables remain preserved. '
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
