from copy import deepcopy
from pathlib import Path

import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_context import ContextRoute, Limits
from legalmath.interpretation.assurance.bounded_product import BoundedProduct, BoundDispatch, PROFILE, NOTE, project_provider_events
from legalmath.interpretation.search.providers import Completion


def envelope():
    return {"source_packet": {"source_key": "test.corpus", "authority": "SYNTHETIC_FIXTURE",
        "selected_slice": "When does the duty apply?", "family_ids": ["scope"], "dependencies": [],
        "units": [{"unit_id": "source.a", "locator": "a", "text": "A duty applies when a request is made.",
                   "normative": True, "span": {}},
                  {"unit_id": "source.b", "locator": "b", "text": "An exception applies if consent is absent.",
                   "normative": True, "span": {}}]},
        "original_questions": [{"question_id": "p14", "text": "When does the duty apply?"}],
        "source_qualification": {"limitations": ["Synthetic control, no legal finding."]},
        "answer_acceptance": {"profile": "product-answer-acceptance.v1",
            "original_questions": [{"question_id": "p14", "text": "When does the duty apply?"}],
            "source_documents": [], "acceptance_obligations": [{"id": "o1", "question_ids": ["p14"],
                 "statement": "Preserve exceptions."}], "original_readings": [], "cases": []}}


def limits():
    return Limits(chunk_tokens=200, overlap_tokens=100, input_tokens=20000,
                  output_tokens=5000, records_per_request=1)


class Scripted:
    live = False
    def __init__(self, fail_at=None):
        self.requests = []
        self.fail_at = fail_at

    def complete(self, request, schema, settings):
        self.requests.append(deepcopy(request))
        if len(self.requests) == self.fail_at: raise RuntimeError("isolated failure")
        if "records" in schema["properties"]:
            value = {"records": [{"id": r["id"], "status": "UNRESOLVED", "findings": [],
                       **({'observations': []} if request['task'] == 'REVIEW_REQUIREMENTS' else {}),
                       "open_dependencies": ["Scripted; not interpreted."]} for r in request["records"]]}
        else:
            sources = [r for r in request["records"] if r["kind"] == "source"]
            quotes = [{"record_id": r["id"], "quote": r["text"], "locator": ""} for r in sources[:1]]
            if 'decisions' in schema['properties']:
                value = {'decisions': [{'issue_id': r['id'], 'disposition': 'WARRANTED',
                    'basis': 'DELIVERED_SOURCE', 'reason': 'Scripted supported criticism.', 'support': quotes}
                    for r in request['payload']['issues']], 'considered': request['required_considered']}
            elif "verdict" in schema["properties"]:
                value = {"verdict": "UNRESOLVED", "considered": request["required_considered"],
                         "reason": "Scripted review retains uncertainty.", "support": quotes,
                         "issues": ["Source reasoning requires actual review."]}
            else:
                value = {"conclusion": "The answer depends on the request and consent.", "support": quotes,
                    "contrary": [], "assumptions": [], "unresolved": ["Actual facts unknown."],
                    "alternatives": [{"condition": "Consent is absent", "consequence": "Consider the exception."}],
                    "considered": request["required_considered"]}
            if 'source_gaps' in schema['properties']: value['source_gaps'] = []
            if 'assertion_bindings' in schema['properties']: value['assertion_bindings'] = []
        return Completion(value, {"provider": "scripted-control"})


def test_product_entry_reaches_complete_investigation_and_consumer(tmp_path):
    from scripts.legal_product_completion import run_product
    provider = Scripted()
    original = envelope()
    result = run_product(tmp_path, tmp_path / "product", provider, tmp_path / "jdk", "2026-10-13T00:00:00Z",
        sources=[], questions=original["original_questions"], acceptance_ref=None, qualification={},
        required={"maximum_calls": 100}, deadline_utc="2030-01-01T00:00:00+00:00", selected_tools=[],
        settings=None, consumer_profile=PROFILE, bounded_envelope=original, bounded_encode=list, bounded_limits=limits())
    assert result["trace"] == ["run_product", "CompleteInvestigation.run", "dossier_answer.propose"]
    tasks = {r["task"] for r in provider.requests}
    assert {"READ_SOURCE", "ASSESS_ORIGINAL_REQUIREMENT", "ANSWER_ORIGINAL_QUESTION",
            "AUDIT_ANSWER_AGAINST_SOURCE", "AUDIT_ANSWER_AND_DETAILED_ACCOUNT"} <= tasks
    assert not result["all_question_reviews_accepted"]
    assert not result["legal_correctness_established"]


