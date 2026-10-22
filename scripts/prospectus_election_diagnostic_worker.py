"""Diagnostic-only sampling and bounded profiling of the unchanged CLI worker."""
import cProfile
import faulthandler
import hashlib
import json
import os
from pathlib import Path
import pstats
import runpy
import signal
import sys
import time

root, prep, here = map(Path, sys.argv[1:4])
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path[:0] = [str(root / 'src'), str(root)]
worker = root / 'scripts/prospectus_election_consumer_worker.py'
sys.argv = [str(worker), str(root), str(prep), str(here), 'ordinary']


class DiagnosticLimit(Exception): pass


def expired(signum, frame): raise DiagnosticLimit('Recorded60second diagnostic limit')


began = time.monotonic(); cpu = time.process_time(); profiler = cProfile.Profile()
outcome = 'NOT_STARTED'; failure = None
with (here / 'stacks.log').open('x') as stacks:
    faulthandler.dump_traceback_later(10, repeat=True, file=stacks)
    signal.signal(signal.SIGALRM, expired); signal.setitimer(signal.ITIMER_REAL, 60)
    try:
        profiler.enable(); runpy.run_path(str(worker), run_name='__main__')
        outcome = 'WORKER_COMPLETED_UNDER_DIAGNOSTIC'
    except DiagnosticLimit:
        outcome = 'DIAGNOSTIC_LIMIT_REACHED'
    except BaseException as error:
        outcome = 'WORKER_ERROR'; failure = {'kind': type(error).__name__, 'error': str(error)}
    finally:
        profiler.disable(); signal.setitimer(signal.ITIMER_REAL, 0)
        faulthandler.cancel_dump_traceback_later()
        profiler.dump_stats(str(here / 'profile.pstats'))
stats = pstats.Stats(profiler)
rows = [{'file': key[0], 'line': key[1], 'function': key[2], 'primitive_calls': value[0],
         'total_calls': value[1], 'self_seconds': value[2], 'cumulative_seconds': value[3]}
        for key, value in stats.stats.items()]
imports = {n: m.__file__ for n, m in sys.modules.items()
           if (n == 'legalmath' or n.startswith('legalmath.')) and getattr(m, '__file__', None)}
assert all(Path(p).resolve().is_relative_to((root / 'src').resolve()) for p in imports.values())
result = {'outcome': outcome, 'worker_error': failure, 'wall_seconds': time.monotonic() - began,
    'cpu_seconds': time.process_time() - cpu, 'product_pass': False, 'import_origins': imports,
    'worker_sha256': hashlib.sha256(worker.read_bytes()).hexdigest(),
    'top_self': sorted(rows, key=lambda r: r['self_seconds'], reverse=True)[:30],
    'top_cumulative': sorted(rows, key=lambda r: r['cumulative_seconds'], reverse=True)[:30]}
with (here / 'profile-summary.json').open('x') as output: json.dump(result, output, indent=2)
assert (here / 'stacks.log').stat().st_size > 0, 'No sampled stacks'
print(json.dumps({'outcome': outcome, 'product_pass': False, 'wall_seconds': result['wall_seconds']}))
