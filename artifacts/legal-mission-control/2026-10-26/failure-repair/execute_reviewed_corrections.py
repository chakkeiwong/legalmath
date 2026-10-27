"""Execute the explicitly reviewed local proposals; never dispatch or promote."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts import legal_context_failure_repair as f

# These are reviewed input correspondences, not fuzzy document replacements.
PRIOR_DOCUMENT_CASES = {
    '2caaa7210d60738cda68bee7', '316988ae7f0c89ee99f2fc06',
    '69ebd8da4a169a0e1aaf4ad8', '6c3289de33cfefe5809c5353',
    '7274085553cc8d909f3706bb', '84e2e99c0648730bff623608',
    '9473d9632f7c26d23aaabf15', 'aca9f668bbb6a91b6cfeb99c',
    'c68013b380847e4559c133e5', 'ce3da5fd18601442705f3b3d',
}
GAP_DOCUMENT_CASES = {'aa36fba11f4e128976186ca2', 'e827e12662205603668d15a1'}
PARAPHRASED_PRIOR_CASE = '9473d9632f7c26d23aaabf15'


def reviewed_proposal(row, packet, request, wire, raw):
    replacements, evidence = [], []
    suffix = row['call'].split('-')[-1]
    for edit in packet['allowed_edits']:
        path, mode = edit['path'], edit['mode']
        if mode in ('DETERMINISTIC_IDENTIFIER_CLEARING', 'REMOVE_AUTHENTICATED_NON_SOURCE_IDS'):
            value = edit['choices'][0]
            basis = {'rule': mode, 'source': path,
                     'preserved': 'kind, query, reason, locators except forbidden typed identifiers; all legal decisions'}
        elif mode == 'EXPLICIT_DISPOSITION_SELECTION':
            f.require(suffix == '0d849a0aec7d20baccb5855f', 'Unreviewed disposition case')
            i = int(path.split('/')[2]); disposition = wire['need_dispositions'][i]
            original = next(n for n in request['payload']['prior_needs']
                            if n['need_id'] == disposition['need_id'])
            f.require(original['route'] == 'CLIENT_FACT' and raw['verdict'] == 'UNRESOLVED',
                      'Changed fact-disposition prerequisite')
            f.require(disposition['reason'] == 'The supplied source identifies relevant duties, but client-specific facts needed to determine application and compliance remain absent.',
                      'Reviewed disposition reason changed')
            value = 'STILL_REQUIRED'
            basis = {'rule': 'REVIEWED_ABSENT_FACT', 'need_id': original['need_id'],
                     'source': f'/need_dispositions/{i}/reason',
                     'reason': 'The unchanged explanation explicitly says the necessary facts remain absent.'}
        elif mode == 'EXPLICIT_DOCUMENT_SELECTION':
            parts = path.split('/'); i, j = int(parts[2]), int(parts[4])
            need = wire['context_needs'][i]; locator = need['locators'][j]['locator']
            if suffix in PRIOR_DOCUMENT_CASES:
                candidates = []
                for k, item in enumerate(request['payload']['prior_needs']):
                    prior = item['original_need']
                    if prior.get('kind') != 'SOURCE_TEXT' or prior['record_ids'] != need['record_ids']:
                        continue
                    if suffix == PARAPHRASED_PRIOR_CASE:
                        f.require([r['locator'] for r in need['locators']] ==
                                  [r['locator'] for r in prior['locators']], 'Changed reviewed locator signature')
                    elif prior['query'] != need['query']:
                        continue
                    for n, target in enumerate(prior['locators']):
                        if target['locator'] == locator:
                            candidates.append((target['index_hash'], k, n, item['need_id']))
                f.require(len(candidates) == 1, 'Ambiguous original need correspondence')
                value, k, n, need_id = candidates[0]
                basis = {'rule': 'EXPLICIT_PRIOR_NEED_REVIEW', 'need_id': need_id,
                         'source': f'/payload/prior_needs/{k}/original_need/locators/{n}/index_hash',
                         'locator': locator, 'paraphrased_query_reviewed': suffix == PARAPHRASED_PRIOR_CASE}
            else:
                f.require(suffix in GAP_DOCUMENT_CASES, 'Unreviewed document case')
                candidates = [(g['index_hash'], k) for k, g in enumerate(raw['source_gaps'])
                              if g['locator'] == locator]
                f.require(len(candidates) == 1, 'Ambiguous existing source-gap identity')
                value, k = candidates[0]
                basis = {'rule': 'EXPLICIT_EXISTING_SOURCE_GAP_REVIEW',
                         'source': f'/source_gaps/{k}/index_hash', 'locator': locator,
                         'reason': 'Same missing provision explicitly identified in the unchanged response.'}
        else:
            raise ValueError(f'Unreviewed correction mode: {mode}')
        replacements.append({'path': path, 'value': value})
        evidence.append({'path': path, 'replacement': value, 'basis': basis})
    return {'packet_sha256': f.object_hash(packet), 'replacements': replacements}, evidence


def main():
    runtime = f.candidate_runtime()
    f.verify_packets(runtime)
    product, identity = runtime.product()
    results = []
    for row in f.classification():
        if row['lane'] == 'substantive_review':
            continue
        packet = f.read(f.PACKETS / (row['call'] + '.json'))
        _, request, wire, _, raw = f.make_packet(row, runtime)
        proposal, evidence = reviewed_proposal(row, packet, request, wire, raw)
        result, corrected = f.evaluate(row, packet, proposal, runtime, product, identity)
        destination = f.BASE / 'reviewed-corrections' / row['call']
        f.save_retained(destination / 'proposal.json', proposal)
        f.save_retained(destination / 'selection-evidence.json', evidence)
        f.save_retained(destination / 'wire-simulation.json', corrected)
        f.save_retained(destination / 'result.json', result)
        results.append(result)
    f.require(len(results) == 19, 'Expected exactly 19 mechanical cases')
    summary = {'kind': 'REVIEWED_OFFLINE_CORRECTIONS_NOT_LIVE_ACCEPTANCE',
               'count': len(results), 'counts': dict(Counter(r['status'] for r in results)),
               'verdict_counts': dict(Counter(r['raw_verdict'] for r in results)),
               'rows': results, 'provider_calls': 0, 'auto_accept': False}
    f.save_retained(f.BASE / 'reviewed-corrections.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k != 'rows'}, indent=2))
    for row in results:
        if row['status'] != 'VALIDATED_PROTOCOL_CANDIDATE':
            print(json.dumps(row))


if __name__ == '__main__':
    main()
