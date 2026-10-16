"""Freeze the settled actual successor comparator, once, under existing locks."""
from pathlib import Path
from datetime import datetime, timezone
from contextlib import ExitStack
import fcntl
import sys
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.legal_mission_execution import read, save, ref, require
from scripts.legal_integration_master import BASE, DOC, PROGRAM, STATE, PLAN
from scripts.legal_integration_phased_live import active_live, LIVE as ORIGINAL_LIVE
from scripts.legal_integration_repair_execution import WORK
from scripts.legal_integration_complete_account_capacity import dispatch_roots
folder = WORK / 'local-refresh'
program = read(ROOT / PROGRAM)
with ExitStack() as stack:
    for name in dict.fromkeys((active_live(program) / 'supervisor.lock', ORIGINAL_LIVE / 'supervisor.lock',
            STATE.with_suffix('.run.lock'), DOC / 'mission.execution.lock', STATE.with_suffix('.lock'))):
        (ROOT / name).parent.mkdir(parents=True, exist_ok=True)
        handle = stack.enter_context((ROOT / name).open('a'))
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    require(not (ROOT / folder / 'baseline.json').exists(), 'Never overwrite frozen round')
    state, binding, ledger = (read(ROOT / p) for p in
        (STATE, BASE / 'current-binding.json', BASE / 'live-calls.json'))
    require(not any(v['status'] == 'RUNNING' for v in state['tasks'].values()), 'Unsettled owner')
    require(not state.get('mission_sync_error'), 'Mission refresh must settle before freeze')
    previous = read(ROOT / program['repair_execution']['baseline']['path'])
    roots = sorted(set(dispatch_roots(program)) | set(previous['dispatch_roots']) |
        set(program['repair_execution']['live_directories'].values()))
    dispatches = sorted({str(p.relative_to(ROOT)) for name in roots for p in (ROOT / name).rglob('dispatch.json')})
    require(set(previous['dispatch_census']) <= set(dispatches), 'Lost previous dispatch journal')
    for path in dispatches:
        require(all(v['status'] in ('VALIDATED', 'FAILED') for v in read(ROOT / path)['calls'].values()), 'Unsettled dispatch')
    paths = {r['path'] for r in binding['bindings']} | set(dispatches)
    paths |= {str(PROGRAM), str(STATE), str(PLAN), str(DOC / 'mission.json'),
        str(BASE / 'current-binding.json'), str(BASE / 'live-calls.json'), str(BASE / 'live-grant.json')}
    paths |= {str(p.relative_to(ROOT)) for p in (ROOT / 'src/legalmath').rglob('*.py')}
    paths |= {str(p.relative_to(ROOT)) for p in (ROOT / 'scripts').glob('legal_*.py')}
    paths |= {str(p.relative_to(ROOT)) for p in (ROOT / 'tests').rglob('*.py')}
    scope = Path(binding['phase_service_scope']['path'])
    paths |= {str(scope), str(scope.parent / 'service-circuit.json'), str(scope.parent / 'service-recovery.json')}
    archived = []
    for name in sorted(paths):
        target = ROOT / folder / 'before' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
        archived.append({'previous': ref(ROOT, name), 'archive': ref(ROOT, target)})
    save(ROOT / folder / 'baseline.json', {'profile': 'integration-repairs-settled-baseline.v1',
        'at_utc': datetime.now(timezone.utc).isoformat(), 'calls': len(ledger['calls']),
        'prior_detours': program['repair_execution']['prior_detours'] + 1,
        'reserved_dispatches': 0, 'running_owners': 0,
        'dispatch_roots': roots, 'dispatch_census': dispatches, 'archived': archived})
print({'frozen': str(folder), 'calls': len(ledger['calls']), 'dispatches': len(dispatches)})
