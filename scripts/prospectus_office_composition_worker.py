"""Complete CLI office composition, independent decisions and adverse controls."""
from copy import deepcopy
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time

root, prep, here, mode = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path.insert(0, str(here / 'installed' if mode == 'installed' else root / 'src'))
from legalmath.cli import main
from legalmath.prospectus.successor import office_change as model
from legalmath.prospectus.successor.office_change_verify import verify
from legalmath.prospectus.successor.contracts import digest


def read(path): return json.loads(gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes())


def save(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + chr(10)).encode()
    with path.open('xb') as stream: stream.write(gzip.compress(raw, mtime=0) if path.suffix == '.gz' else raw)


started = time.monotonic(); config = read(prep / 'config.json')
manifest = root / config['profiles']; temporary = here / (mode + '-answer.json'); assert not temporary.exists()
sys.argv = ['legalmath', 'prospectus', 'consume', '--products', str(root / config['products']),
    '--repository', str(root), '--output', str(temporary), '--mode', 'frozen',
    '--conditional-profiles', str(manifest.relative_to(root)),
    '--conditional-profiles-sha256', hashlib.sha256(manifest.read_bytes()).hexdigest()]
main(); answer = read(temporary); baseline = read(root / config['baseline'])
products = {k: read(root / row['path']) for k,row in read(root / config['products'])['products'].items()}
profile = read(prep / 'profile.json'); expected = read(prep / 'expected.json')
checked = verify(answer, baseline, profile, products, root)
assert {r['scenario']['id']: r['conditional_office_preconditions']['status'] for r in answer[model.KEY]['scenarios']} == expected
if mode == 'installed': assert answer == read(here / 'ordinary-answer.json.gz')
refusals = []


def refuse(name, call):
    try: call()
    except (ValueError, KeyError, TypeError) as error:
        refusals.append({'case': name, 'kind': type(error).__name__, 'reason': str(error)})
    else: raise AssertionError('Adverse control accepted: ' + name)


changed = deepcopy(profile); changed['scenarios'][1]['replacement_country'] = 'COUNTRY_B'
refuse('profile-content-pin', lambda: model.evaluate(products, baseline, changed, root, expected_profile_sha256=digest(profile)))
changed_context = deepcopy(profile); changed_context['context']['office_reading']['quote'] += ' altered'
refuse('source-context', lambda: model.evaluate(products, baseline, changed_context, root, expected_profile_sha256=digest(changed_context)))
for key, value in [('kind', 'ACTUAL'), ('change_kind', 'AGENT_REMOVAL'), ('notice_case', 'missing')]:
    bad = deepcopy(profile); bad['scenarios'][1][key] = value
    refuse(key, lambda bad=bad: model.evaluate(products, baseline, bad, root, expected_profile_sha256=digest(bad)))
bad = deepcopy(profile); bad['scenarios'][1]['identity']['agent_id'] = 'other-agent'
refuse('agent-identity', lambda: model.evaluate(products, baseline, bad, root, expected_profile_sha256=digest(bad)))
for corruption in ('country-result', 'actual-designation', 'actual-effective', 'prior-answer'):
    bad_answer = deepcopy(answer)
    if corruption == 'country-result':
        row = next(r for r in bad_answer[model.KEY]['scenarios'] if r['scenario']['id'] == 'PUBLICATION-30-different')
        row['conditional_office_preconditions']['status'] = 'YES'
    elif corruption == 'actual-designation': bad_answer[model.KEY]['actual_office_designation'] = 'ESTABLISHED'
    elif corruption == 'actual-effective': bad_answer[model.KEY]['actual_change_effective'] = 'YES'
    else: bad_answer['basf_agents']['calculation_agent_office'] = 'A dealer address'
    bad_answer['report_sha256'] = digest({k:v for k,v in bad_answer.items() if k != 'report_sha256'})
    refuse('rehashed-' + corruption, lambda bad_answer=bad_answer: verify(bad_answer, baseline, profile, products, root))
imports = {n: m.__file__ for n,m in sys.modules.items() if (n == 'legalmath' or n.startswith('legalmath.')) and getattr(m, '__file__', None)}
origin = (here / 'installed' if mode == 'installed' else root / 'src').resolve()
assert all(Path(p).resolve().is_relative_to(origin) for p in imports.values())
save(here / (mode + '-imports.json'), imports); save(here / (mode + '-answer.json.gz'), answer)
temporary.unlink()
result = {**checked, 'actual_cli': True, 'complete_installed_equal': mode == 'installed',
    'refusals': refusals, 'module_origins_checked': len(imports), 'wall_seconds': time.monotonic() - started,
    'cpu_gpu': 'CPU;GPU intentionally hidden'}
save(here / (mode + '-verification.json'), result)
print(json.dumps({'status': 'PASS', 'mode': mode, 'scenarios': checked['scenarios'], 'refusals': len(refusals)}))
