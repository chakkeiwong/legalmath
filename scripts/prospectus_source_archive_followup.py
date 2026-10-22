"""Bounded distinct historical-source acquisition under prospectus authority."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
from legalmath.prospectus.execution_authority import Authority, REL, read, write, file_hash, digest

PLAN = 'docs/plans/prospectus-source-authority-archive-2026-10-18.md'
SCRIPT = 'scripts/prospectus_source_archive_followup.py'
REVIEW = REL + '/reviews/source-archive-followup-264'
ATTEMPT = REL + '/attempts/source-authority/attempt-006'
PROPOSAL = REL + '/proposals/source-archive-followup-264.json'
ROUTES = REL + '/closure-routes-2026-10-18-source-archive-followup-264.json'
ORIGINAL = REL + '/attempts/source-authority/attempt-001'
URLS = {
    '2008': 'https://arquivo.pt/textsearch?versionHistory=www.bes.pt%2FRelatorioseContas%2F2008_Relatorios_Contas.pdf&maxItems=50',
    '2009': 'https://arquivo.pt/textsearch?versionHistory=www.bes.pt%2FRelatorioseContas%2F2009_Relatorio_Gestao.pdf&maxItems=50',
}
BOUNDS = {'seconds': 240, 'bytes': 64 * 1024**2, 'reserve_bytes': 2 * 1024**2,
          'metadata_requests': 2, 'metadata_seconds': 20, 'metadata_bytes': 2 * 1024**2,
          'content_requests': 2, 'content_seconds': 45, 'content_bytes': 10 * 1024**2}


def require(value, message):
    if not value: raise ValueError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def prepare():
    tick = time.monotonic(); auth = Authority(ROOT); old, tasks, _ = auth.spec()
    require(old['revision'] == 263, 'Wrong archive program baseline')
    reasoning = next(e for e in reversed(auth.events()) if e.get('task') == 'reasoning-corpus')
    require(reasoning['kind'] == 'ACCEPT', 'Finish reasoning repair before source continuation')
    task = tasks['source-authority']; folder = ROOT / REVIEW; folder.mkdir(parents=True, exist_ok=False)
    inventory = read(ROOT / ORIGINAL / 'edition-inventory.json')
    targets = [r for r in inventory['editions'] if r['id'] in {'bes-2008-pt', 'bes-2009-pt'}]
    require(len(targets) == 2, 'Exact original editions required')
    inputs = set(task['inputs']) | {PLAN, SCRIPT, ORIGINAL + '/edition-inventory.json', ORIGINAL + '/archive-result.json'}
    for row in targets:
        for key in ('source', 'receipt'):
            require(file_hash(ROOT / row[key]) == row[key + '_sha256'], 'Original issuer evidence changed')
            inputs.add(row[key])
    prior_urls = {r['url'] for r in read(ROOT / ORIGINAL / 'archive-result.json')['requests']}
    require(not set(URLS.values()) & prior_urls, 'Repeated historical query')
    admissions = [e['attempt'] for e in auth.events() if e['kind'] == 'ADMIT' and e['budget_key'] == task['budget_key']]
    require(len(admissions) == old['budgets'][task['budget_key']]['maximum_new_attempts'] == 5, 'Wrong source admission history')
    write(folder / 'targets.json', {'urls': URLS, 'editions': targets, 'prior_urls': sorted(prior_urls)}, exclusive=True)
    frozen = {n: file_hash(ROOT / n) for n in sorted(inputs)}
    write(folder / 'frozen.json', frozen, exclusive=True)
    new = deepcopy(old); new['revision'] = 264
    current = next(t for t in new['tasks'] if t['id'] == 'source-authority')
    current.update(dossier=PLAN, priority=-10,
        reason='Inspect distinct public2008/2009 report version histories; preserve unknown publication/authenticity and exact issuer bytes',
        archive_followup={'version': 'bounded-source-archive.v1', 'review': REVIEW, 'bounds': BOUNDS})
    current['inputs'] = sorted(inputs | {REVIEW + '/targets.json', REVIEW + '/frozen.json', REVIEW + '/preparation.json'})
    new['budgets'][task['budget_key']]['maximum_new_attempts'] = 6
    routes = read(ROOT / old['continuation_review']['routes']); routes['baseline_revision'] = 264
    for row in routes['tasks']:
        if row['task'] == 'reasoning-corpus':
            row.update(mode='accepted', remaining='Repaired012 finite engineering evidence accepted; interpretation remains in substantive tasks.',
                next_action='Preserve accepted012; revalidate only if its frozen method/input changes.')
        if row['task'] == 'source-authority':
            row.update(task_sha256=digest(current), dossier=PLAN, phase=0, mode='local',
                remaining=current['reason'], next_action='Execute two bounded exact archive requests, inspect actual metadata, preserve source unknowns and refine consumer work.',
                acceptance='Exact source chain and correctly qualified real consumer effect; unavailable records remain unknown, never proof of absence.',
                external_inputs=[], stop_condition=json.dumps(BOUNDS, sort_keys=True))
    write(ROOT / ROUTES, routes, exclusive=True)
    new['continuation_review'].update(plan=PLAN, routes=ROUTES)
    for name in (PLAN, SCRIPT, ROUTES): new['continuation_review']['bindings'][name] = file_hash(ROOT / name)
    write(folder / 'preparation.json', {'seconds': time.monotonic() - tick, 'prior_admissions': admissions,
        'repaired_reasoning_accept_event': reasoning['sha256'], 'original_editions_verified': len(targets),
        'historical_unmeasured_time': 'UNKNOWN'}, exclusive=True)
    review = {'baseline': digest(old), 'changes': current['reason'], 'scope_unchanged': True, 'budget_unchanged': False,
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN, 'new_information': 'Distinct original2008/2009 URLs, not repeated2010 query',
            'source_limits': 'Archive capture does not imply publication/legal availability or independent authenticity'},
        'evidence_contract': {'question': 'Earlier archival evidence for exact original2008/2009 report bytes',
            'baseline': ORIGINAL + '/edition-inventory.json', 'primary': 'Original receipts, actual metadata/content and correctly bounded consumer statement',
            'veto': 'Invented metadata, wrong source edition, promoted publication claim, corruption or exceeded ceiling',
            'explanatory': ['counts', 'timing'], 'not_concluded': ['source authenticity', 'legal truth', 'historical absence', 'whole task']},
        'budget_revision': {'budget_key': task['budget_key'], 'previous_maximum': 5, 'new_maximum': 6,
            'retained_attempts': admissions, 'reason': current['reason'],
            'next_discriminating_check': 'Exact public version histories of two unqueried retained issuer report URLs',
            'stop_condition': BOUNDS, 'same_scope_authorization': 'User-directed source-evidence build with available public sources'}}
    auth.validate_program(new); write(ROOT / PROPOSAL, new, exclusive=True)
    write(folder / 'review.json', review, exclusive=True)
    print(json.dumps({'prepared_revision': 264, 'queries': list(URLS), 'seconds': time.monotonic() - tick}))


def admitted():
    auth = Authority(ROOT); program, tasks, _ = auth.spec(); task = tasks['source-authority']
    attempt = ROOT / ATTEMPT; admission = read(attempt / 'admission.json')
    require(admission['task_spec'] == task and admission['binding'] == auth.binding(task)
        and admission['program_sha256'] == digest(program), 'Source admission drift')
    latest = next(e for e in reversed(auth.events()) if e.get('task') == task['id'])
    require(latest['kind'] == 'ADMIT' and latest['attempt'] == ATTEMPT, 'Source admission inactive')
    require(not (attempt / 'outputs.json').exists(), 'Source attempt already sealed')
    for name, expected in read(ROOT / REVIEW / 'frozen.json').items():
        require(file_hash(ROOT / name) == expected, 'Source method/input changed')
    return attempt, admission


def start(key):
    attempt, _ = admitted(); folder = attempt / ('metadata-' + key); folder.mkdir(parents=True, exist_ok=False)
    argv = ['curl', '--silent', '--show-error', '--location', '--proto', '=https', '--proto-redir', '=https',
            '--connect-timeout', '5', '--max-time', '20', '--max-filesize', '2097152', '--retry', '0',
            '--dump-header', str(folder / 'headers.txt'), '--output', str(folder / 'body.json'),
            '--write-out', '%{http_code}', URLS[key]]
    write(folder / 'started.json', {'at': now(), 'argv': argv, 'network_attempts_allowed': 1}, exclusive=True)
    print(json.dumps({'key': key, 'argv': argv}))


def finish(key, exit_code, http_status):
    attempt, _ = admitted(); folder = attempt / ('metadata-' + key); started = read(folder / 'started.json')
    size = (folder / 'body.json').stat().st_size if (folder / 'body.json').exists() else 0
    require(size <= BOUNDS['metadata_bytes'], 'Metadata response ceiling')
    value = None
    if exit_code == 0 and http_status == 200:
        value = read(folder / 'body.json')
    rows = value.get('response_items', []) if isinstance(value, dict) else []
    require(isinstance(rows, list), 'Invalid archive response records')
    actual = []
    original = next(r for r in read(ROOT / REVIEW / 'targets.json')['editions'] if r['id'] == 'bes-' + key + '-pt')
    for i, row in enumerate(rows):
        url = row.get('originalURL')
        expected = urlsplit(original['url'])
        parsed = urlsplit(url) if isinstance(url, str) else None
        eligible = bool(parsed and parsed.hostname and parsed.hostname.removeprefix('www.') == expected.hostname.removeprefix('www.')
            and parsed.path == expected.path and parsed.query == expected.query
            and row.get('mimeType') == 'application/pdf' and row.get('statusCode') == 200)
        actual.append({'index': i, 'eligible_metadata': eligible, 'metadata': row})
    result = {'key': key, 'started': started['at'], 'finished': now(), 'curl_exit_code': exit_code,
        'http_status': http_status, 'bytes': size, 'original_source': original['source'],
        'original_sha256': original['source_sha256'], 'records': actual,
        'publication_date': 'UNKNOWN', 'edition_authenticity': 'UNKNOWN',
        'historical_absence_established': False,
        'files': {p.name: file_hash(p) for p in folder.iterdir() if p.is_file()}}
    write(folder / 'result.json', result, exclusive=True)
    print(json.dumps({'key': key, 'curl_exit_code': exit_code, 'http_status': http_status,
        'records': len(rows), 'eligible': sum(r['eligible_metadata'] for r in actual)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'start', 'finish'))
    parser.add_argument('--key', choices=tuple(URLS))
    parser.add_argument('--exit-code', type=int); parser.add_argument('--http-status', type=int)
    args = parser.parse_args()
    if args.action == 'prepare': prepare()
    elif args.action == 'start': start(args.key)
    else: finish(args.key, args.exit_code, args.http_status)


if __name__ == '__main__':
    main()
