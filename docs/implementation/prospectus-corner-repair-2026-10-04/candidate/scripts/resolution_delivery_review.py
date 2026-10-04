"""Verify the completed round and bind its inspected editorial correction.

This offline review preserves all phase attempts. It makes no live requests,
changes no allowance, and does not create a new phase approval or legal verdict.
"""
from pathlib import Path
import hashlib
import json
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from legalmath.interpretation.assurance.workflow import EvidenceJournal
from legalmath.interpretation.assurance.diversity import save

OUT = ROOT / 'artifacts/interpretation/round14'
DOC = ROOT / 'docs/implementation/interpretation-round14'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    phases = read(OUT / 'phase-results.json')
    final = read(OUT / 'final-report.json')
    require(final['phases'] == phases, 'Final phase selection changed')
    require(set(phases) == {'R' + str(i) for i in range(8)}, 'Missing phase')
    journals = {}
    for name in ('execution-reviewed', 'live-reviewed/model', 'live-new-official/model'):
        directory = OUT / name
        binding = read(directory / 'journal.json')['value']['binding']
        report = EvidenceJournal(directory, binding['inputs'],
            maximum_actions=binding['maximum_actions'],
            maximum_per_issue=binding['maximum_per_issue'],
            deadline_seconds=binding['deadline_seconds']).report()
        require(all(a['status'] != 'RESERVED' for a in report['actions']), 'Unfinished action')
        journals[name] = {'sha256': sha(directory / 'journal.json'),
                          'actions': len(report['actions']), 'artifacts_verified': True}
    actions = read(OUT / 'execution-reviewed/journal.json')['value']['actions']
    for phase, selected in phases.items():
        action = actions[selected['receipt']['sequence']]
        manifest = selected['manifest']
        require(action['status'] == 'EXECUTED' and
                action['result_hash'] == selected['receipt']['result_hash'], 'Invalid phase receipt')
        require(read(OUT / 'execution-reviewed' / action['result_file']) == manifest,
                'Phase summary differs from immutable result')
        if 'result_path' in manifest:
            require(sha(ROOT / manifest['result_path']) == manifest['result_sha256'],
                    'Phase evidence changed: ' + phase)
    tested = phases['R6']['manifest']['inputs']['implementation']
    require(all(sha(ROOT / p) == h for p, h in tested.items()), 'Tested implementation changed')
    r7_changes = [p for p, h in phases['R7']['manifest']['inputs']['implementation'].items()
                  if sha(ROOT / p) != h]
    require(set(r7_changes) == {'scripts/resolution_documents.py', 'scripts/resolution_citations.py'},
            'Unexpected post-R7 change')
    suite = ET.parse(ROOT / phases['R6']['directory'] / '../tests.xml').getroot()
    tests = {k: sum(int(s.get(k, 0)) for s in suite.iter('testsuite'))
             for k in ('tests', 'failures', 'errors', 'skipped')}
    require(tests == phases['R6']['manifest']['tests'] and tests == {
        'tests': 765, 'failures': 0, 'errors': 0, 'skipped': 0}, 'Regression evidence differs')
    base = read(DOC / 'baseline.json')
    for path, expected in base['monograph'].items():
        if path.endswith('/06-ensemble.tex'):
            current = (ROOT / path).read_text().replace('\n\\input{chapters/06d-invariant-decisions}\n', '')
            require(current == (OUT / 'manuscript-baseline' / Path(path).name).read_text(),
                    'Existing ensemble content changed')
        else:
            require(sha(ROOT / path) == expected, 'Protected chapter changed: ' + path)
    ledger_path = ROOT / 'artifacts/interpretation/round7/live-allowance.json'
    ledger = read(ledger_path)
    require(ledger['maximum'] == 500 and len(ledger['calls']) == 466, 'Allowance changed')
    repair = read(DOC / 'repair-checkpoint.json')
    require(ledger['calls'][:len(repair['ledger_calls'])] == repair['ledger_calls'],
            'Prior reservations changed')
    require(all(sha(ROOT / p) == h for p, h in repair['rejected_journals'].items()),
            'Rejected history changed')
    get = lambda phase: read(ROOT / phases[phase]['manifest']['result_path'])
    live, pdf, new, verification = (get(p) for p in ('R3', 'R4', 'R5', 'R6'))
    require(live['execution_complete'] and len(live['excluded_checks']) == 272 and
            not live['unreviewed_exclusions'] and live['unencoded_parents_retained'] == 8,
            'Incomplete interpretation inventory')
    require(new['useful_decision_criterion'] and new['source_review_concerns'] == 0 and
            len(new['matches']) == 22 and all(r['matched'] for r in new['matches']),
            'Fresh development result differs')
    require(verification['cvc5']['status'] == 'PASS' and
            all(r['verification']['passed'] for r in verification['catala']), 'Backend disagreement')
    reader_check = read(ROOT / 'docs/monograph/review/reader-facing/document-check.json')
    structure = read(ROOT / 'docs/monograph/review/document-check.json')
    require(reader_check['status'] == 'PASS' and structure['status'] == 'PASSED', 'Document check failed')
    require(reader_check['citation_documents'] == 100 and reader_check['citation_occurrences'] == 234,
            'Citation inventory changed')
    render = read(OUT / 'doc-review/final/render.json')
    book = ROOT / 'docs/monograph/monograph.pdf'
    require(render['pdf_sha256'] == sha(book), 'Rendered review concerns another PDF')
    require(book.read_bytes() == (ROOT / 'docs/proposal/proposal.pdf').read_bytes(), 'Proposal alias differs')
    external = set(tested)
    external.update(phases['R7']['manifest']['inputs']['implementation'])
    external.update(str(p.relative_to(ROOT)) for p in DOC.rglob('*') if p.is_file())
    external.update(str(p.relative_to(ROOT)) for p in ROOT.glob('scripts/resolution_*.py'))
    external.update(str(p.relative_to(ROOT)) for p in ROOT.glob('docs/monograph/chapters/*.tex'))
    external.update(str(p.relative_to(ROOT)) for p in ROOT.glob('docs/monograph/review/**/*.json'))
    external.update(str(p.relative_to(ROOT)) for p in ROOT.glob('docs/monograph/*.pdf'))
    external.update(str(p.relative_to(ROOT)) for p in ROOT.glob('docs/proposal/*.pdf'))
    external.update(('docs/implementation/START-HERE.md', 'docs/monograph/README.md',
                     'docs/plans/assurance-after-round14.md', 'docs/papers/monograph-citation-archive.json'))
    for source in read(ROOT / 'docs/papers/monograph-citation-archive.json')['sources']:
        require(sha(ROOT / source['path']) == source['sha256'], 'Archived authority changed')
        external.add(source['path'])
    result = {
        'status': 'ENGINEERING_AND_EDITORIAL_DELIVERY_VERIFIED',
        'final_report_sha256': sha(OUT / 'final-report.json'), 'journals': journals,
        'tests': tests, 'tested_inputs_unchanged': True,
        'post_r7_tooling_changes': r7_changes,
        'editorial_changes': ['Spacing before citations in two paragraphs (three occurrences)',
                              'Singular/plural correction in result paragraph',
                              'Citation helper restricted to exact reviewed context hashes',
                              'Removed unrelated application import from document helper'],
        'r7_attempts_preserved': [13, 14, 15],
        'rejected_preliminary_reservations': 79,
        'reviewed_live_reservations': 37, 'allowance_consumed': 466, 'allowance_remaining': 34,
        'pages': 270, 'companion_pages': 76, 'protected_chapter_sources_preserved': True,
        'proposal_alias_identical': True, 'citation_documents': 100, 'citation_occurrences': 234,
        'rendered_inspection': {'pages': render['pages'], 'basis': 'Executor visual inspection',
                                'pdf_sha256': sha(book), 'human_reader_acceptance': 'PENDING'},
        'runtime_conformance_cases': 22, 'distinct_source_reference_cases': 11,
        'restored_pairs': live['restored_pairs'], 'unencoded_parents': 8,
        'remaining_pdf_issues': pdf['counts']['MATERIALITY_UNRESOLVED'],
        'legal_accuracy_established': False, 'release_eligible': False,
        'external_files': {p: sha(ROOT / p) for p in sorted(external)}}
    save(OUT / 'post-execution-review.json', result)
    manifest = {'files': {str(p.relative_to(OUT)): sha(p) for p in sorted(OUT.rglob('*'))
                         if p.is_file() and p.name not in ('delivery-manifest.json', '.lock')},
                'external_files': result['external_files'],
                'post_execution_review_sha256': sha(OUT / 'post-execution-review.json'),
                'release_eligible': False}
    save(OUT / 'delivery-manifest.json', manifest)
    print(json.dumps({k: result[k] for k in ('status', 'tests', 'pages', 'allowance_remaining')}))


if __name__ == '__main__':
    main()
