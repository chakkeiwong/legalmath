"""Load explicit pinned conditional profiles for the existing consume API."""
import json
import re
from pathlib import Path
from .anchors import fields
from .contracts import bound_path, digest

VERSION = 'prospectus-conditional-profiles.v1'
ORDER = ('comparative', 'default_f', 'majority', 'amount', 'duration', 'cutoff', 'payment', 'rating', 'votes', 'concert', 'coverage', 'agent_notice', 'notice_delivery', 'affiliate', 'publication', 'labels', 'payment_categories', 'layout_labels', 'reference_roles', 'definition_roles', 'definition_bindings', 'definition_contexts', 'definition_referents', 'definition_remainders', 'definition_dependencies', 'rating_labels', 'cycle_dispositions', 'paragraph_references', 'reference_scope', 'reference_addresses', 'standalone_sections', 'unquoted_definitions', 'purpose_uses', 'bgb_onward', 'holder_authority')
ORDER = (*ORDER, 'issuer_qualification')
ORDER = (*ORDER, 'office_change')
ORDER = (*ORDER, 'election')
ORDER = (*ORDER, 'home_routes')
MANIFEST_LIMIT = 65536
PROFILE_LIMIT = 2 * 1024 * 1024


def _sha(value):
    if not isinstance(value, str) or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('Explicit lowercase SHA256 required')
    return value


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('Duplicate JSON field in conditional profile input')
        result[key] = value
    return result


def _read(root, relative, expected, limit):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError('Conditional input requires a repository-relative path')
    path = bound_path(root, relative)
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('Conditional input exceeds reviewed size bound')
    if digest(raw) != _sha(expected):
        raise ValueError('Conditional input bytes changed')
    try:
        return json.loads(raw, object_pairs_hook=_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite conditional input')))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError('Invalid conditional input JSON') from error


def load(root, manifest_path=None, manifest_sha256=None):
    if manifest_path is None and manifest_sha256 is None:
        return {}
    if manifest_path is None or manifest_sha256 is None:
        raise ValueError('Conditional manifest path and SHA256 are required together')
    manifest = _read(root, manifest_path, manifest_sha256, MANIFEST_LIMIT)
    fields(manifest, {'version', 'profiles'}, {'version', 'profiles'})
    rows = manifest['profiles']
    if manifest['version'] != VERSION or not isinstance(rows, list) or not 1 <= len(rows) <= len(ORDER):
        raise ValueError('Supported bounded nonempty conditional manifest required')
    loaded = {}
    for row in rows:
        keys = {'name', 'path', 'file_sha256', 'profile_sha256'}
        fields(row, keys, keys)
        name = row['name']
        if not isinstance(name, str) or name not in ORDER or name in loaded:
            raise ValueError('Unknown or duplicate conditional profile name')
        profile = _read(root, row['path'], row['file_sha256'], PROFILE_LIMIT)
        semantic = _sha(row['profile_sha256'])
        if not isinstance(profile, dict) or digest(profile) != semantic:
            raise ValueError('Conditional profile semantic content changed')
        loaded[name] = (profile, semantic)
    result = {}
    for name in ORDER:
        if name in loaded:
            profile, semantic = loaded[name]
            result[name + '_profile'] = profile
            result['expected_' + name + '_profile_sha256'] = semantic
    return result
