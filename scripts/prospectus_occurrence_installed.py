"""Separated, isolated installed replay of the actual initial-agent products."""
import gzip
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def save(path, value):
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2).encode()
    with path.open('xb') as out:
        out.write(gzip.compress(raw, compresslevel=1, mtime=0) if path.suffix == '.gz' else raw)


def main():
    here, root = [Path(p).resolve() for p in sys.argv[1:3]]
    mode = sys.argv[3]
    assert mode in ('construct', 'interpret', 'answer', 'omission', 'financial', 'controls')
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    frozen = read(here / 'methods.json')
    helper = Path(__file__).with_name('helpers.py')
    assert sha(helper) == frozen['scripts/prospectus_initial_agent_runner.py']
    assert sha(Path(__file__)) == frozen['scripts/prospectus_occurrence_installed.py']
    spec = importlib.util.spec_from_file_location('retained_initial_agent_helpers', helper)
    checks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checks)
    from legalmath.prospectus.successor import service
    package = Path(sys.prefix).resolve() / 'lib/python3.11/site-packages/legalmath'
    expected = read(here / 'source-package.json')
    actual = {str(p.relative_to(package)): sha(p) for p in package.rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    assert actual == expected and sys.flags.isolated == 1
    assert all(not Path(p).resolve().is_relative_to(root / 'src') for p in sys.path if p)
    aliases = read(here / 'input-aliases.json')
    def load(name):
        path = here / name
        if not path.exists():
            row = aliases[name]
            path = root / row['path']
            assert sha(path) == row['sha256']
        return read(path)
    def no_native(*args, **kwargs): raise AssertionError('Native child forbidden in installed replay')
    subprocess.Popen = no_native
    service.source_product = no_native
    folder = here / ('installed-' + mode)
    folder.mkdir(exist_ok=False)
    if mode == 'construct':
        built = checks.construct(load('baseline-products.json.gz'), root)
        assert built == load('construction-products.json.gz')
        save(folder / 'products.json.gz', built)
        result = {'status': 'PASS', 'full_constructed_P1_P2_equal': True}
    elif mode == 'interpret':
        built = read(here / 'installed-construct/products.json.gz')
        products = checks.finish(built['P1'], built['P2'], load('baseline-products.json.gz'))
        assert products == load('products.json.gz')
        save(folder / 'downstream-products.json.gz', {p: products[p] for p in ('P3', 'P4', 'P5')})
        result = {'status': 'PASS', 'full_rebuilt_P1_P5_equal': True}
    else:
        products = read(here / 'installed-construct/products.json.gz')
        products.update(read(here / 'installed-interpret/downstream-products.json.gz'))
        if mode == 'answer':
            value = service.consume(products, root, mode='frozen')
            assert value == load('ordinary-answer.json.gz')
            save(folder / 'ordinary-answer.json.gz', value)
            result = {'status': 'PASS', 'full_ordinary_answer_equal': True}
        elif mode == 'omission':
            omitted = checks.omission(products, load('baseline-products.json.gz'))
            assert omitted == load('omitted-products.json.gz')
            answer = service.consume(omitted, root, mode='frozen')
            assert answer == load('omitted-answer.json.gz')
            save(folder / 'omitted-answer.json.gz', answer)
            result = {'status': 'PASS', 'full_omitted_products_and_answer_equal': True}
        elif mode == 'financial':
            value, profiles = checks.financial(products, load('prior-profiles.json'), load('baseline-consumer.json.gz'), root)
            assert value == load('current-financial-consumer.json.gz') and profiles == load('financial-profiles.json')
            save(folder / 'current-financial-consumer.json.gz', value)
            result = {'status': 'PASS', 'full_financial_outputs_and_profiles_equal': True}
        else:
            value = checks.controls(products, load('baseline-products.json.gz'),
                load('current-financial-consumer.json.gz'), load('financial-profiles.json'), root)
            assert value == load('actual-controls.json')
            save(folder / 'controls.json', value)
            result = {'status': 'PASS', 'controls': len(value), 'actual_refusals_equal': True}
    proof = {'python': sys.executable, 'prefix': sys.prefix, 'isolated': sys.flags.isolated,
        'sys_path': sys.path, 'modules': {}, 'runner': {'path': str(Path(__file__)), 'sha256': sha(Path(__file__))},
        'helpers': {'path': str(helper), 'sha256': sha(helper)},
        'dependencies': {d.metadata['Name']: d.version for d in importlib.metadata.distributions()}}
    for name, module in list(sys.modules.items()):
        if name == 'legalmath' or name.startswith('legalmath.'):
            path = Path(module.__file__).resolve()
            assert path.is_relative_to(package) and sha(path) == expected[str(path.relative_to(package))]
            proof['modules'][name] = {'path': str(path), 'sha256': sha(path)}
    result.update(native_calls=0, http_calls=0, same_host_only=True)
    save(folder / 'import-proof.json', proof)
    save(folder / 'package-files.json', actual)
    save(folder / 'result.json', result)
    print(json.dumps(result))


if __name__ == '__main__': main()
