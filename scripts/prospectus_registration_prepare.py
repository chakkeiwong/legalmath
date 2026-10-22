"""One bounded, immutable reproduction before the registration-group repair."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import gzip
import json
import os
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.prospectus.execution_authority import Authority, REL, read, write, file_hash
from legalmath.prospectus.successor import service, cases, source_graph

REVIEW = ROOT / REL / 'reviews/registration-groups-253'
PRIOR = ROOT / REL / 'attempts/entitlement/attempt-008'
SOURCE = ROOT / REL / 'reviews/conversion-source-primary-251'
CHANGED = ('src/legalmath/prospectus/closure_mechanisms.py',
           'src/legalmath/prospectus/successor/financial_profiles.py')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def load(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def compressed(path, value):
    with path.open('xb') as stream:
        stream.write(gzip.compress(json.dumps(value, sort_keys=True, allow_nan=False).encode(), mtime=0))


def forbidden(*args, **kwargs):
    raise ValueError('No additional native PDF call is authorized')


def main():
    start = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('120s preparation bound')))
    signal.alarm(120)
    require(not (REVIEW / 'started.json').exists(), 'Preparation already started; no automatic retry')
    program, _, _ = Authority(ROOT).spec()
    require(program['revision'] == 252, 'Wrong preparation baseline')
    write(REVIEW / 'started.json', {'command': ['.venv/bin/python', 'scripts/prospectus_registration_prepare.py'],
          'at': datetime.now(timezone.utc).isoformat(), 'baseline_revision': 252}, exclusive=True)
    production = {str(p.relative_to(ROOT)): file_hash(p) for p in (ROOT / 'src/legalmath').rglob('*')
                  if p.is_file() and '__pycache__' not in p.parts}
    write(REVIEW / 'before-methods.json', production, exclusive=True)
    for name in CHANGED:
        path = REVIEW / 'before' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write((ROOT / name).read_bytes())
    bindings = read(SOURCE / 'source-bindings.json')
    for name, expected in bindings.items():
        require(file_hash(ROOT / name) == expected, 'Original source changed: ' + name)
    for name in ('result.json', 'run-manifest.json', 'outputs.json', 'RESULT.md'):
        path = PRIOR / name
        bindings[str(path.relative_to(ROOT))] = file_hash(path)
    baseline = read(SOURCE / 'baseline.json')
    require(cases.financial_cases(ROOT) == baseline, 'Original financial records changed')
    write(REVIEW / 'baseline.json', baseline, exclusive=True)
    excerpts = read(SOURCE / 'source-excerpts.json')
    write(REVIEW / 'source-excerpts.json', {k: [r for r in v if r['page'] in (43, 44, 129)]
          for k, v in excerpts.items()}, exclusive=True)
    source_graph.pdf_units = forbidden
    rows = []
    for prefix in ('bbva', 'seb'):
        path = PRIOR / (prefix + '-visible-products.json.gz')
        bindings[str(path.relative_to(ROOT))] = file_hash(path)
        prods = load(path)
        for kind in ('one-holder-two-registrations', 'two-holders-one-registration'):
            s = deepcopy(prods['P5']['payload']['scenario_input'])
            s['listed'] = False
            if prefix == 'bbva':
                s.update(five_eligible_closing_prices=[], adjusted_floor_price='3')
                field = 'liquidation_preference'
            else:
                s.pop('reviewed_current_market_price_sek', None)
                s['adjusted_floor_usd'] = '3'
                field = 'principal'
            s['holdings'] = [dict(legal_holder_id='holder-a', registration_name='Registration A', **{field: '5'}),
                             dict(legal_holder_id='holder-a' if kind.startswith('one') else 'holder-b',
                                  registration_name='Registration B' if kind.startswith('one') else 'Registration A',
                                  **{field: '5'})]
            p5 = service.financial_product(prods['P1'], prods['P2'], prods['P3'], scenario=s)
            answer = service.consume({**prods, 'P5': p5}, ROOT)
            q = answer['questions']['Q5']
            require(q['status'] == 'CONDITIONAL', 'Expected unsafe before answer did not reproduce')
            actual = sum(r['shares'] for r in q['value']['calculation']['holder_entitlements'])
            expected = 2 if kind.startswith('one') else 3
            require(actual != expected, 'Expected registration partition defect did not reproduce')
            rows.append({'issue': prefix, 'kind': kind, 'scenario': s, 'P5': p5, 'answer': answer,
                         'source_required_total_shares': expected, 'wrong_total_shares': actual,
                         'source_reuse': str(path.relative_to(ROOT))})
            print(json.dumps({'issue': prefix, 'kind': kind, 'wrong': actual, 'source_required': expected}), flush=True)
    compressed(REVIEW / 'before-primary.json.gz', rows)
    write(REVIEW / 'source-bindings.json', bindings, exclusive=True)
    write(REVIEW / 'preparation-result.json', {'status': 'PASS', 'seconds': time.monotonic() - start,
          'reproduced_primary_defects': len(rows), 'additional_native_calls': 0,
          'previous_measured_seconds': 95.48833898082376, 'previous_native_calls': 6,
          'historical_unmeasured_seconds': 'UNKNOWN'}, exclusive=True)
    signal.alarm(0)


if __name__ == '__main__':
    main()
