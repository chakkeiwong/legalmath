#!/usr/bin/env python3
"""Fixed offline actions for the admitted integration attempt; no live dispatch."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.monitor import save
from scripts.legal_mission_control import admit, read, BASE, INTEGRATION_TASK

OUT = ROOT / 'artifacts/legal-mission-control/2026-10-10/tool-integration'

def admission():
    return admit(read(ROOT / BASE / 'mission.json'), read(ROOT / BASE / 'tools.json'), INTEGRATION_TASK, ROOT)

def reproduce(work):
    from legalmath.interpretation.search.providers import CodexProvider
    from legalmath.interpretation.assurance.source_context import ContextProvider
    from legalmath.interpretation.assurance.scoped_investigation import investigate
    from tests.assurance.test_source_context import preparation
    from tests.assurance.test_integration import source
    from tests.assurance.test_successor_grants import grant
    allowance, _ = grant(work)
    class Blocked(CodexProvider):
        def __init__(self): self.allowance = allowance; self.routing = {'fixture': True}
        def complete(self, *args): raise AssertionError('No service dispatch permitted')
    context, packet = preparation(ROOT, work / 'source', [source()])
    provider = ContextProvider(Blocked(), context, ROOT)
    try:
        investigate(packet, [], {}, {}, provider, work / 'scoped')
    except LegalMathError as exc:
        if exc.code != 'E_AUTHORITY': raise
        return {'status': 'REPRODUCED', 'error': exc.code, 'details': exc.details,
                'verified_underlying_grant': allowance.verify(), 'new_live_calls': 0,
                'limit': 'Qualified wrapper rejected before transport; fixture grant only.'}
    raise AssertionError('Expected pre-repair qualified-provider rejection')

def qualify(work):
    from scripts.legal_mission_integration_checks import qualify
    return qualify(work, admission)

def capacity(work):
    from scripts.legal_mission_integration_checks import capacity
    return capacity(work, admission)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('reproduce', 'qualify', 'capacity'))
    parser.add_argument('--correction', type=int, choices=(1, 2, 3), default=0,
                        help='Retain a bounded correction within this same attempt; no old result overwritten')
    args = parser.parse_args()
    state = admission()
    work = OUT / (args.action + ('-correction-' + str(args.correction) if args.correction else ''))
    work.mkdir(parents=True, exist_ok=False)
    save(work / 'admission.json', state)
    started = time.monotonic()
    try:
        result = globals()[args.action](work)
        code = 0
    except Exception as exc:
        result = {'status': 'FAILED', 'error': getattr(exc, 'code', type(exc).__name__),
                  'details': getattr(exc, 'details', str(exc)), 'new_live_calls': 0}
        code = 1
    result['wall_milliseconds'] = int(1000 * (time.monotonic() - started))
    result['command'] = '.venv/bin/python scripts/legal_mission_tool_integration.py ' + args.action
    if args.correction: result['command'] += ' --correction ' + str(args.correction)
    result['legal_quality_evaluated'] = False
    save(work / 'result.json', result)
    print(json.dumps(result, indent=2))
    return code

if __name__ == '__main__': sys.exit(main())
