"""Selected complete-product route with explicit tools and acceptance sources.

This is callable product code. Provider authority and supported route limits
remain prerequisites; it does not create a grant or supply model responses.
"""
from pathlib import Path
from jsonschema.exceptions import ValidationError as SchemaValidationError

from legalmath.canonical import canonical, digest, loads
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation
from legalmath.interpretation.assurance import dossier_answer, investigation_answer, answer_evidence
from legalmath.interpretation.assurance import source_context
from legalmath.interpretation.assurance.sources import acquire_context, packet_from_context
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.assurance.route_admission import RouteBudgetProvider
from legalmath.interpretation.assurance.transport import CompactProvider
from scripts.legal_independent_tools import IndependentProductToolBackend


def prepare_bounded_context(envelope, tokenizer_path, *, limits=None):
    """Optional library-backed acquisition/review route; full legal acceptance remains open."""
    from legalmath.interpretation.assurance.bounded_context import ContextRoute, tokenizer
    return ContextRoute(envelope, tokenizer(tokenizer_path), limits=limits)


def run_bounded_context(envelope, tokenizer_path, provider, directory, *, limits=None):
    from legalmath.interpretation.assurance.bounded_context import citation_dependencies
    route = prepare_bounded_context(envelope, tokenizer_path, limits=limits)
    packets, blocked = route.reading_plan()
    dependencies, unresolved = citation_dependencies(envelope)
    bridge_packets, bridge_blocks = route.dependency_packets(dependencies)
    result = route.execute(packets + bridge_packets, provider, directory)
    result['blocked_inputs'] = blocked + bridge_blocks + unresolved
    result['complete_reading_established'] = False
    save(Path(directory) / 'result.json', result)
    return route, result


