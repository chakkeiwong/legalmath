"""Durable bounded split/validate/assemble interface for the active product.

Every leaf uses the existing dispatch journal and phase admission. Service
retries belong to the provider. Only a capacity failure can trigger subdivision;
schema or semantic failure never buys another sample. An uncertain leaf is a
continuation veto. Ordinary failed pieces do not cancel independent siblings.
"""
from copy import deepcopy
import fcntl
import json
import re
import time
from jsonschema import validate
from legalmath.canonical import canonical, digest
from legalmath.errors import LegalMathError
from ..bounded_context import require
from ..monitor import save
from .evidence_store import save_exact
from . import capacity_policy as policy, capacity_adapters as adapters


class CapacityManager:
    def __init__(self, product):
        self.product = product

    def call(self, key, request, schema, validator):
        product = self.product
        if hasattr(product, 'phase_admit'):
            from .phase import execute
            outcome = execute(product, 'call-' + key, [dict(key=key, request=request,
                schema=schema, validate=validator)], implementation_identity=product.phase_identity,
                admit=product.phase_admit)
            return outcome['results'][0]['result']
        require(not getattr(product.provider, 'live', True),
            'Live common capacity requires per-leaf phase admission', 'E_AUTHORITY')
        return self.run(dict(key=key, request=request, schema=schema, validate=validator),
            lambda call: product.dispatch._call_direct(call['key'], call['request'], call['schema'], call['validate']))

    def phase(self, name, calls, *, implementation_identity, admit, refresh):
        from .phase import execute
        product = self.product
        if hasattr(product, 'prepare_calls'):
            calls = product.prepare_calls(calls)
        require(len({c['key'] for c in calls}) == len(calls), 'Duplicate capacity phase key', 'E_INTEGRITY')
        contract = dict(profile=policy.PROFILE, phase=name, implementation_identity=implementation_identity,
            calls=[dict(key=c['key'], identity=product.dispatch.request_identity(c['request'], c['schema'])) for c in calls])
        directory = product.directory / 'capacity-phases' / name
        if (directory / 'contract.json').exists():
            require(json.loads((directory / 'contract.json').read_text()) == contract,
                'Capacity phase changed on resume', 'E_INTEGRITY')
        save_exact(directory / 'contract.json', contract)
        # Check uncertain results across the whole ready set before any new
        # sibling dispatch, including a crash between leaf result and assembly.
        for call in calls:
            self.check_retained(call)
        def leaf(call):
            result = execute(product, 'capacity-' + call['key'], [call],
                implementation_identity=implementation_identity, admit=admit, refresh=refresh,
                _capacity_leaf=True)
            return result['results'][0]['result'] if result['results'] else result['resource_refusal']
        results = []
        for call in calls:
            try:
                result = self.run(call, leaf, implementation_identity=implementation_identity)
            except LegalMathError as exc:
                from .service_prerequisite import ServiceDeferred, record
                if isinstance(exc, ServiceDeferred):
                    pause = dict(phase=name, results=results, execution_complete=False,
                        service_prerequisite=record(exc))
                    save(directory / 'service-prerequisite.json', pause)
                    refresh(pause)
                    raise
                result = product.failure(exc)  # Authority/integrity errors are re-raised.
            results.append({'key': call['key'], 'result': result})
            refresh(dict(phase=name, last_call=results[-1], execution_complete=False))
        outcome = dict(phase=name, results=results, legal_acceptance=False,
            execution_complete=all(r['result']['status'] == 'VALIDATED' for r in results))
        save_exact(directory / 'outcome.json', outcome)
        refresh(outcome)
        return outcome

    def check_retained(self, call):
        path = self.product.directory / 'capacity' / call['key'] / 'state.json'
        if not path.exists():
            return
        state = json.loads(path.read_text())
        journal = self.product.dispatch.directory / 'dispatch.json'
        rows = json.loads(journal.read_text())['calls'] if journal.exists() else {}
        for key in state['leaves']:
            row = rows.get(key)
            require(row is None or row['status'] != 'RESERVED',
                'Uncertain capacity leaf: ' + key, 'E_AUTHORITY')
            if row is not None:
                folder = self.product.dispatch.directory / key
                request = json.loads((folder / 'request.json').read_text())
                schema = json.loads((folder / 'schema.json').read_text())
                require(row['identity'] == state['leaves'][key] == self.product.dispatch.request_identity(request,schema),
                    'Capacity leaf request/schema changed', 'E_INTEGRITY')
                result = json.loads((folder / 'result.json').read_text())
                require(digest(result) == row['result_hash'], 'Capacity leaf evidence changed', 'E_INTEGRITY')

    def run(self, call, execute_leaf, *, implementation_identity=None, _shared=False):
        product = self.product
        product.route.check()
        require(re.fullmatch(r'[a-zA-Z0-9_.-]+', call['key']), 'Unsafe capacity key', 'E_SCHEMA')
        call = {**call, 'request': policy.annotate(call['request'])}
        if not _shared and call['request']['task'] in (
                'GENERATE_SOURCE_WARRANTED_CANDIDATES', 'STRUCTURED_CRITICISM'):
            from .capacity_shared import execute
            return execute(self, call, lambda: self.run(call, execute_leaf,
                implementation_identity=implementation_identity, _shared=True))
        configuration = policy.contract(call['request'], product.route.limits)
        adapters.check_population(call['request'])
        contract = dict(budget=configuration, input_hash=product.route.input_hash,
            request_identity=product.dispatch.request_identity(call['request'], call['schema']),
            implementation_identity=implementation_identity or getattr(product, 'phase_identity', 'offline-common-capacity.v1'))
        directory = product.directory / 'capacity' / call['key']
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / 'capacity.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            path = directory / 'state.json'
            state = json.loads(path.read_text()) if path.exists() else dict(
                contract=contract, started=int(time.time()), status='PLANNED', leaves={}, nodes={})
            require(state['contract'] == contract, 'Capacity contract changed on resume', 'E_INTEGRITY')
            self.check_retained(call)
            from .capacity_checkpoint import retained
            imported = retained(product, call)
            if state['status'] == 'SETTLED':
                result = json.loads((directory / 'result.json').read_text())
                require(digest(result) == state['result_hash'], 'Capacity result changed', 'E_INTEGRITY')
                if result['status'] == 'VALIDATED':
                    validate(result['value'], call['schema'])
                    call['validate'](result['value'])
                return result
            save_exact(directory / 'request.json', call['request'])
            save_exact(directory / 'schema.json', call['schema'])
            save(path, state)

            def fail(reason, code='E_RESOURCE_LIMIT'):
                return dict(status='FAILED', error=code, reason=reason,
                    capacity_remainder=dict(stage=call['request']['task'], adapter=configuration['adapter'],
                        original_request_hash=digest(call['request'])))

            def node(current, depth, *, bridge=False):
                product.route.check()
                key = current['key']
                identity = product.dispatch.request_identity(current['request'], current['schema'])
                previous = state['nodes'].get(key)
                if previous:
                    require(previous['identity'] == identity, 'Changed capacity child', 'E_INTEGRITY')
                    if 'result_hash' in previous:
                        value = json.loads((directory / (key + '.json')).read_text())
                        require(digest(value) == previous['result_hash'], 'Capacity child result changed', 'E_INTEGRITY')
                        if value['status'] == 'VALIDATED':
                            validate(value['value'], current['schema'])
                            current['validate'](value['value'])
                        return value
                else:
                    state['nodes'][key] = dict(identity=identity, depth=depth, bridge=bridge)
                    save(path, state)
                def finish(value):
                    save_exact(directory / (key + '.json'), value)
                    state['nodes'][key]['result_hash'] = digest(value)
                    save(path, state)
                    return value
                if time.time() - state['started'] > configuration['maximum_seconds']:
                    return finish(fail('Common capacity elapsed-time bound exhausted'))
                try:
                    measured = False
                    measurement = product.dispatch.measure(current['request'], current['schema'])
                    require(policy.estimate(current['request']) <= configuration['output_tokens'],
                        'Estimated independent decisions exceed output budget', 'E_RESOURCE_LIMIT')
                    state['nodes'][key]['measurement'] = measurement
                    measured = True
                    if key not in state['leaves']:
                        if len(state['leaves']) >= configuration['maximum_calls']:
                            return finish(fail('Common capacity leaf-call bound exhausted'))
                        state['leaves'][key] = identity
                        save(path, state)  # Before admission or transport reservation.
                    result = execute_leaf(current)
                except LegalMathError as exc:
                    result = product.failure(exc)
                if result['status'] == 'VALIDATED' or result.get('error') != 'E_RESOURCE_LIMIT':
                    return finish(result)
                if measured and not any(marker in str(result.get('reason', '')) for marker in (
                        'output exceeds', 'Output exceeds', 'response output byte cap',
                        'Wire output exceeds', 'WIRE_OUTPUT', 'DECODED_OUTPUT')):
                    # Call/time admission, service deadlines and event-log caps
                    # are not evidence that semantic subdivision would help.
                    return finish(result)
                state['nodes'][key]['capacity_failure'] = result
                save(path, state)
                if bridge or depth >= configuration['maximum_depth']:
                    return finish(fail('Joint bridge or finite subdivision bound reached: ' + str(result['reason'])))
                children = adapters.split(product, current)
                if not children:
                    return finish(fail(configuration['reason'] + ' Complete atomic context/result does not fit. '
                        + str(result['reason'])))
                state['nodes'][key]['membership'] = [adapters.ids(c['request']) for c in children]
                save(path, state)
                # Ordinary failures do not stop independent child decisions.
                results = [node(child, depth+1) for child in children]
                if any(r['status'] != 'VALIDATED' for r in results):
                    return finish(dict(status='FAILED', error='E_DEPENDENCY',
                        reason='Capacity pieces incomplete; assembly is blocked', pieces=results))
                validation_started = False
                try:
                    assembled = adapters.merge(product, current, children, [r['value'] for r in results])
                    if configuration['adapter'] == 'source-note':
                        combined = node(assembled, depth+1, bridge=True)
                        if combined['status'] != 'VALIDATED':
                            return finish(combined)
                        value = combined['value']
                    else:
                        value = assembled
                    policy.measure_output(value, current['request'], product.route.limits,
                        product.route.encode, expanded=True)
                    validation_started = True
                    validate(value, current['schema'])
                    current['validate'](value)
                    return finish(dict(status='VALIDATED', value=value,
                        request_hash=digest(current['request']),
                        provenance=dict(capacity_profile=policy.PROFILE, assembled=True,
                            piece_hashes=[digest(r) for r in results], legal_acceptance=False)))
                except Exception as exc:
                    if validation_started and getattr(exc, 'code', None) != 'E_AUTHORITY':
                        return finish(dict(status='FAILED', error=getattr(exc, 'code', type(exc).__name__),
                            reason=str(getattr(exc, 'details', None) or exc), stage='ASSEMBLED_VALIDATION'))
                    return finish(product.failure(exc))

            from .service_prerequisite import ServiceDeferred, record
            try:
                result = imported if imported is not None else node(call, 0)
            except ServiceDeferred as exc:
                state.update(status='DEFERRED_SERVICE', service_prerequisite=record(exc))
                save(path, state)
                raise
            save_exact(directory / 'result.json', result)
            state.pop('service_prerequisite', None)
            state.update(status='SETTLED', result_hash=digest(result))
            save(path, state)
            return result

    def native(self, kind, packet, inputs):
        """Native tools consume the complete graph/candidate set, never shards."""
        require(kind in policy.NATIVE, 'Unregistered native capacity stage', 'E_AUTHORITY')
        data = canonical(dict(packet=packet, inputs=inputs))
        limits = self.product.route.limits
        require(len(data) <= limits.decoded_output_bytes and
            len(self.product.route.encode(data.decode())) <= limits.decoded_output_tokens,
            'Complete native input exceeds decoded-memory budget', 'E_RESOURCE_LIMIT')
        return dict(profile=policy.PROFILE, stage=kind, adapter='complete-native-input',
            input_hash=digest(dict(packet=packet, inputs=inputs)), bytes=len(data),
            maximum_bytes=limits.decoded_output_bytes, semantic_partition=False)
