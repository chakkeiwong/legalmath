"""Semantic partition contracts. No arbitrary JSON splitting or graph union."""
from copy import deepcopy
import re
from jsonschema import validate
from legalmath.canonical import canonical
from ..bounded_context import require
from .capacity_policy import selected


def ids(request):
    mode = selected(request).adapter
    if mode == 'records':
        return [r['id'] for r in request['records']]
    if mode == 'warrants':
        return [r['id'] for r in request['payload']['issues']]
    if mode == 'grouped-review':
        return list(request['required_considered'])
    if mode == 'source-note':
        return [r['id'] for r in request['records']]
    return []


def check_population(request):
    population = ids(request)
    require(len(population) == len(set(population)), 'Duplicate capacity assignment', 'E_SCHEMA')
    return population


def split(product, call):
    """Return two strictly smaller assignment sets, with immutable shared context."""
    request, schema = call['request'], call['schema']
    mode = selected(request).adapter
    population = check_population(request)
    if len(population) < 2 or mode == 'atomic':
        return []
    middle = len(population) // 2
    result = []
    for number, members in enumerate((population[:middle], population[middle:])):
        req, shape = deepcopy(request), deepcopy(schema)
        if mode == 'records':
            from ..bounded_context import response_schema, observation_schema
            req['records'] = [r for r in request['records'] if r['id'] in members]
            shape = (observation_schema if req['task'] == 'REVIEW_REQUIREMENTS' else response_schema)(members)
            packet = {'request': req, 'schema': shape}
            from legalmath.canonical import digest
            packet['packet_hash'] = digest(packet)
            def check(value, packet=packet):
                product.route.validate_response(packet, value, decoded=True)
        elif mode == 'warrants':
            # Review.issues and every source/account remain complete. Only the
            # independently requested issue decisions shrink.
            req['payload']['issues'] = [r for r in request['payload']['issues'] if r['id'] in members]
            properties = shape['properties']['decisions']['items']['properties']
            properties['issue_id'] = {**properties['issue_id'], 'enum': members}
            shape['properties']['decisions'].update(minItems=len(members), maxItems=len(members))
            def check(value, req=req, members=members):
                actual = [r['issue_id'] for r in value['decisions']]
                require(len(actual) == len(set(actual)) and set(actual) == set(members), 'Lost warrant issue')
                require(value['considered'] == req['required_considered'], 'Changed warrant owner')
                product.citations(value, req['records'])
                for row in value['decisions']:
                    require(row['disposition'] != 'WARRANTED' or row['support'], 'Unsupported warrant')
                    require(row['disposition'] != 'UNWARRANTED' or row['support'] or
                        row['basis'] == 'QUESTION_SCOPE', 'Unsupported discarded criticism')
        elif mode == 'grouped-review':
            # Full assignments, origin table, sources and answer remain in the
            # request. This is output pagination, not source-context truncation.
            req['required_considered'] = members
            req['capacity_assignment_instruction'] = (
                'All assignments are retained as joint context. Return decisions only for '
                'required_considered. Preserve exceptions and relationships from the full context.')
            shape['properties']['assignments']['properties'] = {
                key: value for key, value in shape['properties']['assignments']['properties'].items() if key in members}
            shape['properties']['assignments']['required'] = members
            shape['properties']['analyses']['maxItems'] = len(members)
            def check(value, req=req, members=members):
                from .group_review import validate as validate_group
                validate_group(product, req['question']['question_id'], value, members, req['records'])
        elif mode == 'source-note':
            req['records'] = [r for r in request['records'] if r['id'] in members]
            req['verified_locator_bindings'] = [r for r in request.get('verified_locator_bindings', [])
                if r['record_id'] in members]
            req['capacity_piece_instruction'] = (
                'This is a partial source reading for the same original requirement. Preserve all '
                'conditions and contrary evidence. Explicitly retain dependencies on other pieces '
                'as unresolved. Only a later joint synthesis can state the combined conclusion.')
            def check(value, req=req):
                require(len(value['considered']) == len(set(value['considered'])) and
                    set(value['considered']) == set(req['required_considered']), 'Lost requirement owner')
                product.citations(value, req['records'])
                require(value['support'] or value['unresolved'], 'Unsupported partial note')
                if req.get('account_contract'):
                    from .account_contract import validate as validate_account
                    validate_account(value, product, req['records'])
        else:
            return []
        def checked(value, shape=shape, check=check):
            validate(value, shape)
            check(value)
        result.append(dict(key=call['key'] + '-p' + str(number), request=req,
                           schema=shape, validate=checked))
    require([i for child in result for i in ids(child['request'])] == population,
        'Capacity partition changed assignment order or coverage', 'E_INTEGRITY')
    require(all(0 < len(ids(c['request'])) < len(population) for c in result),
        'Capacity partition did not contract', 'E_INTEGRITY')
    return result


def merge(product, call, children, values):
    request = call['request']
    mode = selected(request).adapter
    require(len(children) == len(values), 'Missing capacity piece', 'E_INTEGRITY')
    require([i for c in children for i in ids(c['request'])] == check_population(request),
        'Changed capacity membership', 'E_INTEGRITY')
    if mode == 'records':
        return {'records': [r for value in values for r in value['records']]}
    if mode == 'grouped-review':
        assembled = {'analyses': [], 'assignments': {}}
        for number, value in enumerate(values):
            names = {row['analysis_id']: str(number) + ':' + row['analysis_id'] for row in value['analyses']}
            for row in value['analyses']:
                assembled['analyses'].append({**deepcopy(row), 'analysis_id': names[row['analysis_id']]})
            for key, row in value['assignments'].items():
                require(key not in assembled['assignments'], 'Duplicate assembled assignment', 'E_INTEGRITY')
                assembled['assignments'][key] = {'analysis_id': names[row['analysis_id']]}
        return assembled
    if mode == 'warrants':
        result = {'decisions': [], 'considered': deepcopy(request['required_considered']),
                  'source_gaps': [], 'assertion_bindings': []}
        for value in values:
            offset = len(result['decisions'])
            for binding in value['assertion_bindings']:
                path = binding['path']
                match = re.fullmatch(r'/decisions/([0-9]+)(/.*)?', path)
                require(match and int(match[1]) < len(value['decisions']),
                    'Cannot safely rebase a non-decision warrant assertion', 'E_SCHEMA')
                result['assertion_bindings'].append({**deepcopy(binding),
                    'path': '/decisions/' + str(offset + int(match[1])) + (match[2] or '')})
            result['decisions'].extend(deepcopy(value['decisions']))
            for gap in value['source_gaps']:
                if gap not in result['source_gaps']:
                    result['source_gaps'].append(deepcopy(gap))
        return result
    require(mode == 'source-note', 'No merge adapter', 'E_INTEGRITY')
    # Keep every original source in the joint bridge. If that complete relation
    # cannot fit, return an explicit limitation rather than silently summarize
    # away the distant exception which the bridge is supposed to check.
    req = deepcopy(request)
    req['capacity_partial_readings'] = values
    req['capacity_bridge_instruction'] = (
        'Reconcile ALL partial source readings against ALL original source text. Check cross-piece '
        'conditions, exceptions, alternatives and conflicts. Preserve unresolved relations. '
        'Return one complete original requirement account; partial conclusions are proposals.')
    return dict(key=call['key'] + '-bridge', request=req, schema=call['schema'], validate=call['validate'])
