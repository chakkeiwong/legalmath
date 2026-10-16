"""Failure scope is explicit; a terminal local failure never refunds a call."""
from ...errors import LegalMathError

SHARED_CODES = frozenset({'E_INTEGRITY', 'E_AUTHORITY', 'E_STALE_REVIEW',
                          'E_JOB_STATE', 'E_RESOURCE_LIMIT'})


def shared_failure(exc):
    return isinstance(exc, LegalMathError) and exc.code in SHARED_CODES


class SettledProviderFailure(LegalMathError):
    """Provider confirms this dispatch is over and produced no usable response.

    A timeout, disconnect or lost process alone does not establish settlement.
    Providers may raise this only after reconciling the dispatch outcome.
    """
    def __init__(self, reason):
        super().__init__('E_DEPENDENCY', details={'settled_local_failure': reason})
