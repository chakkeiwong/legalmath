"""Independent current H1 unit acceptance; finite evidence, never whole source."""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import sys

AUTH = 'docs/implementation/prospectus-execution-authority'
BASE = AUTH + '/attempts/source-bes-dep-05'
DONOR = BASE + '/attempt-066'
CRITERION = 'individual-unit-conflict'
VERSION = 'h1-current-unit-acceptance.v1'
LATER = {'h1_individual_unit_review', 'h1_individual_unit_explanation',
         'h1_source_relationship_review', 'h1_source_relationship_explanation',
         'h1_reference_availability_review', 'h1_reference_availability_explanation'}
PRIOR = {'answer', 'cash_flow_review', 'cash_flow_explanation', 'risk_table_review',
         'risk_table_explanation', 'h1_scope_review', 'h1_scope_explanation'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    path = Path(path)
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inventory(directory):
    directory = Path(directory)
    return {str(p.relative_to(directory)): sha(p) for p in sorted(directory.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc', '.pyo'}}


def inputs(root):
    products = read(root / BASE / 'attempt-063/products.json.gz')
    profiles = read(root / BASE / 'attempt-063/profiles.json.gz')
    profiles['relationships'] = read(root / AUTH / 'reviews/h1-current-relationships-427/profile.json')
    profiles['references'] = read(root / AUTH / 'reviews/h1-reference-closure-429/profile.json.gz')
    return products, profiles


def consume(root, products, profiles):
    from legalmath.prospectus import h1_incorporation_scope
    from legalmath.prospectus.successor.contracts import digest
    return h1_incorporation_scope.consume(products, profiles['cash'], profiles['risk'], profiles['scope'], root,
        expected_cash_profile_sha256=digest(profiles['cash']), expected_risk_profile_sha256=digest(profiles['risk']),
        expected_profile_sha256=digest(profiles['scope']), unit_profile=profiles['unit'],
        expected_unit_profile_sha256=digest(profiles['unit']), relationship_profile=profiles['relationships'],
        expected_relationship_profile_sha256=digest(profiles['relationships']), reference_profile=profiles['references'],
        expected_reference_profile_sha256=digest(profiles['references']))


def proof(root, answer, *, adverse=False):
    from scripts.prospectus_h1_unit_oracle import verify
    products, profiles = inputs(root)
    require(set(answer) == PRIOR | LATER, 'Unknown complete current answer fields')
    prior = {k: answer[k] for k in PRIOR}
    original = read(root / BASE / 'attempt-016/profile.json') | {
        'full_units': read(root / BASE / 'attempt-016/source-units.json')}
    actual = answer['h1_individual_unit_review']
    explanation = answer['h1_individual_unit_explanation']
    profile, graph = profiles['unit'], products['P1']['payload']['graph']
    result = verify(actual, explanation, profile, graph, prior, original, root)
    old = read(root / BASE / 'attempt-017/answer-delta.json.gz')['h1_individual_unit_review']
    substantive = lambda v: {k: x for k, x in v.items() if k not in {'prior_sha256', 'profile_sha256'}}
    require(substantive(actual) == substantive(old), 'Historical unit meaning changed')
    controls = []
    if adverse:
        cases = {
            'same-unit-equality': lambda a: a['comparisons'][0].update(same_unit_financial_equality=True),
            'scale-swapped': lambda a: a['pages'][0]['cells'][2].update(scale_to_EUR=1000),
            'unknown-dash-zero': lambda a: a['pages'][0]['cells'][1].update(value=0, status='SOURCE_NUMBER'),
            'official-correction': lambda a: a.update(official_unit_correction_established=True),
            'selected-incorporation': lambda a: a.update(selected_incorporation_reading='overall-range'),
            'wrong-source-identity': lambda a: a['pages'][0]['cells'][2]['source'].update(unit='bes-interim-h1-2010:p53:l223'),
        }
        for name in (*cases, 'stale-prior-binding'):
            bad, bad_profile = deepcopy(actual), deepcopy(profile)
            if name == 'stale-prior-binding':
                bad_profile['prior_sha256'] = '0' * 64
            else:
                cases[name](bad)
            try:
                verify(bad, explanation, bad_profile, graph, prior, original, root)
            except ValueError as exc:
                controls.append({'case': name, 'refused': True, 'reason': str(exc)})
            else:
                raise ValueError('Independent oracle accepted ' + name)
    return {'proof': result, 'controls': controls}


def imported(target):
    target = Path(target).resolve()
    modules = {}
    for name, module in tuple(sys.modules.items()):
        if (name == 'legalmath' or name.startswith('legalmath.')) and getattr(module, '__file__', None):
            path = Path(module.__file__).resolve()
            require(path.is_relative_to(target / 'legalmath'), 'Wrong imported package origin: ' + name)
            modules[name] = {'path': str(path), 'sha256': sha(path)}
    require('legalmath.prospectus.h1_incorporation_scope' in modules, 'Actual public consumer not imported')
    return modules


def validate_submission(root, attempt, task):
    """Recompute the finite oracle and authenticate actual ordinary/installed use."""
    from legalmath.prospectus.execution_authority import Authority, digest, file_hash
    root, attempt = Path(root).resolve(), Path(attempt).resolve()
    selector = task['h1_current_unit_acceptance']
    require(set(selector) == {'version', 'freeze', 'donor'} and selector['version'] == VERSION
            and selector['donor'] == DONOR and task['id'] == 'source-bes-dep-05'
            and task['build_criteria_scope'] == [CRITERION], 'Wrong current unit submission scope')
    frozen = read(root / selector['freeze'])
    expected_files = sorted(set(frozen['evidence']) | {selector['freeze']})
    require(task['build_criterion_lineage'] == {CRITERION: {
        'version': 'criterion-evidence.v1', 'files': expected_files, 'trees': ['src/legalmath']}},
        'Incomplete criterion binding closure')
    require(all(file_hash(root / n) == h for n, h in frozen['evidence'].items()), 'Changed criterion source or method')
    production = inventory(root / 'src/legalmath')
    require(production == frozen['candidate_production'], 'Current production changed')
    donor = root / DONOR
    authority = Authority(root)
    event = next(e for e in reversed(authority.events()) if e.get('attempt') == DONOR and e['kind'] == 'RECORD')
    require(authority.retained_evidence_valid(event), 'Original066 evidence changed')
    require(read(donor / 'package.json')['files'] == frozen['baseline_production'], 'Wrong donor package schema or inventory')
    baseline = read(donor / 'ordinary-answer.json.gz')
    require(baseline == read(donor / 'installed-answer.json.gz'), 'Original066 answers differ')
    package = read(attempt / 'package.json')
    require(package['status'] == 'PASS' and package['files'] == production
            and inventory(attempt / 'installed/legalmath') == production, 'Installed package differs')
    import zipfile
    wheel = root / package['wheel']['path']
    require(file_hash(wheel) == package['wheel']['sha256'], 'Changed wheel')
    with zipfile.ZipFile(wheel) as archive:
        actual = {n.removeprefix('legalmath/'): hashlib.sha256(archive.read(n)).hexdigest()
                  for n in archive.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    require(actual == production, 'Wheel package inventory differs')
    for kind in ('ordinary', 'installed'):
        answer_path = attempt / (kind + '-answer.json.gz')
        answer = read(answer_path)
        receipt = read(attempt / (kind + '.json'))
        require(receipt['status'] == 'PASS' and receipt['answer_sha256'] == file_hash(answer_path)
                and answer == baseline, 'Complete current answer differs from066')
        require(receipt['evaluation'] == proof(root, answer, adverse=True), 'Independent unit proof or adverse results changed')
        target = root / 'src' if kind == 'ordinary' else attempt / 'installed'
        require(receipt['imports'] and 'legalmath.prospectus.h1_incorporation_scope' in receipt['imports'], 'Missing actual public import')
        for item in receipt['imports'].values():
            path = Path(item['path']).resolve()
            require(path.is_relative_to(target / 'legalmath') and file_hash(path) == item['sha256'], 'Invalid actual import proof')
        require(receipt['isolated'] is True, 'Wrong interpreter isolation')
        command = read(attempt / 'commands' / (kind + '.json'))
        expected_python = frozen['runtime']['ordinary_python' if kind == 'ordinary' else 'package_python']
        require(command['exit_code'] == 0 and command['argv'] == [expected_python, '-I', '-B',
                str(root / 'scripts/prospectus_h1_acceptance_program.py'), 'worker', '--kind', kind]
                and receipt['executable'] == str(Path(expected_python).resolve()), 'Actual command/runtime differs')
        require(command['environment']['CUDA_VISIBLE_DEVICES'] == '-1' and command['environment']['PIP_NO_INDEX'] == '1',
                'Unexpected worker environment')
    return True
