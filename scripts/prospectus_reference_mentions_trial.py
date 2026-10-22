"""Bounded, source-first reference-discovery trial under the prospectus authority."""
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from legalmath.prospectus.execution_authority import Authority, digest as authority_digest, file_hash
from legalmath.prospectus.successor.contracts import digest

AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
PREP = AUTH / 'reviews/reference-mentions-355'
HERE = AUTH / 'attempts/basf-references/attempt-094'
PLAN = 'docs/plans/prospectus-reference-mentions-2026-10-20.md'
METHOD = 'scripts/prospectus_reference_mentions_trial.py'
LEDGER = AUTH / 'attempts/basf-references/attempt-025/original-ledger-reconciliation.json.gz'
PRODUCTS = AUTH / 'reviews/conditional-cli-311/products.json'
TARGETS = ('src/legalmath/prospectus/successor/reference_mentions.py',
           'src/legalmath/prospectus/successor/service.py')
SECONDS_BOUND, BYTES_BOUND = 27000, 4096 * 1024**2


def read(path):
    path = Path(path)
    data = gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes()
    return json.loads(data)


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as out:
        json.dump(value, out, ensure_ascii=False, indent=2, allow_nan=False)
        out.write('\n')


def rel(path):
    return str(Path(path).relative_to(ROOT))


# Authored from the original source inventory, before a candidate implementation.
# Whitespace is projected back to exact selected and raw intervals, never inferred
# from a candidate report. Duplicate original lines may intentionally share a span.
HISTORICAL = [
 [('§ 1 Absatz (4)', 'SECTION_REFERENCE')],
 [('Absatz (b) dieses § 1 Absatz (3)', 'PARAGRAPH_REFERENCE')],
 [('§ 6 Absatz (2)', 'SECTION_REFERENCE')],
 [('§ 5 Absatz (1)', 'SECTION_REFERENCE')],
 [('§ 5 Absatz (1)', 'SECTION_REFERENCE')],
 [('Absatzes (2)', 'PARAGRAPH_REFERENCE')],
 [('Absatz (2)', 'PARAGRAPH_REFERENCE')],
 [('Absatz (2)', 'PARAGRAPH_REFERENCE')],
 [('§ 1 Absatz (3)(b)', 'SECTION_REFERENCE')],
 [('§ 1 Absatz (3)(b)', 'SECTION_REFERENCE')],
 [('§ 7', 'SECTION_REFERENCE')], [('§ 13', 'SECTION_REFERENCE')],
 [('§ 3 Absatz (1)', 'SECTION_REFERENCE')], [('§ 7', 'SECTION_REFERENCE')],
 [('§ 13', 'SECTION_REFERENCE')], [('§ 5 Absatz (2)', 'SECTION_REFERENCE')],
 [('§ 30 Absatz 2 des Wertpapiererwerbs- und Übernahmegesetzes (WpÜG)', 'SECTION_REFERENCE')],
 [('§ 13', 'SECTION_REFERENCE')], [('§ 5 Absatz (3)', 'SECTION_REFERENCE')],
 [('Absatz (b)', 'PARAGRAPH_REFERENCE')], [('§ 13', 'SECTION_REFERENCE')],
 [('Absatz (b)', 'PARAGRAPH_REFERENCE')], [('§ 13', 'SECTION_REFERENCE')],
 [('§ 13', 'SECTION_REFERENCE')],
 [('Absatzes (2) dieses § 5', 'PARAGRAPH_REFERENCE')],
 [('Absatzes [(5)] dieses § 5', 'PARAGRAPH_REFERENCE')],
 [('§ 13', 'SECTION_REFERENCE')], [('§ 13', 'SECTION_REFERENCE')],
 [('§ 801 Absatz 1 Satz 1 BGB', 'SECTION_REFERENCE')],
 [('§ 2 Absatz (2)', 'SECTION_REFERENCE')],
 [('Absatz (1)(b) und/oder (1)(c)', 'PARAGRAPH_REFERENCE')],
 [('Absatz (1)(a) und (1)(d) bis (g)', 'PARAGRAPH_REFERENCE')],
 [('Absatz (1)', 'PARAGRAPH_REFERENCE')], [('§ 11', 'SECTION_REFERENCE')],
 [('§ 10', 'SECTION_REFERENCE')], [('§ 15 Aktiengesetz', 'SECTION_REFERENCE')],
 [('§ 13', 'SECTION_REFERENCE')], [('Absatz 2', 'PARAGRAPH_REFERENCE')],
 [('§ 5 Absatz 3, Nr. 1 bis Nr. 8 des SchVG', 'SECTION_REFERENCE')],
 [('§ 18', 'SECTION_REFERENCE'), ('§§ 5 ff. SchVG', 'SECTION_REFERENCE')],
 [('§§ 5 ff. SchVG', 'SECTION_REFERENCE'), ('§§ 5 ff. SchVG', 'SECTION_REFERENCE')],
 [('Absatz (a)(ii) und (iii)', 'PARAGRAPH_REFERENCE')],
 [('§ 13', 'SECTION_REFERENCE')],
 [('§ 13', 'SECTION_REFERENCE'), ('§ 50 Absatz 1 des Wertpapierhandelsgesetzes', 'SECTION_REFERENCE')],
 [('Absatz (1)', 'PARAGRAPH_REFERENCE')], [('Absatz (1)', 'PARAGRAPH_REFERENCE')],
 [('§ 14 Absatz [4]', 'SECTION_REFERENCE')],
]
ADDITIONAL = [
 [('wie nachstehend definiert', 'IMPLICIT_REFERENCE')],
 [('wie nachstehend definiert', 'IMPLICIT_REFERENCE')],
 [('Section 1471(b) des U.S. Internal Revenue Code von 1986', 'SECTION_REFERENCE'),
  ('Section 1471 bis Section 1474 des Code', 'SECTION_REFERENCE')],
 [('Gesetzes zur Abwehr von Steuervermeidung und unfairem Steuerwettbewerb (Steueroasen-Abwehrgesetz)', 'NAMED_LAW_REFERENCE')],
 [('im oben genannten Sinn', 'IMPLICIT_REFERENCE')],
 [('wie unten definiert', 'IMPLICIT_REFERENCE')],
 [('Unterabsätzen (a), (b), (c) und (d)', 'PARAGRAPH_REFERENCE')],
 [('Vorschriften des SchVG', 'NAMED_LAW_REFERENCE')],
 [('Vorschriften des Aktiengesetzes', 'NAMED_LAW_REFERENCE')],
 [('vorstehend unter (a) und (b)', 'IMPLICIT_REFERENCE')],
 [('Für die Zwecke des Vorstehenden', 'IMPLICIT_REFERENCE')],
 [('zwingende gesetzliche Bestimmungen', 'UNSPECIFIED_LAW_REFERENCE')],
 [('U.S. Steuerrecht', 'UNSPECIFIED_LAW_REFERENCE')],
]

