"""Verify known live provider composition without reserving or dispatching."""
from ...canonical import digest
from ...errors import LegalMathError
from ..search.providers import CodexProvider
from .grants import GrantedAllowance


def verify_live_provider(provider):
    from .source_context import ContextProvider
    from .route_admission import RouteBudgetProvider
    current = provider
    seen = set()
    while type(current) in (ContextProvider, RouteBudgetProvider):
        if id(current) in seen:
            raise LegalMathError('E_AUTHORITY', details='Cyclic qualified provider')
        seen.add(id(current))
        underlying = current.provider
        if type(current) is RouteBudgetProvider:
            if (underlying is not current._authority_provider
                    or current.allowance is not getattr(underlying,'allowance',None)
                    or current.live is not True or getattr(underlying,'live',None) is not True):
                raise LegalMathError('E_AUTHORITY',details='Whole-route provider authority changed')
            current.check()
            current=underlying
            continue
        if (underlying is not current._authority_provider
                or current.allowance is not getattr(underlying, 'allowance', None)
                or current.live is not True or getattr(underlying, 'live', None) is not True
                or current._authority_route != digest(getattr(underlying, 'routing', underlying.provider_id))
                or current._authority_context != digest(current.source_context)
                or current.routing != current._qualified_routing):
            raise LegalMathError('E_AUTHORITY', details='Qualified provider authority or context changed')
        for ref in current.source_context['qualification']['evidence']:
            from .integration_contract import read_evidence
            read_evidence(ref, current.source_context_root, json_value=False)
        current = underlying
    if (not isinstance(current, CodexProvider) or getattr(current, 'live', None) is not True
            or not isinstance(current.allowance, GrantedAllowance)):
        raise LegalMathError('E_AUTHORITY', details='Live investigation requires a recorded grant and a known provider')
    return current.allowance.verify()
