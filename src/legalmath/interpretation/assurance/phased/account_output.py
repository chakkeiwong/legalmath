"""Optional typed-account output allowance; ordinary policy remains unchanged."""
from ..bounded_context import require

PROFILE = 'typed-account-output-4k.v1'
OUTPUT_TOKENS = 4096


def validate_profile(request, profile):
    require(profile == PROFILE and request.get('task') == 'ASSESS_ORIGINAL_REQUIREMENT'
        and request.get('account_contract') == 'typed-requirement-account.v1'
        and request.get('response_reference_profile') == 'bounded-indexed-assertions.v2',
        'Account output selection outside its typed requirement contract', 'E_AUTHORITY')


def output_token_limit(request, limits):
    if request.get('capacity_profile') is not None:
        from .capacity_policy import output_tokens
        if request.get('account_output_profile') is not None:
            validate_profile(request, request['account_output_profile'])
        return output_tokens(request, limits)
    profile = request.get('account_output_profile')
    if profile is None:
        return limits.output_tokens
    validate_profile(request, profile)
    require(limits.output_tokens == 3000, 'Account output profile has a different baseline', 'E_AUTHORITY')
    return OUTPUT_TOKENS
