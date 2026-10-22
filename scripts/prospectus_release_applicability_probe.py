"""Retain actual release-category counterexamples with honest source bindings."""
from copy import deepcopy
import gzip
import json
import os
from pathlib import Path
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.localresources/prospectus-preparation/release-applicability/recovery'
sys.path[:0] = [str(ROOT / 'src'), str(ROOT), str(ROOT / 'tests/prospectus_successor')]
sys.dont_write_bytecode = True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.prospectus.successor import report_scope, service
from scripts.prospectus_h1_current_acceptance import read, sha, require
from test_unaudited_release import fixture as fy_fixture, TEXT as FY, UNKNOWN
from test_q1_release import fixture as q1_fixture, TEXT as Q1
from test_report_scope import exact_span, products


def save(name, value):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
    if path.suffix == '.gz':
        raw = gzip.compress(raw, mtime=0)
    require(len(raw) < 16 * 1024**2, 'Probe output bound')
    with path.open('xb') as stream:
        stream.write(raw)


def main():
    tick = time.monotonic()
    require(not OUT.exists(), 'No unchanged retry')
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('60-second probe limit')))
    signal.alarm(60)
    rows, packets, originals = [], [], []
    for label, task, text, fixture in (
            ('fy2010', 'source-bes-dep-08', FY, fy_fixture),
            ('q12011', 'source-bes-dep-11', Q1, q1_fixture)):
        base = ROOT / 'docs/implementation/prospectus-execution-authority/attempts' / task
        original = base / 'attempt-002/release-reading.txt'
        require(original.read_text().strip() == text.strip(), 'Fixture differs from original retained reading')
        selected = read(base / 'attempt-001/selected-reading.json')
        scope = read(base / 'attempt-002/corrected-original-scope.json')
        direct = report_scope.explain(report_scope.admit(selected, scope))
        require(direct[0]['use_assessment']['unaudited_financial_release'] == 'SUPPLIED_SOURCE_DESCRIPTION', 'Original description missing')
        originals.append({'source': label, 'selected': selected, 'scope': scope, 'answer': direct,
                          'reading': {'path': str(original.relative_to(ROOT)), 'sha256': sha(original)}})
        variants = {
            'exact': text,
            'missing-eu': text.replace(' as implemented by the European Union', '', 1),
            'changed-date': text.replace('Lisbon, 31 January 2011' if label == 'fy2010' else 'Lisbon, 2 May 2011', 'Lisbon, 3 May 2011', 1),
            'prefix-commentary': 'Commentary quotes the following issuer release.\n' + text,
            'changed-assurance-word': text.replace('Unaudited', 'Audited', 1),
        }
        for variant, body in variants.items():
            folder = OUT / 'source-inputs' / label / variant
            folder.mkdir(parents=True)
            p1, p2, scope, retained = fixture(folder, body)
            for category in report_scope.PROFILES:
                supplied = deepcopy(scope)
                facts = supplied['reports'][0]['facts']
                facts['identity']['value'] = category
                for field, value in report_scope.PROFILES[category].items():
                    spans = facts[field].get('spans', [exact_span(retained, 'MATERIAL EVENT')])
                    facts[field] = {'status': 'SUPPLIED', 'value': value, 'spans': spans}
                if category == 'COMMITTEE_REPORT':
                    facts['assurance_level'] = deepcopy(UNKNOWN)
                for field in ('addressee', 'purpose', 'reliance_limits'):
                    facts[field] = {'status': 'SUPPLIED', 'spans': [exact_span(retained, 'MATERIAL EVENT')]}
                packet = {'source': label, 'variant': variant, 'category': category, 'P1': p1, 'P2': p2, 'scope': supplied}
                try:
                    answer = service.consume(products(p1, p2, supplied), ROOT, mode='current', include_artifacts=True)
                    packet['answer'] = answer
                    report = answer['source_reports'][0]
                    summary = {'refused': False, 'status': report['status'], 'use_assessment': report['use_assessment']}
                except ValueError as exc:
                    packet['error'] = str(exc)
                    summary = {'refused': True, 'reason': str(exc)}
                packet_path = f'packets/{label}-{variant}-{category}.json.gz'
                save(packet_path, packet)
                packets.append({'path': str((OUT / packet_path).relative_to(ROOT)),
                                'sha256': sha(OUT / packet_path)})
                rows.append({'source': label, 'variant': variant, 'category': category, **summary})
    false = [r for r in rows if not r['refused'] and r['category'] != 'UNAUDITED_FINANCIAL_RELEASE'
             and any(v == 'SUPPLIED_SOURCE_SUPPORT' for v in r['use_assessment'].values())]
    save('consumer-inputs.json.gz', packets)
    save('original-inputs.json.gz', originals)
    result = {'status': 'DEFECT_REPRODUCED' if false else 'NO_DEFECT_REPRODUCED', 'rows': rows,
              'false_support_cases': len(false), 'seconds': time.monotonic() - tick,
              'method': {'path': str(Path(__file__).relative_to(ROOT)), 'sha256': sha(__file__)},
              'source_variants_are_original_documents': False, 'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1'}
    save('probe.json', result)
    signal.alarm(0)
    print(json.dumps({'status': result['status'], 'false_support_cases': len(false), 'cases': len(rows), 'seconds': result['seconds']}), flush=True)


if __name__ == '__main__':
    started = time.monotonic()
    try:
        main()
    except Exception as error:
        save('failure.json', {'status': 'FAIL', 'error': repr(error),
                             'seconds': time.monotonic() - started})
        raise
