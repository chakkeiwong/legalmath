"""Freeze independently specified current-role projection cases."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import signal
import time
from scripts import prospectus_source_coverage as audit
from legalmath.prospectus.execution_authority import Authority

ROOT, AUTH = audit.ROOT, audit.AUTH
PREP = AUTH / 'reviews/definition-roles-327'
PLAN = 'docs/plans/prospectus-definition-current-roles-2026-10-19.md'
METHOD = 'scripts/prospectus_definition_role_cases.py'


def cases():
    source = {'unit': 'heading', 'document': 'source', 'source_sha256': 'a' * 64,
              'start': 0, 'end': 4, 'quote': 'Name'}
    raw = {'id': 'heading', 'document': 'source', 'source_sha256': 'a' * 64, 'raw': 'Name'}
    use = {'unit': 'heading', 'start': 0, 'end': 4, 'source': source, 'role': 'UNKNOWN'}
    report = {'source_pieces': [{'start': 0, 'end': 4, 'text': 'Name', 'kind': 'EXACT_SOURCE_COPY',
                                'raw_binding': source, 'assembly_uses': [use]}],
              'records': [{'id': 'term', 'status': 'UNRESOLVED'}], 'scope_admitted': False}
    assembly = {'units': [{'unit': 'heading', 'text': 'Name', 'role': 'HEADER',
                           'character_map': [{'start': 0, 'end': 4, 'source': source, 'operation': 'Text'}]}]}
    base = {'report': report, 'raw_units': [raw], 'assembly': assembly,
            'approved': {'heading': {'before': 'UNKNOWN', 'after': 'HEADER'}}}
    entries = [{'id': 'reviewed-heading', 'request': deepcopy(base), 'refuse': False,
                'changes': [{'piece': 0, 'use': 0, 'unit': 'heading', 'before': 'UNKNOWN', 'after': 'HEADER'}]}]
    unchanged = deepcopy(base)
    unchanged['report']['source_pieces'][0]['assembly_uses'][0]['role'] = 'HEADER'
    entries.append({'id': 'already-current', 'request': unchanged, 'refuse': False, 'changes': []})
    for kind in ('no-authority', 'wrong-before', 'wrong-current-role', 'altered-raw', 'altered-use-text',
                 'moved-use-offset', 'wrong-map', 'duplicate-unit'):
        request = deepcopy(base)
        if kind == 'no-authority': request['approved'] = {}
        elif kind == 'wrong-before': request['approved']['heading']['before'] = 'OPERATIVE'
        elif kind == 'wrong-current-role': request['assembly']['units'][0]['role'] = 'OPERATIVE'
        elif kind == 'altered-raw': request['raw_units'][0]['raw'] = 'Other'
        elif kind == 'altered-use-text': request['assembly']['units'][0]['text'] = 'Other'
        elif kind == 'moved-use-offset': request['report']['source_pieces'][0]['assembly_uses'][0]['start'] = 1
        elif kind == 'wrong-map': request['assembly']['units'][0]['character_map'][0]['source']['start'] = 1
        else: request['assembly']['units'].append(deepcopy(request['assembly']['units'][0]))
        entries.append({'id': kind, 'request': request, 'refuse': True})
    supplied = deepcopy(base)
    supplied['report']['source_pieces'].append({'start': 4, 'end': 5, 'text': '!',
        'kind': 'SUPPLIED_OR_TRANSFORMED', 'raw_binding': None, 'assembly_uses': []})
    entries.append({'id': 'supplied-keeps-no-raw-quote', 'request': supplied, 'refuse': False,
                    'changes': entries[0]['changes']})
    return entries


def main():
    assert not (PREP / 'case-preparation-start.json').exists(), 'Unchanged retry refused'
    audit.save(PREP / 'case-preparation-start.json', {'command': ['.venv/bin/python', '-m', 'scripts.prospectus_definition_role_cases'],
              'started_at': datetime.now(timezone.utc).isoformat(), 'seconds_bound': 30})
    start = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Role case preparation bound')))
    signal.alarm(30)
    try:
        assert any(e['kind'] == 'RECORD' and e.get('attempt') == audit.rel(audit.HERE) for e in Authority(ROOT).events())
        for name, checksum in audit.read(audit.HERE / 'outputs.json').items():
            assert audit.sha(audit.HERE / name) == checksum
        coverage = audit.read(audit.HERE / 'coverage.json')
        expected = coverage['source_accounting']['retained_vs_current_roles']
        assert len(expected) == 48 and len({r['unit'] for r in expected}) == 44
        assert all(r['retained_role'] == 'UNKNOWN' and r['current_role'] == 'HEADER' for r in expected)
        audit.save(PREP / 'cases.json', {'cases': cases(), 'expected_original_changes': expected,
            'source_audit': audit.rel(audit.HERE / 'coverage.json'),
            'source_audit_sha256': audit.sha(audit.HERE / 'coverage.json')})
        audit.save(PREP / 'cases-freeze.json', {'cases_sha256': audit.sha(PREP / 'cases.json'),
            'method': METHOD, 'method_sha256': audit.sha(ROOT / METHOD), 'plan': PLAN,
            'plan_sha256': audit.sha(ROOT / PLAN), 'frozen_at': datetime.now(timezone.utc).isoformat()})
        result = {'status': 'PASS', 'cases': len(cases()), 'expected_role_changes': len(expected),
                  'wall_seconds': time.monotonic() - start}
        audit.save(PREP / 'case-preparation.json', result)
        print(json.dumps(result))
    except BaseException as error:
        audit.save(PREP / 'case-preparation-failure.json', {'type': type(error).__name__,
                   'message': str(error), 'wall_seconds': time.monotonic() - start})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