def test_synthesis_projection_retains_semantics_and_full_event_receipt(tmp_path):
    product = BoundedProduct(tmp_path, tmp_path/'product', Scripted(), envelope(), list, limits=limits())
    source = next(r for r in product.route.records.values() if r['kind'] == 'source')
    payload = [{'id': 'reading-a', 'value': {'result': {'status': 'VALIDATED',
        'value': {'source': source['id'], 'support': source['text']},
        'provenance': {'provider': 'test', 'events_jsonl': 'event one\nevent two\n',
                       'usage': [{'input_tokens': 12}]}}}}]
    original = deepcopy(payload)
    request = product.request('SYNTHESIZE_FINDINGS', envelope()['original_questions'][0],
                              [source], payload=payload, expected=['reading-a'])
    event = request['payload'][0]['value']['result']
    assert payload == original
    assert event['status'] == 'VALIDATED' and event['value'] == original[0]['value']['result']['value']
    assert event['provenance']['provider'] == 'test' and event['provenance']['usage'] == [{'input_tokens': 12}]
    assert 'events_jsonl' not in event['provenance']
    receipt = event['provenance']['event_log_receipt']
    assert (product.directory / receipt['path']).read_text() == 'event one\nevent two\n'
    assert receipt['utf8_bytes'] == len('event one\nevent two\n'.encode())
    assert product.request('SYNTHESIZE_FINDINGS', envelope()['original_questions'][0],
                           [source], payload=payload, expected=['reading-a']) == request
    projected, _ = project_provider_events(original)
    assert request['payload'] == projected
    source_metadata = {'provenance': {'events_jsonl': 'This field is source data.'}}
    assert project_provider_events(source_metadata) == (source_metadata, {})
    (product.directory / receipt['path']).write_text('changed')
    with pytest.raises(LegalMathError):
        product.request('SYNTHESIZE_FINDINGS', envelope()['original_questions'][0],
                        [source], payload=payload, expected=['reading-a'])


def test_source_failure_does_not_cancel_other_readers(tmp_path):
    provider = Scripted(fail_at=1)
    product = BoundedProduct(tmp_path, tmp_path / "product", provider, envelope(), list, limits=limits())
    result = product.investigate()
    assert not result["execution_complete"]
    assert result["outputs"][0]["result"]["status"] == "FAILED"
    assert result["outputs"][-1]["result"]["status"] == "VALIDATED"
    assert {r["reader"] for r in provider.requests if r["task"] == "READ_SOURCE"} == {"reader-1", "reader-2"}


def test_resume_reuses_only_identical_completed_requests(tmp_path):
    provider = Scripted()
    product = BoundedProduct(tmp_path, tmp_path / "product", provider, envelope(), list, limits=limits())
    first = product.investigate()
    count = len(provider.requests)
    assert product.investigate() == first
    assert len(provider.requests) == count
    from legalmath.interpretation.assurance.monitor import save
    p = tmp_path / "product/calls/read-0000/result.json"
    save(p, {"status": "VALIDATED", "value": {}})
    with pytest.raises(LegalMathError) as caught:
        product.investigate()
    assert caught.value.details == "Changed retained result"


def test_uncertain_dispatch_not_replayed(tmp_path):
    provider = Scripted()
    product = BoundedProduct(tmp_path, tmp_path / "product", provider, envelope(), list, limits=limits())
    packet = product.route.reading_plan()[0][0]
    from legalmath.interpretation.assurance.monitor import save
    save(tmp_path / "product/calls/dispatch.json", {"input_hash": product.route.input_hash,
        "maximum_calls": 1024, "calls": {"read-0000": {"identity": product.dispatch.request_identity(
        packet["request"], packet["schema"]), "status": "RESERVED"}}})
    with pytest.raises(LegalMathError) as caught:
        product.investigate()
    assert "Uncertain prior dispatch" in caught.value.details
    assert not provider.requests


def test_unqualified_live_provider_refused_before_dispatch(tmp_path):
    provider = Scripted()
    provider.live = True
    product = BoundedProduct(tmp_path, tmp_path / "product", provider, envelope(), list, limits=limits())
    with pytest.raises(LegalMathError) as caught:
        product.investigate()
    assert "reviewed persistent provider" in caught.value.details
    assert not provider.requests