# Independent literal examples of the declared grammar, including unsupported
# syntax. These are not generated from implementation regular expressions.
GRAMMAR = [
    ('Die Zahlung richtet sich nach § 27 Absatz (4)(c).', [('§ 27 Absatz (4)(c)', 'SECTION_REFERENCE')], False),
    ('Siehe §\n42 Absatz\t(8).', [('§\n42 Absatz\t(8)', 'SECTION_REFERENCE')], False),
    ('Es gilt Absatz (3)(a) und (b).', [('Absatz (3)(a) und (b)', 'PARAGRAPH_REFERENCE')], False),
    ('Nach Absatzes [(12)] dieses § 23.', [('Absatzes [(12)] dieses § 23', 'PARAGRAPH_REFERENCE')], False),
    ('Ausnahmen in Unterabsätzen (d), (e) und (f).', [('Unterabsätzen (d), (e) und (f)', 'PARAGRAPH_REFERENCE')], False),
    ('Es gilt § 23 Absatz 2 des Mustergesetzes.', [('§ 23 Absatz 2 des Mustergesetzes', 'SECTION_REFERENCE')], False),
    ('Es gelten §§ 19 ff. BeispielG.', [('§§ 19 ff. BeispielG', 'SECTION_REFERENCE')], False),
    ('Section 893(c) of the Example Revenue Code applies.', [('Section 893(c) of the Example Revenue Code', 'SECTION_REFERENCE')], False),
    ('Section 101 to Section 104 of the Example Code.', [('Section 101 to Section 104 of the Example Code', 'SECTION_REFERENCE')], False),
    ('Der Betrag (wie unten definiert) ist zahlbar.', [('wie unten definiert', 'IMPLICIT_REFERENCE')], False),
    ('The amount, as defined below, is due.', [('as defined below', 'IMPLICIT_REFERENCE')], False),
    ('Vorstehend unter (c) und (d) genannte Fälle.', [('Vorstehend unter (c) und (d)', 'IMPLICIT_REFERENCE')], False),
    ('Die Vorschriften des Mustergesetzes gelten.', [('Vorschriften des Mustergesetzes', 'NAMED_LAW_REFERENCE')], False),
    ('Unberührt bleiben zwingende gesetzliche Bestimmungen.', [('zwingende gesetzliche Bestimmungen', 'UNSPECIFIED_LAW_REFERENCE')], False),
    ('Die Zinsen betragen 4,2 Prozent jährlich.', [], False),
    ('Absatzwirtschaft und Paragrafenpapier sind Wörter.', [], False),
    ('Der Absatz (welcher folgt) ist erläuternd.', [], True),
    ('Es gilt Absatz (4) und (', [('Absatz (4)', 'PARAGRAPH_REFERENCE')], True),
    ('Es gilt § ohne Nummer.', [], True),
    ('§ 71\nZahlungen nach § 72.', [('§ 71', 'SECTION_REFERENCE'), ('§ 72', 'SECTION_REFERENCE')], False),
    ('A recital mentions § 9 and later § 9.', [('§ 9', 'SECTION_REFERENCE'), ('§ 9', 'SECTION_REFERENCE')], False),
]


