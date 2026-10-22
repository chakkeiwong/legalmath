"""Bounded FY2010 source-scope repair and actual installed evaluation."""
import argparse
from copy import deepcopy
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
WORK = ROOT / '.localresources/prospectus-preparation/fy2010-scope'
PREP = AUTH / 'reviews/fy2010-scope-436'
HERE = AUTH / 'attempts/source-bes-dep-08/attempt-009'
OLD = AUTH / 'attempts/source-bes-dep-08/attempt-006'
TASK = 'source-bes-dep-08'
SELF = 'scripts/prospectus_fy2010_scope_program.py'
PLAN = 'docs/plans/prospectus-fy2010-scope-reconciliation-2026-10-22.md'
TEST = 'tests/prospectus_successor/test_fy2010_statement_scope.py'
CHANGES = ['prospectus/successor/bes_statement_scope.py', 'prospectus/successor/bes_fy2010_scope.py']
LIMITS = {'new_bytes': 256 * 1024**2, 'reserve_bytes': 2 * 1024**2,
          'seconds': 600, 'process_seconds': 120, 'unchanged_retries': 0}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    return str(Path(path).relative_to(ROOT))


def save(path, value):
    path = Path(path)
    raw = (json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n').encode()
    if path.suffix == '.gz':
        raw = gzip.compress(raw, compresslevel=1, mtime=0)
    require(len(raw) < 32 * 1024**2, 'Individual output ceiling')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)


