"""Bounded original investments-in-associates disclosure delivery."""
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
from scripts import prospectus_h1_group_transcript_repair as prior
from scripts import prospectus_h1_statement_consumer as common

read, save, sha, digest = prior.read, prior.save, prior.sha, prior.digest
compact_digest, same, require, rel = prior.compact_digest, prior.same, prior.require, prior.rel
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
BASE = AUTH / 'attempts/source-bes-dep-05'
PREP = AUTH / 'reviews/h1-associates-405'
HERE = BASE / 'attempt-042'
SELF = 'scripts/prospectus_h1_associates.py'
PLAN = 'docs/plans/prospectus-h1-associates-2026-10-21.md'
PRODUCTION = prior.PRODUCTION
PROFILE = 'bes-h1-2010-statements-associates.v19'
DOCUMENT, PDF = prior.DOCUMENT, prior.PDF
PAGES = (133,134)
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
    paths.add(AUTH/'revisions/0405.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists()) + start.get('temporary_preparation_bytes',0)
    size += max(0, (AUTH/'program.json').stat().st_size-start['program_bytes'])
    seconds = sum(read(p)['wall_seconds'] for d in (PREP, HERE) for p in d.glob('commands/*.json'))
    return {'new_bytes': size, 'new_measured_seconds': seconds, 'new_control_seconds': 60,
        'prior_known_bytes': start['prior_known_bytes'], 'prior_known_seconds': start['prior_known_seconds'],
        'known_cumulative_bytes': start['prior_known_bytes']+size,
        'known_cumulative_seconds': start['prior_known_seconds']+seconds+60,
        'earlier_manual_and_unmeasured_costs': 'UNKNOWN; history retained',
        'execution_allowed': size+reserve < 126*1024**2 and seconds < 1200}


def prepare():
    tick=time.monotonic(); auth=authority(); old=read(AUTH/'program.json')
    require(old['revision']==404 and not PREP.exists() and not HERE.exists(),'Fresh404 required')
    events=auth.events()
    attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e['budget_key']=='source-bes-dep-05']
    require(len(attempts)==old['budgets']['source-bes-dep-05']['maximum_new_attempts']==41,'Retain41attempts')
    require(read(prior.HERE/'result.json')['status']=='PASS','041 must pass')
    protected={}
    for n in (7,15,16,17,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41):
        folder=BASE/f'attempt-{n:03d}'; manifest=folder/'outputs.json'
        records=[e for e in events if e.get('attempt')==rel(folder) and 'outputs_sha256' in e]
        require(records and sha(manifest)==records[-1]['outputs_sha256'],'Unauthenticated original')
        protected[rel(manifest)]=sha(manifest)
        for name,h in read(manifest).items(): require(sha(folder/name)==h,'Changed original '+name)
    previous=prior.costs()
    temporary=Path('/tmp/prospectus-associates-preparation')
    temporary_bytes=sum(p.stat().st_size for p in temporary.rglob('*') if p.is_file())
    temporary_bytes+=sum(p.stat().st_size for p in [Path('/tmp/prospectus-associates-table-map.json'),
        Path('/tmp/prospectus-associates-source-block.py'),Path('/tmp/prospectus-note27-page-133.txt'),
        Path('/tmp/prospectus-note27-page-134.txt'),Path('/tmp/prospectus-note27-layout.txt'),
        Path('/tmp/prospectus-associates-mapping-start.json'),Path('/tmp/prospectus-associates-preflight.json')] if p.exists())
    save(PREP/'accounting-start.json',{'prior_known_bytes':previous['known_cumulative_bytes'],
        'prior_known_seconds':previous['known_cumulative_seconds'],'prior_cost_receipt':previous,
        'temporary_preparation_bytes':temporary_bytes,
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size})
    preflight=read(Path('/tmp/prospectus-associates-preflight.json'))
    require(preflight['status']=='PASS' and preflight['manual_image_review'],'Complete manual source preflight required')
    save(PREP/'mapping-preflight.json',preflight)
    save(PREP/'commands/mapping-preflight.json',{'wall_seconds':preflight['seconds'],
        'command':'Complete Note 27 source/graph/adverse preflight against independently typed image transcript'})
    image_prep=Path('/tmp/prospectus-associates-preparation')
    shutil.copytree(image_prep,PREP/'source-preparation')
    images=[]
    for page in PAGES:
        path=PREP/'source-preparation'/f'page-{page}.png'
        images.append({'page':page,'path':rel(path),'sha256':sha(path)})
        save(PREP/'commands'/f'render-{page}.json',read(image_prep/f'render-{page}.json'))
    save(PREP/'source-preparation/images.json',images)
    save(PREP/'commands/mapping-diagnostic.json',read(image_prep/'mapping-diagnostic.json'))
    save(PREP/'commands/mapping-start.json',{'wall_seconds':read(Path('/tmp/prospectus-associates-mapping-start.json'))['seconds'],
        'command':'Read-only source geometry preparation'})
    (PREP/'baseline').mkdir(); shutil.copyfile(ROOT/PRODUCTION,PREP/'baseline/statement_cells.py')
    production=common.production();save(PREP/'baseline/production.json',production)
    protected.update({n:h for n,h in read(prior.PREP/'freeze.json')['bindings'].items() if n!=PRODUCTION})
    names=[PLAN,SELF,prior.SELF,'pyproject.toml',*TESTS,rel(PREP/'mapping-preflight.json'),rel(PREP/'baseline/statement_cells.py'),
        rel(PREP/'baseline/production.json'),rel(prior.HERE/'ordinary.json.gz'),
        rel(prior.HERE/'source-units.json'),rel(prior.HERE/'reading.json'),
        rel(prior.HERE/'image-transcript.json'),rel(BASE/'attempt-028/COVERAGE-CORRECTION.md'),
        rel(prior.HERE/'images.json'),rel(prior.HERE/'registry-entry.json'),rel(BASE/'attempt-028/retained-risk-coverage-correction.json')]
    names.extend(rel(p) for p in (PREP/'source-preparation').rglob('*') if p.is_file())
    protected.update({n:sha(ROOT/n) for n in names})
    protected.update({n:h for n,h in production.items() if n!=PRODUCTION})
    require(all(sha(ROOT/n)==h for n,h in protected.items()),'Stale inherited binding')
    save(PREP/'freeze.json',{'bindings':protected,'baseline_sha256':sha(ROOT/PRODUCTION),
        'mutable_file':PRODUCTION,'implementation_window':'Once after reviewed source and candidate freeze'})
    config=read(prior.PREP/'config.json'); require(sha(config['package_python'])==config['python_sha256'],'Build interpreter changed')
    save(PREP/'config.json',config)
    new=deepcopy(old);new['revision']=405
    task=next(t for t in new['tasks'] if t['id']=='source-bes-dep-05')
    task.update(dossier=PLAN,pre_admission_review=PLAN,build_criteria_scope=[],
        reason='Deliver Note 27 investment cost, carrying amounts, profit shares and movements with their printed periods; preserve complete 041')
    task['inputs']=sorted((set(task['inputs'])-{PRODUCTION})|set(protected)|{rel(PREP/'freeze.json'),rel(PREP/'config.json')})
    bounds={'measured_seconds':1200,'control_seconds':60,'new_bytes':128*1024**2,'failure_reserve':2*1024**2,
        'previous_known_bytes':previous['known_cumulative_bytes'],'previous_known_seconds':previous['known_cumulative_seconds'],'unchanged_retries':0}
    task['associates_evidence']={'version':PROFILE,'freeze':rel(PREP/'freeze.json'),'bounds':bounds,
        'success_dependencies':DEPENDENCIES,'original_task_acceptance':False}
    new['budgets']['source-bes-dep-05']['maximum_new_attempts']=42
    routes=read(ROOT/old['continuation_review']['routes']); routes['baseline_revision']=405
    for row in routes['tasks']:
        if row['task']==task['id']:
            row.update(task_sha256=compact_digest(task),dossier=PLAN,phase=0,
                remaining='041 group structure retained; Note 27 and remaining policies/notes and source authority remain.',
                next_action='Execute 042 Note 27 source/normal/installed delivery; preserve 041 and all previous compositions and reconcile remaining original requirements.',
                stop_condition='Retain 41 admissions and permit attempt 42; 1200+60 seconds and 128 MiB new; no unchanged retry; retain cumulative costs/failures.')
    save(PREP/'routes.json',routes)
    new['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    new['continuation_review']['bindings'].pop(PRODUCTION,None)
    new['continuation_review']['bindings'].update({n:sha(ROOT/n) for n in
        (PLAN,rel(PREP/'routes.json'),rel(PREP/'freeze.json'),rel(PREP/'baseline/statement_cells.py'))})
    require(old['obligations']==new['obligations'] and old['build_contract']==new['build_contract'],'Scope changed')
    raw=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
    source_bytes=sum(p.stat().st_size for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    forecast=costs()['new_bytes']+2*len(raw)+3*source_bytes+10*1024**2
    require(forecast<126*1024**2,'Forecast exceeds reservation')
    with (PREP/'proposal.json').open('xb') as stream:stream.write(raw)
    from legalmath.prospectus.execution_authority import digest as adigest
    save(PREP/'review.json',{'baseline':adigest(old),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Deliver Note 27; preserve complete 041','Preserve verified original composition including OCR risk tables','Retain 41 admissions and all original obligations'],
        'skeptical_audit':{'verdict':'PASS','plan':PLAN,'forecast_new_bytes':forecast,
            'no_proxy_promotion':'Original date/column geometry,conditional clauses and actual consumers;hashes and arithmetic do not prove legal or financial truth'},
        'evidence_contract':{'question':'Do Note 27 investments in associates retain printed dates, measurements, movements and source qualifications in the complete answer?',
            'primary':'Independent image transcript, original geometry/quotes, prior preservation and normal/installed corruption refusals',
            'promotion_veto':['Wrong date/amount/unit','Omitted clause','Lost prior answer','Conflicting duplicate','Wrong import','Accepted corruption'],
            'continuation_veto':['Invalid authority','Corrupt shared originals','Spent resources'],
            'not_concluded':['Automatic extraction','Verified valuation','Holder recovery','Current law','Whole build']},
        'budget_revision':{'budget_key':'source-bes-dep-05','previous_maximum':41,'new_maximum':42,
            'retained_attempts':attempts,'reason':'Original Note 27 onward dependency of delivered Note 1; retain all previous failures and cumulative costs',
            'next_discriminating_check':'Distinguish acquisition cost, book value, investee equity, profit share and printed comparison periods; retain unknown dashes and unprinted cells',
            'stop_condition':bounds,'same_scope_authorization':'Recover and continue original build'}})
    save(PREP/'commands/preparation.json',{'wall_seconds':time.monotonic()-tick,
        'command':[sys.executable,'-B','-m','scripts.prospectus_h1_associates','prepare']})
    return {'status':'PREPARED','revision':405,'forecast_new_bytes':forecast,'resources':costs()}


def frozen():
    auth = authority(); admission = read(HERE/'admission.json')
    from legalmath.prospectus.execution_authority import digest as adigest
    require(adigest(read(AUTH/'program.json'))==admission['program_sha256'] and
            auth.binding(admission['task_spec'])==admission['binding'], 'Unchanged admission required')
    f = read(PREP/'freeze.json')
    require(all(sha(ROOT/n)==h for n, h in f['bindings'].items()), 'Frozen input changed')
    expected = read(HERE/'candidate-production.json')[PRODUCTION] if (HERE/'candidate-production.json').exists() else f['baseline_sha256']
    require(sha(ROOT/PRODUCTION)==expected, 'Registry outside implementation window')


def command(name, argv, timeout=360):
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


TABLE_MAP = {'financial_information': [[22, [23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34]], [35, [36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47]], [48, [49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 118]], [60, [61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72]], [73, [74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85]], [86, [88, 90, 92, 94, 96, 98, 100, 102, 104, 106, 108, 110]], [87, [89, 91, 93, 95, 97, 99, 101, 103, 105, 107, 109, 111]], [112, [113, 114, 115, 116, 117, 119, 120, 121, 122, 123, 124, 125]], [126, [127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138]], [139, [140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151]], [152, [153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164]], [165, [166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177]], [178, [179, 180, 181, 182, 209, 183, 184, 185, 186, 187, 188, 189]], [190, [191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202]], [203, [204, 205, 206, 207, 208, 210, 211, 212, 213, 214, 215, 216]], [217, [218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229]], [230, [231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242]], [243, [244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255]], [260, [None, None, None, None, None, None, None, None, None, None, 256, 257]], [None, [None, None, None, None, None, None, None, None, None, None, 258, 259]]], 'interest_book_profit': [[275, [276, 277, 278, 279, 280, 281, 282, 283, 284]], [285, [286, 287, 288, 289, 290, 291, 292, 293, 294]], [295, [296, 297, 298, 299, 300, 301, 302, 303, 304]], [305, [306, 307, 308, 309, 310, 311, 312, 313, 314]], [315, [316, 317, 318, 319, 320, 321, 322, 323, 324]], [325, [327, 329, 331, 333, 335, 337, 339, 341, 343]], [326, [328, 330, 332, 334, 336, 338, 340, 342, 344]], [345, [346, 347, 348, 349, 350, 351, 352, 353, 354]], [355, [356, 357, 358, 359, 360, 361, 362, 363, 364]], [365, [366, 367, 368, 369, 370, 371, 372, 373, 374]], [375, [376, 377, 378, 379, 380, 381, 382, 383, 384]], [385, [386, 387, 388, 389, 390, 391, 392, 393, 394]], [395, [396, 397, 398, 399, 400, 401, 402, 403, 404]], [406, [407, 408, 409, 410, 411, 412, 413, 414, 405]], [415, [416, 417, 418, 419, 420, 421, 422, 423, 424]], [425, [426, 427, 428, 429, 430, 431, 432, 433, 434]], [435, [436, 437, 438, 439, 440, 441, 442, 443, 444]], [445, [446, 447, 448, 449, 450, 451, 452, 453, 454]], [467, [None, None, None, 455, 456, 457, 458, 459, 460]], [None, [None, None, None, 461, 462, 463, 464, 465, 466]]]}

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
    require(len(old)==6288,'Wrong 041 baseline')
    by_id={u['id']:u for u in old}
    require(not set(by_id).intersection(u['id'] for u in units),'Unexpected source overlap')
    by_id.update({u['id']:u for u in units})
    require(len(by_id)==6870,'Wrong combined occurrences')
    return sorted(by_id.values(),key=lambda u:(u['page'],u['order'],u['id']))


def normal(value):
    return ''.join(value.split())


def associates_reading(units):
    lookup={(u['page'],u['order']):u for u in units}
    def q(p,i):
        u=lookup[p,i];return {'id':u['id'],'quote':u['raw']}
    def cell(p,i,unit):
        if i is None:return {'value':None,'unit':unit,'status':'NOT_PRINTED'}
        item=q(p,i);token=normal(item['quote'])
        value=None if token=='-' else prior.percent(token) if unit=='percent' else -int(token[1:-1]) if token.startswith('(') else int(token)
        return {**item,'value':value,'unit':unit,'status':'UNKNOWN' if value is None else 'SOURCE_NUMBER'}
    tables=[]
    for key,groups,dates,width in [('financial_information',list(range(4,10)),list(range(10,22)),12),
        ('interest_book_profit',[264,263,269],[265,266,267,268,270,271,272,273,274],9)]:
        rows=[]
        for label,indices in TABLE_MAP[key]:
            rows.append({'label_sources':[] if label is None else [q(133,label)],
                'label':'TOTAL (unlabelled)' if label is None else None,
                'cells':[cell(133,i,'percent' if key=='interest_book_profit' and col<3 else 'EUR thousands') for col,i in enumerate(indices)]})
        tables.append({'key':key,'page':133,'unit_source':q(133,3 if width==12 else 262),
            'group_sources':[q(133,i) for i in groups],'date_sources':[q(133,i) for i in dates],
            'rows':rows,'blank_means_zero':False})
    movement=[]
    for label,indices,markers in [(7+i if i<4 else 8+i,[15+i,22+i,29+i],[11] if i==4 else []) for i in range(7)]+[(36,[37,38,39],[])]:
        movement.append({'label_sources':[q(134,label)],'label':None,'marker_sources':[q(134,i) for i in markers],
            'cells':[cell(134,i,'EUR thousands') for i in indices]})
    tables.append({'key':'movement','page':134,'unit_source':q(134,2),'group_sources':[q(134,3)],
        'date_sources':[q(134,i) for i in (4,5,6)],'rows':movement,'blank_means_zero':False})
    clauses=[('financial-information',133,2),('consolidation-adjustment',133,261),
        ('influence-footnote',133,468),('goodwill-footnote',133,469),
        ('movement-introduction',134,1),('movement-reserve-footnote',134,40)]
    return {'version':'bes-associates-reading.v1',
        'source_groups':[{'page':p,'sources':[q(p,u['order']) for u in units if u['page']==p]} for p in PAGES],
        'tables':tables,'clauses':[{'key':key,'sources':[q(p,i)]} for key,p,i in clauses],
        'reported_interpretation':{
            'measurement':'Acquisition cost, book value, investee equity and share of associates profit are distinct reported quantities',
            'periods':'Financial balance columns compare June 2010 and December 2009; income, profit and acquisition-cost columns print June 2010 and June 2009; movement retains its printed Six month period ended heading',
            'influence':'Footnote (a) attributes equity-method treatment below 20 percent economic interest to significant influence',
            'goodwill':'BES VIDA footnote includes EUR 267440 thousand goodwill and EUR 45052 thousand value-in-force; December 2009 value-in-force EUR 46651 thousand',
            'unicre':'June 2010 acquisition cost 11497, book value 19754 and profit-share entry 8260 remain distinct; Note 1 attributes 8260 to first-application revaluation, not recurring profit',
            'comparative_profit':'December 2009 table total 29977 and movement entry 16792 differ by 13185; the difference equals printed June 2009 profit share, but the cause is not proven',
            'legal_status':'HISTORICAL_REPORT_ASSERTIONS_NOT_VERIFIED_RULES'},
        'distinctions':{k:False for k in ('cost_equals_book_value','equity_equals_group_carrying_amount',
            'profit_share_equals_interest_times_profit','economic_interest_equals_voting_power',
            'below_twenty_always_excluded','dash_means_zero','blank_means_zero','periods_harmonized',
            'goodwill_added_again','unicre_gain_is_recurring_profit','current_ifrs_treatment_verified',
            'same_name_proves_identity','note28_fully_interpreted')},
        'source_scope':{'note27_delivered':True,'note28_page_context_only':True,
            'policy2_2_retained_in_prior':True,'source_authority_or_incorporation_resolved':False}}


def source_check(reading,units,transcript):
    require(len(units)==len({u['id'] for u in units})==582,'Complete two-page source required')
    lookup={u['id']:u for u in units};s=reading['associates_evidence']
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
    require([t['key'] for t in s['tables']]==['financial_information','interest_book_profit','movement'],'Missing table')
    cells=[];absent=0;allrows=0
    for table in s['tables']:
        key=table['key'];manual=transcript[key];page=table['page']
        require(normal(table['unit_source']['quote'])==normal('(in thousands of euro)'),'Wrong financial unit')
        same([normal(q['quote']) for q in table['date_sources']],[normal(x) for x in manual['dates']],'Wrong printed dates: '+key)
        same([normal(q['quote']) for q in table['group_sources']],
             [normal(x) for x in (manual['groups'] if key!='movement' else [manual['period_quote']])],'Wrong column/period groups: '+key)
        require(len(table['rows'])==len(manual['rows'])==(8 if key=='movement' else 20),'Wrong row count')
        for index,(row,entry) in enumerate(zip(table['rows'],manual['rows'])):
            label=' '.join(q['quote'] for q in row['label_sources']) if row['label_sources'] else row['label']
            same(normal(label),normal(entry[0]),f'Wrong label {key} row {index}: {label!r} versus {entry[0]!r}')
            width=12 if key=='financial_information' else 9 if key=='interest_book_profit' else 3
            require(len(row['cells'])==len(entry[1])==width,'Wrong table width')
            for col,(cell,typed) in enumerate(zip(row['cells'],entry[1])):
                unit='percent' if key=='interest_book_profit' and col<3 else 'EUR thousands'
                require(cell['unit']==unit,'Percent and currency conflated')
                if typed=='NOT_PRINTED':
                    require(cell=={'value':None,'unit':unit,'status':'NOT_PRINTED'},'Blank converted to value or dash')
                    require(index>=18 and col<(10 if key=='financial_information' else 3),'Unexpected blank position')
                    absent+=1;continue
                require('id' in cell,'Printed cell lacks occurrence')
                token=normal(cell['quote'])
                value=None if token=='-' else prior.percent(token) if unit=='percent' else -int(token[1:-1]) if token.startswith('(') else int(token)
                require(cell['value']==typed==value and cell['status']==('UNKNOWN' if value is None else 'SOURCE_NUMBER'),f'Wrong {key} row {index} column {col}')
                cells.append(cell)
            printed=[c for c in row['cells'] if 'id' in c];boxes=[lookup[c['id']]['bbox'] for c in printed]
            require(all(a[2]<b[0] for a,b in zip(boxes,boxes[1:])) and max(b[1] for b in boxes)-min(b[1] for b in boxes)<1,'Wrong row geometry')
            for q in row['label_sources']:
                box=lookup[q['id']]['bbox'];require(box[2]<boxes[0][0] and abs(box[1]-boxes[0][1])<1,'Wrong label association')
            for q in row.get('marker_sources',[]):
                require(normal(q['quote'])=='(a)' and abs(lookup[q['id']]['bbox'][1]-boxes[0][1])<2.8,'Wrong movement footnote')
            allrows+=1
        require(table['blank_means_zero'] is False,'Unsupported blank interpretation')
        expected={u['id'] for u in units if u['page']==page and
            ((key=='financial_information' and 169<u['bbox'][1]<320) or
             (key=='interest_book_profit' and 400<u['bbox'][1]<580) or
             (key=='movement' and 7<=u['order']<=39))}
        actual=refs(table['rows'])
        require(len(actual)==len(set(actual)) and set(actual)==expected,'Table occurrence omission/duplication: '+key)
    require(len(cells)==len({c['id'] for c in cells})==418 and absent==26 and allrows==48,'Wrong complete table coverage')
    clauses=refs(s['clauses']); expected={u['id'] for u in units if
        (u['page']==133 and u['order'] in (2,261,468,469)) or (u['page']==134 and u['order'] in (1,40))}
    require(len(clauses)==6 and set(clauses)==expected,'Missing substantive qualification')
    require({x['key'] for x in transcript['anchors']}=={c['key'] for c in s['clauses']},'Missing manual anchors')
    for a in transcript['anchors']:
        text=' '.join(q['quote'] for c in s['clauses'] if c['key']==a['key'] for q in c['sources'])
        require(normal(a['quote']) in normal(text),'Wrong clause anchor '+a['key'])
    same(transcript['pages_reviewed'],list(PAGES),'Incomplete image review')
    for key in ('reported_interpretation','distinctions'):same(s[key],transcript[key],'Unreviewed interpretation '+key)
    old=read(prior.HERE/'reading.json')
    same({k:v for k,v in reading.items() if k!='associates_evidence'},old,'Complete 041 reading changed')
    prior.source_check(old,read(prior.HERE/'source-units.json'),read(prior.HERE/'image-transcript.json'))
    return {'local_occurrences':582,'combined_occurrences':len(combined_units(units)),
        'table_rows':48,'printed_cells':418,'not_printed_positions':26,
        'unknown_dashes':sum(c['value'] is None for c in cells),'clause_groups':6,
        'complete_prior_fields_preserved':True,'financial_or_legal_truth_verified':False}


def arithmetic_diagnostics(reading):
    tables=reading['associates_evidence']['tables'];rows=tables[2]['rows'];reconciliations=[]
    for col in range(3):
        known=[r['cells'][col]['value'] for r in rows[:-1]]
        total=rows[-1]['cells'][col]['value'];subtotal=sum(x for x in known if x is not None)
        reconciliations.append({'printed_date':tables[2]['date_sources'][col]['quote'],
            'sum_known':subtotal,'closing':total,'unknown_positions':sum(x is None for x in known),
            'residual_from_known':total-subtotal,'unknown_values_inferred':False})
    return {'role':'EXPLANATORY_ONLY','movements':reconciliations,
        'december_profit_table':29977,'december_profit_movement':16792,
        'difference':29977-16792,'equals_printed_june_2009':13185,
        'reconciliation_cause_proven':False}


def full_graph_preflight(candidate,reading,graph):
    namespace={'__name__':'legalmath.prospectus.successor._associates_candidate','__package__':'legalmath.prospectus.successor'}
    exec(compile(candidate,'candidate-statement_cells.py','exec'),namespace)
    packet={'version':'source-statement-cells.v1','profile':PROFILE,'document':DOCUMENT,'graph_sha256':digest(graph),
        'review':{'kind':'DEVELOPMENT','reviewer':'Original source mappings','reason':'Actual full-graph preflight'},'reading':reading}
    admitted=namespace['admit'](graph,packet)
    bad=deepcopy(graph);bad['units']=[u for u in bad['units'] if u['id']!='bes-interim-h1-2010:p133:l0']
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
    reading=deepcopy(read(prior.HERE/'reading.json'));reading['associates_evidence']=associates_reading(units)
    checked=source_check(reading,units,transcript);all_units=combined_units(units)
    save(HERE/'source-units.json',units);save(HERE/'reading.json',reading)
    entry={'document':DOCUMENT,'source':PDF,'reading':compact_digest(reading),'pages_digest':compact_digest(all_units),
        'pages':sorted({u['page'] for u in all_units}),'occurrences':len(all_units),
        'reading_fields':list(read(prior.HERE/'registry-entry.json')['reading_fields'])+['associates_evidence']}
    original=(PREP/'baseline/statement_cells.py').read_text()
    require(PROFILE not in original and original.count('PROFILES = {')==1,'Baseline registry changed')
    candidate=original.replace('PROFILES = {\n','PROFILES = {\n    '+repr(PROFILE)+': '+repr(entry)+',\n',1)
    graph=read(BASE/'attempt-007/products.json.gz')['P1']['payload']['graph']
    save(HERE/'full-graph-preflight.json',full_graph_preflight(candidate,reading,graph))
    (HERE/'candidate-statement_cells.py').write_text(candidate);save(HERE/'registry-entry.json',entry)
    names=['reading.json','source-units.json','registry-entry.json','candidate-statement_cells.py',
        'image-transcript.json','SOURCE-REVIEW.md','images.json','full-graph-preflight.json']
    save(HERE/'candidate-freeze.json',{'bindings':{n:sha(HERE/n) for n in names},'candidate_sha256':digest(candidate.encode())})
    from legalmath.prospectus.successor import statement_cells as cells
    try:cells.admit({'units':all_units},supplied({'units':all_units}))
    except ValueError as exc:require('Unsupported source statement' in str(exc),'Unexpected baseline refusal')
    else:raise ValueError('New profile already supported')
    save(HERE/'source-check.json',{'status':'PASS',**checked,'baseline_gap':'Note 27 profile unsupported','source_review':common.ref(review)})



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
            'reason':'Complete 041 plus Note 27; acquisition cost, carrying amounts, economic interests, profit shares and printed periods remain distinct'},
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
    changes={k:(lambda s,k=k:s['distinctions'].update({k:True})) for k in read(HERE/'reading.json')['associates_evidence']['distinctions']}
    changes.update({
        'changed-interest':lambda s:s['tables'][1]['rows'][16]['cells'][0].update(value='50.00'),
        'cost-book-confusion':lambda s:s['tables'][1]['rows'][16]['cells'][3].update(value=11497),
        'unicre-excluded':lambda s:s['tables'][1]['rows'].pop(16),
        'row-duplicated':lambda s:s['tables'][0]['rows'].append(deepcopy(s['tables'][0]['rows'][0])),
        'period-changed':lambda s:s['tables'][0]['date_sources'][11].update(quote='31.12.2009'),
        'blank-filled':lambda s:s['tables'][0]['rows'][-1]['cells'][0].update(value=0,status='SOURCE_NUMBER'),
        'unknown-zero':lambda s:s['tables'][2]['rows'][1]['cells'][0].update(value=0,status='SOURCE_NUMBER'),
        'reserve-sign':lambda s:s['tables'][2]['rows'][4]['cells'][0].update(value=19580),
        'wrong-unit':lambda s:s['tables'][1]['rows'][0]['cells'][0].update(unit='EUR thousands'),
        'movement-lost':lambda s:s['tables'][2]['rows'].pop(),
        'clause-lost':lambda s:s['clauses'].pop(),
        'influence-lost':lambda s:s['reported_interpretation'].update(influence='All holdings below 20 percent excluded'),
        'authority-resolved':lambda s:s['source_scope'].update(source_authority_or_incorporation_resolved=True)})
    for name,change in changes.items():
        bad=supplied(graph);change(bad['reading']['associates_evidence'])
        try:cells.admit(graph,bad)
        except ValueError as exc:
            require('reading differs' in str(exc),'Unexpected reading refusal')
            rows.append({'case':name,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else:raise ValueError('Altered reading accepted: '+name)
    for name in ('missing-page','context-occurrence-lost','source-hash','geometry','duplicate-occurrence'):
        g=deepcopy(graph)
        if name=='missing-page':g['units']=[u for u in g['units'] if u['page']!=134]
        elif name=='context-occurrence-lost':g['units']=[u for u in g['units'] if u['id']!='bes-interim-h1-2010:p133:l0']
        elif name=='source-hash':next(u for u in g['units'] if u['page']==133)['source_sha256']='0'*64
        elif name=='geometry':next(u for u in g['units'] if u['id']=='bes-interim-h1-2010:p133:l23')['bbox'][1]+=4
        else:g['units'].append(deepcopy(next(u for u in g['units'] if u['page']==133)))
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
    require(digest(before)==previous['answer_sha256'],'Complete041baseline answer changed')
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
    for key in baseline_reading: same(before['source_statement_cells'][key],after['source_statement_cells'][key],'Lost041field '+key)
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
          24:'h1_cross_note_consumer',25:'h1_securitisation_consumer',26:'h1_fair_value_consumer',28:'h1_risk_native_consumer',29:'h1_events_consumer',30:'h1_financial_policies_consumer',32:'h1_investment_hedges_consumer',33:'h1_income_collateral_consumer',35:'h1_afs_disclosures_consumer',36:'h1_critical_judgments_consumer',37:'h1_trading_balances_consumer',39:'h1_related_parties_consumer',41:'h1_group_structure_consumer'}
    for n,key in keys.items():
        receipt=read(BASE/f'attempt-{n:03d}/ordinary.json.gz')
        answer={**before,**receipt['replacements'],'source_statement_cells':receipt['addition']}
        require(digest(answer)==receipt['answer_sha256'],'Complete prior answer changed: '+str(n))
        composed[key]=answer
        require(digest(composed)==receipt['full_composed_sha256'],'Complete prior composition changed: '+str(n))
    composed['h1_associates_consumer']=after
    receipt={'status':'PASS','prior_complete_answer_sha256':digest(before),'answer_sha256':digest(after),
        'prior_full_composed_sha256':previous['full_composed_sha256'],'full_composed_sha256':digest(composed),
        'reading_sha256':compact_digest(reading),'replacements':replacements,'addition':body,'controls':cases,
        'source_check':checked,'arithmetic':arithmetic_diagnostics(reading),'imports':imported,'whole_task_complete':False,'source_truth_established':False,
        'recipe':'Reconstruct 041 from 007; preserve 016/017 and 021/022/023/024/025/026/028/029/030/032/033/035/036/037/039/041 compositions; add 042 as h1_associates_consumer'}
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
        elif change=='changed_p2': p2['source_statement_cells']['reading']['associates_evidence']['distinctions']['current_ifrs_treatment_verified']=True
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
    rows.append({'requirement':'Original Note 27 dated financial information, interests, book values, profit shares and movements with complete 041 retained',
                 'status':'THIS_ATTEMPT_MUST_PASS; see actual stage results'})
    inventory=deepcopy(read(prior.HERE/'note-inventory.json'))
    for row in inventory['notes']:
        if row['note']==1:row['status']='RETAINED_FINITE_INTEGRATION'
        elif row['note']==27:row['status']='THIS_ATTEMPT_SUBJECT_TO_STAGE_RESULTS'
    save(HERE/'note-inventory.json',inventory)
    save(HERE/'requirements.json',{'rows':rows,'original_task_acceptance':False,
        'external_adviser_opinion_required':False,
        'next_discriminating_work':'Reconcile remaining accounting policies and uncovered notes with the actual retained full-page/source reading coverage; source authority, controlling edition and incorporation remain.'})

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
            command(name,[python,'-I','-B',str(ROOT/SELF),'worker-'+name],360)
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
    (HERE/'RESULT.md').write_text('# Original investments-in-associates disclosures\n\n'+('Finite source/consumer integration passed. ' if passed else 'Campaign did not pass. ')
        +'Actual stages: '+json.dumps(outcomes)+'.\n\n'
        +'Note 27 retains financial information, economic interests, cost, book values, profit shares and signed movements with printed dates. '
        +'Blank cells remain unprinted and dashes remain unknown; the comparative profit difference remains explicit without a proven cause. '
        +'The full 041 answer and all original compositions including supplied OCR risk tables remain preserved. '
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
