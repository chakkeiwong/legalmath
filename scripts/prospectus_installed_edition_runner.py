"""Installed Python -I runner; checkout paths are used only for retained data."""
from copy import deepcopy
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import runpy
import subprocess
import sys

if sys.argv[3] != 'edition':
    runpy.run_path(str(Path(__file__).with_name('prior-runner.py')), run_name='__main__')
    raise SystemExit(0)

from legalmath.prospectus import programme_editions
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest

HERE, ROOT = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
REF = ROOT / 'docs/implementation/prospectus-execution-authority/attempts/relation-discovery/attempt-005'
TARGET = HERE / 'installed-results/edition'
TARGET.mkdir(parents=True, exist_ok=False)
ENV = Path(sys.executable).parent.parent.resolve()


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def save(name, value):
    data = json.dumps(value, ensure_ascii=False, indent=2).encode()
    with (TARGET / name).open('xb') as stream:
        stream.write(gzip.compress(data, mtime=0) if name.endswith('.gz') else data)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


modules = [programme_editions, service]
proof = {'python': sys.executable, 'prefix': sys.prefix, 'isolated': sys.flags.isolated,
    'sys_path': sys.path,
    'modules': {m.__name__: {'path': m.__file__, 'sha256': sha(m.__file__)} for m in modules},
    'dependencies': {d.metadata['Name']: d.version for d in importlib.metadata.distributions()}}
assert sys.flags.isolated and Path(sys.prefix).resolve() == ENV
assert all(Path(m.__file__).resolve().is_relative_to(ENV) for m in modules)
assert all(not Path(p).resolve().is_relative_to(ROOT / 'src') for p in sys.path if p)
save('import-proof.json', proof)


def no_native(*args, **kwargs):
    raise AssertionError('Native/subprocess start forbidden in installed frozen consumers')


subprocess.Popen = no_native
products = read(REF / 'products.json.gz')
profile = read(REF / 'profile.json')
for case, state in [('edition', 'COMPATIBLE_CANDIDATE'), ('missing', 'MISSING_TARGET'),
                    ('duplicate', 'AMBIGUOUS_TARGET')]:
    value = deepcopy(profile)
    if case == 'missing':
        value['programmes'] = value['programmes'][:1]
    elif case == 'duplicate':
        value['programmes'].append(deepcopy(value['programmes'][-1]))
    result = programme_editions.consume(products, value, ROOT, expected_profile_sha256=digest(value))
    assert result == read(REF / (case + '-consumer.json.gz'))
    assert result['edition_review']['target_state'] == state
    assert result['edition_review']['accepted_relations'] == []
    assert result['answer'] == read(REF / 'baseline-answer.json.gz')
    save(case + '-consumer.json.gz', result)

controls = []
for name in ('changed-image', 'changed-original', 'changed-quote', 'wrong-date-label',
             'omitted-joint-context', 'reversed-period-roles', 'publication-as-target',
             'fabricated-acceptance', 'stale-pin'):
    value = deepcopy(profile)
    if name == 'changed-image':
        value['sources'][0]['cover_sha256'] = '0' * 64
    elif name == 'changed-original':
        value['sources'][0]['source_sha256'] = '0' * 64
    elif name == 'changed-quote':
        value['programmes'][0]['publication_date']['quote'] = '2025年8月7日'
    elif name == 'wrong-date-label':
        value['programmes'][0]['publication_label'] = deepcopy(value['programmes'][0]['issuer_label'])
    elif name == 'omitted-joint-context':
        value['correction']['target_context'].pop()
    elif name == 'reversed-period-roles':
        a, b = value['correction']['before_period'], value['correction']['after_period']
        value['correction']['before_period'], value['correction']['after_period'] = b, a
    elif name == 'publication-as-target':
        value['correction']['target_context'] = [deepcopy(value['correction']['publication_date'])]
    elif name == 'fabricated-acceptance':
        value['accepted_relations'] = [{'from': 'correction', 'to': '2026'}]
    else:
        value['reviewer']['identity'] += 'changed'
    pin = digest(profile) if name == 'stale-pin' else digest(value)
    try:
        programme_editions.consume(products, value, ROOT, expected_profile_sha256=pin)
    except ValueError as error:
        controls.append({'case': name, 'refused': True, 'repinned': name != 'stale-pin', 'reason': str(error)})
    else:
        raise AssertionError('Altered installed edition input accepted: ' + name)
assert controls == read(REF / 'actual-controls.json')
save('controls.json', controls)
save('result.json', {'status': 'PASS', 'native_calls': 0,
    'details': {'full_outputs_equal': True, 'cases': 3, 'controls': 9,
                'accepted_relations': 0, 'independent_legal_acceptance': False}})
print({'stage': 'edition', 'status': 'PASS', 'full_outputs_equal': True, 'controls': 9})
