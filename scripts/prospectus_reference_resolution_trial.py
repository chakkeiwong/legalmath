"""Source-first preparation for the original reference-resolution continuation."""
from copy import deepcopy
from pathlib import Path
import json
import sys

from scripts import prospectus_reference_mentions_trial as old
from scripts.prospectus_reference_mentions_run import costs as prior_costs

ROOT, AUTH = old.ROOT, old.AUTH
PREP = AUTH / 'reviews/reference-resolution-356'
HERE = AUTH / 'attempts/basf-references/attempt-095'
PLAN = 'docs/plans/prospectus-reference-resolution-2026-10-20.md'
METHOD = 'scripts/prospectus_reference_resolution_trial.py'
TARGETS = ('src/legalmath/prospectus/successor/reference_resolution.py',
           'src/legalmath/prospectus/successor/service.py')
read, save, rel, sha = old.read, old.save, old.rel, old.file_hash
SECONDS_BOUND, BYTES_BOUND = 27000, 4096 * 1024**2

# Printed addresses transcribed from original source descriptions, not a new
# candidate. None denotes a law/implicit/unresolved reference, never a guess.
H_PATHS = [
 ('1', [['4']]), ('1', [['3', 'b']]), ('6', [['2']]),
 ('5', [['1']]), ('5', [['1']]), ('4', [['2']]), ('4', [['2']]), ('4', [['2']]),
 ('1', [['3', 'b']]), ('1', [['3', 'b']]), ('7', [[]]), ('13', [[]]),
 ('3', [['1']]), ('7', [[]]), ('13', [[]]), ('5', [['2']]), None,
 ('13', [[]]), ('5', [['3']]), ('5', [['4', 'b']]), ('13', [[]]),
 ('5', [['5', 'b']]), ('13', [[]]), ('13', [[]]), ('5', [['2']]),
 ('5', [['5']]), ('13', [[]]), ('13', [[]]), None, ('2', [['2']]),
 ('9', [['1', 'b'], ['1', 'c']]),
 ('9', [['1', 'a'], ['1', 'd'], ['1', 'e'], ['1', 'f'], ['1', 'g']]),
 ('9', [['1']]), ('11', [[]]), ('10', [[]]), None, ('13', [[]]),
 ('11', [['2']]), None, None, None,
 ('11', [['7', 'a', 'ii'], ['7', 'a', 'iii']]), ('13', [[]]),
 ('13', [[]]), ('13', [['1']]), ('13', [['1']]), ('14', [['4']])]


