"""Verify current P12 inputs and retained phase evidence; no provider access."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'artifacts/interpretation/round2'
sys.path.insert(0, str(ROOT / 'scripts'))
import run_interpretation_search_plan as runner
from legalmath.api.app import create_app


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    current = read(OUT / 'P12/attempt-01/run-manifest.json')
    assert current['status'] == 'PASSED'
    assert runner.inputs()['files'] == current['input_sha256']
    state = read(OUT / 'state.json')
    verified = {}
    for phase in ('P7', 'P8', 'P9', 'P10', 'P11', 'P12'):
        accepted = state['phases'][phase]['attempts'][-1]
        path = ROOT / accepted['path']
        assert accepted['status'] == 'PASSED' and sha(path) == accepted['sha256']
        manifest = read(path)
        for name, expected in manifest['artifact_sha256'].items():
            assert sha(path.parent / name) == expected, (phase, name)
        verified[phase] = {'manifest': accepted['path'], 'sha256': sha(path),
                           'artifacts_checked': len(manifest['artifact_sha256']),
                           'wall_seconds': manifest['wall_seconds'],
                           'commands': manifest['commands']}
    protection = runner.protect()
    allowance = read(OUT / 'live-allowance.json')
    replay = read(OUT / 'P12/attempt-01/replay/result.json')
    assert sha(OUT / 'live-allowance.json') == replay['allowance_sha256_unchanged']
    assert len(allowance['calls']) == 41 and allowance['maximum'] == 100
    cases = list(ET.parse(OUT / 'P12/attempt-01/tests.xml').iter('testcase'))
    assert all(len(c) == 0 for c in cases)
    tests = len(cases)
    search_tests = sum(c.get('classname', '').startswith('tests.search.') for c in cases)
    schema_path = ROOT / 'docs/specs/v0.1/openapi.json'
    schema = read(schema_path)
    with tempfile.TemporaryDirectory(prefix='legalmath-alignment-schema-') as td:
        assert create_app(td).openapi() == schema
    previous = json.loads(subprocess.check_output(
        ['git', 'show', 'HEAD:docs/specs/v0.1/openapi.json'], cwd=ROOT, text=True))
    assert all(schema['paths'].get(k) == v for k, v in previous['paths'].items())
    checked = {'checked_at': datetime.now(timezone.utc).isoformat(),
        'authority': 'ENGINEERING_EVIDENCE_ONLY', 'git_commit': current['git_commit'],
        'command': '.venv/bin/python artifacts/interpretation/round2/check_fact_alignment_evidence.py',
        'plan': 'docs/plans/interpretation-fact-alignment.md',
        'result': 'docs/implementation/interpretation-round2/fact-alignment-result.md',
        'environment': current['environment'],
        'execution_context': 'Acceptance in trusted fixed supervisor; CPU; CUDA_VISIBLE_DEVICES=-1; no GPU framework',
        'random_seeds': 'N/A: deterministic fixtures and frozen-response replay; no new stochastic generation',
        'data_version': {s['circular']: s['source_packet_hash'] for s in replay['sources']},
        'current_input_files_verified': len(current['input_sha256']),
        'frozen_baseline_files_verified': protection['frozen_files'],
        'current_source_changed_since_regression': False, 'verified_phases': verified,
        'full_tests': tests, 'search_tests': search_tests,
        'replayed_pairs': sum(s['comparisons'] for s in replay['sources']),
        'review_packets': sum(s['mismatch_review_packets'] for s in replay['sources']),
        'openapi': {'sha256': sha(schema_path), 'paths': len(schema['paths']),
                    'matches_running_app': True, 'prior_route_definitions_unchanged': True},
        'allowance': {'maximum': allowance['maximum'], 'used': len(allowance['calls']), 'new_calls': 0},
        'legal_accuracy_evaluated': False, 'release_authorized': False}
    (OUT / 'fact-alignment-evidence-check.json').write_text(json.dumps(checked, indent=2)+'\n')
    status = read(OUT / 'execution-status.json')
    status.update(engineering_tests=tests, search_tests=search_tests,
        regression_manifest=verified['P12']['manifest'], regression_manifest_sha256=verified['P12']['sha256'],
        fact_correspondence={'phase': 'P12', 'replayed_pairs': checked['replayed_pairs'],
                            'review_packets': checked['review_packets'], 'extra_automatic_matches': 0,
                            'human_mapping_reviews': 0, 'live_calls': 0,
                            'conditional_example': replay['hypothetical_24ec50_result']},
        evidence_check='artifacts/interpretation/round2/fact-alignment-evidence-check.json')
    (OUT / 'execution-status.json').write_text(json.dumps(status, indent=2)+'\n')
    print(json.dumps({k: checked[k] for k in ('full_tests', 'search_tests', 'replayed_pairs', 'review_packets',
                    'current_input_files_verified', 'frozen_baseline_files_verified', 'allowance')}, indent=2))


if __name__ == '__main__':
    main()
