"""Bounded annual policy/event candidate and actual-consumer verification."""
import argparse
from copy import deepcopy
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
from scripts.prospectus_annual_basis_source import AUTH, SOURCE, read, save, sha
from scripts.prospectus_annual_basis_program import inventory, fingerprint
WORK = ROOT / '.localresources/prospectus-preparation/annual-group'
from scripts.prospectus_annual_group_reading import PROFILE, FIELD, combine
from scripts.prospectus_annual_group_checks import check, mutations, require

PREP = AUTH / 'reviews/annual-group-445'
HERE = SOURCE / 'attempt-021'
OLD = SOURCE / 'attempt-020'
PLAN = 'docs/plans/prospectus-annual-group-integration-2026-10-22.md'
SELF = 'scripts/prospectus_annual_group_program.py'
CHANGE = 'prospectus/successor/statement_cells.py'
FIXTURE = 'tests/prospectus_successor/fixtures/bes_annual2010_statement_cells_v7.json.gz'
OLD_FIXTURE = 'tests/prospectus_successor/fixtures/bes_annual2010_statement_cells_v6.json.gz'
TEST = 'tests/prospectus_successor/test_annual_group_disclosures.py'
SUPPORT = [SELF, PLAN, FIXTURE, TEST, OLD_FIXTURE,
    'scripts/prospectus_annual_group_source.py', 'scripts/prospectus_annual_group_scaffold.py',
    'scripts/prospectus_annual_group_reading.py', 'scripts/prospectus_annual_group_checks.py',
    'docs/plans/prospectus-annual-group-source-review-2026-10-22.md']
PARTS = ['baseline', 'answer', 'controls', 'public-control', 'public-dash', 'public-scope', 'english']


