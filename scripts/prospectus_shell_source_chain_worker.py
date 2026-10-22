"""Fresh full consumers with optional Shell source-chain evidence; no extraction."""
from copy import deepcopy
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT, OUT, MODE = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
assert MODE in ('ordinary', 'installed')
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
PACKAGE = OUT / 'installed' if MODE == 'installed' else ROOT / 'src'
sys.path.insert(0, str(PACKAGE))
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest

AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
PREP = AUTH / 'reviews/shell-source-chain-380'
ORIGINAL = AUTH / 'reviews/shell-maturity-361'
BASE = AUTH / 'attempts/finance-conventions/attempt-013'


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    if str(path).endswith('.gz'):
        raw = gzip.compress(raw, mtime=0)
    with path.open('xb') as stream:
        stream.write(raw)


def exact(a, b):
    assert json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(b, sort_keys=True, ensure_ascii=False)


def consume(request, graph):
    p1 = service.seal('P1', request['bundle'], {'request': digest(request)}, {'request': request, 'graph': graph})
    p2 = service.construction_product(p1, ROOT)
    p3 = service.interpretation_product(p1, p2)
    ps = {'P1': p1, 'P2': p2, 'P3': p3, 'P4': service.law_product(p1, p3),
          'P5': service.financial_product(p1, p2, p3)}
    return ps, service.consume(ps, ROOT, mode='frozen')


def rebind(ps, payload):
    ps = deepcopy(ps)
    bundle = ps['P1']['payload']['request']['bundle']
    ps['P2'] = service.seal('P2', bundle, {'P1': ps['P1']['sha256']}, payload)
    ps['P3'] = service.seal('P3', bundle, {'P1': ps['P1']['sha256'], 'P2': ps['P2']['sha256']}, ps['P3']['payload'])
    ps['P4'] = service.seal('P4', bundle, {'P1': ps['P1']['sha256'], 'P3': ps['P3']['sha256']}, ps['P4']['payload'])
    ps['P5'] = service.seal('P5', bundle, {'P2': ps['P2']['sha256'], 'P3': ps['P3']['sha256']}, ps['P5']['payload'])
    return ps


def corruptions(ps):
    for name in ('false-succession', 'false-publication', 'missing-agreement', 'universal-precedence',
                 'boolean-as-zero', 'missing-qualifier', 'omitted-review'):
        payload = deepcopy(ps['P2']['payload'])
        report = payload['contract_source_chain']
        if name == 'false-succession':
            report['trustee_history']['actual_succession_established'] = True
        elif name == 'false-publication':
            report['edition_link']['historical_publication'] = '2020-08-13'
        elif name == 'missing-agreement':
            report['onward_documents'].pop()
        elif name == 'universal-precedence':
            report['precedence']['condition'] = 'ALWAYS'
        elif name == 'boolean-as-zero':
            report['legal_applicability_established'] = 0
        elif name == 'missing-qualifier':
            report['sources']['conditions_and_agreements'].pop()
        else:
            payload.pop('contract_source_chain')
        yield name, rebind(ps, payload)


records = []
for name in read(PREP / 'cases.json'):
    path = ORIGINAL / (name + '-packet.json.gz')
    assert hashlib.sha256(path.read_bytes()).hexdigest() == read(PREP / 'input-bindings.json')[str(path.relative_to(ROOT))]
    packet = read(path)
    old_ps, old_answer = consume(packet['request'], packet['graph'])
    exact(old_answer, read(BASE / 'ordinary' / (name + '-answer.json.gz')))
    exact(old_ps['P5'], read(BASE / 'ordinary' / (name + '-P5.json.gz')))
    request = deepcopy(packet['request'])
    request['contract_source_chain'] = {'version': 'shell-contract-source-chain.v1'}
    ps, answer = consume(request, packet['graph'])
    exact(answer['questions'], old_answer['questions'])
    exact(ps['P2']['payload']['assembly'], old_ps['P2']['payload']['assembly'])
    exact(ps['P5']['payload'], old_ps['P5']['payload'])
    stable = lambda a: {k: v for k, v in a.items() if k not in
                       ('contract_source_chain', 'report_sha256', 'consumed_products', 'request_sha256')}
    exact(stable(answer), stable(old_answer))
    for suffix, value in (('products', ps), ('answer', answer), ('legacy-products', old_ps), ('legacy-answer', old_answer)):
        save(OUT / MODE / (name + '-' + suffix + '.json.gz'), value)
    if MODE == 'installed':
        for suffix, value in (('products', ps), ('answer', answer)):
            exact(value, read(OUT / 'ordinary' / (name + '-' + suffix + '.json.gz')))
    refusals = []
    if name == 'global-plain':
        for defect, bad in corruptions(ps):
            try:
                service.consume(bad, ROOT, mode='frozen')
            except ValueError as exc:
                assert 'source-chain' in str(exc)
                refusals.append({'id': defect, 'reason': str(exc), 'input_sha256': digest(bad)})
                save(OUT / MODE / 'adverse' / (defect + '.json.gz'), bad)
            else:
                raise AssertionError('Accepted rehashed source-chain forgery ' + defect)
        request_bad = deepcopy(request)
        for defect, profile in (('null-review', None), ('empty-review', {}), ('generic-profile', {'version': 'generic'})):
            request_bad['contract_source_chain'] = profile
            p1 = service.seal('P1', request_bad['bundle'], {'request': digest(request_bad)},
                              {'request': request_bad, 'graph': packet['graph']})
            try:
                service.construction_product(p1, ROOT)
            except ValueError as exc:
                refusals.append({'id': defect, 'reason': str(exc), 'input_sha256': digest(p1)})
                save(OUT / MODE / 'adverse' / (defect + '.json.gz'), p1)
            else:
                raise AssertionError('Accepted undeclared source-chain reading')
    records.append({'id': name, 'answer_sha256': digest(answer), 'refusals': refusals,
                    'legacy_equal': True, 'financial_questions_equal': True, 'assembly_equal': True})
origins = {n: m.__file__ for n, m in sys.modules.items()
           if (n == 'legalmath' or n.startswith('legalmath.')) and getattr(m, '__file__', None)}
assert all(Path(p).resolve().is_relative_to(PACKAGE.resolve()) for p in origins.values())
save(OUT / (MODE + '-imports.json'), origins)
save(OUT / (MODE + '-summary.json'), {'status': 'PASS', 'cases': records,
     'whole_task_complete': False, 'installed_ordinary_equal': MODE == 'installed'})
print(json.dumps({'status': 'PASS', 'mode': MODE, 'cases': len(records),
                  'refusals': sum(len(r['refusals']) for r in records)}))
