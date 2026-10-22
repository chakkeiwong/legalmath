"""One bounded source reconciliation and pre-repair ordinary-consumer probe."""
from copy import deepcopy
import gzip
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest
from scripts.prospectus_typed_delta import changes

AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
PREP = AUTH / 'reviews/basf-margin-production-268'
MARGINS = AUTH / 'attempts/basf-margins'
DONOR = AUTH / 'attempts/basf-meanings/attempt-019'
PLAN = 'docs/plans/prospectus-basf-margin-production-2026-10-18.md'


def read(path):
    path = Path(path)
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2).encode()
    with path.open('xb') as stream:
        stream.write(gzip.compress(data, mtime=0) if path.suffix == '.gz' else data)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def relative(path):
    return str(Path(path).relative_to(ROOT))


def products():
    result = read(DONOR / 'installed-construct/products.json.gz')
    result['P3'] = read(DONOR / 'installed-interpret/semantic.json.gz')
    result.update(read(DONOR / 'installed-complete/downstream-products.json.gz'))
    return result


def original_spec(p):
    """Transcribe immutable reviewed boundaries; infer no borders from geometry."""
    inputs = {}
    for i, name in ((1, 'scope-review.json'), (2, 'v3/scope-review.json'),
                    (3, 'scope-review.json.gz'), (3, 'cumulative-margin-ledger.json')):
        folder = MARGINS / f'attempt-{i:03d}'
        manifest = read(folder / 'outputs.json')
        path = folder / name
        assert sha(path) == manifest[name]
        inputs[relative(path)] = sha(path)
        inputs[relative(folder / 'outputs.json')] = sha(folder / 'outputs.json')
    listed = read(MARGINS / 'attempt-001/scope-review.json')
    redemption = read(MARGINS / 'attempt-002/v3/scope-review.json')
    remaining = read(MARGINS / 'attempt-003/scope-review.json.gz')
    ledger = read(MARGINS / 'attempt-003/cumulative-margin-ledger.json')
    raw = {u['id']: u for u in p['P1']['payload']['graph']['units']}
    from legalmath.prospectus.successor.occurrences import anchor
    bodies = [anchor(raw[f'basf-base-september-2022-exchange:p132:l{i}']) for i in range(20, 30)]
    groups = [{'id': 'listed-notice', 'family': 'listed', 'applies': True,
        'governors': listed['governors'], 'printed_governors': listed['governors'],
        'body': bodies, 'premises': listed['premises']}]
    for family, packet in (('redemption', redemption), ('remaining', remaining)):
        for group in packet['groups']:
            governors = group.get('raw_governors', group.get('governors'))
            groups.append({'id': group['id'], 'family': family,
                'applies': group['applicable_under_supplied_final_terms'],
                'governors': governors, 'printed_governors': group.get('printed_governors', governors),
                'body': group['raw_body'], 'premises': group['premises']})
    images = {**listed['images'], **redemption['images'], **remaining['images']}
    for path, expected in images.items():
        assert sha(ROOT / path) == expected
        inputs[path] = expected
    documents = p['P1']['payload']['request']['bundle']['documents']
    wanted = {'basf-base-september-2022-exchange', 'basf-2032-final'}
    sources = [{k: d[k] for k in ('id', 'path', 'sha256')} for d in documents if d['id'] in wanted]
    assert {s['id'] for s in sources} == wanted
    for source in sources:
        assert sha(ROOT / source['path']) == source['sha256']
        inputs[source['path']] = source['sha256']
    occurrences = [{k: row[k] for k in ('source', 'role', 'status', 'current_role')}
                   for row in ledger['occurrences']]
    assert len(groups) == 54 and len(occurrences) == 522
    assert len({o['source']['unit'] for o in occurrences}) == 522
    governed = [a['unit'] for g in groups for a in g['governors']]
    assert len(governed) == len(set(governed)) == 492
    assert set(governed) <= {o['source']['unit'] for o in occurrences}
    shared = {'listed-notices': listed['shared_outside_scope'],
        'tax-notice': redemption['shared_tax_notice_outside_both_bars'],
        'tax-amount': redemption['tax_amount_definition_outside_make_whole_margin']}
    spec = {'version': 'basf-printed-scope-spec.v1', 'sources': sources, 'groups': groups,
        'occurrences': occurrences, 'shared_outside_scope': shared,
        'anomalies': remaining['anomalies'], 'images': images, 'review_inputs': inputs,
        'scope': 'Supplied BASF2022 base and2032 final terms; reviewed printed extents only',
        'automatic_scope': False, 'independent_legal_acceptance': False}
    # Every literal in the new specification is checked against this current raw graph.
    anchors = [a for g in groups for k in ('governors', 'printed_governors', 'body', 'premises') for a in g[k]]
    anchors += [o['source'] for o in occurrences] + [a for v in shared.values() for a in v]
    from legalmath.prospectus.successor.anchors import bind
    for a in anchors:
        bind(p['P1']['payload']['graph'], a)
    return spec, inputs


