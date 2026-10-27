"""A shared provider prerequisite, distinct from a failed legal assessment."""
from legalmath.errors import LegalMathError

PROFILE = 'defer-unstarted-provider-work.v1'


class ServiceDeferred(LegalMathError):
    """No dispatch began for this request; resume only under checked authority."""

    def __init__(self, reason):
        super().__init__('E_RESOURCE_LIMIT', details=reason)


def record(exc):
    return dict(status='DEFERRED_SERVICE', error=exc.code,
        reason=str(exc.details or exc), shared_scope=['provider-service'],
        dispatched=False, legal_acceptance=False)
