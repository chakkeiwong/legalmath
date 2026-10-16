#!/usr/bin/env python3
"""Fixed source-linked local controls; never dispatches a language model."""
import json
import os
from copy import deepcopy
from pathlib import Path
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from legalmath.canonical import digest, raw_digest
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.assurance.optional_tools import ToolSession
from scripts.legal_integration_tools import ProductToolBackend
from scripts.legal_mission_logical_english import check, conditional_values
from scripts.legal_mission_tool_integration import admission, OUT


def execute(work):
    historical = ROOT / 'artifacts/legal-integration-coverage/2026-10-08/inputs.json'
    packet_path = ROOT / 'artifacts/legal-mission-control/2026-10-09/answer-preparation/source/packet.json'
    assert raw_digest(historical.read_bytes()) == '6aeeb1712cfc103e12174facf44ca367c247c700cbb8c1c4a75fcb5f130c8caf'
    assert raw_digest(packet_path.read_bytes()) == '7f7c3b113825f53c5b87d3a3cc9bebc13ab033baea5d9298998cb1df3ae82a62'
    old = json.loads(historical.read_bytes()); packet = json.loads(packet_path.read_bytes())
    mapping = {}
    for unit in old['packet']['units']:
        matches = [u for u in packet['units'] if unit['text'] in u['text']]
        assert len(matches) == 1, unit['unit_id']
        target = matches[0]; start = target['text'].index(unit['text'])
        mapping[unit['unit_id']] = {'unit_id': target['unit_id'], 'start': start,
            'end': start + len(unit['text']), 'old_unit_hash': digest(unit),
            'full_unit_hash': digest(target), 'exact_text_hash': digest(unit['text'])}
    candidates = deepcopy(old['candidates'])
    for reading in candidates.values():
        for quote in reading['citations']: quote['unit_id'] = mapping[quote['unit_id']]['unit_id']
        if reading['formalization']:
            for fact in reading['formalization']['facts']:
                fact['source_unit_ids'] = [mapping[i]['unit_id'] for i in fact['source_unit_ids']]
    save(work / 'inputs.json', {'packet': packet, 'candidates': candidates})
    save(work / 'source-mapping.json', {'historical': evidence_file(historical, ROOT),
        'full_packet': evidence_file(packet_path, ROOT), 'mapping': mapping,
        'limit': 'Exact-source remapping only; historical proposals, not new full-target generation.'})
    session = ToolSession(ProductToolBackend(['logical-english']), work / 'product-tools')
    result = session.candidates(packet, candidates)
    assert result['status'] == 'PASS', result
    assert len(result['readings']) == 12
    assert sum(r['status'] == 'PASS' for r in result['readings']) == 6
    assert sum(r['status'] == 'UNSUPPORTED' and r['reason'] == 'UNFORMALIZED'
               for r in result['readings']) == 6
    cases = []
    for row in result['readings']:
        if row['status'] != 'PASS': continue
        reading = candidates[row['candidate_id']]; formal = reading['formalization']
        table = json.loads((ROOT / row['conditional_values']['path']).read_bytes())
        assert len(formal['facts']) == 2
        provider = next(f['name'] for f in formal['facts'] if 'provider' in f['name'])
        request = next(f['name'] for f in formal['facts'] if 'request' in f['name'])
        known_provider = {provider: True}
        values = {'unknown_request': conditional_values(table, known_provider),
            'no_request': conditional_values(table, {**known_provider, request: False}),
            'requested': conditional_values(table, {**known_provider, request: True}),
            'unknown_scope': conditional_values(table, {request: False})}
        standing = formal['result'] == 'true'
        assert values['unknown_request']['result'] == (True if standing else 'UNKNOWN')
        assert values['no_request']['result'] == standing
        assert values['requested']['result'] is True
        assert values['unknown_scope']['scope'] == 'UNKNOWN'
        cases.append({'candidate_id': row['candidate_id'], 'local_id': reading['local_id'],
            'standing_trigger_proposal': standing, 'values': values,
            'limit': 'Duty activation only. No fulfillment or legal preference established.'})
    questions = json.loads((ROOT / 'artifacts/legal-tool-comparison/2026-10-06/T0/attempt-1/questions.json').read_bytes())
    question = next(q['question'] for q in questions if q['id'] == 'p14')
    delivered = session.augment({'task': 'CHECK_RETAINED_P14_TOOL_DELIVERY',
        'source_packet': packet, 'candidates': candidates, 'question': question})
    assert delivered['question'] == question
    assert any(c['kind'] == 'candidates' and len(c.get('readings', [])) == 12
               for c in delivered['external_tool_context']['checks'])
    save(work / 'delivered.json', delivered); save(work / 'conditional-cases.json', cases)
    original = next(v for v in candidates.values() if v['formalization'])
    negative = {}
    for fault in ('quote', 'foreign_fact_source', 'non_boolean', 'too_many_facts'):
        admission(); bad = deepcopy(original)
        if fault == 'quote': bad['citations'][0]['quote'] += ' INVENTED'
        if fault == 'foreign_fact_source': bad['formalization']['facts'][0]['source_unit_ids'] = ['foreign.unit']
        if fault == 'non_boolean': bad['formalization']['result_type'] = 'integer'
        if fault == 'too_many_facts':
            bad['formalization']['facts'] = [dict(deepcopy(bad['formalization']['facts'][0]), name='f'+str(i)) for i in range(9)]
        checked = check(packet, {'negative': bad}, work / 'negative' / fault)
        assert checked['status'] == 'UNSUPPORTED', checked
        negative[fault] = checked
    for tool in ('pyarg', 'carneades', 'clingo'):
        workdir = work / 'negative' / ('oversized-' + tool)
        checked = ProductToolBackend([tool]).criticism(packet, {
            'proposal': {'arguments': [{'argument_id': 'a'+str(i)} for i in range(13)]},
            'evaluation': {'semantics': {}, 'blocked_arguments': [], 'defeats': []}}, workdir)
        assert checked['status'] == 'UNSUPPORTED' and checked['reason'] == 'GRAPH_PROFILE_CAPACITY'
        assert not workdir.exists(), 'Unsupported graph dispatched an engine'
        negative['oversized_' + tool] = checked
    save(work / 'negative-controls.json', negative)
    return {'status': 'CONTROLLED_SOURCE_APPLICABILITY_PASS',
        'retained_readings': 12, 'formalized_trigger_proposals': 6,
        'unformalized_fulfillment_proposals': 6, 'negative_controls': list(negative),
        'conditional_cases': evidence_file(work / 'conditional-cases.json', ROOT),
        'downstream_delivery': evidence_file(work / 'delivered.json', ROOT),
        'new_live_calls': 0, 'source_warrant_evaluated': False,
        'legal_quality_evaluated': False,
        'limit': 'Controlled preservation/applicability, not complete answer contribution or legal resolution.'}


def main():
    admitted = admission(); work = OUT / 'source-controls'
    work.mkdir(parents=True, exist_ok=False); save(work / 'admission.json', admitted)
    started = time.monotonic()
    try: result = execute(work); code = 0
    except Exception as exc:
        result = {'status': 'FAILED', 'error': getattr(exc, 'code', type(exc).__name__),
            'details': getattr(exc, 'details', str(exc)), 'new_live_calls': 0}; code = 1
    result.update(command='.venv/bin/python scripts/legal_mission_integration_controls.py',
                  wall_milliseconds=int(1000 * (time.monotonic() - started)))
    save(work / 'result.json', result); print(json.dumps(result, indent=2)); return code


if __name__ == '__main__': sys.exit(main())
