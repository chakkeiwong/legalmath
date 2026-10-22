"""Bounded Note32 source review and full ordinary/installed answer delivery."""
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
from scripts import prospectus_h1_debt_context as prior

read, save, sha, digest = prior.read, prior.save, prior.sha, prior.digest
compact_digest, same, require, rel = prior.compact_digest, prior.same, prior.require, prior.rel
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
BASE = AUTH / 'attempts/source-bes-dep-05'
PREP = AUTH / 'reviews/h1-debt-securities-386'
HERE = BASE / 'attempt-023'
SELF = 'scripts/prospectus_h1_debt_securities.py'
PLAN = 'docs/plans/prospectus-h1-debt-securities-2026-10-21.md'
PRODUCTION = prior.PRODUCTION
PROFILE = 'bes-h1-2010-statements-debt-securities.v3'
DOCUMENT, PDF = prior.DOCUMENT, prior.PDF
PAGES = (138, 139, 140)
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
    paths.add(AUTH/'revisions/0386.json')
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
    require(old['revision'] == 385 and not PREP.exists() and not HERE.exists(), 'Fresh385 required')
    events = auth.events()
    attempts = [e['attempt'] for e in events if e['kind']=='ADMIT' and e['budget_key']=='source-bes-dep-05']
    require(len(attempts)==old['budgets']['source-bes-dep-05']['maximum_new_attempts']==22, 'Retain22attempts')
    require(read(prior.HERE/'result.json')['status']=='PASS', '022 must pass')
    protected = {}
    for n in (7, 15, 16, 17, 21, 22):
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
    production = prior.prior.production()
    save(PREP/'baseline/production.json', production)
    names = [PLAN, SELF, prior.SELF, prior.prior.SELF, 'pyproject.toml', *TESTS,
        rel(BASE/'attempt-001/interim.pdf'), rel(BASE/'attempt-007/products.json.gz'),
        rel(BASE/'attempt-007/scope-consumer.json.gz'), rel(BASE/'attempt-015/source-units.json'),
        rel(BASE/'attempt-015/profile.json'), rel(prior.prior.TRANSCRIPT),
        rel(prior.prior.PREP/'reading.json'), rel(BASE/'attempt-016/answer-supplement.json.gz'),
        rel(BASE/'attempt-017/composition.json'), rel(BASE/'attempt-017/answer-delta.json.gz'),
        rel(BASE/'attempt-021/ordinary.json.gz'), rel(prior.HERE/'ordinary.json.gz'),
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
    new = deepcopy(old); new['revision'] = 386
    task = next(t for t in new['tasks'] if t['id']=='source-bes-dep-05')
    task.update(dossier=PLAN, pre_admission_review=PLAN, build_criteria_scope=[],
        reason='Deliver complete original Note32 with guarantee subsets, covered-bond context,42issues and all footnotes; retain022and original authority limits')
    task['inputs'] = sorted((set(task['inputs'])-{PRODUCTION}) | set(protected) |
                           {rel(PREP/'freeze.json'), rel(PREP/'config.json')})
    bounds = {'measured_seconds': 600, 'control_seconds': 60, 'new_bytes': 112*1024**2,
        'failure_reserve': 2*1024**2, 'previous_known_bytes': previous['known_cumulative_bytes'],
        'previous_known_seconds': previous['known_cumulative_seconds'], 'unchanged_retries': 0}
    task['debt_securities'] = {'version': PROFILE, 'freeze': rel(PREP/'freeze.json'), 'bounds': bounds,
        'success_dependencies': DEPENDENCIES, 'original_task_acceptance': False}
    new['budgets']['source-bes-dep-05']['maximum_new_attempts'] = 23
    routes = read(ROOT/old['continuation_review']['routes']); routes['baseline_revision'] = 386
    for row in routes['tasks']:
        if row['task']==task['id']:
            row.update(task_sha256=compact_digest(task), dossier=PLAN, phase=0,
                remaining='022 debt/policy integration complete; Note32 and wider source coverage/authority remain.',
                next_action='Execute023source review, complete actual consumer and adverse controls, offline installed evidence, coverage; record/refresh and continue.',
                stop_condition='23retained admissions;600+60seconds and112MiB new; no unchanged retry; retain all costs/failures.')
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
        'changes': ['Complete Note32source-to-answer dependency; preserve all022content',
                    'Keep guarantee scope,book/nominal values,coupon/yield and derivatives distinct',
                    'Retain22admissions and all original requirements'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN, 'forecast_new_bytes': forecast,
            'no_proxy_promotion': 'Source image/geometry and full downstream evidence; identity and arithmetic do not prove rights or financial truth'},
        'evidence_contract': {'question': 'Does complete original Note32 reach the answer without unsupported guarantee,payoff or repayment conclusions?',
            'primary': 'Original image transcript/quotes/geometry,full022preservation and actual normal/installed corruption refusals',
            'promotion_veto': ['Omitted source/footnote','Wrong marker/unit/period/issuer','Unsupported right','Wrong import','Accepted corruption'],
            'continuation_veto': ['Invalid authority','Corrupt shared evidence','Spent resources'],
            'not_concluded': ['Automatic extraction','Financial truth','Actual instrument entitlement','Current law','Whole source/build']},
        'budget_revision': {'budget_key': 'source-bes-dep-05', 'previous_maximum': 22, 'new_maximum': 23,
            'retained_attempts': attempts, 'reason': 'New original Note32dependency, not replay of022',
            'next_discriminating_check': 'Complete issue/footnote and scope reading delivered with source-specific refusals',
            'stop_condition': bounds, 'same_scope_authorization': 'Recover and continue original build'}})
    save(PREP/'commands/preparation.json', {'wall_seconds': time.monotonic()-tick,
        'command': [sys.executable, '-B', '-m', 'scripts.prospectus_h1_debt_securities', 'prepare']})
    return {'status': 'PREPARED', 'revision': 386, 'forecast_new_bytes': forecast, 'resources': costs()}


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


