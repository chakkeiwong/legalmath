"""One retained comparator repair; every stage checks its prerequisites."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import shutil
import signal
import sys
import time

from scripts import prospectus_basf_statement as base
from legalmath.prospectus.execution_authority import read, file_hash
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest

ROOT, OUTER = base.ROOT, base.HERE
HERE = OUTER / 'repair'
OFFICE = base.BASE / 'basf-office/attempt-002'
MARGINS = base.BASE / 'basf-margins/attempt-003'
ORIGINAL_METHODS = base.methods
base.HERE, base.PRIOR = HERE, OFFICE
save, load = base.save, base.load
PREDECESSORS = {'prepare': (), 'baseline': ('prepare',), 'profile': ('baseline',),
                'compare': ('baseline', 'profile'), 'controls': ('compare',), 'tests': ('compare',)}


def methods():
    paths = [Path(__file__), OUTER / 'REPAIR-PLAN.md']
    return {**ORIGINAL_METHODS(), **{str(p.relative_to(ROOT)): file_hash(p) for p in paths}}


def bindings():
    assert not (OUTER / 'outputs.json').exists()
    ad = read(OUTER / 'admission.json')
    assert all(file_hash(ROOT / p) == h for p, h in ad['binding'].items())
    assert ORIGINAL_METHODS() == read(OUTER / 'methods.json')
    if (HERE / 'methods.json').exists():
        assert methods() == read(HERE / 'methods.json')
    if (HERE / 'protected-inputs.json').exists():
        assert all(file_hash(ROOT / p) == h for p, h in read(HERE / 'protected-inputs.json').items())
    return ad


def prepare():
    protected = {}
    for folder in (OFFICE, MARGINS):
        for p, h in read(folder / 'outputs.json').items():
            assert file_hash(folder / p) == h
            protected[str((folder / p).relative_to(ROOT))] = h
        protected[str((folder / 'outputs.json').relative_to(ROOT))] = file_hash(folder / 'outputs.json')
    save('protected-inputs.json', protected)
    save('methods.json', methods())
    for p in methods():
        target = HERE / 'methods' / p
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / p, target)
    common = load(MARGINS / 'common.json.gz')
    request = deepcopy(common['request'])
    request['clauses'] = deepcopy(common['candidate_clauses'])
    request['observations'] = {}
    graph = load(MARGINS / 'original-graph.json.gz')
    p1 = service.seal('P1', request['bundle'], {'request': digest(request)}, {'request': request, 'graph': graph})
    p2 = service.seal('P2', request['bundle'], {'P1': p1['sha256']}, common['P2_payload'])
    p3 = load(MARGINS / 'candidate-P3.json.gz')
    products = dict(P1=p1, P2=p2, P3=p3, P4=service.law_product(p1, p3), P5=service.financial_product(p1, p2, p3))
    headers = {k: {x: y for x, y in v.items() if x != 'payload'} for k, v in products.items()}
    assert headers == load(OFFICE / 'candidate-products.json.gz')
    save('products.json.gz', products)
    save('comparator-review.json', {'status': 'PASS', 'baseline': str(OFFICE.relative_to(ROOT)),
        'all_five_product_headers_equal': True, 'old_baseline_stage': 'FAILED',
        'old_comparison': 'INVALID: failed baseline prerequisite; its full_latest_answer_equal field unsupported',
        'local_repairs_used': 1, 'native_calls': 0, 'http_calls': 0})
    return {'current_baseline': str(OFFICE.relative_to(ROOT)), 'all_five_product_headers_equal': True}


def main():
    stage = sys.argv[1]
    assert stage in PREDECESSORS
    ad = bindings()
    for prior in PREDECESSORS[stage]:
        assert read(HERE / 'invocations' / prior / 'result.json')['status'] == 'PASS', 'Failed prerequisite: ' + prior
    folder = HERE / 'invocations' / stage
    folder.mkdir(parents=True, exist_ok=False)
    save('invocations/' + stage + '/started.json', {
        'command': ['.venv/bin/python', '-m', 'scripts.prospectus_basf_statement_repair', stage],
        'git_commit': ad['git_commit'], 'plan': str((OUTER / 'REPAIR-PLAN.md').relative_to(ROOT)),
        'environment': sys.executable, 'started_at': datetime.now(timezone.utc).isoformat(),
        'cpu_gpu': 'CPU only; no GPU/framework imports', 'random_seeds': 'N/A deterministic',
        'required_predecessors': list(PREDECESSORS[stage])})
    tick = time.monotonic()
    def expire(signum, frame):
        raise TimeoutError('120-second comparator repair bound;no further repair authorized')
    signal.signal(signal.SIGALRM, expire)
    signal.alarm(120)
    try:
        details = prepare() if stage == 'prepare' else getattr(base, stage)()
        bindings()
        size = sum(p.stat().st_size for p in OUTER.rglob('*') if p.is_file())
        assert size < 350 * 1024 * 1024
        result = {'status': 'PASS', 'stage': stage, 'details': details,
                  'wall_seconds': time.monotonic() - tick, 'retained_bytes': size}
    except BaseException as error:
        save('invocations/' + stage + '/result.json', {'status': 'FAIL', 'error': repr(error),
                                                     'wall_seconds': time.monotonic() - tick})
        raise
    finally:
        signal.alarm(0)
    save('invocations/' + stage + '/result.json', result)
    print(result)


if __name__ == '__main__':
    main()
