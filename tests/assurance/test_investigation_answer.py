"""Answer-boundary checks; scripted responses are not legal-quality evidence."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from legalmath.canonical import digest, loads
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import investigation_answer as consumer
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.search.models import Settings
from scripts.legal_mission_answer import receipt_proposal
from tests.search.support import FunctionProvider
from .test_successor_workflow import investigation


@pytest.fixture(scope='module')
def prepared(investigation):
    root, runner, _, dossier = investigation
    with TemporaryDirectory(prefix='answer-test-', dir=root / 'artifacts') as td:
        directory = Path(td)
        packet = loads((root / dossier['packet']['path']).read_bytes())
        qualification = {'profile': 'investigation-answer-source-qualification.v1',
                         'source_packet_hash': digest(packet),
                         'limitations': ['Synthetic source: legal accuracy is not tested.'],
                         'evidence': [dossier['packet']], 'details': {'fixture': True}}
        save(directory / 'qualification.json', qualification)
        ref = evidence_file(runner.directory / 'revisions' / dossier['revision'] / 'dossier.json', root)
        args = {'investigation_directory': runner.directory, 'expected_revision': dossier['revision'],
                'questions': [{'question_id': 'gift', 'text': 'Selected gift control'}],
                'qualification_ref': evidence_file(directory / 'qualification.json', root)}
        request = consumer.prepare_request(root, ref, **args)
        yield root, directory, ref, args, request


def test_actual_dossier_is_consumed_without_losing_criticism_or_scoped_uncertainty(prepared):
    root, directory, ref, args, request = prepared
    dossier = loads((root / ref['path']).read_bytes())
    assert request['investigation']['scoped'] == dossier['scoped']
    assert request['investigation']['core'] == dossier['core']
    assert request['investigation']['binding'] == dossier['binding']
    assert request['source_criticism']['proposal']['arguments']
    assert request['source_qualification']['limitations']
    provider = FunctionProvider(receipt_proposal)
    result = consumer.propose(root, ref, provider, directory / 'valid', **args)
    assert result['status'] == 'STRUCTURALLY_VALID_PROPOSAL'
    assert len(provider.requests) == 1
    assert not result['legal_quality_evaluated'] and not result['tool_consideration_verified']
    with pytest.raises(FileExistsError):
        consumer.propose(root, ref, provider, directory / 'valid', **args)
    assert len(provider.requests) == 1


@pytest.mark.parametrize('fault', ['revision', 'question', 'qualification_packet', 'qualification_hash', 'dossier'])
def test_stale_inputs_rejected_before_provider(prepared, fault):
    root, directory, ref, args, _ = prepared
    args, ref = deepcopy(args), deepcopy(ref)
    if fault == 'revision':
        args['expected_revision'] = '0' * 64
    elif fault == 'question':
        args['questions'][0]['text'] = 'A different duty-trigger question'
    elif fault == 'qualification_hash':
        args['qualification_ref']['sha256'] = '0' * 64
    elif fault == 'qualification_packet':
        q = loads((root / args['qualification_ref']['path']).read_bytes())
        q['source_packet_hash'] = '0' * 64
        save(directory / 'wrong-packet.json', q)
        args['qualification_ref'] = evidence_file(directory / 'wrong-packet.json', root)
    else:
        dossier = loads((root / ref['path']).read_bytes())
        dossier['questions']['assignments'] = []
        save(directory / 'wrong-dossier.json', dossier)
        ref = evidence_file(directory / 'wrong-dossier.json', root)
    provider = FunctionProvider(lambda _: pytest.fail('Stale input dispatched'))
    result = consumer.propose(root, ref, provider, directory / ('stale-' + fault), **args)
    assert result['status'] == 'REJECTED' and result['provider_calls'] == 0
    assert not provider.requests


@pytest.mark.parametrize('fault', ['binding', 'missing_question', 'question_hash', 'duplicate_question',
                                  'missing_reading', 'duplicate_reading', 'reading_hash', 'foreign_question',
                                  'fabricated_quote', 'foreign_unit', 'legal', 'release'])
def test_invalid_answer_is_rejected(prepared, fault):
    request = prepared[-1]
    response = receipt_proposal(request)
    if fault == 'binding': response['binding_hash'] = '0' * 64
    elif fault == 'missing_question': response['answers'] = []
    elif fault == 'question_hash': response['answers'][0]['question_hash'] = '0' * 64
    elif fault == 'duplicate_question': response['answers'] *= 2
    elif fault == 'missing_reading': response['reading_account'] = []
    elif fault == 'duplicate_reading': response['reading_account'] *= 2
    elif fault == 'reading_hash': response['reading_account'][0]['reading_hash'] = '0' * 64
    elif fault == 'foreign_question': response['reading_account'][0]['question_ids'] = ['other']
    elif fault == 'fabricated_quote': response['answers'][0]['claims'][0]['support'][0]['quote'] = 'An invented source statement.'
    elif fault == 'foreign_unit': response['answers'][0]['claims'][0]['support'][0]['unit_id'] = 'foreign'
    elif fault == 'legal': response['legal_correctness_established'] = True
    else: response['release_eligible'] = True
    with pytest.raises(LegalMathError):
        consumer.validate_answer(response, request)


def test_unformalized_reading_requires_accounting_without_becoming_a_proof(prepared):
    request = deepcopy(prepared[-1])
    reading = deepcopy(next(iter(request['candidates'].values())))
    reading['formalization'] = None
    request['candidates']['unformalized'] = reading
    response = receipt_proposal(request)
    assert consumer.validate_answer(response, request)['reading_account'][-1]['disposition'] == 'UNRESOLVED'
    response['reading_account'].pop()
    with pytest.raises(LegalMathError):
        consumer.validate_answer(response, request)


def test_context_encoding_preserves_whitespace_unselected_text_and_disagreement(prepared):
    request = prepared[-1]
    packet = request['source_packet']
    context = consumer.expand_source_context(request['source_context'], packet)
    context['documents'][0]['text'] += '\nUnselected contrary text.\n'
    context['documents'][0]['secondary_text'] = 'Different extraction: keep this qualification.'
    view = consumer.source_context_view(context, packet)
    assert view['documents'][0]['secondary_text'] == context['documents'][0]['secondary_text']
    assert consumer.expand_source_context(view, packet) == context


@pytest.mark.parametrize('fault', ['missing', 'duplicate', 'foreign', 'hash'])
def test_every_supplied_tool_check_requires_a_bound_explanation(prepared, fault):
    request = deepcopy(prepared[-1])
    request['investigation']['optional_tools'] = {'checks': [{'key': 'a' * 64, 'result_hash': 'b' * 64}]}
    response = receipt_proposal(request)
    consumer.validate_answer(response, request)
    if fault == 'missing': response['tool_account'] = []
    elif fault == 'duplicate': response['tool_account'] *= 2
    elif fault == 'foreign': response['tool_account'][0]['key'] = 'c' * 64
    else: response['tool_account'][0]['result_hash'] = 'c' * 64
    with pytest.raises(LegalMathError):
        consumer.validate_answer(response, request)


def test_stale_tool_may_be_discussed_but_cannot_be_used_as_corroboration(prepared):
    request = deepcopy(prepared[-1])
    request['investigation']['optional_tools'] = {'checks': [{'key': 'a' * 64, 'result_hash': 'b' * 64}]}
    request['tool_applicability'] = {'a' * 64: 'STALE_CANDIDATES'}
    response = receipt_proposal(request)
    consumer.validate_answer(response, request)
    response['tool_account'][0]['disposition'] = 'USED'
    with pytest.raises(LegalMathError):
        consumer.validate_answer(response, request)


def test_same_packet_retrieval_for_wrong_question_cannot_be_used(prepared):
    request=deepcopy(prepared[-1])
    question='A different request-trigger question'
    check={'key':'a'*64,'result_hash':'b'*64,'kind':'retrieval','tool':'BM25','status':'PASS',
        'packet_hash':digest(request['source_packet']),'query':question,'inputs_hash':digest({'question':question}),
        'target_candidate_id':None,'target_question_hash':None}
    request['investigation']['optional_tools']={'checks':[check]}
    request['tool_applicability']={check['key']:'MATCHES_SUPPLIED_BINDINGS'}
    from legalmath.interpretation.assurance.optional_tools import adapter_results
    response=receipt_proposal(request)
    row=response['tool_account'][0]
    adapter=adapter_results(check)[0]
    row['adapter_accounts']=[{'tool_id':adapter['tool_id'],'result_hash':adapter['result_hash'],
        'disposition':'UNRESOLVED','question_ids':row['question_ids'],
        'effect_on_answer':'No support evaluated.','limitation':'Different query.'}]
    consumer.validate_answer(response,request)
    row['disposition']='USED'
    with pytest.raises(LegalMathError):consumer.validate_answer(response,request)
    row['disposition']='UNRESOLVED';row['adapter_accounts'][0]['disposition']='USED'
    with pytest.raises(LegalMathError):consumer.validate_answer(response,request)


def test_each_nested_adapter_needs_its_own_bound_account(prepared):
    request=deepcopy(prepared[-1])
    check={'key':'a'*64,'result_hash':'b'*64,'kind':'candidates','status':'PASS','tool':'Candidate tools',
        'results':[{'tool':'LegalRuleML','status':'PASS'},{'tool':'Logical English','status':'UNSUPPORTED'}]}
    request['investigation']['optional_tools']={'checks':[check]}
    request['tool_applicability']={check['key']:'MATCHES_SUPPLIED_BINDINGS'}
    response=receipt_proposal(request);row=response['tool_account'][0]
    with pytest.raises(LegalMathError):consumer.validate_answer(response,request)
    from legalmath.interpretation.assurance.optional_tools import adapter_results
    row['adapter_accounts']=[{'tool_id':a['tool_id'],'result_hash':a['result_hash'],'disposition':'UNRESOLVED',
        'question_ids':row['question_ids'],'effect_on_answer':'No causal effect evaluated.',
        'limitation':'Local fixture only.'} for a in adapter_results(check)]
    consumer.validate_answer(response,request)
    row['adapter_accounts'][1]['disposition']='USED'
    with pytest.raises(LegalMathError):consumer.validate_answer(response,request)


def test_oversized_request_retained_without_dispatch_or_truncation(prepared):
    root, directory, ref, args, _ = prepared
    provider = FunctionProvider(lambda _: pytest.fail('Overflow dispatched'))
    result = consumer.propose(root, ref, provider, directory / 'overflow', **args,
                              settings=Settings(max_input_bytes=1000))
    assert result['status'] == 'CAPACITY_BLOCKED' and result['provider_calls'] == 0
    assert result['capacity']['wire_bytes'] > 1000 and not provider.requests
    assert loads((directory / 'overflow/wire-request.json').read_bytes())['source_criticism']


def test_invalid_response_retained_with_one_call_and_no_automatic_retry(prepared):
    root, directory, ref, args, _ = prepared
    def invalid(request):
        response = receipt_proposal(request)
        response['reading_account'] = []
        return response
    provider = FunctionProvider(invalid)
    result = consumer.propose(root, ref, provider, directory / 'invalid-response', **args)
    assert result['status'] == 'REJECTED' and len(provider.requests) == 1
    assert (directory / 'invalid-response/raw-response.json').exists()
    assert not (directory / 'invalid-response/answer.json').exists()


def test_evidence_mutated_during_dispatch_invalidates_well_formed_response(prepared):
    root, directory, ref, args, _ = prepared
    args = deepcopy(args)
    path = directory / 'mutable-qualification.json'
    value = loads((root / args['qualification_ref']['path']).read_bytes())
    save(path, value)
    args['qualification_ref'] = evidence_file(path, root)
    def mutate(request):
        value['limitations'] = ['Changed during dispatch.']
        save(path, value)
        return receipt_proposal(request)
    provider = FunctionProvider(mutate)
    result = consumer.propose(root, ref, provider, directory / 'changed-during-dispatch', **args)
    assert result['status'] == 'REJECTED' and result['error'] == 'E_HASH_MISMATCH'
    assert len(provider.requests) == 1 and not (directory / 'changed-during-dispatch/answer.json').exists()
