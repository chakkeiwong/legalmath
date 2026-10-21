"""Execute one measured immutable phase without reserving hypothetical descendants.

The caller retains the existing master dependency graph and its grant/binding.
This module grants no authority and makes no legal acceptance decision.
"""
from copy import deepcopy
from pathlib import Path
import json
import re
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_context import require
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.assurance.integration_contract import evidence_file, read_evidence
from .evidence_store import save_exact


def execute(product, name, calls, *, implementation_identity, admit, refresh=lambda _: None, _capacity_leaf=False):
    require(re.fullmatch(r'[a-zA-Z0-9_.-]+', name), 'Invalid phase name')
    require(implementation_identity, 'Phase requires explicit implementation binding')
    manager = getattr(product, 'capacity_manager', None)
    if manager is not None and not _capacity_leaf:
        return manager.phase(name, calls, implementation_identity=implementation_identity, admit=admit, refresh=refresh)
    if hasattr(product, 'prepare_calls'):
        calls = product.prepare_calls(calls)
    require(len(calls) == len({r['key'] for r in calls}), 'Duplicate phase call')
    product.route.check()
    directory = product.directory / 'phases' / name
    path = directory / 'phase.json'
    contract = {'profile': 'bounded-persisted-phase.v1', 'name': name,
        'input_hash': product.route.input_hash, 'implementation_identity': implementation_identity,
        'calls': [{'key': r['key'], 'identity': product.dispatch.request_identity(r['request'], r['schema'])}
                  for r in calls]}
    previous = json.loads(path.read_text()) if path.exists() else None
    if previous:
        require(previous['contract'] == contract, 'Changed phase on resume')
    dispatch_path = product.dispatch.directory / 'dispatch.json'
    dispatch = json.loads(dispatch_path.read_text()) if dispatch_path.exists() else {'calls': {}}
    for row in contract['calls']:
        old = dispatch['calls'].get(row['key'])
        if old:
            require(old['identity'] == row['identity'], 'Changed phase dispatch identity')
            require(old['status'] != 'RESERVED', 'Uncertain phase call; reconcile before any dispatch', 'E_AUTHORITY')
    if previous and previous['status'] in ('COMPLETE', 'INCOMPLETE', 'RESOURCE_BLOCKED'):
        outcome = read_evidence(previous['outcome'], product.root)
        for item in outcome.get('results', []):
            if item.get('dispatch_result_hash'):
                retained = json.loads((product.dispatch.directory / item['key'] / 'result.json').read_text())
                require(digest(retained) == item['dispatch_result_hash'], 'Retained phase call changed')
                if retained['status'] == 'VALIDATED':
                    next(r for r in calls if r['key'] == item['key'])['validate'](retained['value'])
        return deepcopy(outcome)

    measured, blocked = [], []
    for call in calls:
        try:
            measured.append({'key': call['key'],
                'measurement': product.dispatch.measure(call['request'], call['schema'])})
        except LegalMathError as exc:
            if exc.code != 'E_RESOURCE_LIMIT':
                raise
            blocked.append({'key': call['key'], 'result': product.failure(exc)})
    state = previous or {'contract': contract, 'status': 'MEASURED',
                         'measurements': measured, 'input_blocks': blocked}
    require(state['measurements'] == measured and state['input_blocks'] == blocked, 'Phase measurement changed')
    if 'logical_dispatches' not in state:
        shared_path = product.dispatch.shared_prefix
        shared_exists = shared_path is not None and (shared_path / 'dispatch.json').exists()
        require(shared_path is None or shared_exists or manager is not None,
            'Missing historical shared dispatch', 'E_INTEGRITY')
        shared = json.loads((shared_path / 'dispatch.json').read_text()) if shared_exists else {'calls': {}}
        if shared_exists:
            require(shared['input_hash'] == product.route.input_hash, 'Shared phase input changed', 'E_INTEGRITY')
        actual = []
        measured_keys = {r['key'] for r in measured}
        for row in contract['calls']:
            if row['key'] not in measured_keys:
                continue
            prior = dispatch['calls'].get(row['key'])
            if prior is None and row['key'].startswith(('read-', 'dependency-', 'detail-', 'reduce-', 'candidates-', 'criticism-')):
                prior = shared['calls'].get(row['key'])
            if prior is None:
                reused = None
                if getattr(product, 'requirement_account_recovery', None) is not None:
                    from ..bounded_checkpoint import retained_response
                    root, reference = product.dispatch.retained_initial
                    call = next(c for c in calls if c['key'] == row['key'])
                    reused = retained_response(root, reference, row['key'], call['request'],
                        call['schema'], row['identity'], product.route.input_hash,
                        limits=product.route.limits, encode=product.route.encode)
                    if reused is not None:
                        require(reused[0]['status'] == 'VALIDATED',
                            'Only validated retained phase responses avoid dispatch')
                        call['validate'](reused[0]['value'])
                if reused is None:
                    actual.append(row['key'])
            else:
                require(prior['identity'] == row['identity'], 'Shared phase request changed', 'E_INTEGRITY')
                require(prior['status'] != 'RESERVED', 'Uncertain shared phase request', 'E_AUTHORITY')
        state['logical_dispatches'] = actual
    save(path, state)
    if state['logical_dispatches']:
        try:
            # The existing live adapter adds the charged service reserve and
            # checks the original deadline. No descendant correction is included.
            # Existing admission must be activated again after another phase
            # ran. The adapter verifies and reuses its immutable reservation.
            admission = admit(name, len(state['logical_dispatches']))
            require('admission' not in state or state['admission'] == admission,
                    'Phase admission changed on resume', 'E_AUTHORITY')
            state['admission'] = admission
        except LegalMathError as exc:
            if exc.code != 'E_RESOURCE_LIMIT':
                raise
            outcome = {'phase': name, 'execution_complete': False, 'results': blocked,
                'resource_refusal': product.failure(exc), 'legal_acceptance': False}
            save_exact(directory / 'outcome.json', outcome)
            state.update(status='RESOURCE_BLOCKED', outcome=evidence_file(directory / 'outcome.json', product.root))
            save(path, state)
            refresh(outcome)
            return outcome
    state['status'] = 'RUNNING'
    save(path, state)
    results = list(blocked)
    for call in calls:
        if call['key'] in {r['key'] for r in blocked}:
            continue
        try:
            dispatch_call = getattr(product.dispatch, '_phase_original_call', product.dispatch.call)
            if _capacity_leaf:
                dispatch_call = product.dispatch._call_direct
            result = dispatch_call(call['key'], call['request'], call['schema'], call['validate'])
        except LegalMathError as exc:
            if exc.code in ('E_AUTHORITY', 'E_INTEGRITY'):
                # Preserve the running phase. A continuation veto is never
                # converted into an ordinary failed independent call.
                state['continuation_veto'] = {'status': 'FAILED', 'error': exc.code,
                    'reason': str(exc.details or exc)}
                save(path, state)
                raise
            result = product.failure(exc)
        row = {'key': call['key'], 'result': result}
        retained = product.dispatch.directory / call['key'] / 'result.json'
        if retained.exists():
            row['dispatch_result_hash'] = digest(json.loads(retained.read_text()))
        results.append(row)
        retained_row = directory / ('result-' + call['key'] + '.json')
        save_exact(retained_row, row)
        state.setdefault('partial_results', {})[call['key']] = evidence_file(retained_row, product.root)
        save(path, state)
        refresh({'phase': name, 'last_call': row, 'execution_complete': False})
    outcome = {'phase': name, 'results': results,
        'execution_complete': len(results) == len(calls) and
            all(r['result']['status'] == 'VALIDATED' for r in results),
        'legal_acceptance': False}
    save_exact(directory / 'outcome.json', outcome)
    state.update(status='COMPLETE' if outcome['execution_complete'] else 'INCOMPLETE',
                 outcome=evidence_file(directory / 'outcome.json', product.root))
    save(path, state)
    refresh(outcome)
    return outcome