def run_product(root, directory, provider, jdk, at, *, sources, questions,
                acceptance_ref, qualification, required, deadline_utc,
                selected_tools, settings, consumer_profile='literal', maximum_answer_output_bytes=None,
                maximum_answer_fields=None, bounded_envelope=None, bounded_encode=None,
                bounded_limits=None, shared_prefix=None, active_questions=None, retained_initial=None,
                bounded_phase='answer', bounded_execution='standard', bounded_acquisition_ref=None,
                bounded_phase_admit=None, bounded_phase_identity=None,
                bounded_requirement_account_profile=None, bounded_requirement_account_recovery=None,
                bounded_requirement_account_input_profile=None,
                bounded_requirement_account_instruction_profile=None,
                bounded_requirement_account_capacity_profile=None,
                bounded_requirement_account_output_profile=None,
                bounded_downstream_input_profile=None,
                bounded_downstream_instruction_profile=None,
                bounded_downstream_capacity_profile=None,
                bounded_retained_preparation=None,
                bounded_common_capacity_profile=None,
                bounded_capacity_checkpoint=None,
                **investigation_options):
    root = Path(root).resolve(); directory = Path(directory).resolve()
    if not directory.is_relative_to(root):
        raise ValueError('Product evidence must remain in the worktree')
    if bounded_envelope is not None:
        from legalmath.interpretation.assurance.bounded_product import BoundedProduct, PROFILE
        from legalmath.interpretation.assurance.answer_acceptance import validate_manifest
        if consumer_profile != PROFILE or bounded_encode is None:
            raise LegalMathError('E_SCHEMA', details='Explicit bounded profile and tokenizer required')
        if bounded_envelope['original_questions'] != questions:
            raise LegalMathError('E_INTEGRITY', details='Bounded route changed original questions')
        if bounded_phase not in ('acquire', 'prepare', 'answer'):
            raise LegalMathError('E_SCHEMA', details='Unknown bounded product phase')
        validate_manifest(bounded_envelope['answer_acceptance'], questions, root)
        backend = IndependentProductToolBackend(selected_tools) if selected_tools else None
        if bounded_execution not in ('standard', 'phased'):
            raise LegalMathError('E_SCHEMA', details='Unknown bounded execution implementation')
        session_type, phase_options = BoundedProduct, {}
        if bounded_execution == 'phased':
            from legalmath.interpretation.assurance.phased.product import PhasedProduct
            if bounded_acquisition_ref is None or not callable(bounded_phase_admit) or not bounded_phase_identity:
                raise LegalMathError('E_AUTHORITY', details='Phased route requires exact retained acquisition and admission')
            session_type = PhasedProduct
            phase_options = {'phase_admit': bounded_phase_admit, 'phase_identity': bounded_phase_identity,
                'downstream_instruction_profile': bounded_downstream_instruction_profile,
                'downstream_capacity_profile': bounded_downstream_capacity_profile,
                'retained_preparation': bounded_retained_preparation}
        elif (bounded_acquisition_ref is not None or bounded_phase_admit is not None or
                bounded_phase_identity is not None or bounded_downstream_instruction_profile is not None
                or bounded_downstream_capacity_profile is not None or bounded_retained_preparation is not None):
            raise LegalMathError('E_SCHEMA', details='Phase options require explicit phased execution')
        session = session_type(root, directory, provider, bounded_envelope, bounded_encode,
            limits=bounded_limits, maximum_calls=required['maximum_calls'], selected_tools=selected_tools,
            maximum_corrections=required.get('maximum_corrections', 0),
            shared_prefix=shared_prefix, active_questions=active_questions, retained_initial=retained_initial,
            requirement_account_profile=bounded_requirement_account_profile,
            requirement_account_recovery=bounded_requirement_account_recovery,
            requirement_account_input_profile=bounded_requirement_account_input_profile,
            requirement_account_instruction_profile=bounded_requirement_account_instruction_profile,
            requirement_account_capacity_profile=bounded_requirement_account_capacity_profile,
            requirement_account_output_profile=bounded_requirement_account_output_profile,
            downstream_input_profile=bounded_downstream_input_profile,
            common_capacity_profile=bounded_common_capacity_profile,
            capacity_checkpoint=bounded_capacity_checkpoint, **phase_options)
        if bounded_execution == 'phased':
            session.install_dispatch_admission()
        session.trace.append('run_product')
        runner = CompleteInvestigation(root, directory / 'investigation', provider, jdk, at,
            settings=settings, optional_tool_backend=backend, **investigation_options)
        investigation = runner.run(sources, investigation_answer.question_text(questions),
            original_questions=questions, bounded_session=session, bounded_acquisition_ref=bounded_acquisition_ref)
        if bounded_phase == 'acquire': return investigation
        acquisition_ref = bounded_acquisition_ref or evidence_file(directory / 'investigation.json', root)
        return dossier_answer.propose(root, acquisition_ref,
            provider, directory / 'answer', investigation_directory=runner.directory,
            expected_revision=investigation['revision'], questions=questions,
            qualification_ref=None, bounded_session=session, bounded_backend=backend,
            bounded_preparation_only=bounded_phase == 'prepare')
    if required['stages'].get('answer_review') != 1:
        raise LegalMathError('E_AUTHORITY', details='Complete product requires one reserved final answer review')
    guard = RouteBudgetProvider(provider, directory / 'budget', required, required['stages'],
                                deadline_utc, continue_settled_failures=True)
    guard.check()
    backend = IndependentProductToolBackend(selected_tools) if selected_tools else None
    runner = CompleteInvestigation(root, directory / 'investigation', guard, jdk, at,
        settings=settings, optional_tool_backend=backend,
        optional_tool_failures='continue-independent', **investigation_options)
    selected = investigation_answer.question_text(questions)
    packet = packet_from_context(acquire_context(sources, max_documents=settings.max_documents,
        max_depth=settings.max_reference_depth), selected)
    save(directory / 'prepared-packet.json', packet)
    bound_qualification = {
        'profile': 'investigation-answer-source-qualification.v1', 'source_packet_hash': digest(packet),
        'limitations': qualification['limitations'],
        'evidence': qualification['evidence'] or [evidence_file(directory / 'prepared-packet.json', root)],
        'details': qualification.get('details', {})}
    save(directory / 'source-qualification.json', bound_qualification)
    context = source_context.prepare(root, sources, packet, bound_qualification)
    save(directory / 'qualified-source-context.json', context)
    if consumer_profile != 'literal':
        from legalmath.interpretation.assurance.answer_transport import final_review_budget, PROFILE
        from legalmath.interpretation.assurance.answer_acceptance import validate_manifest
        from legalmath.interpretation.assurance.integration_contract import read_evidence
        if consumer_profile != PROFILE:
            raise LegalMathError('E_SCHEMA', details='Unknown consumer profile')
        manifest = read_evidence(acceptance_ref, root)
        validate_manifest(manifest, questions, root)
        minimum = {'task':'MINIMUM_PRODUCT_CONTEXT', 'source_packet':packet,
                   'source_qualification':bound_qualification, 'original_questions':questions,
                   'answer_acceptance':manifest}
        preflight = final_review_budget(minimum, answer_bytes=maximum_answer_output_bytes,
            answer_fields=maximum_answer_fields, maximum_input_bytes=runner.downstream_settings.max_input_bytes)
        preflight['scope'] = ('Conservative reservation screen on the declared source/acceptance context. '
            'A refusal means this configuration is unqualified, not that every fuller adaptive encoding is larger. '
            'The actual dossier and final review are checked again before consumer dispatch.')
        save(directory/'minimum-consumer-preflight.json', preflight)
        if not preflight['admitted']:
            raise LegalMathError('E_RESOURCE_LIMIT', details={'stage':'MINIMUM_FINAL_REVIEW', **preflight})
    dossier = runner.run(sources, selected, original_questions=questions, source_context=context)
    dossier_ref = evidence_file(runner.directory / 'revisions' / dossier['revision'] / 'dossier.json', root)
    result = dossier_answer.propose(root, dossier_ref, guard, directory / 'answer',
        investigation_directory=runner.directory, expected_revision=dossier['revision'],
        questions=questions, qualification_ref=evidence_file(directory / 'source-qualification.json', root),
        acceptance_ref=acceptance_ref, dispatch_guard=guard.check,
        continue_independent_reviews=True, raw_evidence_policy='complete',
        maximum_extra_dependency_bytes=0, input_profile=consumer_profile,
        maximum_answer_output_bytes=maximum_answer_output_bytes, maximum_answer_fields=maximum_answer_fields)
    review = {'status':'DEPENDENCY_BLOCKED', 'reason':'Requires a structurally valid synthesis'}
    if result['status'] == 'STRUCTURALLY_VALID_PROPOSAL':
        request = loads((directory / 'answer/answer-review-request.json').read_bytes())
        def unchanged():
            guard.check()
            current = investigation_answer.prepare_request(root, dossier_ref, investigation_directory=runner.directory,
                expected_revision=dossier['revision'], questions=questions,
                qualification_ref=evidence_file(directory / 'source-qualification.json',root), acceptance_ref=acceptance_ref)
            if current != request['context']:
                raise LegalMathError('E_STALE_REVIEW', details='Evidence changed during final answer review')
        try:
            unchanged()
            limits = runner.downstream_settings
            if dossier_answer.wire_size(request, input_profile=consumer_profile) > limits.max_input_bytes:
                raise LegalMathError('E_RESOURCE_LIMIT', details={'stage':'FINAL_ANSWER_REVIEW',
                    'bytes':dossier_answer.wire_size(request, input_profile=consumer_profile),'limit':limits.max_input_bytes})
            from legalmath.interpretation.assurance.answer_transport import AnswerProvider, enforce_final_review_budget
            if consumer_profile != 'literal':
                enforce_final_review_budget(request, loads((directory/'answer/final-review-budget.json').read_bytes()))
            transport = CompactProvider if consumer_profile == 'literal' else AnswerProvider
            response = transport(guard, directory / 'answer-review-transport').complete(
                request, answer_evidence.review_schema(request), limits)
            save(directory / 'answer-review-raw.json', {'value':response.value,'provenance':response.provenance})
            if len(canonical(response.value)) > limits.max_output_bytes:
                raise LegalMathError('E_RESOURCE_LIMIT', details='Final review output exceeds declared bound')
            unchanged()
            checked = answer_evidence.validate_review(response.value, request)
            save(directory / 'answer-review-validated.json', checked)
            review = {'status':response.value['verdict'], 'structurally_valid':True,
                      'result':evidence_file(directory / 'answer-review-validated.json',root)}
        except (LegalMathError, ValueError, OSError, SchemaValidationError) as exc:
            review = {'status':'REJECTED', 'error':getattr(exc,'code',type(exc).__name__),
                      'details':getattr(exc,'details',str(exc))}
    summary = {'investigation_complete': dossier['execution_complete'], 'answer': result,
        'final_review':review,
        'selected_tools': list(selected_tools), 'legal_correctness_established': False,
        'actual_product_route': True, 'provider_live': provider.live}
    save(directory / 'result.json', summary)
    return summary
