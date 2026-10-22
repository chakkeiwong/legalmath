"""Actual CLI and separate source-bound home-route answer verification."""
from copy import deepcopy
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

root, prep, here, mode = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path.insert(0, str(here / 'installed' if mode == 'installed' else root / 'src'))
from legalmath.cli import main
from legalmath.prospectus.successor import home_routes as model, issuer_qualification as issuer
from legalmath.prospectus.successor.home_routes_verify import verify
from legalmath.prospectus.successor.contracts import digest


def read(path): return json.loads(gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes())


def save(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
    with path.open('xb') as stream: stream.write(gzip.compress(raw, mtime=0) if path.suffix == '.gz' else raw)


began = time.monotonic(); config = read(prep / 'config.json')
manifest = root / config['profiles']; temporary = here / (mode + '-answer.json'); assert not temporary.exists()
sys.argv = ['legalmath', 'prospectus', 'consume', '--products', str(root / config['products']),
    '--repository', str(root), '--output', str(temporary), '--mode', 'frozen',
    '--conditional-profiles', str(manifest.relative_to(root)),
    '--conditional-profiles-sha256', hashlib.sha256(manifest.read_bytes()).hexdigest()]
main(); answer = read(temporary); baseline = read(root / config['baseline'])
products = {k: read(root / row['path']) for k, row in read(root / config['products'])['products'].items()}
profile = read(prep / 'profile.json'); expected = read(prep / 'expected.json')
checked = verify(answer, baseline, profile, products, root)
assert {r['id']: r['route_result'] for r in answer[model.KEY]['scenarios']} == expected
assert checked['changed_scenarios'] > 0
rows = {r['id']: r for r in answer[model.KEY]['scenarios']}
assert rows['automatic-foreign-only-german-excluded']['qualification_result']['status'] == 'NO'
assert rows['automatic-foreign-only-german-no-foreign-duty']['qualification_result']['status'] == 'YES'
assert rows['automatic-shared-admission-german-excluded']['qualification_result']['status'] == 'YES'
assert rows['automatic-shared-admission-german-excluded']['answer_changed'] is True
assert rows['provisional-foreign-only-eligible']['derived_qualification']['home_state'] is None
if mode == 'installed': assert answer == read(here / 'ordinary-answer.json.gz')
refusals = []


def refuse(name, call):
    try: call()
    except (ValueError, KeyError, TypeError, FileNotFoundError) as error:
        refusals.append({'case': name, 'kind': type(error).__name__, 'reason': str(error)})
    else: raise AssertionError('Adverse control accepted: ' + name)


changed = deepcopy(profile); changed['scenarios'][1]['facts']['seat'] = 'OTHER_EU_EEA'
refuse('profile-pin', lambda: model.evaluate(products, baseline, changed, root, expected_profile_sha256=digest(profile)))
changed = deepcopy(profile); changed['context']['displayed_law_temporal_applicability'] = 'PROVED'
refuse('source-temporal-context', lambda: model.evaluate(products, baseline, changed, root, expected_profile_sha256=digest(changed)))
for key, value in [('kind', 'ACTUAL'), ('route', 'SECTION2_13_OTHER'), ('base_case', 'missing')]:
    bad = deepcopy(profile); bad['scenarios'][1][key] = value
    refuse(key, lambda bad=bad: model.evaluate(products, baseline, bad, root, expected_profile_sha256=digest(bad)))
bad = deepcopy(profile); bad['scenarios'][1]['facts']['publication_under_section5'] = False
refuse('invented-automatic-publication-condition', lambda: model.evaluate(
    products, baseline, bad, root, expected_profile_sha256=digest(bad)))
bad = deepcopy(profile)
case = next(r for r in bad['scenarios'] if r['id'] == 'provisional-complete')
case['facts']['prior_election_at_choice'] = case['facts'].pop('prior_election_at_evaluation')
refuse('wrong-history-time', lambda: model.evaluate(products, baseline, bad, root, expected_profile_sha256=digest(bad)))
receipt_name = issuer.SOURCE + 'requests/issuer-definition/receipt.json'
copy = read(root / receipt_name); copy['status'] = 'SYNTHETIC_CHANGED_COPY'
altered = here / (mode + '-changed-receipt.json'); save(altered, copy)
original_path = issuer.bound_path
with patch.object(issuer, 'bound_path', side_effect=lambda repo, name: altered if name == receipt_name else original_path(repo, name)):
    refuse('changed-source-receipt', lambda: model.evaluate(products, baseline, profile, root, expected_profile_sha256=digest(profile)))
for kind in ('route-result', 'negative-home-inference', 'inconsistent-admission',
             'actual-home-state', 'historical-law', 'prior-answer'):
    bad = deepcopy(answer)
    if kind in ('route-result', 'negative-home-inference'):
        row = next(r for r in bad[model.KEY]['scenarios'] if r['id'] == 'automatic-seat-OTHER_EU_EEA')
        if kind == 'route-result': row['route_result']['statuses']['german_route'] = 'YES'
        else: row['derived_qualification']['home_state'] = 'NEITHER'
    elif kind == 'inconsistent-admission':
        row = next(r for r in bad[model.KEY]['scenarios'] if r['id'] == 'automatic-complete')
        row['derived_qualification']['admission_scope'] = 'ONLY_OTHER_EU_EEA'
    elif kind == 'actual-home-state': bad[model.KEY]['actual_home_state_established'] = True
    elif kind == 'historical-law': bad[model.KEY]['historical_application_proved'] = True
    else: bad['basf_agents']['calculation_agent_office'] = 'INVENTED'
    bad['report_sha256'] = digest({k: v for k, v in bad.items() if k != 'report_sha256'})
    refuse('rehashed-' + kind, lambda bad=bad: verify(bad, baseline, profile, products, root))
imports = {n: m.__file__ for n, m in sys.modules.items()
           if (n == 'legalmath' or n.startswith('legalmath.')) and getattr(m, '__file__', None)}
origin = (here / 'installed' if mode == 'installed' else root / 'src').resolve()
assert all(Path(p).resolve().is_relative_to(origin) for p in imports.values())
save(here / (mode + '-imports.json'), imports); save(here / (mode + '-answer.json.gz'), answer)
temporary.unlink()
save(here / (mode + '-verification.json'), {**checked, 'actual_cli': True,
    'complete_installed_equal': mode == 'installed', 'refusals': refusals,
    'module_origins_checked': len(imports), 'wall_seconds': time.monotonic() - began,
    'cpu_gpu': 'CPU;GPU intentionally hidden'})
print(json.dumps({'status': 'PASS', 'mode': mode, 'scenarios': checked['scenarios'],
                  'changed_scenarios': checked['changed_scenarios'], 'refusals': len(refusals)}))
