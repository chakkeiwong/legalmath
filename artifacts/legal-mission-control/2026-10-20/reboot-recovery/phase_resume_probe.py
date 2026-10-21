"""Reconstruct saved Gatecoin requests locally; never call a provider."""
from pathlib import Path
from copy import deepcopy
import os
import sys
import json

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.canonical import digest
from legalmath.interpretation.assurance.bounded_context import ContextRoute, Limits, tokenizer
from legalmath.interpretation.assurance.bounded_product import BoundDispatch
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased import downstream_input, downstream_instructions
from legalmath.interpretation.assurance.phased.account_recovery import restore_record_order
from scripts.legal_integration_campaign import provider
from scripts.legal_integration_master import TOKENIZER
from scripts.legal_mission_execution import read, save, require, ref

WORK = Path(__file__).parent
SOURCE = ROOT / 'artifacts/legal-mission-control/2026-10-19/synthesis-resolution/live/gatecoin/product'
program = read(ROOT / 'docs/implementation/legal-mission-control/integration-master.json')
envelope = read(ROOT / program['prerequisite_repair']['source']['path'])
route = ContextRoute(envelope, tokenizer(ROOT / TOKENIZER), limits=Limits())
require(route.records == read(SOURCE / 'source-store.json'), 'Source records changed')
p = object.__new__(PhasedProduct)
p.root, p.directory, p.route = ROOT, WORK / 'phase-probe', route
p.downstream_input_profile = downstream_input.PROFILE
p.downstream_capacity_profile = downstream_input.CAPACITY_PROFILE
p.active_questions = ('gatecoin',)
p.dispatch = BoundDispatch(provider(), p.directory / 'calls', route, maximum_calls=8100)
rows = []
for phase_file in sorted((SOURCE / 'phases').glob('*/phase.json')):
    phase = read(phase_file)
    if phase['contract']['name'] == 'reduction-gatecoin-0':
        continue  # Its explicit historical checkpoint already restores requests.
    for call in phase['contract']['calls']:
        directory = SOURCE / 'calls' / call['key']
        if call['key'] == 'reduce-gatecoin-5-0':
            directory = WORK / 'before' / call['key']
        if not (directory / 'request.json').exists():
            continue
        original, schema = read(directory / 'request.json'), read(directory / 'schema.json')
        require(p.dispatch.request_identity(original, schema) == call['identity'], 'Saved phase identity changed')
        payload = original['payload']
        current = p.request('SYNTHESIZE_FINDINGS', original['question'], p.source_records(payload),
                            payload=payload, expected=[r['id'] for r in payload])
        for field in ('synthesis_scope', 'downstream_capacity_profile'):
            if field in original:
                current[field] = deepcopy(original[field])
        if 'downstream_instruction_profile' in original:
            current = downstream_instructions.annotate(current)
        changed = [k for k in set(original) | set(current) if original.get(k) != current.get(k)]
        fixed = restore_record_order(original, current)
        require(fixed == original, 'Restoration differs from original request')
        rows.append(dict(key=call['key'], phase=phase['contract']['name'], changed_fields=sorted(changed),
            original_identity=call['identity'], reconstructed_identity=p.dispatch.request_identity(current,schema),
            restored_identity=p.dispatch.request_identity(fixed,schema), original=ref(ROOT,directory/'request.json')))
save(WORK/'phase-resume-reproduction.json', dict(profile='debug-phase-order-reproduction.v1',
    provider_calls=0, production_files_changed=False, rows=rows,
    mismatches=sum(bool(r['changed_fields']) for r in rows),
    decision='Order restoration authenticates complete records and every other field before reusing exact requests.',
    limits='Does not reopen an owner, grant a call, prove full replay or establish legal correctness.'))
print(json.dumps({'checked':len(rows), 'mismatches':sum(bool(r['changed_fields']) for r in rows),
                  'changed_fields':sorted({k for r in rows for k in r['changed_fields']}), 'provider_calls':0}))
