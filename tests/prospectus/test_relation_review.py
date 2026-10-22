from copy import deepcopy

import pytest

from legalmath.prospectus.relation_review import VERSION, validate_review_packet
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor


@pytest.fixture
def sample(tmp_path):
    (tmp_path / 'source.pdf').write_bytes(b'synthetic source fixture')
    (tmp_path / 'page.png').write_bytes(b'synthetic render fixture')
    source = digest((tmp_path / 'source.pdf').read_bytes())
    units = [{'id': f'u{i}', 'raw': text, 'document': 'synthetic',
              'source_sha256': source, 'page': 1, 'visible': True,
              'text_sha256': digest(text.encode())}
             for i, text in enumerate(['(i)', 'Field:', 'Value', 'Another field:', 'Other'])]
    graph = {'units': units}
    edge = {'kind': 'label-value', 'from': [anchor(units[1])],
            'to': [anchor(units[2])], 'row_marker': anchor(units[0]),
            'status': 'REQUIRES_REVIEW', 'legal_scope_established': False}
    candidate = {'id': 'relation-candidate:' + digest(edge), **edge}
    discovery = {'candidates': [candidate], 'source_graph_sha256': digest(graph),
                 'accepted_relations': [], 'legal_scope_inferred': False}
    targets = [{'id': 'protected', **{k: edge[k] for k in ('kind', 'from', 'to')}}]
    row = {'candidate_id': candidate['id'], 'candidate_sha256': digest(candidate),
           'protected_target_ids': ['protected'], 'disposition': 'REVIEWABLE_PRINTED_RELATION',
           'reason': 'The synthetic field and value occupy this row.',
           'repair': 'Retain for exposed review.', 'excess': [], 'omitted': [],
           'transcription_anchors': [], 'evidence_anchors': edge['from'] + edge['to'] + [edge['row_marker']],
           'transcription_note': 'Synthetic fixture; no transcription claim.'}
    packet = {'version': VERSION, 'source_graph_sha256': digest(graph),
              'discovery_sha256': digest(discovery), 'protected_targets_sha256': digest(targets),
              'reviewer': {'identity': 'test agent', 'basis': 'AGENT_EXPOSED_DEVELOPMENT_REVIEW',
                           'independent': False},
              'sources': [{'document': 'synthetic', 'source_path': 'source.pdf',
                           'source_sha256': source, 'pages': [{'page': 1, 'path': 'page.png',
                           'sha256': digest((tmp_path / 'page.png').read_bytes())}]}],
              'reviews': [row], 'accepted_relations': [], 'legal_scope_inferred': False}
    return graph, discovery, targets, packet, tmp_path


def test_valid_packet_is_isolated_and_retains_exact_inputs(sample):
    before = deepcopy(sample[:-1])
    result = validate_review_packet(*sample)
    assert sample[:-1] == before
    assert result['candidate_count'] == result['protected_target_count'] == 1
    assert not result['accepted_relations'] and not result['may_change_answer']
    assert not result['legal_scope_inferred'] and not result['independent_legal_acceptance']
    result['packet']['reviews'].clear()
    assert sample[3]['reviews']


@pytest.mark.parametrize('disposition', ['WRONG_PRINTED_SCOPE', 'UNRESOLVED_TRANSCRIPTION'])
def test_disputed_endpoint_is_preserved_without_correction(sample, disposition):
    row = sample[3]['reviews'][0]
    row['disposition'] = disposition
    row['excess' if disposition == 'WRONG_PRINTED_SCOPE' else 'transcription_anchors'] = [sample[1]['candidates'][0]['to'][0]]
    result = validate_review_packet(*sample)
    assert result['dispositions'][disposition] == 1
    assert sample[1]['candidates'][0]['to'][0]['quote'] == 'Value'


