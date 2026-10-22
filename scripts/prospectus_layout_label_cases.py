"""Freeze source-read page spans before implementing layout/name composition."""
from copy import deepcopy
from datetime import datetime, timezone
import time
from scripts import prospectus_payment_categories as prior

ROOT, AUTH = prior.ROOT, prior.AUTH
PREP = AUTH / 'reviews/layout-labels-324'
PLAN = 'docs/plans/prospectus-layout-labels-2026-10-19.md'
METHOD = 'scripts/prospectus_layout_label_cases.py'
SOURCE_ATTEMPT = AUTH / 'attempts/source-bes-dep-09/attempt-002'
PRODUCT = SOURCE_ATTEMPT / 'original-P1.json.gz'
PDF = ROOT / 'docs/implementation/prospectus-integration-closure/bes-original-acquisition/attempt-001/bes-2010-en.pdf'
IMAGE = AUTH / 'attempts/source-bes-dep-09/attempt-001/bes-2010-en-p190.png'
PDF_HASH = 'f6c1196ffcbaed34dc4068b4fbc095b4494e421e224977bfa54b215134e32f25'
IMAGE_HASH = '72b2639000243b613adb1e8f9f96d3bd3126f970cbd6d59f7e5587cedca20e23'


def segment(unit, start=0, end=None):
    if end is None:
        end = len(unit['raw'])
    return {'unit': unit['id'], 'start': start, 'end': end, 'quote': unit['raw'][start:end]}


def layout(text, page=1, box=(40, 0, 600, 842)):
    return {'texts': [{'self_ref': 'body', 'label': 'text', 'text': text,
        'prov': [{'page_no': page, 'bbox': dict(zip(('l', 't', 'r', 'b'), box)) |
                  {'coord_origin': 'TOPLEFT'}}]}]}


def source_case():
    from legalmath.prospectus.successor.contracts import digest
    outputs = prior.read(SOURCE_ATTEMPT / 'outputs.json')
    assert prior.sha(PRODUCT) == outputs['original-P1.json.gz']
    assert prior.sha(PDF) == PDF_HASH and prior.sha(IMAGE) == IMAGE_HASH
    p1 = prior.read(PRODUCT)
    assert p1['stage'] == 'P1'
    assert p1['sha256'] == digest({k: v for k, v in p1.items() if k != 'sha256'})
    units = [u for u in p1['payload']['graph']['units']
             if u['document'] == 'bes-2010-en' and u['page'] == 190]
    assert len(units) == 53 and all(u['source_sha256'] == PDF_HASH for u in units)
    by_id = {u['id']: u for u in units}
    prefix = 'bes-2010-en:p190:l'
    # These selections come from the inspected source image and individual raw
    # lines, not the production layout adapter's output or geometric predicate.
    selected = [segment(by_id[prefix + str(i)], 4 if i == 26 else 0)
                for i in range(53) if i not in (4, 25)]
    assert by_id[prefix + '26']['raw'].startswith('190 Revisores Oficiais de Contas')
    body = '\n'.join(s['quote'] for s in selected)
    expected_names = []
    for label, source_parts in [
        ('Código dos Valores Mobiliários', [(17, 'Código dos Valores Mobiliários')]),
        ('Código dos Valores Mobiliários', [(22, 'Código dos Valores Mobiliários')]),
        ('Ordem dos Revisores Oficiais de Contas', [(24, 'Ordem dos'), (26, 'Revisores Oficiais de Contas')]),
        ('Código das Sociedades Comerciais', [(37, 'Código'), (38, 'das Sociedades Comerciais')])]:
        parts = []
        for number, text in source_parts:
            unit = by_id[prefix + str(number)]
            a = unit['raw'].index(text)
            parts.append(segment(unit, a, a + len(text)))
        expected_names.append({'label': label, 'source_pieces': parts})
    excluded = [segment(by_id[prefix + '4']), segment(by_id[prefix + '25']),
                segment(by_id[prefix + '26'], 0, 4)]
    return {'id': 'bes-original-body', 'origin': 'ORIGINAL_RETAINED_IMAGE_REVIEW',
        'raw_units': units, 'source_sha256': PDF_HASH, 'language': 'en',
        'quotation_convention': 'english', 'layout': layout(body, 190),
        'expected_status': 'PASS', 'expected_segments': selected, 'expected_excluded': excluded,
        'expected_names': expected_names, 'expected_use_labels': [r['label'] for r in expected_names],
        'expected_issue_kinds': [], 'source_authority_established': False,
        'source_files': {prior.rel(PRODUCT): prior.sha(PRODUCT), prior.rel(PDF): PDF_HASH,
                         prior.rel(IMAGE): IMAGE_HASH}}


def unit(identity, raw, y, *, left=50, page=1):
    from legalmath.prospectus.successor.contracts import digest
    # Whitespace and coordinates are authored mechanics; no extracted source is
    # fabricated. Synthetic identity is kept separate from the actual PDF case.
    words = []
    cursor, x = 0, left
    for word in raw.split(' '):
        start = cursor
        cursor += len(word) + 1
        if word:
            words.append({'text': word, 'start': start, 'end': start + len(word),
                          'bbox': [x, y, x + len(word), y + 8]})
            x += len(word) + 3
    return {'id': identity, 'document': 'constructed', 'source_sha256': 'b' * 64,
        'page': page, 'order': int(y), 'raw': raw, 'bbox': [left, y, x, y + 8],
        'words': words, 'language': 'en', 'visible': True,
        'block': identity, 'extraction': 'CONSTRUCTED_CASE', 'text_sha256': digest(raw.encode())}


