"""Share exact completed candidate/criticism work among matched tool arms.

The lock covers lookup, dispatch and publication. Failures remain shared too:
an ordinary later arm cannot resample a failed common interpretation.
"""
import fcntl
import json
from pathlib import Path
from jsonschema import validate
from legalmath.canonical import digest
from ..bounded_context import require
from ..integration_contract import evidence_file, read_evidence
from .evidence_store import save_exact
from .capacity_policy import contract


def execute(manager, call, run):
    product, dispatch = manager.product, manager.product.dispatch
    shared = (dispatch.shared_prefix or dispatch.directory) / 'capacity-shared'
    shared.mkdir(parents=True, exist_ok=True)
    path = shared / (call['key'] + '.json')
    identity = dispatch.request_identity(call['request'], call['schema'])
    budget = contract(call['request'], product.route.limits)
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if path.exists():
            row = json.loads(path.read_text())
            require(row['identity'] == identity and row['input_hash'] == product.route.input_hash,
                'Changed common tool capacity context', 'E_INTEGRITY')
            require(row['budget'] == budget, 'Changed shared capacity policy', 'E_INTEGRITY')
            if row['status'] == 'SETTLED':
                for pointer in row['evidence']:
                    read_evidence(pointer, product.root, json_value=False)
                # Preserve the source checkpoint's integrity, including an imported
                # output that originally failed only the size screen.
                if product.capacity_checkpoint is not None:
                    from .capacity_checkpoint import retained
                    retained(product, call)
                value = read_evidence(row['result'], product.root)
                if value['status'] == 'VALIDATED':
                    validate(value['value'], call['schema'])
                    call['validate'](value['value'])
                return value
            require(row['status'] == 'RUNNING' and row['owner'] == str(product.directory),
                'Common interpretation interrupted in another arm; reconcile its dispatch before reuse', 'E_AUTHORITY')
        # Publication can be interrupted after transport settles. Only the same
        # owner may resume its durable journal; another arm may never resample.
        save_exact(path, dict(profile='shared-common-capacity.v1', status='RUNNING',
            identity=identity, input_hash=product.route.input_hash, budget=budget, owner=str(product.directory)))
        value = run()
        folder = product.directory/'capacity'/call['key']
        state = json.loads((folder/'state.json').read_text())
        evidence = [evidence_file(folder/name, product.root) for name in ('state.json','request.json','schema.json')]
        for key in state['leaves']:
            for name in ('request.json','schema.json','result.json'):
                source = dispatch.directory/key/name
                if source.exists():
                    evidence.append(evidence_file(source, product.root))
        result = evidence_file(folder/'result.json', product.root)
        save_exact(path, dict(profile='shared-common-capacity.v1', status='SETTLED', identity=identity,
            input_hash=product.route.input_hash, budget=budget, result=result, evidence=evidence))
        return value
