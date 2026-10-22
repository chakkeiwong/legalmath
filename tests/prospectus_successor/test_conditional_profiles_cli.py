"""Explicit profile binding, CLI routing and preserved default behavior."""
from argparse import ArgumentParser, Namespace
from copy import deepcopy
import json
from pathlib import Path
import pytest
from legalmath.prospectus.successor import conditional_profiles as module, service
from legalmath.prospectus.successor.contracts import digest


def fixture(root, names=('votes', 'rating')):
    profiles = []; expected = {}
    for name in names:
        profile = {'version': name + '.test', 'ordinary_answer_sha256': 'a' * 64}
        path = name + '.json'; raw = json.dumps(profile).encode(); (root/path).write_bytes(raw)
        profiles.append({'name': name, 'path': path, 'file_sha256': digest(raw), 'profile_sha256': digest(profile)})
        expected[name + '_profile'] = profile; expected['expected_' + name + '_profile_sha256'] = digest(profile)
    manifest = {'version': module.VERSION, 'profiles': profiles}
    return manifest, expected


def put(root, manifest):
    raw = json.dumps(manifest).encode(); (root/'manifest.json').write_bytes(raw)
    return digest(raw)


def test_manifest_preserves_pins_and_fixed_order(tmp_path):
    manifest, expected = fixture(tmp_path)
    actual = module.load(tmp_path, 'manifest.json', put(tmp_path, manifest))
    assert actual == expected
    assert list(actual) == ['rating_profile', 'expected_rating_profile_sha256', 'votes_profile', 'expected_votes_profile_sha256']
    assert actual['votes_profile']['ordinary_answer_sha256'] == 'a' * 64
    assert module.load(tmp_path) == {}


@pytest.mark.parametrize('kind', ['missing-pin', 'missing-path', 'manifest-hash', 'profile-hash',
    'semantic-hash', 'unknown-name', 'duplicate-name', 'empty', 'version', 'extra-field',
    'absolute-path', 'escape-path', 'wrong-type', 'malformed-hash', 'missing-row-field'])
def test_invalid_manifest_or_profile_refuses(tmp_path, kind):
    manifest, _ = fixture(tmp_path); path = 'manifest.json'; pin = None
    if kind == 'profile-hash': manifest['profiles'][0]['file_sha256'] = '0' * 64
    elif kind == 'semantic-hash': manifest['profiles'][0]['profile_sha256'] = '0' * 64
    elif kind == 'unknown-name': manifest['profiles'][0]['name'] = 'arbitrary'
    elif kind == 'duplicate-name': manifest['profiles'].append(deepcopy(manifest['profiles'][0]))
    elif kind == 'empty': manifest['profiles'] = []
    elif kind == 'version': manifest['version'] = 'other'
    elif kind == 'extra-field': manifest['ignored'] = True
    elif kind == 'absolute-path': manifest['profiles'][0]['path'] = str(tmp_path/'votes.json')
    elif kind == 'escape-path': manifest['profiles'][0]['path'] = '../outside.json'
    elif kind == 'wrong-type': manifest['profiles'] = {'votes': True}
    elif kind == 'malformed-hash': manifest['profiles'][0]['profile_sha256'] = 'not-a-hash'
    elif kind == 'missing-row-field': del manifest['profiles'][0]['profile_sha256']
    pin = put(tmp_path, manifest)
    if kind == 'missing-pin': pin = None
    elif kind == 'missing-path': path = None
    elif kind == 'manifest-hash': pin = '0' * 64
    with pytest.raises(ValueError): module.load(tmp_path, path, pin)


@pytest.mark.parametrize('raw', [b'{"version":1,"version":2}', b'{"x":NaN}', b'not json'])
def test_duplicate_nonfinite_or_malformed_json_refuses(tmp_path, raw):
    (tmp_path/'manifest.json').write_bytes(raw)
    with pytest.raises(ValueError): module.load(tmp_path, 'manifest.json', digest(raw))


def test_size_and_symlink_limits(tmp_path):
    raw = b' ' * (module.MANIFEST_LIMIT + 1); (tmp_path/'large.json').write_bytes(raw)
    with pytest.raises(ValueError): module.load(tmp_path, 'large.json', digest(raw))
    outside = tmp_path.parent/'outside-profile.json'; outside.write_text('{}')
    (tmp_path/'link.json').symlink_to(outside)
    with pytest.raises(ValueError): module.load(tmp_path, 'link.json', digest(b'{}'))


def test_consume_parser_accepts_paired_options_and_assess_does_not():
    parser = ArgumentParser(); service.configure(parser)
    args = parser.parse_args(['consume', '--products', 'products.json', '--output', 'answer.json',
        '--conditional-profiles', 'profiles.json', '--conditional-profiles-sha256', 'a' * 64])
    assert args.conditional_profiles == 'profiles.json' and args.conditional_profiles_sha256 == 'a' * 64
    old = parser.parse_args(['consume', '--products', 'products.json', '--output', 'answer.json'])
    assert old.conditional_profiles is None and old.conditional_profiles_sha256 is None
    with pytest.raises(SystemExit):
        parser.parse_args(['assess', '--request', 'request.json', '--output', 'answer.json',
            '--conditional-profiles', 'profiles.json'])


@pytest.mark.parametrize('supplied', [False, True])
def test_dispatch_routes_exact_pins_and_preserves_no_profile_route(tmp_path, monkeypatch, supplied):
    manifest, expected = fixture(tmp_path)
    pin = put(tmp_path, manifest)
    (tmp_path/'products.json').write_text('{"products":{}}')
    calls = []
    def consume(products, root, bank=None, **kwargs):
        calls.append((products, Path(root), bank, kwargs))
        return {'report_sha256': 'answer', 'questions': {'Q1': {'status': 'UNKNOWN'}}}
    monkeypatch.setattr(service, 'consume', consume)
    args = Namespace(prospectus_command='consume', products=str(tmp_path/'products.json'),
        repository=str(tmp_path), output=str(tmp_path/'answer.json'), mode='frozen',
        conditional_profiles='manifest.json' if supplied else None,
        conditional_profiles_sha256=pin if supplied else None)
    service.dispatch(args)
    assert calls == [({}, tmp_path, None, {'mode': 'frozen', **(expected if supplied else {})})]
