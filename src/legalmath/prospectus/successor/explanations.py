"""One subset-minimal explanation of a supplied finite Boolean conclusion.

Deletion preserves sufficiency. A counterexample after deleting a retained
literal proves its necessity and survives removal of further assumptions.
This is not minimum cardinality, causal explanation, or legal fact validation.
"""
from .contracts import digest
from .predicates import dispatch, names

VERSION = 'subset-minimal.v1'
LIMITS = {'max_facts': 12, 'max_nodes': 4096, 'max_depth': 24}


def validate_option(option):
    if option != VERSION or not isinstance(option, str):
        raise ValueError('Unsupported law explanation profile')


def validate_expression(expression):
    pending, count = [(expression, 0)], 0
    while pending:
        node, depth = pending.pop()
        count += 1
        if count > LIMITS['max_nodes'] or depth > LIMITS['max_depth']:
            raise ValueError('Explanation expression resource limit')
        if isinstance(node, dict) and len(node) == 1:
            op, args = next(iter(node.items()))
            if op == 'not':
                pending.append((args, depth + 1))
            elif op in {'all', 'any'} and isinstance(args, list):
                pending.extend((arg, depth + 1) for arg in args)
    return sorted(names(expression))


def explain(expression, observations, *, engine='finite', authority_active=True):
    support = validate_expression(expression)
    if not isinstance(observations, dict):
        raise ValueError('Explanation observations must be a mapping')
    base = {'version': VERSION, 'scope': 'ONE_BASIS_SUPPLIED_BOOLEAN_CONSEQUENCE',
            'claim': 'SUBSET_MINIMAL_NOT_MINIMUM_CARDINALITY',
            'order': 'SORTED_FACT_NAME_DELETION', 'limits': dict(LIMITS),
            'expression_sha256': digest(expression), 'observations_sha256': digest(observations),
            'counterexample_scope': 'BOOLEAN_ASSIGNMENTS_NOT_VERIFIED_EVENTS'}

    def unavailable(reason):
        return {**base, 'status': 'NOT_AVAILABLE', 'reason': reason}

    if not authority_active:
        return unavailable('INACTIVE_AUTHORITY')
    if engine != 'finite':
        return unavailable('UNSUPPORTED_ENGINE')
    if len(support) > LIMITS['max_facts']:
        return unavailable('DOMAIN_LIMIT')
    answer = dispatch(expression, observations)
    if answer['status'] not in {'YES', 'NO'}:
        return unavailable(answer['status'])
    target = answer['status']
    retained = {n: observations[n] for n in support if type(observations.get(n)) is bool}
    for name in tuple(retained):
        reduced = {n: v for n, v in retained.items() if n != name}
        if dispatch(expression, reduced)['status'] == target:
            retained = reduced
    counterexamples = {}
    opposite = 'false' if target == 'YES' else 'true'
    for name in retained:
        result = dispatch(expression, {n: v for n, v in retained.items() if n != name})
        if opposite not in result['witnesses']:
            raise ValueError('Explanation necessity witness missing')
        counterexamples[name] = result['witnesses'][opposite]
    return {**base, 'status': 'EXPLAINED', 'conclusion': target, 'literals': retained,
            'deletion_counterexamples': counterexamples}
