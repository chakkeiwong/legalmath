#!/usr/bin/env python3
"""One user-requested Sol diagnostic: tiny JSON, then the exact failed source request."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import legal_mission_live_pilot as pilot
from legalmath.canonical import canonical, digest
from legalmath.interpretation.assurance import readable_tables, source_references
from legalmath.interpretation.assurance.semantics import validate_inventory
from legalmath.interpretation.search.models import Settings
from legalmath.interpretation.search.providers import CodexProvider
from jsonschema import Draft202012Validator

MODEL = 'gpt-6.1-sol'
OUT = pilot.OUT / 'sol-canary'
PLAN = ROOT / 'docs/plans/legal-mission-sol-canary.md'
PRIOR = pilot.OUT / 'provider-evidence/0006-54e0a372e0d886d2'
EXPECTED = {'status': 'CANARY_OK', 'echo': 'legalmath-sol-20261010'}
TINY_SCHEMA = {'type': 'object', 'additionalProperties': False,
    'properties': {k: {'type': 'string', 'enum': [v]} for k, v in EXPECTED.items()},
    'required': list(EXPECTED)}
TINY_REQUEST = {'task': 'SERVICE_CANARY', 'instructions':
    'Return exactly the expected_response object, without commentary or tools.',
    'expected_response': EXPECTED}


class CanaryAllowance(pilot.PilotAllowance):
    def stage_limit(self, stage):
        pilot.require(stage == 'core', 'Canary may only use baseline/core', 'E_AUTHORITY')
        return 8  # Six retained core calls plus at most two diagnostic calls.


class RecordedProvider(CodexProvider):
    def command(self, directory, schema, output):
        command = super().command(directory, schema, output)
        pilot.save(OUT / self.step / 'command.json', {'argv': command})
        return command


def now():
    return datetime.now(timezone.utc).isoformat()


def prepare():
    pilot.check_frozen(pilot.OUT / 'decomposed')
    allowance = CanaryAllowance('baseline')
    state = allowance.verify()
    pilot.require(state['used'] == 6 and state['stage_used']['core'] == 6,
                  'Canary requires the unchanged six-call starting point', 'E_AUTHORITY')
    pilot.require(allowance.remaining_seconds() >= 370, 'Insufficient grant time', 'E_RESOURCE_LIMIT')
    route = CodexProvider(allowance=allowance).routing
    sol_route = deepcopy(route)
    sol_route['model'] = MODEL
    paths = list((pilot.OUT / 'decomposed/baseline/product').glob(
        'revisions/*/core/actions/action-0001/transport/call-000/source-references'))
    pilot.require(len(paths) == 1, 'Ambiguous retained transport')
    transport = paths[0]
    retained = {name: pilot.read(transport / name) for name in (
        'original-request.json', 'original-schema.json', 'expanded-wire-request.json',
        'references.json', 'wire-request.json', 'wire-schema.json')}
    wire, schema = pilot.read(PRIOR / 'request.json'), pilot.read(PRIOR / 'schema.json')
    pilot.require(canonical(wire) == canonical(retained['wire-request.json']) and
                  canonical(schema) == canonical(retained['wire-schema.json']),
                  'Replay differs from the actual failed call')
    prior_manifest = pilot.read(PRIOR / 'manifest.json')
    for name in ('request.json', 'schema.json'):
        pilot.require(pilot.ref(PRIOR / name)['sha256'] ==
                      prior_manifest['files'][name]['retained_sha256'], 'Retained bytes changed')
    expanded = retained['expanded-wire-request.json']
    pilot.require(canonical(readable_tables.decode(wire, expected_request_hash=digest(expanded)))
                  == canonical(expanded), 'Readable-table round trip changed request')
    refs = retained['references.json']
    source_references.verify_table(refs, retained['original-request.json']['source_packet'],
                                   refs['request_hash'])
    settings = Settings.model_validate(pilot.read(pilot.OUT / 'decomposed/protocol.json')
                                      ['arms']['baseline']['settings']['search'])
    files = [Path(__file__), PLAN, PRIOR / 'request.json', PRIOR / 'schema.json',
             PRIOR / 'manifest.json', *[transport / n for n in retained]]
    protocol = {'model': MODEL, 'prior_route': route, 'route': sol_route,
        'remote_model_attestation': 'NOT_ESTABLISHED', 'files': [pilot.ref(p) for p in files],
        'grant_prefix': pilot.read(allowance.path), 'calls_maximum': 2,
        'deadline_utc': pilot.END, 'settings': settings.model_dump(),
        'tiny_timeout_seconds': 60, 'tiny_request': TINY_REQUEST, 'tiny_schema': TINY_SCHEMA,
        'source_request_hash': digest(wire), 'source_schema_hash': digest(schema),
        'transport': str(transport.relative_to(ROOT)), 'retries': 0,
        'authorization': "what's the problem? can you use codex gpt sol 6.1? It is working. can you try a canary test to test that?"}
    pilot.immutable(OUT / 'protocol.json', protocol)
    return allowance, protocol, retained, wire, schema, settings


def execute():
    pilot.require(not (OUT / 'run-manifest.json').exists(),
                  'A started canary cannot restart; inspect its retained evidence', 'E_AUTHORITY')
    allowance, protocol, retained, wire, schema, settings = prepare()
    began = time.monotonic()
    manifest = {'started_utc': now(), 'status': 'RUNNING',
        'command': '.venv/bin/python scripts/legal_mission_model_canary.py execute',
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'environment': str(Path(sys.executable).absolute()), 'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1',
        'random_seeds': 'N/A: provider exposes no seed; one diagnostic response per condition',
        'data_version': protocol['source_request_hash'], 'plan': pilot.ref(PLAN),
        'protocol': pilot.ref(OUT / 'protocol.json'),
        'result_file': str((OUT / 'result.json').relative_to(ROOT)),
        'result_note': 'docs/implementation/legal-mission-control/results/sol-canary.md',
        'calls_before': 6, 'deadline_utc': pilot.END}
    with (OUT / 'run-manifest.json').open('x') as stream:
        json.dump(manifest, stream, indent=2)
    provider = RecordedProvider(allowance=allowance)
    provider.routing = deepcopy(protocol['route'])
    results = []
    try:
        for name, request, output_schema, limit in (
                ('tiny-json', TINY_REQUEST, TINY_SCHEMA, 60),
                ('source-replay', wire, schema, settings.timeout_seconds)):
            provider.step = name
            pilot.require(allowance.remaining_seconds() >= limit + 5,
                          'Grant time insufficient for next canary', 'E_RESOURCE_LIMIT')
            print(json.dumps({'event': 'dispatch', 'step': name, 'model': MODEL,
                              'timeout_seconds': limit, 'used_before': allowance.verify()['used']}), flush=True)
            start = time.monotonic()
            row = {'step': name, 'model': MODEL, 'request_hash': digest(request),
                   'timeout_seconds': limit, 'input_bytes': len(canonical(request))}
            try:
                answer = provider.complete(request, output_schema,
                    settings.model_copy(update={'timeout_seconds': limit}))
                pilot.save(OUT / name / 'response.json', {'value': answer.value, 'provenance': answer.provenance})
                Draft202012Validator(output_schema).validate(answer.value)
                if name == 'tiny-json':
                    pilot.require(answer.value == EXPECTED, 'Unexpected tiny response')
                else:
                    refs = retained['references.json']
                    packet = retained['original-request.json']['source_packet']
                    resolved = source_references.resolve_response(answer.value,
                        retained['original-schema.json'], output_schema, refs, packet, refs['request_hash'])
                    inventory = validate_inventory(resolved, packet)
                    pilot.save(OUT / name / 'validated-inventory.json', inventory)
                    row.update({'claims': len(inventory['claims']), 'units': len(inventory['units']),
                                'semantic_support': 'NOT_ESTABLISHED'})
                row.update({'status': 'PASS', 'slot': answer.provenance['allowance_slot'],
                            'usage': answer.provenance['usage']})
            except Exception as exc:
                row.update({'status': 'FAIL', 'error': getattr(exc, 'code', type(exc).__name__),
                            'details': getattr(exc, 'details', str(exc))})
            row['wall_milliseconds'] = round((time.monotonic() - start) * 1000)
            results.append(row)
            pilot.save(OUT / name / 'result.json', row)
            print(json.dumps({k: v for k, v in row.items() if k not in ('details', 'usage')}), flush=True)
            if row['status'] != 'PASS':
                break
        result = {'status': 'PASS' if len(results) == 2 and all(r['status'] == 'PASS' for r in results)
                  else 'DIAGNOSTIC_FAILED', 'model': MODEL, 'steps': results,
                  'calls_used': allowance.verify()['used'], 'legal_progress': 'NOT_ESTABLISHED',
                  'full_integration': 'NOT_ESTABLISHED', 'remote_model_attestation': 'NOT_ESTABLISHED'}
        pilot.save(OUT / 'result.json', result)
    finally:
        manifest.update({'finished_utc': now(), 'wall_seconds': round(time.monotonic() - began, 3),
                         'calls_after': allowance.verify()['used'],
                         'status': pilot.read(OUT / 'result.json')['status']
                         if (OUT / 'result.json').exists() else 'INTERRUPTED_OR_ERROR'})
        pilot.save(OUT / 'run-manifest.json', manifest)
    return {'status': result['status'], 'model': MODEL, 'calls_used': result['calls_used'],
            'evidence': str(OUT.relative_to(ROOT))}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check', 'execute'])
    args = parser.parse_args()
    if args.action == 'check':
        prepare()
        print(json.dumps({'status': 'READY', 'model': MODEL, 'maximum_new_calls': 2}))
    else:
        print(json.dumps(execute()))
