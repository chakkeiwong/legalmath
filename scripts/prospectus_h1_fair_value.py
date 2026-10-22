"""Bounded original Note43 fair-value source and answer delivery."""
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
from scripts import prospectus_h1_securitisation as prior
from scripts import prospectus_h1_statement_consumer as common

read, save, sha, digest = prior.read, prior.save, prior.sha, prior.digest
compact_digest, same, require, rel = prior.compact_digest, prior.same, prior.require, prior.rel
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
BASE = AUTH / 'attempts/source-bes-dep-05'
PREP = AUTH / 'reviews/h1-fair-value-389'
HERE = BASE / 'attempt-026'
SELF = 'scripts/prospectus_h1_fair_value.py'
PLAN = 'docs/plans/prospectus-h1-fair-value-2026-10-21.md'
PRODUCTION = prior.PRODUCTION
PROFILE = 'bes-h1-2010-statements-fair-value.v6'
DOCUMENT, PDF = prior.DOCUMENT, prior.PDF
PAGES = (159, 160)
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
    paths.add(AUTH/'revisions/0389.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH/'program.json').stat().st_size-start['program_bytes'])
    seconds = sum(read(p)['wall_seconds'] for d in (PREP, HERE) for p in d.glob('commands/*.json'))
    return {'new_bytes': size, 'new_measured_seconds': seconds, 'new_control_seconds': 60,
        'prior_known_bytes': start['prior_known_bytes'], 'prior_known_seconds': start['prior_known_seconds'],
        'known_cumulative_bytes': start['prior_known_bytes']+size,
        'known_cumulative_seconds': start['prior_known_seconds']+seconds+60,
        'earlier_manual_and_unmeasured_costs': 'UNKNOWN; history retained',
        'execution_allowed': size+reserve < 98*1024**2 and seconds < 660}


def prepare():
    tick=time.monotonic(); auth=authority(); old=read(AUTH/'program.json')
    require(old['revision']==388 and not PREP.exists() and not HERE.exists(),'Fresh388 required')
    events=auth.events()
    attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e['budget_key']=='source-bes-dep-05']
    require(len(attempts)==old['budgets']['source-bes-dep-05']['maximum_new_attempts']==25,'Retain25attempts')
    require(read(prior.HERE/'result.json')['status']=='PASS','025 must pass')
    protected={}
    for n in (7,15,16,17,21,22,23,24,25):
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
        rel(prior.HERE/'image-transcript.json'),rel(prior.HERE/'images/page-159.png'),
        rel(prior.HERE/'images.json'),rel(prior.HERE/'registry-entry.json')]
    protected.update({n:sha(ROOT/n) for n in names})
    protected.update({n:h for n,h in production.items() if n!=PRODUCTION})
    require(all(sha(ROOT/n)==h for n,h in protected.items()),'Stale inherited binding')
    save(PREP/'freeze.json',{'bindings':protected,'baseline_sha256':sha(ROOT/PRODUCTION),
        'mutable_file':PRODUCTION,'implementation_window':'Once after reviewed source and candidate freeze'})
    config=read(prior.PREP/'config.json'); require(sha(config['package_python'])==config['python_sha256'],'Build interpreter changed')
    save(PREP/'config.json',config)
    new=deepcopy(old);new['revision']=389
    task=next(t for t in new['tasks'] if t['id']=='source-bes-dep-05')
    task.update(dossier=PLAN,pre_admission_review=PLAN,build_criteria_scope=[],
        reason='Deliver original Note43 complete dated values and valuation assumptions; preserve025 and distinguish source estimate from legal recovery')
    task['inputs']=sorted((set(task['inputs'])-{PRODUCTION})|set(protected)|{rel(PREP/'freeze.json'),rel(PREP/'config.json')})
    bounds={'measured_seconds':660,'control_seconds':60,'new_bytes':100*1024**2,'failure_reserve':2*1024**2,
        'previous_known_bytes':previous['known_cumulative_bytes'],'previous_known_seconds':previous['known_cumulative_seconds'],'unchanged_retries':0}
    task['fair_value_evidence']={'version':PROFILE,'freeze':rel(PREP/'freeze.json'),'bounds':bounds,
        'success_dependencies':DEPENDENCIES,'original_task_acceptance':False}
    new['budgets']['source-bes-dep-05']['maximum_new_attempts']=26
    routes=read(ROOT/old['continuation_review']['routes']); routes['baseline_revision']=389
    for row in routes['tasks']:
        if row['task']==task['id']:
            row.update(task_sha256=compact_digest(task),dossier=PLAN,phase=0,
                remaining='025consolidation integration complete; Note43 and wider source/authority remain.',
                next_action='Execute026 full Note43 source/normal/installed delivery and adverse controls; record,refresh and continue original coverage.',
                stop_condition='26 retained admissions;660+60seconds and100MiB new; no unchanged retry; retain cumulative costs/failures.')
    save(PREP/'routes.json',routes)
    new['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    new['continuation_review']['bindings'].pop(PRODUCTION,None)
    new['continuation_review']['bindings'].update({n:sha(ROOT/n) for n in
        (PLAN,rel(PREP/'routes.json'),rel(PREP/'freeze.json'),rel(PREP/'baseline/statement_cells.py'))})
    require(old['obligations']==new['obligations'] and old['build_contract']==new['build_contract'],'Scope changed')
    raw=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
    source_bytes=sum(p.stat().st_size for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    forecast=costs()['new_bytes']+2*len(raw)+3*source_bytes+10*1024**2
    require(forecast<98*1024**2,'Forecast exceeds reservation')
    with (PREP/'proposal.json').open('xb') as stream:stream.write(raw)
    from legalmath.prospectus.execution_authority import digest as adigest
    save(PREP/'review.json',{'baseline':adigest(old),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Complete Note43 values and all valuation assumptions; preserve complete025','Deduplicate overlapping page159 with equality checks','Retain25admissions and all original obligations'],
        'skeptical_audit':{'verdict':'PASS','plan':PLAN,'forecast_new_bytes':forecast,
            'no_proxy_promotion':'Table image/geometry and actual consumers; arithmetic and exact hashes do not prove fair value or recovery'},
        'evidence_contract':{'question':'Does complete Note43 reach the answer with correct date alignment and all assumptions?',
            'primary':'Independent image transcript, original geometry/quotes, prior preservation and normal/installed corruption refusals',
            'promotion_veto':['Wrong date/amount/unit','Omitted clause','Lost prior answer','Conflicting duplicate','Wrong import','Accepted corruption'],
            'continuation_veto':['Invalid authority','Corrupt shared originals','Spent resources'],
            'not_concluded':['Automatic extraction','Verified valuation','Holder recovery','Current law','Whole build']},
        'budget_revision':{'budget_key':'source-bes-dep-05','previous_maximum':25,'new_maximum':26,
            'retained_attempts':attempts,'reason':'Original Note43 dependency; no replay of025',
            'next_discriminating_check':'Source date geometry, reported approximation versus differing values, complete downstream delivery',
            'stop_condition':bounds,'same_scope_authorization':'Recover and continue original build'}})
    save(PREP/'commands/preparation.json',{'wall_seconds':time.monotonic()-tick,
        'command':[sys.executable,'-B','-m','scripts.prospectus_h1_fair_value','prepare']})
    return {'status':'PREPARED','revision':389,'forecast_new_bytes':forecast,'resources':costs()}


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
    require(sha(BASE/'attempt-001/interim.pdf')==PDF,'Wrong original PDF')
    (HERE/'images').mkdir()
    source=prior.HERE/'images/page-159.png'
    expected=next(x for x in read(prior.HERE/'images.json') if x['page']==159)
    require(sha(source)==expected['sha256'],'Retained159 image changed')
    shutil.copyfile(source,HERE/'images/page-159.png')
    command('render-160',['pdftoppm','-f','160','-l','160','-r','160','-singlefile','-png',
        str(BASE/'attempt-001/interim.pdf'),str(HERE/'images/page-160')],60)
    save(HERE/'images.json',[{'page':p,'path':rel(HERE/'images'/f'page-{p}.png'),
        'sha256':sha(HERE/'images'/f'page-{p}.png'),'origin':'REUSED_CHECKED025' if p==159 else 'ORIGINAL_RENDER'} for p in PAGES])


def original_units():
    products = read(BASE/'attempt-007/products.json.gz')
    return sorted([u for u in products['P1']['payload']['graph']['units']
        if u['document']==DOCUMENT and u['page'] in PAGES], key=lambda u: (u['page'],u['order'],u['id']))


def combined_units(units):
    by_id={}
    for folder in (BASE/'attempt-015',BASE/'attempt-022',BASE/'attempt-023',BASE/'attempt-024',prior.HERE):
        for unit in read(folder/'source-units.json'):
            if unit['id'] in by_id:same(unit,by_id[unit['id']],'Conflicting prior occurrence')
            by_id[unit['id']]=unit
    require(len(by_id)==2021,'Wrong025 occurrence count')
    overlaps=0
    for unit in units:
        if unit['id'] in by_id:
            same(unit,by_id[unit['id']],'Overlapping source changed');overlaps+=1
        by_id[unit['id']]=unit
    require(overlaps==128 and len(by_id)==2058,'Wrong overlapping page accounting')
    return sorted(by_id.values(),key=lambda u:(u['page'],u['order'],u['id']))


def fair_value_reading(units):
    lookup={(u['page'],u['order']):u for u in units}
    def q(page,line):
        u=lookup[page,line];return {'id':u['id'],'quote':u['raw']}
    def qs(page,first,last):return [q(page,i) for i in range(first,last+1)]
    def number(line):
        quote=q(159,line);token=''.join(quote['quote'].split())
        return {**quote,'value':int(token),'status':'SOURCE_NUMBER','unit':'EUR thousands'}
    def row(label,indices):return {'label':q(159,label),'cells':[number(i) for i in indices]}
    rows=[row(25+i,[34+i,43+i,52+i,61+i]) for i in range(9)]
    rows+=[row(70,[71,72,73,74])]
    rows+=[row(75+i,[82+i,89+i,96+i,103+i]) for i in range(7)]
    rows+=[row(110,[111,112,113,114])]
    arithmetic=[]
    for start,end,total in ((0,9,9),(10,17,17)):
        arithmetic.append({'section':'financial_assets' if start==0 else 'financial_liabilities',
            'computed_sums':[sum(rows[i]['cells'][c]['value'] for i in range(start,end)) for c in range(4)],
            'reported_totals':[v['value'] for v in rows[total]['cells']],
            'residuals':[rows[total]['cells'][c]['value']-sum(rows[i]['cells'][c]['value'] for i in range(start,end)) for c in range(4)]})
    return {'source_groups':{str(p):[q(p,u['order']) for u in units if u['page']==p] for p in PAGES},
        'heading':qs(159,16,17),'table':{'unit':q(159,18),'date_groups':[q(159,20),q(159,19)],
            'column_headers':qs(159,21,24),'column_dates':['2010-06-30','2010-06-30','2009-12-31','2009-12-31'],
            'column_measures':['BOOK_VALUE','FAIR_VALUE','BOOK_VALUE','FAIR_VALUE'],'rows':rows,
            'date_alignment_basis':'Original page image and x coordinates; native header order is reversed'},
        'methods':{
            'fair_value_methodology_reference':{'sources':qs(159,115,116),'referenced_period':'Year ended31December2009',
                'reference_status':'NAMED_UNRESOLVED_DEPENDENCY; annual2009methodology not verified by this note'},
            'amortised_cost_scope':{'sources':qs(159,117,118),'scope':'Following methods estimate fair values of instruments measured at amortised cost in the balance sheet'},
            'cash_and_bank_assets':{'sources':qs(159,119,121),'method':'Short-term nature makes carrying value a reasonable estimate of fair value',
                'exact_equality_asserted':False},
            'customer_loans':{'sources':qs(159,122,125)+qs(160,1,2),
                'method':'Discount expected future capital and interest cash flows assuming contractual instalment dates',
                'grouping':'Loans with similar credit risk characteristics estimated collectively',
                'discount_rate':'Current rates used for loans with similar characteristics','default_free_or_recovery_guaranteed':False},
            'held_to_maturity':{'sources':qs(160,3,5),'method':'Quoted market prices when available; for unlisted securities discount expected future cash flows'},
            'bank_deposit_liabilities':{'sources':qs(160,6,8),'method':'Short-term nature makes carrying value a reasonable estimate of fair value',
                'exact_equality_asserted':False},
            'customer_deposits':{'sources':qs(160,9,15),'method':'Discount expected capital and interest assuming contractual instalment dates using current rates for similar instruments',
                'reported_assumptions':"Floating interest rates and maturity substantially below one year support the report's not-significant-difference statement",
                'every_instrument_verified':False},
            'issued_and_subordinated_debt':{'sources':qs(160,16,18),
                'method':'Market prices when available; otherwise discounted expected future cash flows'}},
        'source_comparisons':{'arithmetic_role':'EXPLANATORY_ONLY','totals':arithmetic,
            'bank_deposits_book_minus_fair':[rows[12]['cells'][i]['value']-rows[12]['cells'][i+1]['value'] for i in (0,2)],
            'reported_approximation_is_not_exact_equality':True,
            'book_minus_fair_is_holder_recovery_or_realised_gain':False},
        'source_context':{'origin':'SUPPLIED_DEVELOPMENT_READING','source_authenticity':'NOT_ESTABLISHED',
            'incorporation_status':'UNRESOLVED','current_law_or_standard_verified':False,
            'valuation_recomputed':False,'discount_rates_supplied':False,'IFRS_hierarchy_inferred':False,
            'holder_rights_or_recovery_established':False,'note44_context_only':True}}


def source_check(reading,units,transcript):
    require(len(units)==165 and len({u['id'] for u in units})==165,'Complete165occurrences required')
    lookup={u['id']:u for u in units}; source=reading['fair_value_evidence']
    require(all(u['source_sha256']==PDF and u['visible'] and u['page'] in PAGES for u in units),'Changed source')
    def quotes(value):
        result=[]
        if isinstance(value,dict):
            if 'id' in value and 'quote' in value:
                require(value['id'] in lookup and value['quote']==lookup[value['id']]['raw'],'Changed exact quote')
                result.append(value['id'])
            for k,v in value.items():
                if k not in ('id','quote'):result+=quotes(v)
        elif isinstance(value,list):
            for item in value:result+=quotes(item)
        return result
    quotes(source)
    require(set(quotes(source['source_groups']))==set(lookup),'Incomplete contextual coverage')
    expected={u['id'] for u in units if (u['page']==159 and 115<=u['order']<=125) or (u['page']==160 and 1<=u['order']<=18)}
    require(set(quotes(source['methods']))==expected,'Incomplete valuation assumptions')
    table=source['table']; norm=lambda v:''.join(v.split())
    require(len(table['rows'])==len(transcript['rows'])==18,'Incomplete fair-value rows')
    same([norm(x['quote']) for x in table['date_groups']],[norm(x) for x in transcript['date_groups']],'Wrong dates')
    same([norm(x['quote']) for x in table['column_headers']],[norm(x) for x in transcript['column_headers']],'Wrong measures')
    require(norm(table['unit']['quote'])==norm(transcript['unit']),'Wrong units')
    dates=[lookup[q['id']]['bbox'] for q in table['date_groups']]
    require(dates[0][0]<dates[1][0],'Date groups reversed')
    for row,typed in zip(table['rows'],transcript['rows']):
        require(norm(row['label']['quote'])==norm(typed[0]),'Wrong row label')
        same([c['value'] for c in row['cells']],typed[1:],'Image/numeric disagreement')
        geometry=[lookup[q['id']]['bbox'] for q in [row['label']]+row['cells']]
        centers=[(b[0]+b[2])/2 for b in geometry];ys=[b[1] for b in geometry]
        require(centers==sorted(centers) and max(ys)-min(ys)<3,'Wrong row/column association')
        require(centers[1]<(dates[0][0]+dates[0][2])/2<centers[2] and centers[3]<(dates[1][0]+dates[1][2])/2<centers[4],'Wrong group geometry')
        require(all(int(''.join(c['quote'].split()))==c['value'] for c in row['cells']),'Number differs from exact quote')
        require(all(c['unit']=='EUR thousands' and c['status']=='SOURCE_NUMBER' for c in row['cells']),'Wrong numeric unit/status')
    old=read(prior.HERE/'reading.json');same({k:v for k,v in reading.items() if k!='fair_value_evidence'},old,'025reading changed')
    prior.source_check(old,read(prior.HERE/'source-units.json'),read(prior.HERE/'image-transcript.json'))
    combined=combined_units(units)
    return {'local_occurrences':165,'overlap_occurrences':128,'new_occurrences':37,'total_occurrences':len(combined),
        'table_rows':18,'numeric_positions':72,'method_occurrences':len(expected),'all_prior_fields_preserved':True,
        'date_groups_checked_against_image_geometry':True,'arithmetic_role':'EXPLANATORY_ONLY',
        'totals_residuals':[x['residuals'] for x in source['source_comparisons']['totals']]}


def source_worker():
    units=original_units();transcript=read(HERE/'image-transcript.json');review=HERE/'SOURCE-REVIEW.md'
    require(review.is_file() and len(review.read_text())>1000,'Substantive source review required')
    for item in read(HERE/'images.json'):require(sha(ROOT/item['path'])==item['sha256'],'Source image changed')
    reading=deepcopy(read(prior.HERE/'reading.json'));reading['fair_value_evidence']=fair_value_reading(units)
    checked=source_check(reading,units,transcript);all_units=combined_units(units)
    save(HERE/'source-units.json',units);save(HERE/'reading.json',reading)
    entry={'document':DOCUMENT,'source':PDF,'reading':compact_digest(reading),'pages_digest':compact_digest(all_units),
        'pages':sorted({u['page'] for u in all_units}),'occurrences':len(all_units),
        'reading_fields':list(read(prior.HERE/'registry-entry.json')['reading_fields'])+['fair_value_evidence']}
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
    save(HERE/'source-check.json',{'status':'PASS',**checked,'baseline_gap':'Complete Note43profile unsupported','source_review':common.ref(review)})


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
            'reason':'Complete025plus Note43; source dates,valuation assumptions and prior limits remain explicit'},
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
        'date-order-reversed':lambda d:d['table']['date_groups'].reverse(),
        'column-dates-reversed':lambda d:d['table']['column_dates'].reverse(),
        'measures-reversed':lambda d:d['table']['column_measures'].reverse(),
        'row-omitted':lambda d:d['table']['rows'].pop(),
        'fair-as-book':lambda d:d['table']['rows'][6]['cells'].__setitem__(0,d['table']['rows'][6]['cells'][1]),
        'wrong-unit':lambda d:d['table']['rows'][0]['cells'][0].update(unit='EUR million'),
        'date-quote-changed':lambda d:d['table']['date_groups'][0].update(quote='30.06.2009'),
        'cross-page-assumption-lost':lambda d:d['methods']['customer_loans']['sources'].pop(),
        'contractual-payment-lost':lambda d:d['methods']['customer_loans'].update(method='Assume immediate payment'),
        'credit-grouping-lost':lambda d:d['methods']['customer_loans'].update(grouping='All loans treated identically'),
        'discount-rate-invented':lambda d:d['methods']['customer_loans'].update(discount_rate='5 percent'),
        'default-free-assumed':lambda d:d['methods']['customer_loans'].update(default_free_or_recovery_guaranteed=True),
        'market-fallback-lost':lambda d:d['methods']['held_to_maturity'].update(method='All securities have quoted prices'),
        'deposit-equality-assumed':lambda d:d['methods']['bank_deposit_liabilities'].update(exact_equality_asserted=True),
        'all-customers-verified':lambda d:d['methods']['customer_deposits'].update(every_instrument_verified=True),
        'debt-method-lost':lambda d:d['methods'].pop('issued_and_subordinated_debt'),
        'annual-methodology-resolved':lambda d:d['methods']['fair_value_methodology_reference'].update(reference_status='VERIFIED'),
        'difference-as-recovery':lambda d:d['source_comparisons'].update(book_minus_fair_is_holder_recovery_or_realised_gain=True),
        'valuation-recomputed':lambda d:d['source_context'].update(valuation_recomputed=True),
        'hierarchy-invented':lambda d:d['source_context'].update(IFRS_hierarchy_inferred=True),
        'current-law-verified':lambda d:d['source_context'].update(current_law_or_standard_verified=True),
        'incorporation-assumed':lambda d:d['source_context'].update(incorporation_status='CONFIRMED')}
    rows=[]
    for name,change in changes.items():
        bad=supplied(graph);change(bad['reading']['fair_value_evidence'])
        try:cells.admit(graph,bad)
        except ValueError as exc:rows.append({'case':name,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else:raise ValueError('Altered interpretation accepted: '+name)
    for name in ('missing-page','source-hash','geometry','duplicate-page-occurrence'):
        g=deepcopy(graph)
        if name=='missing-page':g['units']=[u for u in g['units'] if u['page']!=160]
        elif name=='source-hash':g['units'][-1]['source_sha256']='0'*64
        elif name=='geometry':g['units'][-1]['bbox'][0]+=1
        else:g['units'].append(deepcopy(next(u for u in g['units'] if u['page']==159)))
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
    require(digest(before)==previous['answer_sha256'],'Complete025baseline answer changed')
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
    for key in baseline_reading: same(before['source_statement_cells'][key],after['source_statement_cells'][key],'Lost025field '+key)
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
          24:'h1_cross_note_consumer',25:'h1_securitisation_consumer'}
    for n,key in keys.items():
        receipt=read(BASE/f'attempt-{n:03d}/ordinary.json.gz')
        answer={**before,**receipt['replacements'],'source_statement_cells':receipt['addition']}
        require(digest(answer)==receipt['answer_sha256'],'Complete prior answer changed: '+str(n))
        composed[key]=answer
        require(digest(composed)==receipt['full_composed_sha256'],'Complete prior composition changed: '+str(n))
    composed['h1_fair_value_consumer']=after
    receipt={'status':'PASS','prior_complete_answer_sha256':digest(before),'answer_sha256':digest(after),
        'prior_full_composed_sha256':previous['full_composed_sha256'],'full_composed_sha256':digest(composed),
        'reading_sha256':compact_digest(reading),'replacements':replacements,'addition':body,'controls':cases,
        'source_check':checked,'imports':imported,'whole_task_complete':False,'source_truth_established':False,
        'recipe':'Reconstruct025from007and frozen profile; reconstruct021through025from retained receipts; preserve016/017 and all compositions; add026as h1_fair_value_consumer'}
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
        elif change=='changed_p2': p2['source_statement_cells']['reading']['fair_value_evidence']['source_context']['valuation_recomputed']=True
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
    rows.append({'requirement':'Complete Note43 dated book/fair values and all valuation assumptions',
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
        status=('RETAINED_FINITE_INTEGRATION' if number in (10,21,32,35,42) else
                'THIS_ATTEMPT_SUBJECT_TO_STAGE_RESULTS' if number==43 else
                'RETAINED_SUPPLEMENT_ONLY' if number in (11,12,28,36,37,38) else
                'SOURCE_RETAINED_FULL_INTERPRETATION_NOT_ESTABLISHED')
        inventory.append({'note':number,'page':u['page'],'id':u['id'],'quote':raw,'status':status})
    save(HERE/'note-inventory.json',{'scope':'Native original headings61–171; heading detection alone is not semantic coverage',
        'notes':inventory,'policies':{'2.2':'RETAINED_FINITE_INTEGRATION','2.8':'RETAINED_FINITE_INTEGRATION','2.9':'RETAINED_FINITE_INTEGRATION',
        '2.15':'RETAINED_SUPPLEMENT_ONLY','remaining':'NOT_FULLY_INTERPRETED'},
        'task_acceptance':False})
    save(HERE/'requirements.json',{'rows':rows,'original_task_acceptance':False,'external_adviser_opinion_required':False,
        'next_discriminating_work':'Next original dependency is Note44risk management beginning160; map its end before admission. Annual2009fair-value methodology remains unresolved; preserve historical authority/incorporation gaps and follow original inventory without replaying completed installs.'})


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
    (HERE/'RESULT.md').write_text('# Original fair-value note integration\n\n'+('Finite source/consumer integration passed. ' if passed else 'Campaign did not pass. ')
        +'Actual stages: '+json.dumps(outcomes)+'.\n\n'
        +'The complete Note43 reading preserves eighteen table rows,72numeric positions,the original date groups and all six amortised-cost methods. '
        +'Historical methodology reference,contractual timing,credit-risk grouping,current similar-instrument rates and market-price fallbacks remain explicit. '
        +'Reported estimates do not establish exact equality,verified valuation or creditor recovery. '
        +'All025fields and016/017/021through025compositions are retained through checked lossless recipes.\n\n'
        +'|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|\n|---|---|---|---|---|---|\n'
        +'|'+('Retain finite integration' if passed else 'Retain actual failure')+'|Original images/quotes/geometry and actual full normal/installed answers|See stage records|Remaining notes and authority|Record/refresh; read Note44and remaining coverage|Financial truth,current law,holder entitlement,automatic extraction,whole build|\n\n'
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