@pytest.mark.parametrize('case', [
    'missing', 'duplicate', 'foreign', 'candidate_hash', 'candidate_changed',
    'graph_changed', 'targets_changed', 'source_changed', 'render_changed',
    'render_missing', 'duplicate_page', 'forged_anchor', 'empty_reason',
    'empty_repair', 'independent', 'governing', 'accepted', 'extra_claim',
    'wrong_without_dispute', 'transcription_without_anchor', 'excess_outside',
    'omitted_present', 'dispute_not_evidenced', 'wrong_target', 'absolute_path',
    'foreign_page', 'empty_evidence', 'duplicate_anchor', 'candidate_bad_id',
    'candidate_duplicate', 'target_duplicate', 'bad_text_hash', 'reviewable_dispute',
    'endpoint_evidence_missing', 'render_escape', 'source_missing', 'marker_forged',
])
def test_invalid_or_overclaiming_packets_refuse(sample, case):
    graph, discovery, targets, packet, root = sample
    row = packet['reviews'][0]
    endpoint = discovery['candidates'][0]['to'][0]
    if case == 'missing': packet['reviews'].clear()
    elif case == 'duplicate': packet['reviews'].append(deepcopy(row))
    elif case == 'foreign': row['candidate_id'] = 'foreign'
    elif case == 'candidate_hash': row['candidate_sha256'] = '0' * 64
    elif case == 'candidate_changed': discovery['candidates'][0]['to'][0]['quote'] = 'changed'
    elif case == 'graph_changed': graph['units'][2]['raw'] = 'changed'
    elif case == 'targets_changed': targets.clear()
    elif case == 'source_changed': (root / 'source.pdf').write_bytes(b'changed')
    elif case == 'render_changed': (root / 'page.png').write_bytes(b'changed')
    elif case == 'render_missing': packet['sources'][0]['pages'].clear()
    elif case == 'duplicate_page': packet['sources'][0]['pages'] *= 2
    elif case == 'forged_anchor': row['evidence_anchors'] = [{**endpoint, 'quote': 'forged'}]
    elif case == 'empty_reason': row['reason'] = '  '
    elif case == 'empty_repair': row['repair'] = ''
    elif case == 'independent': packet['reviewer']['independent'] = True
    elif case == 'governing': packet['legal_scope_inferred'] = True
    elif case == 'accepted': packet['accepted_relations'] = ['invented']
    elif case == 'extra_claim': row['governing_law_confirmed'] = True
    elif case == 'wrong_without_dispute': row['disposition'] = 'WRONG_PRINTED_SCOPE'
    elif case == 'transcription_without_anchor': row['disposition'] = 'UNRESOLVED_TRANSCRIPTION'
    elif case == 'excess_outside': row.update(disposition='WRONG_PRINTED_SCOPE', excess=[anchor(graph['units'][4])])
    elif case == 'omitted_present': row.update(disposition='WRONG_PRINTED_SCOPE', omitted=[endpoint])
    elif case == 'dispute_not_evidenced': row.update(disposition='WRONG_PRINTED_SCOPE', excess=[endpoint], evidence_anchors=[anchor(graph['units'][0])])
    elif case == 'wrong_target': row['protected_target_ids'] = []
    elif case == 'absolute_path': packet['sources'][0]['source_path'] = str(root / 'source.pdf')
    elif case == 'foreign_page':
        graph['units'][4]['page'] = 2
        discovery['source_graph_sha256'] = packet['source_graph_sha256'] = digest(graph)
        packet['discovery_sha256'] = digest(discovery)
        row['evidence_anchors'] = [anchor(graph['units'][4])]
    elif case == 'empty_evidence': row['evidence_anchors'] = []
    elif case == 'duplicate_anchor': row['evidence_anchors'] *= 2
    elif case == 'candidate_bad_id':
        discovery['candidates'][0]['id'] = 'bad'
        packet['discovery_sha256'] = digest(discovery)
    elif case == 'candidate_duplicate':
        discovery['candidates'] *= 2
        packet['discovery_sha256'] = digest(discovery)
    elif case == 'target_duplicate':
        targets *= 2
        packet['protected_targets_sha256'] = digest(targets)
    elif case == 'bad_text_hash':
        graph['units'][4]['text_sha256'] = 'bad'
        discovery['source_graph_sha256'] = packet['source_graph_sha256'] = digest(graph)
        packet['discovery_sha256'] = digest(discovery)
    elif case == 'reviewable_dispute': row['excess'] = [endpoint]
    elif case == 'endpoint_evidence_missing': row['evidence_anchors'] = [anchor(graph['units'][0])]
    elif case == 'render_escape': packet['sources'][0]['pages'][0]['path'] = '../page.png'
    elif case == 'source_missing': packet['sources'].clear()
    elif case == 'marker_forged':
        discovery['candidates'][0]['row_marker']['quote'] = 'forged'
        packet['discovery_sha256'] = digest(discovery)
    with pytest.raises(ValueError): validate_review_packet(*sample)
