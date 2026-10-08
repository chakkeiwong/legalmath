"""Real retained inputs through synthetic transport: no legal answer labels."""
import sys
from pathlib import Path

from legalmath.canonical import canonical
from legalmath.interpretation.search.providers import Completion

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
import assurance_new_grant_checks as checks


def test_appendix_driver_uses_full_revised_source_and_keeps_all_original_questions(tmp_path, monkeypatch):
    from legalmath.interpretation.search import providers
    from legalmath.interpretation.assurance import grants
    requests = []
    class Synthetic:
        def __init__(self, **kwargs): pass
        def complete(self, request, schema, settings):
            assert len(canonical(request)) <= settings.max_input_bytes
            requests.append(request)
            return Completion({'question_id': request['question']['question_id'],
                'status': 'NOT_ESTABLISHED', 'proposition': 'Synthetic accounting response only.',
                'evidence': [], 'missing_premises': ['No semantic assessment supplied by this synthetic provider.'],
                'alternative_readings': [], 'next_source_questions': []}, {'synthetic': True})
    monkeypatch.setattr(providers, 'CodexProvider', Synthetic)
    monkeypatch.setattr(grants, 'GrantSlice', lambda *a, **k: object())
    monkeypatch.setattr(checks, 'OUT', tmp_path)
    work = tmp_path/'sources'; work.mkdir()
    result = checks.F2_sources(work)
    assert len(requests) == 2
    assert all(len(r['source_packet']['units']) == 177 for r in requests)
    assert all(not r['prior_round_proposals'] for r in requests)
    assert result['source_question_count'] == 6
    assert result['authority_questions_legally_closed'] == 0
    assert len(result['original_inventory_status']) == 2
    assert all(row['retained_requests'] for row in result['original_inventory_status'])
    assert {r['role'] for r in result['proposals']} == {'source-first', 'exception-challenger'}


def test_large_readable_input_keeps_all_concerns_and_checks_actual_response_shape(tmp_path, monkeypatch):
    from legalmath.interpretation.search import providers
    from legalmath.interpretation.assurance import grants, readable_tables
    requests = []
    class Synthetic:
        def __init__(self, **kwargs): pass
        def complete(self, request, schema, settings):
            assert len(canonical(request)) <= settings.max_input_bytes
            restored = readable_tables.decode(request,
                expected_request_hash=request['input_encoding']['original_request_hash'])
            # This is a test provider, not an authenticity verifier. The actual
            # transport already checked the independently retained original.
            requests.append(restored)
            original = restored['output_identity_contract']
            return Completion({'packet_hash': original['packet_hash'],
                'interpretation_hash': original['interpretation_hash'], 'coverage_hash': original['coverage_hash'],
                'concerns': [{'concern_id': c['concern_id'], 'status': 'RETAINED_UNRESOLVED',
                    'evidence': [], 'rationale': 'Synthetic accounting only.'} for c in restored['coverage']['concerns']],
                'questions': [{'question_id': q['control_id'], 'question_hash': __import__('legalmath.canonical', fromlist=['digest']).digest(q),
                    'status': 'UNRESOLVED', 'rationale': 'Synthetic accounting only.'} for q in restored['interpretation']['questions']],
                'revised_interpretation': None, 'remaining_uncertainty': ['All semantic questions remain.']}, {'synthetic': True})
    monkeypatch.setattr(providers, 'CodexProvider', Synthetic)
    monkeypatch.setattr(grants, 'GrantSlice', lambda *a, **k: object())
    monkeypatch.setattr(checks, 'OUT', tmp_path)
    work = tmp_path/'tables'; work.mkdir()
    result = checks.F2_tables(work)
    assert len(requests) == 2
    assert result['concern_denominator'] == 263
    assert all(r['status'] == 'VALIDATED_TRANSPORT_PROPOSAL' and r['concerns'] == 263 for r in result['records'])
    assert result['synthetic_input']