def securities_reading(units, transcript):
    lookup = {(u['page'],u['order']): u for u in units}
    def q(page, line):
        u = lookup[page,line]; return {'id': u['id'], 'quote': u['raw']}
    def qs(page, first, last): return [q(page,i) for i in range(first,last+1)]
    def number(page, line):
        quote = q(page,line); token = ''.join(quote['quote'].split())
        value = None if token=='-' else int('-'+token[1:-1] if token.startswith('(') else token)
        return {**quote, 'value': value, 'status': 'DASH_UNKNOWN' if value is None else 'SOURCE_NUMBER', 'unit': 'EUR thousands'}
    summary = {'unit_source': q(138,3), 'date_headers': qs(138,9,10),
        'periods': ['2010-06-30','2009-12-31'],
        'rows': [{'label': q(138,4+i), 'cells': [number(138,11+i),number(138,16+i)]} for i in range(5)],
        'totals': [number(138,21),number(138,22)]}
    covered = {'sources': qs(138,25,33), 'headers': qs(138,34,44)+qs(138,51,55),
        'rows': [{'designation': q(138,35+i), 'nominal_value': number(138,45+i), 'book_value': number(138,48+i),
                  'issue_date': q(138,56+i), 'maturity_date': q(138,59+i), 'interest_payment': q(138,62+i),
                  'stated_rate': q(138,65+i), 'reported_rating': q(138,68+i)} for i in range(3)],
        'reported_issuance': {'unit': 'EUR million', 'year_2009': 1000, 'year_2008': 2500, 'programme_maximum': 10000},
        'reported_collateral': {'sources': qs(138,71,72), 'unit': 'EUR thousands',
            'values': [4038230,4053833], 'dates': ['2010-06-30','2009-12-31'], 'note21_resolved': False},
        'reported_legal_context': {'cover_pool': 'Mortgage credit assets and limited classes of other assets; issuer maintains segregation',
            'privilege': 'Source reports statutory special creditor privilege for relevant covered-bond holders',
            'cited_authorities': ['Decree-Law59/2006','Bank of Portugal Regulations5/2006,6/2006,7/2006,8/2006','Bank of Portugal Instruction13/2006'],
            'authorities_verified': False, 'specific_holder_eligibility_established': False},
        'ratings_are_historical_source_labels': True, 'current_rating_established': False,
        'repayment_certainty_established': False, 'complete_contract_terms': False}
    repayments = [27,29,30,31,32]
    movements = {'headers': qs(139,8,16), 'unit_source': q(139,11),
        'columns': ['2009-12-31','issues','repayments','net_repurchase','other_movements','2010-06-30'],
        'rows': [{'label': q(139,1+i), 'cells': [number(139,line) for line in
                  (17+i,22+i,repayments[i],33+i,38+i,43+i)]} for i in range(5)],
        'totals': [number(139,i) for i in range(48,54)], 'footnote_sources': qs(139,54,55),
        'other_movements': ['accrued interest','fair value adjustments','foreign exchange differences'],
        'certificates_of_deposit': {'marker': q(139,28), 'row_index': 1, 'column': 'repayments',
            'net_presentation': True, 'reason': 'Short-term maturity', 'gross_cash_repayment_inferred': False},
        'dash_imputed_zero': False}
    footnotes = {chr(ord('a')+i): q(140,284+i) for i in range(21)}
    rate_notes = {4:'o',5:'p',6:'q',8:'r',9:'s',10:'t',11:'u',13:'b',14:'d',15:'c',
                  17:'e',18:'f',20:'g',21:'h',25:'i',27:'j',28:'k',30:'l',33:'m',35:'n'}
    issues = []
    for i, t in enumerate(transcript['issues']):
        marker = t['marker_line']; key = rate_notes.get(i)
        issues.append({'issuer': q(140,6+i), 'designation': q(140,49+i), 'issue_currency': q(140,113+i),
            'maturity_year': q(140,158+i), 'stated_rate_or_index': q(140,200+i), 'book_value': number(140,242+i),
            'designation_marker': q(140,marker) if marker is not None else None,
            'designation_footnote': footnotes['a'] if marker is not None else None,
            'rate_footnote_key': key, 'rate_footnote': footnotes[key] if key else None,
            'effective_emission_rate_source': footnotes[key] if key is not None and key in 'opqrstu' else None,
            'complete_payoff_terms': False})
    return {'source_groups': {str(p): [q(p,u['order']) for u in units if u['page']==p] for p in PAGES},
        'summary': summary,
        'state_guarantee': {'sources': qs(138,23,24), 'category': 'Bonds', 'unit': 'EUR million',
            'values': [1548,1565], 'dates': ['2010-06-30','2009-12-31'], 'subset_only': True,
            'all_debt_guaranteed': False, 'particular_instrument_covered': 'NOT_ESTABLISHED'},
        'covered_bonds': covered, 'movements': movements,
        'repurchase': {'sources': qs(139,56,58), 'policy': '2.8',
            'treatment': 'Repurchased debt derecognised; carrying amount minus acquisition cost recognised in income',
            'holder_rights_inferred': False},
        'issues': {'scope_sources': qs(140,1,4), 'headers': [q(140,n) for n in (5,48,91,155,156,157)],
            'unit': 'EUR thousands', 'rows': issues, 'footnotes': footnotes,
            'amount_basis': 'Book values at30June2010; issue currencies remain separate descriptors',
            'gross_issues_equal_book_value_sum_assumed': False, 'fixed_coupon_equals_effective_emission_rate': False,
            'embedded_derivative_or_fair_value_option': 'Disjunction as reported; neither branch selected',
            'payoff_formulae_invented': False, 'instrument_match_established': False},
        'source_context': {'reading_kind': 'SUPPLIED_DEVELOPMENT_READING','incorporation_status':'UNRESOLVED',
            'source_authenticity':'NOT_ESTABLISHED','financial_accuracy_proved':False,'automatic_extraction':False,
            'all_notes_read':False,'BES_Finance_standalone_accounts_supplied':False,'cashflows_derived':False,
            'historical_source_claims_are_verified_current_law':False}}


