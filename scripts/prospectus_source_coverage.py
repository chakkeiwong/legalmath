"""Audit every retained BASF reference/definition against the current answer."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import json
import signal
import sys
import time
from scripts import prospectus_reference_roles as prior
from legalmath.prospectus.execution_authority import Authority, CODE, digest as adigest
from legalmath.prospectus.successor.contracts import digest

ROOT, AUTH, engine = prior.ROOT, prior.AUTH, prior.engine
PREP = AUTH / 'reviews/source-coverage-326'
HERE = AUTH / 'attempts/basf-references/attempt-065'
PLAN = 'docs/plans/prospectus-source-coverage-audit-2026-10-19.md'
METHOD = 'scripts/prospectus_source_coverage.py'
LEDGER = AUTH / 'reviews/internal-closure-279/reconciliation-proposed.json.gz'
DOSSIER = AUTH / 'attempts/basf-references/attempt-026/definition-dossier.json'
STAGES = ('inventory', 'verify', 'seal')
STATUTES = {'H16', 'H28', 'H35', 'H38', 'H39', 'H40', 'A2', 'A3', 'A7', 'A8', 'A11', 'A12'}
REPORTS = ('relative_call_notices', 'payment_method_references', 'original_reference_review',
           'governance_references', 'default_references', 'substitution_references',
           'financial_references', 'internal_references')
read, save, sha, rel = prior.read, prior.save, prior.sha, prior.rel


def baseline():
    products, old = prior.baseline()
    answer = read(prior.HERE / 'ordinary-answer.json.gz')
    assert digest(answer) == '41c95fe520c483626ac5ac54732855f3b4d20a079e56f2376c7488f50d033731'
    assert {k: v for k, v in answer.items() if k not in ('reference_role_review', 'report_sha256')} == {
        k: v for k, v in old.items() if k != 'report_sha256'}
    return products, answer


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    seconds = start['prior']['combined_measured_seconds'] + extra
    for folder in (PREP, HERE):
        for pattern in ('stages/*/result.json', 'stages/*/failure.json'):
            seconds += sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths = {p for folder in (PREP, HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update((ROOT / PLAN, ROOT / METHOD, AUTH / 'revisions/0326.json'))
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = start['prior']['combined_bytes'] + sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    assert seconds < 16200 and size < 2428 * 1024**2, 'Cumulative source-audit resource bound'
    return {'combined_measured_seconds': seconds, 'combined_bytes': size, 'prior_costs_reset': False,
            'seconds_bound': 16200, 'bytes_bound_with_4MiB_reserve': 2432 * 1024**2,
            'unmeasured_authoring_and_older_office_time': 'UNKNOWN; never treated as zero'}


def prepare():
    program = read(AUTH / 'program.json')
    assert program['revision'] == 325
    events = Authority(ROOT).events()
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 64 and any(e['kind'] == 'RECORD' and e.get('attempt') == rel(prior.HERE) for e in events)
    for name, checksum in read(prior.HERE / 'outputs.json').items():
        assert sha(prior.HERE / name) == checksum, name
    products, answer = baseline()
    assert len(read(LEDGER)['records']) == 60
    save(PREP / 'baseline.json', {'products_sha256': digest(products), 'answer_sha256': digest(answer),
         'original_ledger_sha256': sha(LEDGER), 'definition_dossier_sha256': sha(DOSSIER),
         'source_graph_sha256': digest(products['P1']['payload']['graph']),
         'selected_text_sha256': digest(products['P2']['payload']['assembly']['continuous_text'].encode()),
         'meaning_proved': False, 'task_accepted': False})
    bindings = {name: sha(ROOT / name) for name in (*CODE, PLAN, METHOD, prior.METHOD,
                  rel(LEDGER), rel(DOSSIER), rel(prior.PRODUCTS), rel(prior.HERE / 'ordinary-answer.json.gz'),
                  rel(prior.HERE / 'outputs.json'), rel(PREP / 'METHOD-REVIEW.md'))}
    bindings.update({rel(p): sha(p) for p in (ROOT / 'src/legalmath').rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'})
    for row in read(prior.PRODUCTS)['products'].values():
        bindings[row['path']] = row['sha256']
    bindings.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    save(PREP / 'freeze.json', {'bindings': bindings})
    save(PREP / 'installation.json', [])
    proposal = deepcopy(program)
    proposal['revision'] = 326
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=rel(PREP / 'METHOD-REVIEW.md'),
        reason='Reconcile every original reference and definition against actual current source-to-answer evidence before choosing the next substantive closure repair',
        source_coverage_audit={'review': rel(PREP), 'original_task_complete': False,
                               'combined_seconds': 16200, 'combined_bytes': 2432 * 1024**2})
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [rel(PREP / 'freeze.json'), rel(PREP / 'installation.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 65
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 326
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                next_action='Audit all original reference/definition occurrences and current answers, then execute the resulting substantive repair',
                stop_condition='65admissions;90s stages;existing16200s/2432MiB;no new requests, production mutation or unchanged retry')
    save(PREP / 'routes.json', routes)
    proposal['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN),
        rel(PREP / 'routes.json'): sha(PREP / 'routes.json'), rel(PREP / 'freeze.json'): sha(PREP / 'freeze.json')})
    forecast = {'seconds': costs()['combined_measured_seconds'] + 300,
                'bytes': costs()['combined_bytes'] + 64 * 1024**2, 'estimate_only': True}
    assert forecast['seconds'] < 16200 and forecast['bytes'] < 2428 * 1024**2
    review = {'baseline': adigest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Complete retained source coverage audit; no source, meaning or production claim promoted'],
        'skeptical_audit': {'verdict': 'PASS', 'review': rel(PREP / 'METHOD-REVIEW.md'), 'forecast': forecast},
        'evidence_contract': {'primary': 'Every original identity and exact source interval reconciled with current complete answer',
            'promotion_veto': ['Omitted original', 'Fabricated quote', 'False completion', 'Stale status treated as current'],
            'continuation_veto': ['Corrupt baseline', 'Frozen drift', 'Resource exhaustion'],
            'explanatory_only': ['Counts', 'Runtime'], 'not_concluded': ['Full linguistic recall', 'Legal truth', 'Task acceptance']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 64, 'new_maximum': 65,
            'retained_attempts': attempts, 'reason': 'The remaining original coverage ledger predates several source and consumer repairs',
            'next_discriminating_check': 'Exact60reference and62definition identities with610use associations and current source/answer dispositions',
            'stop_condition': '90s stages;300s/64MiB forecast within existing16200s/2432MiB;no unchanged retry',
            'same_scope_authorization': 'User-directed refreshed master and continued internal general build'}}
    save(PREP / 'proposal.json', proposal)
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 326, 'forecast': forecast}


def source_check(source, raw):
    unit = raw[source['unit']]
    assert (unit['document'], unit['source_sha256']) == (source['document'], source['source_sha256'])
    assert type(source['start']) is int and type(source['end']) is int
    assert 0 <= source['start'] < source['end'] <= len(unit['raw'])
    assert unit['raw'][source['start']:source['end']] == source['quote']


def inventory():
    products, answer = baseline()
    ledger = read(LEDGER)
    raw = {r['id']: r for r in products['P1']['payload']['graph']['units']}
    assembly = products['P2']['payload']['assembly']
    selected = {r['unit']: r for r in assembly['units']}
    packet = products['P3']['payload']['interpretation_input']['reference_admission']
    references = {r['id']: r for r in packet['references']}
    reports = {}
    for report in REPORTS:
        assert not answer[report]['missing']
        for row in answer[report]['references']:
            assert {k: v for k, v in references[row['id']].items() if k != 'reason'} == {k: v for k, v in row.items() if k != 'reason'}
            reports.setdefault(row['id'], []).append(report)
    statutory = {r['id']: r for r in answer['statutory_references']['records']}
    assert set(statutory) == STATUTES
    rows = []
    for old in ledger['records']:
        identity = ('H' if old['family'] == 'historical_candidate_lines' else 'A') + str(old['index'])
        retained = old.get('current_reference')
        current = None if retained is None else references.get(retained['id'])
        differences = []
        if current is not None:
            differences = [k for k in set(retained) | set(current) if retained.get(k) != current.get(k)]
            source_check(current['source'], raw)
            source_check(current['authority'], raw)
            for target in current['targets']:
                source_check(target['source'], raw)
                assert target['use'] in selected
            assert current['id'] in reports
        for piece in old['source_pieces']:
            if piece.get('kind') == 'RAW_ANCHOR':
                source_check(piece['original'], raw)
        law = statutory.get(identity)
        has_publication = identity == 'H43'
        if has_publication:
            assert answer['publication_routes_review']['context']['current_source_available'] is True
        rows.append({'id': identity, 'family': old['family'], 'index': old['index'],
            'original_record_sha256': digest(old['original']), 'historical_status': old['current_status'],
            'current_reference': None if current is None else current['id'],
            'current_reference_sha256': None if current is None else digest(current),
            'current_reference_changes': sorted(differences), 'consumer_paths': [] if current is None else reports[current['id']],
            'source_target_binding': 'EXACT_CURRENT_SOURCE_AND_TARGET' if current is not None else 'EXTERNAL_LEGAL_READING',
            'statutory': None if law is None else {'id': law['id'], 'availability': law['availability'],
                'application': law['application'], 'uncertainties': law['uncertainties']},
            'publication_profile': has_publication,
            'full_legal_interpretation_established': False})
    definition = answer['definition_sources']
    text = assembly['continuous_text']
    pieces = definition['source_pieces']
    offset = 0
    counts = Counter()
    role_differences = []
    for number, piece in enumerate(pieces):
        assert piece['start'] == offset and piece['end'] > offset
        assert text[piece['start']:piece['end']] == piece['text']
        offset = piece['end']
        counts[piece['kind']] += len(piece['text'])
        if piece['kind'] == 'EXACT_SOURCE_COPY':
            source_check(piece['raw_binding'], raw)
            assert piece['raw_binding']['quote'] == piece['text']
        else:
            assert piece['raw_binding'] is None
        for use in piece['assembly_uses']:
            current = selected.get(use['unit'])
            assert current is not None
            if use['role'] != current['role']:
                role_differences.append({'piece': number, 'unit': use['unit'],
                                        'retained_role': use['role'], 'current_role': current['role']})
    assert offset == len(text)
    intervals = definition['intervals']
    for span in intervals:
        assert 0 <= span['start'] < span['end'] <= len(text)
        assert text[span['start']:span['end']] == span['quote']
        touching = [i for i, p in enumerate(pieces) if p['start'] < span['end'] and span['start'] < p['end']]
        assert span['source_piece_indices'] == touching
    definitions = []
    applications = definition['application_supplement']['applications']
    for record in definition['records']:
        uses = []
        for use in record['uses']:
            span = intervals[use['interval']]
            matched = [a for a in applications if (a['start'], a['end']) == (span['start'], span['end'])]
            uses.append({'interval': use['interval'], 'span_sha256': digest(span), 'classification': use['classification'],
                'scope_candidate_indices': use['interval_candidates'],
                'supplemental_applications': [{'id': a['id'], 'role': a['role'], 'rule': a['rule'], 'remaining': a['remaining']} for a in matched]})
        definitions.append({'id': record['id'], 'kind': record['kind'], 'forms': record['forms'],
            'record_sha256': digest(record), 'declarations': record['declarations'],
            'status': record['status'], 'uses': uses, 'reading': record['reading'],
            'governing_scope_admitted': record['scope_admitted'], 'meaning_admitted': record['meaning_admitted']})
    report = {'version': 'prospectus-source-coverage.v1', 'baseline': read(PREP / 'baseline.json'),
        'references': rows, 'definitions': definitions,
        'source_accounting': {'selected_characters': len(text), 'characters_by_kind': dict(counts),
                              'retained_vs_current_roles': role_differences},
        'question_statuses': {q: row['status'] for q, row in answer['questions'].items()},
        'cycles': deepcopy(answer['reference_role_review']['questions']['Q1']['dependency_cycles']),
        'original_inventory_exhaustive': False, 'whole_task_complete': False,
        'next_question': 'Which source-supported governing extents and uses remain conditional, and which current role metadata must be reconciled?'}
    save(HERE / 'coverage.json', report)
    return {'status': 'PASS', 'references': len(rows), 'definitions': len(definitions),
            'use_associations': sum(len(r['uses']) for r in definitions),
            'retained_role_differences': len(role_differences)}


def validate(report):
    """A second pass checks retained identities directly, not report counts."""
    products, answer = baseline()
    original = read(LEDGER)['records']
    wanted = [(r['family'], r['index'], digest(r['original'])) for r in original]
    actual = [(r['family'], r['index'], r['original_record_sha256']) for r in report['references']]
    assert actual == wanted
    reference_ids = {r['id']: r for r in products['P3']['payload']['interpretation_input']['reference_admission']['references']}
    for row, old in zip(report['references'], original):
        link = old.get('current_reference')
        assert row['current_reference'] == (None if link is None else link['id'])
        if link is not None:
            assert row['current_reference_sha256'] == digest(reference_ids[link['id']])
        assert row['full_legal_interpretation_established'] is False
    original_definitions = answer['definition_sources']['records']
    dossier = read(DOSSIER)['records']
    assert [r['id'] for r in original_definitions] == [r['id'] for r in dossier]
    for current, original_record in zip(original_definitions, dossier):
        assert (current['kind'], current['forms'], current['reading']) == (
            original_record['kind'], original_record['forms'], original_record['reading'])
        actual_uses = [(answer['definition_sources']['intervals'][u['interval']]['start'],
                       answer['definition_sources']['intervals'][u['interval']]['end'],
                       answer['definition_sources']['intervals'][u['interval']]['quote']) for u in current['uses']]
        assert actual_uses == [(u['start'], u['end'], u['quote']) for u in original_record['uses']]
    assert [r['id'] for r in report['definitions']] == [r['id'] for r in original_definitions]
    for row, old in zip(report['definitions'], original_definitions):
        assert row['record_sha256'] == digest(old)
        assert row['declarations'] == old['declarations']
        assert [u['interval'] for u in row['uses']] == [u['interval'] for u in old['uses']]
        for use in row['uses']:
            assert use['span_sha256'] == digest(answer['definition_sources']['intervals'][use['interval']])
        assert row['governing_scope_admitted'] is False and row['meaning_admitted'] is False
    assert report['baseline'] == read(PREP / 'baseline.json')
    assert report['whole_task_complete'] is False and report['original_inventory_exhaustive'] is False
    assert sum(report['source_accounting']['characters_by_kind'].values()) == len(products['P2']['payload']['assembly']['continuous_text'])
    return True


def verify():
    report = read(HERE / 'coverage.json')
    assert validate(report)
    refused = []
    for kind in ('omitted-reference', 'duplicate-reference', 'definition-omission', 'altered-interval', 'false-completion'):
        bad = deepcopy(report)
        if kind == 'omitted-reference': bad['references'].pop()
        elif kind == 'duplicate-reference': bad['references'][1] = deepcopy(bad['references'][0])
        elif kind == 'definition-omission': bad['definitions'].pop()
        elif kind == 'altered-interval': bad['definitions'][0]['uses'][0]['span_sha256'] = '0' * 64
        else: bad['whole_task_complete'] = True
        try:
            validate(bad)
        except AssertionError:
            refused.append(kind)
        else:
            raise AssertionError('Invalid coverage accepted: ' + kind)
    result = {'status': 'PASS', 'complete_identity_comparison': True, 'misuse_refusals': refused,
              'coverage_sha256': sha(HERE / 'coverage.json'), 'legal_truth_proved': False}
    save(HERE / 'verification.json', result)
    return result


def seal():
    report = read(HERE / 'coverage.json')
    source_kinds = report['source_accounting']['characters_by_kind']
    pending = Counter(u['classification'] for r in report['definitions'] for u in r['uses'])
    result = {'status': 'PASS', 'task': 'basf-references', 'original_task_complete': False,
        'result_kind': 'COMPLETE_ORIGINAL_COVERAGE_AUDIT', 'resources': costs(),
        'definition_use_classifications': dict(pending), 'source_characters': source_kinds,
        'next_action': 'Review retained/current source-role differences and complete source-supported definition extent/use interpretation'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(HERE / 'stages' / s / 'started.json')['command'] for s in STAGES],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU;GPU intentionally hidden',
        'seeds': 'N/A deterministic', 'data_version': sha(LEDGER), 'wall_time': costs(), 'plan': PLAN,
        'result': rel(HERE / 'result.json')})
    (HERE / 'RESULT.md').write_text('''# Complete retained source inventory reconciled

The audit preserves all60 original reference records and all62 definition
records with610 use associations. Current source spans and actual answer paths
are checked; historical ledger descriptions remain as historical evidence.
Twelve retained statutory readings and the H43 publication supplement are
distinguished from their unresolved historical applicability. Supplied text and
generated separators are never presented as exact raw PDF quotations.

|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain current coverage report|Exact original identities, source intervals and actual answer mappings|Omitted, duplicated, altered and self-completed reports refused|Governing scope, unmodeled meanings and discovery recall|Review role differences and remaining definition applications|Whole source-task acceptance or legal truth|

The audit validates coverage of the retained findings. It cannot show that the
original source reading found every implicit reference, or that all supplied
meanings are correct. Its strongest alternative explanation is an incomplete
original inventory; further source and supported-domain work remains necessary.
''')
    return result


def main():
    stage = sys.argv[1]
    assert stage == 'prepare' or stage in STAGES
    folder = (PREP if stage == 'prepare' else HERE) / 'stages' / stage
    assert not (folder / 'started.json').exists(), 'Unchanged audit retry refused'
    if stage == 'prepare':
        save(PREP / 'accounting-start.json', {'prior': prior.costs(),
             'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
             'program_bytes': (AUTH / 'program.json').stat().st_size})
    else:
        for previous in STAGES[:STAGES.index(stage)]:
            assert read(HERE / 'stages' / previous / 'result.json')['status'] == 'PASS'
        engine.PREP, engine.HERE = PREP, HERE
        engine.frozen()
    save(folder / 'started.json', {'command': ['.venv/bin/python', '-m', 'scripts.prospectus_source_coverage', stage],
        'started_at': datetime.now(timezone.utc).isoformat(), 'seconds_bound': 90})
    start = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Source coverage stage bound')))
    signal.alarm(90)
    try:
        result = globals()[stage]()
        if stage != 'prepare':
            engine.frozen()
        costs(time.monotonic() - start)
        result['wall_seconds'] = time.monotonic() - start
        save(folder / 'result.json', result)
        if stage == 'seal':
            save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as error:
        save(folder / 'failure.json', {'type': type(error).__name__, 'message': str(error), 'wall_seconds': time.monotonic() - start})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