def simple():
    a = unit('line1', '“Alpha', 10)
    margin = unit('margin', '190', 15, left=20)
    b = unit('line2', 'Beta” Alpha Beta.', 20)
    # The quoted occurrence and the later punctuation-bounded occurrence are
    # both complete Alpha Beta literal uses.
    parts = [segment(a, 1), segment(b, 0, 4)]
    return {'id': 'constructed-separated-margin', 'origin': 'CONSTRUCTED',
        'raw_units': [a, margin, b], 'source_sha256': 'b' * 64, 'language': 'en',
        'quotation_convention': 'english', 'layout': layout(a['raw'] + '\n' + b['raw']),
        'expected_status': 'PASS', 'expected_segments': [segment(a), segment(b)],
        'expected_excluded': [segment(margin)],
        'expected_names': [{'label': 'Alpha Beta', 'source_pieces': parts}],
        'expected_use_labels': ['Alpha Beta', 'Alpha Beta'], 'expected_issue_kinds': []}


def constructed():
    result = [simple()]
    for kind in ('changed-candidate', 'missing-geometry', 'bad-word-offset',
                 'overlapping-ownership', 'different-edition', 'partial-word-box',
                 'empty-body', 'duplicate-unit'):
        row = deepcopy(simple())
        row['id'] = kind
        row['expected_status'] = 'REFUSE'
        if kind == 'changed-candidate':
            row['layout']['texts'][0]['text'] = row['layout']['texts'][0]['text'].replace('Alpha', 'Alphx', 1)
        elif kind == 'missing-geometry':
            row['raw_units'][0]['words'][0]['bbox'] = None
        elif kind == 'bad-word-offset':
            row['raw_units'][0]['words'][0]['start'] = 2
        elif kind == 'overlapping-ownership':
            extra = deepcopy(row['layout']['texts'][0]); extra['self_ref'] = 'duplicate-body'
            row['layout']['texts'].append(extra)
        elif kind == 'different-edition':
            row['raw_units'][0]['source_sha256'] = 'c' * 64
        elif kind == 'partial-word-box':
            row['layout']['texts'][0]['prov'][0]['bbox']['l'] = 52
        elif kind == 'empty-body':
            row['layout']['texts'][0]['prov'][0]['bbox'].update(l=400, r=500)
        else:
            row['raw_units'].append(deepcopy(row['raw_units'][0]))
        result.append(row)
    row = deepcopy(simple())
    row['id'] = 'regions-do-not-pair-quotes'
    row['layout']['texts'] = [
        {'self_ref': 'first', 'label': 'text', 'text': row['raw_units'][0]['raw'],
         'prov': [{'page_no': 1, 'bbox': {'l': 40, 't': 0, 'r': 600, 'b': 19, 'coord_origin': 'TOPLEFT'}}]},
        {'self_ref': 'second', 'label': 'text', 'text': row['raw_units'][2]['raw'],
         'prov': [{'page_no': 1, 'bbox': {'l': 40, 't': 19, 'r': 600, 'b': 40, 'coord_origin': 'TOPLEFT'}}]}]
    row['expected_names'] = []
    row['expected_use_labels'] = []
    row['expected_issue_kinds'] = ['UNBALANCED_QUOTE', 'UNMATCHED_QUOTE']
    result.append(row)
    return result


def main():
    from legalmath.prospectus.execution_authority import Authority
    assert not (PREP / 'cases.json').exists() and not (PREP / 'candidate.py').exists()
    started = time.monotonic()
    assert prior.read(AUTH / 'program.json')['revision'] == 323
    events = [e for e in Authority(ROOT).events() if e.get('attempt') == prior.rel(prior.HERE)]
    assert events[-1]['kind'] == 'RECORD'
    assert prior.read(prior.HERE / 'result.json')['status'] == 'PASS'
    prior.save(PREP / 'accounting-start.json', {'prior': prior.costs(),
        'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
        'program_bytes': (AUTH / 'program.json').stat().st_size})
    original = source_case()
    cases = [original, *constructed()]
    prior.save(PREP / 'cases.json', {'version': 'layout-label-cases.v1', 'cases': cases,
        'raw_sources_replaced': False, 'scope_or_meaning_inferred': False})
    prior.save(PREP / 'cases-freeze.json', {'cases_sha256': prior.sha(PREP / 'cases.json'),
        'authoring_method': METHOD, 'authoring_method_sha256': prior.sha(ROOT / METHOD),
        'plan': PLAN, 'plan_sha256': prior.sha(ROOT / PLAN),
        'source_files': original['source_files'],
        'candidate_exists': False, 'frozen_at': datetime.now(timezone.utc).isoformat(),
        'temporal_separation': 'Same agent authored source intervals before candidate; not a blind annotation study'})
    elapsed = time.monotonic() - started
    assert elapsed < 30 and sum(p.stat().st_size for p in PREP.rglob('*') if p.is_file()) < 2 * 1024**2
    prior.save(PREP / 'case-preparation.json', {'status': 'PASS', 'cases': len(cases),
        'original_page_units': 53, 'wall_seconds': elapsed,
        'command': ['.venv/bin/python', '-m', 'scripts.prospectus_layout_label_cases']})
    print({'status': 'PASS', 'cases': len(cases), 'wall_seconds': elapsed})


if __name__ == '__main__':
    main()