def source_check(reading, units, transcript):
    require(len(units)==445 and len({u['id'] for u in units})==445, 'Complete445source occurrences required')
    lookup = {u['id']:u for u in units}; source = reading['debt_securities']
    require(all(u['source_sha256']==PDF and u['visible'] and u['page'] in PAGES for u in units), 'Source/visibility changed')
    quoted = [q for group in source['source_groups'].values() for q in group]
    require(len(quoted)==445 and {q['id'] for q in quoted}==set(lookup), 'Incomplete source partition')
    def quotes(value):
        if isinstance(value,dict):
            if 'id' in value and 'quote' in value:
                require(value['id'] in lookup and value['quote']==lookup[value['id']]['raw'], 'Changed source quote')
            for v in value.values(): quotes(v)
        elif isinstance(value,list):
            for v in value: quotes(v)
    quotes(source)
    def normalized(text): return ''.join(text.split())
    def rowcheck(cells, expected):
        require(len(cells)==len(expected), 'Transcript column mismatch')
        ys=[]; xs=[]
        for cell, value in zip(cells,expected):
            u=lookup[cell['id']]; ys.append(u['bbox'][1]); xs.append((u['bbox'][0]+u['bbox'][2])/2)
            if 'value' in cell:
                require(cell['value']==value and cell['unit']=='EUR thousands', 'Wrong image amount/table unit')
                require(cell['status']==('DASH_UNKNOWN' if value is None else 'SOURCE_NUMBER'), 'Dash coerced')
            else: require(normalized(cell['quote'])==normalized(value), 'Image/text mismatch: '+cell['id'])
        require(max(ys)-min(ys)<3 and xs==sorted(xs), 'Wrong row/column association')
    require(len(transcript['summary'])==5 and len(source['summary']['rows'])==5, 'Incomplete summary')
    for row, expected in zip(source['summary']['rows'],transcript['summary']): rowcheck(row['cells'],expected)
    same([c['value'] for c in source['summary']['totals']],transcript['summary_totals'],'Summary total mismatch')
    cover_fields=['designation','nominal_value','book_value','issue_date','maturity_date','interest_payment','stated_rate','reported_rating']
    require(len(transcript['covered_bonds'])==len(source['covered_bonds']['rows'])==3, 'Incomplete covered table')
    for row, expected in zip(source['covered_bonds']['rows'],transcript['covered_bonds']):
        rowcheck([row[k] for k in cover_fields],expected)
    require(len(transcript['movements'])==len(source['movements']['rows'])==5, 'Incomplete movements')
    for row, expected in zip(source['movements']['rows'],transcript['movements']): rowcheck(row['cells'],expected)
    same([c['value'] for c in source['movements']['totals']],transcript['movement_totals'],'Movement total mismatch')
    marker=lookup[source['movements']['certificates_of_deposit']['marker']['id']]
    cell=lookup[source['movements']['rows'][1]['cells'][2]['id']]
    require(abs(marker['bbox'][1]-cell['bbox'][1])<3, 'Wrong net-presentation marker')
    fields=['issuer','designation','issue_currency','book_value','maturity_year','stated_rate_or_index']
    require(len(transcript['issues'])==len(source['issues']['rows'])==42, 'Incomplete issue table')
    markers=[]
    for row,t in zip(source['issues']['rows'],transcript['issues']):
        rowcheck([row[k] for k in fields],t['values'])
        marker=row['designation_marker']
        require((marker is not None)==(t['marker_line'] is not None),'Lost source marker')
        if marker:
            u=lookup[marker['id']]; d=lookup[row['designation']['id']]
            require(normalized(marker['quote'])=='a)' and abs(u['bbox'][1]-d['bbox'][1])<3 and u['bbox'][0]>=d['bbox'][2]-1, 'Wrong embedded-derivative marker')
            require(u['order']==t['marker_line'],'Marker transcript mismatch'); markers.append(u['order'])
    require(sorted(markers)==list(range(92,113)), 'All21designation markers required exactly once')
    same({k:normalized(v['quote']) for k,v in source['issues']['footnotes'].items()},
         {k:normalized(v) for k,v in transcript['footnotes'].items()}, 'Footnotes differ from independent image reading')
    baseline=read(prior.HERE/'reading.json')
    same({k:v for k,v in reading.items() if k!='debt_securities'},baseline,'022reading changed')
    prior.source_check(baseline,read(prior.HERE/'source-units.json'),read(prior.HERE/'image-transcript.json'))
    balance=next(r for r in baseline['tables']['liabilities']['rows'] if r['label'] and 'Debt securities issued' in r['label']['quote'])
    same([c['value'] for c in balance['cells']],transcript['summary_totals'],'Note32statement mismatch')
    totals=transcript['summary_totals']
    require([sum(r['cells'][i]['value'] for r in source['summary']['rows']) for i in range(2)]==totals,'Source summary arithmetic mismatch')
    movement=[c['value'] for c in source['movements']['totals']]
    require(sum(movement[:-1])==movement[-1]==totals[0] and movement[0]==totals[1], 'Aggregate movement mismatch')
    return {'new_occurrences':445,'prior_occurrences':884,'total_occurrences':1329,'issue_rows':42,
        'covered_rows':3,'movement_positions':36,'unknown_dashes':sum(c['value'] is None for r in source['movements']['rows'] for c in r['cells']),
        'footnotes':21,'designation_markers':21,'prior_fields_preserved':True,
        'arithmetic_role':'EXPLANATORY_ONLY; category dashes remain unknown; book values not equated to issue flows'}


