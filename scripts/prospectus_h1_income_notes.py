"""Bounded original interest, fee and administrative-expense note delivery."""
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
from scripts import prospectus_h1_basis_policy as prior
from scripts import prospectus_h1_statement_consumer as common
from scripts import prospectus_h1_income_notes_mapping as mapping
from scripts import prospectus_h1_income_notes_tables as table_support
delivery=prior

read, save, sha, digest = prior.read, prior.save, prior.sha, prior.digest
compact_digest, same, require, rel = prior.compact_digest, prior.same, prior.require, prior.rel
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
BASE = AUTH / 'attempts/source-bes-dep-05'
PREP = AUTH / 'reviews/h1-income-notes-412'
HERE = BASE / 'attempt-049'
SELF = 'scripts/prospectus_h1_income_notes.py'
PLAN = 'docs/plans/prospectus-h1-income-notes-2026-10-21.md'
READING = 'reading.json.gz'
PRODUCTION = prior.PRODUCTION
PROFILE = 'bes-h1-2010-statements-income-notes.v24'
DOCUMENT, PDF = prior.DOCUMENT, prior.PDF
PAGES = (103,104,115)
TESTS = prior.TESTS
KEYS={**delivery.KEYS,48:'h1_basis_policy_consumer'}
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
    paths.update(ROOT/n for n in (PLAN, SELF, PRODUCTION,'scripts/prospectus_h1_income_notes_mapping.py','scripts/prospectus_h1_income_notes_tables.py'))
    paths.add(AUTH/'revisions/0412.json')
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
    require(old['revision']==411 and not PREP.exists() and not HERE.exists(),'Fresh411 required')
    events=auth.events()
    attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e['budget_key']=='source-bes-dep-05']
    require(len(attempts)==old['budgets']['source-bes-dep-05']['maximum_new_attempts']==48,'Retain48attempts')
    require(read(delivery.HERE/'result.json')['status']=='PASS','Successful048 required')
    protected={}
    for n in (7,15,16,17,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48):
        folder=BASE/f'attempt-{n:03d}'; manifest=folder/'outputs.json'
        records=[e for e in events if e.get('attempt')==rel(folder) and 'outputs_sha256' in e]
        require(records and sha(manifest)==records[-1]['outputs_sha256'],'Unauthenticated original')
        protected[rel(manifest)]=sha(manifest)
        for name,h in read(manifest).items(): require(sha(folder/name)==h,'Changed original '+name)
    previous=delivery.costs()
    temporary=ROOT/'.localresources/prospectus-preparation/h1-income-notes-049'
    temporary_bytes=sum(p.stat().st_size for p in temporary.rglob('*') if p.is_file())
    temporary_bytes+=sum(p.stat().st_size for p in Path('/tmp/prospectus-income-notes-preparation').rglob('*') if p.is_file())
    temporary_bytes+=Path('/tmp/prepare_prospectus_income_notes_049.py').stat().st_size
    temporary_bytes+=sum(p.stat().st_size for p in Path('/tmp/prospectus-income-notes-selection').rglob('*') if p.is_file())
    save(PREP/'accounting-start.json',{'prior_known_bytes':previous['known_cumulative_bytes'],
        'prior_known_seconds':previous['known_cumulative_seconds'],'prior_cost_receipt':previous,
        'temporary_preparation_bytes':temporary_bytes,
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size})
    preflight=read(temporary/'preflight.json')
    require(preflight['status']=='PASS' and preflight['actual_source_worker_passed'],'Actual source-worker preflight required')
    save(PREP/'mapping-preflight.json',preflight)
    save(PREP/'commands/mapping-preflight.json',{'wall_seconds':preflight['seconds'],
        'command':'Actual income-note source-worker, gzip storage, original graph and adverse preflight'})
    shutil.copytree(temporary,PREP/'preflight-execution')
    image_prep=Path('/tmp/prospectus-income-notes-preparation')
    shutil.copytree(image_prep,PREP/'source-preparation')
    images=[]
    for page in PAGES:
        path=PREP/'source-preparation'/f'page-{page}.png'
        images.append({'page':page,'path':rel(path),'sha256':sha(path)})
        save(PREP/'commands'/f'render-{page}.json',read(image_prep/f'render-{page}.json'))
    save(PREP/'source-preparation/images.json',images)
    save(PREP/'commands/inspection.json',read(image_prep/'inspection.json'))
    early=read('/tmp/prospectus-income-notes-selection/table-check.json')
    require(early['status']=='PASS','Early table check failed')
    save(PREP/'commands/table-check.json',{'command':'Image rows, original geometry and adverse table check',
        'wall_seconds':early['wall_seconds']})
    shutil.copytree('/tmp/prospectus-income-notes-selection',PREP/'selection-evidence')
    (PREP/'baseline').mkdir(); shutil.copyfile(ROOT/PRODUCTION,PREP/'baseline/statement_cells.py')
    production=common.production();save(PREP/'baseline/production.json',production)
    protected.update({n:h for n,h in read(delivery.PREP/'freeze.json')['bindings'].items() if n!=PRODUCTION})
    names=[PLAN,SELF,prior.SELF,'scripts/prospectus_h1_income_notes_mapping.py','scripts/prospectus_h1_income_notes_tables.py','pyproject.toml',*TESTS,rel(PREP/'mapping-preflight.json'),rel(PREP/'baseline/statement_cells.py'),
        rel(PREP/'baseline/production.json'),rel(delivery.HERE/'ordinary.json.gz'),
        rel(prior.HERE/'source-units.json'),rel(prior.HERE/prior.READING),
        rel(prior.HERE/'image-transcript.json'),rel(BASE/'attempt-028/COVERAGE-CORRECTION.md'),
        rel(prior.HERE/'images.json'),rel(prior.HERE/'registry-entry.json'),rel(BASE/'attempt-028/retained-risk-coverage-correction.json')]
    names.extend(rel(p) for d in ('source-preparation','preflight-execution','selection-evidence') for p in (PREP/d).rglob('*') if p.is_file())
    protected.update({n:sha(ROOT/n) for n in names})
    protected.update({n:h for n,h in production.items() if n!=PRODUCTION})
    require(all(sha(ROOT/n)==h for n,h in protected.items()),'Stale inherited binding')
    save(PREP/'freeze.json',{'bindings':protected,'baseline_sha256':sha(ROOT/PRODUCTION),
        'mutable_file':PRODUCTION,'implementation_window':'Once after reviewed source and candidate freeze'})
    config=read(prior.PREP/'config.json'); require(sha(config['package_python'])==config['python_sha256'],'Build interpreter changed')
    save(PREP/'config.json',config)
    new=deepcopy(old);new['revision']=412
    task=next(t for t in new['tasks'] if t['id']=='source-bes-dep-05')
    task.update(dossier=PLAN,pre_admission_review=PLAN,build_criteria_scope=[],
        reason='Deliver original Notes 5, 6 and 13 with original numeric rows, date/unit associations, dash and expense-label anomalies, and source conditions; preserve complete 048')
    task['inputs']=sorted((set(task['inputs'])-{PRODUCTION})|set(protected)|{rel(PREP/'freeze.json'),rel(PREP/'config.json')})
    bounds={'measured_seconds':1200,'control_seconds':60,'new_bytes':256*1024**2,'failure_reserve':4*1024**2,'worker_seconds':120,'large_file_bytes':32*1024**2,
        'previous_known_bytes':previous['known_cumulative_bytes'],'previous_known_seconds':previous['known_cumulative_seconds'],'unchanged_retries':0}
    task['income_notes_evidence']={'version':PROFILE,'freeze':rel(PREP/'freeze.json'),'bounds':bounds,
        'success_dependencies':DEPENDENCIES,'original_task_acceptance':False}
    new['budgets']['source-bes-dep-05']['maximum_new_attempts']=49
    routes=read(ROOT/old['continuation_review']['routes']); routes['baseline_revision']=412
    for row in routes['tasks']:
        if row['task']==task['id']:
            row.update(task_sha256=compact_digest(task),dossier=PLAN,phase=0,
                remaining='Successful 048 retained; complete Notes 5, 6 and 13 and remaining policy/note/source-authority obligations remain.',
                next_action='Execute 049 income-note source/normal/installed delivery; preserve 048 and all failures; reconcile remaining original requirements.',
                stop_condition='Retain 48 admissions and permit attempt 49; 1200+60 seconds and 256 MiB new; no unchanged retry; retain cumulative costs/failures.')
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
        'changes':['Deliver complete Notes 5, 6 and 13 with complete 048 retained','Preserve gzip persistence and actual source-worker preflight','Retain 48 admissions and all original obligations'],
        'skeptical_audit':{'verdict':'PASS','plan':PLAN,'forecast_new_bytes':forecast,
            'no_proxy_promotion':'Original full-page quotes/geometry,conditional clauses and actual consumers;hashes and arithmetic do not prove legal or financial truth'},
        'evidence_contract':{'question':'Does complete original Notes 5, 6 and 13 reach the full answer with date, unit, row associations and accompanying conditions intact?',
            'primary':'Separately typed image-checked transcript, original geometry/quotes, prior preservation and normal/installed corruption refusals',
            'promotion_veto':['Wrong date/amount/unit','Omitted clause','Lost prior answer','Conflicting duplicate','Wrong import','Accepted corruption'],
            'continuation_veto':['Invalid authority','Corrupt shared originals','Spent resources'],
            'not_concluded':['Automatic extraction','Verified valuation','Holder recovery','Current law','Whole build']},
        'budget_revision':{'budget_key':'source-bes-dep-05','previous_maximum':48,'new_maximum':49,
            'retained_attempts':attempts,'reason':'Remaining original income and administrative-note requirements; preserve successful 048, original obligations and actual cumulative costs',
            'next_discriminating_check':'Original date/row geometry, dash semantics, broad derivative interest and service liability/expense date distinction',
            'stop_condition':bounds,'same_scope_authorization':'Recover and continue original build'}})
    save(PREP/'commands/preparation.json',{'wall_seconds':time.monotonic()-tick,
        'command':[sys.executable,'-B','-m','scripts.prospectus_h1_income_notes','prepare']})
    return {'status':'PREPARED','revision':412,'forecast_new_bytes':forecast,'resources':costs()}


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
    require(len(old)==7282,'Wrong 048 baseline')
    by_id={u['id']:u for u in old}
    require(len(old)==len(by_id),'Duplicate prior occurrence')
    require(len(units)==len({u['id'] for u in units}),'Duplicate local occurrence')
    overlap=set(by_id).intersection(u['id'] for u in units)
    require(not overlap,'Unexpected prior source overlap')
    for unit in units:
        if unit['id'] in by_id:
            same(by_id[unit['id']],unit,'Conflicting shared occurrence')
        else:by_id[unit['id']]=unit
    require(len(by_id)==7464,'Wrong combined occurrences')
    return sorted(by_id.values(),key=lambda u:(u['page'],u['order'],u['id']))


