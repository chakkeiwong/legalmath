"""Actual product replay through all paid phases; stop before any new admission."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from pathlib import Path
import sys
import json
import time
from copy import deepcopy
from unittest.mock import patch
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from scripts.legal_integration_master import BASE, PROGRAM, STATE
from scripts.legal_integration_synthesis_resolution import WORK, KEY, QUESTIONS, PREDECESSORS, IMPLEMENTATION
from scripts.legal_mission_execution import read, save, ref, require
from scripts.legal_integration_campaign import provider
from scripts import legal_integration_phased_live as live
from legalmath.errors import LegalMathError
from legalmath.canonical import digest
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased.downstream_input import CAPACITY_PROFILE
from legalmath.interpretation.assurance.phased import synthesis_recovery

RESULTS = WORK/'validation-2'


def run(question=None):
    began = time.monotonic()
    protected = {str(p): ref(ROOT, p) for p in (PROGRAM, STATE, BASE/'live-calls.json',
        BASE/'current-binding.json', BASE/'live-grant.json')}
    implementation = {p:ref(ROOT,p) for p in sorted(IMPLEMENTATION)}
    checkpoints = (read(ROOT/WORK/'checkpoints.json') if not question else {
        question: dict(accounts=ref(ROOT, WORK/'checkpoints'/question/'accounts.json'),
            successor=ref(ROOT, WORK/'checkpoints'/question/'successor.json'))})
    runtime = deepcopy(read(ROOT/PROGRAM))
    runtime[KEY] = dict(work=str(WORK), downstream_capacity_profile=CAPACITY_PROFILE,
        recoveries={q: row['accounts'] for q, row in checkpoints.items()},
        successors={q: row['successor'] for q, row in checkpoints.items()})
    ordinary_read, ordinary_phase = live.read, PhasedProduct.run_phase
    reports = {}

    def runtime_read(path):
        return deepcopy(runtime) if Path(path) == ROOT/PROGRAM else ordinary_read(path)

    def forbidden(*args, **kwargs):
        raise AssertionError('Provider dispatch/reservation forbidden in production replay')

    for q in ([question] if question else QUESTIONS):
        require(q in QUESTIONS, 'Unknown question')
        start = time.monotonic()
        directory = RESULTS/'production-replay'/q
        predecessor = ROOT/PREDECESSORS[q]
        service = provider()
        service.complete = service.fork = service.allowance.reserve = forbidden
        boundaries, completed = [], []
        captured = {}

        def observe_phase(product, name, calls):
            captured[name] = (product, calls)
            outcome = ordinary_phase(product, name, calls)
            if outcome['execution_complete']:
                print(json.dumps(dict(question=q, phase=name, action='retained_phase_complete',
                    results=len(outcome['results']))), flush=True)
                old = predecessor/'phases'/name/'outcome.json'
                if old.exists() and ordinary_read(old)['execution_complete']:
                    expected = {r['key']: r['result'] for r in ordinary_read(old)['results']}
                    require({r['key']: r['result'] for r in outcome['results']} == expected,
                        'Historical successful phase results changed: ' + name)
                    membership = 'reduction-' + q + '-' + name.rsplit('-', 1)[1] + '-membership.json'
                    completed.append(dict(name=name, count=len(expected), exact_results=True,
                        historical_membership=ref(ROOT, predecessor/membership)))
            return outcome

        def stop_admission(root, base, phase_directory, name, count, **kwargs):
            product, calls = captured[name]
            state = ordinary_read(product.directory/'phases'/name/'phase.json')
            require(count > 0 and count == len(state['logical_dispatches']) and not state['input_blocks'],
                'Invalid pending admission census')
            calls = product.prepare_calls(calls)
            by_key = {r['key']: r for r in calls}
            pending = state['logical_dispatches']
            wires = []
            for key in pending:
                call = by_key[key]
                wire = synthesis_recovery.replay_wire(ROOT, checkpoints[q]['successor'], key,
                    call['request'], call['schema'], product.route.input_hash, limits=product.route.limits)
                wires.append(dict(key=key, exact_historical_wire=wire is not None,
                    request_hash=digest(call['request']), measurement=product.dispatch.measure(call['request'], call['schema'])))
            boundaries.append(dict(phase=name, missing_count=count, retained_count=len(calls)-count,
                pending=wires, membership={r['key']: [x['id'] for x in r['request']['payload']]
                    for r in calls}, contract=state['contract']))
            raise LegalMathError('E_RESOURCE_LIMIT', details='Deliberate zero-call replay admission boundary')

        print(json.dumps(dict(question=q, action='replay_started')), flush=True)
        with patch.object(live, 'read', runtime_read), patch.object(live, 'admit', stop_admission), \
                patch.object(PhasedProduct, 'run_phase', observe_phase):
            result = live.product_route(q, None, service, preparation_only=True,
                recovery_context=dict(common_directory=str(directory), phase_directory=str(RESULTS/'replay-admission'/q)))
        require(len(boundaries) == 1, 'Replay did not reach exactly one missing-work boundary: ' + q)
        details = ordinary_read(ROOT/directory/'requirement-details.json')
        require(details == ordinary_read(predecessor/'requirement-details.json')
            and all(x['result']['status'] == 'VALIDATED' for x in details), 'Completed roots changed: ' + q)
        for phase in completed:
            name = phase['name']
            membership = name + '-membership.json'
            require(ordinary_read(ROOT/directory/membership) == ordinary_read(predecessor/membership),
                'Historical member hashes changed: ' + name)
            require(ordinary_read(ROOT/directory/(name+'.json')) == ordinary_read(predecessor/(name+'.json')),
                'Historical reduction population changed: ' + name)
        expected_levels = {'p10': 5, 'evidence': 4, 'p14': 0, 'gatecoin': 0}
        require(len(completed) == expected_levels[q], 'Wrong completed historical level count: ' + q)
        expected_phase = {'p10': 'reduction-p10-5', 'evidence': 'reduction-evidence-4',
            'p14': 'reduction-p14-0', 'gatecoin': 'reduction-gatecoin-1'}
        require(boundaries[0]['phase'] == expected_phase[q], 'Wrong missing-work frontier: ' + q)
        if q == 'p14': require(boundaries[0]['retained_count'] == 21, 'P14 lost successful responses')
        if q == 'gatecoin':
            adopted = ordinary_read(ROOT/directory/'phases/reduction-gatecoin-0/outcome.json')
            require(adopted['execution_complete'] and len(adopted['results']) == 117,
                'Gatecoin did not preserve 116 successes and adopt its one exact diagnostic')
        require(all(ref(ROOT, p) == evidence for p, evidence in protected.items()), 'Replay mutated live authority/state')
        require(all(ref(ROOT, p) == evidence for p, evidence in implementation.items()), 'Implementation changed during replay')
        reports[q] = dict(verdict='PASS', roots=len(details), completed=completed, boundaries=boundaries,
            details=ref(ROOT, directory/'requirement-details.json'), result=ref(ROOT, directory/'result.json'),
            provider_calls=0, wall_seconds=time.monotonic()-start, legal_acceptance=False,
            implementation=implementation, protected=protected, command=[sys.executable,*sys.argv],
            environment='.venv-context', gpu='Intentionally hidden with CUDA_VISIBLE_DEVICES=-1',
            seeds='N/A: deterministic replay', plan=ref(ROOT,'docs/plans/legal-synthesis-resolution-2026-10-19.md'),
            completion_review=ref(ROOT,WORK/'completion-review.md'))
        save(ROOT/RESULTS/('replay-'+q+'.json'), reports[q])
        print(json.dumps(dict(question=q, verdict='PASS', roots=len(details),
            completed_levels=len(completed), missing_count=boundaries[0]['missing_count'],
            wall_seconds=reports[q]['wall_seconds'])), flush=True)
    if not question:
        save(ROOT/RESULTS/'replay.json', dict(verdict='PASS', production_replay=True, provider_calls=0,
            ledger_unchanged=True, protected=protected, questions={q:ref(ROOT,RESULTS/('replay-'+q+'.json')) for q in QUESTIONS},
            wall_seconds=time.monotonic()-began, legal_acceptance=False))


if __name__ == '__main__':
    try:
        run(sys.argv[1] if len(sys.argv) > 1 else None)
    except Exception as exc:
        import traceback
        save(ROOT/RESULTS/('replay-'+(sys.argv[1] if len(sys.argv)>1 else 'all')+'-failure.json'),
            dict(verdict='FAIL',error=getattr(exc,'code',type(exc).__name__),
                reason=str(getattr(exc,'details',None) or exc),traceback=traceback.format_exc(),provider_calls=0))
        raise
