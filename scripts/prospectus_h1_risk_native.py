"""Bounded original native risk disclosures and answer delivery."""
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
from scripts import prospectus_h1_fair_value as prior
from scripts import prospectus_h1_statement_consumer as common

read, save, sha, digest = prior.read, prior.save, prior.sha, prior.digest
compact_digest, same, require, rel = prior.compact_digest, prior.same, prior.require, prior.rel
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
BASE = AUTH / 'attempts/source-bes-dep-05'
PREP = AUTH / 'reviews/h1-risk-native-390'
HERE = BASE / 'attempt-027'
SELF = 'scripts/prospectus_h1_risk_native.py'
PLAN = 'docs/plans/prospectus-h1-risk-native-2026-10-21.md'
PRODUCTION = prior.PRODUCTION
PROFILE = 'bes-h1-2010-statements-risk-native.v7'
DOCUMENT, PDF = prior.DOCUMENT, prior.PDF
PAGES = (160,161,164,165,166,167,168,169)
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
    paths.add(AUTH/'revisions/0390.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH/'program.json').stat().st_size-start['program_bytes'])
    seconds = sum(read(p)['wall_seconds'] for d in (PREP, HERE) for p in d.glob('commands/*.json'))
    return {'new_bytes': size, 'new_measured_seconds': seconds, 'new_control_seconds': 60,
        'prior_known_bytes': start['prior_known_bytes'], 'prior_known_seconds': start['prior_known_seconds'],
        'known_cumulative_bytes': start['prior_known_bytes']+size,
        'known_cumulative_seconds': start['prior_known_seconds']+seconds+60,
        'earlier_manual_and_unmeasured_costs': 'UNKNOWN; history retained',
        'execution_allowed': size+reserve < 118*1024**2 and seconds < 720}


def prepare():
    tick=time.monotonic(); auth=authority(); old=read(AUTH/'program.json')
    require(old['revision']==389 and not PREP.exists() and not HERE.exists(),'Fresh389 required')
    events=auth.events()
    attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e['budget_key']=='source-bes-dep-05']
    require(len(attempts)==old['budgets']['source-bes-dep-05']['maximum_new_attempts']==26,'Retain26attempts')
    require(read(prior.HERE/'result.json')['status']=='PASS','026 must pass')
    protected={}
    for n in (7,15,16,17,21,22,23,24,25,26):
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
        rel(prior.HERE/'image-transcript.json'),rel(prior.HERE/'images/page-160.png'),
        rel(prior.HERE/'images.json'),rel(prior.HERE/'registry-entry.json')]
    protected.update({n:sha(ROOT/n) for n in names})
    protected.update({n:h for n,h in production.items() if n!=PRODUCTION})
    require(all(sha(ROOT/n)==h for n,h in protected.items()),'Stale inherited binding')
    save(PREP/'freeze.json',{'bindings':protected,'baseline_sha256':sha(ROOT/PRODUCTION),
        'mutable_file':PRODUCTION,'implementation_window':'Once after reviewed source and candidate freeze'})
    config=read(prior.PREP/'config.json'); require(sha(config['package_python'])==config['python_sha256'],'Build interpreter changed')
    save(PREP/'config.json',config)
    new=deepcopy(old);new['revision']=390
    task=next(t for t in new['tasks'] if t['id']=='source-bes-dep-05')
    task.update(dossier=PLAN,pre_admission_review=PLAN,build_criteria_scope=[],
        reason='Deliver native Note44risk tables and prose with OCR162–163explicitly pending; preserve complete026')
    task['inputs']=sorted((set(task['inputs'])-{PRODUCTION})|set(protected)|{rel(PREP/'freeze.json'),rel(PREP/'config.json')})
    bounds={'measured_seconds':720,'control_seconds':60,'new_bytes':120*1024**2,'failure_reserve':2*1024**2,
        'previous_known_bytes':previous['known_cumulative_bytes'],'previous_known_seconds':previous['known_cumulative_seconds'],'unchanged_retries':0}
    task['risk_native_evidence']={'version':PROFILE,'freeze':rel(PREP/'freeze.json'),'bounds':bounds,
        'success_dependencies':DEPENDENCIES,'original_task_acceptance':False}
    new['budgets']['source-bes-dep-05']['maximum_new_attempts']=27
    routes=read(ROOT/old['continuation_review']['routes']); routes['baseline_revision']=390
    for row in routes['tasks']:
        if row['task']==task['id']:
            row.update(task_sha256=compact_digest(task),dossier=PLAN,phase=0,
                remaining='026fair-value integration complete; Note44native and OCR branches plus wider source/authority remain.',
                next_action='Execute027native risk source/normal/installed delivery and adverse controls; then continue OCR162–163and original coverage.',
                stop_condition='27 retained admissions;720+60seconds and120MiB new; no unchanged retry; retain cumulative costs/failures.')
    save(PREP/'routes.json',routes)
    new['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    new['continuation_review']['bindings'].pop(PRODUCTION,None)
    new['continuation_review']['bindings'].update({n:sha(ROOT/n) for n in
        (PLAN,rel(PREP/'routes.json'),rel(PREP/'freeze.json'),rel(PREP/'baseline/statement_cells.py'))})
    require(old['obligations']==new['obligations'] and old['build_contract']==new['build_contract'],'Scope changed')
    raw=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
    source_bytes=sum(p.stat().st_size for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    forecast=costs()['new_bytes']+2*len(raw)+3*source_bytes+30*1024**2
    require(forecast<118*1024**2,'Forecast exceeds reservation')
    with (PREP/'proposal.json').open('xb') as stream:stream.write(raw)
    from legalmath.prospectus.execution_authority import digest as adigest
    save(PREP/'review.json',{'baseline':adigest(old),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Complete native Note44tables and risk prose; preserve complete026','Deduplicate overlapping page160 with equality checks','Retain26admissions and all original obligations'],
        'skeptical_audit':{'verdict':'PASS','plan':PLAN,'forecast_new_bytes':forecast,
            'no_proxy_promotion':'Table images/geometry and actual consumers; exact hashes and reported risks do not prove adequacy or recovery'},
        'evidence_contract':{'question':'Do native risk disclosures reach the answer with all assumptions,unknowns,units and unresolved OCR scope preserved?',
            'primary':'Independent image transcript, original geometry/quotes, prior preservation and normal/installed corruption refusals',
            'promotion_veto':['Wrong date/amount/unit','Omitted clause','Lost prior answer','Conflicting duplicate','Wrong import','Accepted corruption'],
            'continuation_veto':['Invalid authority','Corrupt shared originals','Spent resources'],
            'not_concluded':['Automatic extraction','Verified valuation','Holder recovery','Current law','Whole build']},
        'budget_revision':{'budget_key':'source-bes-dep-05','previous_maximum':26,'new_maximum':27,
            'retained_attempts':attempts,'reason':'Original Note44native dependency; no replay of026',
            'next_discriminating_check':'Source row/date geometry,negative liquidity label conflict,mixed units and complete downstream delivery',
            'stop_condition':bounds,'same_scope_authorization':'Recover and continue original build'}})
    save(PREP/'commands/preparation.json',{'wall_seconds':time.monotonic()-tick,
        'command':[sys.executable,'-B','-m','scripts.prospectus_h1_risk_native','prepare']})
    return {'status':'PREPARED','revision':390,'forecast_new_bytes':forecast,'resources':costs()}


def frozen():
    auth = authority(); admission = read(HERE/'admission.json')
    from legalmath.prospectus.execution_authority import digest as adigest
    require(adigest(read(AUTH/'program.json'))==admission['program_sha256'] and
            auth.binding(admission['task_spec'])==admission['binding'], 'Unchanged admission required')
    f = read(PREP/'freeze.json')
    require(all(sha(ROOT/n)==h for n, h in f['bindings'].items()), 'Frozen input changed')
    expected = read(HERE/'candidate-production.json')[PRODUCTION] if (HERE/'candidate-production.json').exists() else f['baseline_sha256']
    require(sha(ROOT/PRODUCTION)==expected, 'Registry outside implementation window')


def command(name, argv, timeout=200):
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
    source=prior.HERE/'images/page-160.png'
    expected=next(x for x in read(prior.HERE/'images.json') if x['page']==160)
    require(sha(source)==expected['sha256'],'Retained160 image changed')
    shutil.copyfile(source,HERE/'images/page-160.png')
    for page in PAGES:
        if page==160:continue
        command('render-'+str(page),['pdftoppm','-f',str(page),'-l',str(page),'-r','160','-singlefile','-png',
            str(BASE/'attempt-001/interim.pdf'),str(HERE/'images'/f'page-{page}')],60)
    save(HERE/'images.json',[{'page':p,'path':rel(HERE/'images'/f'page-{p}.png'),
        'sha256':sha(HERE/'images'/f'page-{p}.png'),'origin':'REUSED_CHECKED026' if p==160 else 'ORIGINAL_RENDER'} for p in PAGES])


def original_units():
    products = read(BASE/'attempt-007/products.json.gz')
    return sorted([u for u in products['P1']['payload']['graph']['units']
        if u['document']==DOCUMENT and u['page'] in PAGES], key=lambda u: (u['page'],u['order'],u['id']))


def combined_units(units):
    by_id={}
    for folder in (BASE/'attempt-015',BASE/'attempt-022',BASE/'attempt-023',BASE/'attempt-024',BASE/'attempt-025',prior.HERE):
        for unit in read(folder/'source-units.json'):
            if unit['id'] in by_id:same(unit,by_id[unit['id']],'Conflicting prior occurrence')
            by_id[unit['id']]=unit
    require(len(by_id)==2058,'Wrong026 occurrence count')
    overlaps=0
    for unit in units:
        if unit['id'] in by_id:
            same(unit,by_id[unit['id']],'Overlapping source changed');overlaps+=1
        by_id[unit['id']]=unit
    require(overlaps==37 and len(by_id)==2650,'Wrong overlapping page accounting')
    return sorted(by_id.values(),key=lambda u:(u['page'],u['order'],u['id']))


TABLE_KEYS=('credit_exposure','market_var','average_interest','currency','treasury','liquidity','bof_movement','capital')


def risk_native_reading(units,transcript):
    from decimal import Decimal
    lookup={(u['page'],u['order']):u for u in units}
    require(len(lookup)==len(units),'Mixed native/OCR orders require a separate review')
    def q(page,line):
        u=lookup[page,line];return {'id':u['id'],'quote':u['raw']}
    def qs(page,first,last):return [q(page,i) for i in range(first,last+1)]
    def value(u,unit):
        raw=''.join(u['raw'].split());number=None
        if raw!='-':
            token=raw.rstrip('%');number=str(Decimal('-'+token[1:-1] if token.startswith('(') else token))
        return {'id':u['id'],'quote':u['raw'],'value':number,
            'status':'DASH_UNKNOWN' if raw=='-' else 'SOURCE_NUMBER','unit':'PERCENT' if raw.endswith('%') else unit}
    def block(page,start,end,xmin=None):
        selected=[u for u in units if u['page']==page and start<=u['order']<=end and (xmin is None or u['bbox'][0]>xmin)]
        ys={}
        for u in selected:ys.setdefault(round(u['bbox'][1],1),[]).append(u)
        return [sorted(group,key=lambda u:u['bbox'][0]) for _,group in sorted(ys.items())]
    def ordinary_rows(page,start,end,label_start,count,unit):
        cols=block(page,start,end); require(len(cols)==count,'Wrong table row grouping')
        return [{'label_sources':[q(page,label_start+i)],'cells':[value(u,unit) for u in row]} for i,row in enumerate(cols)]
    credit=[{'label_sources':[q(161,11+i)],'cells':[value(lookup[161,25+i],'EUR thousands'),value(lookup[161,37+i],'EUR thousands')]} for i in range(12)]
    credit.append({'label_sources':[],'label':'TOTAL (unlabelled source row)','cells':[value(lookup[161,i],'EUR thousands') for i in (49,50)]})
    var=[{'label_sources':[q(164,15+i)],'cells':[value(u,'EUR thousands') for u in row]} for i,row in enumerate(block(164,22,31))]
    require(len(var)==5 and all(len(r['cells'])==2 for r in var),'VaR row grouping')
    avg=[]
    for label,indices in [(20+i,[24+i,28+i,32+i,36+i,40+i,44+i]) for i in range(4)]+[(48,[49,50,51,52,53,54])]+[(55+i,[58+i,61+i,64+i,67+i,70+i,73+i]) for i in range(3)]+[(76,[77,78,79,80,81,82]),(87,[83,84,85,86])]:
        avg.append({'label_sources':[q(165,label)],'cells':[value(lookup[165,i],'EUR thousands') for i in indices],
            'column_positions':[1,2,4,5] if label==87 else list(range(6))})
    fx_labels=[[104],[106],[108],[110],[111,112],[151],[160],[169],[178],[239],[195],[204],[213],[222],[]]
    fx=[]
    for label_ids in fx_labels:
        if label_ids:y=lookup[165,label_ids[0]]['bbox'][1]
        else:y=lookup[165,231]['bbox'][1]
        candidates=[u for u in units if u['page']==165 and 96<=u['order']<=238 and u['bbox'][0]>165 and abs(u['bbox'][1]-y)<1]
        candidates=sorted(candidates,key=lambda u:u['bbox'][0]);require(len(candidates)==8,'Currency row needs8values: '+str(label_ids))
        fx.append({'label_sources':[q(165,i) for i in label_ids],'label':None if label_ids else 'TOTAL (unlabelled source row)',
            'cells':[value(u,'EUR thousands') for u in candidates]})
    treasury=[{'label_sources':[q(166,i)],'cells':[value(lookup[166,j],'EUR million') for j in (i+1,i+2)]} for i in (7,10,13,16,19,22)]
    liquidity=[{'label_sources':[q(166,33)],'cells':[value(lookup[166,j],'EUR million') for j in (36,37)]}]
    liquidity += [{'label_sources':[q(166,i)],'cells':[value(lookup[166,j],'EUR million') for j in (i+1,i+2)]} for i in (38,41,44,47)]
    bof=[{'label_sources':[q(168,24+i)],'cells':[value(lookup[168,j],'EUR million') for j in (33+i,42+i)]} for i in range(9)]
    bof += [{'label_sources':[q(168,51)],'cells':[value(lookup[168,j],'EUR million') for j in (52,53)]}]
    cap_spec=[([6],[7,38]),([8],[9,10]),([11],[12,13]),([14],[15,16]),([17],[18,19]),([20],[21,22]),([23],[24,25]),([26],[27,28]),
        ([31,32],[29,30]),([33],[39,40]),([34],[41,42]),([35,36],[43,44]),([37],[45,46]),([47],[48,49]),([50],[51,52]),
        ([53],[54,55]),([56],[57,58]),([85,86],[59,60]),([61],[62,63]),([64],[65,66]),([67],[68,69]),([88,70],[71,72]),
        ([73,74],[75,76]),([77,79],[81,83]),([78,80],[82,84])]
    capital=[{'label_sources':[q(169,j) for j in labels],'cells':[value(lookup[169,j],'EUR million') for j in values]} for labels,values in cap_spec]
    def table(page,headers,rows,unit):return {'headers':[q(page,i) for i in headers],'rows':rows,'unit':unit}
    tables={'credit_exposure':table(161,[9,10,23,24],credit,'EUR thousands'),
        'market_var':table(164,[14,20,21],var,'EUR thousands'),
        'average_interest':table(165,list(range(1,20)),avg,'EUR thousands;rates in percent'),
        'currency':table(165,[90,91,92,93,94,95,102,103,113,114,115,116,117,118,119,240],fx,'EUR thousands'),
        'treasury':table(166,[4,5,6],treasury,'EUR million'),
        'liquidity':table(166,[32,34,35],liquidity,'EUR million'),
        'bof_movement':table(168,list(range(16,24))+[54],bof,'EUR million'),
        'capital':table(169,[1,2,3,4,5,87,89,90],capital,'EUR million;ratios in percent')}
    for key,t in tables.items():
        width=6 if key=='average_interest' else 8 if key=='currency' else 2
        t['column_dates']=['2010-06-30']*(width//2)+['2009-12-31']*(width//2)
    sections={
        'risk_scope':{'sources':qs(160,19,28),'reading':'Report names credit,market,liquidity and operational risk.'},
        'credit':{'sources':qs(160,29,34)+qs(161,1,9),'reading':'Failure to honour contractual obligations may cause loss; traditional banking and trading counterparty exposures included. CDS net exposure per reference entity is considered; fair-value policy2.4 is a referenced unresolved dependency. Ongoing credit-process teams and regular risk-committee review are reported.',
            'exposure_equals_expected_loss':False,'enforceable_netting_established':False},
        'market':{'sources':qs(164,1,13)+qs(164,32,43),'reading':'ALCO integrates market and balance-sheet management. Trading VaR uses Monte Carlo,99percent confidence,10day horizon,and one-year historical volatilities/correlations; stress testing considers larger losses. Trading VaR33310/32569thousand differs from banking-book duration sensitivity to200bp parallel shift; reported equity effect657/607million.',
            'VaR_is_maximum_loss':False,'parameters_adopted_as_engine_defaults':False,'flow_periods':['Six months ended30June2010','Year ended31December2009']},
        'currency':{'sources':qs(165,88,89)+[q(165,240)],'reading':'Reported currency assets/liabilities; source sign convention asset/(liability). Missing dashes stay unknown.'},
        'liquidity':{'sources':qs(165,241,246)+qs(166,1,3)+qs(166,25,31)+qs(166,50,54),
            'reading':'Funding and liquidation difficulties may create loss. Strategy points to management report; mismatch reports and dynamic coverage are reported. Treasury-gap footnote uses immediate liquidity and short-term interbank assets less interbank debt up to one year. Net buffer excludes pledged over-one-year-loan collateral and applies central-bank haircuts.',
            'source_label_conflict':'p166:l54 calls913million a treasury gap; the preceding table labels it Global liquidity,while first Treasury Gap is8327million negative. Preserve both source labels.',
            'liquidity_sufficiency_verified':False,'collateral_availability_verified':False,
            'authority_reference':'Bank of Portugal Instruction13/2009 reported,not independently verified'},
        'operational':{'sources':qs(166,55,57)+qs(167,1,5),'reading':'Loss from procedures,people,systems or external events; reported identification,monitoring,control and mitigation system,Global Risk Department unit and departmental/subsidiary representatives.'},
        'capital':{'sources':qs(167,6,31)+qs(168,1,15)+[q(168,54),q(169,1),q(169,90)],
            'reading':'Capital growth,supervisory minimums and strategy; Executive Committee sets strategy. Reported IRBF credit/TSA operational authorization from31March2009 under Decree-Laws103/2007 and104/2007. BOF includes specified capital/reserves/profits/noncontrolling/preferences and full deductions for listed losses/assets; associates and expected-loss adjustments at50percent. COF includes eligible subordinated debt and45percent positive equity fair-value reserves,with50percent deductions. COF cannot exceed BOF; LowerTierII limited to50percent BOF. Deductions include prudential amortization of recovered nonperforming-loan assets. Notice11/2008 transition Dec2009–Dec2012 for2008actuarial effects;137million annual inclusion reported.',
            'current_compliance_verified':False,'holder_recovery_established':False},
        'capital_notice_references':{'sources':[q(169,i) for i in (61,64,67)],
            'reading':'Notice5/2007credit,8/2007market and9/2007operational references retained as historical reported dependencies.'}}
    return {'source_groups':{str(p):[q(p,u['order']) for u in units if u['page']==p] for p in PAGES},'tables':tables,'sections':sections,
        'source_context':{'origin':'SUPPLIED_DEVELOPMENT_READING','source_authenticity':'NOT_ESTABLISHED','incorporation_status':'UNRESOLVED',
            'current_law_or_standard_verified':False,'risk_recomputed':False,'all_Note44_covered':False,
            'pending_source_pages':[162,163],'pending_reason':'Mixed native/OCR sector and rating tables require separate image association',
            'dash_imputed_zero':False,'independent_financial_acceptance':False}}


def source_check(reading,units,transcript):
    from decimal import Decimal
    require(len(units)==629 and len({u['id'] for u in units})==629,'Complete629source occurrences required')
    lookup={u['id']:u for u in units};source=reading['risk_native_evidence']
    require(all(u['source_sha256']==PDF and u['visible'] and u['page'] in PAGES for u in units),'Changed source')
    def quotes(value):
        result=[]
        if isinstance(value,dict):
            if 'id' in value and 'quote' in value:
                require(value['id'] in lookup and value['quote']==lookup[value['id']]['raw'],'Changed exact quote');result.append(value['id'])
            for k,v in value.items():
                if k not in ('id','quote'):result+=quotes(v)
        elif isinstance(value,list):
            for item in value:result+=quotes(item)
        return result
    quotes(source);require(set(quotes(source['source_groups']))==set(lookup),'Incomplete page context')
    expected=set()
    for p,a,b in [(160,19,34),(161,1,9),(164,1,13),(164,32,43),(165,88,89),(165,240,246),(166,1,3),(166,25,31),(166,50,57),(167,1,31),(168,1,15),(168,54,54),(169,1,1),(169,61,61),(169,64,64),(169,67,67),(169,90,90)]:
        expected.update(u['id'] for u in units if u['page']==p and a<=u['order']<=b)
    require(set(quotes(source['sections']))==expected,'Missing substantive prose or footnote')
    norm=lambda v:''.join(v.split());amounts=0;unknown=0
    require(set(transcript['tables'])==set(TABLE_KEYS),'Missing table transcript')
    table_checks={}
    for key,t in source['tables'].items():
        typed=transcript['tables'][key];require(len(t['rows'])==len(typed['rows']),'Wrong row count '+key)
        same(t['column_dates'],typed['column_dates'],'Wrong date association '+key)
        for row,typedrow in zip(t['rows'],typed['rows']):
            label=' '.join(x['quote'] for x in row['label_sources']) if row['label_sources'] else row['label']
            require(norm(label)==norm(typedrow[0]),'Wrong label '+key+': '+label)
            require(len(row['cells'])==len(typedrow)-1,'Wrong width '+key)
            centers=[];ys=[]
            for cell,want in zip(row['cells'],typedrow[1:]):
                token=''.join(cell['quote'].split());actual=cell['value'];amounts+=1
                if token=='-':require(actual is None and want=='-' and cell['status']=='DASH_UNKNOWN','Dash imputed');unknown+=1
                else:
                    numeric=token.rstrip('%'); numeric='-'+numeric[1:-1] if numeric.startswith('(') else numeric
                    require(Decimal(actual)==Decimal(numeric)==Decimal(str(want).rstrip('%')),'Image amount mismatch '+key)
                    require((cell['unit']=='PERCENT')==str(want).endswith('%'),'Percent unit mismatch')
                bb=lookup[cell['id']]['bbox'];centers.append((bb[0]+bb[2])/2);ys.append(bb[1])
            require(centers==sorted(centers) and max(ys)-min(ys)<3,'Wrong cell geometry '+key)
            for label in row['label_sources']:require(abs(lookup[label['id']]['bbox'][1]-ys[0])<4,'Wrong label row '+key)
        require([norm(x['quote']) for x in t['headers']]==[norm(x) for x in typed['headers']],'Header/footnote mismatch '+key)
        table_checks[key]={'rows':len(t['rows']),'positions':sum(len(r['cells']) for r in t['rows'])}
    old=read(prior.HERE/'reading.json');same({k:v for k,v in reading.items() if k!='risk_native_evidence'},old,'026reading changed')
    prior.source_check(old,read(prior.HERE/'source-units.json'),read(prior.HERE/'image-transcript.json'))
    all_units=combined_units(units)
    return {'local_occurrences':629,'overlap_occurrences':37,'new_occurrences':592,'total_occurrences':len(all_units),
        'tables':table_checks,'numeric_or_unknown_positions':amounts,'unknown_dashes':unknown,'substantive_occurrences':len(expected),
        'complete_prior_fields_preserved':True,'Note44_complete':False,'pending_pages':[162,163]}


def source_worker():
    units=original_units();transcript=read(HERE/'image-transcript.json');review=HERE/'SOURCE-REVIEW.md'
    require(review.is_file() and len(review.read_text())>1000,'Substantive source review required')
    for item in read(HERE/'images.json'):require(sha(ROOT/item['path'])==item['sha256'],'Source image changed')
    reading=deepcopy(read(prior.HERE/'reading.json'));reading['risk_native_evidence']=risk_native_reading(units,transcript)
    checked=source_check(reading,units,transcript);all_units=combined_units(units)
    save(HERE/'source-units.json',units);save(HERE/'reading.json',reading)
    entry={'document':DOCUMENT,'source':PDF,'reading':compact_digest(reading),'pages_digest':compact_digest(all_units),
        'pages':sorted({u['page'] for u in all_units}),'occurrences':len(all_units),
        'reading_fields':list(read(prior.HERE/'registry-entry.json')['reading_fields'])+['risk_native_evidence']}
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
    save(HERE/'source-check.json',{'status':'PASS',**checked,'baseline_gap':'Native Note44profile unsupported','source_review':common.ref(review)})


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
            'reason':'Complete026plus native Note44; risk units,periods,unknowns and pending OCR coverage remain explicit'},
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
    graph={'units':combined_units(read(HERE/'source-units.json'))}
    changes={
        'credit-is-loss':lambda d:d['sections']['credit'].update(exposure_equals_expected_loss=True),
        'netting-inferred':lambda d:d['sections']['credit'].update(enforceable_netting_established=True),
        'VaR-as-maximum':lambda d:d['sections']['market'].update(VaR_is_maximum_loss=True),
        'model-adopted':lambda d:d['sections']['market'].update(parameters_adopted_as_engine_defaults=True),
        'flow-periods-equal':lambda d:d['sections']['market'].update(flow_periods=['Year2010','Year2009']),
        'liquidity-label-silenced':lambda d:d['sections']['liquidity'].update(source_label_conflict='No discrepancy'),
        'liquidity-sufficient':lambda d:d['sections']['liquidity'].update(liquidity_sufficiency_verified=True),
        'collateral-guaranteed':lambda d:d['sections']['liquidity'].update(collateral_availability_verified=True),
        'capital-compliant':lambda d:d['sections']['capital'].update(current_compliance_verified=True),
        'capital-as-recovery':lambda d:d['sections']['capital'].update(holder_recovery_established=True),
        'operational-omitted':lambda d:d['sections'].pop('operational'),
        'liquidity-footnote-omitted':lambda d:d['sections']['liquidity']['sources'].pop(),
        'unknown-dash-zero':lambda d:d['tables']['bof_movement']['rows'][1]['cells'][0].update(value='0',status='SOURCE_NUMBER'),
        'wrong-monetary-unit':lambda d:d['tables']['treasury']['rows'][0]['cells'][0].update(unit='EUR thousands'),
        'wrong-sign':lambda d:d['tables']['treasury']['rows'][1]['cells'][0].update(value='14057'),
        'row-omitted':lambda d:d['tables']['capital']['rows'].pop(),
        'dates-reversed':lambda d:d['tables']['credit_exposure']['headers'].reverse(),
        'all-note-covered':lambda d:d['source_context'].update(all_Note44_covered=True),
        'pending-pages-erased':lambda d:d['source_context'].update(pending_source_pages=[]),
        'risk-recomputed':lambda d:d['source_context'].update(risk_recomputed=True),
        'current-law-verified':lambda d:d['source_context'].update(current_law_or_standard_verified=True),
        'incorporation-assumed':lambda d:d['source_context'].update(incorporation_status='CONFIRMED')}
    rows=[]
    for name,change in changes.items():
        bad=supplied(graph);change(bad['reading']['risk_native_evidence'])
        try:cells.admit(graph,bad)
        except ValueError as exc:rows.append({'case':name,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else:raise ValueError('Altered interpretation accepted: '+name)
    for name in ('missing-page','source-hash','geometry','duplicate-page-occurrence'):
        g=deepcopy(graph)
        if name=='missing-page':g['units']=[u for u in g['units'] if u['page']!=169]
        elif name=='source-hash':g['units'][-1]['source_sha256']='0'*64
        elif name=='geometry':g['units'][-1]['bbox'][0]+=1
        else:g['units'].append(deepcopy(next(u for u in g['units'] if u['page']==160)))
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
    require(digest(before)==previous['answer_sha256'],'Complete026baseline answer changed')
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
    for key in baseline_reading: same(before['source_statement_cells'][key],after['source_statement_cells'][key],'Lost026field '+key)
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
          24:'h1_cross_note_consumer',25:'h1_securitisation_consumer',26:'h1_fair_value_consumer'}
    for n,key in keys.items():
        receipt=read(BASE/f'attempt-{n:03d}/ordinary.json.gz')
        answer={**before,**receipt['replacements'],'source_statement_cells':receipt['addition']}
        require(digest(answer)==receipt['answer_sha256'],'Complete prior answer changed: '+str(n))
        composed[key]=answer
        require(digest(composed)==receipt['full_composed_sha256'],'Complete prior composition changed: '+str(n))
    composed['h1_risk_native_consumer']=after
    receipt={'status':'PASS','prior_complete_answer_sha256':digest(before),'answer_sha256':digest(after),
        'prior_full_composed_sha256':previous['full_composed_sha256'],'full_composed_sha256':digest(composed),
        'reading_sha256':compact_digest(reading),'replacements':replacements,'addition':body,'controls':cases,
        'source_check':checked,'imports':imported,'whole_task_complete':False,'source_truth_established':False,
        'recipe':'Reconstruct026from007; reconstruct021through026 and016/017 retained compositions; add027as h1_risk_native_consumer'}
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
        elif change=='changed_p2': p2['source_statement_cells']['reading']['risk_native_evidence']['source_context']['risk_recomputed']=True
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
    rows.append({'requirement':'Note44 native credit/market/liquidity/operational/capital disclosures; OCR162–163 remain',
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
        status=('RETAINED_FINITE_INTEGRATION' if number in (10,21,32,35,42,43) else
                'THIS_ATTEMPT_SUBJECT_TO_STAGE_RESULTS' if number==44 else
                'RETAINED_SUPPLEMENT_ONLY' if number in (11,12,28,36,37,38) else
                'SOURCE_RETAINED_FULL_INTERPRETATION_NOT_ESTABLISHED')
        inventory.append({'note':number,'page':u['page'],'id':u['id'],'quote':raw,'status':status})
    save(HERE/'note-inventory.json',{'scope':'Native original headings61–171; heading detection alone is not semantic coverage',
        'notes':inventory,'policies':{'2.2':'RETAINED_FINITE_INTEGRATION','2.8':'RETAINED_FINITE_INTEGRATION','2.9':'RETAINED_FINITE_INTEGRATION',
        '2.15':'RETAINED_SUPPLEMENT_ONLY','remaining':'NOT_FULLY_INTERPRETED'},
        'task_acceptance':False})
    save(HERE/'requirements.json',{'rows':rows,'original_task_acceptance':False,'external_adviser_opinion_required':False,
        'next_discriminating_work':'Next original dependency is Note44sector/rating OCR tables162–163; distinguish source IDs from repeated order values,inspect images and repair associations without treating OCR as ground truth. Keep all original authority and wider source gaps.'})


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
        elif name=='tests': command('tests',[str(ROOT/'.venv/bin/python'),'-B','-m','pytest','-q',*TESTS,'--junitxml='+str(HERE/'tests.xml')],200)
        else:
            python=read(PREP/'config.json')['package_python'] if name=='installed' else str(ROOT/'.venv/bin/python')
            command(name,[python,'-I','-B',str(ROOT/SELF),'worker-'+name],200)
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
    (HERE/'RESULT.md').write_text('# Original native risk-disclosure integration\n\n'+('Finite source/consumer integration passed. ' if passed else 'Campaign did not pass. ')
        +'Actual stages: '+json.dumps(outcomes)+'.\n\n'
        +'Native Note44tables and prose retain credit exposure,market VaR,interest periods,currency,liquidity,operational risk and capital. '
        +'Mixed units,printed dashes,historical authority references and the conflicting treasury-gap label remain explicit. '
        +'Sector/rating OCRtables162–163 remain pending; no whole-Note44acceptance is claimed. '
        +'Complete026and all prior compositions remain checked and preserved.\n\n'
        +'|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|\n|---|---|---|---|---|---|\n'
        +'|'+('Retain finite integration' if passed else 'Retain actual failure')+'|Original images/quotes/geometry and actual full normal/installed answers|See stage records|Remaining notes and authority|Record/refresh; review OCR162–163and remaining coverage|Financial truth,current law,holder entitlement,automatic extraction,whole build|\n\n'
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
