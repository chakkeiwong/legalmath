"""Bounded, retained validation of the admitted temporal-input repair."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import gzip
import json
import os
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.prospectus.execution_authority import Authority, REL, file_hash
from legalmath.prospectus.successor import service, law_facts

PLAN = 'docs/plans/prospectus-interval-validation-2026-10-17.md'
REVIEW = ROOT / REL / 'reviews/interval-validation'
OLD = ROOT / REL / 'attempts/law-applicability/attempt-006'
HERE = ROOT / REL / 'attempts/law-applicability/attempt-007'
BAD = [False, 0, 0.0, '', [], {}, True, 1, ['2027-01-01'], 'not-a-date',
       '2026-10-13', '2026-10-13T00:00:00', '2026-02-30T00:00:00Z']
TESTS = ['tests/prospectus_successor/test_interval_validation.py',
         'tests/prospectus_successor/test_ratio_facts.py',
         'tests/prospectus_successor/test_successor.py',
         'tests/prospectus_successor/test_adoption.py::test_ast_conflicting_overrides_and_half_open_dates']


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    with path.open('xb') as f:
        f.write(gzip.compress(data, mtime=0) if path.suffix == '.gz' else data)


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def methods():
    files = [p for p in (ROOT / 'src/legalmath').rglob('*')
             if p.is_file() and '__pycache__' not in p.parts]
    files += [ROOT / name.split('::')[0] for name in TESTS]
    files += [Path(__file__)]
    return {str(p.relative_to(ROOT)): file_hash(p) for p in sorted(files)}


def used_bytes():
    paths = [REVIEW, HERE, ROOT / PLAN, Path(__file__), ROOT / TESTS[0],
             ROOT / REL / 'proposals/interval-validation-224.json',
             ROOT / REL / 'proposals/interval-validation-224-review.json',
             ROOT / REL / 'revisions/0224.json',
             ROOT / REL / 'closure-routes-2026-10-17-after-solver-224.json',
             ROOT / REL / 'continuation-reviews/solver-223-record']
    files = set()
    for p in paths:
        files.update(q for q in p.rglob('*') if q.is_file()) if p.is_dir() else files.add(p)
    return sum(p.stat().st_size for p in files if p.exists())


def previous_seconds():
    return read(REVIEW / 'reproduction.json')['seconds'] + sum(
        read(p)['seconds'] for p in (HERE / 'stages').glob('*/result.json'))


def authenticate():
    auth = Authority(ROOT)
    spec, tasks, _ = auth.spec()
    require(spec['revision'] == 224, 'Wrong authority revision')
    admission = read(HERE / 'admission.json')
    require(admission['binding'] == auth.binding(tasks['law-applicability']), 'Admission input drift')
    for n, h in read(OLD / 'outputs.json').items():
        require(file_hash(OLD / n) == h, 'Original006 evidence changed: ' + n)
    before = read(REVIEW / 'before-methods.json')
    current = methods()
    require({n for n in current if n.startswith('src/')} == set(before), 'Unexpected production file change')
    require([n for n, h in before.items() if current[n] != h] ==
            ['src/legalmath/prospectus/successor/anchors.py'], 'Repair escaped declared production file')
    frozen = HERE / 'repaired-methods.json'
    if frozen.exists():
        require(read(frozen) == current, 'Repaired methods changed after execution started')
    else:
        save(frozen, current)
        for name in ['src/legalmath/prospectus/successor/anchors.py',
                     'scripts/prospectus_interval_validation.py', *[n.split('::')[0] for n in TESTS]]:
            target = HERE / 'methods' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write((ROOT / name).read_bytes())
    require(used_bytes() + 1024**2 < 32*1024**2, 'Storage reserve exceeded')
    require(previous_seconds() < 300, 'Cumulative runtime exceeded')
    return admission


def tests():
    # Pin imports before pytest; this interpreter's editable install can point
    # at the main worktree. The argv is retained exactly.
    command = [sys.executable, '-c',
        'import sys; sys.path[:0]=[sys.argv[1],sys.argv[2]]; import pytest; raise SystemExit(pytest.main(sys.argv[3:]))',
        str(ROOT / 'src'), str(ROOT), '-q', *TESTS, '--junitxml=' + str(HERE / 'tests.xml')]
    save(HERE / 'test-command.json', {'argv': command})
    with (HERE / 'tests.stdout').open('xb') as out, (HERE / 'tests.stderr').open('xb') as err:
        result = subprocess.run(command, cwd=ROOT, stdout=out, stderr=err, timeout=50,
                                env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    require(result.returncode == 0, 'Focused tests failed; retained logs required')
    suites = ET.parse(HERE / 'tests.xml').getroot()
    counts = {k: sum(int(s.get(k, '0')) for s in suites.iter('testsuite'))
              for k in ('tests', 'failures', 'errors', 'skipped')}
    require(counts['tests'] > 0 and not any(counts[k] for k in ('failures','errors','skipped')), 'Invalid test report')
    return counts


def execute(products, law, cases):
    p4 = service.law_product(products['P1'], products['P3'], cases=cases, law_input=law)
    answer = service.consume({**products, 'P4': p4}, ROOT, mode='current')
    require(answer['may_execute_transaction'] is False and answer['independent_legal_acceptance'] is False,
            'Conditional result acquired execution authority')
    return {'P4': p4, 'answer': answer}


def consumers():
    products = read(OLD / 'common-products.json.gz')
    scenarios = read(OLD / 'cases-result.json')['cases']
    cases = read(OLD / 'favorable-deposit-P4.json.gz')['payload']['cases']
    valid, refusals = [], []
    for row in scenarios:
        name = row['case']
        law = read(OLD / (name + '-input.json.gz'))
        try:
            record = execute(products, law, cases)
        except ValueError as exc:
            require(row['status'] == 'REJECTED', 'Valid baseline refused: ' + name)
            require(str(exc) == row['reason'], 'Original refusal changed: ' + name)
            refusals.append({'case': name, 'reason': str(exc)})
            continue
        require(row['status'] != 'REJECTED', 'Original adverse case accepted')
        require(record['answer'] == read(OLD / (name + '-answer.json.gz')), 'Complete answer regression: ' + name)
        require(record['P4'] == read(OLD / (name + '-P4.json.gz')), 'Complete P4 regression: ' + name)
        save(HERE / 'valid' / (name + '.json.gz'), record)
        valid.append({'case': name, 'status': row['status'], 'complete_equal': True})
    favorable = read(OLD / 'favorable-deposit-input.json.gz')
    adverse = []
    for target in ('law_bases','facts'):
        for field in ('valid_until','known_until'):
            for i, value in enumerate(BAD):
                data = deepcopy(favorable)
                data[target][0][field] = value
                try:
                    execute(products, data, cases)
                except ValueError as exc:
                    adverse.append({'id': f'{target}/{field}/{i}', 'target': target, 'field': field,
                                    'value': value, 'status': 'REFUSED', 'reason': str(exc)})
                else:
                    raise ValueError('Malformed interval accepted: ' + str((target,field,i)))
    boundary = []
    timepoint = '2026-10-13T00:00:00Z'
    for target in ('law_bases','facts'):
        for field in ('valid_until','known_until'):
            for label, ending, expected in [('null', None, 'YES'),
                    ('after', '2026-10-14T00:00:00Z', 'YES'),
                    ('at', timepoint, 'UNKNOWN'),
                    ('equivalent-offset', '2026-10-13T08:00:00+08:00', 'UNKNOWN')]:
                data = deepcopy(favorable)
                changed = data[target][0]
                changed[field.replace('until','from')] = '2026-10-12T00:00:00Z'
                changed[field] = ending
                record = execute(products, data, cases)
                actual = record['answer']['questions']['Q4']['status']
                require(actual == expected, 'Half-open boundary mismatch')
                if label == 'null':
                    absent = deepcopy(data); del absent[target][0][field]
                    counterpart = execute(products, absent, cases)
                    require(record['answer']['questions'] == counterpart['answer']['questions'],
                            'Explicit null altered substantive open-end result')
                name = target + '-' + field + '-' + label
                save(HERE / 'boundaries' / (name + '.json.gz'), {'input':data, **record})
                boundary.append({'case':name,'status':actual,'expected':expected})
    # An intentionally permissive old helper must fail the very same adverse
    # criterion. This is a local test injection, never a production fallback.
    namespace = {}
    source = (REVIEW / 'before-anchors.py').read_text().replace('from .contracts import timestamp',
        'from legalmath.prospectus.successor.contracts import timestamp')
    exec(compile(source, 'retained-before-anchors.py', 'exec'), namespace)
    good = law_facts.in_period
    try:
        law_facts.in_period = namespace['in_period']
        mutant = deepcopy(favorable); mutant['law_bases'][0]['valid_until'] = False
        found = execute(products, mutant, cases)['answer']['questions']['Q4']['status']
        require(found == 'YES', 'Mutation control did not expose original defect')
    finally:
        law_facts.in_period = good
    result = {'valid': valid, 'original_refusals': refusals, 'new_refusals': adverse,
              'boundaries': boundary, 'bad_helper_reproduces_yes': True,
              'actual_legal_currentness_established': False, 'whole_task_complete': False}
    save(HERE / 'consumer-evidence.json', result)
    return {'complete_valid':len(valid),'original_refusals':len(refusals),
            'malformed_refusals':len(adverse),'boundary_consumers':len(boundary),
            'bad_helper_detected':True}


def seal():
    evidence = read(HERE / 'consumer-evidence.json')
    require(len(evidence['valid']) == 21 and len(evidence['new_refusals']) == 52 and
            len(evidence['original_refusals']) == 2 and len(evidence['boundaries']) == 16, 'Incomplete consumer matrix')
    require(all(read(HERE / 'stages' / name / 'result.json')['status'] == 'PASS'
                for name in ('tests','consumers')), 'Required stage missing')
    return {'status': 'PASS', 'known_seconds_before_seal':previous_seconds(), 'new_bytes':used_bytes(),
            'summary': {'complete_valid':21,'original_refusals':2,'new_refusals':52,'boundary_consumers':16}}


def main():
    stage = sys.argv[1]
    require(stage in {'tests','consumers','seal'}, 'Unknown stage')
    folder = HERE / 'stages' / stage
    save(folder / 'started.json', {'command':['.venv/bin/python','scripts/prospectus_interval_validation.py',stage],
        'at':datetime.now(timezone.utc).isoformat(), 'cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1'})
    start = time.monotonic()
    signal.alarm(60)
    try:
        admission = authenticate()
        detail = globals()[stage]()
        require(methods() == read(HERE / 'repaired-methods.json'), 'Method drift')
        require(previous_seconds()+time.monotonic()-start < 300, 'Cumulative bound')
        require(used_bytes()+1024**2 < 32*1024**2, 'Storage bound')
        result = {'status':'PASS','seconds':time.monotonic()-start,'detail':detail}
    except Exception as exc:
        save(folder / 'result.json', {'status':'FAIL','seconds':time.monotonic()-start,
                                    'error':type(exc).__name__+': '+str(exc)})
        raise
    save(folder / 'result.json', result)
    if stage == 'seal':
        manifest = {'git_commit':admission['git_commit'],'plan':PLAN,
            'result':str((HERE/'RESULT.md').relative_to(ROOT)), 'interpreter':sys.executable,
            'environment': 'Existing .venv; imports pinned to current worktree src',
            'cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1','random_seeds':'N/A deterministic',
            'sources':str((OLD/'outputs.json').relative_to(ROOT)),
            'source_manifest_sha256':file_hash(OLD/'outputs.json'),
            'methods':'repaired-methods.json', 'commands':[read(p) for p in sorted((HERE/'stages').glob('*/started.json'))],
            'stages':{p.parent.name:read(p) for p in (HERE/'stages').glob('*/result.json')},
            'known_seconds_including_preparation':previous_seconds(),'historical_unmeasured_seconds':'UNKNOWN',
            'new_bytes_before_seal':used_bytes()}
        save(HERE/'run-manifest.json',manifest)
        save(HERE/'result.json',{'task':'law-applicability','status':'PASS',
            'scope':'MALFORMED_INTERVAL_VALIDATION','whole_task_complete':False,
            'whole_program_complete':False, **detail})
        require((HERE/'RESULT.md').is_file(), 'Detailed result note required')
        save(HERE/'outputs.json',{str(p.relative_to(HERE)):file_hash(p) for p in sorted(HERE.rglob('*'))
            if p.is_file() and p.name not in {'admission.json','outputs.json'} and '__pycache__' not in p.parts})
    signal.alarm(0)
    print(json.dumps({'stage':stage,**result}))

if __name__ == '__main__':
    main()