def main():
    began = time.monotonic()
    PREP.mkdir(parents=True, exist_ok=True)
    save(PREP / 'preparation-started.json', {'command': sys.argv, 'stage_bound_seconds': 90,
        'cpu': 'CUDA_VISIBLE_DEVICES=-1', 'revision': read(AUTH / 'program.json')['revision']})
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Preparation90s bound')))
    signal.alarm(90)
    try:
        assert read(AUTH / 'program.json')['revision'] == 267
        p = products()
        spec, inputs = original_spec(p)
        for name in ('installed-construct/products.json.gz', 'installed-interpret/semantic.json.gz',
                     'installed-complete/downstream-products.json.gz', 'installed-answer/ordinary-answer.json.gz',
                     'outputs.json'):
            path = DONOR / name
            if name != 'outputs.json':
                assert sha(path) == read(DONOR / 'outputs.json')[name]
            inputs[relative(path)] = sha(path)
        for name in ('src/legalmath/prospectus/successor/service.py',
                     'src/legalmath/prospectus/execution_acceptance.py'):
            dest = PREP / 'pre-edit' / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((ROOT / name).read_bytes())
        baseline = service.consume(p, ROOT, mode='frozen')
        assert digest(baseline) == digest(read(DONOR / 'installed-answer/ordinary-answer.json.gz'))
        changed = dict(p)
        payload = deepcopy(p['P3']['payload']['interpretation_input'])
        payload['governing_admission']['governing'] = [e for e in payload['governing_admission']['governing']
            if not e['id'].startswith('basf-remaining-margin:')]
        changed['P3'] = service.interpretation_product(p['P1'], p['P2'], payload)
        for stage, function, args in (
            ('P4', service.law_product, (p['P1'], changed['P3'])),
            ('P5', service.financial_product, (p['P1'], p['P2'], changed['P3']))):
            old = p[stage]['payload']
            changed[stage] = function(*args, old['cases'], old['law_input' if stage == 'P4' else 'scenario_input'])
        answer = service.consume(changed, ROOT, mode='frozen')
        assert 'printed_margin_review' not in answer
        removed = {d['id'] for d in p['P3']['payload']['dependencies']} - {
            d['id'] for d in changed['P3']['payload']['dependencies']}
        assert len(removed) == 284
        save(PREP / 'spec.json', spec)
        save(PREP / 'source-inputs.json', inputs)
        save(PREP / 'pre-repair-omission.json.gz', {'products_delta': changes(p, changed),
            'answer_delta': changes(baseline, answer), 'products_sha256': digest(changed),
            'answer_sha256': digest(answer), 'removed_dependency_ids': sorted(removed)})
        result = {'status': 'PASS', 'reproduced_gap': 'Missing remaining family silently removes284 dependencies without scope-review diagnostic',
            'baseline_equal019': True, 'groups': 54, 'occurrences': 522, 'governors': 492,
            'selected_edges': len(p['P3']['payload']['interpretation_input']['governing_admission']['governing']),
            'original_source_anchors_checked': True, 'wall_seconds': time.monotonic() - began}
        save(PREP / 'preparation-result.json', result)
        print(json.dumps(result))
    except BaseException as exc:
        save(PREP / 'preparation-failure.json', {'type': type(exc).__name__, 'message': str(exc),
            'wall_seconds': time.monotonic() - began})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
