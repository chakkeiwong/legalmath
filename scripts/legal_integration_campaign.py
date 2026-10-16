"""Fixed campaign preparation and execution for the registered integration master.

No action in this module infers a grant from an expired historical allowance.
Dynamic populations are admitted against finite stage caps before descendants.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import fcntl
import json
import os
import subprocess
import time

from scripts.legal_integration_master import (ROOT, BASE, DOC, PROGRAM, STATE, PLAN,
    TOKENIZER, RULES, QUESTIONS, TOOLS, MasterExecution, ref, read, save, require)
from legalmath.canonical import canonical, digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_context import ContextRoute, Limits, tokenizer
from legalmath.interpretation.assurance.bounded_product import BoundedProduct, NOTE, AUDIT, PROFILE
from legalmath.interpretation.assurance.bounded_provider import BoundedCodexProvider
from scripts.legal_product_completion import run_product

LIVE = BASE / 'live'
LIMITS = Limits()
ENVELOPE = BASE / 'combined-envelope.json'
CANARIES = BASE / 'canaries'
RESOURCES = BASE / 'resource-envelope.json'
ARM_BUFFER = 32
COMMON_CAP = 320
SOURCE_REVIEW_GROUP_MINIMUM = 1
CALL_TIMEOUT = 120
MAXIMUM_CALLS = 8100
WINDOW_SECONDS = 6 * 24 * 3600
MAXIMUM_CORRECTIONS = 0  # Opt in only in a reviewed current campaign.


def provider():
    return BoundedCodexProvider(ROOT, ROOT / BASE, tokenizer(ROOT / TOKENIZER), LIMITS,
        routing_file=ROOT / BASE / 'campaign-routing.toml')


def session(directory, service, *, questions=QUESTIONS, tools=(), shared=None, maximum=8100, downstream_input_profile=None):
    return BoundedProduct(ROOT, directory, service, read(ROOT / ENVELOPE),
        tokenizer(ROOT / TOKENIZER), limits=LIMITS, maximum_calls=maximum,
        maximum_corrections=MAXIMUM_CORRECTIONS,
        active_questions=questions, selected_tools=tools, shared_prefix=shared, downstream_input_profile=downstream_input_profile)


def product(directory, service, *, q=None, tool=None, phase='answer', shared=None, maximum=8100,
            questions=None):
    envelope = read(ROOT / ENVELOPE)
    return run_product(ROOT, directory, service, ROOT / '/unused-jdk', '2026-10-13T00:00:00Z',
        sources=[], questions=envelope['original_questions'], acceptance_ref=None, qualification={},
        required={'maximum_calls': maximum, 'maximum_corrections': MAXIMUM_CORRECTIONS},
        deadline_utc=read(ROOT / BASE / 'live-grant.json')['deadline_utc'],
        selected_tools=[] if tool is None else [tool], settings=None, consumer_profile=PROFILE,
        bounded_envelope=envelope, bounded_encode=tokenizer(ROOT / TOKENIZER), bounded_limits=LIMITS,
        active_questions=questions if questions is not None else QUESTIONS if q is None else [q],
        shared_prefix=shared, bounded_phase=phase)


def prepare():
    from legalmath.interpretation.search.providers import CodexProvider
    from scripts.legal_integration_rehearsal import UnresolvedProvider
    root = ROOT / BASE
    require(not (root / 'live-grant.json').exists(), 'Do not change an approved campaign')
    current = CodexProvider().routing
    # Retain the configured service endpoint but explicitly select the model
    # requested by the user and previously canary-tested in this mission.
    lines = ['model = "gpt-6.1-sol"', 'model_provider = ' + json.dumps(current['provider'])]
    if current['fields']:
        lines.append('[model_providers.' + current['provider'] + ']')
        for key, value in current['fields'].items():
            lines.append(key + ' = ' + (str(value).lower() if type(value) is bool else json.dumps(value)))
    (root / 'campaign-routing.toml').write_text('\n'.join(lines) + '\n')
    service = provider()
    dry = session(root / 'request-preparation', UnresolvedProvider())
    packets, blocked = dry.route.reading_plan()
    from legalmath.interpretation.assurance.bounded_context import citation_dependencies
    bridges, bridge_blocks = dry.route.dependency_packets(citation_dependencies(dry.route.envelope)[0])
    require(not blocked and not bridge_blocks, 'Unqualified acquisition records')
    measurements = [service.measure(p['request'], p['schema']) for p in packets + bridges]
    canaries = []
    for q in dry.route.envelope['original_questions']:
        qid = q['question_id']
        ids = dry.route.retrieve(q['text'], expand=False)['record_ids'][:2]
        packet = dry.route.make_packet('READ_SOURCE', ids, question_ids=[qid], reader='service-canary')
        # Deliberately overbroad conclusion tests the review's ability to refuse
        # promotion. This is a control input, not an asserted legal answer.
        assignment = {'conclusion': 'A recorded action alone conclusively establishes full compliance; '
            'no further legal standard, contrary passage or client fact matters.',
            'control': 'Deliberately unsupported overstatement; evaluate against the supplied sources.'}
        request = dry.request('AUDIT_ANSWER_AGAINST_SOURCE', q, [dry.route.records[i] for i in ids],
                              payload=assignment, expected=ids)
        row = {'question': qid, 'reading': packet, 'review_request': request, 'review_schema': AUDIT,
               'reading_measurement': service.measure(packet['request'], packet['schema']),
               'review_measurement': service.measure(request, AUDIT)}
        save(root / 'canaries' / (qid + '.json'), row)
        canaries.append(ref(ROOT, root / 'canaries' / (qid + '.json')))
    populations = {}
    source_count = sum(r['kind'] == 'source' for r in dry.route.records.values())
    for q in QUESTIONS:
        count = sum(r['kind'] in ('obligation', 'reading', 'case') and dry.applicable(r, q)
                    for r in dry.route.records.values())
        populations[q] = {'requirements': count, 'source_chunks': source_count,
            'common_call_cap': 320, 'answer_call_cap': count + source_count + 32,
            'comparison_call_cap': 6, 'arms': ['baseline', *TOOLS]}
    rehearsal = root / 'original-rehearsal-final/rehearsal-summary.json'
    from scripts.legal_mission_execution import verify
    for reference in read(rehearsal)['implementation']: verify(ROOT, reference)
    result = read(root / 'original-rehearsal-final/result.json')
    require(set(result['answers']) == set(QUESTIONS) and
            all(a.get('answer', {}).get('status') == 'VALIDATED' for a in result['answers'].values()),
            'Original-input rehearsal did not reach every answer')
    from legalmath.interpretation.search.schema import validate_output_schema
    schemas = list((root / 'original-rehearsal-final/calls').glob('*/schema.json'))
    for path in schemas: validate_output_schema(read(path))
    # Resource caps are finite hypotheses, not promises that arbitrary generated
    # populations will fit. Rebudgeting explicitly refuses unsupported demand.
    scope = {'acquisition': len(packets) + len(bridges), 'canaries': 8,
        'common_preparation': 4 * 320,
        'answer_nominal_from_rehearsal': 7 * sum(len(a['reviews']) + 3 for a in result['answers'].values()),
        'comparisons': 24 * 6, 'cross_question_reviews': 7 * 6}
    nominal = scope['acquisition'] + scope['canaries'] + scope['common_preparation'] + \
        scope['answer_nominal_from_rehearsal'] + scope['comparisons'] + scope['cross_question_reviews']
    conservative = scope['acquisition'] + scope['canaries'] + scope['common_preparation'] + \
        7 * sum(p['answer_call_cap'] for p in populations.values()) + scope['comparisons'] + scope['cross_question_reviews']
    require(conservative <= MAXIMUM_CALLS, 'Declared entire campaign exceeds total cap')
    save(root / 'resource-envelope.json', {'scope': scope, 'total_nominal_with_common_caps': nominal,
        'conservative_sum_of_stage_caps': conservative,
        'global_ceiling': MAXIMUM_CALLS, 'populations': populations,
        'per_call_timeout_seconds': CALL_TIMEOUT, 'parallel_workers': 2,
        'window_seconds': WINDOW_SECONDS, 'input_output_limits': asdict(LIMITS),
        'maximum_acquisition_input_tokens': max(m['local_tokens'] for m in measurements),
        'original_rehearsal_schemas_checked': len(schemas),
        'uncertainty': 'Real findings can require more reduction or review work than scripted outputs. '
            'The actual population is re-budgeted before each answer phase; no silent scope reduction.',
        'deadline_policy': 'Check sufficient remaining time for the admitted stage at the call timeout. '
            'The clock and global ceiling both bind; unused calls never extend the clock.'})
    bindings = [ref(ROOT, p) for p in (PROGRAM, PLAN, RULES, BASE / 'combined-envelope.json', BASE / 'applicability.json',
        BASE / 'campaign-routing.toml', BASE / 'resource-envelope.json', rehearsal,
        DOC / 'integration-master-execution-review.md',
        Path('scripts/legal_integration_master.py'), Path('scripts/legal_integration_campaign.py'),
        Path('scripts/legal_product_completion.py'),
        Path('src/legalmath/interpretation/assurance/bounded_product.py'),
        Path('src/legalmath/interpretation/assurance/bounded_provider.py'),
        Path('src/legalmath/interpretation/assurance/bounded_context.py'))]
    # Freeze the actual dirty implementation, not merely a git commit that
    # predates these files. Dependencies include the provider and native adapters.
    implementation = [ref(ROOT, p) for p in sorted((ROOT / 'src/legalmath').rglob('*.py'))]
    implementation += [ref(ROOT, ROOT / p) for p in ('scripts/legal_independent_tools.py',
        'scripts/legal_integration_tools.py', 'requirements-context.lock')]
    save(root / 'implementation-manifest.json', {'files': implementation,
        'interpreter': str(ROOT / '.venv-context/bin/python'), 'devices': 'CPU; CUDA_VISIBLE_DEVICES=-1',
        'model': service.routing['model'], 'seed': 'N/A: no service seed control; matched effects are case-specific'})
    bindings += implementation
    proposal = {'profile': 'integration-master-approval-proposal.v1', 'dispatch_ready': True,
        'maximum_calls': MAXIMUM_CALLS, 'window_seconds': WINDOW_SECONDS,
        'routing': service.routing, 'routing_hash': digest(service.routing), 'bindings': bindings + canaries,
        'historical_calls': 41, 'historical_grant_reused': False, 'live_authorized': False,
        'command': '.venv-context/bin/python scripts/legal_integration_master.py approve-and-run',
        'resume_command': '.venv-context/bin/python scripts/legal_integration_master.py live',
        'installation_target': str(Path.home() / '.codex/rules/legalmath-integration-master.rules'),
        'host_rules': ref(ROOT, RULES), 'all_stages': scope,
        'scope': 'Four original questions; complete source acquisition; six isolated tool arms each; '
            'matched assessments and terminal release review. Finite stage caps can leave named work open.',
        'provider_cost': 'Existing configured account/route; no inspected authoritative price schedule. '
            'Ceiling bounds calls, not a monetary charge or hidden reasoning tokens.',
        'source_renderer_installation': {
            'command': 'sudo -n apt-get install --no-install-recommends -y libreoffice-writer',
            'packages': 11, 'download_megabytes': '16.0', 'installed_megabytes': '59.5',
            'purpose': 'Provide the missing Word importer/rendering component for original judgment verification.',
            'failure_policy': 'No interactive password prompt; retain installation failure and continue independent product work.'},
        'review': 'Local qualification and scripted rehearsal support execution mechanics only; '
            'canaries, generated-population capacity, source semantics and tool effects remain live tests.'}
    save(root / 'approval-proposal.json', proposal)
    return proposal


def approve():
    """Called only by the separately approved grouped host action."""
    from scripts.legal_integration_master import install_rules
    proposal = read(ROOT / BASE / 'approval-proposal.json')
    require(proposal['dispatch_ready'], 'Proposal not prepared')
    for item in proposal['bindings']:
        from scripts.legal_mission_execution import verify
        verify(ROOT, item)
    require(not (ROOT / BASE / 'live-grant.json').exists(), 'Existing grant must be resumed, never renewed')
    now = datetime.now(timezone.utc)
    local_deadline = datetime.fromisoformat(read(ROOT / PROGRAM)['deadline_utc'])
    require(now + timedelta(seconds=proposal['window_seconds']) <= local_deadline,
            'Proposed service window no longer fits local scheduling deadline; revise the concrete proposal')
    installed = install_rules()
    save(ROOT / BASE / 'live-grant.json', {'profile': 'integration-master-live-grant.v1',
        'approved': True, 'approval_text': 'User approved the grouped approve-and-run action and its '
            'bound proposal, rules installation, model, call ceiling and service window.',
        'proposal': ref(ROOT, BASE / 'approval-proposal.json'), 'maximum_calls': proposal['maximum_calls'],
        'routing_hash': proposal['routing_hash'], 'started_utc': now.isoformat(),
        'deadline_utc': (now + timedelta(seconds=proposal['window_seconds'])).isoformat(), 'rules': installed})
    renderer = ['apt-get', 'install', '--no-install-recommends', '-y', 'libreoffice-writer']
    if os.geteuid() != 0: renderer = ['sudo', '-n', *renderer]
    try:
        outcome = subprocess.run(renderer, cwd=ROOT, capture_output=True, text=True, timeout=300)
        evidence = {'command': renderer, 'returncode': outcome.returncode, 'output': outcome.stdout + outcome.stderr}
    except Exception as exc:
        evidence = {'command': renderer, 'error': str(exc)}
    save(ROOT / BASE / 'renderer-installation.json', evidence)


def complete_node(execution, tid, function):
    from scripts.legal_mission_execution import process_identity, process_alive
    with execution.locked() as state:
        row = state['tasks'][tid]
        resuming = row['status'] == 'RUNNING'
        if resuming:
            require(row.get('master_live') and not process_alive(row.get('live_supervisor')),
                    'Live node still has an owner or lacks a resumable reservation')
            number = len(row['attempts'])
    if not resuming: number = execution.start(tid)
    with execution.locked() as state:
        state['tasks'][tid].update(master_live=True, live_supervisor=process_identity(__import__('os').getpid()))
        save(execution.state_path, state)
    directory = ROOT / BASE / tid / ('attempt-' + str(number))
    directory.mkdir(parents=True, exist_ok=True)
    began = time.monotonic()
    try:
        value = function()
        status = value.pop('_node_status', 'SUCCEEDED')
        conclusion = value.pop('_conclusion', tid + ' execution evidence retained; acceptance remains scoped.')
    except Exception as exc:
        status = 'FAILED'
        value = {'error': getattr(exc, 'code', type(exc).__name__),
                 'reason': str(getattr(exc, 'details', None) or exc)}
        if isinstance(exc, LegalMathError) and exc.code in {'E_AUTHORITY', 'E_INTEGRITY'}:
            value['continuation_veto'] = True
        conclusion = tid + ' failed: ' + value['reason'][:500]
    save(directory / 'evidence.json', value)
    if value.get('continuation_veto'):
        execution.record_continuation_veto(value['error'], value['reason'],
            [ref(ROOT, directory / 'evidence.json')], live_consumers(execution))
    save(directory / 'result.json', {'task_id': tid, 'status': status, 'conclusion': conclusion,
        'next_action': 'Refresh and continue independent ready nodes; preserve every failed dependency.',
        'evidence': [ref(ROOT, directory / 'evidence.json')], 'plan': str(PLAN),
        'wall_seconds': time.monotonic() - began, 'legal_acceptance': False})
    execution.finish(tid, directory / 'result.json')
    return value


def live_consumers(execution):
    return [tid for tid in execution.tasks if tid == 'live-approval'
            or tid.startswith(('acquire-', 'baseline-', 'tool-', 'compare-'))]


def applicability_pairs():
    from scripts.legal_integration_acceptance import validate_applicability, current_register
    from scripts.legal_mission_execution import verify
    reference = current_register(read(ROOT / PROGRAM), 'applicability')
    require(reference, 'Reviewed applicability register required before product trials')
    verify(ROOT, reference)
    return validate_applicability(read(ROOT / reference['path']), ROOT)


def eligible_tools(question):
    pairs = applicability_pairs()
    return [tool for tool in TOOLS if pairs[question, tool]['decision'] == 'applicable']


def block_failed_preflight(execution, outcomes, semantic_ok, evidence):
    for question in QUESTIONS:
        tid = 'acquire-' + question
        if tid in execution.summary()['ready'] and (not semantic_ok or not outcomes[question]['passed']):
            reason = ('Semantic preservation prerequisite did not qualify; acquisition was not dispatched.'
                      if not semantic_ok else 'Question service canary failed; acquisition was not dispatched.')
            execution.block_before_dispatch(tid, reason, evidence,
                shared_scope=live_consumers(execution) if not semantic_ok else [tid])


def validate_canary_read(product, packet, value):
    return product.route.validate_response(packet, value,
        decoded=getattr(product.provider, 'reference_transport', False))


def canaries(service):
    revision = read(ROOT/PROGRAM).get('canary_validation_repair')
    if revision:
        from scripts.legal_integration_canary_validation import revalidate
        return revalidate(service, ROOT/LIVE, revision['canaries'])
    outcomes = {}
    dry = session(ROOT / LIVE / 'canaries', service, maximum=8)
    for q in QUESTIONS:
        inputs = read(ROOT / CANARIES / (q + '.json'))
        try:
            packet = inputs['reading']
            reading = dry.dispatch.call('canary-read-' + q, packet['request'], packet['schema'],
                lambda v, p=packet: validate_canary_read(dry, p, v))
            request = inputs['review_request']
            def check(value):
                require(set(value['considered']) == set(request['required_considered']), 'Canary lost source coverage')
                dry.citations(value, request['records'])
                require(value['verdict'] != 'ACCEPT', 'Reviewer accepted deliberately unsupported compliance')
            review = dry.dispatch.call('canary-review-' + q, request, AUDIT, check)
            outcomes[q] = {'reading': reading, 'review': review,
                'passed': reading['status'] == review['status'] == 'VALIDATED'}
        except Exception as exc:
            if isinstance(exc, LegalMathError) and exc.code in ('E_AUTHORITY', 'E_INTEGRITY'):
                save(ROOT / LIVE / 'canary-results.json', {**outcomes, q: {
                    'passed': False, 'continuation_veto': True, 'reason': str(exc)}})
                raise
            outcomes[q] = {'passed': False, 'reason': str(getattr(exc, 'details', None) or exc)}
        save(ROOT / LIVE / 'canary-results.json', outcomes)
    return outcomes


def arm_call_budget(requirements, sources, dependencies, *, maximum_corrections=0,
                    observed_construction_calls=0):
    require(maximum_corrections in (0, 1), 'Unreviewed correction count')
    require(all(type(n) is int and n >= 0 for n in
                (requirements, sources, dependencies, observed_construction_calls)),
            'Invalid generated review population')
    # One source per request bounds the adaptive review grouping. Dependency
    # reviews include unresolved items, not just proposed successful resolutions.
    reviews = requirements + sources + dependencies
    construction = max(ARM_BUFFER, observed_construction_calls * 2)
    initial = reviews + construction
    account_corrections = requirements if maximum_corrections else 0
    warrant_assessments = reviews if maximum_corrections else 0
    correction = initial + account_corrections + warrant_assessments if maximum_corrections else 0
    return {'review_calls': reviews, 'construction_allowance': construction,
            'observed_construction_calls': observed_construction_calls,
            'correction_reserve': correction, 'account_correction_reserve': account_corrections,
            'warrant_assessment_reserve': warrant_assessments,
            'maximum_corrections': maximum_corrections,
            'maximum_calls': initial + correction}


def acquire(q, service):
    from legalmath.interpretation.assurance.phased.evidence_store import load_exact
    require(read(ROOT / LIVE / 'canary-results.json')[q]['passed'], 'Question service canary failed')
    common = ROOT / LIVE / 'common' / q
    acquisition = load_exact(ROOT / LIVE / 'acquisition/investigation.json')
    require(acquisition['question_acquisition_complete'][q], 'Relevant source acquisition failed')
    scope_probe=session(common,service,questions=[q],maximum=COMMON_CAP)
    findings = sum(q in scope_probe.acquisition_questions(scope_probe.route.records[record['id']])
        for output in acquisition['outputs'] if output['result']['status'] == 'VALIDATED'
        for record in output['result']['value']['records'])
    # Establish a smallest feasible lower bound before spending on common
    # preparation. An actual adaptive upper bound is enforced by the stage cap.
    envelope = read(ROOT / ENVELOPE)
    count = sum(q in record.get('question_ids', QUESTIONS)
        for field in ('acceptance_obligations', 'original_readings', 'cases')
        for record in envelope['answer_acceptance'][field])
    minimum = count + max(0, (findings + count - 1 + 4) // 5) + 2
    common.mkdir(parents=True, exist_ok=True)
    save(common / 'acquisition-rebudget.json', {'actual_finding_records': findings,
        'applicable_requirements': count, 'minimum_common_calls': minimum, 'common_cap': COMMON_CAP,
        'role': 'Capacity refusal screen; a passing lower bound does not prove fit. '
                'Every actual request and adaptive expansion remains bounded and retained.'})
    require(minimum <= COMMON_CAP, 'Actual population cannot fit even the minimum common-stage demand')
    outcome = product(common, service, q=q, phase='prepare', shared=ROOT / LIVE / 'acquisition/calls', maximum=COMMON_CAP)
    require(outcome['answers'][q].get('status') == 'PREPARED', 'Question common preparation failed')
    prepared = read(common / 'preparation.json')[q]
    # The actually generated summary, original mapping and native-independent
    # candidates now exist. Reserve maximum answer output plus reviewer input.
    probe = session(common, service, questions=[q], shared=ROOT / LIVE / 'acquisition/calls', maximum=COMMON_CAP)
    question = next(row for row in probe.route.envelope['original_questions'] if row['question_id'] == q)
    review_reservations = []
    for detail in read(common / 'requirement-details.json'):
        if not probe.applicable(probe.route.records[detail['id']], q): continue
        material = {'answer': None, 'requirement': probe.route.records[detail['id']],
                    'detailed_account': detail['result']['value']}
        request = probe.request('AUDIT_ANSWER_AND_DETAILED_ACCOUNT', question,
            probe.source_records(material), payload=material, expected=[detail['id']])
        measurement = probe.dispatch.measure(request, AUDIT)
        reservation = {'id': detail['id'], 'tokens': max(measurement['local_tokens'],
                       measurement['provider']['local_tokens']) + LIMITS.output_tokens + 64,
                       'bytes': max(measurement['bytes'],measurement['provider']['bytes']) + LIMITS.output_bytes + 256}
        review_reservations.append(reservation)
    source_records = [r for r in probe.route.records.values() if r['kind']=='source'
                      and q in probe.acquisition_questions(r)]
    # Check every adjacent pair, including starts after odd-sized greedy groups.
    for start in range(len(source_records)):
        group = source_records[start:start+SOURCE_REVIEW_GROUP_MINIMUM]
        request = probe.request('AUDIT_ANSWER_AGAINST_SOURCE',question,group,payload=None,
                                expected=[r['id'] for r in group])
        measurement = probe.dispatch.measure(request,AUDIT)
        review_reservations.append({'id':'source-group-'+str(start),
            'tokens':max(measurement['local_tokens'],measurement['provider']['local_tokens'])+LIMITS.output_tokens+64,
            'bytes':max(measurement['bytes'],measurement['provider']['bytes'])+LIMITS.output_bytes+256})
    save(common / 'review-output-reservations.json', review_reservations)
    require(all(r['tokens'] <= LIMITS.input_tokens and r['bytes'] <= LIMITS.input_bytes
                for r in review_reservations), 'Actual detail plus maximum answer cannot fit mandatory review')
    count = len(prepared['requirement_ids'])
    dependencies = [r for r in load_exact(common/'investigation.json').get('discovered_dependencies', [])
                    if r['question_id'] == q]
    observed_construction = sum(p.name.startswith(('reduce-', 'candidates-', 'criticism-'))
                                for p in (common/'calls').iterdir() if p.is_dir() and (p/'result.json').exists())
    arm_budget = arm_call_budget(count, len(source_records), len(dependencies),
        maximum_corrections=MAXIMUM_CORRECTIONS, observed_construction_calls=observed_construction)
    bound = arm_budget['maximum_calls']
    state = service.check()
    remaining = state['maximum'] - len(state['calls'])
    tools = eligible_tools(q)
    downstream_bound = (1 + len(tools)) * bound + 6 * len(tools)
    require(remaining >= bound, 'No single complete answer arm fits the remaining campaign')
    seconds = (datetime.fromisoformat(read(ROOT / BASE / 'live-grant.json')['deadline_utc']) -
               datetime.now(timezone.utc)).total_seconds()
    require(seconds >= bound * CALL_TIMEOUT + 305,
            'Insufficient deadline headroom for one complete answer arm')
    value = {'question': q, 'common_result': ref(ROOT, common / 'result.json'),
        'maximum_calls_each_arm': bound, 'arm_budget': arm_budget,
        'actual_dependency_population': [r['id'] for r in dependencies],
        'all_arms_fit_remaining_calls': remaining >= downstream_bound,
        'actual_requirement_population': prepared['requirement_ids'],
        'remaining_campaign_calls': remaining, 'review_reservations': ref(ROOT, common / 'review-output-reservations.json'),
        'eligible_tools': tools, 'downstream_call_bound': downstream_bound,
        'next': 'Independent complete baseline and applicable tool arms; unresolved pairs remain open'}
    save(common / 'downstream-budget.json', value)
    return value


def answer(q, tool, service):
    if tool is not None:
        require(tool in eligible_tools(q), 'Tool lacks reviewed applicability and warranted target')
    common = ROOT / LIVE / 'common' / q
    budget = read(common / 'downstream-budget.json')['maximum_calls_each_arm']
    directory = ROOT / LIVE / 'arms' / q / (tool or 'baseline')
    outcome = product(directory, service, q=q, tool=tool, shared=common / 'calls', maximum=budget)
    row = outcome['answers'][q]
    require(row.get('answer', {}).get('status') == 'VALIDATED', 'Product did not produce a valid question answer')
    # Baseline semantic validity gates comparisons, not independent candidates.
    return {'question': q, 'tool': tool, 'product': ref(ROOT, directory / 'result.json'),
        'review_accepted': row['review_accepted'],
        '_node_status': 'SUCCEEDED' if tool is not None or row['review_accepted'] else 'FAILED',
        '_conclusion': ('Product answer retained. ' + ('Source review accepted the baseline.'
            if row['review_accepted'] else 'Review has open or rejected conclusions; no promotion.'))}


def validate_effect(value, baseline, candidate, evaluator, sources):
    require(value['baseline_quote'].strip() and value['candidate_quote'].strip() and
            value['baseline_quote'] in baseline['answer']['value']['conclusion'] and
            value['candidate_quote'] in candidate['answer']['value']['conclusion'],
            'Fabricated or empty answer comparison')
    evaluator.citations(value, sources)
    require(value['support'] or value['effect'] == 'insufficient', 'Effect lacks source support')
    if value['effect'] != 'insufficient':
        require(baseline.get('review_accepted'), 'Effect verdict requires an accepted baseline')
        if value['effect'] == 'harmful' and not candidate.get('review_accepted'):
            reviews = candidate.get('reviews', [])
            require(reviews and all(r.get('status') == 'VALIDATED' for r in reviews),
                    'Broken review machinery cannot establish harm')
            adverse = [r['value'] for r in reviews if r['value'].get('verdict') == 'REJECT']
            require(adverse and all(r.get('support') and r.get('issues') for r in adverse),
                    'Harm requires a valid source-supported adverse review')
            for review in adverse:
                evaluator.citations(review, sources)
        else:
            require(candidate.get('review_accepted'), 'Effect verdict requires an accepted candidate')
        require(not value['unresolved'], 'Unresolved assessment cannot establish a tool effect')
        native = [r for r in candidate.get('tools', []) if r['id'].startswith('tool-')]
        require(native and all(r['value'].get('status') == 'PASS' for r in native),
                'Failed or unsupported native input cannot establish a tool effect')


def compare(q, tool, service):
    from legalmath.interpretation.assurance.phased.evidence_store import load_exact
    require(tool in eligible_tools(q), 'Comparison lacks reviewed applicability')
    from legalmath.interpretation.assurance.bounded_product import obj, array, TEXT, QUOTE
    baseline_path = ROOT / LIVE / 'arms' / q / 'baseline/result.json'
    candidate_path = ROOT / LIVE / 'arms' / q / tool / 'result.json'
    if not candidate_path.exists():
        return {'_node_status': 'BLOCKED', 'effect': 'INSUFFICIENT_EVIDENCE',
                '_conclusion': 'Candidate failed before a matched answer existed.'}
    baseline_result,candidate_result=load_exact(baseline_path),load_exact(candidate_path)
    require(baseline_result['input_hash']==candidate_result['input_hash']
            and baseline_result['active_questions']==candidate_result['active_questions']==[q],
            'Comparison source/question identities differ')
    baseline, candidate = baseline_result['answers'][q], candidate_result['answers'][q]
    require(baseline.get('review_accepted'), 'Comparison requires valid baseline')
    require(candidate.get('answer', {}).get('status') == 'VALIDATED', 'Candidate answer invalid')
    revision = read(ROOT / PROGRAM).get('repair_execution')
    evaluator = session(ROOT / LIVE / 'comparisons' / q / tool, service, questions=[q], maximum=6,
        downstream_input_profile=revision['downstream_input_profile'] if revision else None)
    question = next(v for v in evaluator.route.envelope['original_questions'] if v['question_id'] == q)
    schema = obj({'effect': {'type': 'string', 'enum': ['helps', 'no_benefit', 'harmful', 'limited', 'insufficient']},
        'reason': TEXT, 'baseline_quote': TEXT, 'candidate_quote': TEXT,
        'support': array(QUOTE), 'unresolved': array(TEXT), 'tool_consideration': TEXT})
    payload = {'baseline': baseline['answer']['value'], 'candidate': candidate['answer']['value'],
        'native_tools': candidate['tools'], 'predeclared_applicability': applicability_pairs()[q, tool],
        'review_outcomes': {'baseline': baseline['review_accepted'], 'candidate': candidate['review_accepted'],
                           'candidate_reviews': candidate.get('reviews', [])},
        'instructions': 'Compare the same question and sources with only the named native feedback changed. '
            'Quote exact baseline and candidate conclusion text. Missing supported applicability or review '
            'is insufficient evidence, not no benefit. Do not claim a general ranking.'}
    sources = evaluator.source_records(payload)
    request = evaluator.request('ASSESS_MATCHED_TOOL_EFFECT', question, sources, payload=payload)
    if revision and revision.get('downstream_instruction_profile'):
        from legalmath.interpretation.assurance.phased.downstream_instructions import PROFILE as INSTRUCTIONS, annotate
        require(revision['downstream_instruction_profile'] == INSTRUCTIONS, 'Unknown comparison instructions')
        request = annotate(request)
    def check(value):
        validate_effect(value, baseline, candidate, evaluator, sources)
    outcome = evaluator.dispatch.call('matched-effect', request, schema, check)
    require(outcome['status'] == 'VALIDATED', 'Invalid comparison; evaluation remains open')
    return {'result': outcome, 'baseline': ref(ROOT, baseline_path), 'candidate': ref(ROOT, candidate_path),
        'matched_input_hash': evaluator.route.input_hash, 'full_tool_evaluation': False,
        'required_next': 'Release review checks native supported/adverse cases and all seven integration stages.'}


def _live():
    execution = MasterExecution(ROOT, PROGRAM, STATE)
    frontier = execution.summary()
    if not any(t.startswith(('acquire-', 'baseline-', 'tool-', 'compare-')) or t == 'live-approval'
               for t in frontier['ready'] + frontier['running']):
        return frontier
    service = provider()
    service.check()
    if 'live-approval' in execution.summary()['ready']:
        complete_node(execution, 'live-approval', lambda: {'grant': ref(ROOT, BASE / 'live-grant.json'),
            'proposal': ref(ROOT, BASE / ('reopening-binding.json' if
                (ROOT/BASE/'reopening-binding.json').exists() else 'approval-proposal.json'))})
    semantic_ok=True
    preflight_evidence = []
    if (ROOT/BASE/'reopening-binding.json').exists():
        from scripts.legal_integration_reopening_live import semantic_control
        semantic_ok=semantic_control(service)['qualified']
        preflight_evidence.append(ref(ROOT, LIVE / 'semantic-control/result.json'))
    ready = canaries(service)
    preflight_evidence.append(ref(ROOT, LIVE / 'canary-results.json'))
    block_failed_preflight(execution, ready, semantic_ok, preflight_evidence)
    if not semantic_ok or not any(row['passed'] for row in ready.values()):
        return execution.summary()
    acquisition_cap = read(ROOT / RESOURCES)['scope']['acquisition']
    investigation = product(ROOT / LIVE / 'acquisition', service, phase='acquire', maximum=acquisition_cap,
                            questions=[q for q in QUESTIONS if ready[q]['passed']])
    # Each question checks its own acquisition dependencies. A failed judgment
    # reading does not cancel the independent circular questions.
    def run_node(tid):
        local_service = provider()
        if tid.startswith('acquire-'): action = lambda: acquire(tid[8:], local_service)
        elif tid.startswith('baseline-'): action = lambda: answer(tid[9:], None, local_service)
        elif tid.startswith('tool-'):
            q, tool = tid[5:].split('-', 1); action = lambda: answer(q, tool, local_service)
        else:
            q, tool = tid[8:].split('-', 1); action = lambda: compare(q, tool, local_service)
        return complete_node(execution, tid, action)
    while True:
        service.check()
        pairs = applicability_pairs()
        for tid in execution.summary()['ready']:
            if tid.startswith(('tool-', 'compare-')):
                question, tool = tid.split('-', 1)[1].split('-', 1)
                row = pairs[question, tool]
                if row['decision'] != 'applicable':
                    execution.block_before_dispatch(tid,
                        'Applicability: ' + row['decision'] + '. ' + row['reason'], row['evidence'])
        ready = [t for t in execution.summary()['ready']
                 if t.startswith(('acquire-', 'baseline-', 'tool-', 'compare-'))]
        with execution.locked() as state:
            ready += [t for t, row in state['tasks'].items() if row['status'] == 'RUNNING' and row.get('master_live')]
        if not ready: break
        # Separate ready product branches; no nested autonomous agents.
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(run_node, ready[:2]))
    view = execution.summary()
    if 'release-review' in view['ready']:
        complete_node(execution, 'release-review', lambda: release(service))
        view = execution.summary()
    save(ROOT / LIVE / 'frontier.json', view)
    return view


def live():
    program = read(ROOT / PROGRAM)
    if program.get('execution_refresh'):
        from scripts.legal_integration_current_live import live as current_live
        return current_live()
    require(not program.get('acceptance_revision'),
            'Acceptance revision has no qualified live binding; complete its source/product/runtime prerequisites before a reviewed live continuation')
    if program.get('reviewed_reopening'):
        from scripts.legal_integration_reopening import activate
        from scripts.legal_integration_reopening_live import bind
        if not (ROOT/BASE/'reopening-binding.json').exists(): bind()
        activate()
    elif (ROOT/BASE/'recovery-approval.json').exists():
        from scripts.legal_integration_recovery import activate
        activate()
    (ROOT / LIVE).mkdir(parents=True, exist_ok=True)
    with (ROOT / LIVE / 'supervisor.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            return _live()
        except LegalMathError as exc:
            if exc.code in {'E_AUTHORITY', 'E_INTEGRITY'}:
                path = ROOT / LIVE / 'continuation-veto.json'
                if not path.exists():
                    save(path, {'code': exc.code, 'reason': str(exc)})
                execution = MasterExecution(ROOT, PROGRAM, STATE)
                execution.record_continuation_veto(exc.code, str(exc), [ref(ROOT, path)],
                                                   live_consumers(execution))
            raise


def release(service):
    interactions = {}
    for arm in ('baseline', *TOOLS):
        answers = {}
        for q in QUESTIONS:
            path = ROOT / LIVE / 'arms' / q / arm / 'result.json'
            if path.exists(): answers[q] = read(path)['answers'][q]
            else: answers[q] = {'status': 'DEPENDENCY_BLOCKED'}
        reviewer = session(ROOT / LIVE / 'interactions' / arm, service, maximum=6)
        interactions[arm] = reviewer.audit_interactions(answers)
    execution = MasterExecution(ROOT, PROGRAM, STATE).summary()
    decisions = {}
    for tool in TOOLS:
        matched = {}
        for q in QUESTIONS:
            node = execution['tasks'][f'compare-{q}-{tool}']
            matched[q] = {'status': node['status'], 'reason': node['reason']}
        decisions[tool] = {'matched_cases': matched,
            'fully_integrated': False,
            'acceptance': 'REQUIRES_SUBSTANTIVE_STAGE_REVIEW',
            'required': ['source-warranted supported target', 'native supported and adverse cases',
                         'actual invocation and downstream use', 'matched source-backed effect',
                         'scope-specific decision over all seven integration stages']}
    value = {'engineering': 'EXECUTION_RECORDED; INSPECT_REMAINING_FAILURES',
        'tools': decisions, 'interactions': interactions, 'frontier': execution,
        'legal': 'Conditional answers and their review records require substantive release assessment.',
        'mission_complete': False, 'residual_owner': 'Product team: failed engineering/review/applicability; '
            'legal research: named unresolved authority; client: specifically requested private facts.',
        'next_action': 'Review retained actual answers and tool warrants, record each original coverage decision '
            'and each tool disposition in mission control; do not certify from invocation counts.'}
    save(ROOT / LIVE / 'release-review.json', value)
    return {**value, '_node_status': 'BLOCKED',
        '_conclusion': 'Automated closeout retained. Substantive source and tool-stage acceptance review remains required.'}