def test_review_rejects_omission_fabricated_quote_and_false_locator(tmp_path):
    product = BoundedProduct(tmp_path, tmp_path / "product", Scripted(), envelope(), list, limits=limits())
    record = next(r for r in product.route.records.values() if r["kind"] == "source")
    for quote in [{"record_id": record["id"], "quote": "Invented text", "locator": ""},
                  {"record_id": record["id"], "quote": record["text"], "locator": "P20"}]:
        with pytest.raises(LegalMathError): product.citations({"support": [quote]}, [record])
    with pytest.raises(LegalMathError):
        product.citations({"conclusion": "Paragraph 20 establishes fulfillment.", "support": []}, [record])


def test_final_source_audit_receives_remote_exception(tmp_path):
    provider = Scripted()
    product = BoundedProduct(tmp_path, tmp_path / "product", provider, envelope(), list, limits=limits())
    product.audit_answer("p14", envelope()["original_questions"][0], {"conclusion": "Duty always applies"}, [])
    inspected = {r["unit_id"] for request in provider.requests for r in request["records"]}
    assert inspected == {"source.a", "source.b"}


def test_dependency_review_has_own_population_and_cited_remote_context(tmp_path):
    provider = Scripted()
    product = BoundedProduct(tmp_path, tmp_path/'product', provider, envelope(), list, limits=limits())
    a, b = [r for r in product.route.records.values() if r['kind'] == 'source']
    answer = {'conclusion': 'Conditional on consent.', 'considered': ['reduction-1'],
        'support': [{'record_id': b['id'], 'quote': b['text'], 'locator': ''}]}
    dependency = {'id': 'dependency-a', 'question_id': 'p14', 'origin_id': a['id'],
                  'delivered_ids': [a['id']], 'dependency': 'Check the exception.'}
    product.audit_dependencies('p14', envelope()['original_questions'][0], answer, [dependency])
    request = provider.requests[0]
    assert request['required_considered'] == ['dependency-a']
    assert request['payload']['answer']['considered'] == ['reduction-1']
    assert request['review_scope']['assigned_source_ids'] == [a['id']]
    assert request['review_scope']['context_source_ids'] == [b['id']]
    assert request['review_scope']['cited_source_ids_outside_window'] == []
    assert {r['id'] for r in request['records']} == {a['id'], b['id']}


def test_scoped_review_marks_unaffordable_context_without_accepting_foreign_quotes(tmp_path, monkeypatch):
    product = BoundedProduct(tmp_path, tmp_path/'product', Scripted(), envelope(), list, limits=limits())
    a, b = [r for r in product.route.records.values() if r['kind'] == 'source']
    answer = {'conclusion': 'Conditional.', 'support': [{'record_id': b['id'], 'quote': b['text']}]}
    def measure(request, schema):
        if len(request['records']) > 1:
            raise LegalMathError('E_RESOURCE_LIMIT', details='Test window capacity')
    monkeypatch.setattr(product.dispatch, 'measure', measure)
    request = product.request('AUDIT_ANSWER_AGAINST_SOURCE', envelope()['original_questions'][0],
                              [a], payload=answer, expected=[a['id']])
    assert request['review_scope']['cited_source_ids_outside_window'] == [b['id']]
    assert request['required_considered'] == [a['id']]
    answer['support'][0]['quote'] = 'Invented exception'
    with pytest.raises(LegalMathError):
        product.request('AUDIT_ANSWER_AGAINST_SOURCE', envelope()['original_questions'][0],
                        [a], payload=answer, expected=[a['id']])


def test_input_schema_overflow_is_pre_dispatch(tmp_path):
    provider = Scripted()
    route = ContextRoute(envelope(), list, limits=limits())
    dispatch = BoundDispatch(provider, tmp_path, route)
    with pytest.raises(LegalMathError): dispatch.call("big", {"body": "x" * 21000}, NOTE, lambda v: None)
    assert not provider.requests


