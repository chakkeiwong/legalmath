"""One reviewed H1 statement integration; immutable evidence and bounded stages."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
BASE = AUTH / 'attempts/source-bes-dep-05'
PREP = AUTH / 'reviews/h1-statement-consumer-384'
HERE = BASE / 'attempt-021'
PLAN = 'docs/plans/prospectus-h1-statement-consumer-2026-10-21.md'
SELF = 'scripts/prospectus_h1_statement_consumer.py'
PRODUCTION = 'src/legalmath/prospectus/successor/statement_cells.py'
TRANSCRIPT = AUTH / 'drafts/h1-statements-384-image-values.txt'
SOURCE_REVIEW = AUTH / 'drafts/h1-statements-384-source-review.md'
PROFILE = 'bes-h1-2010-statements-review.v1'
DOCUMENT = 'bes-interim-h1-2010'
PDF = 'b86022629850867b5bedbdaf701a451a816f46766d102fc487fc51da658b0ea7'
PAGES = (56, 57, 58, 172, 173)
TESTS = ['tests/prospectus_successor/test_statement_cells.py',
         'tests/prospectus_successor/test_shell_source_chain_consumer.py']
CONTEXT = {'origin': 'SUPPLIED_DEVELOPMENT_READING', 'source_authenticity': 'NOT_ESTABLISHED',
    'incorporation_status': 'UNRESOLVED', 'assurance': 'MODERATE_LIMITED_REVIEW',
    'full_audit_established': False, 'independent_financial_review': False,
    'all_referenced_notes_read': False, 'dash_imputed_zero': False,
    'BES_Finance_standalone_accounts_supplied': False, 'arithmetic_role': 'EXPLANATORY_ONLY'}
DEPENDENCIES = {'source': [], 'implement': ['source'], 'tests': ['implement'],
    'ordinary': ['tests'], 'controls': ['ordinary'], 'package': ['controls'],
    'installed': ['package'], 'coverage': []}


def read(path):
    p = Path(path)
    return json.loads(gzip.decompress(p.read_bytes()) if p.suffix == '.gz' else p.read_bytes())


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else encoded(value)).hexdigest()


def compact_digest(value):
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode())


def sha(path):
    return digest(Path(path).read_bytes())


def rel(path):
    return str(Path(path).relative_to(ROOT))


def ref(path):
    return {'path': rel(path), 'sha256': sha(path)}


def save(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
    if path.suffix == '.gz':
        raw = gzip.compress(raw, mtime=0)
    if len(raw) > 2 * 1024**2:
        raise ValueError('Two-MiB output reservation exceeded: ' + path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def same(a, b, label):
    require(encoded(a) == encoded(b), label)


def production():
    return {rel(p): sha(p) for p in (ROOT / 'src/legalmath').rglob('*') if p.is_file()
            and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')}


def authority():
    sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
    from legalmath.prospectus.execution_authority import Authority
    return Authority(ROOT)


def source_reading():
    reading = deepcopy(read(BASE / 'attempt-015/profile.json')['reading'])
    reading['source_context'] = deepcopy(CONTEXT)
    return reading


def read_transcript():
    result = {}
    current = None
    for line in TRANSCRIPT.read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        if line.startswith('['):
            current = line.strip('[]')
            result[current] = []
        else:
            result[current].append([None if x == '-' else Decimal(x) for x in line.split(',')])
    return result


def source_check(reading, units):
    """Use original quotes, geometry and separately typed image values."""
    lookup = {u['id']: u for u in units}
    require(len(units) == len(lookup) == 533, 'Complete533 source occurrences required')
    require(all(u['visible'] and u['source_sha256'] == PDF and u['page'] in PAGES for u in units),
            'Wrong source edition or hidden occurrence')
    quoted = [q for group in reading['source_groups'].values() for q in group]
    require(Counter(q['id'] for q in quoted) == Counter(lookup.keys()), 'Complete contextual partition required')
    require(all(q['quote'] == lookup[q['id']]['raw'] for q in quoted), 'Changed source quote')
    expected = read_transcript()
    widths = {56: [(350,410),(410,460),(460,510),(510,560)],
              57: [(310,370),(370,425),(425,480),(480,540)], 58: [(390,452),(452,510)]}
    periods = ['2010Q2','2009Q2','2010H1','2009H1']
    used = []
    unknown = 0
    for name, table in reading['tables'].items():
        require(name in expected and len(table['rows']) == len(expected[name]), 'Wrong statement row inventory')
        same(table['columns'], periods if name in ('income','comprehensive') else ['2010-06-30','2009-12-31'], 'Wrong period order')
        ys = []
        for index, (row, values) in enumerate(zip(table['rows'], expected[name])):
            require(len(row['cells']) == len(values), 'Missing statement cell')
            for item in ([row['label']] if row['label'] else []) + row['notes']:
                require(item['quote'] == lookup[item['id']]['raw'], 'Wrong row-label/note association')
            row_y = []
            for col, (cell, image_value) in enumerate(zip(row['cells'], values)):
                unit = lookup[cell['source_unit']]
                require(cell['quote'] == unit['raw'], 'Wrong amount quote')
                token = ''.join(unit['raw'].split())
                actual = None if token == '-' else Decimal('-' + token[1:-1] if token.startswith('(') else token)
                require(actual == image_value, 'Native numeral differs from image transcript: ' + cell['source_unit'])
                require((cell['value'] is None if actual is None else Decimal(str(cell['value'])) == actual), 'Wrong typed amount')
                require(cell['status'] == ('DASH_UNKNOWN' if actual is None else 'SOURCE_NUMBER'), 'Unknown dash coerced')
                require(cell['unit'] == ('EUR per share' if name == 'income' and index >= 30 else 'EUR thousands'), 'Wrong monetary unit')
                lo, hi = widths[unit['page']][col]
                require(lo <= (unit['bbox'][0] + unit['bbox'][2]) / 2 < hi, 'Amount in wrong column')
                row_y.append(unit['bbox'][1])
                used.append(unit['id'])
                unknown += actual is None
            require(max(row_y) - min(row_y) < 2, 'Amount row misalignment')
            ys.append(sum(row_y) / len(row_y))
        require(ys == sorted(ys) and len(set(ys)) == len(ys), 'Statement rows reordered')
    require(set(reading['tables']) == set(expected) and len(used) == len(set(used)) == 266 and unknown == 3,
            'Complete266 distinct cells and three dashes required')
    # Context is separately image-reviewed and kept whole, not inferred from sums.
    terms = reading['terms']
    require(terms['measurement']['EPS_unit'] == 'EUR per share' and not terms['scope']['all_referenced_notes_read'], 'EPS/notes qualification lost')
    require(terms['review_method']['objective'] == 'moderate level of assurance' and not terms['review_method']['full_audit_asserted'], 'Assurance overstated')
    require(terms['review_conclusion']['materiality_qualified'] and not terms['authority']['financial_accuracy_proved'], 'Source limits lost')
    require(not terms['attribution']['Group_profit_equals_parent_profit'] and not terms['attribution']['page59_clipped_values_restored'], 'Entity/clipping limits lost')
    same(reading['source_context'], CONTEXT, 'Unsupported source context')
    return {'cells': 266, 'rows': 87, 'occurrences': 533, 'unknown_dashes': 3,
            'tables': 5, 'image_transcript': ref(TRANSCRIPT), 'method': 'Source quotes, numeric geometry and separate image transcription'}


def costs(reserve=0):
    start = read(PREP / 'accounting-start.json')
    paths = {p for d in (PREP, HERE) for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / n for n in (PLAN, SELF, PRODUCTION))
    paths.update((TRANSCRIPT, SOURCE_REVIEW, AUTH / 'revisions/0384.json'))
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    seconds = sum(read(p)['wall_seconds'] for d in (PREP, HERE) for p in d.glob('commands/*.json'))
    return {'new_bytes': size, 'new_measured_seconds': seconds, 'new_control_seconds': 60,
        'prior_known_bytes': start['prior_known_bytes'], 'prior_known_seconds': start['prior_known_seconds'],
        'known_cumulative_bytes': start['prior_known_bytes'] + size,
        'known_cumulative_seconds': start['prior_known_seconds'] + seconds + 60,
        'earlier_manual_and_unmeasured_costs': 'UNKNOWN; retained, never reset',
        'execution_allowed': size + reserve < 78 * 1024**2 and seconds < 480}


def prepare():
    tick = time.monotonic()
    auth = authority()
    old = read(AUTH / 'program.json')
    require(old['revision'] == 383 and not PREP.exists() and not HERE.exists(), 'Fresh383 preparation required')
    events = auth.events()
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e['budget_key'] == 'source-bes-dep-05']
    require(len(attempts) == old['budgets']['source-bes-dep-05']['maximum_new_attempts'] == 20, 'Retain all20admissions')
    protected = {}
    for number in (7, 15, 16, 17, 20):
        folder = BASE / f'attempt-{number:03d}'
        records = [e for e in events if e.get('attempt') == rel(folder) and 'outputs_sha256' in e]
        require(records and sha(folder / 'outputs.json') == records[-1]['outputs_sha256'], 'Unauthenticated original manifest')
        protected[rel(folder / 'outputs.json')] = sha(folder / 'outputs.json')
        for name, checksum in read(folder / 'outputs.json').items():
            require(sha(folder / name) == checksum, 'Original evidence changed: ' + name)
    paths = {p for p in BASE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    for number in range(1,21):
        folder = BASE / f'attempt-{number:03d}'
        if (folder / 'workspace.json').exists():
            directory = Path(read(folder / 'workspace.json')['directory'])
            paths.update(p for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    timers = {}
    for number in range(5,17):
        p = BASE / f'attempt-{number:03d}/result.json'
        timers[rel(p)] = read(p)['cumulative_seconds']
    m = BASE / 'attempt-017/run-manifest.json'
    timers[rel(m)] = read(m)['preparation_seconds'] + read(m)['wall_seconds']
    p = AUTH / 'continuation-reviews/h1-unit-212-record/receipt.json'
    timers[rel(p)] = read(p)['wall_seconds']
    for number in (18,19,20):
        p = BASE / f'attempt-{number:03d}/result.json'
        timers[rel(p)] = read(p)['wall_seconds']
    save(PREP / 'accounting-start.json', {'prior_known_bytes': sum(p.stat().st_size for p in paths),
        'prior_known_seconds': sum(timers.values()), 'timers': timers,
        'unknown_costs': 'Early001-004/manual costs and unmeasured installed validation/control cost UNKNOWN',
        'retained_storage_scope': 'All source05 attempts and referenced historical workspace directories; shared builds charged elsewhere',
        'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
        'program_bytes': (AUTH / 'program.json').stat().st_size})
    (PREP / 'baseline').mkdir()
    shutil.copyfile(ROOT / PRODUCTION, PREP / 'baseline/statement_cells.py')
    save(PREP / 'baseline/production.json', production())
    units = read(BASE / 'attempt-015/source-units.json')
    reading = source_reading()
    save(PREP / 'reading.json', reading)
    selected = sorted(units, key=lambda u: (u['page'],u['order'],u['id']))
    entry = {'document': DOCUMENT, 'source': PDF, 'reading': compact_digest(reading),
        'pages_digest': compact_digest(selected), 'pages': list(PAGES), 'occurrences': 533,
        'reading_fields': ['source_groups','tables','terms','scope']}
    save(PREP / 'registry-entry.json', entry)
    old_source = (ROOT / PRODUCTION).read_text()
    require(PROFILE not in old_source and old_source.count('PROFILES = {') == 1, 'Registry baseline differs')
    addition = '    ' + repr(PROFILE) + ': ' + repr(entry) + ',\n'
    candidate = old_source.replace('PROFILES = {\n', 'PROFILES = {\n' + addition, 1)
    (PREP / 'candidate-statement_cells.py').write_text(candidate)
    products = read(BASE / 'attempt-007/products.json.gz')
    names = [PLAN, SELF, rel(TRANSCRIPT), rel(SOURCE_REVIEW), 'pyproject.toml', *TESTS]
    names += [rel(BASE / f'attempt-{n:03d}' / file) for n, files in {
        7:['products.json.gz','scope-consumer.json.gz'],
        15:['profile.json','source-units.json','analysis.json','reading.py','RESULT.md'],
        16:['answer-supplement.json.gz'],17:['answer-delta.json.gz','composition.json']}.items() for file in files]
    names += [d['path'] for d in products['P1']['payload']['request']['bundle']['documents']]
    names += [i['path'] for i in read(BASE / 'attempt-015/profile.json')['images']]
    names += [rel(p) for p in PREP.glob('*.json') if p.name != 'accounting-start.json']
    names += [rel(PREP / 'baseline/statement_cells.py'), rel(PREP / 'baseline/production.json'), rel(PREP / 'candidate-statement_cells.py')]
    protected.update({n: sha(ROOT / n) for n in names})
    protected.update({n:h for n,h in production().items() if n != PRODUCTION})
    save(PREP / 'freeze.json', {'bindings': protected, 'mutable_file': PRODUCTION,
        'baseline_sha256': sha(ROOT / PRODUCTION), 'candidate_sha256': digest(candidate.encode()),
        'implementation_window': 'Only after successful source stage, once; frozen before tests/consumers'})
    package_python = read(AUTH / 'attempts/source-authority/attempt-011/package.json')['python']
    require(Path(package_python).is_file(), 'Retained offline build interpreter missing')
    save(PREP / 'config.json', {'package_python': package_python, 'python_sha256': sha(package_python)})
    new = deepcopy(old)
    new['revision'] = 384
    task = next(t for t in new['tasks'] if t['id'] == 'source-bes-dep-05')
    task.update(dossier=PLAN, pre_admission_review=PLAN, build_criteria_scope=[],
        reason='Connect complete retained H1 primary statements to existing P1-P5 statement consumer; preserve source limits and original requirements')
    task['inputs'] = sorted((set(task['inputs']) - {PRODUCTION}) | set(protected) | {rel(PREP / 'freeze.json'), rel(PREP / 'config.json')})
    bounds = {'measured_seconds':480,'control_seconds':60,'new_bytes':80*1024**2,'failure_reserve':2*1024**2,
        'previous_known_bytes':read(PREP/'accounting-start.json')['prior_known_bytes'],
        'previous_known_seconds':read(PREP/'accounting-start.json')['prior_known_seconds'], 'unchanged_retries':0}
    task['statement_integration'] = {'version':PROFILE,'freeze':rel(PREP/'freeze.json'),
        'bounds':bounds,'success_dependencies':DEPENDENCIES,'original_task_acceptance':False}
    new['budgets']['source-bes-dep-05']['maximum_new_attempts'] = 21
    routes = read(ROOT / old['continuation_review']['routes'])
    routes['baseline_revision'] = 384
    for row in routes['tasks']:
        if row['task'] == 'source-authority':
            row.update(phase=6, remaining='012 independently verified retained repaired consumer;011 storage FAIL retained. Whole source authority remains unproved.',
                next_action='Preserve completed012; no repeated verification/consumer/build. Continue independent original tasks; future source-authority work requires reviewed resources.',
                stop_condition='Known006+1880.4325241597364s of1900s;442996833bytes of448MiB; no new campaign within ordinary control allowance.')
        if row['task'] == task['id']:
            row.update(task_sha256=compact_digest(task),
                dossier=PLAN,phase=0, remaining='Original015533-occurrence/266-cell primary reading remains detached from normal statement consumer; unit/limited-review paths already exist.',
                next_action='Execute021 source, single registry edit, normal/installed complete consumer checks and original coverage reconciliation; record/refresh and continue.',
                stop_condition='21 total admissions;480+60s and80MiB new including authority/package files; prior known costs and unknown costs retained; no unchanged retry.')
    save(PREP / 'routes.json', routes)
    new['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    new['continuation_review']['bindings'].pop(PRODUCTION, None)
    new['continuation_review']['bindings'][rel(PREP/'baseline/statement_cells.py')] = sha(PREP/'baseline/statement_cells.py')
    new['continuation_review']['bindings'].update({n:sha(ROOT/n) for n in (PLAN,rel(PREP/'routes.json'),rel(PREP/'freeze.json'))})
    require(old['obligations']==new['obligations'] and old['build_contract']==new['build_contract'], 'Original scope changed')
    raw = (json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
    src_bytes = sum(p.stat().st_size for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    forecast = costs()['new_bytes'] + 2*len(raw) + 3*src_bytes + 8*1024**2
    require(forecast < 78*1024**2, 'Exact authority/source/install/log forecast exceeds reservation')
    with (PREP/'proposal.json').open('xb') as stream: stream.write(raw)
    from legalmath.prospectus.execution_authority import digest as authority_digest
    save(PREP/'review.json', {'baseline':authority_digest(old),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Connect originalH1 statement reading through existing normal consumer','Retain original source/consumer evidence and all20admissions',
                   'Replace mutable registry input by protected baseline and exact candidate during explicit implementation window','Refresh completed source012 route'],
        'skeptical_audit':{'verdict':'PASS','plan':PLAN,'forecast_new_bytes':forecast,
            'baseline':'Original007products/answer and015reading; no source reinterpretation or automatic claim'},
        'evidence_contract':{'question':'Does the actual consumer deliver the complete source-qualified H1 statement reading?',
            'primary':'Original source/geometry/image values; complete normal/installed answers and actual corruption refusals',
            'promotion_veto':['Changed source/answer','Wrong imports','Accepted corruption'],
            'continuation_veto':['Invalid authority','Corrupt originals','Spent resource reservation'],
            'not_concluded':['Financial truth','Automatic extraction','Whole source05/build']},
        'budget_revision':{'budget_key':'source-bes-dep-05','previous_maximum':20,'new_maximum':21,
            'retained_attempts':attempts,'reason':'First normal primary-statement delivery, not another unit component replay',
            'next_discriminating_check':'Complete source and actual normal/installed matched answers with rehashed controls',
            'stop_condition':bounds,'same_scope_authorization':'User recover and continue original build'}})
    save(PREP/'commands/preparation.json',{'wall_seconds':time.monotonic()-tick,'command':[sys.executable,'-m',SELF,'prepare']})
    return {'status':'PREPARED','revision':384,'forecast_new_bytes':forecast,'resources':costs()}


def frozen(candidate=False):
    auth = authority()
    admission = read(HERE/'admission.json')
    from legalmath.prospectus.execution_authority import digest as adigest
    require(adigest(read(AUTH/'program.json')) == admission['program_sha256'] and
            auth.binding(admission['task_spec']) == admission['binding'], 'Current unchanged admission required')
    f = read(PREP/'freeze.json')
    require(all(sha(ROOT/n)==h for n,h in f['bindings'].items()), 'Frozen input or non-target production changed')
    require(sha(ROOT/PRODUCTION)==f['candidate_sha256' if candidate else 'baseline_sha256'], 'Registry outside reviewed implementation window')


def source_worker():
    reading = read(PREP/'reading.json')
    units = read(BASE/'attempt-015/source-units.json')
    checked = source_check(reading,units)
    for image in read(BASE/'attempt-015/profile.json')['images']:
        require(sha(ROOT/image['path'])==image['sha256'],'Original image changed')
    from legalmath.prospectus.successor import statement_cells as cells
    supplied = {'version':'source-statement-cells.v1','profile':PROFILE,'document':DOCUMENT,
        'graph_sha256':digest({'units':units}),'review':{'kind':'DEVELOPMENT','reviewer':'Original source review','reason':'H1 complete reading'},
        'reading':reading}
    try: cells.admit({'units':units},supplied)
    except ValueError as exc: require('Unsupported source statement' in str(exc),'Unexpected baseline refusal')
    else: raise ValueError('Claimed missing H1 profile already works')
    save(HERE/'source-check.json',{'status':'PASS',**checked,'baseline_gap':'Unsupported H1 statement profile',
        'source_review':ref(SOURCE_REVIEW),'original_qualifications':ref(BASE/'attempt-015/profile.json')})


def implement_worker():
    require(sha(ROOT/PRODUCTION)==read(PREP/'freeze.json')['baseline_sha256'],'Baseline changed before edit')
    shutil.copyfile(PREP/'candidate-statement_cells.py', ROOT/PRODUCTION)
    require(sha(ROOT/PRODUCTION)==read(PREP/'freeze.json')['candidate_sha256'],'Candidate edit failed')
    save(HERE/'candidate-production.json',production())


def supplied(graph):
    return {'version':'source-statement-cells.v1','profile':PROFILE,'document':DOCUMENT,
        'graph_sha256':digest(graph),'review':{'kind':'DEVELOPMENT','reviewer':'Retained015 and2026-10-21 full source review',
        'reason':'Complete H1 statements and limited-review reading; unknown authority and broader notes remain'},
        'reading':read(PREP/'reading.json')}


def build_products(original, include=True):
    from legalmath.prospectus.successor import service
    p1 = deepcopy(original['P1'])
    request = p1['payload']['request']
    if include: request['source_statement_cells']=supplied(p1['payload']['graph'])
    p1=service.seal('P1',request['bundle'],{'request':digest(request)},p1['payload'])
    p2=service.construction_product(p1,ROOT)
    p3=service.interpretation_product(p1,p2,original['P3']['payload'].get('interpretation_input'))
    l,f=original['P4']['payload'],original['P5']['payload']
    return {'P1':p1,'P2':p2,'P3':p3,'P4':service.law_product(p1,p3,l.get('cases'),l.get('law_input')),
        'P5':service.financial_product(p1,p2,p3,f.get('cases'),f.get('scenario_input'))}


def registry_controls():
    from legalmath.prospectus.successor import statement_cells as cells
    import importlib.util
    p=BASE/'attempt-015/reading.py'
    spec=importlib.util.spec_from_file_location('original_h1_adverse',p)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    old=read(BASE/'attempt-015/profile.json')
    graph={'units':read(BASE/'attempt-015/source-units.json')}
    cases=[]
    for name in module.CASES:
        if name=='IFRS-validated': continue  # This belongs to the old outer profile, not registered reading.
        altered=module.altered(old,name)
        bad=supplied(graph)
        if name=='missing-source-page':
            ids={q['id'] for q in altered['source_units']}
            g={'units':[u for u in graph['units'] if u['id'] in ids]}
            bad['graph_sha256']=digest(g)
        else:
            g=graph;bad['reading']={**altered['reading'],'source_context':deepcopy(CONTEXT)}
        try: cells.admit(g,bad)
        except ValueError as exc: cases.append({'case':name,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else: raise ValueError('Changed original statement accepted: '+name)
    bad=supplied(graph);bad['reading']['source_context']['full_audit_established']=True
    try: cells.admit(graph,bad)
    except ValueError as exc: cases.append({'case':'context-full-audit','refused':True,'reason':str(exc),'input_sha256':digest(bad)})
    else: raise ValueError('Full audit overclaim accepted')
    return cases


def consumer_worker(kind):
    from legalmath.prospectus.successor import service
    old=read(BASE/'attempt-007/products.json.gz')
    baseline=build_products(old,False)
    same(old,baseline,'Complete legacy P1-P5 changed')
    prior=read(BASE/'attempt-007/scope-consumer.json.gz')['answer']
    before=service.consume(baseline,ROOT,include_artifacts=True)
    same(prior,before,'Complete legacy normal answer changed')
    current=build_products(old,True)
    after=service.consume(current,ROOT,include_artifacts=True)
    for phase in ('P2','P3','P4','P5'):
        payload=deepcopy(current[phase]['payload'])
        if phase=='P2': payload.pop('source_statement_cells')
        if phase=='P3': payload.pop('source_statement_cells_sha256')
        same(payload,old[phase]['payload'],'Undeclared phase payload changed: '+phase)
    same(current['P1']['payload']['graph'],old['P1']['payload']['graph'],'Source graph changed')
    replacements={k:after[k] for k in ('request_sha256','consumed_products','report_sha256')}
    expected={**before,**replacements,'source_statement_cells':after['source_statement_cells']}
    same(expected,after,'Undeclared complete answer changed')
    same(before['questions'],after['questions'],'Financial/legal answers changed')
    require(after['questions']['Q3']['status']=='PARTIAL' and not after['may_execute_transaction'] and not after['independent_legal_acceptance'],'Original limits changed')
    body=after['source_statement_cells']; reading=read(PREP/'reading.json')
    for key in ('source_groups','tables','terms','scope','source_context'): same(body[key],reading[key],'Lost original statement field: '+key)
    require(body['consumed'] and not body['independent_financial_acceptance'] and body['legal_dependency_resolution']=='UNCHANGED','Invalid integration claim')
    source_check({k:body[k] for k in ('source_groups','tables','terms','scope','source_context')},read(BASE/'attempt-015/source-units.json'))
    cases=registry_controls()
    imported={n:m.__file__ for n,m in sys.modules.items() if n.startswith('legalmath') and getattr(m,'__file__',None)}
    location=HERE/'installed' if kind=='installed' else ROOT/'src'
    require(all(Path(p).resolve().is_relative_to(location) for p in imported.values()),'Wrong production import origin')
    # Reconstruct, then hash the complete retained supplement composition in memory.
    del old,baseline,current,prior,before,expected
    later=read(BASE/'attempt-016/answer-supplement.json.gz')
    previous=read(BASE/'attempt-017/composition.json')
    same(digest(later),previous['previous_content_sha256'],'Full016supplement changed')
    later.update(read(BASE/'attempt-017/answer-delta.json.gz'))
    same(digest(later),previous['complete_composed_sha256'],'Complete017composition changed')
    require('h1_normal_statement_consumer' not in later,'Composition key collision')
    later['h1_normal_statement_consumer']=after
    receipt={'status':'PASS','answer_sha256':digest(after),'full_composed_sha256':digest(later),
        'legacy_normal_sha256':digest(read(BASE/'attempt-007/scope-consumer.json.gz')['answer']),
        'source_reading_sha256':compact_digest(reading),'all_prior_fields_preserved':True,
        'replacements':replacements,'addition':body,'controls':cases,'imports':imported,
        'whole_task_complete':False,'source_truth_established':False}
    if kind=='installed':
        ordinary=read(HERE/'ordinary.json.gz')
        for key in ('answer_sha256','full_composed_sha256','legacy_normal_sha256','source_reading_sha256','replacements','addition','controls'):
            same(receipt[key],ordinary[key],'Installed result differs: '+key)
        del later, after
        controls_worker('installed-controls.json')
        same(read(HERE/'installed-controls.json'),read(HERE/'controls.json'),'Installed product corruptions differ')
    save(HERE/(kind+'.json.gz'),receipt)


def controls_worker(output='controls.json'):
    from legalmath.prospectus.successor import service
    original=read(BASE/'attempt-007/products.json.gz')
    current=build_products(original,True)
    rows=[]
    for change in ('missing_p2','changed_p2','missing_p3','changed_p3','unsupplied'):
        bad=deepcopy(current);request=bad['P1']['payload']['request'];p2,p3=bad['P2']['payload'],bad['P3']['payload']
        if change=='missing_p2': del p2['source_statement_cells']
        elif change=='changed_p2': p2['source_statement_cells']['reading']['tables']['income']['rows'][0]['cells'][0]['value']+=1
        elif change=='missing_p3': del p3['source_statement_cells_sha256']
        elif change=='changed_p3': p3['source_statement_cells_sha256']='0'*64
        else: del request['source_statement_cells']
        b=request['bundle']
        bad['P1']=service.seal('P1',b,{'request':digest(request)},bad['P1']['payload'])
        for phase,parents in [('P2',['P1']),('P3',['P1','P2']),('P4',['P1','P3']),('P5',['P2','P3'])]:
            bad[phase]=service.seal(phase,b,{p:bad[p]['sha256'] for p in parents},bad[phase]['payload'])
        try: service.consume(bad,ROOT,include_artifacts=True)
        except ValueError as exc:
            require('Consumed statement cells' in str(exc),'Unintended consumer refusal')
            rows.append({'case':change,'refused':True,'reason':str(exc),'input_sha256':digest(bad),
                'reconstruction':'Rebuild021 candidate then apply named controls_worker mutation; reseal all five phases'})
        else: raise ValueError('Rehashed forged product accepted: '+change)
    save(HERE/output,{'status':'PASS','actual_consumer_refusals':rows})


def command(name,argv,timeout=120):
    require(costs(1024**2)['execution_allowed'],'Pre-command resource reservation exhausted')
    target=HERE/'commands';target.mkdir(exist_ok=True)
    tick=time.monotonic();result=None;error=None
    try:
        with (target/(name+'.log')).open('x') as stream:
            result=subprocess.run(argv,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout,
                env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1','PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1',
                     'PYTHONPATH':str(ROOT/'src')+os.pathsep+str(ROOT),'PIP_NO_INDEX':'1','PIP_DISABLE_PIP_VERSION_CHECK':'1'})
        require(result.returncode==0,'Inspect retained '+name+'.log')
    except Exception as exc: error={'type':type(exc).__name__,'reason':str(exc)}
    save(target/(name+'.json'),{'command':argv,'wall_seconds':time.monotonic()-tick,
        'exit_code':None if result is None else result.returncode,'error':error})
    require(error is None,'Command failed: '+name+': '+str(error))
    require(costs()['execution_allowed'],'Post-command resource ceiling exceeded')


def package_worker():
    source=HERE/'package-source';source.mkdir()
    shutil.copyfile(ROOT/'pyproject.toml',source/'pyproject.toml')
    shutil.copytree(ROOT/'src',source/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.pyo','*.egg-info'))
    python=read(PREP/'config.json')['package_python']
    require(sha(python)==read(PREP/'config.json')['python_sha256'],'Build interpreter changed')
    command('wheel',[python,'-I','-B','-m','pip','wheel','--no-deps','--no-build-isolation','--no-index',
                    '--wheel-dir',str(HERE/'wheel'),str(source)],60)
    wheels=list((HERE/'wheel').glob('*.whl'));require(len(wheels)==1,'Exactly one wheel required')
    expected={n.removeprefix('src/legalmath/'):h for n,h in read(HERE/'candidate-production.json').items()}
    with zipfile.ZipFile(wheels[0]) as archive:
        actual={n.removeprefix('legalmath/'):digest(archive.read(n)) for n in archive.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    same(actual,expected,'Wheel production differs')
    command('install',[python,'-I','-B','-m','pip','install','--no-index','--no-deps','--no-compile',
                      '--target',str(HERE/'installed'),str(wheels[0])],60)
    folder=HERE/'installed/legalmath'
    same({str(p.relative_to(folder)):sha(p) for p in folder.rglob('*') if p.is_file()},expected,'Installed bytes differ')
    save(HERE/'package.json',{'python':python,'wheel':ref(wheels[0]),'files':expected})


def coverage_worker():
    rows=[
        {'requirement':'Original51-173source membership under both conditional constructions','evidence':ref(BASE/'attempt-007/result.json'),'status':'RETAINED_CONDITIONAL'},
        {'requirement':'Individual/management51-54 and printed unit conflict','evidence':ref(BASE/'attempt-017/composition.json'),'status':'RETAINED_CONDITIONAL'},
        {'requirement':'Consolidated56-58/limited review172-173 full statement reading in normal/installed answer','status':'THIS_ATTEMPT_MUST_PASS'},
        {'requirement':'Page59equity clipping','evidence':ref(BASE/'attempt-010/RESULT.md'),'status':'UNKNOWN_CLIPPED_TOTALS_AND_UNIT'},
        {'requirement':'Cash-flow60 and risk162-163','evidence':ref(BASE/'attempt-007/RESULT.md'),'status':'RETAINED_CONDITIONAL'},
        {'requirement':'Policy2.15,Notes11/12/28/36/37/38 supplemental interpretation','evidence':ref(BASE/'attempt-016/answer-supplement.json.gz'),'status':'RETAINED_SUPPLEMENT_NOT_GENERAL_INTERPRETATION'},
        {'requirement':'Remaining policies/notes61-171','status':'SOURCE_RETAINED_BUT_FULL_SEMANTIC_COVERAGE_NOT_ESTABLISHED'},
        {'requirement':'Controlling Portuguese edition, historical authority and incorporation','status':'NOT_ESTABLISHED'},
        {'requirement':'BES Finance standalone accounts','status':'NOT_SUPPLIED_BY_BANK_GROUP_STATEMENTS'}]
    save(HERE/'requirements.json',{'rows':rows,'original_task_acceptance':False,'external_adviser_opinion_required':False,
        'next_discriminating_work':'Map original remaining note headings and exact incorporation requirements; prioritize a named missing source-to-answer dependency, not another install replay'})


def stage(name):
    require(name in DEPENDENCIES and not (HERE/'stages'/name).exists(),'Unknown or already started stage')
    for parent in DEPENDENCIES[name]: require(read(HERE/'stages'/parent/'result.json')['status']=='PASS','Failed predecessor: '+parent)
    candidate=(HERE/'candidate-production.json').exists()
    frozen(candidate)
    reserve=46*1024**2 if name=='package' else 2*1024**2
    require(costs(reserve)['execution_allowed'],'Stage storage reservation exhausted')
    save(HERE/'stages'/name/'started.json',{'pid':os.getpid(),'at':datetime.now(timezone.utc).isoformat(),'stage':name})
    error=None
    try:
        if name=='tests': command('tests',[str(ROOT/'.venv/bin/python'),'-B','-m','pytest','-q',*TESTS,'--junitxml='+str(HERE/'tests.xml')],120)
        elif name=='package': package_worker()
        else:
            python=read(PREP/'config.json')['package_python'] if name=='installed' else str(ROOT/'.venv/bin/python')
            command(name,[python,'-I','-B',str(ROOT/SELF),'worker-'+name],120)
        frozen((HERE/'candidate-production.json').exists())
    except Exception as exc: error={'type':type(exc).__name__,'reason':str(exc)}
    save(HERE/'stages'/name/'result.json',{'status':'FAIL' if error else 'PASS','error':error})
    return {'stage':name,'status':'FAIL' if error else 'PASS','resources':costs()}


def finalize():
    require(not (HERE/'outputs.json').exists(),'Already sealed')
    outcomes={n:read(HERE/'stages'/n/'result.json')['status'] if (HERE/'stages'/n/'result.json').exists() else 'BLOCKED' for n in DEPENDENCIES}
    passed=all(v=='PASS' for v in outcomes.values())
    save(HERE/'result.json',{'task':'source-bes-dep-05','status':'PASS' if passed else 'FAIL','stages':outcomes,
        'task_complete':False,'whole_program_complete':False,'build_criteria_claimed':[],'resources':costs()})
    (HERE/'RESULT.md').write_text('# H1 primary statement consumer continuation\n\n'
        +('Complete finite normal and installed integration passed. ' if passed else 'The integration campaign did not pass. ')
        +'Actual stage results: '+json.dumps(outcomes)+'.\n\n'
        +'The source check uses the original533occurrences and a separate image transcription of266cells across87rows. '
        +'All periods, EPS units, three unknown dashes, Group/Bank attributions and limited-review qualifications remain explicit. '
        +'Normal and installed receipts compare full answers and preserve016/017by lossless composition. See actual stage status before relying on any criterion.\n\n'
        +'|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|\n|---|---|---|---|---|---|\n'
        +'|'+('Retain finite integration' if passed else 'Retain diagnosed failure')+'|Full source/consumer comparisons|Retained stage records|Remaining notes, authenticity and controlling incorporation|Record/refresh; follow requirements.json|Financial truth, automatic parsing or whole task/build|\n\n'
        +'Post-run review: exact hashing preserves a supplied interpretation, not its truth. The separate image transcript and source/geometry checks test numeric associations; broader interpretations remain unresolved. '
        +'This is a local integration result, with no new external advice, extraction, network or GPU use. Failed historical attempts and all old ceilings remain unchanged.\n')
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(p) for p in sorted((HERE/'commands').glob('*.json'))],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1; GPUs intentionally hidden',
        'random_seeds':'N/A deterministic','plan':PLAN,'result':rel(HERE/'RESULT.md'),
        'data_version':ref(PREP/'freeze.json'),'resources':costs()})
    save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    return {'status':'SEALED','candidate_passed':passed,'resources':costs()}


if __name__=='__main__':
    sys.dont_write_bytecode=True
    os.environ.update(CUDA_VISIBLE_DEVICES='-1',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
    action=sys.argv[1]
    if action.startswith('worker-'):
        kind=action.removeprefix('worker-')
        sys.path.insert(0,str(HERE/'installed') if kind=='installed' else str(ROOT/'src'))
        def forbidden(*args, **kwargs):
            raise RuntimeError('No native/network child allowed in retained-source worker')
        subprocess.Popen = forbidden
        if kind in ('ordinary','installed'): consumer_worker(kind)
        else: {'source':source_worker,'implement':implement_worker,'controls':controls_worker,'coverage':coverage_worker}[kind]()
        result={'status':'PASS','worker':kind}
    elif action=='prepare': result=prepare()
    elif action=='finalize': result=finalize()
    else: result=stage(action)
    print(json.dumps(result))