def inventory(folder):
    return {str(p.relative_to(folder)): sha(p) for p in sorted(Path(folder).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}


def authority():
    sys.path.insert(0, str(ROOT / 'src'))
    from legalmath.prospectus.execution_authority import Authority
    return Authority(ROOT)


def prepare():
    start = time.monotonic()
    a = authority()
    p, _, _ = a.spec()
    require(p['revision'] == 435 and not PREP.exists() and not HERE.exists(), 'Fresh435required')
    require(read(WORK / 'probe/result.json')['status'] == 'REPRODUCED', 'Actual omission reproduction required')
    events = a.events()
    last = next(e for e in reversed(events) if e.get('task') == 'source-bes-dep-05')
    require(last['kind'] == 'REJECT' and last['reason'] == 'Installed-component storage ceiling', 'Retain071failure')
    donor = read(AUTH / 'reviews/component-435/donor.json')
    folders = [AUTH / 'reviews/component-435', AUTH / 'attempts/source-bes-dep-05/attempt-071']
    observed = sum(f.stat().st_size for d in folders for f in d.rglob('*') if f.is_file())
    save(PREP / 'accounting-start.json', {'inherited434': donor['prior_cumulative_costs'],
         'observed435review_attempt_bytes': observed, 'observed435other_files': {
             rel(f): f.stat().st_size for f in [AUTH / 'revisions/0435.json',
             *sorted((AUTH / 'proposals').glob('component-435*.json'))]},
         'prior071rejection': last, 'history_names': [f.name for f in (AUTH / 'history').glob('*.json')],
         'program_bytes': (AUTH / 'program.json').stat().st_size,
         'cumulative_note': 'Retain prior ledger and disjoint observed additions; earlier manual time remains unknown. No new phase resets any earlier bound.'})
    target = WORK / 'candidate/src/legalmath'
    shutil.copytree(ROOT / 'src/legalmath', target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    save(PREP / 'baseline.json', {'production': inventory(ROOT / 'src/legalmath'),
         'program_sha256': hashlib.sha256(json.dumps(p, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest(),
         'runtime': read(AUTH / 'reviews/release-applicability-434/freeze.json')['runtime'],
         'seconds': time.monotonic() - start})
    return {'status': 'PREPARED'}


def costs():
    initial = read(PREP / 'accounting-start.json')
    files = {f for folder in (WORK, PREP, HERE) if folder.exists() for f in folder.rglob('*')
             if f.is_file() and '__pycache__' not in f.parts}
    files |= {ROOT / SELF, ROOT / PLAN, ROOT / TEST, ROOT / 'scripts/prospectus_fy2010_scope_probe.py'}
    files |= {ROOT / 'src/legalmath' / n for n in CHANGES}
    files.add(AUTH / 'revisions/0436.json')
    files.update(f for f in (AUTH / 'history').glob('*.json') if f.name not in initial['history_names'])
    size = sum(f.stat().st_size for f in files if f.is_file())
    size += max(0, (AUTH / 'program.json').stat().st_size - initial['program_bytes'])
    seconds = read(WORK / 'probe/result.json')['seconds'] + read(PREP / 'baseline.json')['seconds']
    seconds += sum(read(f)['seconds'] for folder in (PREP, HERE) for f in folder.glob('commands/*.json')
                   if 'seconds' in read(f) and read(f).get('role') != 'NESTED')
    return {'new_bytes': size, 'new_measured_seconds': seconds, 'inherited': rel(PREP / 'accounting-start.json'),
            'unknown_manual_seconds': 'UNKNOWN', 'limits': LIMITS,
            'allowed': size + LIMITS['reserve_bytes'] < LIMITS['new_bytes'] and seconds < LIMITS['seconds']}


def command(name, argv, folder, *, seconds=120, nested=False):
    usage = costs()
    require(usage['allowed'] and usage['new_measured_seconds'] + seconds < LIMITS['seconds'], 'Execution bound')
    folder.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONPATH': '', 'PYTHONNOUSERSITE': '1',
           'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
           'PIP_NO_INDEX': '1', 'PIP_NO_CACHE_DIR': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1'}
    tick = time.monotonic()
    with (folder / (name + '.log')).open('x') as log:
        child = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        save(folder / (name + '-started.json'), {'argv': argv, 'pid': child.pid, 'time_ns': time.time_ns()})
        try:
            code = child.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
            code = -1
    save(folder / (name + '.json'), {'argv': argv, 'exit_code': code, 'seconds': time.monotonic() - tick,
         'role': 'NESTED' if nested else 'OUTER', 'environment': {k: env[k] for k in ('CUDA_VISIBLE_DEVICES', 'PIP_NO_INDEX', 'PYTHONPATH')}})
    require(code == 0, 'Inspect retained ' + name + ' failure')
    require(costs()['allowed'], 'Post-command resource ceiling')


def trial():
    code = ('import sys; from pathlib import Path; r=Path.cwd(); '
            'sys.path[:0]=[str(r/".localresources/prospectus-preparation/fy2010-scope/candidate/src"),str(r)]; '
            'import pytest; raise SystemExit(pytest.main(["-q","-p","no:cacheprovider",'
            '"tests/prospectus_successor/test_fy2010_statement_scope.py",'
            '"tests/prospectus_successor/test_bes_statement_scope.py",'
            '"tests/prospectus_successor/test_statement_cells.py",'
            '"--junitxml=.localresources/prospectus-preparation/fy2010-scope/tests.xml"]))')
    command('tests', [str(ROOT / '.venv/bin/python'), '-I', '-B', '-c', code], PREP / 'commands', seconds=60)
    command('candidate', [str(ROOT / '.venv/bin/python'), '-I', '-B', str(ROOT / SELF), 'worker', '--kind', 'candidate'], PREP / 'commands')
    return {'status': 'PASS', 'costs': costs()}


def source_units():
    value = read(AUTH / 'attempts/source-bes-dep-08/attempt-005/P1.json.gz')
    return value['payload']['graph']


def controls(graph, assembly, packet):
    """Finite original-page adverse inputs through reference admission."""
    from legalmath.prospectus.successor import reviewed_references
    from legalmath.prospectus.successor.contracts import digest
    from legalmath.prospectus.successor.occurrences import anchor
    cases = ('one_unit', 'omit_last', 'omit_page', 'partial_quote', 'duplicate', 'extra_cover',
             'wrong_source', 'wrong_use', 'wrong_form', 'excluded_restriction', 'changed_selected_text',
             'wrong_questions', 'missing_source_unit', 'changed_original_text', 'hidden_target')
    results = []
    for name in cases:
        g, asm, p = graph, assembly, deepcopy(packet)
        row = p['references'][0]
        if name == 'one_unit': row['targets'] = row['targets'][:1]
        elif name == 'omit_last': row['targets'].pop()
        elif name == 'omit_page': row['targets'] = [v for v in row['targets'] if ':p41:' in v['use']]
        elif name == 'partial_quote': row['targets'][0]['source'] = anchor(next(u for u in graph['units'] if u['id'] == row['targets'][0]['use']), 0, 5)
        elif name == 'duplicate': row['targets'][-1] = deepcopy(row['targets'][0])
        elif name == 'extra_cover':
            u = next(u for u in graph['units'] if u['document'] == 'bes-release-fy10' and u['page'] == 1)
            row['targets'].append({'source': anchor(u), 'use': u['id'], 'language': 'en'})
        elif name == 'wrong_source': row['targets'][0]['source']['source_sha256'] = '0' * 64
        elif name == 'wrong_use': row['targets'][0]['use'] = row['targets'][1]['use']
        elif name == 'wrong_form': row['form'] = 'named'
        elif name in ('excluded_restriction', 'changed_selected_text', 'wrong_questions'):
            asm = deepcopy(assembly)
            key = 'bes-supplement-2:p1:l37' if name == 'excluded_restriction' else row['targets'][-1]['use']
            u = next(u for u in asm['units'] if u['unit'] == key)
            if name == 'excluded_restriction': u['role'] = 'EXCLUDED'
            elif name == 'changed_selected_text': u['text'] += ' changed'
            else: u['questions'] = ['Q1']
        else:
            g = deepcopy(graph)
            u = next(u for u in g['units'] if u['id'] == row['targets'][-1]['use'])
            if name == 'missing_source_unit': g['units'].remove(u)
            elif name == 'hidden_target': u['visible'] = False
            else:
                u['raw'] += ' changed'
                u['text_sha256'] = digest(u['raw'].encode())
        p['assembly_sha256'] = digest(asm)
        try:
            reviewed_references.admit(g, asm, p)
        except ValueError as exc:
            results.append({'case': name, 'rejected': True, 'reason': str(exc)})
        else:
            raise ValueError('Scope control accepted: ' + name)
    return results


def verify_answer(answer, baseline, graph):
    """Independent set/meaning checker; no call into the new scope rule."""
    from legalmath.prospectus.successor.contracts import digest
    key = 'reviewed-reference:BES-DEP-08-conditional-statement-link'
    dep, = [d for d in answer['dependencies'] if d['id'] == key]
    required = {u['id'] for u in graph['units'] if u['document'] == 'bes-release-fy10' and u['page'] in (41, 42)}
    actual = [v['unit'] for v in dep['targets']]
    require(len(actual) == len(required) == 300 and set(actual) == required, 'Actual answer target coverage')
    scope = dep['statement_scope_check']
    require(scope['target_units'] == 300 and scope['pages'] == [41, 42] and
            scope['source_authenticity'] == 'NOT_ESTABLISHED' and scope['incorporation_status'] == 'UNRESOLVED' and
            not scope['independent_legal_acceptance'], 'Unsupported scope conclusion')
    source_by_id = {u['id']:u for u in graph['units']}
    def exact_anchor(unit):
        return {'unit':unit['id'], 'document':unit['document'], 'source_sha256':unit['source_sha256'],
                'start':0, 'end':len(unit['raw']), 'quote':unit['raw']}
    restriction = [u for u in graph['units'] if u['document']=='bes-supplement-2' and u['page']==1 and
                   (u['raw'].startswith('Any information not listed in the cross reference list') or u['raw']=='for information purposes only.')]
    require(len(restriction)==2 and scope['restriction']==[exact_anchor(u) for u in restriction], 'Scope restriction missing or changed')
    require(scope['release_identity_and_qualification']==[exact_anchor(source_by_id['bes-release-fy10:p1:l'+str(i)]) for i in range(5)], 'Release context changed')
    require(scope['context_pages_do_not_expand_incorporation'] is True, 'Context expanded incorporation')
    stripped = deepcopy(answer)
    del next(d for d in stripped['dependencies'] if d['id'] == key)['statement_scope_check']
    exempt = {'report_sha256', 'consumed_products'}
    require({k:v for k,v in stripped.items() if k not in exempt} == {k:v for k,v in baseline.items() if k not in exempt}, 'Unexplained complete answer change')
    cells = answer['source_statement_cells']
    rows = cells['rows']
    require(cells == baseline['source_statement_cells'] and len(rows) == 76 and sum(len(r['cells']) for r in rows) == 200, 'Statement meaning changed')
    require(sum(c['value'] is None for r in rows for c in r['cells']) == 23, 'Unknown dash changed')
    require(not answer['independent_legal_acceptance'] and not answer['may_execute_transaction'] and answer['questions']['Q3']['status'] == 'PARTIAL', 'Unsupported acceptance')
    return {'required_occurrences': 300, 'rows': 76, 'cells': 200, 'unknown_dashes': 23,
            'protected_answer_sha256': digest({k:v for k,v in stripped.items() if k not in exempt}),
            'source_meaning_preserved': True, 'source08_complete': False}


def oracle_controls(checker, answer, baseline, graph):
    caught = []
    for name in ('omitted-target', 'duplicate-target', 'erased-restriction', 'invented-authenticity', 'changed-cell', 'dash-to-zero'):
        changed = deepcopy(answer)
        dep = next(d for d in changed['dependencies'] if d['id']=='reviewed-reference:BES-DEP-08-conditional-statement-link')
        if name=='omitted-target': dep['targets'].pop()
        elif name=='duplicate-target': dep['targets'][-1]=deepcopy(dep['targets'][0])
        elif name=='erased-restriction': dep['statement_scope_check']['restriction']=[]
        elif name=='invented-authenticity': dep['statement_scope_check']['source_authenticity']='AUTHENTICATED'
        elif name=='changed-cell': changed['source_statement_cells']['rows'][0]['cells'][0]['value']+=1
        else:
            cell=next(c for r in changed['source_statement_cells']['rows'] for c in r['cells'] if c['value'] is None)
            cell['value']=0
        try:
            checker(changed,baseline,graph)
        except ValueError:
            caught.append(name)
        else:
            raise ValueError('Permissive answer checker: '+name)
    return caught


def evaluate(folder):
    from scripts import prospectus_fy2010_product as fy
    # The old helper pins its own CLI to source. The package was imported from
    # the selected candidate/installed root before loading it; remove its added
    # checkout path so later imports cannot silently switch production trees.
    sys.path[:] = [p for p in sys.path if Path(p or '.').resolve() != ROOT / 'src']
    from legalmath.prospectus.successor import service
    ps = fy.load_products(OLD, 'after')
    supplied = ps['P3']['payload']['interpretation_input']
    updated = fy.products(ps['P1'], supplied)
    answer = service.consume(updated, ROOT, mode='frozen', include_artifacts=True)
    save(folder / 'answer.json.gz', answer)
    graph = ps['P1']['payload']['graph']
    baseline = read(WORK / 'probe/baseline-answer.json.gz')
    proof = verify_answer(answer, baseline, graph)
    adverse = controls(graph, ps['P2']['payload']['assembly'], supplied['reference_admission'])
    bad = read(WORK / 'probe/omission-input.json.gz')
    try:
        changed = fy.products(ps['P1'], bad)
        service.consume(changed, ROOT, mode='frozen', include_artifacts=True)
    except ValueError as exc:
        refusal = {'rejected': True, 'reason': str(exc)}
    else:
        raise ValueError('Actual omitted-target consumer still accepted')
    oracle = oracle_controls(verify_answer,answer,baseline,graph)
    try:
        oracle_controls(lambda *_: True,answer,baseline,graph)
    except ValueError as exc:
        require(str(exc).startswith('Permissive answer checker:'), 'Wrong permissive control failure')
    else:
        raise ValueError('Permissive checker undetected')
    return {'status': 'PASS', 'proof': proof, 'controls': adverse, 'actual_omission': refusal,
            'oracle_controls':oracle,'permissive_checker_detected':True}


def worker(kind):
    target = WORK / 'candidate/src' if kind == 'candidate' else HERE / 'installed' if kind == 'installed' else ROOT / 'src'
    sys.path.insert(0, str(target))
    import legalmath.prospectus.successor.service
    folder = WORK / 'candidate-result' if kind == 'candidate' else HERE / kind
    folder.mkdir(parents=True, exist_ok=False)
    result = evaluate(folder)
    expected = (target / 'legalmath').resolve()
    imports = {}
    for name, module in sorted(sys.modules.items()):
        if name == 'legalmath' or name.startswith('legalmath.'):
            path = getattr(module, '__file__', None)
            if path:
                path = Path(path).resolve()
                require(path.is_relative_to(expected), 'Wrong package import: ' + name)
                imports[name] = {'path': str(path), 'sha256': sha(path)}
    require(sys.flags.isolated == 1, 'Isolated worker required')
    if kind != 'candidate':
        require(result == read(WORK / 'candidate-result/result.json'), 'Substantive result differs')
        require(read(folder / 'answer.json.gz') == read(WORK / 'candidate-result/answer.json.gz'), 'Complete installed/ordinary answer differs')
    save(folder / 'result.json', result)
    save(folder / 'imports.json', {'modules': imports, 'executable': sys.executable, 'sys_path': sys.path,
         'isolated': True, 'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1'})
    return {'status': 'PASS', 'worker': kind}


def freeze():
    a = authority()
    from legalmath.prospectus.execution_authority import digest
    old, _, _ = a.spec()
    require(old['revision'] == 435 and not a.status()['running'], 'Current435required')
    require(read(PREP / 'commands/tests.json')['exit_code'] == read(PREP / 'commands/candidate.json')['exit_code'] == 0, 'Candidate results required')
    baseline = read(PREP / 'baseline.json')
    require(inventory(ROOT / 'src/legalmath') == baseline['production'], 'Production changed')
    candidate = inventory(WORK / 'candidate/src/legalmath')
    changed = {n for n in set(candidate) | set(baseline['production']) if candidate.get(n) != baseline['production'].get(n)}
    require(changed == set(CHANGES), 'Unexpected production change')
    evidence = {n: sha(ROOT/n) for n in (SELF, PLAN, TEST, 'scripts/prospectus_fy2010_scope_probe.py')}
    evidence.update({rel(p): sha(p) for p in WORK.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    evidence.update({'src/legalmath/' + n:h for n,h in candidate.items()})
    save(PREP / 'freeze.json', {'evidence': evidence, 'candidate': candidate, 'baseline': baseline['production'],
         'runtime': baseline['runtime'], 'limits': LIMITS})
    proposal = deepcopy(old)
    proposal['revision'] = 436
    task = next(t for t in proposal['tasks'] if t['id'] == TASK)
    task.update(dossier=PLAN, pre_admission_review=PLAN, reason='Reproduced omitted FY2010 statement target incorrectly resolves through actual consumer',
                fy2010_scope_review=rel(PREP/'freeze.json'))
    task['inputs'] = sorted(set(task['inputs']) | set(evidence) | {rel(PREP/'freeze.json')})
    attempts = [e['attempt'] for e in a.events() if e['kind'] == 'ADMIT' and e['budget_key'] == TASK]
    require(len(attempts) == old['budgets'][TASK]['maximum_new_attempts'] == 8, 'Retain eight admissions')
    proposal['budgets'][TASK]['maximum_new_attempts'] = 9
    routes = read(ROOT / old['continuation_review']['routes'])
    routes['baseline_revision'] = 436
    for route in routes['tasks']:
        if route['task'] == TASK:
            route.update(task_sha256=digest(task), dossier=PLAN, phase=0,
                remaining='Actual299-target reference falsely resolves; preserve all original200cell meanings and authority unknowns.',
                next_action='Complete finite FY scope repair, ordinary/installed checks and full original-requirement reconciliation.',
                stop_condition='Admission009;600seconds256MiB; no unchanged retry or external action.')
        elif route['task'] == 'source-bes-dep-05':
            route.update(phase=2, remaining='071sealed functional checks passed but authority rejected the storage reserve shortfall; named criterion pending.',
                next_action='Review bounded compact evidence submission after substantive shared-code repairs; preserve rejected071 and avoid another full installation.',
                stop_condition='No072admission granted;435recovery exhausted.')
    save(PREP/'routes.json', routes)
    proposal['continuation_review'].update(plan=PLAN, routes=rel(PREP/'routes.json'))
    for n in CHANGES:
        key = 'src/legalmath/' + n
        if key in proposal['continuation_review']['bindings']:
            proposal['continuation_review']['bindings'][key] = candidate[n]
    proposal['continuation_review']['bindings'].update({n:sha(ROOT/n) for n in (SELF, PLAN, rel(PREP/'freeze.json'), rel(PREP/'routes.json'))})
    save(PREP/'proposal.json', proposal)
    save(PREP/'review.json', {'baseline':digest(old), 'scope_unchanged':True, 'budget_unchanged':False,
         'changes':['Enforce exact FY2010 statement targets and selected source restriction', 'Preserve source05/071storage rejection and original unresolved source scope'],
         'skeptical_audit':{'verdict':'PASS','plan':PLAN,'probe':rel(WORK/'probe/result.json'),'tests':rel(WORK/'tests.xml'),
             'primary':'Actual consumer, complete answer comparison and independent target-set checker'},
         'evidence_contract':{'baseline':rel(OLD),'primary':'Full300target coverage; all adverse scope controls refuse;200cell meaning unchanged',
             'promotion_veto':['Wrong scope/source/import','Changed financial meaning','False authenticity/acceptance'],
             'continuation_veto':['Invalid authority','Corrupt common evidence','Bound exhausted'],
             'explanatory':['Counts','Runtime','Arithmetic'], 'not_concluded':['General incorporation','Historical authenticity','Whole source/build completion']},
         'budget_revision':{'budget_key':TASK,'previous_maximum':8,'new_maximum':9,'retained_attempts':attempts,
             'reason':'Distinct actual source coverage failure reproduced after applicability repair',
             'next_discriminating_check':'Original positive and omission through ordinary and isolated installed consumer',
             'stop_condition':LIMITS,'same_scope_authorization':'Recover and continue original prospectus build'}})
    forecast = costs()['new_bytes'] + 3 * (PREP/'proposal.json').stat().st_size + 3 * sum((ROOT/'src/legalmath'/n).stat().st_size for n in baseline['production'])
    forecast += 2*(WORK/'candidate-result/answer.json.gz').stat().st_size + 12*1024**2
    require(forecast + LIMITS['reserve_bytes'] < LIMITS['new_bytes'], 'Final artifacts and authority overhead exceed forecast')
    save(PREP/'forecast.json', {'bytes':forecast,'includes_final_manifest_and_control_allowance':True})
    return {'status':'FROZEN','forecast_bytes':forecast}


def cutover():
    a = authority()
    from legalmath.prospectus.execution_authority import digest
    f = read(PREP/'freeze.json')
    require(digest(a.spec()[0]) == read(PREP/'review.json')['baseline'], 'Wrong cutover baseline')
    require(inventory(ROOT/'src/legalmath') == f['baseline'], 'Baseline changed')
    for n in CHANGES:
        shutil.copyfile(WORK/'candidate/src/legalmath'/n, ROOT/'src/legalmath'/n)
    require(inventory(ROOT/'src/legalmath') == f['candidate'], 'Cutover inventory differs')
    save(PREP/'cutover.json', {'changed':CHANGES,'revision_required':436})
    return {'status':'CUTOVER_COMPLETE_REVISION_REQUIRED'}


def admitted():
    a = authority()
    p,t,_ = a.spec()
    require(p['revision'] == 436 and read(HERE/'admission.json')['binding'] == a.binding(t[TASK]), 'Current436admission required')
    require(next(e for e in reversed(a.events()) if e.get('task') == TASK)['kind'] == 'ADMIT', 'Attempt terminal')


def stage(kind):
    admitted()
    frozen = read(PREP/'freeze.json')
    if kind == 'package':
        source = HERE/'package-source'
        source.mkdir()
        shutil.copyfile(ROOT/'pyproject.toml', source/'pyproject.toml')
        shutil.copytree(ROOT/'src', source/'src', ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info'))
        python = frozen['runtime']['package_python']
        command('wheel', [python,'-I','-B','-m','pip','wheel','--no-deps','--no-build-isolation','--no-index','--wheel-dir',str(HERE/'wheel'),str(source)], HERE/'commands', seconds=60)
        wheel, = (HERE/'wheel').glob('*.whl')
        command('install', [python,'-I','-B','-m','pip','install','--no-index','--no-deps','--no-compile','--target',str(HERE/'installed'),str(wheel)], HERE/'commands', seconds=60)
        require(inventory(HERE/'installed/legalmath') == frozen['candidate'], 'Installed inventory differs')
        save(HERE/'package.json', {'status':'PASS','files':frozen['candidate'],'wheel':{'path':rel(wheel),'sha256':sha(wheel)}})
    else:
        if kind == 'installed': require(read(HERE/'package.json')['status']=='PASS','Package required')
        python = frozen['runtime']['package_python' if kind == 'installed' else 'ordinary_python']
        command(kind, [python,'-I','-B',str(ROOT/SELF),'worker','--kind',kind], HERE/'commands')
    return {'status':'PASS','stage':kind,'costs':costs()}


def seal():
    admitted()
    frozen = read(PREP/'freeze.json')
    require(all(sha(ROOT/n)==h for n,h in frozen['evidence'].items()), 'Frozen evidence changed')
    require(inventory(ROOT/'src/legalmath') == frozen['candidate'] == inventory(HERE/'installed/legalmath'), 'Package differs')
    require(read(HERE/'ordinary/result.json') == read(HERE/'installed/result.json'), 'Consumers differ')
    require((HERE/'RESULT.md').is_file(), 'Substantive reconciliation required')
    usage = costs()
    save(HERE/'result.json', {'task':TASK,'status':'PASS','task_complete':False,'whole_program_complete':False,
         'costs':usage,'plan':PLAN,'interpretation':'Exact-source conditional scope repair; original authority and meaning limits retained'})
    save(HERE/'run-manifest.json', {'git_commit':read(HERE/'admission.json')['git_commit'], 'plan':PLAN, 'result':rel(HERE/'RESULT.md'),
         'commands':[rel(p) for p in sorted((HERE/'commands').glob('*.json'))], 'frozen':rel(PREP/'freeze.json'),
         'runtime':frozen['runtime'],'data_version':{'release_sha256':'b28420dced99cbb219a3f447ed43fa603d6ae1bc0086fb7705876e25631a569f'},
         'cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1','random_seeds':'N/A deterministic','wall_seconds':usage['new_measured_seconds']})
    output = {str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    projected = usage['new_bytes'] + len(json.dumps(output).encode()) + 1024*1024
    require(projected + LIMITS['reserve_bytes'] < LIMITS['new_bytes'], 'Post-manifest reserve required')
    save(HERE/'outputs.json', output)
    require(costs()['allowed'], 'Post-seal resource ceiling')
    return {'status':'SEALED','costs':costs()}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['prepare','trial','worker','freeze','cutover','stage','seal'])
    p.add_argument('--kind',choices=['candidate','ordinary','package','installed'])
    args=p.parse_args()
    result = worker(args.kind) if args.action=='worker' else stage(args.kind) if args.action=='stage' else globals()[args.action]()
    print(json.dumps(result),flush=True)
