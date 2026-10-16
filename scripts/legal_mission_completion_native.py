#!/usr/bin/env python3
"""Installed engines on retained source-warrant controls; no model calls."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from pathlib import Path
from datetime import datetime, timezone
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.legal_mission_completion import check, BASE
from scripts.legal_independent_tools import IndependentProductToolBackend
from legalmath.interpretation.assurance.arguments import evaluate_criticism
from legalmath.interpretation.assurance.optional_tools import adapter_results
from legalmath.canonical import digest


def main():
    check(active=True)
    source = ROOT / 'artifacts/legal-mission-control/2026-10-09/continuation/product-contribution/reviewed/prepared.json'
    prepared = json.loads(source.read_text())
    out = BASE / ('native-' + datetime.now(timezone.utc).strftime('%H%M%S%f'))
    out.mkdir()
    packet = prepared['packet']; candidates = prepared['candidates']
    results = {}
    for tool in sorted(IndependentProductToolBackend.TOOL_IDS):
        backend = IndependentProductToolBackend([tool])
        try:
            if tool == 'bm25':
                result = [backend.retrieval(packet, {'question': q}, out / tool / qid)
                          for qid, q in prepared['questions'].items()]
            elif tool in ('legalruleml', 'logical-english'):
                result = backend.candidates(packet, candidates, out / tool)
            else:
                result = {}
                for name in ('questioned', 'assumed', 'false-supported', 'undercut'):
                    proposal = prepared['proposals'][name]
                    evaluation = evaluate_criticism(proposal, packet, list(candidates))
                    result[name] = backend.criticism(packet, {'proposal': proposal, 'evaluation': evaluation}, out / tool / name)
            results[tool] = {'status': 'EXECUTED', 'result': result, 'identity': backend.identity()}
        except Exception as exc:
            results[tool] = {'status': 'FAILED', 'error': type(exc).__name__, 'reason': str(exc)}
        (out / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    summary = {'source': str(source.relative_to(ROOT)), 'source_hash': digest(prepared),
        'output': str(out.relative_to(ROOT)), 'results': results, 'provider_calls': 0,
        'cpu_only': True, 'legal_warrant_discovered_by_tools': False,
        'scope': 'Retained conditional/checklist and supplied counterexample; no new model answer.'}
    (BASE / 'native-result.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({k: v['status'] for k, v in results.items()}, indent=2))
    return int(any(v['status'] == 'FAILED' for v in results.values()))


if __name__ == '__main__':
    sys.exit(main())