def normal(value):
    return ''.join(value.split())


def income_notes_reading(units):
    lookup={(u['page'],u['order']):u for u in units}
    def q(p,i):
        u=lookup[p,i];return {'id':u['id'],'quote':u['raw']}
    return {'version':'bes-income-notes-reading.v1','notes':[5,6,13],
        'source_groups':[{'page':p,'sources':[q(p,u['order']) for u in units if u['page']==p]} for p in PAGES],
        'clauses':[{'key':key,'sources':[q(p,i) for i in range(a,b+1)],'interpretation':meaning}
            for key,p,a,b,meaning in mapping.SPECS],
        'tables':table_support.tables(units),'distinctions':deepcopy(mapping.DISTINCTIONS),
        'source_scope':{'origin':'SUPPLIED_DEVELOPMENT_READING','notes5_6_13_delivered':True,'note12_complete':False,
            'historical_report_assertions_only':True,'source_authority_or_incorporation_resolved':False}}


def source_check(reading,units,transcript):
    require(len(units)==len({u['id'] for u in units})==182,'Complete three-page source required')
    lookup={u['id']:u for u in units};s=reading['income_notes_evidence']
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
    same(s['notes'],[5,6,13],'Wrong note scope')
    ranges={103:(1,60),104:(1,41),115:(1,72)}
    expected={u['id'] for u in units if ranges[u['page']][0]<=u['order']<=ranges[u['page']][1]}
    substantive=refs(s['clauses'])
    require(len(substantive)==len(set(substantive)) and set(substantive)==expected,'Missing or duplicated substantive occurrence')
    require(len(s['clauses'])==9,'Wrong clause count')
    clauses={c['key']:c for c in s['clauses']}
    require({x['key'] for x in transcript['anchors']}==set(clauses) and len(transcript['anchors'])==9,'Missing image-checked anchors')
    for anchor in transcript['anchors']:
        actual=' '.join(x['quote'] for x in clauses[anchor['key']]['sources'])
        require(normal(anchor['quote']) in normal(actual),'Image-checked passage mismatch: '+anchor['key'])
    for clause in s['clauses']:
        boxes=[lookup[q['id']]['bbox'] for q in clause['sources']]
        require(all(len(b)==4 and b[0]<b[2] and b[1]<b[3] for b in boxes),'Invalid clause geometry')
        # Original tables are column-major in native extraction. The table
        # validator checks actual row/column geometry instead of imposing prose order.
        if clause['key'] not in ('interest-table','fee-table','administrative-table'):
            require(all(b[1]>=a[1]-3 for a,b in zip(boxes,boxes[1:])),'Wrong clause order')
    expected_reading=income_notes_reading(units)
    same(s['clauses'],expected_reading['clauses'],'Reviewed clause mapping changed')
    same(s['source_scope'],expected_reading['source_scope'],'Source scope changed')
    table_check=table_support.validate(s['tables'],units,transcript)
    same(s['distinctions'],transcript['distinctions'],'Unreviewed interpretation distinctions')
    same(transcript['pages_reviewed'],list(PAGES),'Incomplete image review')
    require('not a blind independent reading' in transcript['independence_limit'],
            'Image/native reading dependence must remain explicit')
    old=read(prior.HERE/prior.READING)
    same({k:v for k,v in reading.items() if k!='income_notes_evidence'},old,'Complete 048 reading changed')
    prior.source_check(old,read(prior.HERE/'source-units.json'),read(prior.HERE/'image-transcript.json'))
    return {**table_check,'local_occurrences':182,'combined_occurrences':len(combined_units(units)),
        'clause_groups':9,'substantive_occurrences':len(expected),
        'image_checked_passages':9,'complete_prior_fields_preserved':True,
        'image_reading_is_blind':False,'financial_or_legal_truth_verified':False}


