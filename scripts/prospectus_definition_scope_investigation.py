"""Source-first definition investigation; no production parser or legal closure."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
os.environ.update(PYTHONDONTWRITEBYTECODE='1', CUDA_VISIBLE_DEVICES='-1',
                  PYTHONPATH=os.pathsep.join((str(ROOT / 'src'), str(ROOT))))
from legalmath.prospectus.execution_authority import Authority, CODE, digest
from legalmath.prospectus.successor.contracts import digest as product_digest

AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
PRIOR = AUTH / 'attempts/basf-references/attempt-025'
PREP = AUTH / 'reviews/definition-scope-285'
HERE = AUTH / 'attempts/basf-references/attempt-026'
METHOD = 'scripts/prospectus_definition_scope_investigation.py'
PLAN = 'docs/plans/prospectus-definition-scope-continuation-2026-10-18.md'
STAGES = ('snapshot', 'inventory', 'reconcile', 'seal')
PREPARATION = ('probe', 'propose')
LEDGER = AUTH / 'attempts/basf-references/attempt-022/candidate-answer-reconciliation.json.gz'
P2_SHA256 = '9f30313da49e2b98669c027747404271ce1f09279a5f2b6e0c860d8fe672e561'


def read(path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(gzip.compress(data, mtime=0) if path.suffix == '.gz' else data)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path):
    return str(path.relative_to(ROOT))


def imported_sources():
    """Bind the actual project helpers used by the identity reconstruction."""
    modules = {}
    for name, module in tuple(sys.modules.items()):
        if not (name == 'legalmath' or name.startswith('legalmath.') or
                name == 'scripts' or name.startswith('scripts.')):
            continue
        filename = getattr(module, '__file__', None)
        if filename is None:  # Namespace packages carry no executable source.
            continue
        path = Path(filename).resolve()
        expected = ROOT / ('src' if name.startswith('legalmath') else 'scripts')
        assert path.is_relative_to(expected) and path.suffix == '.py', (name, str(path))
        modules[name] = {'path': rel(path), 'sha256': sha(path)}
    assert {'legalmath.prospectus.successor.contracts',
            'legalmath.prospectus.successor.occurrences',
            'scripts.prospectus_internal_consumer_continuation',
            'scripts.prospectus_typed_delta'} <= modules.keys()
    return modules


def prior_check():
    manifest = read(PRIOR / 'outputs.json')
    assert manifest['result.json'] == sha(PRIOR / 'result.json')
    for name, expected in manifest.items():
        assert sha(PRIOR / name) == expected, 'Sealed025 changed: ' + name
    result = read(PRIOR / 'result.json')
    assert result['status'] == 'PASS' and result['original_task_complete'] is False
    assert result['result_kind'] == 'FINITE_STATUTORY_SOURCE_TO_ANSWER_INTEGRATION'
    return result


def products():
    from scripts.prospectus_internal_consumer_continuation import retained
    from scripts.prospectus_typed_delta import apply
    row = read(PRIOR / 'candidate-retained-answer.json.gz')
    original, _ = retained('candidate-answer')
    result = apply(original, row['products_delta'])
    assert product_digest(result) == row['products_sha256'], 'Lossy sealed025 reconstruction'
    return result


def costs(extra_seconds=0):
    start = read(PREP / 'accounting-start.json')
    receipts = [p for d in (PREP, HERE) for pattern in ('stages/*/result.json', 'stages/*/failure.json')
                for p in d.glob(pattern)]
    seconds = extra_seconds + sum(read(p)['wall_seconds'] for p in receipts)
    seconds += sum(read(p)['wall_seconds'] for p in PREP.glob('source-marker-review*.json'))
    paths = {p for d in (PREP, HERE) if d.exists() for p in d.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / p for p in (METHOD, PLAN))
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    paths.add(AUTH / 'revisions/0285.json')
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    assert seconds < 1800 and size < 60 * 1024**2, 'Definition investigation resource bound exhausted'
    prior_seal = read(PRIOR / 'stages/seal/result.json')
    return {'additional_measured_seconds': seconds, 'additional_bytes': size,
            'explicit_additional_seconds_bound': 1800, 'explicit_additional_bytes_bound': 64 * 1024**2,
            'reserve_bytes': 4 * 1024**2, 'prior_admissions_retained': 25,
            'prior_statutory_resources': start['prior_statutory_resources'],
            'prior_statutory_seal_receipt_seconds': prior_seal['wall_seconds'],
            'prior_statutory_snapshot_plus_final_seal_seconds':
                start['prior_statutory_resources']['additional_measured_seconds'] + prior_seal['wall_seconds'],
            'manual_authoring_reading_controller_seconds': 'UNKNOWN', 'prior_costs_reset': False}


def frozen():
    prior_check()
    for name, expected in read(PREP / 'freeze.json')['bindings'].items():
        assert sha(ROOT / name) == expected, 'Investigation method/input changed: ' + name
    admission = read(HERE / 'admission.json')
    assert digest(read(AUTH / 'program.json')) == admission['program_sha256']
    for name, expected in admission['binding'].items():
        assert sha(ROOT / name) == expected, 'Admission input changed: ' + name


def source_view():
    p = products()
    selected = p['P2']['payload']['selected_contract']
    candidate, raw_text = selected['candidate_text'], selected['raw_body']
    assert p['P2']['sha256'] == P2_SHA256 and len(candidate) == 46365
    assert p['P2']['payload']['assembly']['continuous_text'] == candidate
    graph = p['P1']['payload']['graph']
    raw = {u['id']: u for u in graph['units']}
    assert len(raw) == len(graph['units'])
    source_map = selected['source_map']
    cursor = 0
    for item in source_map:
        unit = raw[item['unit']]
        assert cursor <= item['start'] < item['end'] <= len(raw_text)
        assert not raw_text[cursor:item['start']].strip(), 'Unmapped raw text'
        assert unit['visible'] and raw_text[item['start']:item['end']] == unit['raw']
        cursor = item['end']
    assert not raw_text[cursor:].strip(), 'Unmapped raw suffix'
    pieces = []
    for mapping in selected['character_map']:
        left, right = mapping['start'], mapping['end']
        if left == right:
            continue
        if mapping['operation'] != 'COPY':
            assert mapping['operation'] == 'SUBSTITUTE' and mapping.get('basis')
            pieces.append({'start': left, 'end': right, 'text': candidate[left:right],
                           'kind': 'SUPPLIED_OR_TRANSFORMED', 'operation': mapping['operation'],
                           'basis': mapping['basis'], 'raw_binding': None,
                           'replaced_raw_interval': {'start': mapping['raw_start'],
                               'end': mapping['raw_end'],
                               'quote': raw_text[mapping['raw_start']:mapping['raw_end']]}})
            continue
        a, b = mapping['raw_start'], mapping['raw_end']
        assert b - a == right - left and candidate[left:right] == raw_text[a:b]
        cursor = a
        for item in source_map:
            x, y = max(a, item['start']), min(b, item['end'])
            if x >= y:
                continue
            if cursor < x:
                text = raw_text[cursor:x]
                assert text.isspace(), 'Unmapped non-whitespace in COPY'
                pieces.append({'start': left + cursor - a, 'end': left + x - a,
                               'text': text, 'kind': 'GENERATED_SEPARATOR', 'raw_binding': None})
            unit = raw[item['unit']]
            start, end = x - item['start'], y - item['start']
            anchor = {'unit': unit['id'], 'document': unit['document'],
                      'source_sha256': unit['source_sha256'], 'start': start, 'end': end,
                      'quote': unit['raw'][start:end], 'page': unit['page'],
                      'bbox': unit['bbox'], 'language': unit['language']}
            pieces.append({'start': left + x - a, 'end': left + y - a,
                           'text': candidate[left + x - a:left + y - a],
                           'kind': 'EXACT_SOURCE_COPY', 'raw_binding': anchor})
            cursor = y
        if cursor < b:
            text = raw_text[cursor:b]
            assert text.isspace(), 'Unmapped trailing non-whitespace in COPY'
            pieces.append({'start': left + cursor - a, 'end': right,
                           'text': text, 'kind': 'GENERATED_SEPARATOR', 'raw_binding': None})
    pieces.sort(key=lambda item: (item['start'], item['end']))
    cursor = 0
    for piece in pieces:
        assert piece['start'] == cursor and piece['text'] == candidate[cursor:piece['end']]
        if piece['raw_binding']:
            assert piece['text'] == piece['raw_binding']['quote']
        cursor = piece['end']
    assert cursor == len(candidate), 'Incomplete candidate map'
    from legalmath.prospectus.successor.occurrences import _DependencyLookup
    assembly = p['P2']['payload']['assembly']
    lookup = _DependencyLookup(graph, assembly)
    selected_units = {u['unit']: u for u in assembly['units']}
    assert len(selected_units) == len(assembly['units'])
    for piece in pieces:
        if piece['raw_binding'] is None:
            piece['assembly_uses'] = []
            continue
        source_anchor = {k: piece['raw_binding'][k] for k in
                         ('unit', 'document', 'source_sha256', 'start', 'end', 'quote')}
        matches = lookup.uses(graph, assembly, source_anchor, roles=('OPERATIVE', 'UNKNOWN'))
        piece['assembly_uses'] = [{**use, 'role': selected_units[use['unit']]['role'],
            'context': selected_units[use['unit']]['context'],
            'questions': selected_units[use['unit']]['questions'],
            'language': selected_units[use['unit']]['language']} for use in matches]
        piece['assembly_use_status'] = ('MISSING' if not matches else
            'UNIQUE_COPY' if len(matches) == 1 else 'MULTIPLE_COPIES')
    source = {'candidate_text': candidate, 'pieces': pieces,
         'p1_sha256': p['P1']['sha256'], 'p2_sha256': p['P2']['sha256'],
         'selected_contract_sha256': product_digest(selected), 'source_graph_sha256': product_digest(graph),
         'source': rel(PRIOR / 'candidate-retained-answer.json.gz'),
         'source_sha256': sha(PRIOR / 'candidate-retained-answer.json.gz'),
         'assembly_sha256': product_digest(assembly),
         'assembly_copy_statuses': dict(Counter(piece['assembly_use_status'] for piece in pieces
                                                if piece['raw_binding'] is not None)),
         'assembly_role_does_not_establish_governing_scope': True}
    headers = list(re.finditer(r'(?m)^§\s+(\d+)\s*$', candidate))
    sections = [{'number': m.group(1), 'start': m.start(),
                 'end': headers[i + 1].start() if i + 1 < len(headers) else len(candidate)}
                for i, m in enumerate(headers)]
    assert [r['number'] for r in sections] == [str(i) for i in range(1, 16)]
    source['preamble'] = {'start': 0, 'end': sections[0]['start'],
                          'quote': candidate[:sections[0]['start']]}
    return source, sections


def snapshot():
    source, sections = source_view()
    save(HERE / 'selected-source.json.gz', source)
    with (HERE / 'selected-text.txt').open('x') as stream:
        stream.write(source['candidate_text'])
    save(HERE / 'sections.json', sections)
    return {'status': 'PASS', 'candidate_characters': len(source['candidate_text']),
            'source_pieces': dict(Counter(p['kind'] for p in source['pieces'])), 'sections': len(sections),
            'assembly_copy_statuses': source['assembly_copy_statuses'],
            'ordinary_answers_run': 0, 'discovery_evaluated': False}


def clipped(source, interval):
    text = source['candidate_text']
    start, end = interval['start'], interval['end']
    assert type(start) is int and type(end) is int and 0 <= start < end <= len(text)
    assert interval['quote'] == text[start:end], 'Authored source interval changed'
    result = []
    for piece in source['pieces']:
        a, b = max(start, piece['start']), min(end, piece['end'])
        if a >= b:
            continue
        item = {'start': a, 'end': b, 'text': text[a:b], 'kind': piece['kind']}
        if piece['raw_binding']:
            anchor = deepcopy(piece['raw_binding'])
            anchor['start'] += a - piece['start']
            anchor['end'] = anchor['start'] + b - a
            anchor['quote'] = text[a:b]
            item['raw_binding'] = anchor
            item['assembly_uses'] = [{**use, 'start': use['start'] + a - piece['start'],
                'end': use['start'] + b - piece['start'],
                'source': {k: anchor[k] for k in
                           ('unit', 'document', 'source_sha256', 'start', 'end', 'quote')}}
                for use in piece['assembly_uses']]
            item['assembly_use_status'] = piece['assembly_use_status']
        else:
            item.update(raw_binding=None, basis=piece.get('basis'), assembly_uses=[])
        result.append(item)
    assert sum(r['end'] - r['start'] for r in result) == end - start
    return {**interval, 'source_pieces': result}


def literal_intervals(text, forms):
    """Reconcile only manually supplied spellings; this discovers no terms."""
    assert forms and len(forms) == len(set(forms))
    found = set()
    for form in forms:
        assert isinstance(form, str) and form.strip()
        for match in re.finditer(re.escape(form), text):
            a, b = match.span()
            # Keep compound components visible, but do not turn inflections or
            # arbitrary substrings into literal spellings of the supplied term.
            if a and (text[a - 1].isalnum() or text[a - 1] == '_'):
                continue
            if b < len(text) and (text[b].isalnum() or text[b] == '_'):
                continue
            found.add((a, b))
    return found


def inventory():
    source = read(HERE / 'selected-source.json.gz')
    dossier = read(HERE / 'definition-dossier.json')
    authors = [p for p in (HERE / 'stages').glob('author-*/result.json')
               if read(p)['status'] == 'PASS']
    assert len(authors) == 1, 'One successful measured source-authoring receipt required'
    author = read(authors[0].parent / 'started.json')
    assert read(authors[0])['dossier_sha256'] == sha(HERE / 'definition-dossier.json')
    assert author['author_script_sha256'] == sha(HERE / 'author-dossier.py')
    assert author['author_script_sha256'] == sha(PREP / 'source-author-template.py')
    assert author['source_snapshot_sha256'] == sha(HERE / 'selected-source.json.gz')
    assert author['source_sections_sha256'] == sha(HERE / 'sections.json')
    assert author['method_sha256'] == sha(ROOT / METHOD)
    assert dossier['selected_contract_sha256'] == source['selected_contract_sha256']
    assert dossier['discovery_completeness_established'] is False
    assert dossier['ordinary_answer_integration_established'] is False
    assert dossier['preamble_reading']['reading'].strip()
    assert dossier['preamble_reading']['selected_text_sha256'] == digest(source['preamble']['quote'])
    sections = read(HERE / 'sections.json')
    assert [r['number'] for r in dossier['section_readings']] == [r['number'] for r in sections]
    for reading, section in zip(dossier['section_readings'], sections):
        assert reading['reading'].strip() and reading['selected_section_sha256'] == digest(
            source['candidate_text'][section['start']:section['end']])
    records = dossier['records']
    ids = {r['id'] for r in records}
    assert len(ids) == len(records) and records
    bound = []
    for record in records:
        assert record['reading'].strip() and record['scope_alternatives']
        expected_uses = literal_intervals(source['candidate_text'], record['forms'])
        assert expected_uses, 'Authored spellings have no current source occurrence'
        for scope in record['scope_alternatives']:
            assert scope['reason'].strip() and scope['scope'].strip()
            assert scope['source_reasons'], 'Scope needs a source-bound reason'
            assert scope['extent'], 'Retain proposed scope intervals, not just a label'
            for interval in scope['extent']:
                clipped(source, interval)
            for interval in scope['source_reasons']:
                clipped(source, interval)
        row = deepcopy(record)
        row['scope_alternatives'] = [{**scope,
            'extent': [clipped(source, interval) for interval in scope['extent']],
            'source_reasons': [clipped(source, interval) for interval in scope['source_reasons']]}
            for scope in record['scope_alternatives']]
        row['declarations'] = [clipped(source, interval) for interval in record['declarations']]
        row['uses'] = []
        use_intervals = set()
        for use in record['uses']:
            assert use['classification'] in {'IN_DEFINING_EXCERPT', 'POTENTIAL_USE', 'AMBIGUOUS_USE',
                'UNRESOLVED_SCOPE',
                'MISSING_DECLARATION', 'COMPOUND_COMPONENT', 'UNSUPPORTED_FORM'}
            assert set(use['declaration_candidates']) <= ids
            assert use['scope_reading'].strip()
            assert use['quote'] in record['forms'], 'Use is not an authored literal spelling'
            assert (use['start'], use['end']) not in use_intervals, 'Duplicate authored use'
            use_intervals.add((use['start'], use['end']))
            row['uses'].append(clipped(source, use))
        assert use_intervals == expected_uses, 'Authored spelling occurrences were omitted or invented'
        assert row['declarations'] or any(u['classification'] in {'MISSING_DECLARATION', 'UNSUPPORTED_FORM'}
                                         for u in row['uses'])
        bound.append(row)
    assert dossier['known_misses'] and dossier['remaining']
    save(HERE / 'bound-inventory.json.gz', {**dossier, 'records': bound,
         'authored_dossier_sha256': sha(HERE / 'definition-dossier.json'),
         'source_snapshot_sha256': sha(HERE / 'selected-source.json.gz'),
         'parser_evaluated': False, 'binding_admission_granted': False})
    return {'status': 'PASS', 'source_records': len(records),
            'retained_use_occurrences': sum(len(r['uses']) for r in records),
            'section_readings': len(sections), 'counts_are_not_recall': True,
            'literal_occurrences_of_authored_forms_reconciled': True,
            'discovery_evaluated': False, 'ordinary_answers_run': 0}


def reconcile():
    path = LEDGER
    original = read(path)
    current = read(PRIOR / 'original-ledger-reconciliation.json.gz')
    identities = [(r['family'], r['index']) for r in original['records']]
    assert len(identities) == len(set(identities)) == 60
    assert Counter(r['family'] for r in original['records']) == {
        'historical_candidate_lines': 47, 'additional_explicit_review_findings': 13}
    assert identities == [(r['family'], r['index']) for r in current['records']]
    for old, new in zip(original['records'], current['records']):
        assert all(new[k] == value for k, value in old.items()), 'Prior ledger record lost'
    inventory = read(HERE / 'bound-inventory.json.gz')
    # Retain the whole original document, including every historical disposition.
    save(HERE / 'reconciliation.json.gz', {'original_reference_ledger': original,
         'statutory_updated_reference_ledger': current,
         'statutory_updated_reference_ledger_sha256': sha(PRIOR / 'original-ledger-reconciliation.json.gz'),
         'original_reference_ledger_path': rel(path), 'original_reference_ledger_sha256': sha(path),
         'original_reference_records': len(identities), 'added_definition_records': [r['id'] for r in inventory['records']],
         'definition_inventory_sha256': sha(HERE / 'bound-inventory.json.gz'),
         'denominator_replaced': False, 'original_task_complete': False})
    return {'status': 'PASS', 'original_reference_records': 60,
            'additional_definition_records': len(inventory['records']),
            'original_task_complete': False, 'denominator_replaced': False}


def seal():
    findings = read(HERE / 'bound-inventory.json.gz')
    result = {'status': 'PASS', 'task': 'basf-references',
        'result_kind': 'CURRENT_SELECTED_DEFINITION_SOURCE_INVESTIGATION',
        'original_task_complete': False, 'discovery_evaluated': False, 'ordinary_answers_run': 0,
        'resources': costs(), 'remaining': findings['remaining'],
        'next_action': 'Freeze independent finite source cases and known misses; review reusable discovery and its ordinary-consumer integration before admission'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': subprocess.check_output(
         ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
         'commands': [row['command'] for row in sorted(
             (read(p) for p in (HERE / 'stages').glob('*/started.json')),
             key=lambda row: row['started_at'])],
         'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU; GPU intentionally hidden',
         'data_version': sha(PRIOR / 'outputs.json'), 'random_seeds': 'N/A deterministic source investigation',
         'wall_time': costs(), 'plan': PLAN, 'result': rel(HERE / 'result.json'),
         'artifacts': rel(HERE), 'method_freeze': sha(PREP / 'freeze.json')})
    note = '''# Current definitions and uses investigated

The source dossier binds the current selected contract to its raw source copies,
supplied transformations and generated separators. All fifteen selected sections
were read. Declarations, aliases, individual uses, competing scopes, missing terms
and unsupported forms remain source-review evidence. No parser, binding admission
or ordinary-answer integration was evaluated. All sixty original reference records
and the sealed025 comparator remain retained without replacement.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Retain bounded source investigation | Current quotations, maps and authored scope dossier retained | See actual stage receipts | Discovery completeness, governing scope and implicit language | Independent finite cases, implemented-method review and actual downstream effects | Automatic recall, legal application or whole-build completion |

An omission shared by the source reading and its dossier remains a possible
explanation. Counts and identity checks cannot disprove it. The separately frozen
original-source cases and deliberate misses required by the plan must precede
parser evaluation. Local missing discovery remains an engineering gap; no
fundamental limitation of an external package has been established.
'''
    with (HERE / 'RESULT.md').open('x') as stream:
        stream.write(note)
    return {'status': 'PASS', 'original_task_complete': False, 'resources': result['resources']}


def recorded_prior():
    events = Authority(ROOT).events()
    assert next(e for e in reversed(events) if e.get('attempt') == rel(PRIOR))['kind'] == 'RECORD'
    attempts = [e['attempt'] for e in events
                if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 25 and len(set(attempts)) == 25
    return attempts


def probe():
    prior_check()
    recorded_prior()
    source, sections = source_view()
    ledger = read(LEDGER)
    assert len(ledger['records']) == 60
    modules = imported_sources()
    result = {'status': 'PASS', 'role': 'SOURCE_AND_ENVIRONMENT_IDENTITY_ONLY',
        'modules': modules, 'selected_contract_sha256': source['selected_contract_sha256'],
        'p2_sha256': source['p2_sha256'], 'candidate_characters': len(source['candidate_text']),
        'source_pieces': dict(Counter(p['kind'] for p in source['pieces'])),
        'assembly_copy_statuses': source['assembly_copy_statuses'],
        'section_numbers': [r['number'] for r in sections],
        'prior_outputs_sha256': sha(PRIOR / 'outputs.json'),
        'original_reference_records': len(ledger['records']),
        'production_changes': 0, 'ordinary_answers_run': 0, 'discovery_evaluated': False}
    save(PREP / 'identity-probe.json', result)
    return result


def propose():
    program = read(AUTH / 'program.json')
    assert program['revision'] == 284
    prior_check()
    attempts = recorded_prior()
    assert read(PREP / 'stages/probe/result.json')['status'] == 'PASS'
    assert (PREP / 'PRE-ADMISSION-REVIEW.md').is_file()
    bindings = {rel(p): sha(p) for p in PREP.rglob('*')
                if p.is_file() and '__pycache__' not in p.parts}
    bindings.update({name: sha(ROOT / name) for name in (*CODE, PLAN, METHOD)})
    bindings.update({rel(p): sha(p) for p in (PRIOR / 'outputs.json', LEDGER)})
    for module in read(PREP / 'identity-probe.json')['modules'].values():
        assert sha(ROOT / module['path']) == module['sha256'], 'Probed project helper changed'
        bindings[module['path']] = module['sha256']
    save(PREP / 'freeze.json', {'bindings': bindings})
    proposal = deepcopy(program)
    proposal['revision'] = 285
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [rel(PREP / 'freeze.json')]))
    task.update(dossier=PLAN, pre_admission_review=rel(PREP / 'PRE-ADMISSION-REVIEW.md'),
        reason='Investigate exact current selected definitions and scope before discovery implementation; retain all original references',
        definition_scope_investigation={'review': rel(PREP), 'comparator': rel(PRIOR),
            'no_production_change': True, 'parser_or_answer_evaluation': False,
            'additional_bounds': {'stage_seconds': 180, 'measured_seconds': 1800,
                'bytes_including_4MiB_reserve': 64 * 1024**2}})
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 26
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 285
    for row in routes['tasks']:
        if row['task'] == task['id']:
            row.update(dossier=PLAN, task_sha256=digest(task),
                next_action='Read all15 current selected sections and the preamble; retain raw-bound declarations/uses and scope alternatives; freeze independent cases before parser integration',
                stop_condition='26 cumulative admissions;180s stages;1800 additional measured seconds;64MiB including4MiB reserve;no unchanged retries')
    save(PREP / 'routes.json', routes)
    proposal['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN),
        rel(PREP / 'routes.json'): sha(PREP / 'routes.json'), rel(PREP / 'freeze.json'): sha(PREP / 'freeze.json')})
    review = {'baseline': digest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Preserve sealed025 and all60 original ledger records',
            'Compose current selected COPY maps; distinguish supplied transformations and separators',
            'Retain manually authored section readings, declarations, uses, alternatives and known misses'],
        'skeptical_audit': {'verdict': 'PASS', 'review': rel(PREP / 'PRE-ADMISSION-REVIEW.md'),
            'wrong_historical_baseline_rejected': True, 'counts_are_not_recall': True},
        'evidence_contract': {'primary': 'Current source/map identity and source-authored section/declaration/use/scope dossier',
            'promotion_veto': ['Incorrect quotation or source map', 'Omitted required section reading', 'Erased original ledger record'],
            'continuation_veto': ['Corrupted sealed input', 'Frozen drift', 'Exhausted reviewed resources'],
            'explanatory_only': ['Term counts', 'Map counts', 'Elapsed time'],
            'not_concluded': ['Parser recall', 'Governing legal scope', 'Ordinary-answer integration', 'Original task/build completion']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 25, 'new_maximum': 26,
            'retained_attempts': attempts,
            'reason': 'Statutory integration retained; original definitions remain, and baseline inspection exposed a changed selected definition',
            'next_discriminating_check': 'Whole current selected source reading with exact raw-copy and supplied-text distinctions',
            'stop_condition': '180s stages;1800 explicitly additional measured seconds;64MiB including4MiB reserve;no unchanged retries',
            'same_scope_authorization': 'User requests refreshed master and continued general build with internal supported-behavior proof'},
        'resources_before_admission': costs(), 'old_costs_and_admissions_retained': True,
        'original_obligations_preserved': True}
    save(PREP / 'proposal.json', proposal)
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 285, 'resources': costs()}


def main():
    assert len(sys.argv) == 2
    label = sys.argv[1]
    assert label in (*PREPARATION, *STAGES), 'Unknown investigation stage'
    preparation = label in PREPARATION
    folder = (PREP if preparation else HERE) / 'stages' / label
    assert not (folder / 'started.json').exists(), 'Unchanged stage retry refused'
    if label == 'probe':
        program = read(AUTH / 'program.json')
        assert program['revision'] == 284
        prior = read(PRIOR / 'result.json')
        save(PREP / 'accounting-start.json', {'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
            'program_bytes': (AUTH / 'program.json').stat().st_size,
            'prior_statutory_resources': prior['resources'], 'prior_result_sha256': sha(PRIOR / 'result.json')})
    costs()
    dependencies = {'probe': (), 'propose': ('probe',), 'snapshot': ('propose',),
                    'inventory': ('snapshot',), 'reconcile': ('inventory',), 'seal': ('reconcile',)}
    for dependency in dependencies[label]:
        base = PREP if dependency in PREPARATION else HERE
        assert read(base / 'stages' / dependency / 'result.json')['status'] == 'PASS', dependency
    save(folder / 'started.json', {'command': ['.venv/bin/python', '-m',
        'scripts.prospectus_definition_scope_investigation', label],
        'started_at': datetime.now(timezone.utc).isoformat(), 'stage_seconds': 180})
    began = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Definition investigation stage bound')))
    signal.alarm(180)
    try:
        if not preparation:
            frozen()
        result = {'probe': probe, 'propose': propose, 'snapshot': snapshot,
                  'inventory': inventory, 'reconcile': reconcile, 'seal': seal}[label]()
        if not preparation:
            frozen()
        costs(time.monotonic() - began)
        result['wall_seconds'] = time.monotonic() - began
        save(folder / 'result.json', result)
        if label == 'seal':
            save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*')
                if p.is_file() and '__pycache__' not in p.parts})
        print(json.dumps(result, ensure_ascii=False))
    except BaseException as exc:
        save(folder / 'failure.json', {'type': type(exc).__name__, 'message': str(exc),
            'wall_seconds': time.monotonic() - began})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
