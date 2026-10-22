"""Independent installed construction, split interpretation and answer replay."""
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
    assert mode in ('construct', 'interpret', 'complete', 'answer',
                   'omission-interpret', 'omission', 'financial', 'controls')
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    frozen = read(here / 'methods.json')
    helper = Path(__file__).with_name('helpers.py')
    assert sha(helper) == frozen['scripts/prospectus_initial_agent_runner.py']
    assert sha(Path(__file__)) == frozen['scripts/prospectus_initial_answer_installed.py']
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

    def constructed(): return read(here / 'installed-construct/products.json.gz')
    def rebuilt():
        products = constructed()
        products['P3'] = read(here / 'installed-interpret/semantic.json.gz')
        products.update(read(here / 'installed-complete/downstream-products.json.gz'))
        return products

    def development_omitted():
        retained = load('products.json.gz')
        return {'P1': retained['P1'], 'P2': retained['P2'],
                'P3': load('omitted-P3.json.gz'),
                **load('omitted-downstream-products.json.gz')}

    if mode == 'construct':
        built = checks.construct(load('baseline-products.json.gz'), root)
        save(folder / 'products.json.gz', built)
        assert built == load('construction-products.json.gz')
        result = {'status': 'PASS', 'full_constructed_P1_P2_equal': True}
    elif mode == 'interpret':
        built, before = constructed(), load('baseline-products.json.gz')
        semantic = service.interpretation_product(built['P1'], built['P2'], before['P3']['payload']['interpretation_input'])
        save(folder / 'semantic.json.gz', semantic)
        assert semantic == load('products.json.gz')['P3']
        result = {'status': 'PASS', 'fresh_full_P3_equal': True}
    elif mode == 'complete':
        built = constructed()
        semantic = read(here / 'installed-interpret/semantic.json.gz')
        products = checks.complete(built['P1'], built['P2'], load('baseline-products.json.gz'), semantic)
        save(folder / 'downstream-products.json.gz', {p: products[p] for p in ('P4', 'P5')})
        assert products == load('products.json.gz')
        result = {'status': 'PASS', 'fresh_P4_P5_and_complete_P1_P5_equal': True}
    else:
        products = rebuilt()
        if mode == 'answer':
            value = service.consume(products, root, mode='frozen')
            save(folder / 'ordinary-answer.json.gz', value)
            assert value == load('ordinary-answer.json.gz')
            checks.compare_answers(load('baseline-consumer.json.gz')['answer'], value, products)
            result = {'status': 'PASS', 'full_ordinary_answer_equal': True, 'exact_delta': True}
        elif mode == 'omission-interpret':
            semantic = service.interpretation_product(products['P1'], products['P2'],
                checks.omission_input(load('baseline-products.json.gz')))
            save(folder / 'semantic.json.gz', semantic)
            assert semantic == load('omitted-P3.json.gz')
            result = {'status': 'PASS', 'fresh_full_omitted_P3_equal': True, 'same_changed_P1_P2': True}
        elif mode == 'omission':
            semantic = read(here / 'installed-omission-interpret/semantic.json.gz')
            omitted = checks.complete(products['P1'], products['P2'], products, semantic)
            save(folder / 'downstream-products.json.gz', {p: omitted[p] for p in ('P4', 'P5')})
            assert omitted == development_omitted()
            answer = service.consume(omitted, root, mode='frozen')
            save(folder / 'omitted-answer.json.gz', answer)
            assert answer == load('omitted-answer.json.gz')
            result = {'status': 'PASS', 'full_fresh_omitted_products_and_answer_equal': True}
        elif mode == 'financial':
            value, profiles = checks.financial(products, load('prior-profiles.json'), load('baseline-consumer.json.gz'), root)
            save(folder / 'current-financial-consumer.json.gz', value)
            save(folder / 'financial-profiles.json', profiles)
            assert value == load('current-financial-consumer.json.gz') and profiles == load('financial-profiles.json')
            result = {'status': 'PASS', 'full_fresh_financial_outputs_and_profiles_equal': True}
        else:
            value = checks.controls(products, load('baseline-products.json.gz'),
                load('current-financial-consumer.json.gz'), load('financial-profiles.json'), root)
            save(folder / 'controls.json', value)
            assert value == load('actual-controls.json')
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