def source_worker():
    units=original_units(); transcript=read(HERE/'image-transcript.json'); review=HERE/'SOURCE-REVIEW.md'
    require(review.is_file() and len(review.read_text())>1000, 'Substantive source review required')
    for item in read(HERE/'images.json'): require(sha(ROOT/item['path'])==item['sha256'], 'Source image changed')
    reading=deepcopy(read(prior.HERE/'reading.json')); reading['debt_securities']=securities_reading(units,transcript)
    checked=source_check(reading,units,transcript)
    all_units=sorted(read(BASE/'attempt-015/source-units.json')+read(prior.HERE/'source-units.json')+units,
                     key=lambda u:(u['page'],u['order'],u['id']))
    save(HERE/'source-units.json',units); save(HERE/'reading.json',reading)
    entry={'document':DOCUMENT,'source':PDF,'reading':compact_digest(reading),'pages_digest':compact_digest(all_units),
        'pages':sorted({u['page'] for u in all_units}),'occurrences':len(all_units),
        'reading_fields':['source_groups','tables','terms','scope','debt_context','debt_securities']}
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
    save(HERE/'source-check.json',{'status':'PASS',**checked,'baseline_gap':'Note32profile unsupported','source_review':prior.prior.ref(review)})


def candidate_frozen():
    f=read(HERE/'candidate-freeze.json')
    require(all(sha(HERE/n)==h for n,h in f['bindings'].items()),'Candidate interpretation changed')
    return f


