"""Reconcile original definition uses with the current bounded discovery path."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import json
import signal
import sys
import time
from scripts import prospectus_definition_role_recovery as prior
from legalmath.prospectus.execution_authority import Authority, CODE, digest as adigest
from legalmath.prospectus.successor.contracts import digest

ROOT, AUTH, engine = prior.ROOT, prior.AUTH, prior.engine
PREP = AUTH / 'reviews/definition-use-audit-329'
HERE = AUTH / 'attempts/basf-references/attempt-068'
PLAN = 'docs/plans/prospectus-definition-scope-completion-2026-10-19.md'
METHOD = 'scripts/prospectus_definition_use_audit.py'
SOURCE = AUTH / 'attempts/basf-references/attempt-026'
STAGES = ('inventory', 'verify', 'seal')
read, save, sha, rel = prior.read, prior.save, prior.sha, prior.rel


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    measured = start['prior']['combined_measured_seconds'] + extra
    for folder in (PREP, HERE):
        for pattern in ('stages/*/result.json', 'stages/*/failure.json'):
            measured += sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    charged = start['prior']['conservative_extra_seconds']
    paths = {p for folder in (PREP, HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update((ROOT / PLAN, ROOT / METHOD, AUTH / 'revisions/0329.json'))
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = start['prior']['combined_bytes'] + sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    assert measured + charged < 16200 and size < 2428 * 1024**2, 'Cumulative definition-use audit bound'
    return {'combined_measured_seconds': measured, 'conservative_extra_seconds': charged,
        'combined_accounted_seconds': measured + charged, 'combined_bytes': size,
        'seconds_bound': 16200, 'bytes_bound_with_4MiB_reserve': 2432 * 1024**2,
        'prior_costs_reset': False, 'unmeasured_authoring_and_older_office_time': 'UNKNOWN; never treated as zero'}


def baseline():
    products, _ = prior.prior.baseline()
    answer = read(prior.HERE / 'ordinary-answer.json.gz')
    assert digest(answer) == '6ba48cc3d8c8ea91bde3e9a8edac5aea83f89a09bc5a6b1586f190f1114cad0e'
    text = products['P2']['payload']['assembly']['continuous_text']
    assert text == (SOURCE / 'selected-text.txt').read_text()
    return products, answer, text


def prepare():
    program = read(AUTH / 'program.json')
    assert program['revision'] == 328
    events = Authority(ROOT).events()
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 67 and any(e['kind'] == 'RECORD' and e.get('attempt') == rel(prior.HERE) for e in events)
    for folder in (prior.HERE, SOURCE):
        for name, checksum in read(folder / 'outputs.json').items():
            assert sha(folder / name) == checksum
    products, answer, text = baseline()
    dossier = read(SOURCE / 'definition-dossier.json')
    current = answer['definition_sources']
    assert [r['id'] for r in current['records']] == [r['id'] for r in dossier['records']]
    save(PREP / 'source-basis.json', {'selected_text_sha256': digest(text.encode()),
        'dossier_sha256': sha(SOURCE / 'definition-dossier.json'), 'answer_sha256': digest(answer),
        'products_sha256': digest(products), 'all_fifteen_sections_read': True,
        'review_scope': 'Complete selected German text; no new legal scope admission',
        'original_record_ids': [r['id'] for r in dossier['records']],
        'original_use_associations': sum(len(r['uses']) for r in dossier['records'])})
    bindings = {n: sha(ROOT / n) for n in (*CODE, PLAN, METHOD, prior.METHOD, prior.prior.METHOD,
                engine.METHOD, 'src/legalmath/prospectus/successor/definition_forms.py',
                'src/legalmath/prospectus/successor/definition_discovery.py')}
    bindings.update({rel(p): sha(p) for p in (ROOT / 'src/legalmath').rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'})
    for path in (SOURCE / 'outputs.json', SOURCE / 'definition-dossier.json', SOURCE / 'selected-text.txt',
                 SOURCE / 'sections.json', prior.HERE / 'ordinary-answer.json.gz', prior.HERE / 'outputs.json', prior.PRODUCTS):
        bindings[rel(path)] = sha(path)
    for row in read(prior.PRODUCTS)['products'].values():
        bindings[row['path']] = row['sha256']
    bindings.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file()})
    save(PREP / 'freeze.json', {'bindings': bindings})
    save(PREP / 'installation.json', [])
    proposal = deepcopy(program)
    proposal['revision'] = 329
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=rel(PREP / 'METHOD-REVIEW.md'),
        reason='Reconcile all original definition-use associations and bounded form discovery before substantive scope completion',
        definition_use_audit={'review': rel(PREP), 'no_production_change': True, 'original_task_complete': False,
                              'cumulative_accounted_seconds': 16200, 'cumulative_bytes': 2432 * 1024**2})
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [rel(PREP / 'freeze.json'), rel(PREP / 'installation.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 68
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 329
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                next_action='Compare every original term/use with current exact conditional treatment; repair concrete discovery/scope gaps then register original-task acceptance',
                stop_condition='68admissions;90s stages;existing16200accounted seconds/2432MiB with705seconds retained charges;no unchanged retry')
    save(PREP / 'routes.json', routes)
    proposal['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN),
        rel(PREP / 'routes.json'): sha(PREP / 'routes.json'), rel(PREP / 'freeze.json'): sha(PREP / 'freeze.json')})
    forecast = {'seconds': costs()['combined_accounted_seconds'] + 150,
                'bytes': costs()['combined_bytes'] + 40 * 1024**2, 'estimate_only': True}
    assert forecast['seconds'] < 16200 and forecast['bytes'] < 2428 * 1024**2
    review = {'baseline': adigest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Original62records/610uses reconciled with bounded supplied forms; exact rule uses separated from related report existence'],
        'skeptical_audit': {'verdict': 'PASS', 'review': rel(PREP / 'METHOD-REVIEW.md'), 'forecast': forecast},
        'evidence_contract': {'primary': 'Every original association retained with exact source and honest current evidence disposition',
            'promotion_veto': ['Omitted association', 'False scope', 'Overlap treated as meaning', 'Hidden new occurrence'],
            'continuation_veto': ['Source corruption', 'Frozen drift', 'Resource exhaustion'],
            'explanatory_only': ['Counts', 'Runtime'], 'not_concluded': ['Semantic completeness', 'Automatic recall', 'Whole-task acceptance']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 67, 'new_maximum': 68,
            'retained_attempts': attempts, 'reason': 'Current provenance corrected; original declaring-section hypotheses and current conditional reports require complete use reconciliation',
            'next_discriminating_check': 'Original exact uses compared with existing supplied-form parser and actual explicit application records',
            'stop_condition': '90s stages;150s/40MiB forecast in existing cumulative bounds;no unchanged retry',
            'same_scope_authorization': 'Continue general build and establish supported behavior internally'}}
    save(PREP / 'proposal.json', proposal)
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 329, 'forecast': forecast}


def inventory():
    from legalmath.prospectus.successor.definition_forms import discover_forms
    products, answer, text = baseline()
    dossier = read(SOURCE / 'definition-dossier.json')
    current = answer['definition_sources']
    rules = current['application_supplement']['applications']
    old_intervals = current['intervals']
    rows, generated = [], []
    for record, retained in zip(dossier['records'], current['records']):
        assert record['id'] == retained['id'] and record['forms'] == retained['forms']
        forms = list(dict.fromkeys(' '.join(f.split()) for f in record['forms']))
        request = {'text': text, 'text_sha256': digest(text.encode()),
            'forms': [{'id': str(i), 'text': f} for i, f in enumerate(forms)], 'regions': [[0, len(text)]]}
        discovered = discover_forms(request)
        assert discovered['scope_admitted'] is discovered['meaning_admitted'] is discovered['general_recall_established'] is False
        found = {(r['start'], r['end']): r for r in discovered['uses']}
        uses = []
        for use, original_use in zip(retained['uses'], record['uses']):
            interval = old_intervals[use['interval']]
            assert (interval['start'], interval['end'], interval['quote']) == (original_use['start'], original_use['end'], original_use['quote'])
            a, b = interval['start'], interval['end']
            assert text[a:b] == interval['quote']
            exact = [r for r in rules if (r['start'], r['end']) == (a, b)]
            uses.append({'interval': use['interval'], 'start': a, 'end': b, 'quote': text[a:b],
                'original_classification': use['classification'], 'original_use_sha256': digest(original_use),
                'source_piece_indices': interval['source_piece_indices'],
                'source_roles': sorted({u['role'] for i in interval['source_piece_indices']
                                        for u in current['source_pieces'][i]['assembly_uses']}),
                'supplied_form_found': (a, b) in found,
                'exact_five_rule_applications': [{'id': r['id'], 'role': r['role'], 'rule': r['rule'], 'remaining': r['remaining']} for r in exact],
                'governing_term_meaning_established_by_this_audit': False})
        original_set = {(u['start'], u['end']) for u in record['uses']}
        extra = [{'start': a, 'end': b, 'quote': text[a:b], 'context': text[max(0,a-90):min(len(text),b+90)],
                  'normalization_map': found[(a,b)]['normalization_map']}
                 for a, b in sorted(set(found) - original_set)]
        missing = [{'start': u['start'], 'end': u['end'], 'quote': u['quote'],
                    'classification': u['classification'], 'context': text[max(0,u['start']-90):min(len(text),u['end']+90)]}
                   for u in record['uses'] if (u['start'], u['end']) not in found]
        rows.append({'id': record['id'], 'forms': record['forms'], 'kind': record['kind'],
            'original_reading': record['reading'], 'original_scope_hypotheses': [r['scope'] for r in record['scope_alternatives']],
            'uses': uses, 'not_proposed_by_supplied_forms': missing, 'additional_proposals': extra,
            'all_term_uses_semantically_bound': False})
        generated.append({'record': record['id'], 'result': discovered})
    save(HERE / 'discovery.json.gz', generated)
    value = {'version': 'definition-use-coverage.v1', 'basis': read(PREP / 'source-basis.json'),
        'records': rows, 'five_rule_report_sha256': digest(current['application_supplement']),
        'related_conditional_reports': {k: digest(answer[k]) for k in ('payment_category_review', 'causal_rating_review',
            'control_votes_review', 'concert_necessary_review', 'affiliate_substitution_review', 'publication_routes_review')},
        'related_report_existence_is_not_term_scope': True, 'whole_task_complete': False,
        'original_use_associations': sum(len(r['uses']) for r in rows),
        'not_proposed_associations': sum(len(r['not_proposed_by_supplied_forms']) for r in rows),
        'additional_associations': sum(len(r['additional_proposals']) for r in rows)}
    save(HERE / 'coverage.json', value)
    return {'status': 'PASS', 'records': len(rows), **{k: value[k] for k in
            ('original_use_associations', 'not_proposed_associations', 'additional_associations')}}


def validate(coverage):
    dossier = read(SOURCE / 'definition-dossier.json')
    text = (SOURCE / 'selected-text.txt').read_text()
    answer = read(prior.HERE / 'ordinary-answer.json.gz')
    apps = answer['definition_sources']['application_supplement']['applications']
    discovery = read(HERE / 'discovery.json.gz')
    assert coverage['whole_task_complete'] is False and coverage['related_report_existence_is_not_term_scope'] is True
    assert [r['id'] for r in coverage['records']] == [r['id'] for r in dossier['records']]
    assert [r['record'] for r in discovery] == [r['id'] for r in dossier['records']]
    for row, original, lexical in zip(coverage['records'], dossier['records'], discovery):
        assert (row['forms'], row['kind'], row['original_reading']) == (original['forms'], original['kind'], original['reading'])
        assert row['all_term_uses_semantically_bound'] is False
        assert [(u['start'], u['end'], u['quote'], u['original_use_sha256']) for u in row['uses']] == [
            (u['start'], u['end'], u['quote'], digest(u)) for u in original['uses']]
        observed = set()
        for use in lexical['result']['uses']:
            a, b = use['start'], use['end']
            assert text[a:b] == use['raw']
            spans = use['normalization_map']
            assert spans[0][0] == a and spans[-1][1] == b and all(x[1] == y[0] for x,y in zip(spans,spans[1:]))
            assert len(spans) == len(use['normalized_form'])
            for char, (x,y) in zip(use['normalized_form'], spans):
                assert text[x:y].isspace() if char == ' ' else text[x:y] == char
            observed.add((a,b))
        original_set = {(u['start'],u['end']) for u in original['uses']}
        assert {(u['start'],u['end']) for u in row['additional_proposals']} == observed - original_set
        assert {(u['start'],u['end']) for u in row['not_proposed_by_supplied_forms']} == original_set - observed
        for use in row['uses']:
            assert use['supplied_form_found'] is ((use['start'],use['end']) in observed)
            expected = [{'id': a['id'], 'role': a['role'], 'rule': a['rule'], 'remaining': a['remaining']}
                        for a in apps if (a['start'],a['end']) == (use['start'],use['end'])]
            assert use['exact_five_rule_applications'] == expected
            assert use['governing_term_meaning_established_by_this_audit'] is False
    for key, nested in (('original_use_associations','uses'),('not_proposed_associations','not_proposed_by_supplied_forms'),
                        ('additional_associations','additional_proposals')):
        assert coverage[key] == sum(len(r[nested]) for r in coverage['records'])
    return {'status': 'PASS', 'original_identity_and_discovery_partition_checked': True}


def verify():
    coverage = read(HERE / 'coverage.json')
    result = validate(coverage)
    refused = []
    for kind in ('omitted-record', 'omitted-use', 'altered-quote', 'lost-additional', 'invented-scope', 'false-completion'):
        bad = deepcopy(coverage)
        if kind == 'omitted-record': bad['records'].pop()
        elif kind == 'omitted-use': bad['records'][0]['uses'].pop()
        elif kind == 'altered-quote': bad['records'][0]['uses'][0]['quote'] += 'x'
        elif kind == 'lost-additional':
            row = next((r for r in bad['records'] if r['additional_proposals']), None)
            assert row is not None, 'Use a distinct reviewed control if there are no additional proposals'
            row['additional_proposals'].pop()
        elif kind == 'invented-scope': bad['records'][0]['uses'][0]['governing_term_meaning_established_by_this_audit'] = True
        else: bad['whole_task_complete'] = True
        try:
            validate(bad)
        except AssertionError:
            refused.append(kind)
        else:
            raise AssertionError('Accepted mutation: ' + kind)
    result['refused'] = refused
    save(HERE / 'verification.json', result)
    return result


def seal():
    coverage = read(HERE / 'coverage.json')
    result = {'status': 'PASS', 'task': 'basf-references', 'original_task_complete': False,
        'result_kind': 'ORIGINAL_DEFINITION_USE_COVERAGE',
        'resources': costs(), 'remaining': 'Review every missing/additional form occurrence and source-reasoned governing use',
        'next_action': 'Use concrete discovery and semantic-coverage differences to choose repair; do not replace the original acceptance denominator'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(HERE / 'stages' / s / 'started.json')['command'] for s in STAGES],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU; no GPU use',
        'seeds': 'N/A deterministic', 'data_version': sha(SOURCE / 'definition-dossier.json'),
        'wall_time': costs(), 'plan': PLAN, 'result': rel(HERE / 'result.json')})
    (HERE / 'RESULT.md').write_text('''# Original definition-use coverage

Every original62definition record and610use association is retained with its
source interval, current source roles, supplied-form discovery disposition and
exact matching entries in the five-rule application supplement. Additional
proposals and omissions are explicit. Other conditional reports are listed as
related evidence only; their existence does not establish governing term scope.

|Decision|Primary criterion|Veto status|Main uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain complete original-use reconciliation|Original identities, exact source intervals and full discovery partition|Omission/quotation/scope/completion mutations refused|Which additional or withheld matches are substantive and which governing uses are supported|Inspect every difference and specify missing mechanism|Semantic completeness, automatic recall or whole task|

The original dossier's lexical denominator itself may omit typography variants
or include compound components. Neither a parser match nor a discrepancy alone
proves a legal interpretation. The next source review distinguishes those
alternatives before implementation. All original uncertainty remains visible.
''')
    return result


def main():
    stage = sys.argv[1]
    assert stage == 'prepare' or stage in STAGES
    folder = (PREP if stage == 'prepare' else HERE) / 'stages' / stage
    assert not (folder / 'started.json').exists(), 'Unchanged retry refused'
    if stage == 'prepare':
        save(PREP / 'accounting-start.json', {'prior': prior.costs(),
            'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
            'program_bytes': (AUTH / 'program.json').stat().st_size})
    else:
        for before in STAGES[:STAGES.index(stage)]:
            assert read(HERE / 'stages' / before / 'result.json')['status'] == 'PASS'
        engine.PREP, engine.HERE, engine.PLAN = PREP, HERE, PLAN
        engine.METHOD, engine.TARGETS = METHOD, ()
        engine.frozen()
    save(folder / 'started.json', {'command': ['.venv/bin/python', '-m', 'scripts.prospectus_definition_use_audit', stage],
        'started_at': datetime.now(timezone.utc).isoformat(), 'seconds_bound': 90})
    start = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Definition-use audit bound')))
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
