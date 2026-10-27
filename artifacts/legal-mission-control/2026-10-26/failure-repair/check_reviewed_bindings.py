"""Five explicit attribution reviews; not automatic evidence or legal acceptance."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts import legal_context_failure_repair as f

REASON_CASES = {
    '133410bdb809436d99438cab': {
        'P15': 'source:d996fc27b2d2e.u22.4405:0',
        'P16': 'source:d996fc27b2d2e.u23.4635:0'},
    '14ec7201038c25b790594880': {'P14': 'source:d996fc27b2d2e.u21.4164:0'},
    '86f6117938349c3e555ee450': {'P14': 'source:d996fc27b2d2e.u21.4164:0'},
}
QUERY_CASES = {
    'e1e28e46975b5dd55ef2013d': 'Footnote 3 and applicable standards for appropriate cybersecurity, recovery and continuity measures.',
    'aa36fba11f4e128976186ca2': 'Footnote 3 and the referenced cybersecurity requirements, including the applicable standards for appropriateness, comprehensiveness and robustness.',
}
FOOTNOTE = 'source:d996fc27b2d2e.u42.7511:0'
DOCUMENT_SOURCE = 'docs/papers/Circular on tokenisation of SFC-authorised investment products_SFC(2026).json'


def only_add_reviewed_bindings(baseline, proposed, links):
    expected = deepcopy(baseline)
    expected['assertion_bindings'] = baseline['assertion_bindings'] + links
    f.require(f.object_hash(proposed) == f.object_hash(expected),
              'Binding review changed substantive fields or unreviewed links')


def main():
    runtime = f.candidate_runtime()
    f.verify_packets(runtime)
    product, identity = runtime.product()
    rows, controls = [], []
    for row in f.classification():
        suffix = row['call'].split('-')[-1]
        if suffix not in REASON_CASES and suffix not in QUERY_CASES:
            continue
        packet, request, wire, prepared, raw = f.make_packet(row, runtime)
        if suffix == 'aa36fba11f4e128976186ca2':
            correction = f.read(f.BASE / 'reviewed-corrections' / row['call'] / 'proposal.json')
            f.require(correction['packet_sha256'] == f.object_hash(packet), 'Stale document correction')
            wire = f.apply_edits(wire, packet['allowed_edits'], correction['replacements'])
        baseline = runtime.refs.resolve(wire, prepared,
                                        maximum_bytes=identity['limits']['decoded_output_bytes'])
        expected_failure = runtime.outcome(lambda: runtime.validate(product, request, baseline))
        f.require(expected_failure['status'] == 'FAILED' and
                  expected_failure['reason'] == 'Numbered assertion has no document/proposition binding',
                  'Baseline no longer reproduces the reviewed failure')
        indexes = [x['index_hash'] for x in request['available_source_indexes']
                   if x['source']['path'] == DOCUMENT_SOURCE]
        f.require(len(indexes) == 1, 'Missing or ambiguous reviewed source document')
        index_hash = indexes[0]
        links, evidence = [], []
        if suffix in REASON_CASES:
            for locator, record_id in REASON_CASES[suffix].items():
                citations = [c for c in raw['need_dispositions'][0]['support']
                             if c['locator'] == locator and c['record_id'] == record_id]
                f.require(len(citations) == 1, 'Reviewed support citation changed')
                path = '/need_dispositions/0/reason'
                links.append({'path': path, 'index_hash': index_hash, 'citation': citations[0]})
                evidence.append({'path': path, 'locator': locator, 'record_id': record_id,
                                 'basis': 'Exact same delivered indexed quotation already attached to this disposition.',
                                 'limits': 'Attribution only; missing facts, later treatment and legal entailment remain separately assessed.'})
        else:
            sources = [r for r in request['records'] if r['id'] == FOOTNOTE]
            f.require(len(sources) == 1, 'Reviewed footnote was not delivered')
            citation = {'record_id': FOOTNOTE, 'locator': 'FN3', 'quote': sources[0]['text']}
            expected_paths = ['/context_needs/0/query', '/context_needs/1/query'] if suffix.startswith('e1e') else ['/context_needs/2/query']
            actual_paths = [f'/context_needs/{i}/query' for i, need in enumerate(baseline['context_needs'])
                            if need['query'] == QUERY_CASES[suffix]]
            f.require(actual_paths == expected_paths, 'Reviewed query paths changed')
            for path in actual_paths:
                links.append({'path': path, 'index_hash': index_hash, 'citation': citation})
                evidence.append({'path': path, 'locator': 'FN3', 'record_id': FOOTNOTE,
                                 'basis': 'Exact delivered footnote identifies the requested provision; it supplies an example, not complete adequacy criteria.',
                                 'limits': 'The validator scans context queries as numbered assertions. Linking the requested text does not establish adequacy or satisfy the missing need.'})
        proposed = deepcopy(baseline)
        proposed['assertion_bindings'].extend(links)
        only_add_reviewed_bindings(baseline, proposed, links)
        for field in ('verdict', 'reason', 'issues'):
            f.require(proposed[field] == raw[field], f'Substantive change in {field}')
        outcome = runtime.outcome(lambda: runtime.validate(product, request, proposed))
        result = {'call': row['call'], 'category': row['category'],
                  'baseline': expected_failure, 'outcome': outcome,
                  'raw_verdict': raw['verdict'], 'binding_count': len(links),
                  'request_sha256': row['request_sha256'], 'raw_sha256': row['raw_sha256'],
                  'baseline_decoded_sha256': f.object_hash(baseline),
                  'proposed_decoded_sha256': f.object_hash(proposed),
                  'provider_calls': 0, 'auto_accept': False,
                  'legal_acceptance': 'NOT_PROMOTED; original legal decision and unresolved needs unchanged'}
        destination = f.BASE / 'reviewed-bindings' / row['call']
        f.save_retained(destination / 'evidence.json', evidence)
        f.save_retained(destination / 'decoded-simulation.json', proposed)
        f.save_retained(destination / 'result.json', result)
        rows.append(result)
        if suffix.startswith('1334'):
            for damage in ('wrong_document', 'fabricated_quote', 'wrong_locator', 'foreign_path', 'missing_link'):
                bad = deepcopy(proposed)
                target = bad['assertion_bindings'][0]
                if damage == 'wrong_document':
                    target['index_hash'] = next(x['index_hash'] for x in request['available_source_indexes'] if x['index_hash'] != index_hash)
                elif damage == 'fabricated_quote':
                    target['citation']['quote'] = 'This evidence was invented.'
                elif damage == 'wrong_locator':
                    target['citation']['locator'] = 'P14'
                elif damage == 'foreign_path':
                    target['path'] = '/absent'
                else:
                    bad['assertion_bindings'].pop(0)
                control = runtime.outcome(lambda: runtime.validate(product, request, bad))
                f.require(control['status'] == 'FAILED', f'Adverse attribution passed: {damage}')
                controls.append({'damage': damage, **control})
            bad = deepcopy(proposed); bad['reason'] += ' Changed substantive reasoning.'
            control = runtime.outcome(lambda: only_add_reviewed_bindings(baseline, bad, links))
            f.require(control['status'] == 'FAILED', 'Substantive mutation accepted')
            controls.append({'damage': 'changed_reason', **control})
    f.require(len(rows) == 5, 'Expected all five binding cases')
    summary = {'kind': 'EXPLICIT_LOCAL_ATTRIBUTION_REVIEW_NOT_LEGAL_ACCEPTANCE',
               'count': len(rows), 'counts': dict(Counter(r['outcome']['status'] for r in rows)),
               'binding_count': sum(r['binding_count'] for r in rows),
               'rows': rows, 'adverse_controls': controls, 'provider_calls': 0, 'auto_accept': False}
    f.save_retained(f.BASE / 'reviewed-bindings.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in ('rows', 'adverse_controls')}, indent=2))
    print(json.dumps({'adverse_controls_rejected': len(controls)}))


if __name__ == '__main__':
    main()
