"""Versioned capacity policy shared by planning, transport and validation.

Budgets are engineering bounds, not predictions of semantic completeness or of
the provider's hidden context window. Unselected historical routes stay exact.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
from ..bounded_context import require

PROFILE = 'common-stage-capacity.v1'


@dataclass(frozen=True)
class Stage:
    adapter: str
    output_tokens: int
    output_bytes: int
    reason: str
    maximum_calls: int = 31
    maximum_depth: int = 4
    maximum_seconds: int = 14400


def stage(adapter, tokens, reason):
    return Stage(adapter, tokens, max(24000, 8 * tokens), reason)


STAGES = {
    'READ_SOURCE': stage('records', 3000, 'Independent source observations; later dependency review is mandatory.'),
    'REVIEW_REQUIREMENTS': stage('records', 3000, 'Independent metadata observations, never legal-source warrants.'),
    'REVIEW_SOURCE_DEPENDENCY': stage('atomic', 4096, 'The linked passages must be jointly interpreted.'),
    'ASSESS_ORIGINAL_REQUIREMENT': stage('source-note', 4096, 'Source pieces require a joint semantic synthesis and original-source review.'),
    'SYNTHESIZE_FINDINGS': stage('atomic', 4096, 'The synthesis owner packs and contracts complete findings with exact membership.'),
    'GENERATE_SOURCE_WARRANTED_CANDIDATES': stage('atomic', 8192, 'Readings and six dimensions must cover the entire supplied source packet.'),
    'STRUCTURED_CRITICISM': stage('atomic', 8192, 'Premises, attacks and preferences form one graph; graph verdicts cannot be unioned.'),
    'ANSWER_ORIGINAL_QUESTION': stage('atomic', 4096, 'The answer must reconcile the complete prepared findings; subsequent reviews retain originals.'),
    'AUDIT_ANSWER_AGAINST_SOURCE': stage('atomic', 4096, 'The caller packs source assignments against the complete answer.'),
    'AUDIT_ANSWER_AND_DETAILED_ACCOUNT': stage('atomic', 4096, 'One complete answer/account relation must remain joint.'),
    'AUDIT_SOURCE_DEPENDENCY_ASSIGNMENTS': stage('grouped-review', 8192, 'Decisions can be partitioned while keeping the complete shared answer and source context.'),
    'AUDIT_SOURCE_AND_DEPENDENCIES': stage('atomic', 4096, 'Joint source/dependency judgment cannot be reduced to votes.'),
    'AUDIT_EXPLICIT_DEPENDENCY_CONTEXT': stage('atomic', 4096, 'This is the joint bridge required by a prior missing-context review.'),
    'AUDIT_WITHIN_QUESTION_DEPENDENCY': stage('atomic', 4096, 'One dependency and its complete context stay together.'),
    'REVIEW_CROSS_QUESTION_DEPENDENCIES': stage('atomic', 4096, 'Both answers must be considered jointly.'),
    'ASSESS_REVIEW_WARRANT': stage('warrants', 4096, 'Independent issue decisions share the entire answer, review, accounts and source context.'),
    'CORRECT_REVIEWED_REQUIREMENT': stage('atomic', 4096, 'One correction must preserve all warranted defects and source gaps.'),
    'CORRECT_REVIEWED_ANSWER': stage('atomic', 4096, 'One correction must preserve all warranted defects; fresh reviews remain mandatory.'),
    'CORRECT_REFERENCE_FORMAT': stage('atomic', 4096, 'Reference-only repair must preserve the complete retained response.'),
    'ASSESS_MATCHED_TOOL_EFFECT': stage('atomic', 8192, 'Both accepted answers and native evidence must be assessed jointly.'),
}
NATIVE = {'retrieval', 'candidates', 'criticism', 'metadata-inventory'}


def selected(request):
    profile = request.get('capacity_profile')
    if profile is None:
        return None
    require(profile == PROFILE, 'Unknown common capacity profile', 'E_AUTHORITY')
    require(request.get('task') in STAGES, 'Unregistered capacity stage: ' + str(request.get('task')), 'E_AUTHORITY')
    value = STAGES[request['task']]
    if request.get('review_repair_profile') is not None:
        from .review_repair import PROFILE as REVIEW_REPAIR, TASKS as REVIEW_TASKS
        require(request['review_repair_profile'] == REVIEW_REPAIR and request['task'] in REVIEW_TASKS,
            'Unregistered review repair capacity', 'E_AUTHORITY')
        if request['task'] == 'AUDIT_SOURCE_DEPENDENCY_ASSIGNMENTS':
            value = replace(value, output_tokens=32768, output_bytes=262144)
    if request.get('capacity_no_partition') is not None:
        require(request['capacity_no_partition'] is True, 'Invalid capacity partition restriction', 'E_AUTHORITY')
        value = replace(value, adapter='atomic', reason='The caller requires this complete relation to remain atomic.')
    return value


def guidance(text, policy):
    # Only instruction strings are changed; source, answer and evidence prose
    # are never traversed or rewritten.
    return text.replace('3000 local tokens', str(policy.output_tokens) + ' local tokens').replace(
        '3000-local-token', str(policy.output_tokens) + '-local-token')


def annotate(request):
    require(request.get('capacity_profile') in (None, PROFILE), 'Conflicting capacity profile', 'E_AUTHORITY')
    result = deepcopy(request)
    result['capacity_profile'] = PROFILE
    policy = selected(result)
    for key in ('instructions', 'downstream_instructions', 'response_reference_instructions'):
        if isinstance(result.get(key), str):
            result[key] = guidance(result[key], policy)
    result['capacity_instructions'] = (
        f'Return the full requested result within {policy.output_tokens} local tokens and '
        f'{policy.output_bytes} UTF-8 bytes, including JSON. Preserve every material '
        'condition, exception, rival and unresolved dependency. These bounds never '
        'authorize omitting an assigned item or inventing a settled conclusion.')
    if 'output_limit' in result:
        result['output_limit'] = dict(local_tokens=policy.output_tokens, bytes=policy.output_bytes)
    return result


def output_bytes(request, limits):
    policy = selected(request)
    return policy.output_bytes if policy else limits.output_bytes


def output_tokens(request, limits):
    policy = selected(request)
    return policy.output_tokens if policy else limits.output_tokens


def estimate(request):
    policy = selected(request)
    if policy is None:
        return 0
    if policy.adapter == 'warrants':
        return 512 + 768 * len(request['payload']['issues'])
    if policy.adapter == 'grouped-review':
        return 1024 + 1200 * len(request['required_considered'])
    if policy.adapter == 'records':
        return 512 + 768 * len(request['records'])
    return 0  # No justified size estimator for free legal prose or a graph.


def contract(request, limits):
    from .account_input import input_token_limit
    from .downstream_input import input_byte_limit
    policy = selected(request)
    require(policy is not None, 'Capacity contract not selected', 'E_AUTHORITY')
    return dict(profile=PROFILE, stage=request['task'], **asdict(policy),
        input_tokens=input_token_limit(request, limits), input_bytes=input_byte_limit(request, limits),
        decoded_bytes=limits.decoded_output_bytes, decoded_tokens=limits.decoded_output_tokens,
        estimated_output_tokens=estimate(request), estimate_is_guarantee=False)


def measure_output(value, request, limits, encode, *, expanded=False):
    from legalmath.canonical import canonical
    data = canonical(value)
    size, tokens = len(data), len(encode(data.decode()))
    maximum_bytes = limits.decoded_output_bytes if expanded else output_bytes(request, limits)
    maximum_tokens = limits.decoded_output_tokens if expanded else output_tokens(request, limits)
    require(size <= maximum_bytes and tokens <= maximum_tokens,
        dict(stage='DECODED_OUTPUT' if expanded else 'WIRE_OUTPUT', bytes=size, local_tokens=tokens,
             maximum_bytes=maximum_bytes, maximum_tokens=maximum_tokens), 'E_RESOURCE_LIMIT')
    return dict(bytes=size, local_tokens=tokens, expanded=expanded)
