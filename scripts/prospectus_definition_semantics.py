"""Complete original-record semantic reconciliation under prospectus authority."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import json
import signal
import sys
import time

from scripts import prospectus_definition_use_audit as prior
from scripts import prospectus_definition_semantic_links as links
from legalmath.prospectus.execution_authority import Authority, CODE, digest as adigest
from legalmath.prospectus.successor.contracts import digest

ROOT, AUTH, engine = prior.ROOT, prior.AUTH, prior.engine
PREP = AUTH / 'reviews/definition-semantics-330'
HERE = AUTH / 'attempts/basf-references/attempt-069'
PLAN = 'docs/plans/prospectus-definition-semantic-reconciliation-2026-10-19.md'
METHOD = 'scripts/prospectus_definition_semantics.py'
LINKS = 'scripts/prospectus_definition_semantic_links.py'
SOURCE, PRODUCTS = prior.SOURCE, prior.prior.PRODUCTS
STAGES = ('inventory', 'verify', 'seal')
read, save, sha, rel = prior.read, prior.save, prior.sha, prior.rel


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    measured = start['prior']['combined_measured_seconds'] + extra
    for folder in (PREP, HERE):
        for pattern in ('stages/*/result.json', 'stages/*/failure.json'):
            measured += sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    charged = start['prior']['conservative_extra_seconds']
    paths = {p for folder in (PREP, HERE) for p in folder.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update((ROOT / PLAN, ROOT / METHOD, ROOT / LINKS, AUTH / 'revisions/0330.json'))
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = start['prior']['combined_bytes'] + sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    assert measured + charged < 16200 and size < 2428 * 1024**2, 'Cumulative semantic reconciliation bound'
    return {'combined_measured_seconds': measured, 'conservative_extra_seconds': charged,
            'combined_accounted_seconds': measured + charged, 'combined_bytes': size,
            'seconds_bound': 16200, 'bytes_bound_with_4MiB_reserve': 2432 * 1024**2,
            'prior_costs_reset': False, 'unmeasured_authoring_and_older_office_time': 'UNKNOWN; never treated as zero'}


def baseline():
    products, answer, text = prior.baseline()
    coverage = read(prior.HERE / 'coverage.json')
    nodes = {n['id']: n for n in products['P3']['payload']['clauses']['nodes']}
    assert len(nodes) == len(products['P3']['payload']['clauses']['nodes']), 'Duplicate clause identity'
    assert set(links.LINKS) == {r['id'].split('-')[0] for r in coverage['records']}
    for record in coverage['records']:
        node_id, path, _, _ = links.LINKS[record['id'].split('-')[0]]
        node = nodes[node_id]
        assert node['role'] == 'OPERATIVE' and node['quote'] and node['spans']
        assert links.field(node, path) is not None
    return products, answer, text, coverage, nodes


def prepare():
    program = read(AUTH / 'program.json')
    assert program['revision'] == 329
    events = Authority(ROOT).events()
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 68 and any(e['kind'] == 'RECORD' and e.get('attempt') == rel(prior.HERE) for e in events)
    for folder in (prior.HERE, SOURCE):
        for name, checksum in read(folder / 'outputs.json').items():
            assert sha(folder / name) == checksum
    products, answer, text, coverage, _ = baseline()
    save(PREP / 'source-basis.json', {'products_sha256': digest(products), 'answer_sha256': digest(answer),
        'coverage_sha256': sha(prior.HERE / 'coverage.json'), 'source_text_sha256': digest(text.encode()),
        'record_ids': [r['id'] for r in coverage['records']], 'use_associations': 610,
        'manual_links_sha256': sha(ROOT / LINKS), 'whole_task_complete': False})
    bindings = {n: sha(ROOT / n) for n in (*CODE, PLAN, METHOD, LINKS, prior.METHOD, engine.METHOD)}
    bindings.update({rel(p): sha(p) for p in (ROOT / 'src/legalmath').rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'})
    for path in (prior.HERE / 'coverage.json', prior.HERE / 'outputs.json',
                 prior.prior.HERE / 'ordinary-answer.json.gz', prior.prior.HERE / 'outputs.json',
                 SOURCE / 'definition-dossier.json', SOURCE / 'selected-text.txt', PRODUCTS):
        bindings[rel(path)] = sha(path)
    for row in read(PRODUCTS)['products'].values():
        bindings[row['path']] = row['sha256']
    bindings.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file()})
    save(PREP / 'freeze.json', {'bindings': bindings})
    save(PREP / 'installation.json', [])
    proposal = deepcopy(program)
    proposal['revision'] = 330
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=rel(PREP / 'METHOD-REVIEW.md'),
        reason='Connect every original definition to inspected current meaning and distinguish actual use bindings from same-spelling other-purpose applications',
        definition_semantic_reconciliation={'review': rel(PREP), 'original_task_complete': False,
            'cumulative_accounted_seconds': 16200, 'cumulative_bytes': 2432 * 1024**2})
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [rel(PREP / 'freeze.json'), rel(PREP / 'installation.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 69
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 330
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                next_action='Verify complete existing meaning links; bind actual definition applications by record, occurrence and purpose before original-task acceptance',
                stop_condition='69admissions;90s stages;existing16200accounted seconds/2432MiB including705seconds;no unchanged retry')
    save(PREP / 'routes.json', routes)
    proposal['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN),
        rel(PREP / 'routes.json'): sha(PREP / 'routes.json'), rel(PREP / 'freeze.json'): sha(PREP / 'freeze.json')})
    snapshot = costs()
    forecast = {'seconds': snapshot['combined_accounted_seconds'] + 150,
                'bytes': snapshot['combined_bytes'] + 28 * 1024**2, 'estimate_only': True}
    assert forecast['seconds'] < 16200 and forecast['bytes'] < 2428 * 1024**2
    review = {'baseline': adigest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['All62current declaration links reconciled;610original uses and15discovery differences retained; purpose-specific binding gap reproduced'],
        'skeptical_audit': {'verdict': 'PASS', 'review': rel(PREP / 'METHOD-REVIEW.md'), 'forecast': forecast},
        'evidence_contract': {'primary': 'Exact complete record/use matrix against manually reviewed field links and independently enumerated purpose cases',
            'promotion_veto': ['Omission', 'False field link', 'Same-span other-purpose meaning', 'False completion'],
            'continuation_veto': ['Corruption', 'Frozen drift', 'Cumulative bound'],
            'explanatory_only': ['Counts', 'Runtime'], 'not_concluded': ['Governing scope for all uses', 'General grammar', 'Actual facts', 'Task completion']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 68, 'new_maximum': 69,
            'retained_attempts': attempts, 'reason': '068retains lexical differences; current clause-field meaning and purpose-specific record binding must be reconciled before repair',
            'next_discriminating_check': 'Complete62record matrix and explicit U06/U07same-span counterexample',
            'stop_condition': '90s stages;150s/28MiB forecast in unchanged cumulative bounds;no unchanged retry',
            'same_scope_authorization': 'Continue general build with internally established supported behavior'}}
    save(PREP / 'proposal.json', proposal)
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 330, 'forecast': forecast}


def inventory():
    products, answer, text, coverage, nodes = baseline()
    applications = {(a['start'], a['end']): a for a in answer['definition_sources']['application_supplement']['applications']}
    rows, differences = [], []
    for record in coverage['records']:
        short = record['id'].split('-')[0]
        node_id, path, relationship, reason = links.LINKS[short]
        node = nodes[node_id]
        uses = []
        for use in record['uses']:
            app = applications.get((use['start'], use['end']))
            uses.append({'interval': use['interval'], 'start': use['start'], 'end': use['end'], 'quote': use['quote'],
                'original_use_sha256': use['original_use_sha256'], 'disposition': links.use_disposition(record['id'], app),
                'application_id': app['id'] if app else None, 'application_rule': app['rule'] if app else None,
                'application_sha256': digest(app) if app else None})
        rows.append({'id': record['id'], 'original_reading': record['original_reading'],
            'evidence': {'product': 'P3', 'node': node_id, 'field': path, 'node_sha256': digest(node),
                'value': deepcopy(links.field(node, path)), 'relationship': relationship, 'review_reason': reason},
            'uses': uses, 'all_uses_governed': False})
        for item in record['not_proposed_by_supplied_forms']:
            category = 'REVIEWED_AGENCY_SLASH_BOUNDARY' if short == 'D26' else 'COMPOUND_COMPONENT_WITHHELD'
            assert short in {'D21', 'D26', 'D31'}
            differences.append({'record': record['id'], 'kind': 'WITHHELD', 'start': item['start'], 'end': item['end'],
                'quote': item['quote'], 'context': item['context'], 'disposition': category,
                'automatic_scope_established': False})
        for item in record['additional_proposals']:
            assert short in {'U06', 'U07'} and (item['start'], item['end']) == (21547, 21576)
            app = applications[(item['start'], item['end'])]
            assert app['rule'] == 'makewhole'
            differences.append({'record': record['id'], 'kind': 'ADDITIONAL', 'start': item['start'], 'end': item['end'],
                'quote': item['quote'], 'context': item['context'], 'disposition': 'ALREADY_IN_289_APPLICATION_SUPPLEMENT',
                'application_id': app['id'], 'record_use_disposition': links.use_disposition(record['id'], app),
                'automatic_scope_established': False})
    value = {'version': 'definition-semantic-reconciliation.v1', 'basis': read(PREP / 'source-basis.json'),
        'records': rows, 'discovery_differences': differences, 'whole_task_complete': False,
        'conditional_source_review': True, 'governing_uses_not_inferred_from_overlap': True,
        'original_use_associations': sum(len(r['uses']) for r in rows)}
    save(HERE / 'coverage.json', value)
    return {'status': 'PASS', 'records': len(rows), 'original_uses': value['original_use_associations'],
        'use_dispositions': dict(Counter(u['disposition'] for r in rows for u in r['uses'])),
        'differences': dict(Counter(r['disposition'] for r in differences))}


def validate(value):
    products = {k: read(ROOT / r['path']) for k, r in read(PRODUCTS)['products'].items()}
    nodes = {n['id']: n for n in products['P3']['payload']['clauses']['nodes']}
    original = read(SOURCE / 'definition-dossier.json')
    coverage = read(prior.HERE / 'coverage.json')
    text = (SOURCE / 'selected-text.txt').read_text()
    answer = read(prior.prior.HERE / 'ordinary-answer.json.gz')
    apps = {(a['start'], a['end']): a for a in answer['definition_sources']['application_supplement']['applications']}
    assert value['whole_task_complete'] is False and value['governing_uses_not_inferred_from_overlap'] is True
    assert value['basis'] == read(PREP / 'source-basis.json')
    assert [r['id'] for r in value['records']] == [r['id'] for r in original['records']]
    for row, source in zip(value['records'], original['records']):
        short = row['id'].split('-')[0]
        node_id, path, relationship, reason = links.LINKS[short]
        node = nodes[node_id]
        assert row['evidence'] == {'product': 'P3', 'node': node_id, 'field': path, 'node_sha256': digest(node),
            'value': links.field(node, path), 'relationship': relationship, 'review_reason': reason}
        assert row['original_reading'] == source['reading'] and row['all_uses_governed'] is False
        assert [(u['start'], u['end'], u['quote'], u['original_use_sha256']) for u in row['uses']] == [
            (u['start'], u['end'], u['quote'], digest(u)) for u in source['uses']]
        for use in row['uses']:
            assert text[use['start']:use['end']] == use['quote']
            expected = 'GOVERNING_USE_NOT_RECONCILED'
            if short in links.EXPECTED_USE_CLASSES:
                candidates = [label for label, starts in links.EXPECTED_USE_CLASSES[short].items() if use['start'] in starts]
                assert len(candidates) == 1
                expected = candidates[0]
            assert use['disposition'] == expected
            app = apps.get((use['start'], use['end']))
            assert (use['application_id'], use['application_rule'], use['application_sha256']) == (
                app['id'] if app else None, app['rule'] if app else None, digest(app) if app else None)
    original_differences = []
    for record in coverage['records']:
        for field, kind in (('not_proposed_by_supplied_forms', 'WITHHELD'), ('additional_proposals', 'ADDITIONAL')):
            original_differences.extend((record['id'], kind, u['start'], u['end'], u['quote'], u['context']) for u in record[field])
    actual = value['discovery_differences']
    assert [(u['record'], u['kind'], u['start'], u['end'], u['quote'], u['context']) for u in actual] == original_differences
    assert Counter(u['disposition'] for u in actual) == {'COMPOUND_COMPONENT_WITHHELD': 11,
        'REVIEWED_AGENCY_SLASH_BOUNDARY': 2, 'ALREADY_IN_289_APPLICATION_SUPPLEMENT': 2}
    for row in actual:
        assert row['automatic_scope_established'] is False
        if row['kind'] == 'ADDITIONAL':
            assert row['application_id'] == 'amount:21547'
            assert row['record_use_disposition'] == ('OTHER_PURPOSE_DEFINITION' if row['record'].startswith('U06-') else 'EXISTING_CONDITIONAL_APPLICATION')
    assert value['original_use_associations'] == sum(len(r['uses']) for r in value['records']) == 610
    return {'status': 'PASS', 'all_original_identities_and_reviewed_links': True,
            'purpose_cases_independently_enumerated': True}


def verify():
    value = read(HERE / 'coverage.json')
    result = validate(value)
    refused = []
    for kind in ('missing-record', 'missing-use', 'wrong-evidence-node', 'wrong-evidence-value', 'other-purpose', 'false-completion'):
        bad = deepcopy(value)
        if kind == 'missing-record': bad['records'].pop()
        elif kind == 'missing-use': bad['records'][0]['uses'].pop()
        elif kind == 'wrong-evidence-node': bad['records'][0]['evidence']['node'] = 'basf-redemption:tax'
        elif kind == 'wrong-evidence-value': bad['records'][2]['evidence']['value'] = 'USD'
        elif kind == 'other-purpose':
            row = next(r for r in bad['records'] if r['id'].startswith('U06-'))
            use = next(u for u in row['uses'] if u['start'] == 19119)
            use['disposition'] = 'EXISTING_CONDITIONAL_APPLICATION'
        else: bad['whole_task_complete'] = True
        try:
            validate(bad)
        except AssertionError:
            refused.append(kind)
        else:
            raise AssertionError('Accepted semantic-reconciliation mutation: ' + kind)
    result['refused'] = refused
    save(HERE / 'verification.json', result)
    return result


def seal():
    value = read(HERE / 'coverage.json')
    counts = dict(Counter(u['disposition'] for r in value['records'] for u in r['uses']))
    result = {'status': 'PASS', 'task': 'basf-references', 'original_task_complete': False,
        'result_kind': 'COMPLETE_ORIGINAL_DEFINITION_SEMANTIC_RECONCILIATION', 'use_dispositions': counts,
        'resources': costs(), 'next_action': 'Bind reviewed conditional applications by record identity, source interval and purpose; preserve other-use uncertainty and prior report',
        'remaining': 'Original source-specific acceptance, other governing-use links, typed agency mapping and source uncertainty'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(HERE / 'stages' / s / 'started.json')['command'] for s in STAGES],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU; no GPU use', 'seeds': 'N/A deterministic',
        'data_version': sha(SOURCE / 'definition-dossier.json'), 'wall_time': costs(), 'plan': PLAN, 'result': rel(HERE / 'result.json')})
    (HERE / 'RESULT.md').write_text('''# Current definition meanings and governing uses

All62original records now have a specific inspected P3field and a statement of
what that field represents and leaves open. All610original use associations
remain. A record is never discharged by a matching label, a source overlap or
the presence of a related conditional profile.

The exact purpose controls distinguish a tax application from a make-whole
application even when the original records share the same spelling and span.
The repaired next mechanism must make those links explicit in the complete
answer. Existing declaration content is reused; remaining use-scope decisions
are kept separate. No legal or factual uncertainty is overwritten.

|Decision|Primary criterion|Veto status|Main uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain complete semantic reconciliation|All original identities and inspected field links; independent purpose cases|Six omission/forgery/completion controls refused|Remaining occurrence-specific scope and missing typed source classifications|Integrate exact purpose-aware bindings; then original-task validator|Whole task, exhaustive grammar, historical law or actual events|

The strongest alternative explanation for an apparently unimplemented term is
that its meaning already appears in a conditional clause but its definition
record lacks the connection. The complete matrix distinguishes this from a
genuinely missing declaration or agency-classification mechanism. A reviewed
meaning is still a supplied interpretation; the matrix alone cannot prove its
application to every original occurrence or another prospectus.
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
        engine.PREP, engine.HERE, engine.PLAN, engine.METHOD, engine.TARGETS = PREP, HERE, PLAN, METHOD, ()
        engine.frozen()
    save(folder / 'started.json', {'command': ['.venv/bin/python', '-m', 'scripts.prospectus_definition_semantics', stage],
        'started_at': datetime.now(timezone.utc).isoformat(), 'seconds_bound': 90})
    start = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Definition semantic reconciliation bound')))
    signal.alarm(90)
    try:
        result = globals()[stage]()
        if stage != 'prepare': engine.frozen()
        costs(time.monotonic() - start)
        result['wall_seconds'] = time.monotonic() - start
        save(folder / 'result.json', result)
        if stage == 'seal': save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as error:
        save(folder / 'failure.json', {'type': type(error).__name__, 'message': str(error), 'wall_seconds': time.monotonic() - start})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
