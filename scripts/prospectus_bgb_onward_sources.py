"""Bounded primary-source continuation after the sealed spelling repair."""
from copy import deepcopy
from datetime import datetime, timezone
from html import unescape
import json
import os
import re
import signal
import sys
import time

from scripts import prospectus_purpose_use_spelling_repair as prior
from scripts.prospectus_statutory_sources_accounted import SourceHTML
from legalmath.prospectus.execution_authority import Authority, CODE, digest

ROOT, AUTH = prior.ROOT, prior.AUTH
PREP = AUTH / 'reviews/bgb-onward-sources-353'
HERE = AUTH / 'attempts/basf-references/attempt-092'
PLAN = 'docs/plans/prospectus-bgb-onward-sources-2026-10-20.md'
METHOD = 'scripts/prospectus_bgb_onward_sources.py'
SECTIONS = ('206', '210', '211')
BASE = AUTH / 'attempts/basf-references/attempt-023'
read, save, sha, rel = prior.read, prior.save, prior.sha, prior.rel


def decode_source(raw, section):
    assert 0 < len(raw) <= 1024**2
    match = re.search(br'charset\s*=\s*["\x27]?([A-Za-z0-9_-]+)', raw[:8192], re.I)
    assert match, 'Actual response charset required'
    charset = match[1].decode('ascii')
    html = raw.decode(charset, errors='strict')
    title = re.search(r'<title>(.*?)</title>', html, re.I | re.S)
    assert title and re.match(r'\s*§\s*' + section + r'\s+BGB\b', unescape(title[1])), 'Wrong official section'
    assert html.rstrip().lower().endswith('</html>'), 'Truncated official HTML'
    parser = SourceHTML()
    parser.feed(html)
    parser.close()
    # Match the retained023 extractor; offsets refer to this retained text,
    # while the original bytes and their hash remain separately available.
    lines = [' '.join(line.split()) for line in ''.join(parser.text).splitlines()]
    text = '\n'.join(line for line in lines if line) + '\n'
    assert re.search(r'(?m)^§\s*' + section + r'(?:[ \t]|$)', text) and '\ufffd' not in text
    return charset, text, parser.links


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    base = start['prior']
    seconds = base['combined_measured_seconds'] + extra
    for folder in (PREP, HERE):
        for pattern in ('stages/*/result.json', 'stages/*/failure.json'):
            seconds += sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    seconds += sum(read(p)['tool_wall_seconds'] for p in HERE.glob('requests/*/receipt.json'))
    paths = {p for folder in (PREP, HERE) for p in folder.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / p for p in (PLAN, METHOD))
    paths.add(AUTH / 'revisions/0353.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = base['combined_bytes'] + sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    charge = base['conservative_extra_seconds'] + 120
    assert seconds + charge < prior.SECONDS_BOUND and size < prior.BYTES_BOUND - 4 * 1024**2
    assert seconds - base['combined_measured_seconds'] < 180, 'New source-command bound'
    assert size - base['combined_bytes'] < 48 * 1024**2, 'New source-storage bound'
    assert len(list(HERE.glob('requests/*/started.json'))) <= 3, 'Three reviewed GETs only'
    return {'combined_measured_seconds': seconds, 'conservative_extra_seconds': charge,
        'combined_accounted_seconds': seconds + charge, 'combined_bytes': size,
        'seconds_bound': prior.SECONDS_BOUND, 'bytes_bound_with_4MiB_reserve': prior.BYTES_BOUND,
        'new_GETs': len(list(HERE.glob('requests/*/started.json'))), 'maximum_new_GETs': 3,
        'prior_costs_reset': False, 'historical_acquisition_allowances_reset': False,
        'unmeasured_authoring_and_older_time': 'UNKNOWN; conservative charge is not a measurement'}


def prepare():
    program = read(AUTH / 'program.json')
    assert program['revision'] == 352
    events = Authority(ROOT).events()
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 91
    assert [e['kind'] for e in events if e.get('attempt') == rel(prior.HERE)][-1] == 'RECORD'
    assert read(prior.HERE / 'result.json')['status'] == 'PASS'
    for name, checksum in read(prior.HERE / 'outputs.json').items():
        assert sha(prior.HERE / name) == checksum, name
    save(PREP / 'accounting-start.json', {'prior': prior.costs(),
        'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
        'program_bytes': (AUTH / 'program.json').stat().st_size})
    names = [*CODE, PLAN, METHOD, prior.METHOD, rel(PREP / 'preparation-diagnostic.json'),
        'scripts/prospectus_statutory_sources_accounted.py',
        'src/legalmath/prospectus/successor/statutory_references.py',
        'src/legalmath/prospectus/successor/statutory_references_spec.json',
        rel(prior.HERE / 'outputs.json'), rel(prior.HERE / 'ordinary-answer.json.gz')]
    for section in ('801', '802'):
        names.extend([rel(BASE / f'requests/bgb-{section}/body'),
                      rel(BASE / f'local/extract-bgb-{section}/text.txt')])
    bindings = {name: sha(ROOT / name) for name in names}
    production = sorted(rel(p) for p in (ROOT / 'src/legalmath').rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    bindings.update({name: sha(ROOT / name) for name in production})
    bindings[rel(PREP / 'accounting-start.json')] = sha(PREP / 'accounting-start.json')
    save(PREP / 'freeze.json', {'bindings': bindings, 'production_changes': False,
        'production_paths': production,
        'current_sources_are_historical_editions': False})
    proposal = deepcopy(program)
    proposal['revision'] = 353
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=PLAN,
        reason='Return to historical/onward source gap: inspect complete BGB206,210,211 before legal integration',
        bgb_onward_source_review={'review': rel(PREP), 'original_task_complete': False,
            'production_changes': False, 'maximum_new_GETs': 3,
            'accounted_seconds_bound': prior.SECONDS_BOUND, 'bytes_with_reserve': prior.BYTES_BOUND})
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [rel(PREP / 'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 92
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 353
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=digest(task),
                next_action='Retain complete BGB onward readings and exceptions; review actual source-to-answer integration next',
                stop_condition='92 admissions;three new direct GETs;180 command seconds/48MiB new;25200 accounted seconds/3712MiB cumulative')
    save(PREP / 'routes.json', routes)
    proposal['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN),
        rel(PREP / 'routes.json'): sha(PREP / 'routes.json'), rel(PREP / 'freeze.json'): sha(PREP / 'freeze.json')})
    snapshot = costs()
    forecast = {'seconds': snapshot['combined_accounted_seconds'] + 180,
        'bytes': snapshot['combined_bytes'] + 48 * 1024**2, 'estimate_only': True}
    assert forecast['seconds'] < prior.SECONDS_BOUND and forecast['bytes'] < prior.BYTES_BOUND - 4 * 1024**2
    review = {'baseline': digest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Refresh all seven source-gap classes', 'Read missing BGB802 onward conditions before schema design'],
        'skeptical_audit': {'verdict': 'PASS', 'review': PLAN, 'forecast': forecast},
        'evidence_contract': {'primary': 'Correct complete primary sections, exact quotations, conditions and exceptions',
            'promotion_veto': ['Wrong/incomplete source', 'Decoding loss', 'Missing exception', 'False historical/application closure'],
            'continuation_veto': ['Corrupt baseline', 'Frozen drift', 'Cumulative exhaustion'],
            'explanatory_only': ['Counts', 'Runtime'],
            'not_concluded': ['Downstream integration', 'Historical edition', 'Actual deadline', 'Entitlement', 'Whole build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 91, 'new_maximum': 92,
            'retained_attempts': attempts, 'reason': 'Complete missing primary onward readings for original H28',
            'next_discriminating_check': 'Full206/210/211 conditions and exceptions against literal802 antecedent',
            'stop_condition': 'Three GETs;180 seconds/48MiB new;unchanged25200 accounted seconds/3712MiB cumulative',
            'same_scope_authorization': 'User requests refreshed master and continued internally checked general build'},
        'acquisition_revision': {'added_BGB_onward_GETs': 3, 'old_allowances_reset': False,
            'schvg_route_remains_exhausted': True}, 'resource_accounting': snapshot}
    save(PREP / 'proposal.json', proposal)
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 353, 'forecast': forecast}


def frozen():
    admission = read(HERE / 'admission.json')
    assert digest(read(AUTH / 'program.json')) == admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec']) == admission['binding']
    freeze = read(PREP / 'freeze.json')
    actual = sorted(rel(p) for p in (ROOT / 'src/legalmath').rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    assert actual == freeze['production_paths'], 'Source preparation cannot change the production tree'
    for name, checksum in freeze['bindings'].items():
        assert sha(ROOT / name) == checksum, name


def local():
    text = (BASE / 'local/extract-bgb-802/text.txt').read_text()
    _, reproduced, _ = decode_source((BASE / 'requests/bgb-802/body').read_bytes(), '802')
    assert reproduced == text, 'Draft parser must reproduce the complete retained802 text'
    quote = 'Auf diese Frist finden die Vorschriften der §§ 206, 210, 211 entsprechende Anwendung.'
    assert text.count(quote) == 1 and 'sechs Monate' in text
    save(HERE / 'referring-source.json', {'path': rel(BASE / 'local/extract-bgb-802/text.txt'),
        'sha256': sha(BASE / 'local/extract-bgb-802/text.txt'), 'start': text.index(quote),
        'end': text.index(quote) + len(quote), 'quote': quote, 'complete_text': text,
        'historical_edition_proved': False, 'application_proved': False})
    return {'status': 'PASS', 'retained_referring_provision': 'BGB802', 'onward_sources': list(SECTIONS),
        'parser_reproduces_complete_retained802': True}


def start(section):
    assert section in SECTIONS and read(HERE / 'stages/local/result.json')['status'] == 'PASS'
    for preceding in SECTIONS[:SECTIONS.index(section)]:
        assert read(HERE / 'stages' / f'finish-{preceding}' / 'result.json')['status'] == 'PASS'
    folder = HERE / 'requests' / section
    folder.mkdir(parents=True, exist_ok=False)
    url = f'https://www.gesetze-im-internet.de/bgb/__{section}.html'
    command = ['curl', '--silent', '--show-error', '--proto', '=https', '--max-time', '20',
        '--connect-timeout', '8', '--max-filesize', '1048576', '--dump-header', str(folder / 'headers'),
        '--output', str(folder / 'body'), '--stderr', str(folder / 'stderr'), '--write-out', '%{http_code}', url]
    save(folder / 'started.json', {'command': command, 'url': url,
        'started_at': datetime.now(timezone.utc).isoformat(), 'redirects': False, 'retries': 0})
    return {'status': 'PASS', 'section': section, 'command': command, 'execution_required': True}


def finish(section):
    folder = HERE / 'requests' / section
    assert read(HERE / 'stages' / f'start-{section}' / 'result.json')['status'] == 'PASS'
    started = read(folder / 'started.json')
    code, wall = int(sys.argv[2]), float(sys.argv[3])
    assert 0 <= wall <= 25
    headers = (folder / 'headers').read_text(errors='strict') if (folder / 'headers').exists() else ''
    statuses = re.findall(r'(?m)^HTTP/[^ ]+ (\d{3})', headers)
    http = int(statuses[-1]) if statuses else None
    retained = code == 0 and http == 200 and (folder / 'body').is_file()
    receipt = {'status': 'RESPONSE_RETAINED' if retained else 'UNAVAILABLE_RESPONSE_RETAINED',
        'url': started['url'], 'effective_url': started['url'], 'redirects': False,
        'exit_code': code, 'http_code': http, 'tool_wall_seconds': wall,
        'finished_at': datetime.now(timezone.utc).isoformat(),
        'files': {p.name: sha(p) for p in folder.iterdir() if p.is_file()},
        'historical_application_proved': False}
    save(folder / 'receipt.json', receipt)
    return {'status': 'PASS', 'section': section, 'source_status': receipt['status'], 'http_code': http}


def extract():
    sources = []
    for section in SECTIONS:
        assert read(HERE / 'stages' / f'finish-{section}' / 'result.json')['status'] == 'PASS'
        folder = HERE / 'requests' / section
        receipt = read(folder / 'receipt.json')
        for name, checksum in receipt['files'].items():
            assert sha(folder / name) == checksum, name
        if receipt['status'] != 'RESPONSE_RETAINED':
            continue
        raw = (folder / 'body').read_bytes()
        charset, text, links = decode_source(raw, section)
        (folder / 'text.txt').write_text(text)
        save(folder / 'extraction.json', {'method': 'SourceHTML;declared charset;decode title entities;023 line whitespace normalization',
            'charset': charset, 'raw_sha256': sha(folder / 'body'), 'text_sha256': sha(folder / 'text.txt'),
            'links': links, 'historical_edition_proved': False})
        sources.append({'section': section, 'characters': len(text), 'path': rel(folder / 'text.txt')})
    return {'status': 'PASS', 'sources': sources, 'substantive_source_review_pending': True}


def seal():
    extraction = read(HERE / 'stages/extract/result.json')
    assert extraction['status'] == 'PASS'
    assert [row['section'] for row in extraction['sources']] == list(SECTIONS), 'All three complete sources required'
    note = HERE / 'SOURCE-REVIEW.md'
    assert note.is_file() and note.stat().st_size > 1000
    findings = read(HERE / 'source-findings.json')
    assert findings['production_changed'] is False and findings['historical_application_proved'] is False
    assert [row['section'] for row in findings['readings']] == list(SECTIONS), 'One reviewed reading per section required'
    assert findings['antecedent_review']['historical_or_actual_application_proved'] is False
    assert findings['antecedent_review']['literal_source'] == rel(BASE / 'local/extract-bgb-802/text.txt')
    assert findings['antecedent_review']['local_interpretation']
    for row in findings['readings']:
        assert row['text_path'] == rel(HERE / 'requests' / row['section'] / 'text.txt')
        text = (ROOT / row['text_path']).read_text()
        assert sha(ROOT / row['text_path']) == row['text_sha256']
        assert row['excerpts'] and row['conditions'] and isinstance(row['exceptions'], list)
        assert row['literal_law'] and row['local_corresponding_application'] and row['unresolved']
        for part in row['excerpts']:
            assert 0 <= part['start'] < part['end'] <= len(text)
            assert text[part['start']:part['end']] == part['quote']
    result = {'status': 'PASS', 'task': 'basf-references', 'original_task_complete': False,
        'result_kind': 'BGB_ONWARD_SOURCE_READINGS', 'readings': len(findings['readings']),
        'production_changed': False, 'downstream_integration_complete': False,
        'historical_application_proved': False, 'resources': costs(),
        'next_action': 'Review source-to-answer integration of actual onward conditions and scope; keep historical applicability open'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(p)['command'] for p in sorted(HERE.glob('stages/*/started.json'))]
            + [read(p)['command'] for p in sorted(HERE.glob('requests/*/started.json'))],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU;GPU intentionally hidden',
        'seeds': 'N/A deterministic source review', 'data_version': sha(prior.PRODUCTS),
        'wall_time': costs(), 'plan': PLAN, 'result': rel(HERE / 'result.json'),
        'source_review': rel(note), 'source_review_sha256': sha(note)})
    return result


def main():
    stage = sys.argv[1]
    assert stage in {'prepare', 'local', 'extract', 'seal',
        *(f'{verb}-{section}' for verb in ('start', 'finish') for section in SECTIONS)}
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    folder = (PREP if stage == 'prepare' else HERE) / 'stages' / stage
    assert not (folder / 'started.json').exists(), 'Unchanged retry refused'
    if stage != 'prepare':
        frozen()
        costs()
    save(folder / 'started.json', {'command': ['.venv/bin/python', '-m', 'scripts.prospectus_bgb_onward_sources', *sys.argv[1:]],
        'started_at': datetime.now(timezone.utc).isoformat()})
    started = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('90second local stage bound')))
    signal.alarm(90)
    try:
        if '-' in stage:
            verb, section = stage.split('-', 1)
            result = globals()[verb](section)
        else:
            result = globals()[stage]()
        if stage != 'prepare':
            frozen()
        result['wall_seconds'] = time.monotonic() - started
        costs(result['wall_seconds'])
        save(folder / 'result.json', result)
        if stage == 'seal':
            save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as error:
        save(folder / 'failure.json', {'type': type(error).__name__, 'message': str(error),
            'wall_seconds': time.monotonic() - started})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