def test_persistent_campaign_charges_failures_and_checks_expiry(tmp_path):
    from datetime import datetime, timedelta, timezone
    from legalmath.interpretation.assurance.bounded_provider import CampaignAllowance
    from legalmath.interpretation.assurance.monitor import save
    from legalmath.interpretation.assurance.integration_contract import evidence_file
    route = {"model": "test-model", "provider": "test", "fields": {}}
    save(tmp_path / "proposal.json", {"dispatch_ready": True, "maximum_calls": 1,
        "routing_hash": digest(route), "window_seconds": 3600, "bindings": []})
    now = datetime.now(timezone.utc)
    grant = {"profile": "integration-master-live-grant.v1", "approved": True,
        "approval_text": "Synthetic test approval", "proposal": evidence_file(tmp_path / "proposal.json", tmp_path),
        "maximum_calls": 1, "routing_hash": digest(route), "started_utc": now.isoformat(),
        "deadline_utc": (now + timedelta(seconds=3600)).isoformat()}
    save(tmp_path / "live-grant.json", grant)
    allowance = CampaignAllowance(tmp_path, route, root=tmp_path)
    allowance.expected = "test"
    assert allowance.reserve("test") == 1
    with pytest.raises(LegalMathError): allowance.reserve("test")
    # No output is needed for the reservation to remain charged.
    assert len(allowance.check()["calls"]) == 1
    grant["deadline_utc"] = (now - timedelta(seconds=1)).isoformat()
    save(tmp_path / "live-grant.json", grant)
    with pytest.raises(LegalMathError): allowance.check()


def test_requirement_failure_continues_unrelated_question(tmp_path):
    from scripts.legal_integration_rehearsal import UnresolvedProvider
    class FailingDetail(UnresolvedProvider):
        def complete(self, request, schema, settings):
            if request['task'] == 'ASSESS_ORIGINAL_REQUIREMENT' and request['payload']['id'] == 'obligation:o1':
                raise RuntimeError('One local detail failed')
            return super().complete(request, schema, settings)
    original = envelope()
    original['original_questions'].append({'question_id': 'p10', 'text': 'What is the responsibility?'})
    original['answer_acceptance']['acceptance_obligations'].append(
        {'id': 'o2', 'question_ids': ['p10'], 'statement': 'Separate the responsible actor.'})
    product = BoundedProduct(tmp_path, tmp_path/'product', FailingDetail(), original, list, limits=limits())
    result = product.answer(product.investigate())
    assert result['answers']['p14']['status'] == 'FAILED'
    assert result['answers']['p10']['answer']['status'] == 'VALIDATED'


def test_shared_checkpoints_preserve_inputs_and_do_not_dispatch(tmp_path):
    provider = Scripted()
    common = BoundedProduct(tmp_path, tmp_path/'common', provider, envelope(), list, limits=limits())
    common.investigate()
    fresh = Scripted()
    arm = BoundedProduct(tmp_path, tmp_path/'arm', fresh, envelope(), list, limits=limits(),
                         shared_prefix=tmp_path/'common/calls')
    assert arm.investigate()['execution_complete']
    assert not fresh.requests
    changed = envelope()
    changed['original_questions'][0]['text'] = 'Different question'
    other = BoundedProduct(tmp_path, tmp_path/'other', fresh, changed, list, limits=limits(),
                           shared_prefix=tmp_path/'common/calls')
    with pytest.raises(LegalMathError): other.investigate()
    assert not fresh.requests


def test_source_and_requirement_audit_capacity_failure_is_local(tmp_path):
    provider = Scripted()
    product = BoundedProduct(tmp_path, tmp_path/'product', provider, envelope(), list, limits=limits())
    records = [r for r in product.route.records.values() if r['kind'] == 'obligation']
    other = deepcopy(records[0]); other['id'] = 'obligation:o2'; product.route.records[other['id']] = other
    product.route.store_hash = digest(product.route.records)
    details = [{'id': records[0]['id'], 'result': {'value': {'conclusion': 'x' * 21000}}},
               {'id': other['id'], 'result': {'value': {'conclusion': 'small'}}}]
    audits = product.audit_answer('p14', envelope()['original_questions'][0], {'conclusion': 'conditional'}, details)
    assert audits[-2]['status'] == 'FAILED'
    assert audits[-1]['status'] == 'VALIDATED'


def test_judgment_read_failure_does_not_block_circular_question(tmp_path):
    original = envelope()
    original['original_questions'].append({'question_id': 'gatecoin', 'text': 'Does the case support trust?'})
    original['source_packet']['units'][1]['locator'] = 'https://legalref.judiciary.hk/example.docx'
    class FailJudgment(Scripted):
        def complete(self, request, schema, settings):
            if any(r.get('unit_id') == 'source.b' for r in request.get('records', [])):
                raise RuntimeError('Judgment read failed')
            return super().complete(request, schema, settings)
    product = BoundedProduct(tmp_path, tmp_path/'product', FailJudgment(), original, list, limits=limits())
    acquisition = product.investigate()
    assert not acquisition['execution_complete']
    assert acquisition['question_acquisition_complete'] == {'p14': True, 'gatecoin': False}
