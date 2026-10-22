"""Bounded offline replay of all six optional prospectus consumers."""
from datetime import datetime, timezone
import fcntl
from pathlib import Path
import shutil
import signal
import sys
import time

from scripts import prospectus_installed_optionals as base
from legalmath.prospectus.execution_authority import read, write, file_hash
from legalmath.prospectus.successor import process_ledger

ROOT = base.ROOT
HERE = ROOT / 'docs/implementation/prospectus-execution-authority/attempts/native-candidates/attempt-008'
PRIOR = HERE.parent / 'attempt-007'
EDITION = HERE.parents[1] / 'relation-discovery/attempt-005'
PLAN = 'docs/plans/prospectus-installed-editions-2026-10-15.md'
RUNNER = ROOT / 'scripts/prospectus_installed_edition_runner.py'
OLD_RUNNER = ROOT / 'scripts/prospectus_installed_optional_runner.py'
CASES = (*base.CASES, 'edition')
base.HERE, base.PRIOR, base.PLAN, base.RUNNER, base.CASES = HERE, PRIOR, PLAN, RUNNER, CASES
save = base.save


def methods():
    names = [Path(__file__), Path(base.__file__), RUNNER, OLD_RUNNER, ROOT / PLAN,
             ROOT / 'pyproject.toml', ROOT / 'src/legalmath/prospectus/programme_editions.py']
    return {str(p.relative_to(ROOT)): file_hash(p) for p in names}


base.methods = methods


def prepare():
    for prior in (PRIOR, EDITION):
        assert all(file_hash(prior / p) == h for p, h in read(prior / 'outputs.json').items())
    result = base.prepare()
    shutil.copyfile(OLD_RUNNER, base.workspace() / 'prior-runner.py')
    assert file_hash(base.workspace() / 'prior-runner.py') == file_hash(OLD_RUNNER)
    save('pre-run-audit.json', {'status': 'PASS', 'plan': PLAN,
        'baseline': str(EDITION.relative_to(ROOT)), 'prior_installed': str(PRIOR.relative_to(ROOT)),
        'primary_criterion': 'Exact complete installed outputs and all adverse controls under one wheel',
        'portability_claim': False, 'native_allowance': 0, 'http_allowance': 0,
        'historical_native_lower_bound': 77, 'historical_source_http_lower_bound': 9,
        'outer_command_limit': 10, 'planned_commands': 9, 'local_repair_limit': 1})
    return result


def compare():
    stages = ('inventory', *CASES)
    results = {s: read(HERE / 'installed-results' / s / 'result.json') for s in stages}
    assert all(r['status'] == 'PASS' and r['native_calls'] == 0 for r in results.values())
    package = base.workspace() / 'environment/lib/python3.11/site-packages/legalmath'
    expected = read(HERE / 'source-package.json')
    assert base.package_files(package) == expected
    proofs = {s: read(HERE / 'installed-results' / s / 'import-proof.json') for s in stages}
    for proof in proofs.values():
        assert proof['isolated'] == 1
        for mod in proof['modules'].values():
            p = Path(mod['path']).resolve()
            assert p.is_relative_to(package) and file_hash(p) == mod['sha256']
            assert mod['sha256'] == expected[str(p.relative_to(package))]
    ledger = process_ledger.checked(HERE / 'command-ledger.json')
    assert len(ledger['reservations']) == 9
    controls = [row for s in CASES for row in read(HERE / 'installed-results' / s / 'controls.json')]
    assert len(controls) == 18 and all(r.get('refused') or r.get('safely_unresolved') for r in controls)
    edition = results['edition']['details']
    assert edition['full_outputs_equal'] and edition['cases'] == 3 and edition['controls'] == 9
    result = {'status': 'PASS', 'installed_optional_apis': list(CASES),
        'actual_controls': 18, 'edition_cases': 3, 'outer_commands': 9, 'native_calls': 0,
        'http_calls': 0, 'exact_package_files': len(expected), 'full_outputs_match': True,
        'different_host_portability': False, 'independent_legal_acceptance': False,
        'default_changed': False, 'fresh_extraction_evaluated': False,
        'historical_visible_native_reservation_lower_bound': 77,
        'historical_visible_source_http_lower_bound': 9}
    save('comparison.json', result)
    return result


def main():
    stage = sys.argv[1]
    assert stage in {'prepare', 'build', 'install', 'inventory', *CASES, 'compare'}
    ad = base.bindings()
    folder = HERE / 'invocations' / stage
    folder.mkdir(parents=True, exist_ok=False)
    tick = time.monotonic()
    save('invocations/' + stage + '/started.json', {
        'command': ['.venv/bin/python', '-m', 'scripts.prospectus_installed_editions', stage],
        'git_commit': ad['git_commit'], 'plan': PLAN, 'environment': sys.executable,
        'started_at': datetime.now(timezone.utc).isoformat(),
        'cpu_gpu': 'CPU only;CUDA_VISIBLE_DEVICES=-1', 'random_seeds': 'N/A deterministic',
        'methods': methods()})
    def expired(signum, frame):
        raise TimeoutError('120-second installed edition stage bound; no automatic retry')
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(120)
    try:
        if stage != 'prepare':
            assert methods() == read(HERE / 'method-identities.json')
        if stage in ('inventory', *CASES):
            result = base.installed(stage)
        elif stage in ('build', 'install'):
            result = getattr(base, stage)()
        else:
            result = globals()[stage]()
        base.bindings()
        size = sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())
        size += sum(p.stat().st_size for p in base.workspace().rglob('*') if p.is_file())
        assert size < 500 * 1024 * 1024
        outcome = {'status': 'PASS', 'details': result, 'wall_seconds': time.monotonic() - tick,
                   'evidence_and_workspace_bytes': size}
    except BaseException as error:
        save('invocations/' + stage + '/result.json', {'status': 'FAIL', 'error': repr(error),
                                                     'wall_seconds': time.monotonic() - tick})
        raise
    finally:
        signal.alarm(0)
    save('invocations/' + stage + '/result.json', outcome)
    print(outcome)


if __name__ == '__main__':
    with (HERE / 'execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        main()
