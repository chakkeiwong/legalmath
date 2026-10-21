"""Zero-call production reconstruction; never installs or promotes a checkpoint."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import ast
from itertools import combinations
from pathlib import Path
import json
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.legal_integration_master import BASE, PROGRAM, TOKENIZER
from scripts.legal_integration_campaign import provider
from scripts.legal_mission_execution import read, save, ref, require, verify
from legalmath.canonical import canonical, digest
from legalmath.interpretation.assurance.bounded_context import Limits, tokenizer
from legalmath.interpretation.assurance.bounded_product import NOTE, GUIDANCE
from legalmath.interpretation.assurance import bounded_references
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased import (
    account_contract, account_encoding, account_instructions, account_input,
    account_output, downstream_instructions)
from jsonschema import validate

WORK = Path(__file__).resolve().parent
EVIDENCE = ROOT / 'artifacts/legal-mission-control/2026-10-17/gap-refresh/settled-recovery/live/common/evidence'
DIAGNOSTIC = ROOT / 'artifacts/legal-mission-control/2026-10-18/request-variants'
ORIGINALS = {
    'p14': ('2026-10-16/integration-repairs/round-7/live/common/p14/calls/reduce-p14-0-6', 3097),
    'gatecoin': ('2026-10-16/integration-repairs/round-6/live/common/gatecoin/calls/reduce-gatecoin-0-69', 3099),
}
attempted = []


def forbidden(*args, **kwargs):
    attempted.append('FORBIDDEN_PROVIDER_OR_RESERVATION')
    raise AssertionError('Zero-call diagnostic forbids completion, fork, reservation and phase admission')


def exception(exc):
    return {'error': getattr(exc, 'code', type(exc).__name__),
            'reason': str(getattr(exc, 'details', None) or exc)}


def checked(action):
    try:
        return {'passed': True, 'result': action()}
    except Exception as exc:
        return {'passed': False, **exception(exc)}


def product(qid, service, folder, program):
    return PhasedProduct(ROOT, folder / qid, service,
        read(ROOT / program['prerequisite_repair']['source']['path']), tokenizer(ROOT / TOKENIZER),
        limits=Limits(), maximum_calls=8100, maximum_corrections=1, active_questions=[qid],
        phase_admit=forbidden, phase_identity=ref(ROOT, BASE / 'current-binding.json')['sha256'],
        requirement_account_profile=account_contract.PROFILE,
        requirement_account_input_profile=account_encoding.PROFILE,
        requirement_account_instruction_profile=account_instructions.PROFILE,
        requirement_account_capacity_profile=account_input.CAPACITY_PROFILE,
        requirement_account_output_profile=account_output.PROFILE,
        downstream_input_profile=program['repair_execution']['downstream_input_profile'],
        downstream_instruction_profile=downstream_instructions.PROFILE)


def size(value, encode):
    raw = canonical(value)
    return {'bytes': len(raw), 'tokens': len(encode(raw.decode()))}


def synthesis_builder(p):
    # Read the literal from the real production method; do not invent guidance.
    source = ROOT / 'src/legalmath/interpretation/assurance/phased/product.py'
    scopes = [node.value.value for node in ast.walk(ast.parse(source.read_text()))
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str) and any(isinstance(t, ast.Subscript)
            and isinstance(t.slice, ast.Constant) and t.slice.value == 'synthesis_scope'
            for t in node.targets)]
    require(len(scopes) == 1, 'Production synthesis scope is ambiguous')
    question = next(q for q in p.route.envelope['original_questions'] if q['question_id'] == 'evidence')
    def build(rows, records=None):
        request = p.request('SYNTHESIZE_FINDINGS', question,
            p.source_records(rows) if records is None else records,
            payload=rows, expected=[r['id'] for r in rows])
        request['synthesis_scope'] = scopes[0]
        return downstream_instructions.annotate(request)
    return build


def evidence(service, folder, program, references):
    p = product('evidence', service, folder, program)
    build = synthesis_builder(p)
    inputs = {r['id']: r for r in read(EVIDENCE / 'reduction-evidence-2.json')}
    membership = read(EVIDENCE / 'reduction-evidence-3-membership.json')
    fixtures = []
    for i, ids in enumerate(membership['groups']):
        if len(ids) == 1:
            continue
        key = f'reduce-evidence-3-{i}'
        paths = [EVIDENCE / 'calls' / key / name for name in ('request.json', 'schema.json')]
        references.extend(ref(ROOT, path) for path in paths)
        saved, schema = (read(path) for path in paths)
        group = [inputs[rid] for rid in ids]
        require(all(digest(inputs[rid]) == membership['input_hashes'][rid] for rid in ids),
            'Retained synthesis membership changed')
        rebuilt = build(group)
        exact = canonical(rebuilt) == canonical(saved)
        # Reloading canonical JSON changes traversal order. Authenticate that the
        # saved records are the exact same source objects before order replay.
        require({r['id']: r for r in rebuilt['records']} == {r['id']: r for r in saved['records']},
            'Reconstructed sources differ from actual dispatched sources')
        ordered = build(group, saved['records'])
        require(canonical(ordered) == canonical(saved) and schema == NOTE,
            'Production request reconstruction differs beyond source ordering')
        fixtures.append({'key': key, 'canonical_reload_exact': exact,
            'saved_source_order_replay_exact': True, 'request_hash': digest(saved)})
    require(fixtures, 'No actual production construction fixture')
    rows = read(EVIDENCE / 'reduction-evidence-3.json')
    require(len(rows) == 4, 'Changed terminal evidence population')
    command = service.command(Path('/tmp/legalmath-provider-measure'), Path('schema.json'), Path('result.json'))
    instructions = next(x for x in command if x.startswith('developer_instructions='))
    observations = []
    for count in range(1, len(rows) + 1):
        for indices in combinations(range(len(rows)), count):
            group = [rows[i] for i in indices]
            request = build(group)
            prepared = bounded_references.prepare(request, NOTE)
            dispatch = {'request': prepared['request'], 'response_schema': prepared['schema'],
                        'product_instructions': GUIDANCE}
            visible = {'request': prepared['request'], 'response_schema': prepared['schema'],
                       'developer_instructions': instructions}
            dimensions = {'decoded': size(request, p.route.encode),
                'dispatch': size(dispatch, p.route.encode), 'provider': size(visible, p.route.encode),
                'wire_request': size(prepared['request'], p.route.encode),
                'wire_schema': size(prepared['schema'], p.route.encode),
                'local_payload': size(request['payload'], p.route.encode),
                'local_sources': size(request['records'], p.route.encode)}
            # Record the complete candidate, including rejected ones, for audit.
            save(folder / ('request-' + '-'.join(map(str, indices)) + '.json'), request)
            observations.append({'members': [r['id'] for r in group], 'indices': list(indices),
                'source_count': len(request['records']), 'measurements': dimensions,
                'actual_dispatch_measure': checked(lambda: p.dispatch.measure(request, NOTE)),
                'actual_provider_measure': checked(lambda: service.measure(prepared['request'], prepared['schema'])),
                'fits_candidate_250000_bytes_70000_tokens': all(
                    dimensions[layer]['bytes'] <= 250000 and dimensions[layer]['tokens'] <= 70000
                    for layer in ('dispatch', 'provider'))})
    return {'production_request_fixtures': fixtures, 'observations': observations,
        'active_input_bytes': p.route.limits.input_bytes,
        'active_downstream_tokens': account_input.input_token_limit(request, p.route.limits),
        'profile_candidate_is_not_active': True, 'provider_hidden_framing': 'UNMEASURED',
        'constructor_scope': 'Exact source/profile constructor; no account recovery or phase execution. '
            'Actual retained successful reduction requests authenticate the request builder.',
        'legal_acceptance': False}


def originals(service, folder, program, references):
    outcomes = {}
    for qid, (local_name, slot) in ORIGINALS.items():
        def run():
            diagnostic = DIAGNOSTIC / qid / 'original'
            manifest = read(diagnostic / 'manifest.json')
            require(manifest['global_slot'] == slot, 'Changed diagnostic slot')
            for reference in [manifest['authority'], *manifest['files'].values()]:
                verify(ROOT, reference)
                references.append(reference)
            references.append(ref(ROOT, diagnostic / 'manifest.json'))
            local = ROOT / 'artifacts/legal-mission-control' / local_name
            references.extend(ref(ROOT, local / name) for name in ('request.json', 'schema.json', 'reference-binding.json'))
            request, schema = read(local / 'request.json'), read(local / 'schema.json')
            p = product(qid, service, folder, program)
            require(request['input_hash'] == p.route.input_hash, 'Different current source population')
            prepared = bounded_references.prepare(request, schema)
            require(prepared == read(local / 'reference-binding.json'), 'Different retained production reference binding')
            require(prepared['request'] == read(diagnostic / 'request.json')
                and prepared['schema'] == read(diagnostic / 'schema.json'), 'Different exact-original wire input')
            value = read(diagnostic / 'result.json')
            validate(value, prepared['schema'])
            wire_size = size(value, p.route.encode)
            require(wire_size['bytes'] <= p.route.limits.output_bytes
                and wire_size['tokens'] <= account_output.output_token_limit(request, p.route.limits),
                'Wire output exceeds production limit')
            decoded = bounded_references.resolve(value, prepared, maximum_bytes=p.route.limits.decoded_output_bytes)
            validate(decoded, schema)
            decoded_size = size(decoded, p.route.encode)
            require(decoded_size['bytes'] <= p.route.limits.decoded_output_bytes
                and decoded_size['tokens'] <= p.route.limits.decoded_output_tokens,
                'Decoded output exceeds production limit')
            downstream_instructions.validate_correction(request, decoded)
            require(len(decoded['considered']) == len(set(decoded['considered']))
                and set(decoded['considered']) == set(request['required_considered']), 'Synthesis omitted an input')
            p.citations(decoded, request['records'])
            require(decoded['support'] or decoded['unresolved'], 'Unsupported settled synthesis')
            save(folder / (qid + '-decoded.json'), decoded)
            return {'slot': slot, 'wire_size': wire_size, 'decoded_size': decoded_size,
                'unresolved_count': len(decoded['unresolved']), 'support_count': len(decoded['support']),
                'exact_original_binding': True, 'production_decode_schema_citations': True,
                'production_checkpoint_promoted': False, 'legal_entailment_checked': False}
        outcomes[qid] = checked(run)
    return outcomes


def main():
    branch = sys.argv[1]
    require(branch in ('evidence', 'originals'), 'Unknown diagnostic')
    folder = WORK / branch
    folder.mkdir(exist_ok=False)
    began = time.monotonic()
    program = read(ROOT / PROGRAM)
    references = [ref(ROOT, path) for path in (PROGRAM, BASE / 'current-binding.json', BASE / 'live-grant.json',
        Path(__file__), ROOT / program['prerequisite_repair']['source']['path'],
        ROOT / 'src/legalmath/interpretation/assurance/phased/product.py',
        ROOT / 'src/legalmath/interpretation/assurance/bounded_product.py',
        ROOT / 'src/legalmath/interpretation/assurance/bounded_provider.py',
        ROOT / 'src/legalmath/interpretation/assurance/bounded_references.py')]
    if branch == 'evidence':
        references.extend(ref(ROOT, EVIDENCE / name) for name in (
            'reduction-evidence-2.json', 'reduction-evidence-3.json', 'reduction-evidence-3-membership.json'))
    before = len(read(ROOT / BASE / 'live-calls.json')['calls'])
    service = provider()
    service.complete = service.fork = service.allowance.reserve = forbidden
    result = checked(lambda: globals()[branch](service, folder, program, references))
    for reference in references:
        verify(ROOT, reference)
    require(not attempted, 'Forbidden provider operation attempted')
    report = {'profile': 'post-p10-offline-diagnostic.v1', 'branch': branch, **result,
        'provider_calls': 0, 'forbidden_operations_attempted': attempted,
        'references': references, 'immutable_inputs_unchanged': True,
        'shared_live_calls_before': before, 'shared_live_calls_after': len(read(ROOT / BASE / 'live-calls.json')['calls']),
        'shared_ledger_is_live': True, 'at_utc': datetime.now(timezone.utc).isoformat(),
        'wall_seconds': time.monotonic() - began, 'command': [sys.executable, str(Path(__file__).relative_to(ROOT)), branch],
        'environment': sys.executable, 'devices': 'CPU only; CUDA_VISIBLE_DEVICES=-1',
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'plan': 'docs/implementation/legal-mission-control/results/post-p10-continuation-2026-10-18.md',
        'seeds': 'N/A: deterministic reconstruction; no statistical ranking', 'legal_acceptance': False}
    save(folder / 'result.json', report)
    print(json.dumps({'branch': branch, 'passed': result['passed'], 'provider_calls': 0,
        'wall_seconds': report['wall_seconds'], **{k: v for k, v in result.items() if k in ('error', 'reason')}}), flush=True)


if __name__ == '__main__':
    main()