def implement_worker():
    f=candidate_frozen(); require(sha(ROOT/PRODUCTION)==read(PREP/'freeze.json')['baseline_sha256'],'Baseline changed')
    shutil.copyfile(HERE/'candidate-statement_cells.py',ROOT/PRODUCTION)
    require(sha(ROOT/PRODUCTION)==f['candidate_sha256'],'Registry write failed')
    save(HERE/'candidate-production.json',prior.prior.production())


def supplied(graph):
    return {'version':'source-statement-cells.v1','profile':PROFILE,'document':DOCUMENT,'graph_sha256':digest(graph),
        'review':{'kind':'DEVELOPMENT','reviewer':'Original page images, exact quotes and independent table transcript',
            'reason':'Complete022plus original Note32; financial,legal and incorporation limits retained'},
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
    graph={'units':read(BASE/'attempt-015/source-units.json')+read(prior.HERE/'source-units.json')+read(HERE/'source-units.json')}
    changes={
        'all-debt-guaranteed':lambda d:d['state_guarantee'].update(all_debt_guaranteed=True),
        'guarantee-unit':lambda d:d['state_guarantee'].update(unit='EUR thousands'),
        'guarantee-holder':lambda d:d['state_guarantee'].update(particular_instrument_covered='CONFIRMED'),
        'law-verified':lambda d:d['covered_bonds']['reported_legal_context'].update(authorities_verified=True),
        'cover-pool-lost':lambda d:d['covered_bonds']['reported_legal_context'].update(cover_pool='All assets'),
        'current-rating':lambda d:d['covered_bonds'].update(current_rating_established=True),
        'nominal-as-book':lambda d:d['covered_bonds']['rows'][0].update(book_value=d['covered_bonds']['rows'][0]['nominal_value']),
        'dash-zero':lambda d:d['movements']['rows'][1]['cells'][1].update(value=0,status='SOURCE_NUMBER'),
        'net-as-gross':lambda d:d['movements']['certificates_of_deposit'].update(gross_cash_repayment_inferred=True),
        'other-movements-lost':lambda d:d['movements'].update(other_movements=['Cash only']),
        'derecognition-right':lambda d:d['repurchase'].update(holder_rights_inferred=True),
        'issuer-changed':lambda d:d['issues']['rows'][2]['issuer'].update(quote='BES - Sede'),
        'currency-changed':lambda d:d['issues']['rows'][2]['issue_currency'].update(quote='EUR'),
        'currency-as-unit':lambda d:d['issues']['rows'][2]['book_value'].update(unit='USD thousands'),
        'coupon-as-yield':lambda d:d['issues']['rows'][4].update(stated_rate_or_index=d['issues']['footnotes']['o']),
        'missing-marker':lambda d:d['issues']['rows'][13].update(designation_marker=None),
        'missing-issue':lambda d:d['issues']['rows'].pop(),
        'missing-footnote':lambda d:d['issues']['footnotes'].pop('u'),
        'wrong-basket':lambda d:d['issues']['rows'][14].update(rate_footnote=d['issues']['footnotes']['c']),
        'book-as-issues':lambda d:d['issues'].update(gross_issues_equal_book_value_sum_assumed=True),
        'invented-payoff':lambda d:d['issues'].update(payoff_formulae_invented=True),
        'incorporation-assumed':lambda d:d['source_context'].update(incorporation_status='CONFIRMED')}
    rows=[]
    for name,change in changes.items():
        bad=supplied(graph); change(bad['reading']['debt_securities'])
        try: cells.admit(graph,bad)
        except ValueError as exc: rows.append({'case':name,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else: raise ValueError('Altered interpretation accepted: '+name)
    for name in ('missing-page','source-hash','geometry'):
        g=deepcopy(graph)
        if name=='missing-page': g['units']=[u for u in g['units'] if u['page']!=140]
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
    require(digest(before)==previous['answer_sha256'],'Complete022baseline answer changed')
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
    for key in baseline_reading: same(before['source_statement_cells'][key],after['source_statement_cells'][key],'Lost022field '+key)
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
    composed['h1_debt_context_consumer']=before
    require(digest(composed)==previous['full_composed_sha256'],'Complete022composition changed')
    composed['h1_debt_securities_consumer']=after
    receipt={'status':'PASS','prior_complete_answer_sha256':digest(before),'answer_sha256':digest(after),
        'prior_full_composed_sha256':previous['full_composed_sha256'],'full_composed_sha256':digest(composed),
        'reading_sha256':compact_digest(reading),'replacements':replacements,'addition':body,'controls':cases,
        'source_check':checked,'imports':imported,'whole_task_complete':False,'source_truth_established':False,
        'recipe':'Reconstruct022from007and frozen profile; derive021via its retained replacements/addition and verify; retain016/017/021/022 and add023as h1_debt_securities_consumer'}
    del composed,before,after,old_answer
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
        elif change=='changed_p2': p2['source_statement_cells']['reading']['debt_securities']['state_guarantee']['all_debt_guaranteed']=True
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
    save(HERE/'package.json',{'python':python,'wheel':prior.prior.ref(wheels[0]),'files':expected})


def coverage_worker():
    previous=read(prior.HERE/'requirements.json'); rows=deepcopy(previous['rows'])
    for row in rows:
        if row.get('status','').startswith('THIS_ATTEMPT_MUST_PASS'):
            row.update(status='RETAINED_COMPLETE_FINITE_INTEGRATION',evidence=prior.prior.ref(prior.HERE/'result.json'))
    rows.append({'requirement':'Complete Note32summary/covered bonds/movements/42issues/21footnotes',
                 'status':'THIS_ATTEMPT_MUST_PASS; see stage outcomes'})
    save(HERE/'requirements.json',{'rows':rows,'original_task_acceptance':False,'external_adviser_opinion_required':False,
        'next_discriminating_work':'Resolve original Note10buyback period ambiguity and Note21collateral reference; map remaining61–171policy/note coverage and controlling edition/incorporation. Do not replay completed installs.'})


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
    (HERE/'RESULT.md').write_text('# Original Note32integration\n\n'+('Finite source/consumer integration passed. ' if passed else 'Campaign did not pass. ')
        +'Actual stages: '+json.dumps(outcomes)+'.\n\n'
        +'The complete original Note32reading preserves five summary categories,three covered-bond rows,five movement categories,42issue rows and21footnotes. '
        +'Guarantee subsets and their units,book versus nominal amounts,net certificate-of-deposit presentation,unknown dashes,reported collateral law, '
        +'historical ratings,index baskets and fixed coupons versus effective emission rates remain distinct. '
        +'All022fields and016/017/021/022compositions are retained through checked lossless recipes.\n\n'
        +'|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|\n|---|---|---|---|---|---|\n'
        +'|'+('Retain finite integration' if passed else 'Retain actual failure')+'|Original images/quotes/geometry and actual full normal/installed answers|See stage records|Remaining notes and authority|Record/refresh; resolve Note10/21and remaining coverage|Financial truth,current law,holder entitlement,automatic extraction,whole build|\n\n'
        +'Post-run review: exact profiles preserve supplied readings; a shared wrong interpretation remains the strongest alternative explanation. '
        +'The independent image transcript and full quote/geometry review address source association and omissions. '
        +'They do not prove external financial or legal truth. Remaining coverage is an implementation/evidence gap,not evidence that a package is fundamentally unsuitable.\n')
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(p) for p in sorted((HERE/'commands').glob('*.json'))],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU_ONLY;CUDA_VISIBLE_DEVICES=-1;GPU intentionally hidden',
        'random_seeds':'N/A deterministic','plan':PLAN,'result':rel(HERE/'RESULT.md'),
        'data_version':prior.prior.ref(PREP/'freeze.json'),'resources':costs()})
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
