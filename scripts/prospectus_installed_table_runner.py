"""Isolated installed consumers; checkout is used only for sealed input data."""
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

from legalmath.prospectus import basf_statement, basf_equity
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest

HERE, ROOT = [Path(p).resolve() for p in sys.argv[1:3]]
PRIOR = HERE.parent / 'attempt-002/repair'
TARGET = HERE / 'installed-results'
TARGET.mkdir(exist_ok=False)
ENV = Path(sys.executable).parent.parent.resolve()


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def save(name, value):
    data = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2).encode()
    with (TARGET / name).open('xb') as stream:
        stream.write(gzip.compress(data, mtime=0) if name.endswith('.gz') else data)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


modules = [basf_statement, basf_equity, service]
proof = {'python': sys.executable, 'prefix': sys.prefix, 'isolated': sys.flags.isolated,
         'sys_path': sys.path,
         'modules': {m.__name__: {'path': m.__file__, 'sha256': sha(m.__file__)} for m in modules},
         'dependencies': {d.metadata['Name']: d.version for d in importlib.metadata.distributions()}}
assert sys.flags.isolated and Path(sys.prefix).resolve() == ENV
assert all(Path(m.__file__).resolve().is_relative_to(ENV) for m in modules)
assert all(not Path(p).resolve().is_relative_to(ROOT / 'src') for p in sys.path if p)
package = ENV / 'lib/python3.11/site-packages/legalmath'
actual = {str(p.relative_to(package)): sha(p) for p in package.rglob('*')
          if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
assert actual == read(HERE / 'source-package.json')
save('import-proof.json', proof)
save('package-files.json', actual)


def no_native(*args, **kwargs):
    raise AssertionError('Subprocess/native start forbidden in installed frozen consumers')


subprocess.Popen = no_native
products = read(HERE / 'products.json.gz')
statement_profile, equity_profile = read(PRIOR / 'profile.json'), read(HERE / 'profile.json')
statement_result = basf_statement.consume(products, statement_profile, ROOT,
                                         expected_profile_sha256=digest(statement_profile))
assert statement_result == read(PRIOR / 'statement-consumer.json.gz')
save('statement-consumer.json.gz', statement_result)
equity_result = basf_equity.consume(products, statement_profile, equity_profile, ROOT,
                                  expected_statement_profile_sha256=digest(statement_profile),
                                  expected_profile_sha256=digest(equity_profile))
assert equity_result == read(HERE / 'equity-consumer.json.gz')
assert equity_result['answer'] == read(HERE / 'baseline-answer.json.gz')
save('equity-consumer.json.gz', equity_result)
controls = {}
for label, folder, evaluate in [('statement', PRIOR, basf_statement.evaluate), ('equity', HERE, basf_equity.evaluate)]:
    expected = read(folder / 'actual-controls.json')
    observed = []
    for row in expected:
        suffix = '.json' if label == 'statement' else '.json.gz'
        altered = read(folder / 'adverse-inputs' / (row['case'] + suffix))
        args = [products['P1']['payload']['graph'], statement_result['answer']['incorporation']]
        if label == 'equity':
            args.append(statement_result['statement_review'])
        try:
            evaluate(*args, altered['profile'], ROOT, expected_profile_sha256=altered['expected_profile_sha256'])
        except ValueError as error:
            observed.append({'case': row['case'], 'refused': True, 'repinned': row['repinned'], 'reason': str(error)})
        else:
            raise AssertionError('Altered installed input accepted: ' + label + '/' + row['case'])
    assert observed == expected
    controls[label] = observed
save('controls.json', controls)
save('result.json', {'status': 'PASS', 'full_outputs_equal': True, 'native_calls': 0,
    'exact_package_files': len(actual), 'controls': {k: len(v) for k, v in controls.items()},
    'same_host_only': True, 'independent_legal_acceptance': False})
print({'status': 'PASS', 'full_outputs_equal': True, 'controls': {k: len(v) for k, v in controls.items()}})
