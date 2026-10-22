"""Exact conditional error enclosures; inclusion never establishes a cause."""
from fractions import Fraction
import re


def rational(value):
    if type(value) is int:
        return Fraction(value)
    if not isinstance(value, str) or re.fullmatch(r'-?[0-9]+(?:/[1-9][0-9]*)?', value) is None:
        raise ValueError('Exact integer or rational string required')
    return Fraction(value)


def enclose(amounts, coefficients, error_bounds):
    """Enclose sum(a*x) if abs(x-d)<=epsilon, without imputing unknown d."""
    if (not all(isinstance(v, (list, tuple)) for v in (amounts, coefficients, error_bounds))
            or not amounts or len(amounts) != len(coefficients) or len(amounts) != len(error_bounds)):
        raise ValueError('Matched nonempty amount, coefficient and error vectors required')
    if any(v is not None and type(v) is not int for v in amounts):
        raise ValueError('Displayed integer amounts or explicit unknowns required')
    if any(type(c) is not int for c in coefficients):
        raise ValueError('Integer relation coefficients required')
    errors = [rational(e) for e in error_bounds]
    if any(e < 0 for e in errors):
        raise ValueError('Nonnegative error bounds required')
    unknowns = [i for i, (d, c) in enumerate(zip(amounts, coefficients)) if d is None and c != 0]
    known = sum(d * c for d, c in zip(amounts, coefficients) if d is not None)
    radius = sum(abs(c) * e for c, e in zip(coefficients, errors))
    interval = None if unknowns else [str(known - radius), str(known + radius)]
    excluded = None if unknowns else not (known - radius <= 0 <= known + radius)
    return {'status': 'UNKNOWN_COMPONENT' if unknowns else 'CONDITIONAL_ENCLOSURE',
            'known_residual_part': known, 'unknown_term_indices': unknowns,
            'displayed_residual': None if unknowns else known,
            'maximum_relation_error': str(radius), 'underlying_residual_enclosure': interval,
            'rounding_only_explanation': 'UNDETERMINED_UNKNOWN_COMPONENT' if unknowns else
                'EXCLUDED_UNDER_ASSUMPTIONS' if excluded else 'NOT_EXCLUDED_UNDER_ASSUMPTIONS',
            'actual_rounding_cause_established': False,
            'underlying_relation_established': False}