def full_graph_preflight(candidate,reading,graph):
    namespace={'__name__':'legalmath.prospectus.successor._income_notes_candidate','__package__':'legalmath.prospectus.successor'}
    exec(compile(candidate,'candidate-statement_cells.py','exec'),namespace)
    packet={'version':'source-statement-cells.v1','profile':PROFILE,'document':DOCUMENT,'graph_sha256':digest(graph),
        'review':{'kind':'DEVELOPMENT','reviewer':'Original source mappings','reason':'Actual full-graph preflight'},'reading':reading}
    admitted=namespace['admit'](graph,packet)
    bad=deepcopy(graph);bad['units']=[u for u in bad['units'] if u['id']!='bes-interim-h1-2010:p103:l0']
    negative=deepcopy(packet);negative['graph_sha256']=digest(bad)
    try:namespace['admit'](bad,negative)
    except ValueError as exc:require('original pages or geometry' in str(exc),'Wrong context refusal')
    else:raise ValueError('Missing source context accepted')
    return {'status':'PASS','actual_graph_admitted':True,'context_loss_refused':True,'admitted_sha256':admitted['sha256']}


def source_worker():
    units=original_units();transcript=read(HERE/'image-transcript.json');review=HERE/'SOURCE-REVIEW.md'
    require(review.is_file() and len(review.read_text())>1000,'Substantive source review required')
    require(transcript['method']=='MANUALLY_TYPED_FROM_ORIGINAL_IMAGES','Separately typed image-checked transcript required')
    for item in read(HERE/'images.json'):require(sha(ROOT/item['path'])==item['sha256'],'Source image changed')
    reading=deepcopy(read(prior.HERE/prior.READING));reading['income_notes_evidence']=income_notes_reading(units)
    checked=source_check(reading,units,transcript);all_units=combined_units(units)
    save(HERE/'source-units.json',units);save(HERE/READING,reading)
    entry={'document':DOCUMENT,'source':PDF,'reading':compact_digest(reading),'pages_digest':compact_digest(all_units),
        'pages':sorted({u['page'] for u in all_units}),'occurrences':len(all_units),
        'reading_fields':list(read(prior.HERE/'registry-entry.json')['reading_fields'])+['income_notes_evidence']}
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
    save(HERE/'source-check.json',{'status':'PASS',**checked,'baseline_gap':'Notes 5, 6 and 13 profile unsupported','source_review':common.ref(review)})



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
        'review':{'kind':'DEVELOPMENT','reviewer':'Original page images, exact clauses and separately typed image-checked passages',
            'reason':'Complete 048 plus original Notes 5, 6 and 13; date/row associations, unknown dash, expense-label anomaly and service liability/expense dates remain explicit'},
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
        'column-swap':lambda s:s['tables'][0]['rows'][0]['cells'].reverse(),
        'dash-zero':lambda s:s['tables'][0]['rows'][13]['cells'][1].update(value=0,status='REPORTED_INTEGER'),
        'date-changed':lambda s:s['tables'][0]['period_ends'].reverse(),
        'label-corrected':lambda s:s['tables'][0]['rows'][13]['label_source'].update(quote='Other interest expense'),
        'unit-changed':lambda s:s['tables'][0].update(unit='EUR_MILLIONS'),
        'row-lost':lambda s:s['tables'][2]['rows'].pop(),
        'unwind-changed':lambda s:s['distinctions']['unwind_discount_eur_thousands'].update({'2010-06-30':10813}),
        'hedges-only':lambda s:s['distinctions']['risk_derivative_categories'].pop(),
        'service-date-changed':lambda s:s['distinctions'].update(service_liability_and_expense_dates_distinct=False),
        'service-assumptions-unconditional':lambda s:s['distinctions'].update(service_pension_assumptions='ALWAYS'),
        'note12-complete':lambda s:s['distinctions'].update(note12_complete=True),
        'clause-lost':lambda s:s['clauses'].pop(),
        'authority-resolved':lambda s:s['source_scope'].update(source_authority_or_incorporation_resolved=True)}
    for name,change in changes.items():
        bad=supplied(graph);change(bad['reading']['income_notes_evidence'])
        try:cells.admit(graph,bad)
        except ValueError as exc:
            require('reading differs' in str(exc),'Unexpected reading refusal')
            rows.append({'case':name,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else:raise ValueError('Altered reading accepted: '+name)
    for name in ('missing-page','context-occurrence-lost','source-hash','geometry','duplicate-occurrence'):
        g=deepcopy(graph)
        if name=='missing-page':g['units']=[u for u in g['units'] if u['page']!=104]
        elif name=='context-occurrence-lost':g['units']=[u for u in g['units'] if u['id']!='bes-interim-h1-2010:p103:l0']
        elif name=='source-hash':next(u for u in g['units'] if u['page']==104)['source_sha256']='0'*64
        elif name=='geometry':next(u for u in g['units'] if u['id']=='bes-interim-h1-2010:p103:l22')['bbox'][1]+=4
        else:g['units'].append(deepcopy(next(u for u in g['units'] if u['page']==104)))
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
    if kind=='baseline':require(answer_hash==read(delivery.HERE/'ordinary.json.gz')['answer_sha256'],'Complete048baseline changed')
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
        same(before['source_statement_cells'][key],after['source_statement_cells'][key],'Lost048field '+key)
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
    composed['h1_income_notes_consumer']=parts
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
        elif change=='changed_p2': p2['source_statement_cells']['reading']['income_notes_evidence']['distinctions']['current_law_or_standard_verified']=True
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
    rows.append({'requirement':'Original Notes 5, 6 and 13 numeric/conditional delivery with complete 048 retained',
                 'status':'THIS_ATTEMPT_MUST_PASS; see actual stage results'})
    inventory=deepcopy(read(delivery.HERE/'note-inventory.json'))
    for row in inventory['notes']:
        if row['note'] in (5,6,13):row['status']='THIS_ATTEMPT_SUBJECT_TO_STAGE_RESULTS'
        if row['note']==12:row['page115_context']='THIS_ATTEMPT; full Note12 remains separately incomplete'
    inventory['policies']['2.1']='RETAINED_FINITE_INTEGRATION'
    inventory['policies']['remaining']='ALL_23_HAVE_FINITE_DELIVERIES; ORIGINAL_SOURCE_ACCEPTANCE_REMAINS_OPEN'
    policy_receipt=deepcopy(read(delivery.HERE/'policy-coverage-reconciliation.json'))
    policy_receipt['previous_policies'].append({'policy':'2.1','attempt':48,
        'result':common.ref(delivery.HERE/'result.json'),'source_check':common.ref(delivery.HERE/'source-check.json'),
        'status':'RETAINED_FINITE_INTEGRATION','original_task_accepted':False})
    policy_receipt.update(current_policy=None,current_status='ALL_LISTED_FINITE_RESULTS_RETAINED')
    save(HERE/'policy-coverage-reconciliation.json',policy_receipt)
    save(HERE/'note-inventory.json',inventory)
    save(HERE/'requirements.json',{'rows':rows,'original_task_acceptance':False,
        'external_adviser_opinion_required':False,
        'next_discriminating_work':'Continue uncovered/supplement-only notes, including full Note12; source authority, controlling edition and incorporation remain.'})

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
            source_truth_established=False,recipe='Reconstruct048from007;preserve016/017andallsuccessful021–048compositions;add049as h1_income_notes_consumer')
        save(HERE/'ordinary.json.gz',receipt)
        installed=deepcopy(receipt);installed['imports']=read(HERE/'installed.json')['imports']
        save(HERE/'installed.json.gz',installed)
    save(HERE/'result.json',{'task':'source-bes-dep-05','status':'PASS' if passed else 'FAIL','stages':outcomes,
        'task_complete':False,'whole_program_complete':False,'build_criteria_claimed':[],'resources':costs()})
    (HERE/'RESULT.md').write_text('# Original income and operating-expense notes\n\n'+('Finite source/consumer integration passed. ' if passed else 'Campaign did not pass. ')
        +'Actual stages: '+json.dumps(outcomes)+'.\n\n'
        +'Notes 5, 6 and 13 retain original numeric associations, reported unknowns and source conditions; page-115 service context remains partial Note 12 coverage. '
        +'Historical regulatory and accounting statements remain attributed to the report; no current rule or legal title is inferred. '
        +('The full 048 answer and all original compositions including supplied OCR risk tables are preserved. ' if passed else
          'Complete 048 and historical composition preservation is required; consult actual stage failures before claiming delivery. ')
        +'Historical report claims do not establish current standards,rights,valuation or whole-source acceptance.\n\n'
        +'|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|\n|---|---|---|---|---|---|\n'
        +'|'+('Retain finite integration' if passed else 'Retain actual failure')+'|Original images/quotes/geometry and actual full normal/installed answers|See stage records|Remaining notes and authority|Record/refresh;reconcile remaining source obligations with actual current coverage|Financial truth,current law,holder entitlement,automatic extraction,whole build|\n\n'
        +'Post-run review: exact profiles preserve supplied readings; a shared wrong interpretation remains the strongest alternative explanation. '
        +'The separately typed image-checked transcript and full quote/geometry review address source association and omissions. '
        +'Native text was seen before image transcription; this is not blind independent evidence. They do not prove external financial or legal truth. Remaining coverage is an implementation/evidence gap,not evidence that a package is fundamentally unsuitable.\n')
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
