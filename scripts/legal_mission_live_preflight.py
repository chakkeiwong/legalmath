#!/usr/bin/env python3
"""Freeze the concrete pilot specification locally; no live dispatch or grant."""
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from legalmath.canonical import digest, raw_digest
from legalmath.interpretation.search.providers import CodexProvider
from legalmath.interpretation.assurance import source_context
from legalmath.interpretation.assurance.sources import acquire_context, packet_from_context
from legalmath.interpretation.assurance.investigation_answer import question_text
from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation
from legalmath.interpretation.assurance.investigation_observations import method
from legalmath.interpretation.assurance.integration_contract import evidence_file, read_evidence
from legalmath.interpretation.assurance.monitor import save
from scripts.legal_integration_tools import ProductToolBackend
from scripts.legal_mission_tool_integration import admission, OUT


def execute(work):
    source = ROOT / 'artifacts/legal-mission-control/2026-10-09/answer-preparation/source'
    qualification = json.loads((source / 'qualification.json').read_bytes())
    for ref in qualification['evidence']: read_evidence(ref, ROOT, json_value=False)
    old_context = json.loads((source / 'context.json').read_bytes())
    roots = [{'url': d['url'], 'media_type': d['media_type'], 'data': d['text'].encode(),
              'selection': d['selection']} for d in old_context['documents']]
    def no_network(_): raise AssertionError('Offline preflight attempted acquisition')
    actual_context = acquire_context(roots, fetcher=no_network, max_documents=4, max_depth=0)
    questions = json.loads((source / 'questions.json').read_bytes())
    original_questions = json.loads((ROOT / 'artifacts/legal-tool-comparison/2026-10-06/T0/attempt-1/questions.json').read_bytes())
    assert questions == [{'question_id': q['id'], 'text': q['question']}
                         for q in original_questions if q['id'] in ('p10', 'evidence')]
    packet = packet_from_context(actual_context, question_text(questions))
    assert packet == json.loads((source / 'packet.json').read_bytes())
    assert digest(packet) == qualification['source_packet_hash']
    qualified = source_context.prepare(ROOT, roots, packet, qualification)
    save(work / 'qualified-source-context.json', qualified)
    provider = CodexProvider(allowance=None)  # Constructor reads route only; no .complete call exists here.
    service = urlsplit(provider.routing['fields'].get('base_url', ''))
    assert not (service.username or service.password or service.query), 'Route contains nonpublic fields'
    arms = {}
    for arm in ('baseline', 'candidate'):
        runner = CompleteInvestigation(ROOT, work / 'proposed-execution' / arm,
            provider, ROOT / '.localresources/java-toolchain/jdk-17.0.20.1+1', '2026-10-10T00:00:00Z',
            maximum_scoped_actions=82, scoped_rounds=1, scoped_batch_size=12,
            optional_tool_backend=ProductToolBackend(sorted(ProductToolBackend.TOOL_IDS)) if arm == 'candidate' else None)
        runner.settings = runner.settings.model_copy(update={'max_documents': 4, 'max_reference_depth': 0})
        arms[arm] = method(runner)
    base = dict(arms['baseline']); candidate = dict(arms['candidate'])
    base.pop('optional_tools'); candidate.pop('optional_tools')
    assert base == candidate, 'Unmatched pilot methods'
    historical_ledger = ROOT / 'artifacts/legal-integration-coverage/2026-10-08/additional-200-calls-100-repairs/allowance.json'
    historical_grant = historical_ledger.parent / 'authorization.json'
    prior = json.loads(historical_ledger.read_bytes())
    grant = json.loads(historical_grant.read_bytes())
    assert prior['maximum'] == 200 and len(prior['calls']) == 49
    assert time.time() > grant['deadline_epoch']
    stages = {'core': 36, 'question_assignment': 3, 'scoped': 82,
              'challenge_panel': 0, 'dossier_reviews': 64, 'interaction': 1, 'synthesis': 1}
    per_arm = sum(stages.values()); global_calls = 2 * per_arm + 1
    assert per_arm == 187 and global_calls == 375
    specification = {'status': 'LIVE_NOT_READY', 'authorized_live_calls': 0,
        'proposal_is_not_grant': True, 'questions': questions,
        'source_packet': evidence_file(source / 'packet.json', ROOT),
        'source_qualification': evidence_file(source / 'qualification.json', ROOT),
        'source_context': evidence_file(work / 'qualified-source-context.json', ROOT),
        'source_inputs': source_context.input_identity(roots),
        'route': provider.routing, 'route_hash': digest(provider.routing), 'arms': arms,
        'arm_order': ['baseline', 'candidate'], 'same_model_dependence': 'UNMEASURED',
        'proposed_stage_ceiling_per_arm': stages, 'proposed_call_ceiling_per_arm': per_arm,
        'optional_assessment_calls': 1, 'proposed_global_call_ceiling': global_calls,
        'proposed_duration_hours': 36, 'actual_started_utc': None, 'actual_deadline_utc': None,
        'output_policy': {'input_bytes': 200000, 'general_output_bytes': 200000,
            'review_output_ceiling_bytes': 4000, 'minimum_reasoning_bytes_per_group': 1000,
            'interaction_output_ceiling_bytes': 8000, 'extra_dependency_bytes': 12000,
            'review_limits': 'Allocated from exact fresh dossier by capacity_budget before dispatch'},
        'historical_resources': {'authorization': evidence_file(historical_grant, ROOT),
            'ledger': evidence_file(historical_ledger, ROOT), 'used_calls': 49,
            'expired_unused_calls': 151, 'transfer_authorized': False},
        'money': {'service_prices': None, 'currency': None, 'ceiling': None,
            'service_enforcement': None, 'token_limits': None,
            'byte_limit_is_monetary_limit': False},
        'blockers': ['No fresh explicit live grant/deadline',
            'Generic grant incompatible with latest expired specialized predecessor',
            'Actual service billing, token limits and enforced spending ceiling missing'],
        'dynamic_admission': ['Generated pair count must fit the declared scoped envelope',
            'Whole genuine dossier must pass partition and aggregate budget before reviews',
            'Both complete answers required; no source/reading/pair pruning or silent renewals'],
        'claim_limit': 'One descriptive P10/evidence pair; no superiority, legal closure or full six-tool evaluation.',
        'new_live_calls': 0}
    save(work / 'pilot-specification.json', specification)
    return {'status': specification['status'], 'proposed_global_calls': global_calls,
        'proposed_calls_per_arm': per_arm, 'packet_units': len(packet['units']),
        'source_reconstructed': True, 'methods_match_except_backend': True,
        'specification': evidence_file(work / 'pilot-specification.json', ROOT),
        'blockers': specification['blockers'], 'new_live_calls': 0,
        'fee_bearing_provider_probe': False}


def main():
    state = admission(); work = OUT / 'live-preflight'
    work.mkdir(parents=True, exist_ok=False); save(work / 'admission.json', state)
    started = time.monotonic()
    try: result = execute(work); code = 0
    except Exception as exc:
        result = {'status': 'FAILED', 'error': getattr(exc, 'code', type(exc).__name__),
            'details': getattr(exc, 'details', str(exc)), 'new_live_calls': 0}; code = 1
    result.update(command='.venv/bin/python scripts/legal_mission_live_preflight.py',
                  wall_milliseconds=int(1000 * (time.monotonic() - started)))
    save(work / 'result.json', result); print(json.dumps(result, indent=2)); return code


if __name__ == '__main__': sys.exit(main())
