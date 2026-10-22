"""Bounded original H1 source census and requirement reconciliation."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, write
from scripts.prospectus_h1_current_acceptance import read, require, BASE, AUTH, inventory
from scripts.prospectus_h1_current_coverage import references, schema_probes

HERE = ROOT / BASE / 'attempt-068'
PREP = ROOT / AUTH / 'reviews/h1-original-requirements-431'
DONOR = ROOT / BASE / 'attempt-067'
PLAN = 'docs/plans/prospectus-h1-original-requirements-2026-10-22.md'
SELF = 'scripts/prospectus_h1_original_requirements.py'
LIMITS = {'new_bytes': 96 * 1024**2, 'measured_seconds': 180, 'control_seconds': 60,
          'worker_seconds': 120, 'unchanged_retries': 0, 'production_writes': 0}


def rel(p):
    return str(p.relative_to(ROOT))


def save(path, value, *, large=False):
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
    require(len(raw) < (24 * 1024**2 if large else 2 * 1024**2), 'New output ceiling')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)


def resources():
    initial = read(PREP / 'accounting-start.json')
    paths = {p for folder in (PREP, HERE) if folder.exists() for p in folder.rglob('*') if p.is_file()}
    paths.update(ROOT / n for n in (SELF, PLAN))
    paths.add(ROOT / AUTH / 'revisions/0431.json')
    paths.update(p for p in (ROOT / AUTH / 'history').glob('*.json') if p.name not in initial['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (ROOT / AUTH / 'program.json').stat().st_size - initial['program_bytes'])
    seconds = sum(read(p)['seconds'] for folder in (PREP, HERE) for p in folder.glob('commands/*.json'))
    return {'new_bytes': size, 'new_measured_seconds': seconds, 'control_reservation_seconds': 60,
        'prior_known_bytes': initial['prior']['known_cumulative_bytes'],
        'prior_booked_seconds': initial['prior']['known_cumulative_seconds'],
        'known_cumulative_bytes': initial['prior']['known_cumulative_bytes'] + size,
        'booked_cumulative_seconds': initial['prior']['known_cumulative_seconds'] + seconds + 60,
        'historical_unmeasured_seconds': 'UNKNOWN; earlier control allocations and manual inspection are not measured runtime',
        'allowed': size < 94 * 1024**2 and seconds < 180}


def prepare():
    tick = time.monotonic()
    a = Authority(ROOT)
    old, _, _ = a.spec()
    require(old['revision'] == 430 and not PREP.exists() and not HERE.exists(), 'Fresh430required')
    state = a.status()
    require(not state['running'] and any(r['id'] == 'individual-unit-conflict' for r in state['current_build']['verified_criteria']),
            'Recorded/refreshed current unit evidence required')
    from scripts.prospectus_h1_acceptance_program import costs
    save(PREP / 'accounting-start.json', {'prior': costs(),
        'history_names': [p.name for p in (ROOT / AUTH / 'history').glob('*.json')],
        'program_bytes': (ROOT / AUTH / 'program.json').stat().st_size})
    evidence = {rel(DONOR / n): h for n, h in read(DONOR / 'outputs.json').items()}
    for n in (SELF, PLAN, rel(DONOR / 'outputs.json'),
        'scripts/prospectus_h1_current_coverage.py', BASE + '/attempt-007/products.json.gz',
        BASE + '/attempt-066/requirements.json', AUTH + '/dossiers/source-bes-dep-05.md'):
        evidence[n] = file_hash(ROOT / n)
    save(PREP / 'freeze.json', {'evidence': evidence, 'production': inventory(ROOT / 'src/legalmath'), 'limits': LIMITS})
    program = deepcopy(old)
    program['revision'] = 431
    task = next(t for t in program['tasks'] if t['id'] == 'source-bes-dep-05')
    contract = deepcopy(task['build_criterion_lineage'])
    task.update(dossier=PLAN, pre_admission_review=PLAN, build_criteria_scope=[],
        reason='Reconcile original H1 source requirements and exact remaining source intervals against current067delivery',
        h1_original_requirements={'freeze': rel(PREP / 'freeze.json'), 'limits': LIMITS})
    task['inputs'] = sorted(set(task['inputs']) | set(evidence) | {rel(PREP / 'freeze.json')})
    require(task['build_criterion_lineage'] == contract, 'Previous unit evidence contract changed')
    attempts = [e['attempt'] for e in a.events() if e['kind'] == 'ADMIT' and e['budget_key'] == task['budget_key']]
    require(len(attempts) == old['budgets'][task['budget_key']]['maximum_new_attempts'] == 67, 'Retain67admissions')
    program['budgets'][task['budget_key']]['maximum_new_attempts'] = 68
    routes = read(ROOT / old['continuation_review']['routes'])
    routes['baseline_revision'] = 431
    for row in routes['tasks']:
        if row['task'] == task['id']:
            row.update(task_sha256=digest(task), dossier=PLAN, phase=0,
                remaining='Unit criterion verified; complete meaning, source authority and original source acceptance remain open.',
                next_action='Census exact source-to-field gaps and reconcile original requirements; review concrete omissions, then continue original frontier.',
                stop_condition='Attempt068;96MiB and180+60seconds; no production or external action; coverage counts cannot accept task.')
    save(PREP / 'routes.json', routes)
    program['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    program['continuation_review']['bindings'].update({n: file_hash(ROOT / n) for n in
        (SELF, PLAN, rel(PREP / 'routes.json'), rel(PREP / 'freeze.json'))})
    require(program['obligations'] == old['obligations'] and program['build_contract'] == old['build_contract'], 'Original scope changed')
    save(PREP / 'proposal.json', program, large=True)
    save(PREP / 'review.json', {'baseline': digest(old), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Return from completed acceptance repair to exact original source requirements',
                    'Preserve current unit criterion and all historical requirements'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN, 'counts_are_not_semantics': True,
            'production_changes': 0, 'external_opinion_required': False},
        'evidence_contract': {'question': 'Which exact original source passages and substantive requirements remain unevaluated?',
            'baseline': rel(DONOR), 'primary': 'Exact source/quote/interval and original requirement preservation with explicit dispositions',
            'promotion_veto': ['Lost source requirement', 'Context treated as meaning', 'Wrong source identity or interval'],
            'continuation_veto': ['Corrupt common evidence', 'Invalid authority', 'Exhausted bound'],
            'explanatory': ['Occurrence counts', 'Runtime'], 'not_concluded': ['Semantic completeness', 'Source truth', 'Original task completion']},
        'budget_revision': {'budget_key': task['budget_key'], 'previous_maximum': 67, 'new_maximum': 68,
            'retained_attempts': attempts, 'reason': 'Return to original substantive requirements after verified current unit acceptance',
            'next_discriminating_check': 'Exact unreferenced source intervals and current interpretation limitations',
            'stop_condition': LIMITS, 'same_scope_authorization': 'Recover and continue original prospectus build'}})
    save(PREP / 'commands/preparation.json', {'seconds': time.monotonic() - tick, 'command': SELF + ' prepare'})
    forecast = resources()['new_bytes'] + 3 * (PREP / 'proposal.json').stat().st_size + 4 * 1024**2
    require(forecast < 94 * 1024**2, 'Forecast exceeds reservation')
    return {'status': 'PREPARED', 'revision': 431, 'forecast_bytes': forecast, 'resources': resources()}


def gaps(text, intervals):
    covered = [False] * len(text)
    for left, right in intervals:
        covered[left:right] = [True] * (right - left)
    missing = [i for i, char in enumerate(text) if not covered[i] and not char.isspace()]
    if not missing:
        return []
    groups, left, previous = [], missing[0], missing[0]
    for i in missing[1:]:
        if any(covered[previous + 1:i]):
            groups.append({'start': left, 'end': previous + 1, 'quote': text[left:previous + 1]})
            left = i
        previous = i
    groups.append({'start': left, 'end': previous + 1, 'quote': text[left:previous + 1]})
    return groups


def run():
    tick = time.monotonic()
    a = Authority(ROOT)
    program, tasks, _ = a.spec()
    task = tasks['source-bes-dep-05']
    admission = read(HERE / 'admission.json')
    require(program['revision'] == 431 and admission['binding'] == a.binding(task), 'Current431admission required')
    require(not (HERE / 'started.json').exists(), 'Preserve prior run; no unchanged retry')
    save(HERE / 'started.json', {'at': datetime.now(timezone.utc).isoformat(), 'command': SELF + ' run'})
    frozen = read(PREP / 'freeze.json')
    require(all(file_hash(ROOT / n) == h for n, h in frozen['evidence'].items()), 'Frozen evidence changed')
    require(inventory(ROOT / 'src/legalmath') == frozen['production'], 'Production changed')
    probes = schema_probes()
    require(gaps('ab cd', [(0, 2)]) == [{'start': 3, 'end': 5, 'quote': 'cd'}]
            and gaps('ab cd', [(0, 5)]) == [], 'Interval union diagnostic failed')
    graph = read(ROOT / BASE / 'attempt-007/products.json.gz')['P1']['payload']['graph']
    units = {u['id']: u for u in graph['units']}
    require(len(units) == len(graph['units']), 'Duplicate original source')
    answer = read(DONOR / 'ordinary-answer.json.gz')
    require(answer == read(DONOR / 'installed-answer.json.gz'), 'Current actual answer differs by environment')
    reading = answer['answer']['source_statement_cells']
    sections = {'answer': {'source_statement_cells': reading}}
    sections.update({n: answer[n] for n in ('cash_flow_review', 'risk_table_review', 'h1_scope_review',
        'h1_individual_unit_review', 'h1_source_relationship_review')})
    direct = {}
    for row in references(sections, units):
        if not row['context']:
            direct.setdefault(row['id'], []).append(row)
    selected = sorted((u for u in units.values() if u['document'] == 'bes-interim-h1-2010' and 51 <= u['page'] <= 173),
                      key=lambda u: (u['page'], u['order'], u['id']))
    missing = []
    for u in selected:
        rows = direct.get(u['id'], [])
        intervals = gaps(u['raw'], [(r['start'], r['end']) for r in rows])
        if intervals:
            missing.append({'id': u['id'], 'page': u['page'], 'order': u['order'], 'quote': u['raw'],
                            'uncovered': intervals, 'direct_reference_count': len(rows)})
    address_rows = []
    key = lambda u: (u['page'], u['order'], u['id'])
    for address in answer['h1_reference_availability_review']['map']['registry']:
        first, end = address['heading'], address['end_exclusive']
        local = [r for r in missing if key(first) <= key(r) < key(end)]
        address_rows.append({'level': address['level'], 'number': address['number'],
            'heading': first['id'], 'end_exclusive': end['id'], 'uncovered_source_occurrences': len(local),
            'missing_ids': [r['id'] for r in local],
            'delivered_sections': [r['path'] for r in address['delivered_sections']],
            'complete_meaning_checked': False})
    requirements = read(ROOT / BASE / 'attempt-066/requirements.json')['rows']
    dispositions = []
    for index, row in enumerate(requirements):
        status = row['status']
        current = ('CURRENT_FINITE_DELIVERY_RETAINED_MEANING_NOT_FULLY_PROVED'
                   if status.startswith(('RETAINED', 'THIS_ATTEMPT')) else 'ORIGINAL_UNRESOLVED_OR_HISTORICAL_LIMIT_REQUIRES_SOURCE_REVIEW')
        dispositions.append({'original_index': index, 'original': row, 'current_disposition': current,
                             'current_delivery': rel(DONOR / 'ordinary-answer.json.gz')})
    diagnostic = {'status': 'CURRENT_SOURCE_CENSUS_WITH_MEANING_UNCHECKED', 'original_task_complete': False,
        'schema_probes': probes, 'source_occurrences': len(selected), 'uncovered_occurrences': len(missing),
        'addresses': address_rows, 'uncovered_source': missing,
        'source_context': reading['source_context'], 'scope': reading['scope'],
        'known_source_limits': ['Individual statement intended unit unresolved', 'Page59clipped values and currency unresolved',
            'Controlling Portuguese edition and historical authenticity not established', 'Incorporation alternatives not selected',
            'Bank/Group statements do not supply BES Finance standalone accounts',
            'Source note addresses and exact quotations do not prove full interpretation'],
        'reference_discrepancies': answer['h1_reference_availability_review']['map']['discrepancies'],
        'interpretation': 'Missing intervals nominate exact passages for source review; complete quote coverage is not semantic correctness.'}
    save(HERE / 'source-census.json', diagnostic)
    save(HERE / 'requirements.json', {'rows': dispositions, 'original_requirement_count': len(requirements),
        'original_task_complete': False, 'next_action': 'Review every uncovered original passage and the meaning of its closest delivered field.'})
    require(inventory(ROOT / 'src/legalmath') == frozen['production'], 'Diagnostic changed production')
    save(HERE / 'commands/census.json', {'seconds': time.monotonic() - tick, 'command': SELF + ' run', 'status': 'PASS'})
    require(resources()['allowed'], 'Reservation exceeded')
    return {'status': diagnostic['status'], 'source_occurrences': len(selected), 'uncovered_occurrences': len(missing),
            'address_count': len(address_rows), 'requirements': len(requirements), 'resources': resources()}


if __name__ == '__main__':
    action = sys.argv[1]
    require(action in {'prepare', 'run', 'resources'}, 'Unknown action')
    print(json.dumps(globals()[action]()), flush=True)