def independent_cases():
    # Literal fixtures authored before the candidate, with arbitrary labels and
    # expected destinations. They are not generated from a parser's patterns.
    cases = [
        ('explicit', ['§ 27', '(1) Siehe § 42 Absatz (2).', '§ 42', '(1) Erstes.', '(2) Zweites.'],
         [('§ 42 Absatz (2)', 'STRUCTURAL_ADDRESS', '42', [['2']])]),
        ('relative-list', ['§ 27', '(1) Beginn.', '(a) Erstes.', '(b) Zweites.', '(c) Siehe Absatz (a) bis (b).'],
         [('Absatz (a) bis (b)', 'STRUCTURAL_ADDRESS', '27', [['1', 'a'], ['1', 'b']])]),
        ('compound-self', ['§ 27', '(3) Beginn.', '(b) Es gilt Absatz (b) dieses § 27 Absatz (3).'],
         [('Absatz (b) dieses § 27 Absatz (3)', 'STRUCTURAL_ADDRESS', '27', [['3', 'b']])]),
        ('shared-law', ['§ 18', '(1) Vertragsbestimmung.', '§ 27', '(1) Es gelten § 18 und §§ 5 ff. BeispielG.'],
         [('§ 18', 'EXTERNAL_LAW_REFERENCE', None, []), ('§§ 5 ff. BeispielG', 'EXTERNAL_LAW_REFERENCE', None, [])]),
        ('external-name', ['§ 27', '(1) Es gilt § 23 Absatz 2 des Mustergesetzes.'],
         [('§ 23 Absatz 2 des Mustergesetzes', 'EXTERNAL_LAW_REFERENCE', None, [])]),
        ('missing', ['§ 27', '(1) Siehe § 42 Absatz (2).'],
         [('§ 42 Absatz (2)', 'UNRESOLVED_STRUCTURE', None, [])]),
        ('duplicate-section', ['§ 27', '(1) Erstes.', '§ 27', '(1) Siehe Absatz (1).'],
         [('Absatz (1)', 'UNRESOLVED_STRUCTURE', None, [])]),
        ('ambiguous-i', ['§ 27', '(1) Beginn.', '(h) Achtes.', '(i) Siehe Absatz (h).'],
         [('Absatz (h)', 'UNRESOLVED_STRUCTURE', None, [])]),
        ('no-header', ['Es gilt Absatz (2).'], [('Absatz (2)', 'UNRESOLVED_CONTEXT', None, [])]),
        ('implicit', ['§ 27', '(1) Der Betrag ist wie unten definiert.'],
         [('wie unten definiert', 'UNRESOLVED_IMPLICIT', None, [])]),
        ('split', ['§ 27', '(1) Siehe § 42', 'Absatz (2).', '§ 42', '(2) Ziel.'],
         [('§ 42\nAbsatz (2)', 'STRUCTURAL_ADDRESS', '42', [['2']])]),
        ('roman', ['§ 27', '(7) Beginn.', '(a) Oberpunkt.', '(ii) Zweites.', '(iii) Es gilt Absatz (a)(ii).'],
         [('Absatz (a)(ii)', 'STRUCTURAL_ADDRESS', '27', [['7', 'a', 'ii']])]),
        ('direct-components', ['§ 27', '(1) Siehe § 42(2).', '§ 42', '(2) Ziel.'],
         [('§ 42(2)', 'STRUCTURAL_ADDRESS', '42', [['2']])]),
    ]
    output = []
    for ident, lines, expected in cases:
        text, units, pieces, headers, layout = '\n'.join(lines), [], [], [], []
        document_hash, pos = old.digest(('document:' + ident).encode()), 0
        for index, line in enumerate(lines):
            unit = ident + ':' + str(index)
            raw = {'unit': unit, 'document': ident, 'source_sha256': document_hash,
                   'start': 0, 'end': len(line), 'quote': line}
            units.append({'id': unit, 'document': ident, 'source_sha256': document_hash,
                          'raw': line, 'text_sha256': old.digest(line.encode())})
            pieces.append({'start': pos, 'end': pos + len(line), 'text': line,
                           'kind': 'EXACT_SOURCE_COPY', 'raw_binding': raw})
            is_header = old.re.fullmatch(r'§\s*[0-9]+', line) is not None
            if is_header:
                headers.append({'start': pos, 'end': pos + len(line), 'unit': unit})
            layout.append({'unit': unit, 'context': ident + ':context', 'role': 'HEADER' if is_header else 'OPERATIVE'})
            pos += len(line)
            if index < len(lines) - 1:
                pieces.append({'start': pos, 'end': pos + 1, 'text': '\n',
                               'kind': 'GENERATED_SEPARATOR', 'raw_binding': None})
                pos += 1
        source = {'version': 'reference-mention-request.v1', 'text': text,
                  'text_sha256': old.digest(text.encode()), 'raw_units': units,
                  'source_pieces': pieces, 'section_headers': headers}
        output.append({'id': ident, 'request': {'version': 'reference-resolution-request.v1', 'source': source,
                                               'layout': layout},
                       'expected': [{'raw': raw, 'status': status, 'section': section, 'paths': paths}
                                    for raw, status, section, paths in expected]})
    return {'candidate_derived': False, 'cases': output}


