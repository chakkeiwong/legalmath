"""Continue product reasoning with failed optional evidence explicitly retained."""
from ...errors import LegalMathError
from ...canonical import digest
from .optional_tools import ToolSession


class IndependentToolSession(ToolSession):
    def _check(self, kind, packet, inputs, *, candidates=None):
        try:
            return super()._check(kind, packet, inputs, candidates=candidates)
        except LegalMathError as exc:
            # The parent has already validated and durably recorded this exact
            # FAILED result. Other integrity, budget and interruption errors
            # still propagate. No retry and no status downgrade occur here.
            if (exc.code == 'E_DEPENDENCY' and isinstance(exc.details, dict)
                    and 'optional_tool_failure' in exc.details):
                failed = exc.details['optional_tool_failure']
                checks = self.report()['checks']
                if (isinstance(failed, dict) and failed.get('status') == 'FAILED'
                        and any(c.get('result_hash') == digest(failed)
                                and {k: v for k, v in c.items() if k not in {'key', 'result_hash'}} == failed
                                for c in checks)):
                    return failed
            raise