def independent_cases():
    cases = []
    for number, (text, phrases, issue) in enumerate(GRAMMAR):
        expected, position = [], 0
        for phrase, kind in phrases:
            start = text.index(phrase, position)
            expected.append({'start': start, 'end': start + len(phrase), 'raw': phrase, 'kind': kind})
            position = start + len(phrase)
        cases.append({'id': 'G' + str(number), 'text': text, 'expected': expected, 'issue_required': issue})
    return {'version': 'independent-reference-cases.v1', 'candidate_derived': False, 'cases': cases}


def project(request, a, b):
    """Independent exact projection; does not import candidate mapping code."""
    rows = []
    position = a
    for p in request['source_pieces']:
        left, right = max(a, p['start']), min(b, p['end'])
        if left >= right:
            continue
        assert left == position
        anchor = None
        if p['raw_binding'] is not None:
            raw = p['raw_binding']
            delta = raw['start'] - p['start']
            anchor = {k: raw[k] for k in ('unit', 'document', 'source_sha256')}
            anchor.update(start=left + delta, end=right + delta,
                          quote=request['text'][left:right])
        rows.append({'start': left, 'end': right, 'kind': p['kind'], 'source': anchor})
        position = right
    assert position == b
    return rows


def prepare():
    assert not PREP.exists() and not HERE.exists()
    program = read(AUTH / 'program.json')
    assert program['revision'] == 354
    events = Authority(ROOT).events()
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 93
    old = AUTH / 'attempts/basf-references/attempt-093'
    assert [e['kind'] for e in events if e.get('attempt') == rel(old)] == ['ADMIT', 'RECORD']
    for name, checksum in read(old / 'outputs.json').items():
        assert file_hash(old / name) == checksum
    from scripts.prospectus_bgb_onward_integration import costs as old_costs
    prior = old_costs()
    assert prior['combined_accounted_seconds'] + 120 + 300 < SECONDS_BOUND
    assert prior['combined_bytes'] + 128 * 1024**2 < BYTES_BOUND - 4 * 1024**2
    accounting_start = {'prior': prior,
        'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
        'program_bytes': (AUTH / 'program.json').stat().st_size,
        'production_bytes': {n: (ROOT / n).stat().st_size if (ROOT / n).exists() else 0 for n in TARGETS}}
    manifest = read(PRODUCTS)
    products = {}
    for stage, row in manifest['products'].items():
        assert file_hash(ROOT / row['path']) == row['sha256']
        products[stage] = read(ROOT / row['path'])
    answer = read(old / 'ordinary-answer.json.gz')
    text = products['P2']['payload']['assembly']['continuous_text']
    pieces = []
    for p in answer['definition_sources']['source_pieces']:
        raw = p.get('raw_binding')
        pieces.append({**{k: p[k] for k in ('start', 'end', 'text', 'kind')},
            'raw_binding': {k: raw[k] for k in ('unit', 'document', 'source_sha256', 'start', 'end', 'quote')} if raw else None})
    ids = {p['raw_binding']['unit'] for p in pieces if p['raw_binding']}
    raw_units = [{k: u[k] for k in ('id', 'document', 'source_sha256', 'raw', 'text_sha256')}
                 for u in products['P1']['payload']['graph']['units'] if u['id'] in ids]
    headers = []
    units = {u['unit']: u for u in products['P2']['payload']['assembly']['units']}
    for p in pieces:
        raw = p['raw_binding']
        unit = units.get(raw['unit']) if raw else None
        if unit and unit['role'] == 'HEADER' and re.fullmatch(r'§\s*[0-9]+', p['text']):
            headers.append({'start': p['start'], 'end': p['end'], 'unit': raw['unit']})
    request = {'version': 'reference-mention-request.v1', 'text': text,
        'text_sha256': digest(text.encode()), 'source_pieces': pieces,
        'raw_units': raw_units, 'section_headers': headers}
    ledger = read(LEDGER)
    expected = []
    for r in ledger['records']:
        historical = r['family'] == 'historical_candidate_lines'
        ident = ('H' if historical else 'A') + str(r['index'])
        source_ids = {p['original'].get('unit') for p in r['source_pieces']}
        phrases = (HISTORICAL if historical else ADDITIONAL)[r['index']]
        consumed = {}
        for phrase, kind in phrases:
            pattern = r'\s+'.join(re.escape(word) for word in phrase.split())
            spans = [(m.start(), m.end()) for m in re.finditer(pattern, text)
                if any(p['raw_binding'] and p['raw_binding']['unit'] in source_ids
                       and p['start'] < m.end() and m.start() < p['end'] for p in pieces)]
            assert len(spans) == sum(p == phrase for p, _ in phrases), (ident, phrase, spans)
            occurrence = consumed.get(phrase, 0)
            a, b = spans[occurrence]
            consumed[phrase] = occurrence + 1
            expected.append({'record': ident, 'start': a, 'end': b, 'raw': text[a:b],
                             'kind': kind, 'source_projection': project(request, a, b)})
    assert len({r['record'] for r in expected}) == 60
    # Complete source validation before creating an immutable preparation directory.
    position = 0
    raw_index = {u['id']: u for u in raw_units}
    for piece in pieces:
        assert piece['start'] == position and piece['end'] > position
        assert text[piece['start']:piece['end']] == piece['text']
        raw = piece['raw_binding']
        if raw:
            unit = raw_index[raw['unit']]
            assert unit['raw'][raw['start']:raw['end']] == piece['text'] == raw['quote']
            assert unit['document'] == raw['document'] and unit['source_sha256'] == raw['source_sha256']
            assert digest(unit['raw'].encode()) == unit['text_sha256']
        position = piece['end']
    assert position == len(text)
    PREP.mkdir(parents=True)
    save(PREP / 'accounting-start.json', accounting_start)
    save(PREP / 'request.json', request)
    save(PREP / 'independent-cases.json', independent_cases())
    save(PREP / 'expected.json', {'version': 'original-reference-mentions.v1',
        'source': rel(LEDGER), 'source_sha256': file_hash(LEDGER),
        'request_sha256': file_hash(PREP / 'request.json'), 'records': expected,
        'record_count': 60, 'candidate_derived': False, 'general_recall_established': False})
    (PREP / 'baseline').mkdir()
    (PREP / 'baseline/service.py').write_bytes((ROOT / TARGETS[1]).read_bytes())
    bindings = {rel(p): file_hash(p) for p in (PREP / 'request.json', PREP / 'expected.json', PREP / 'independent-cases.json',
        LEDGER, PRODUCTS, ROOT / PLAN, ROOT / METHOD, PREP / 'baseline/service.py', old / 'outputs.json')}
    save(PREP / 'source-freeze.json', {'bindings': bindings, 'candidate_executed': False,
        'source_expectations_from_candidate': False, 'original_records': 60,
        'distinct_expected_mentions': len({(r['start'], r['end'], r['kind']) for r in expected}),
        'previous_result_event': 'RECORD', 'previous_task_complete': False})
    proposal = deepcopy(program)
    proposal['revision'] = 355
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=PLAN, reason='Repair general mention discovery against the entire original60-record denominator without authored target leakage',
        reference_mention_discovery={'review': rel(PREP), 'original_task_complete': False,
            'accounted_seconds_bound': SECONDS_BOUND, 'bytes_bound_with_4MiB_reserve': BYTES_BOUND})
    # Production methods are frozen after admitted implementation. Old sealed
    # method snapshots remain inputs; active targets must not be admission pins.
    task['inputs'] = list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]
        + list(bindings) + [rel(PREP / 'source-freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 94
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 355
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(task_sha256=authority_digest(task), dossier=PLAN,
                remaining='093 ordinary/installed reading integration is recorded. General discovery, target/definition scope, historical law,default(f),office and incorporation remain open.',
                next_action='Execute source-bound discovery against original60 and independent grammar; reconcile exact unmatched/extra mentions before target-resolution continuation',
                stop_condition='94 cumulative admissions;300new command seconds/128MiB;27000accounted seconds/4096MiB including4MiB reserve;no unchanged retry')
        elif row['task'] == 'basf-meanings':
            row.update(remaining='020/021 attribution failures retained. Actual022 RECORD repairs task attribution,192 checked decisions and16 forgery refusals; no whole-task ACCEPT. Original meaning/exhaustiveness requirements remain.',
                next_action='Use sealed022 current attribution evidence; reconcile original default(f) meaning and explicit alternatives without repeating repaired020/021 attribution checks')
        elif row['task'] == 'basf-office':
            row['next_action'] = 'Preserve conditional notice/delivery calculations; determine role-specific designated-office evidence or retain an explicit conditional unknown; no dealer-address substitution or unchanged80-case retry'
    save(PREP / 'routes.json', routes)
    proposal['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    for name in TARGETS:
        proposal['continuation_review']['bindings'].pop(name, None)
    proposal['continuation_review']['bindings'].update({PLAN: file_hash(ROOT / PLAN),
        rel(PREP / 'routes.json'): file_hash(PREP / 'routes.json'),
        rel(PREP / 'source-freeze.json'): file_hash(PREP / 'source-freeze.json')})
    review = {'baseline': authority_digest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['One reusable source-bound discovery API/CLI, without another pinned answer supplement',
                    'Correct stale093 and meanings022 routes; preserve all original obligations and evidence'],
        'skeptical_audit': {'verdict': 'PASS', 'review': PLAN,
            'wrong_baseline_rejected': 'Original expected spans, not candidate or authored answer links',
            'resources': 'Explicit cumulative extension; smaller new discovery consumers; no full-answer claim'},
        'evidence_contract': {'primary': 'Exact original mention/source reconciliation and complete installed discovery equality',
            'promotion_veto': ['Missing original span', 'Forged raw source', 'Invented target', 'False closure', 'Wrong installed import'],
            'continuation_veto': ['Corrupt frozen evidence', 'Unreviewed drift', 'Cumulative resource exhaustion'],
            'explanatory_only': ['Counts', 'Runtime'],
            'not_concluded': ['General recall', 'Target resolution', 'Legal meaning', 'History', 'Build completion']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 93, 'new_maximum': 94,
            'retained_attempts': attempts, 'reason': 'Fragmented discovery leaves original relative/implicit/law mentions uncovered',
            'next_discriminating_check': 'Original60 exact-span discovery,independent grammar and isolated installed CLI',
            'stop_condition': '300new command seconds/128MiB;27000seconds/4096MiB cumulative;no unchanged retry',
            'same_scope_authorization': 'User directed refresh and continued internally supported general build'},
        'resource_accounting': {'retained_costs': prior, 'limits_extended': True,
            'old_seconds_bound': prior['seconds_bound'], 'new_seconds_bound': SECONDS_BOUND,
            'old_bytes_bound': prior['bytes_bound_with_4MiB_reserve'], 'new_bytes_bound': BYTES_BOUND,
            'reason': 'Preserve all costs and immutable revision copies while testing actual general discovery',
            'additional_conservative_authoring_charge_seconds': 120, 'older_unmeasured_time': 'UNKNOWN'}}
    save(PREP / 'proposal.json', proposal)
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 355, 'records': 60,
        'distinct_expected_mentions': read(PREP / 'source-freeze.json')['distinct_expected_mentions'],
        'candidate_executed': False, 'prior_accounted_seconds': prior['combined_accounted_seconds']}


def main():
    if sys.argv[1:] != ['prepare']:
        raise ValueError('Only source-first preparation is available before admission')
    print(json.dumps(prepare()))


if __name__ == '__main__':
    main()