def prepare():
    assert not PREP.exists() and not HERE.exists()
    program = read(AUTH / 'program.json')
    assert program['revision'] == 355
    events = old.Authority(ROOT).events()
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 94
    previous = AUTH / 'attempts/basf-references/attempt-094'
    assert [e['kind'] for e in events if e.get('attempt') == rel(previous)] == ['ADMIT', 'RECORD']
    for name, checksum in read(previous / 'outputs.json').items():
        assert sha(previous / name) == checksum
    prior = prior_costs()
    assert prior['combined_accounted_seconds'] + 120 + 300 < SECONDS_BOUND
    assert prior['combined_bytes'] + 128 * 1024**2 < BYTES_BOUND - 4 * 1024**2
    products = {}
    for stage, row in read(old.PRODUCTS)['products'].items():
        assert sha(ROOT / row['path']) == row['sha256']
        products[stage] = read(ROOT / row['path'])
    answer = read(AUTH / 'attempts/basf-references/attempt-093/ordinary-answer.json.gz')
    source = read(old.PREP / 'request.json')
    units = {u['unit']: u for u in products['P2']['payload']['assembly']['units']}
    assert all(p['raw_binding']['unit'] in units for p in source['source_pieces'] if p['raw_binding'])
    layout = [{k: units[u['id']][k] for k in ('unit', 'context', 'role')} for u in source['raw_units']]
    request = {'version': 'reference-resolution-request.v1', 'source': source, 'layout': layout}
    expected = []
    for row in read(old.PREP / 'expected.json')['records']:
        ident = row['record']
        address = H_PATHS[int(ident[1:])] if ident.startswith('H') else (
            ('10', [['1', 'a'], ['1', 'b'], ['1', 'c'], ['1', 'd']]) if ident == 'A6' else None)
        # H43 also contains an explicit WpHG citation. Its §13 expectation has
        # a printed address, but its second expectation is statutory.
        if ident == 'H43' and row['raw'] != '§ 13':
            address = None
        status = ('SECTION_CONTAINER' if address and address[1] == [[]] else 'STRUCTURAL_ADDRESS') if address else (
            'UNRESOLVED_IMPLICIT' if row['kind'] == 'IMPLICIT_REFERENCE' else
            'UNRESOLVED_UNSPECIFIED_LAW' if row['kind'] == 'UNSPECIFIED_LAW_REFERENCE' else 'EXTERNAL_LAW_REFERENCE')
        expected.append({**row, 'status': status, 'section': address[0] if address else None,
                         'paths': address[1] if address else []})
    ledger = read(old.LEDGER)
    references = {}
    for row in ledger['records']:
        ref = row['current_reference']
        if ref is None:
            continue
        slim = {'id': ref['id'], 'source': {k: ref['source'][k] for k in ('unit', 'document', 'source_sha256', 'start', 'end', 'quote')},
                'targets': [{k: t['source'][k] for k in ('unit', 'document', 'source_sha256', 'start', 'end', 'quote')} for t in ref['targets']]}
        assert slim['id'] not in references or references[slim['id']] == slim
        references[slim['id']] = slim
    graph_units = {s['unit'] for r in references.values() for s in [r['source'], *r['targets']]}
    raw = [dict((k, u[k]) for k in ('id', 'document', 'source_sha256', 'raw', 'text_sha256'))
           for u in products['P1']['payload']['graph']['units'] if u['id'] in graph_units]
    assert {u['id'] for u in raw} == graph_units
    graph = {'version': 'reviewed-reference-graph.v1', 'references': list(references.values()), 'raw_units': raw}
    for ref in graph['references']:
        for anchor in [ref['source'], *ref['targets']]:
            unit = next(u for u in raw if u['id'] == anchor['unit'])
            assert unit['document'] == anchor['document'] and unit['source_sha256'] == anchor['source_sha256']
            assert unit['raw'][anchor['start']:anchor['end']] == anchor['quote']
    PREP.mkdir(parents=True)
    save(PREP / 'accounting-start.json', {'prior': prior,
        'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
        'program_bytes': (AUTH / 'program.json').stat().st_size,
        'production_bytes': {n: (ROOT / n).stat().st_size if (ROOT / n).exists() else 0 for n in TARGETS}})
    save(PREP / 'request.json', request)
    save(PREP / 'expected.json', {'records': expected, 'record_count': 60, 'candidate_derived': False})
    save(PREP / 'reviewed-graph.json', graph)
    save(PREP / 'independent-cases.json', independent_cases())
    save(PREP / 'prior-index.json', [{k: n[k] for k in ('section', 'path', 'start', 'end', 'unit', 'document', 'context', 'printed_label')}
        for n in answer['reference_addresses']['index']])
    save(PREP / 'retained-statutory-records.json', answer['statutory_references'])
    (PREP / 'baseline').mkdir()
    (PREP / 'baseline/service.py').write_bytes((ROOT / TARGETS[1]).read_bytes())
    paths = [PREP / n for n in ('request.json', 'expected.json', 'reviewed-graph.json', 'prior-index.json',
        'retained-statutory-records.json', 'baseline/service.py', 'independent-cases.json')]
    paths += [old.LEDGER, old.PRODUCTS, old.PREP / 'request.json', old.PREP / 'expected.json',
        previous / 'outputs.json', ROOT / PLAN, ROOT / METHOD]
    bindings = {rel(p): sha(p) for p in paths}
    save(PREP / 'source-freeze.json', {'bindings': bindings, 'candidate_executed': False,
        'assembly_blocker_reproduced': False, 'missing_current_assembly_units': 0,
        'original_records': 60, 'distinct_mentions': 61, 'statutory_records_retained': 12})
    proposal = deepcopy(program)
    proposal['revision'] = 356
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=PLAN,
        reason='Derive source-only printed destinations and reconcile every discovered mention with the retained reviewed graph',
        reference_resolution={'review': rel(PREP), 'original_task_complete': False,
            'accounted_seconds_bound': SECONDS_BOUND, 'bytes_bound_with_4MiB_reserve': BYTES_BOUND})
    task['inputs'] = list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS] + list(bindings) + [rel(PREP / 'source-freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 95
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 356
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(task_sha256=old.authority_digest(task), dossier=PLAN,
                remaining='094 discovery recorded:60 original records/61 mentions. Source-only destinations, reviewed graph reconciliation, definitions and seven original gap classes remain.',
                next_action='Resolve supported printed addresses without reviewed targets; retain every graph/source relation, then continue original62 definitions/612 associations',
                stop_condition='95 cumulative admissions;300new command seconds/128MiB;27000accounted seconds/4096MiB including4MiB reserve;no unchanged retry')
    save(PREP / 'routes.json', routes)
    proposal['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    for name in TARGETS:
        proposal['continuation_review']['bindings'].pop(name, None)
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN),
        rel(PREP / 'routes.json'): sha(PREP / 'routes.json'), rel(PREP / 'source-freeze.json'): sha(PREP / 'source-freeze.json')})
    review = {'baseline': old.authority_digest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Reusable source-only resolution followed by explicit reviewed-graph reconciliation',
                    'Preserve current12 statutory records; reject unobserved assembly repair and avoid old missing-source labels'],
        'skeptical_audit': {'verdict': 'PASS', 'review': PLAN,
            'baseline': 'Exact original sources/paths; reviewed targets excluded from resolver request',
            'pre_mortem': 'Shared law qualifier, semantic subset, partial anchor and installed leakage controls'},
        'evidence_contract': {'primary': 'Original60 exact outcomes, graph/raw-target conservation and complete installed equality',
            'promotion_veto': ['Invented destination', 'Answer leakage', 'Raw forgery', 'Implicit guess', 'Wrong installed import'],
            'continuation_veto': ['Frozen corruption', 'Unreviewed drift', 'Cumulative exhaustion'],
            'explanatory_only': ['Counts', 'Runtime'], 'not_concluded': ['Legal truth', 'General recall', 'Build completion']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 94, 'new_maximum': 95,
            'retained_attempts': attempts, 'reason': 'Discovered mentions still lack reusable printed destination/graph reconciliation',
            'next_discriminating_check': 'All original addresses and graph relations under source-only and installed consumers',
            'stop_condition': '300new command seconds/128MiB;27000seconds/4096MiB cumulative;no unchanged retry',
            'same_scope_authorization': 'User directed refresh and continued internally supported general build'},
        'resource_accounting': {'retained_costs': prior, 'limits_extended': False,
            'additional_conservative_authoring_charge_seconds': 120, 'older_unmeasured_time': 'UNKNOWN'}}
    save(PREP / 'proposal.json', proposal)
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 356, 'original_records': 60, 'reviewed_edges': len(references),
            'printed_paragraphs': 99, 'candidate_executed': False}


if __name__ == '__main__':
    assert sys.argv[1:] == ['prepare']
    print(json.dumps(prepare()))
