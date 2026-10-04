#!/usr/bin/env python3
"""Freeze a whole-method window from the tested snapshot; issue no model calls."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

SNAPSHOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SNAPSHOT/'src')]


def freeze(workspace):
    from legalmath.canonical import canonical, digest, raw_digest
    from legalmath.interpretation.assurance import investigation_observations as observations
    from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation
    from legalmath.interpretation.assurance.diversity import save
    from legalmath.interpretation.assurance.grants import GrantSlice
    from legalmath.interpretation.assurance.executable_references_v2 import PROTOCOL
    from legalmath.interpretation.search.providers import CodexProvider

    root = Path(workspace).resolve()
    out = root/'artifacts/assurance-new-grant/2026-09-29'
    state = json.loads((out/'state.json').read_text())
    receipt = state['phases']['F4'][-1]
    manifest = root/receipt['path']
    if raw_digest(manifest.read_bytes()) != receipt['sha256']:
        raise RuntimeError('Changed final verification receipt')
    verified = json.loads(manifest.read_text())
    if verified['status'] != 'PASSED' or Path(verified['result']['snapshot']) != SNAPSHOT:
        raise RuntimeError('Use the successfully tested snapshot to freeze the method')
    snapshot = json.loads((manifest.parent/'snapshot.json').read_text())
    for name, expected in snapshot['inputs'].items():
        if raw_digest((SNAPSHOT/name).read_bytes()) != expected:
            raise RuntimeError('Tested snapshot changed: '+name)
    allowance = GrantSlice(out/'grant.json', out/'future-pilot-allowance.json', 120)
    before = allowance.verify()
    at = datetime.now(timezone.utc)
    # This is a research configuration, not a claim of sufficient search depth.
    # Its pilot has one fixed arm; another path must not create another arm.
    provider = CodexProvider(allowance=allowance)
    toolchain = {'compiler': SNAPSHOT/'.localresources/catala-toolchain/opam-root/catala-clean-1.2.1/bin/catala',
        'upstream': SNAPSHOT/'.localresources/catala-toolchain/catala-0f895e048d19dbe72f24cdd6d5f3398bfe1335fa',
        'lock': SNAPSHOT/'docs/implementation/catala/toolchain-lock.json'}
    runner = CompleteInvestigation(root, out/'future-pilot/investigation', provider,
        SNAPSHOT/'.localresources/java-toolchain/jdk-17.0.20.1+1',
        at.isoformat().replace('+00:00', 'Z'), catala=toolchain,
        maximum_scoped_actions=48, scoped_rounds=2, scoped_batch_size=12,
        scoped_schedule='round-first', reference_protocol=PROTOCOL, machine_qualification=True)
    # The source freeze is an explicit, bounded list of encountered development
    # bytes, not a claim to enumerate every public or private document ever seen.
    development = set(); source_receipts = []
    old = root/'artifacts/assurance-successor/2026-09-28/study-source-freeze.json'
    previous = json.loads(old.read_text())
    for task in previous['tasks']:
        context = task.get('context', {})
        for document in context.get('documents', []): development.add(document['raw_sha256'])
    # Raw archived inputs give the actual identity even when an older task did
    # not preserve a context in the study selection record.
    for name in ('examples/integrated-assurance/sources', 'examples/second-circular-23ec46',
                 'examples/multi-circular-2026/source-text',
                 'artifacts/assurance-successor/2026-09-28/source-inputs',
                 'artifacts/authority-source-revision/2026-09-29/attempt-01/sources'):
        for path in sorted((root/name).rglob('*')):
            if path.is_file() and path.suffix.lower() in ('.pdf', '.html', '.htm', '.bin', '.txt', '.json'):
                value = raw_digest(path.read_bytes()); development.add(value)
                source_receipts.append({'path': str(path.relative_to(root)), 'sha256': value})
    for task in previous['tasks']:
        for document in task.get('sources', []):
            path = root/document['path']
            if raw_digest(path.read_bytes()) != document['sha256']:
                raise RuntimeError('Development source changed')
            development.add(document['sha256']); source_receipts.append(document)
    if not development: raise RuntimeError('No development source identities were recovered')
    window = out/'whole-method-window'
    config = {'verification': receipt, 'tested_snapshot': str(SNAPSHOT),
        'method_configuration': observations.method(runner), 'at': runner.at,
        'source_families': ['SFC_PUBLIC_CIRCULAR'], 'window_days': 30,
        'duration_status': 'Convenience bound; no statistical power claim',
        'pilot_allowance_path': str(allowance.slice_path), 'pilot_maximum': 120,
        'development_source_receipts': source_receipts,
        'development_registry_qualification': 'Explicit retained research sources; completeness of every source previously encountered anywhere is not established.',
        'inventory_completeness': 'NOT_ESTABLISHED',
        'execution_policy': 'Admit a genuinely later source before any source or interpretation stage. Retain failures and incomplete tasks. This freeze does not schedule or dispatch a model request.'}
    if window.exists():
        spec = json.loads((window/'freeze.json').read_text())
        bound = observations.frozen_method(window, spec['window_hash'])
        if canonical(bound) != canonical(config['method_configuration']):
            raise RuntimeError('An existing window cannot be overwritten or reset')
    else:
        spec = observations.freeze(window, runner, config['source_families'],
            ends_at=(at+timedelta(days=30)).isoformat().replace('+00:00', 'Z'),
            development_sources=development)
        save(window/'execution-configuration.json', config)
    report = observations.report(window, spec['window_hash'])
    if allowance.verify() != before: raise RuntimeError('Freeze unexpectedly spent a model call')
    save(out/'future-window-result.json', {'status': 'WHOLE_METHOD_FROZEN_NO_OBSERVATIONS',
        'window': str(window.relative_to(root)), 'window_hash': spec['window_hash'],
        'method_hash': spec['method_hash'], 'starts_at': spec['starts_at'], 'ends_at': spec['ends_at'],
        'development_sources': len(spec['development_sources']), 'report': report,
        'live_calls': 0, 'grant': before, 'verification': receipt})
    return {'status': 'WHOLE_METHOD_FROZEN_NO_OBSERVATIONS', 'window_hash': spec['window_hash'],
            'development_sources': len(spec['development_sources']), 'live_calls': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--workspace', required=True)
    print(json.dumps(freeze(parser.parse_args().workspace)))
