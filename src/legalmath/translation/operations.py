"""Closed, target-independent library vocabulary for shared model version 2."""
from ..errors import LegalMathError

ROUNDING = {'toward_zero', 'floor', 'ceiling', 'nearest_away'}


def result_type(name, args):
    if name in ('numeric.min', 'numeric.max'):
        if len(args) == 2 and args[0] == args[1] and args[0] in ('integer', 'decimal', 'money_hkd'):
            return args[0]
    elif name in ('date.add_days', 'date.add_months_clamped') and args == ['date', 'integer']:
        return 'date'
    elif name == 'date.month_end' and args == ['date']:
        return 'date'
    elif name == 'list.length' and len(args) == 1 and args[0].startswith('list['):
        return 'integer'
    elif name == 'list.sequence' and args == ['integer', 'integer']:
        # Begin inclusive, end exclusive; bounded to 10,000 items at execution.
        return 'list[integer]'
    raise LegalMathError('E_TYPE', details='Unknown library operation or argument types: ' + str(name))
