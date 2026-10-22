"""Lossless JSON deltas with exact Python JSON scalar types."""


def changes(before, after, path=()):
    if before is after:
        return []
    if type(before) is not type(after):
        return [{'op': 'set', 'path': list(path), 'value': after}]
    if isinstance(before, dict):
        result = [{'op': 'delete', 'path': [*path, key]} for key in sorted(before.keys() - after.keys())]
        for key in sorted(after):
            if key not in before:
                result.append({'op': 'set', 'path': [*path, key], 'value': after[key]})
            else:
                result.extend(changes(before[key], after[key], (*path, key)))
        return result
    if isinstance(before, list):
        if len(before) != len(after):
            return [{'op': 'set', 'path': list(path), 'value': after}]
        return [entry for i, (a, b) in enumerate(zip(before, after)) for entry in changes(a, b, (*path, i))]
    if before != after:
        return [{'op': 'set', 'path': list(path), 'value': after}]
    return []


def apply(before, operations):
    def replace(node, path, operation):
        if not path:
            if operation['op'] != 'set':
                raise ValueError('Cannot delete delta root')
            return operation['value']
        copy = dict(node) if isinstance(node, dict) else list(node)
        key = path[0]
        if len(path) == 1 and operation['op'] == 'delete':
            del copy[key]
        elif len(path) == 1:
            copy[key] = operation['value']
        else:
            copy[key] = replace(node[key], path[1:], operation)
        return copy
    result = before
    for operation in operations:
        if operation['op'] not in {'set', 'delete'}:
            raise ValueError('Unknown delta operation')
        result = replace(result, operation['path'], operation)
    return result


def equal(before, after, message):
    if changes(before, after):
        raise ValueError(message)


def self_check():
    import json
    values = [False, 0, 0.0, True, 1, 1.0, None, '0', [], {},
              {'a': [False, 0, {'b': None}]}, {'a': [0, False], 'extra': 1}]
    for a in values:
        for b in values:
            delta = changes(a, b)
            restored = apply(a, delta)
            equal(restored, b, 'Typed delta failed round trip')
            if json.dumps(restored, sort_keys=True) != json.dumps(b, sort_keys=True):
                raise ValueError('Independent JSON serialization rejects round trip')
            if type(a) is not type(b):
                if not delta:
                    raise ValueError('Scalar type change omitted')
    return len(values)**2
