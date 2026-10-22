"""Build one prospectus phase from explicit, pinned supplied inputs."""
from pathlib import Path
import json
import os
from .anchors import fields
from .contracts import bound_path, digest, write
from .conditional_profiles import _read

VERSION = 'prospectus-preparation.v1'
MANIFEST_VERSION = 'prospectus-prepared-products.v1'
STAGES = ('P1', 'P2', 'P3', 'P4', 'P5')
RECIPE_LIMIT = 65536
INPUT_LIMIT = 64 * 1024 * 1024
PRODUCT_LIMIT = 128 * 1024 * 1024


def _relative(value):
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError('Preparation paths must be repository relative')
    return value


def load_recipe(root, path, pin):
    recipe = _read(root, path, pin, RECIPE_LIMIT)
    fields(recipe, {'version', 'inputs'}, {'version', 'inputs'})
    if recipe['version'] != VERSION:
        raise ValueError('Unsupported preparation recipe')
    specs = recipe['inputs']
    keys = {'request', 'interpretation', 'law', 'financial'}
    fields(specs, keys, keys)
    values = {}
    for name, row in specs.items():
        fields(row, {'path', 'sha256'}, {'path', 'sha256'})
        values[name] = _read(root, row['path'], row['sha256'], INPUT_LIMIT)
    if not isinstance(values['request'], dict):
        raise ValueError('Preparation requires an explicit request')
    if values['interpretation'] is not None and not isinstance(values['interpretation'], dict):
        raise ValueError('Interpretation input must be a mapping or null')
    for name, field in (('law', 'law_input'), ('financial', 'scenario_input')):
        value = values[name]
        fields(value, {'cases', field}, {'cases', field})
        if not isinstance(value['cases'], list) or (value[field] is not None and not isinstance(value[field], dict)):
            raise ValueError('Explicit phase case list and input required')
    return recipe, values


def load_parents(root, stage, recipe, recipe_pin, path=None, pin=None):
    from .service import verify, PRODUCT_VERSION
    previous = STAGES[:STAGES.index(stage)]
    if not previous:
        if path is not None or pin is not None:
            raise ValueError('P1 does not accept prepared parent products')
        return {}, {}
    if path is None or pin is None:
        raise ValueError('Later preparation stages require a pinned parent manifest')
    manifest = _read(root, path, pin, RECIPE_LIMIT)
    keys = {'version', 'recipe_sha256', 'products', 'prepared_through'}
    fields(manifest, keys, keys)
    if (manifest['version'] != MANIFEST_VERSION or manifest['recipe_sha256'] != recipe_pin
            or manifest['prepared_through'] != previous[-1]
            or not isinstance(manifest['products'], dict) or set(manifest['products']) != set(previous)):
        raise ValueError('Parent manifest recipe, sequence or stages differ')
    products = {}
    for name in previous:
        row = manifest['products'][name]
        fields(row, {'path', 'sha256'}, {'path', 'sha256'})
        products[name] = _read(root, row['path'], row['sha256'], PRODUCT_LIMIT)
        if products[name].get('version') != PRODUCT_VERSION:
            raise ValueError('Preparation requires current-version products')
        verify(products[name], name)
    request = products['P1']['payload']['request']
    if request != recipe['request']:
        raise ValueError('Parent request differs from explicit recipe input')
    bundle = request['bundle']
    links = {'P1':{'request':digest(request)}, 'P2':{'P1':products['P1']['sha256']}}
    if 'P2' in products:
        links['P3'] = {'P1':products['P1']['sha256'], 'P2':products['P2']['sha256']}
    if 'P3' in products:
        links['P4'] = {'P1':products['P1']['sha256'], 'P3':products['P3']['sha256']}
    for name in previous:
        verify(products[name], name, bundle, links[name])
    if 'P3' in products and products['P3']['payload'].get('interpretation_input') != recipe['interpretation']:
        raise ValueError('Parent interpretation differs from explicit recipe input')
    if 'P4' in products:
        law = products['P4']['payload']
        if law.get('law_input') != recipe['law']['law_input'] or law.get('cases') != recipe['law']['cases']:
            raise ValueError('Parent law input differs from explicit recipe input')
    return products, manifest['products']


def prepare(root, *, stage, recipe_path, recipe_sha256, output,
            parents_path=None, parents_sha256=None):
    from . import service
    root = Path(root).resolve()
    if stage not in STAGES:
        raise ValueError('Unknown preparation stage')
    _relative(output)
    folder = bound_path(root, output)
    if folder.exists():
        raise ValueError('Preparation output directory already exists; preserve prior evidence')
    recipe, inputs = load_recipe(root, recipe_path, recipe_sha256)
    parents, references = load_parents(root, stage, inputs, recipe_sha256, parents_path, parents_sha256)
    request = inputs['request']
    for document in request['bundle']['documents']:
        if digest(bound_path(root, document['path']).read_bytes()) != document['sha256']:
            raise ValueError('Source bytes changed before preparation: ' + document['id'])
    folder.mkdir(parents=True, exist_ok=False)
    try:
        if stage == 'P1':
            product = service.source_product(request, root)
        elif stage == 'P2':
            product = service.construction_product(parents['P1'], root)
        elif stage == 'P3':
            product = service.interpretation_product(parents['P1'], parents['P2'], inputs['interpretation'])
        elif stage == 'P4':
            x = inputs['law']
            product = service.law_product(parents['P1'], parents['P3'], x['cases'], x['law_input'])
        else:
            x = inputs['financial']
            product = service.financial_product(parents['P1'], parents['P2'], parents['P3'], x['cases'], x['scenario_input'])
        path = folder/(stage+'.json')
        temporary = path.with_name(path.name + '.' + str(os.getpid()) + '.tmp')
        with temporary.open('x', encoding='utf-8') as stream:
            json.dump(product, stream, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        raw = path.read_bytes()
        if len(raw) > PRODUCT_LIMIT:
            raise ValueError('Prepared product exceeds declared size bound; retained for review')
        row = {'path':str(path.relative_to(root)), 'sha256':digest(raw)}
        manifest = {'version':MANIFEST_VERSION, 'recipe_sha256':recipe_sha256,
                    'prepared_through':stage, 'products':{**references, stage:row}}
        manifest_path = folder/'products.json'
        write(manifest_path, manifest)
        receipt = {'status':'PREPARED', 'stage':stage, 'recipe_sha256':recipe_sha256,
                   'product_sha256':product['sha256'], 'product_file_sha256':row['sha256'],
                   'manifest':str(manifest_path.relative_to(root)), 'manifest_sha256':digest(manifest_path.read_bytes()),
                   'source_reextracted':stage == 'P1', 'legal_acceptance':False}
        write(folder/'receipt.json', receipt)
        return receipt
    except Exception as error:
        write(folder/'failure.json', {'type':type(error).__name__, 'message':str(error),
                                     'stage':stage, 'recipe_sha256':recipe_sha256})
        raise


def configure(commands):
    parser = commands.add_parser('prepare', help='Build one phase from pinned explicit inputs')
    parser.add_argument('--stage', required=True, choices=STAGES)
    parser.add_argument('--recipe', required=True)
    parser.add_argument('--recipe-sha256', required=True)
    parser.add_argument('--parents')
    parser.add_argument('--parents-sha256')
    parser.add_argument('--repository', default='.')
    parser.add_argument('--output', required=True, help='New repository-relative output directory')


def dispatch(args):
    return prepare(args.repository, stage=args.stage, recipe_path=args.recipe,
                   recipe_sha256=args.recipe_sha256, output=args.output,
                   parents_path=args.parents, parents_sha256=args.parents_sha256)