def costs():
    prior = read(AUTH / 'reviews/annual-income-444/post-record.json')['costs']
    extra = (AUTH / 'reviews/annual-income-444/post-record.json').stat().st_size
    extra += (AUTH / 'continuation-reviews/after-444.json').stat().st_size
    seconds = read(WORK / 'preparation.json')['seconds']
    seconds += sum(read(p)['seconds'] for p in WORK.glob('render-*.json'))
    seconds += sum(read(p).get('seconds', 0) for folder in (PREP, HERE) for p in folder.glob('commands/*.json'))
    files = {p for folder in (WORK, PREP, HERE) if folder.exists() for p in folder.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    files.update(ROOT / p for p in SUPPORT)
    files.add(ROOT / 'scripts/prospectus_annual_group_submission.py')
    if (PREP / 'start.json').exists():
        start = read(PREP / 'start.json')
        files.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
        files.add(AUTH / 'revisions/0445.json')
        extra += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    size = sum(p.stat().st_size for p in files if p.is_file()) + extra
    return {'new_seconds': seconds, 'cumulative_charged_seconds': prior['cumulative_charged_seconds'] + seconds,
        'new_bytes': size, 'cumulative_bytes': prior['cumulative_bytes'] + size,
        'allowed': seconds < 650 and prior['cumulative_charged_seconds'] + seconds < 4360 and
            size + 2*1024**2 < 180*1024**2 and prior['cumulative_bytes'] + size + 2*1024**2 < 1100*1024**2}


def candidate():
    require(read(AUTH / 'program.json')['revision'] == 444, 'Baseline444required')
    require(not (WORK / 'candidate').exists(), 'No unchanged candidate retry')
    sys.path.insert(0, str(ROOT/'src'))
    from legalmath.prospectus.execution_authority import Authority
    a = Authority(ROOT)
    require(a.retained_evidence_valid(read(AUTH/'reviews/annual-income-444/post-record.json')['event']), '444 evidence changed')
    require(sha(SOURCE / 'attempt-002/original-P1.json.gz') == read(WORK / 'preparation.json')['source_sha256'], 'Original source changed')
    graph = read(SOURCE / 'attempt-002/original-P1.json.gz')['payload']['graph']
    old = read(ROOT / OLD_FIXTURE)['reading']
    require(old == read(OLD / 'ordinary-answer/request.json.gz')['source_statement_cells']['reading'], 'Wrong complete baseline reading')
    combined = combine(old, graph)
    proof = check(combined[FIELD], graph)
    pages = combined['source_context']['source_pages']
    selected = sorted([u for u in graph['units'] if u['document'] == 'bes-2010-en' and u['page'] in pages],
                      key=lambda u: (u['page'], u['order'], u['id']))
    save(ROOT / FIXTURE, {'graph': {'units': selected}, 'reading': combined})
    baseline = inventory(ROOT / 'src/legalmath')
    require(baseline == read(OLD / 'package.json')['files'], 'Production differs from verified444package')
    shutil.copytree(ROOT / 'src/legalmath', WORK / 'candidate/src/legalmath', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    entry = {'document': 'bes-2010-en', 'source': selected[0]['source_sha256'], 'reading': fingerprint(combined),
        'pages_digest': fingerprint(selected), 'pages': pages, 'occurrences': len(selected),
        'reading_fields': ['primary_statements', 'eps_cash_notes', 'capital_notes', 'basis_estimates_pronouncements', 'consolidation_assets_subsequent_events', 'remaining_accounting_policies', 'income_notes_and_group_context', FIELD]}
    path = WORK / 'candidate/src/legalmath' / CHANGE
    text = path.read_text()
    anchor = 'PROFILES = {' + chr(10)
    require(PROFILE not in text and text.count(anchor) == 1, 'Profile insertion changed')
    path.write_text(text.replace(anchor, anchor + '    ' + repr(PROFILE) + ': ' + repr(entry) + ',' + chr(10), 1))
    save(PREP / 'candidate.json', {'baseline': baseline, 'candidate': inventory(WORK / 'candidate/src/legalmath'),
        'profile': entry, 'source_proof': proof, 'plan_sha256': sha(ROOT / PLAN)})
    return {'status': 'PREPARED', 'source_occurrences': len(selected), 'proof': proof}


def command(name, argv, folder, limit=60):
    state = costs()
    require(state['allowed'] and state['new_seconds'] + limit < 650 and state['cumulative_charged_seconds'] + limit < 4360, 'Substantive ceiling')
    folder.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONPATH': '', 'PYTHONNOUSERSITE': '1',
        'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'PIP_NO_INDEX': '1',
        'PIP_NO_CACHE_DIR': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1'}
    started = time.monotonic()
    with (folder / (name + '.log')).open('x') as log:
        child = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        save(folder / (name + '-started.json'), {'argv': argv, 'pid': child.pid, 'time_ns': time.time_ns()})
        try:
            code = child.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
            code = -1
    save(folder / (name + '.json'), {'argv': argv, 'exit_code': code, 'seconds': time.monotonic()-started,
        'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1'})
    require(code == 0, 'Inspect retained failure ' + name)
    require(costs()['allowed'], 'Post-command ceiling')


def tests_suite(suite):
    suites={
      'new':[TEST],
      'previous':['tests/prospectus_successor/test_annual_income_notes.py','tests/prospectus_successor/test_annual_remaining_policies.py','tests/prospectus_successor/test_annual_consolidation_events.py'],
      'core':['tests/prospectus_successor/test_annual_basis_estimates.py','tests/prospectus_successor/test_statement_cells.py','tests/prospectus_successor/test_english_report_applicability.py']}
    argv=['-q','-p','no:cacheprovider',*suites[suite],'--junitxml='+str(WORK/('tests-'+suite+'.xml'))]
    code='import sys; from pathlib import Path; r=Path.cwd(); sys.path[:0]=[str(r/".localresources/prospectus-preparation/annual-group/candidate/src"),str(r)]; import pytest; raise SystemExit(pytest.main('+repr(argv)+'))'
    command('tests-'+suite,[str(ROOT/'.venv/bin/python'),'-I','-B','-c',code],PREP/'commands')
    return {'status':'PASS','suite':suite,'costs':costs()}


def expected_444(digest):
    from scripts.prospectus_annual_income_program import expected_443
    expected=expected_443(digest)
    delta=read(OLD/'ordinary-answer/answer-delta.json.gz')
    require(digest(expected)==delta['baseline_answer_sha256'],'Annual-v6 baseline changed')
    for row in delta['changes']:
        target=expected
        for key in row['path'][:-1]:target=target[key]
        target[row['path'][-1]]=row['value']
    require(digest(expected)==delta['actual_answer_sha256'],'Complete444 reconstruction differs')
    return expected


def base_products():
    from scripts.prospectus_2010_capital_product_cases import configure, original
    from scripts.prospectus_2010_annual_cases import reseal
    configure(ROOT, SOURCE/'attempt-012')
    ps = original()
    delta = read(SOURCE/'attempt-012/after-delta.json.gz')
    for phase, addition in delta['payload_additions'].items():
        target = ps[phase]['payload']['request'] if phase == 'P1' else ps[phase]['payload']
        require(not set(target)&set(addition), 'Unexpected existing product addition')
        target.update(addition)
    reseal(ps)
    require({k:v['sha256'] for k,v in ps.items()} == delta['expected_hashes'], 'Original products differ')
    return ps


def finish(result, folder, target, kind, part):
    imports = {}
    for name, module in sys.modules.copy().items():
        filename = getattr(module, '__file__', None)
        if filename and (name == 'legalmath' or name.startswith('legalmath.')):
            path = Path(filename).resolve()
            require(path.is_relative_to((target/'legalmath').resolve()), 'Wrong project import '+name)
            imports[name] = {'path': str(path), 'sha256': sha(path)}
    require(sys.flags.isolated == 1, 'Isolated worker required')
    if kind != 'candidate':
        require(result == read(WORK/('candidate-'+part)/'result.json'), 'Candidate/current/installed mismatch')
    save(folder/'result.json', result)
    save(folder/'imports.json', {'modules': imports, 'executable': sys.executable, 'isolated': True})


def worker(kind, part):
    target = WORK/'candidate/src' if kind == 'candidate' else HERE/'installed-package' if kind == 'installed' else ROOT/'src'
    sys.path.insert(0, str(target))
    from legalmath.prospectus.successor import service, statement_cells
    from legalmath.prospectus.successor.contracts import digest
    from scripts import prospectus_english_applicability_program as earlier
    from scripts.prospectus_2010_capital_product_cases import configure, p1_from, rebuild
    configure(ROOT, SOURCE/'attempt-012')
    folder = WORK/(kind+'-'+part) if kind == 'candidate' else HERE/(kind+'-'+part)
    folder.mkdir(parents=True, exist_ok=False)
    if part in ('baseline','answer'):
        expected = expected_444(digest)
        reference = base_products()
        req = read(OLD/'ordinary-answer/request.json.gz')
        graph = reference['P1']['payload']['graph']
        if part == 'answer':
            prerequisite = WORK/'candidate-baseline' if kind == 'candidate' else HERE/(kind+'-baseline')
            require(read(prerequisite/'result.json')['status']=='PASS', 'Complete old-v6consumer baseline required')
            req['source_statement_cells'] = {**req['source_statement_cells'], 'profile': PROFILE, 'reading': read(ROOT/FIXTURE)['reading'],
                'review': {'kind':'DEVELOPMENT','reviewer':'inspected original annual source',
                          'reason':'Preserve seven prior fields; add original Note1 group disclosures'}}
        products = rebuild(reference, p1_from(req, graph))
        answer = service.consume(products, ROOT, mode='frozen', include_artifacts=True)
        if part == 'baseline':
            require(answer == expected, 'Complete old-v6answer changed')
            result = {'status':'PASS','complete_444_answer_sha256':digest(answer)}
        else:
            skip = {'source_statement_cells','request_sha256','report_sha256','consumed_products'}
            require({k:v for k,v in answer.items() if k not in skip} == {k:v for k,v in expected.items() if k not in skip}, 'Unrelated complete answer changed')
            for key in ('primary_statements','eps_cash_notes','capital_notes','basis_estimates_pronouncements','consolidation_assets_subsequent_events','remaining_accounting_policies','income_notes_and_group_context'):
                require(answer['source_statement_cells'][key] == expected['source_statement_cells'][key], 'Old meaning changed '+key)
            proof = check(answer['source_statement_cells'][FIELD], graph)
            require(not answer['source_statement_cells']['source_context']['all_notes_read'] and
                    answer['questions']['Q3']['status']=='PARTIAL' and not answer['may_execute_transaction'] and
                    not answer['independent_legal_acceptance'], 'Unsupported promotion')
            save(folder/'answer-delta.json.gz', {'baseline':{'path':str((OLD/'ordinary-answer/answer-delta.json.gz').relative_to(ROOT)),
                'sha256':sha(OLD/'ordinary-answer/answer-delta.json.gz')}, 'baseline_answer_sha256':digest(expected),
                'actual_answer_sha256':digest(answer), 'changes':earlier.answer_delta(expected,answer)})
            save(folder/'request.json.gz',req)
            result = {'status':'PASS','baseline_answer_sha256':digest(expected),'actual_answer_sha256':digest(answer),
                'proof':proof,'all_notes_read':False,'task_complete':False}
    elif part == 'english':
        cases = read(SOURCE/'attempt-015/ordinary-result/result.json')['cases']
        result_cases = []
        for path in sorted((earlier.PROBE/'packets').glob('*.json.gz')):
            prior = next(r for r in cases if r['case']==path.stem)
            try:
                answer = service.consume(earlier.products(service,read(path)),ROOT,mode='current',include_artifacts=True)
            except ValueError as exc:
                require(prior['refused'] and prior['reason']==str(exc),'English refusal changed')
                result_cases.append({'case':path.stem,'refused':True})
            else:
                require(not prior['refused'] and digest(answer)==prior['answer_sha256'],'English answer changed')
                result_cases.append({'case':path.stem,'refused':False,'answer_sha256':digest(answer)})
        result={'status':'PASS','english_regressions':result_cases}
    else:
        base=WORK/'candidate-answer' if kind=='candidate' else HERE/(kind+'-answer')
        require(read(base/'result.json')['status']=='PASS','Matched new answer required')
        req=read(base/'request.json.gz')
        graph=read(SOURCE/'attempt-002/original-P1.json.gz')['payload']['graph']
        names={'public-control':'majority','public-dash':'dash-imputed','public-scope':'ascendi-scope'}
        caught=[]
        public=[]
        for name,changed in mutations(req['source_statement_cells']['reading'][FIELD]):
            if part!='controls' and names.get(part)!=name:
                continue
            try:
                check(changed,graph)
            except ValueError:
                pass
            else:
                raise ValueError('Semantic checker accepted '+name)
            bad=deepcopy(req['source_statement_cells'])
            bad['reading'][FIELD]=changed
            try:
                statement_cells.admit(graph,bad)
            except ValueError as exc:
                require('reading differs' in str(exc),'Wrong refusal '+name)
                caught.append(name)
            else:
                raise ValueError('Production accepted '+name)
            if part in names:
                altered=deepcopy(req)
                altered['source_statement_cells']=bad
                try:
                    service.construction_product(p1_from(altered,graph),ROOT)
                except ValueError as exc:
                    require('reading differs' in str(exc),'Wrong public refusal '+name)
                    public.append(name)
                else:
                    raise ValueError('Public construction accepted '+name)
        result={'status':'PASS','semantic_mutations_refused':caught,'public_refusals':public}
    finish(result,folder,target,kind,part)
    return {'status':'PASS','kind':kind,'part':part}


def run_part(part):
    command('candidate-'+part,[str(ROOT/'.venv/bin/python'),'-I','-B',str(ROOT/SELF),'worker','--kind','candidate','--part',part],PREP/'commands')
    return {'status':'PASS','part':part,'costs':costs()}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['candidate','tests','run-part','worker','costs'])
    parser.add_argument('--suite',choices=['new','previous','core'])
    parser.add_argument('--kind',choices=['candidate','ordinary','installed'])
    parser.add_argument('--part',choices=PARTS)
    args=parser.parse_args()
    started=time.monotonic()
    receipt=PREP/'commands/candidate-preparation.json'
    if args.action=='candidate' and receipt.exists():
        require((PREP/'failed-candidate/candidate-preparation.json').exists(),'Diagnosed failure must be preserved')
        receipt=PREP/'commands/candidate-recovery.json'
        require(not receipt.exists(),'Single changed recovery already used')
    try:
        result=worker(args.kind,args.part) if args.action=='worker' else run_part(args.part) if args.action=='run-part' else tests_suite(args.suite) if args.action=='tests' else globals()[args.action]()
    except Exception as exc:
        if args.action=='candidate':
            save(receipt,{'argv':sys.argv,'exit_code':1,'seconds':time.monotonic()-started,'error':str(exc)})
        raise
    if args.action=='candidate':
        save(receipt,{'argv':sys.argv,'exit_code':0,'seconds':time.monotonic()-started})
    print(json.dumps(result),flush=True)
