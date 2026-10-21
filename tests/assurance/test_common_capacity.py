"""Behavioral controls for the common capacity path; no live model calls."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json
import pytest
from jsonschema import validate
from legalmath.canonical import canonical, digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_context import Limits
from legalmath.interpretation.assurance.bounded_product import BoundedProduct, NOTE, WARRANT
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased import capacity_policy as policy, capacity_adapters as adapters
from legalmath.interpretation.assurance.phased.phase import execute
from legalmath.interpretation.search.providers import Completion
from tests.assurance.test_bounded_product import Scripted, envelope, limits
from tests.assurance.test_phased_product import PhasedScripted


def product(tmp_path, provider=None, *, phased=False, **kwargs):
    options = dict(common_capacity_profile=policy.PROFILE, limits=limits(), **kwargs)
    if phased:
        options.update(phase_admit=lambda name, count: {'name': name, 'count': count}, phase_identity='test-code.v1')
    cls = PhasedProduct if phased else BoundedProduct
    return cls(tmp_path, tmp_path/'product', provider or Scripted(), envelope(), list, **options)


def warrant(p, count=6):
    sources = [r for r in p.route.records.values() if r['kind'] == 'source']
    req = p.request('ASSESS_REVIEW_WARRANT', envelope()['original_questions'][0], sources,
        payload=dict(answer={'conclusion': 'Only if the exception does not apply.'},
            review={'issues': ['Full original issue context remains visible.']},
            issues=[dict(id='i'+str(i), text='Check source condition '+str(i)) for i in range(count)]), expected=['review-0'])
    def check(value):
        actual = [r['issue_id'] for r in value['decisions']]
        assert actual == ['i'+str(i) for i in range(count)]
        p.citations(value, sources)
    return dict(key='warrant', request=req, schema=WARRANT, validate=check)


def run(p, c):
    return p.dispatch.call(c['key'], c['request'], c['schema'], c['validate'])


def test_output_exact_boundary_and_one_over():
    req = policy.annotate({'task': 'STRUCTURED_CRITICISM'})
    value = {'a': 'x'*50}
    length = len(canonical(value))
    cap = Limits(decoded_output_bytes=length, decoded_output_tokens=length)
    assert policy.measure_output(value, req, cap, list, expanded=True)['bytes'] == length
    with pytest.raises(LegalMathError):
        policy.measure_output({'a': 'x'*51}, req, cap, list, expanded=True)
    tokens = policy.output_tokens(req, cap)
    assert policy.measure_output({'a': 'x'*(tokens-8)}, req, cap, list)['local_tokens'] == tokens
    with pytest.raises(LegalMathError):
        policy.measure_output({'a': 'x'*(tokens-7)}, req, cap, list)


def test_unknown_stage_and_profile_fail_before_transport(tmp_path):
    p = product(tmp_path)
    for req in ({'task': 'UNREVIEWED_STAGE'}, {'task': 'READ_SOURCE', 'capacity_profile': 'future'}):
        with pytest.raises(LegalMathError):
            p.dispatch.call('bad', req, {}, lambda _: None)
    assert not p.provider.requests


def test_warrant_output_partition_preserves_full_context_and_resumes(tmp_path):
    p = product(tmp_path)
    c = warrant(p)
    value = run(p, c)
    assert value['status'] == 'VALIDATED'
    assert len(p.provider.requests) == 2
    for req in p.provider.requests:
        for field in ('answer', 'review'):
            assert req['payload'][field] == c['request']['payload'][field]
        assert req['records'] == c['request']['records']
        assert len(req['payload']['issues']) == 3
    assert run(p, c) == value and len(p.provider.requests) == 2


@pytest.mark.parametrize('mutation', ['source', 'schema', 'version'])
def test_changed_contract_cannot_reuse(tmp_path, monkeypatch, mutation):
    p = product(tmp_path)
    c = warrant(p)
    run(p, c)
    if mutation == 'source':
        c['request']['records'][0]['text'] += ' Changed.'
    elif mutation == 'schema':
        c['schema'] = deepcopy(c['schema'])
        c['schema']['properties']['considered']['maxItems'] = 1
    else:
        monkeypatch.setitem(policy.STAGES, 'ASSESS_REVIEW_WARRANT',
            replace(policy.STAGES['ASSESS_REVIEW_WARRANT'], maximum_depth=3))
    with pytest.raises(LegalMathError):
        run(p, c)
    assert len(p.provider.requests) == 2


def test_failed_independent_child_does_not_cancel_sibling(tmp_path):
    p = product(tmp_path, Scripted(fail_at=1))
    result = run(p, warrant(p))
    assert result['status'] == 'FAILED' and result['error'] == 'E_DEPENDENCY'
    assert len(p.provider.requests) == 2
    assert result['pieces'][1]['status'] == 'VALIDATED'


def test_uncertain_leaf_blocks_resampling(tmp_path):
    p = product(tmp_path)
    c = warrant(p)
    run(p, c)
    path = p.dispatch.directory/'dispatch.json'
    state = json.loads(path.read_text())
    state['calls']['warrant-p0']['status'] = 'RESERVED'
    path.write_text(json.dumps(state))
    with pytest.raises(LegalMathError) as error:
        run(p, c)
    assert error.value.code == 'E_AUTHORITY'
    assert len(p.provider.requests) == 2


def test_completed_leaf_tampering_blocks_assembled_reuse(tmp_path):
    p = product(tmp_path)
    c = warrant(p)
    run(p, c)
    (p.dispatch.directory/'warrant-p0/result.json').write_text('{}')
    with pytest.raises(LegalMathError) as error:
        run(p, c)
    assert error.value.code == 'E_INTEGRITY'


class Overflow(Scripted):
    def complete(self, request, schema, settings):
        if len(request['payload']['issues']) > 1:
            self.requests.append(deepcopy(request))
            raise LegalMathError('E_RESOURCE_LIMIT', details='Actual provider output exceeds local token allowance')
        return super().complete(request, schema, settings)


def test_actual_overflow_has_finite_recovery_not_same_request_retry(tmp_path):
    p = product(tmp_path, Overflow())
    c = warrant(p, 3)
    result = run(p, c)
    assert result['status'] == 'VALIDATED'
    assert [len(r['payload']['issues']) for r in p.provider.requests] == [3, 1, 2, 1, 1]
    assert len({digest(r) for r in p.provider.requests}) == 5
    assert json.loads((p.dispatch.directory/'warrant/result.json').read_text())['status'] == 'FAILED'
    assert run(p, c) == result and len(p.provider.requests) == 5


def test_semantic_failure_is_not_a_capacity_retry(tmp_path):
    class Wrong(Scripted):
        def complete(self, request, schema, settings):
            result = super().complete(request, schema, settings)
            result.value['decisions'] = []
            return result
    p = product(tmp_path, Wrong())
    result = run(p, warrant(p, 2))
    assert result['status'] == 'FAILED' and len(p.provider.requests) == 1


def test_service_deadline_is_not_split(tmp_path):
    class Deadline(Scripted):
        def complete(self, request, schema, settings):
            self.requests.append(request)
            raise LegalMathError('E_RESOURCE_LIMIT', details='Codex call deadline with output; inspect retained evidence')
    p = product(tmp_path, Deadline())
    assert run(p, warrant(p, 2))['status'] == 'FAILED'
    assert len(p.provider.requests) == 1


def test_leaf_call_and_depth_bounds(tmp_path, monkeypatch):
    monkeypatch.setitem(policy.STAGES, 'ASSESS_REVIEW_WARRANT',
        replace(policy.STAGES['ASSESS_REVIEW_WARRANT'], maximum_depth=1, maximum_calls=2))
    p = product(tmp_path, Overflow())
    result = run(p, warrant(p, 3))
    assert result['status'] == 'FAILED' and len(p.provider.requests) <= 2


def test_oversized_atomic_context_is_explicit(tmp_path):
    p = product(tmp_path)
    req = p.request('STRUCTURED_CRITICISM', envelope()['original_questions'][0], [], payload='x'*250000)
    result = p.dispatch.call('criticism', req, {}, lambda _: None)
    assert result['status'] == 'FAILED' and result['capacity_remainder']['adapter'] == 'atomic'
    assert 'graph' in result['reason'] and not p.provider.requests


def test_grouped_review_keeps_remote_exception_and_namespaces(tmp_path):
    from legalmath.interpretation.assurance.phased import group_review
    class Review(PhasedScripted):
        def complete(self, request, schema, settings):
            # A hostile omission would turn this fixture's answer into ACCEPT.
            assert any('exception' in r['text'] for r in request['records'])
            return super().complete(request, schema, settings)
    p = product(tmp_path, Review(), phased=True)
    sources = [r for r in p.route.records.values() if r['kind'] == 'source']
    ids = ['assignment-'+str(i) for i in range(8)]
    req = p.request('AUDIT_SOURCE_DEPENDENCY_ASSIGNMENTS', envelope()['original_questions'][0], sources,
        payload=dict(answer={'conclusion':'Duty always applies.'}, assignments=ids), expected=ids)
    shape = group_review.schema(ids, legal_indexes=[])
    result = p.dispatch.call('group', req, shape,
        lambda v: group_review.validate(p, 'p14', v, ids, sources))
    assert result['status'] == 'VALIDATED'
    assert len(p.provider.requests) == 2
    assert len({r['analysis_id'] for r in result['value']['analyses']}) == 2
    assert all(r['decision']['verdict'] == 'UNRESOLVED' for r in result['value']['analyses'])
    assert set(result['value']['assignments']) == set(ids)


def test_missing_or_duplicate_assignments_are_rejected(tmp_path):
    p = product(tmp_path)
    c = warrant(p, 2)
    c['request']['payload']['issues'][1]['id'] = 'i0'
    with pytest.raises(LegalMathError):
        run(p, c)
    assert not p.provider.requests


def test_original_assembled_validation_can_veto_merge(tmp_path):
    p = product(tmp_path)
    c = warrant(p)
    def reject(value):
        raise LegalMathError('E_SCHEMA', details='Contradictory assembled decisions')
    c['validate'] = reject
    result = run(p, c)
    assert result['status'] == 'FAILED' and result['error'] == 'E_SCHEMA'
    assert len(p.provider.requests) == 2


def test_all_active_model_stages_are_registered_and_budgeted(tmp_path):
    p = product(tmp_path)
    for task, definition in policy.STAGES.items():
        req = {'task': task, 'payload': {'issues': []}, 'records': [], 'required_considered': []}
        measurement = p.dispatch.measure(req, {'type': 'object'})
        assert measurement['capacity']['stage'] == task
        assert measurement['capacity']['output_tokens'] == definition.output_tokens
    assert len(policy.STAGES) == 20


def test_real_product_entry_and_reviews_use_common_interface(tmp_path):
    provider = PhasedScripted()
    old = BoundedProduct(tmp_path, tmp_path/'acquisition', provider, envelope(), list, limits=limits())
    investigation = old.investigate()
    p = product(tmp_path, provider, phased=True)
    p.install_dispatch_admission()
    count = len(provider.requests)
    outcome = p.answer(investigation)
    assert outcome['answers']['p14']['answer']['status'] == 'VALIDATED'
    assert not outcome['all_question_reviews_accepted']
    assert all(r['capacity_profile'] == policy.PROFILE for r in provider.requests[count:])
    assert len(list((p.directory/'capacity').glob('*/state.json'))) > 2
    used = len(provider.requests)
    assert p.answer(investigation)['answers'] == outcome['answers']
    assert len(provider.requests) == used


def test_native_complete_graph_has_memory_bound(tmp_path):
    p = product(tmp_path)
    graph = {'arguments':['a','b'], 'attacks':[['a','b']]}
    receipt = p.capacity_manager.native('criticism', {}, graph)
    assert receipt['input_hash'] == digest(dict(packet={}, inputs=graph))
    assert not receipt['semantic_partition']
    with pytest.raises(LegalMathError):
        p.capacity_manager.native('criticism', {}, {'text':'x'*3000000})
    with pytest.raises(LegalMathError):
        p.capacity_manager.native('unknown-solver', {}, graph)


def test_instructions_and_transport_settings_agree(tmp_path):
    p = product(tmp_path)
    req = policy.annotate(p.request('ANSWER_ORIGINAL_QUESTION', envelope()['original_questions'][0], [], payload={}, expected=[]))
    from legalmath.interpretation.assurance.bounded_references import prepare
    wire = prepare(req, NOTE)
    assert '3000 local tokens' not in wire['request']['instructions']
    assert str(policy.STAGES[req['task']].output_tokens) in wire['request']['capacity_instructions']
    assert p.dispatch.measure(req, NOTE)['bytes'] > len(canonical(req))


def test_independent_phase_survives_atomic_capacity_failure(tmp_path):
    p = product(tmp_path, phased=True)
    bad = dict(key='atomic', request={'task':'STRUCTURED_CRITICISM','text':'x'*250000},
        schema={}, validate=lambda _: None)
    good = warrant(p, 1)
    result = execute(p, 'independent', [bad, good], implementation_identity='test-code.v1',
        admit=p.phase_admit)
    assert [r['result']['status'] for r in result['results']] == ['FAILED','VALIDATED']


def test_source_reading_partitions_then_validates_complete_population(tmp_path):
    class ReadingOverflow(Scripted):
        def complete(self, request, schema, settings):
            if len(request['records']) > 1:
                self.requests.append(request)
                raise LegalMathError('E_RESOURCE_LIMIT', details='Actual provider output exceeds local token allowance')
            return super().complete(request, schema, settings)
    p = product(tmp_path, ReadingOverflow())
    ids = [r['id'] for r in p.route.records.values() if r['kind'] == 'source']
    packet = p.route.make_packet('READ_SOURCE', ids)
    result = p.dispatch.call('reading', packet['request'], packet['schema'],
        lambda value: p.route.validate_response(packet, value))
    assert result['status'] == 'VALIDATED'
    assert [r['id'] for r in result['value']['records']] == ids
    assert len(p.provider.requests) == 3
    assert all(r['status'] == 'UNRESOLVED' for r in result['value']['records'])


@pytest.mark.parametrize('broken_bridge', [False, True])
def test_partial_source_notes_require_joint_exception_bridge(tmp_path, broken_bridge):
    class NoteOverflow(Scripted):
        def complete(self, request, schema, settings):
            if len(request['records']) > 1 and 'capacity_partial_readings' not in request:
                self.requests.append(request)
                raise LegalMathError('E_RESOURCE_LIMIT', details='Actual provider output exceeds local token allowance')
            if 'capacity_partial_readings' in request:
                assert len(request['records']) == 2
                assert len(request['capacity_partial_readings']) == 2
                assert any('exception' in row['text'] for row in request['records'])
                if broken_bridge:
                    self.requests.append(request)
                    raise RuntimeError('Joint bridge failed')
            return super().complete(request, schema, settings)
    p = product(tmp_path, NoteOverflow())
    sources = [r for r in p.route.records.values() if r['kind'] == 'source']
    req = p.request('ASSESS_ORIGINAL_REQUIREMENT', envelope()['original_questions'][0], sources,
        payload={'assignment':'Assess the duty with its exception.'}, expected=['requirement'])
    def check(value):
        assert any('exception' in row['consequence'] for row in value['alternatives'])
    result = p.dispatch.call('source-notes', req, NOTE, check)
    assert result['status'] == ('FAILED' if broken_bridge else 'VALIDATED')
    assert len(p.provider.requests) == 4


def test_warrant_merge_rebases_exact_assertion_paths(tmp_path):
    p = product(tmp_path)
    c = warrant(p, 2)
    c['request'] = policy.annotate(c['request'])
    children = adapters.split(p, c)
    values = []
    for child in children:
        value = Scripted().complete(child['request'], child['schema'], p.dispatch.settings).value
        value['assertion_bindings'] = [{'path':'/decisions/0/reason', 'index_hash':'test',
            'citation':{'record_id':'r', 'quote':'q', 'locator':''}}]
        values.append(value)
    merged = adapters.merge(p, c, children, values)
    assert [r['path'] for r in merged['assertion_bindings']] == ['/decisions/0/reason','/decisions/1/reason']
    values[0]['assertion_bindings'][0]['path'] = '/unrecognized'
    with pytest.raises(LegalMathError):
        adapters.merge(p, c, children, values)


def test_actual_provider_output_budget_and_settings(tmp_path, monkeypatch):
    from legalmath.interpretation.assurance.bounded_provider import BoundedCodexProvider
    from legalmath.interpretation.search.providers import CodexProvider
    class Allowance:
        def service_recovery_policy(self): return None
        def terminal_recovery_attempts(self): return 0
    p = object.__new__(BoundedCodexProvider)
    p.allowance, p.encode, p.limits = Allowance(), list, Limits()
    p.check = lambda: None
    p.measure = lambda *args: {}
    req = policy.annotate({'task':'STRUCTURED_CRITICISM'})
    def complete(self, request, schema, settings):
        return Completion({'a':'x'*4000}, {})
    monkeypatch.setattr(CodexProvider, 'complete', complete)
    from legalmath.interpretation.search.models import Settings
    assert p._complete(req, {}, Settings()).value['a'] == 'x'*4000
    with pytest.raises(LegalMathError):
        p._complete({'task':'STRUCTURED_CRITICISM'}, {}, Settings())


def test_remaining_wall_time_is_durable(tmp_path, monkeypatch):
    from legalmath.interpretation.assurance.phased import capacity
    p = product(tmp_path)
    c = warrant(p)
    # Persist a plan before a simulated crash, without a dispatched leaf.
    original = capacity.adapters.split
    def crash(*args): raise RuntimeError('interruption before subdivision')
    monkeypatch.setattr(capacity.adapters, 'split', crash)
    with pytest.raises(RuntimeError): run(p, c)
    monkeypatch.setattr(capacity.adapters, 'split', original)
    original_time = capacity.time.time()
    monkeypatch.setattr(capacity.time, 'time', lambda: original_time + 20000)
    result = run(p, c)
    assert result['status'] == 'FAILED' and 'elapsed-time' in result['reason']
    assert not p.provider.requests


def test_full_native_tool_entry_receives_complete_candidates_and_graph(tmp_path):
    from legalmath.interpretation.search.models import DIMENSIONS
    class Tools(Scripted):
        def complete(self, req, schema, settings):
            self.requests.append(req)
            if req['task'] == 'GENERATE_SOURCE_WARRANTED_CANDIDATES':
                units = req['source_packet']['units']
                value = dict(readings=[dict(local_id='candidate', family='scope', subject='Duty',
                    statement='Conditional duty', distinction='Consent matters', citations=[
                        {'unit_id':units[0]['unit_id'], 'quote':units[0]['text']}],
                    assumptions=[], questions=[], formalization=None)],
                    dimensions=[dict(dimension=d, status='AMBIGUOUS', source_unit_ids=[r['unit_id'] for r in units],
                        explanation='Requires review') for d in DIMENSIONS],
                    coverage=[dict(unit_id=r['unit_id'], status='CONTEXT', reason='Source retained') for r in units], questions=[])
            else:
                value = dict(arguments=[], attacks=[], preferences=[], cases=[], case_queries=[], questions=['Unresolved'])
            return Completion(value, {})
    class Backend:
        tools = ('bm25','legalruleml','pyarg')
        def identity(self): return {'version':'test'}
        def retrieval(self, packet, inputs, folder): return {'status':'PASS'}
        def candidates(self, packet, inputs, folder):
            assert list(inputs) == ['candidate']
            return {'status':'UNSUPPORTED'}
        def criticism(self, packet, inputs, folder):
            assert 'proposal' in inputs and 'evaluation' in inputs
            return {'status':'UNSUPPORTED'}
    p = product(tmp_path, Tools(), selected_tools=Backend.tools)
    p.tools('p14', envelope()['original_questions'][0], Backend(), findings=[])
    bindings = list((p.directory/'native').rglob('product-binding.json'))
    assert len(bindings) == 3
    assert all(json.loads(path.read_text())['binding']['capacity']['semantic_partition'] is False for path in bindings)
    second = BoundedProduct(tmp_path, tmp_path/'another-arm', p.provider, envelope(), list, limits=limits(),
        selected_tools=Backend.tools, shared_prefix=p.dispatch.directory, common_capacity_profile=policy.PROFILE)
    previous = len(p.provider.requests)
    second.tools('p14', envelope()['original_questions'][0], Backend(), findings=[])
    assert len(p.provider.requests) == previous
    assert len(list((second.directory/'native').rglob('product-binding.json'))) == 3


def test_input_exact_boundary_includes_schema_and_guidance(tmp_path):
    p = product(tmp_path)
    c = warrant(p, 1)
    measured = p.dispatch.measure(c['request'], c['schema'])
    p.route.limits = replace(p.route.limits, input_tokens=measured['local_tokens'], input_bytes=measured['bytes'])
    assert p.dispatch.measure(c['request'], c['schema'])['bytes'] == measured['bytes']
    p.route.limits = replace(p.route.limits, input_bytes=measured['bytes']-1)
    with pytest.raises(LegalMathError): p.dispatch.measure(c['request'], c['schema'])


def test_budget_profile_reaches_nonreference_transport(tmp_path):
    class SettingsCapture(Scripted):
        def complete(self, request, schema, settings):
            assert settings.max_output_bytes == policy.STAGES[request['task']].output_bytes
            return super().complete(request, schema, settings)
    p = product(tmp_path, SettingsCapture())
    assert run(p, warrant(p, 1))['status'] == 'VALIDATED'


def test_matched_comparison_routes_through_phases(tmp_path, monkeypatch):
    from scripts import legal_integration_campaign as campaign, legal_integration_phased_live as live
    from legalmath.interpretation.assurance.monitor import save
    class Comparison(Scripted):
        def complete(self, request, schema, settings):
            self.requests.append(request)
            assert request['task'] == 'ASSESS_MATCHED_TOOL_EFFECT'
            return Completion(dict(effect='insufficient', reason='Synthetic only', baseline_quote='Conditional duty',
                candidate_quote='Conditional duty', support=[], unresolved=['No legal claim'], tool_consideration='Retained'), {})
    for attr, value in [('ROOT',tmp_path), ('LIVE',Path('live')), ('ENVELOPE',Path('envelope.json')),
                        ('PROGRAM',Path('program.json')), ('TOKENIZER',Path('tokenizer'))]:
        monkeypatch.setattr(campaign, attr, value)
    monkeypatch.setattr(campaign, 'tokenizer', lambda _: list)
    monkeypatch.setattr(campaign, 'eligible_tools', lambda _: ['bm25'])
    monkeypatch.setattr(campaign, 'applicability_pairs', lambda: {('p14','bm25'):{'scope':'test'}})
    monkeypatch.setattr(campaign, 'validate_effect', lambda *args: None)
    monkeypatch.setattr(campaign, 'ref', lambda *args: {'path':'test','sha256':'test'})
    monkeypatch.setattr(live, 'phase_admit', lambda owner: lambda name,count: dict(name=name,count=count))
    save(tmp_path/'program.json', {'common_capacity':{'capacity_profile':policy.PROFILE}})
    save(tmp_path/'envelope.json', envelope())
    value = {'input_hash':'same', 'active_questions':['p14'], 'answers':{'p14':{'answer':{
        'status':'VALIDATED', 'value':{'conclusion':'Conditional duty'}}, 'tools':[], 'review_accepted':True}}}
    save(tmp_path/'live/arms/p14/baseline/result.json', value)
    save(tmp_path/'live/arms/p14/bm25/result.json', value)
    service = Comparison()
    result = campaign.compare('p14','bm25',service)
    assert result['result']['status'] == 'VALIDATED'
    assert service.requests[0]['capacity_profile'] == policy.PROFILE
    assert list((tmp_path/'live/comparisons/p14/bm25/capacity').glob('*/state.json'))


def test_exact_valid_answer_migrates_without_resampling(tmp_path):
    from legalmath.interpretation.assurance.integration_contract import evidence_file
    from legalmath.interpretation.assurance.monitor import save
    provider = Scripted()
    old = BoundedProduct(tmp_path, tmp_path/'old', provider, envelope(), list, limits=limits())
    question = envelope()['original_questions'][0]
    sources = [r for r in old.route.records.values() if r['kind'] == 'source']
    previous = old.note('answer-p14', 'ANSWER_ORIGINAL_QUESTION', question, sources, {}, ['one'])
    assert previous['status'] == 'VALIDATED'
    row = {n:evidence_file(old.dispatch.directory/'answer-p14'/(n+'.json'), tmp_path)
        for n in ('request','schema','result')}
    row.update(mode='VALIDATED', dispatch=evidence_file(old.dispatch.directory/'dispatch.json', tmp_path))
    save(tmp_path/'checkpoint.json', dict(profile='common-capacity-checkpoint.v1',
        input_hash=old.route.input_hash, calls={'answer-p14':row}))
    p = product(tmp_path, provider, phased=True, capacity_checkpoint=evidence_file(tmp_path/'checkpoint.json',tmp_path))
    used = len(provider.requests)
    value = p.note('answer-p14','ANSWER_ORIGINAL_QUESTION',question,sources,{},['one'])
    assert value['value'] == previous['value'] and len(provider.requests) == used
    assert value['provenance']['new_provider_calls'] == 0
    assert not (p.dispatch.directory/'dispatch.json').exists()
    assert p.note('answer-p14','ANSWER_ORIGINAL_QUESTION',question,sources,{},['one']) == value


def test_failed_semantic_checkpoint_is_not_resampled(tmp_path):
    from legalmath.interpretation.assurance.integration_contract import evidence_file
    from legalmath.interpretation.assurance.monitor import save
    p = product(tmp_path)
    call = warrant(p, 1)
    row = dict(mode='RETAINED_FAILURE')
    failure = dict(status='FAILED', error='E_SCHEMA', reason='Retained semantic rejection')
    for name,value in [('request',call['request']),('schema',call['schema']),('result',failure)]:
        save(tmp_path/(name+'.json'),value)
        row[name] = evidence_file(tmp_path/(name+'.json'),tmp_path)
    save(tmp_path/'checkpoint.json', dict(profile='common-capacity-checkpoint.v1',
        input_hash=p.route.input_hash, calls={'warrant':row}))
    p.capacity_checkpoint = evidence_file(tmp_path/'checkpoint.json',tmp_path)
    assert run(p,call) == failure and not p.provider.requests


def test_interrupted_shared_interpretation_cannot_move_to_another_arm(tmp_path):
    from legalmath.interpretation.assurance.phased.capacity_shared import execute as shared
    p = product(tmp_path)
    call = dict(key='candidates-p14',request=policy.annotate({'task':'GENERATE_SOURCE_WARRANTED_CANDIDATES'}),
        schema={},validate=lambda _:None)
    def crash(): raise RuntimeError('Interrupted before publication')
    with pytest.raises(RuntimeError): shared(p.capacity_manager,call,crash)
    second = BoundedProduct(tmp_path,tmp_path/'other',p.provider,envelope(),list,limits=limits(),
        shared_prefix=p.dispatch.directory, common_capacity_profile=policy.PROFILE)
    with pytest.raises(LegalMathError) as error:
        shared(second.capacity_manager,call,lambda:pytest.fail('Duplicate interpretation'))
    assert error.value.code == 'E_AUTHORITY' and not p.provider.requests


def test_native_retention_preserves_evidence_paths_and_detects_changes(tmp_path):
    from legalmath.interpretation.assurance.phased.capacity_checkpoint import native
    from legalmath.interpretation.assurance.integration_contract import evidence_file
    from legalmath.interpretation.assurance.monitor import save
    p = product(tmp_path)
    binding = dict(kind='retrieval',packet_hash='p',inputs_hash='i',backend={'version':'old'},capacity={})
    save(tmp_path/'native-evidence.json',{'hits':['remote exception']})
    value = dict(status='PASS',evidence=evidence_file(tmp_path/'native-evidence.json',tmp_path))
    save(tmp_path/'native-result.json',value)
    save(tmp_path/'native-binding.json',dict(status='COMPLETED',
        binding={k:v for k,v in binding.items() if k!='capacity'},result_hash=digest(value)))
    save(tmp_path/'checkpoint.json',dict(profile='common-capacity-checkpoint.v1',input_hash=p.route.input_hash,
        calls={},native=[dict(kind='retrieval',binding=evidence_file(tmp_path/'native-binding.json',tmp_path),
            result=evidence_file(tmp_path/'native-result.json',tmp_path))]))
    p.capacity_checkpoint = evidence_file(tmp_path/'checkpoint.json',tmp_path)
    assert native(p,binding) == value
    with pytest.raises(LegalMathError): native(p,{**binding,'inputs_hash':'changed'})
    save(tmp_path/'native-evidence.json',{})
    with pytest.raises(LegalMathError): native(p,binding)
