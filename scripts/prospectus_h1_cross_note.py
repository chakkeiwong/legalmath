"""Bounded Note10/21 source comparisons and full answer delivery."""
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
from scripts import prospectus_h1_debt_securities as prior
from scripts import prospectus_h1_statement_consumer as common

read, save, sha, digest = prior.read, prior.save, prior.sha, prior.digest
compact_digest, same, require, rel = prior.compact_digest, prior.same, prior.require, prior.rel
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
BASE = AUTH / 'attempts/source-bes-dep-05'
PREP = AUTH / 'reviews/h1-cross-note-387'
HERE = BASE / 'attempt-024'
SELF = 'scripts/prospectus_h1_cross_note.py'
PLAN = 'docs/plans/prospectus-h1-cross-note-2026-10-21.md'
PRODUCTION = prior.PRODUCTION
PROFILE = 'bes-h1-2010-statements-cross-notes.v4'
DOCUMENT, PDF = prior.DOCUMENT, prior.PDF
PAGES = (107, 123, 124, 125)
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
    paths.add(AUTH/'revisions/0387.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH/'program.json').stat().st_size-start['program_bytes'])
    seconds = sum(read(p)['wall_seconds'] for d in (PREP, HERE) for p in d.glob('commands/*.json'))
    return {'new_bytes': size, 'new_measured_seconds': seconds, 'new_control_seconds': 60,
        'prior_known_bytes': start['prior_known_bytes'], 'prior_known_seconds': start['prior_known_seconds'],
        'known_cumulative_bytes': start['prior_known_bytes']+size,
        'known_cumulative_seconds': start['prior_known_seconds']+seconds+60,
        'earlier_manual_and_unmeasured_costs': 'UNKNOWN; history retained',
        'execution_allowed': size+reserve < 110*1024**2 and seconds < 600}


def prepare():
    tick = time.monotonic(); auth = authority(); old = read(AUTH/'program.json')
    require(old['revision'] == 386 and not PREP.exists() and not HERE.exists(), 'Fresh386 required')
    events = auth.events()
    attempts = [e['attempt'] for e in events if e['kind']=='ADMIT' and e['budget_key']=='source-bes-dep-05']
    require(len(attempts)==old['budgets']['source-bes-dep-05']['maximum_new_attempts']==23, 'Retain23attempts')
    require(read(prior.HERE/'result.json')['status']=='PASS', '023 must pass')
    protected = {}
    for n in (7, 15, 16, 17, 21, 22, 23):
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
    names = [PLAN, SELF, prior.SELF, prior.prior.SELF, common.SELF, 'pyproject.toml', *TESTS,
        rel(BASE/'attempt-001/interim.pdf'), rel(BASE/'attempt-007/products.json.gz'),
        rel(BASE/'attempt-007/scope-consumer.json.gz'), rel(BASE/'attempt-015/source-units.json'),
        rel(BASE/'attempt-015/profile.json'), rel(common.TRANSCRIPT),
        rel(common.PREP/'reading.json'), rel(BASE/'attempt-016/answer-supplement.json.gz'),
        rel(BASE/'attempt-017/composition.json'), rel(BASE/'attempt-017/answer-delta.json.gz'),
        rel(BASE/'attempt-021/ordinary.json.gz'), rel(BASE/'attempt-022/ordinary.json.gz'),
        rel(BASE/'attempt-022/reading.json'), rel(BASE/'attempt-022/source-units.json'),
        rel(BASE/'attempt-022/image-transcript.json'), rel(prior.HERE/'ordinary.json.gz'),
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
    new = deepcopy(old); new['revision'] = 387
    task = next(t for t in new['tasks'] if t['id']=='source-bes-dep-05')
    task.update(dossier=PLAN, pre_admission_review=PLAN, build_criteria_scope=[],
        reason='Deliver original Note10/21 and compare buyback periods/collateral without invented reconciliation; preserve023and all authority limits')
    task['inputs'] = sorted((set(task['inputs'])-{PRODUCTION}) | set(protected) |
                           {rel(PREP/'freeze.json'), rel(PREP/'config.json')})
    bounds = {'measured_seconds': 600, 'control_seconds': 60, 'new_bytes': 112*1024**2,
        'failure_reserve': 2*1024**2, 'previous_known_bytes': previous['known_cumulative_bytes'],
        'previous_known_seconds': previous['known_cumulative_seconds'], 'unchanged_retries': 0}
    task['cross_note_evidence'] = {'version': PROFILE, 'freeze': rel(PREP/'freeze.json'), 'bounds': bounds,
        'success_dependencies': DEPENDENCIES, 'original_task_acceptance': False}
    new['budgets']['source-bes-dep-05']['maximum_new_attempts'] = 24
    routes = read(ROOT/old['continuation_review']['routes']); routes['baseline_revision'] = 387
    for row in routes['tasks']:
        if row['task']==task['id']:
            row.update(task_sha256=compact_digest(task), dossier=PLAN, phase=0,
                remaining='023Note32complete; linked Note10/21readings and wider source coverage/authority remain.',
                next_action='Execute024original cross-note review,actual normal/installed evidence and controls; inventory coverage,record,refresh and continue.',
                stop_condition='24retained admissions;600+60seconds and112MiB new; no unchanged retry; retain all costs/failures.')
    save(PREP/'routes.json', routes)
    new['continuation_review'].update(plan=PLAN, routes=rel(PREP/'routes.json'))
    new['continuation_review']['bindings'].pop(PRODUCTION, None)
    new['continuation_review']['bindings'].update({n: sha(ROOT/n) for n in
        (PLAN, rel(PREP/'routes.json'), rel(PREP/'freeze.json'), rel(PREP/'baseline/statement_cells.py'))})
    require(old['obligations']==new['obligations'] and old['build_contract']==new['build_contract'], 'Scope changed')
    raw = (json.dumps(new, ensure_ascii=False, indent=2)+'\n').encode()
    source_bytes = sum(p.stat().st_size for p in (ROOT/'src/legalmath').rglob('*')
                       if p.is_file() and '__pycache__' not in p.parts)
    forecast = costs()['new_bytes']+2*len(raw)+3*source_bytes+18*1024**2
    require(forecast < 110*1024**2, 'Forecast exceeds reservation')
    with (PREP/'proposal.json').open('xb') as stream: stream.write(raw)
    from legalmath.prospectus.execution_authority import digest as adigest
    save(PREP/'review.json', {'baseline': adigest(old), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Complete Note10/21source-to-answer dependencies; preserve all023content',
                    'Keep mismatched buyback periods and impairment categories explicit',
                    'Retain23admissions and all original requirements'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN, 'forecast_new_bytes': forecast,
            'no_proxy_promotion': 'Source image/geometry and full downstream evidence; identity and arithmetic do not prove rights or financial truth'},
        'evidence_contract': {'question': 'Do original Note10/21reach the answer without forced period reconciliation or unsupported collateral/impairment conclusions?',
            'primary': 'Original image transcript/quotes/geometry,full023preservation and actual normal/installed corruption refusals',
            'promotion_veto': ['Omitted source/footnote','Wrong marker/unit/period/issuer','Unsupported right','Wrong import','Accepted corruption'],
            'continuation_veto': ['Invalid authority','Corrupt shared evidence','Spent resources'],
            'not_concluded': ['Automatic extraction','Financial truth','Actual instrument entitlement','Current law','Whole source/build']},
        'budget_revision': {'budget_key': 'source-bes-dep-05', 'previous_maximum': 23, 'new_maximum': 24,
            'retained_attempts': attempts, 'reason': 'New original Note10/21dependencies, not replay of023',
            'next_discriminating_check': 'Complete referenced notes and cross-note differences delivered with source-specific refusals',
            'stop_condition': bounds, 'same_scope_authorization': 'Recover and continue original build'}})
    save(PREP/'commands/preparation.json', {'wall_seconds': time.monotonic()-tick,
        'command': [sys.executable, '-B', '-m', 'scripts.prospectus_h1_cross_note', 'prepare']})
    return {'status': 'PREPARED', 'revision': 387, 'forecast_new_bytes': forecast, 'resources': costs()}


def frozen():
    auth = authority(); admission = read(HERE/'admission.json')
    from legalmath.prospectus.execution_authority import digest as adigest
    require(adigest(read(AUTH/'program.json'))==admission['program_sha256'] and
            auth.binding(admission['task_spec'])==admission['binding'], 'Unchanged admission required')
    f = read(PREP/'freeze.json')
    require(all(sha(ROOT/n)==h for n, h in f['bindings'].items()), 'Frozen input changed')
    expected = read(HERE/'candidate-production.json')[PRODUCTION] if (HERE/'candidate-production.json').exists() else f['baseline_sha256']
    require(sha(ROOT/PRODUCTION)==expected, 'Registry outside implementation window')


def command(name, argv, timeout=150):
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


def cross_note_reading(units, transcript):
    lookup={(u['page'],u['order']):u for u in units}
    def q(page,line):
        u=lookup[page,line]; return {'id':u['id'],'quote':u['raw']}
    def qs(page,first,last): return [q(page,i) for i in range(first,last+1)]
    def number(page,line):
        quote=q(page,line); token=''.join(quote['quote'].split())
        value=None if token=='-' else int('-'+token[1:-1] if token.startswith('(') else token)
        return {**quote,'value':value,'status':'DASH_UNKNOWN' if value is None else 'SOURCE_NUMBER','unit':'EUR thousands'}
    note10={'headers':qs(107,3,6)+[q(107,17)],'periods':['six_months_ended_2010-06-30','six_months_ended_2009-06-30'],
        'rows':[{'label':q(107,7+i),'cells':[number(107,18+i),number(107,28+i)]} for i in range(10)],
        'totals':[number(107,38),number(107,39)],'dash_imputed_zero':False}
    loan_spec=[
        (7,36,43,'domestic_corporate'),(8,37,44,'domestic_corporate'),(9,38,45,'domestic_corporate'),
        (10,39,46,'domestic_corporate'),(11,40,47,'domestic_corporate'),(12,41,48,'domestic_corporate'),(13,42,49,'domestic_corporate'),
        (15,50,52,'domestic_retail'),(16,51,53,'domestic_retail'),(5,54,55,'domestic_total'),
        (19,56,63,'foreign_corporate'),(20,57,64,'foreign_corporate'),(21,58,65,'foreign_corporate'),
        (22,59,66,'foreign_corporate'),(23,60,67,'foreign_corporate'),(24,61,68,'foreign_corporate'),(25,62,69,'foreign_corporate'),
        (27,70,72,'foreign_retail'),(28,71,73,'foreign_retail'),(17,74,75,'foreign_total'),
        (30,76,80,'overdue_age'),(31,77,81,'overdue_age'),(32,78,82,'overdue_age'),(33,79,83,'overdue_age'),
        (29,84,85,'overdue_total'),(None,86,87,'gross_total'),(34,88,89,'impairment_deduction'),(None,90,91,'net_total')]
    loan_rows=[{'label':q(123,label) if label is not None else None,'role':role,'cells':[number(123,a),number(123,b)]}
               for label,a,b,role in loan_spec]
    loans={'headers':[q(123,n) for n in (2,3,4,35)],'hierarchy_sources':[q(123,n) for n in (5,6,14,17,18,26,29,34)],
        'dates':['2010-06-30','2009-12-31'],'rows':loan_rows,
        'unlabelled_totals':'Gross and net roles follow source position and deduction; no invented printed label',
        'subtotals_not_additive_to_children':True}
    movements={'headers':[q(124,n) for n in (10,11,12,13,14)],
        'printed_period_heading':q(124,11),'dates':['2010-06-30','2009-12-31','2009-06-30'],
        'period_caution':'Spanning Six month period ended heading retained; December column not silently relabelled as annual',
        'rows':[{'label':q(124,15+i),'cells':[number(124,n+i) for n in (21,27,33)]} for i in range(6)],
        'closing':{'label':q(124,39),'cells':[number(124,n) for n in (40,41,42)]},
        'unwind_sources':qs(124,43,44),
        'unwind_treatment':'Source describes interest on overdue loans recognised as interest and similar income; impairment calculated using discounted cash flows'}
    layout2010=[(16,[17,18,19,35,36,37,38]),(20,[21,22,39,40,41,42,43]),
                (27,[23,24,44,45,46,47,48]),(28,[25,26,49,50,51,52,53])]
    layout2009=[(73,list(range(74,81))),(81,list(range(82,89))),(103,list(range(89,96))),(104,list(range(96,103)))]
    impairment={'columns':['individual_gross','individual_impairment','portfolio_gross','portfolio_impairment','total_gross','total_impairment','net_loans'],
        '2010-06-30':{'headers':qs(125,2,15)+qs(125,29,34),'rows':[{'label':q(125,label),'cells':[number(125,n) for n in nums]} for label,nums in layout2010]},
        '2009-12-31':{'headers':qs(125,54,72),'rows':[{'label':q(125,label),'cells':[number(125,n) for n in nums]} for label,nums in layout2009]},
        'method_basis_is_not_default_status':True,'portfolio_classification_proves_safety':False,
        'individual_basis_sources':qs(125,106,107),
        'individual_basis_description':'Includes loans with objective evidence of impairment,overdue loans over90days and restructured loans',
        'restructured':{'sources':qs(125,108,111),'unit':'EUR thousands','values':[98243,103197],
            'dates':['2010-06-30','2009-12-31'],'description':'Source cites Bank of Portugal definition:previously overdue,considered performing through restructuring',
            'definition_independently_verified':False,'performing_implies_no_impairment':False},
        'interest':{'sources':qs(125,112,114),'unit':'EUR million','values':['178.2','395.6'],
            'comparator_date':'2009-12-31','scope':'these loans; preserve original referent without selecting a narrower set',
            'includes_unwind_of_discount_for_overdue_loans':True,'period_equivalence_established':False}}
    baseline=read(prior.HERE/'reading.json')
    return {'source_groups':{str(p):[q(p,u['order']) for u in units if u['page']==p] for p in PAGES},
        'other_operating':note10,'loans':loans,'impairment_movements':movements,'impairment_detail':impairment,
        'securitised_loans':{'sources':qs(124,1,5),'unit':'EUR million','values':['4214.2','4346.4'],
            'dates':['2010-06-30','2009-12-31'],'measurement':'Net of impairment; consolidation of securitisation vehicles',
            'liability_description':'Related liabilities booked under debt securities issued; Notes32and42',
            'policy2_2_resolved':False,'note42_resolved':False,'loan_asset_equals_debt_liability':False},
        'collateral_comparison':{'note21_sources':qs(124,6,7),'note32_sources':deepcopy(baseline['debt_securities']['covered_bonds']['reported_collateral']['sources']),
            'unit':'EUR thousands','values':[4038230,4053833],'dates':['2010-06-30','2009-12-31'],
            'reported_amounts_agree':True,'source_reference_read':True,'legal_eligibility_established':False,
            'particular_holder_privilege_established':False},
        'buyback_comparison':{'note10_row':deepcopy(note10['rows'][1]),'note10_periods':note10['periods'],
            'note35':deepcopy(baseline['debt_context']['buyback_gains']),
            'reference_read':True,'amounts_and_periods_reconciled':False,'typo_established':False,'rounding_policy_established':False,
            'conclusion':'Note10has4251/106662thousand forJune2010/June2009; Note35has4.2/110.5million withJune2010/December2009 wording. Preserve both; no common comparator or exact reconciliation established'},
        'source_context':{'origin':'SUPPLIED_DEVELOPMENT_READING','source_authenticity':'NOT_ESTABLISHED',
            'incorporation_status':'UNRESOLVED','all_notes_read':False,'cashflows_derived':False,
            'outside_new_interpretation':['Page107Note11retained as context; prior supplement preserved'],
            'historical_source_claims_are_verified_current_law':False}}


def source_check(reading,units,transcript):
    require(len(units)==331 and len({u['id'] for u in units})==331,'Complete331source occurrences required')
    lookup={u['id']:u for u in units}; source=reading['cross_note_evidence']
    require(all(u['source_sha256']==PDF and u['visible'] and u['page'] in PAGES for u in units),'Source changed')
    quoted=[q for group in source['source_groups'].values() for q in group]
    require(len(quoted)==331 and {q['id'] for q in quoted}==set(lookup),'Incomplete context partition')
    require(all(q['quote']==lookup[q['id']]['raw'] for q in quoted),'Changed contextual quote')
    def verify_new_quotes(value):
        if isinstance(value,dict):
            if 'id' in value and 'quote' in value and value['id'] in lookup:
                require(value['quote']==lookup[value['id']]['raw'],'Changed new source quote')
            for v in value.values(): verify_new_quotes(v)
        elif isinstance(value,list):
            for v in value: verify_new_quotes(v)
    verify_new_quotes(source)
    old=read(prior.HERE/'reading.json')
    same({k:v for k,v in reading.items() if k!='cross_note_evidence'},old,'023reading changed')
    prior.source_check(old,read(prior.HERE/'source-units.json'),read(prior.HERE/'image-transcript.json'))
    def rowcheck(row,expected,alignment=True):
        cells=row['cells']; require(len(cells)==len(expected),'Wrong number of cells')
        xs=[];ys=[]
        for cell,value in zip(cells,expected):
            u=lookup[cell['id']]
            require(cell['quote']==u['raw'] and cell['value']==value and cell['unit']=='EUR thousands','Image/quote/amount disagreement')
            require(cell['status']==('DASH_UNKNOWN' if value is None else 'SOURCE_NUMBER'),'Unknown coerced')
            xs.append((u['bbox'][0]+u['bbox'][2])/2);ys.append(u['bbox'][1])
        require(xs==sorted(xs) and max(ys)-min(ys)<3,'Wrong numeric row/column')
        if alignment and row.get('label'):
            u=lookup[row['label']['id']]
            require(row['label']['quote']==u['raw'] and abs(u['bbox'][1]-ys[0])<3,'Wrong label association')
    note=source['other_operating']; require(len(note['rows'])==len(transcript['note10'])==10,'Incomplete Note10')
    normalize=lambda text: ''.join(text.split())
    same([normalize(q['quote']) for q in note['headers']],
         [normalize(t) for t in transcript['note10_headers']],'Note10header mismatch')
    for row,t in zip(note['rows'],transcript['note10']):rowcheck(row,t)
    same([c['value'] for c in note['totals']],transcript['note10_totals'],'Wrong Note10totals')
    require(sum(c['value'] is None for r in note['rows'] for c in r['cells'])==1,'Missing Note10unknown')
    require(len(source['loans']['rows'])==len(transcript['loans'])==28,'Incomplete loan table')
    for row,t in zip(source['loans']['rows'],transcript['loans']):rowcheck(row,t,alignment=row['role'] not in ('domestic_total','foreign_total','overdue_total'))
    move=source['impairment_movements']; require(len(move['rows'])==len(transcript['impairment_movements'])==6,'Missing impairment movement')
    same([normalize(q['quote']) for q in move['headers']],
         [normalize(t) for t in transcript['impairment_headers']],'Impairment header mismatch')
    for row,t in zip(move['rows'],transcript['impairment_movements']):rowcheck(row,t)
    rowcheck(move['closing'],transcript['impairment_closing'])
    for period in ('2010-06-30','2009-12-31'):
        rows=source['impairment_detail'][period]['rows']; require(len(rows)==len(transcript['impairment_detail'][period])==4,'Missing impairment classification')
        for row,t in zip(rows,transcript['impairment_detail'][period]):rowcheck(row,t)
        for row in rows:
            a,b,c,d,e,f,g=[cell['value'] for cell in row['cells']]
            require(a+c==e and b+d==f and e-f==g,'Impairment source arithmetic mismatch')
        for c in range(7):require(sum(r['cells'][c]['value'] for r in rows[:3])==rows[3]['cells'][c]['value'],'Impairment category totals mismatch')
    net=[c['value'] for c in source['loans']['rows'][-1]['cells']]
    balance=next(r for r in old['tables']['assets']['rows'] if r['label'] and 'Loans and advances to customers' in r['label']['quote'])
    same(net,[c['value'] for c in balance['cells']],'Statement loans mismatch')
    for i in range(2):
        require(source['loans']['rows'][-3]['cells'][i]['value']+source['loans']['rows'][-2]['cells'][i]['value']==net[i],'Gross less impairment mismatch')
    for i in range(3):require(sum(r['cells'][i]['value'] for r in move['rows'])==move['closing']['cells'][i]['value'],'Impairment movement mismatch')
    require(source['collateral_comparison']['values']==old['debt_securities']['covered_bonds']['reported_collateral']['values'],'Collateral source comparison mismatch')
    return {'new_occurrences':331,'prior_occurrences':1329,'total_occurrences':1660,'numeric_positions':155,
        'note10_rows':10,'loan_rows':28,'impairment_movement_positions':21,'impairment_detail_positions':56,
        'unknown_dashes':1,'prior_fields_preserved':True,'arithmetic_role':'EXPLANATORY_ONLY',
        'buyback_periods_reconciled':False,'collateral_legal_truth_established':False}


def source_worker():
    units=original_units(); transcript=read(HERE/'image-transcript.json'); review=HERE/'SOURCE-REVIEW.md'
    require(review.is_file() and len(review.read_text())>1000, 'Substantive source review required')
    for item in read(HERE/'images.json'): require(sha(ROOT/item['path'])==item['sha256'], 'Source image changed')
    reading=deepcopy(read(prior.HERE/'reading.json')); reading['cross_note_evidence']=cross_note_reading(units,transcript)
    checked=source_check(reading,units,transcript)
    all_units=sorted(read(BASE/'attempt-015/source-units.json')+read(BASE/'attempt-022/source-units.json')+read(prior.HERE/'source-units.json')+units,
                     key=lambda u:(u['page'],u['order'],u['id']))
    save(HERE/'source-units.json',units); save(HERE/'reading.json',reading)
    entry={'document':DOCUMENT,'source':PDF,'reading':compact_digest(reading),'pages_digest':compact_digest(all_units),
        'pages':sorted({u['page'] for u in all_units}),'occurrences':len(all_units),
        'reading_fields':['source_groups','tables','terms','scope','debt_context','debt_securities','cross_note_evidence']}
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
    save(HERE/'source-check.json',{'status':'PASS',**checked,'baseline_gap':'Note10/21profile unsupported','source_review':common.ref(review)})


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
            'reason':'Complete023plus original Note10/21; mismatched periods and all financial/legal limits retained'},
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
    graph={'units':read(BASE/'attempt-015/source-units.json')+read(BASE/'attempt-022/source-units.json')+read(prior.HERE/'source-units.json')+read(HERE/'source-units.json')}
    changes={
        'forced-reconciliation':lambda d:d['buyback_comparison'].update(amounts_and_periods_reconciled=True),
        'typo-assumed':lambda d:d['buyback_comparison'].update(typo_established=True),
        'rounding-assumed':lambda d:d['buyback_comparison'].update(rounding_policy_established=True),
        'wrong-comparator':lambda d:d['other_operating']['periods'].__setitem__(1,'year_ended_2009-12-31'),
        'wrong-gain':lambda d:d['other_operating']['rows'][1]['cells'][1].update(value=110500),
        'dash-zero':lambda d:d['other_operating']['rows'][7]['cells'][0].update(value=0,status='SOURCE_NUMBER'),
        'missing-income-row':lambda d:d['other_operating']['rows'].pop(),
        'missing-loan-row':lambda d:d['loans']['rows'].pop(),
        'subtotals-double-counted':lambda d:d['loans'].update(subtotals_not_additive_to_children=False),
        'impairment-sign':lambda d:d['loans']['rows'][-2]['cells'][0].update(value=1681539),
        'changed-period':lambda d:d['impairment_movements']['dates'].__setitem__(1,'2009-06-30'),
        'lost-unwind':lambda d:d['impairment_movements'].update(unwind_sources=[]),
        'individual-as-defaulted':lambda d:d['impairment_detail'].update(method_basis_is_not_default_status=False),
        'portfolio-safe':lambda d:d['impairment_detail'].update(portfolio_classification_proves_safety=True),
        'restructured-safe':lambda d:d['impairment_detail']['restructured'].update(performing_implies_no_impairment=True),
        'definition-verified':lambda d:d['impairment_detail']['restructured'].update(definition_independently_verified=True),
        'interest-period-equivalent':lambda d:d['impairment_detail']['interest'].update(period_equivalence_established=True),
        'loan-as-liability':lambda d:d['securitised_loans'].update(loan_asset_equals_debt_liability=True),
        'securitisation-unit':lambda d:d['securitised_loans'].update(unit='EUR thousands'),
        'note42-resolved':lambda d:d['securitised_loans'].update(note42_resolved=True),
        'collateral-eligible':lambda d:d['collateral_comparison'].update(legal_eligibility_established=True),
        'holder-privilege':lambda d:d['collateral_comparison'].update(particular_holder_privilege_established=True),
        'incorporation-assumed':lambda d:d['source_context'].update(incorporation_status='CONFIRMED')}
    rows=[]
    for name,change in changes.items():
        bad=supplied(graph); change(bad['reading']['cross_note_evidence'])
        try: cells.admit(graph,bad)
        except ValueError as exc: rows.append({'case':name,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else: raise ValueError('Altered interpretation accepted: '+name)
    for name in ('missing-page','source-hash','geometry'):
        g=deepcopy(graph)
        if name=='missing-page': g['units']=[u for u in g['units'] if u['page']!=125]
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
    require(digest(before)==previous['answer_sha256'],'Complete023baseline answer changed')
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
    for key in baseline_reading: same(before['source_statement_cells'][key],after['source_statement_cells'][key],'Lost023field '+key)
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
    composed['h1_debt_securities_consumer']=before
    require(digest(composed)==previous['full_composed_sha256'],'Complete023composition changed')
    composed['h1_cross_note_consumer']=after
    receipt={'status':'PASS','prior_complete_answer_sha256':digest(before),'answer_sha256':digest(after),
        'prior_full_composed_sha256':previous['full_composed_sha256'],'full_composed_sha256':digest(composed),
        'reading_sha256':compact_digest(reading),'replacements':replacements,'addition':body,'controls':cases,
        'source_check':checked,'imports':imported,'whole_task_complete':False,'source_truth_established':False,
        'recipe':'Reconstruct023from007and frozen profile; derive021/022from retained replacements/addition and verify; retain016/017/021/022/023 and add024as h1_cross_note_consumer'}
    del composed,before,after,old_answer,answer022
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
        elif change=='changed_p2': p2['source_statement_cells']['reading']['cross_note_evidence']['buyback_comparison']['amounts_and_periods_reconciled']=True
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
    rows.append({'requirement':'Complete Note10/21tables and conditional buyback/collateral source comparisons',
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
        status=('RETAINED_FINITE_INTEGRATION' if number in (32,35) else
                'THIS_ATTEMPT_SUBJECT_TO_STAGE_RESULTS' if number in (10,21) else
                'RETAINED_SUPPLEMENT_ONLY' if number in (11,12,28,36,37,38) else
                'SOURCE_RETAINED_FULL_INTERPRETATION_NOT_ESTABLISHED')
        inventory.append({'note':number,'page':u['page'],'id':u['id'],'quote':raw,'status':status})
    save(HERE/'note-inventory.json',{'scope':'Native original headings61–171; heading detection alone is not semantic coverage',
        'notes':inventory,'policies':{'2.8':'RETAINED_FINITE_INTEGRATION','2.9':'RETAINED_FINITE_INTEGRATION',
        '2.15':'RETAINED_SUPPLEMENT_ONLY','remaining':'NOT_FULLY_INTERPRETED'},
        'task_acceptance':False})
    save(HERE/'requirements.json',{'rows':rows,'original_task_acceptance':False,'external_adviser_opinion_required':False,
        'next_discriminating_work':'Next original linked sources are policy2.2 and Note42securitisation; retain Note10/35period disagreement and source authority limits. Use remaining-note inventory, not a completed install replay.'})


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
        elif name=='tests': command('tests',[str(ROOT/'.venv/bin/python'),'-B','-m','pytest','-q',*TESTS,'--junitxml='+str(HERE/'tests.xml')],150)
        else:
            python=read(PREP/'config.json')['package_python'] if name=='installed' else str(ROOT/'.venv/bin/python')
            command(name,[python,'-I','-B',str(ROOT/SELF),'worker-'+name],150)
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
    (HERE/'RESULT.md').write_text('# Original Note10/21integration\n\n'+('Finite source/consumer integration passed. ' if passed else 'Campaign did not pass. ')
        +'Actual stages: '+json.dumps(outcomes)+'.\n\n'
        +'The complete Note10/21reading preserves operating income,loan breakdown,impairment movements and individual/portfolio classifications. '
        +'The buyback periods/amounts remain distinct; matching collateral amounts establish reported consistency only. '
        +'Loan assets and securitisation liabilities,impairment method and default status,and restructuring and safety remain distinct. '
        +'All023fields and016/017/021/022/023compositions are retained through checked lossless recipes.\n\n'
        +'|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|\n|---|---|---|---|---|---|\n'
        +'|'+('Retain finite integration' if passed else 'Retain actual failure')+'|Original images/quotes/geometry and actual full normal/installed answers|See stage records|Remaining notes and authority|Record/refresh; resolve policy2.2/Note42and remaining coverage|Financial truth,current law,holder entitlement,automatic extraction,whole build|\n\n'
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
