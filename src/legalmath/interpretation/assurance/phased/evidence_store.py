"""Chunked exact JSON storage with individually bounded immutable records.

The manifest preserves order and types. This is disk serialization, never model
context compression; consumers reconstruct all content before semantic use.
"""
from pathlib import Path
import json
import re
from copy import deepcopy
from legalmath.canonical import canonical, digest, MAX_BYTES, loads, _check
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_context import require
from legalmath.interpretation.assurance.monitor import save


def save_exact(path, value):
    """Use ordinary canonical JSON when it fits, otherwise exact bounded storage."""
    _check(value)
    try:
        canonical(value)
    except LegalMathError as exc:
        if exc.code != 'E_RESOURCE_LIMIT':
            raise
        return write(path, value)
    save(path, value)
    return None


def load_exact(path):
    value = loads(Path(path).read_bytes())
    if isinstance(value, dict) and value.get('profile') == 'bounded-exact-evidence-store.v1':
        return read(path)
    return value


def write(path, value, *, leaf_bytes=262144):
    require(type(leaf_bytes) is int and 32 <= leaf_bytes <= MAX_BYTES, 'Invalid evidence leaf bound')
    _check(value)  # Preserve canonical types and the original nesting-depth bound.
    path = Path(path)
    blob_root = path.parent / (path.name + '.records')
    blob_root.mkdir(parents=True, exist_ok=True)
    require(not blob_root.is_symlink() and blob_root.resolve().parent == path.parent.resolve(),
            'Foreign evidence directory')
    encoder = json.JSONEncoder(sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    def small(node):
        size = 0
        record = {'type': 'value', 'value': node}
        for part in encoder.iterencode(record):
            size += len(part.encode('utf-8'))
            if size > leaf_bytes:
                return None
        return record
    def retain(record):
        encoded = canonical(record)
        require(len(encoded) <= leaf_bytes, 'Evidence leaf exceeds local bound', 'E_RESOURCE_LIMIT')
        identity = digest(record)
        target = blob_root / (identity + '.json')
        require(target.resolve().parent == blob_root.resolve(), 'Foreign evidence path')
        if target.exists():
            require(target.read_bytes() == encoded, 'Changed immutable evidence record')
        else:
            with target.open('xb') as stream:
                stream.write(encoded)
        return identity
    def encode(node):
        # Store a whole bounded subtree instead of creating one file per scalar.
        # The encoder stops measuring at the leaf bound; canonical() only sees
        # individual bounded records, never the combined investigation.
        bounded = small(node)
        if bounded is not None:
            return retain(bounded)
        if isinstance(node, dict):
            if not node:
                return retain({'type': 'value', 'value': node})
            pairs = []
            for key, child in node.items():
                canonical({key: None})
                pairs.append([key, encode(child)])
            return collection('dict', pairs)
        if isinstance(node, list):
            if not node:
                return retain({'type': 'value', 'value': node})
            return collection('list', [encode(child) for child in node])
        if isinstance(node, str):
            size = max(1, (leaf_bytes - 64) // 12)
            parts = [node[i:i+size] for i in range(0, len(node), size)]
            if len(parts) > 1:
                return collection('string', [retain({'type': 'value', 'value': s}) for s in parts])
        return retain({'type': 'value', 'value': node})
    def collection(kind, values):
        pages, batch = [], []
        for value in values:
            trial = {'type': 'page', 'items': batch + [value]}
            if len(canonical(trial)) > leaf_bytes:
                require(batch, 'Atomic collection reference exceeds local bound', 'E_RESOURCE_LIMIT')
                pages.append(retain({'type': 'page', 'items': batch}))
                batch = []
            batch.append(value)
        if batch:
            pages.append(retain({'type': 'page', 'items': batch}))
        # Index pages too, so no unbounded manifest list is created.
        if len(canonical({'type': kind, 'pages': pages})) <= leaf_bytes:
            return retain({'type': kind, 'pages': pages})
        return retain({'type': kind, 'page_index': collection('list', pages)})
    root = encode(value)
    manifest = {'profile': 'bounded-exact-evidence-store.v1', 'root': root,
        'record_directory': blob_root.name, 'leaf_bytes': leaf_bytes}
    save(path, manifest)
    return manifest


def read(path):
    path = Path(path)
    manifest = loads(path.read_bytes())
    require(manifest.get('profile') == 'bounded-exact-evidence-store.v1', 'Wrong evidence store profile')
    require(manifest['record_directory'] == path.name + '.records', 'Foreign evidence directory')
    require(type(manifest.get('leaf_bytes')) is int and 32 <= manifest['leaf_bytes'] <= MAX_BYTES,
            'Invalid retained leaf bound')
    directory = path.parent / manifest['record_directory']
    require(not directory.is_symlink() and directory.resolve().parent == path.parent.resolve(),
            'Foreign evidence directory')
    cache, active = {}, set()
    def record(identity):
        require(isinstance(identity, str) and re.fullmatch(r'[0-9a-f]{64}', identity), 'Invalid evidence hash')
        target = directory / (identity + '.json')
        require(target.resolve().is_relative_to(directory.resolve()), 'Foreign evidence path')
        data = target.read_bytes()
        require(len(data) <= manifest['leaf_bytes'], 'Evidence leaf exceeds retained bound')
        row = loads(data)
        require(digest(row) == identity, 'Evidence record changed')
        return row
    def pages(row):
        identities = row.get('pages')
        if identities is None:
            identities = decode(row['page_index'])
        require(isinstance(identities, list), 'Invalid evidence page index')
        result = []
        for identity in identities:
            page = record(identity)
            require(page.get('type') == 'page', 'Invalid evidence page')
            result.extend(page['items'])
        return result
    def decode(identity):
        if identity in cache:
            return deepcopy(cache[identity])
        require(identity not in active, 'Cyclic evidence manifest')
        active.add(identity)
        row = record(identity)
        if row['type'] == 'value':
            result = row['value']
        elif row['type'] == 'dict':
            pairs = pages(row)
            require(len(pairs) == len({p[0] for p in pairs}), 'Duplicate evidence dictionary key')
            result = {key: decode(child) for key, child in pairs}
        elif row['type'] == 'list':
            result = [decode(child) for child in pages(row)]
        elif row['type'] == 'string':
            parts = [decode(child) for child in pages(row)]
            require(all(isinstance(s, str) for s in parts), 'Invalid string part')
            result = ''.join(parts)
        else:
            require(False, 'Unknown evidence record type')
        active.remove(identity)
        cache[identity] = result
        return result
    result = deepcopy(decode(manifest['root']))
    _check(result)
    return result

