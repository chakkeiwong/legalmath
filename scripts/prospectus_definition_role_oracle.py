"""Independent full-answer expectation from the frozen pre-candidate audit."""
from copy import deepcopy
import hashlib
import json


def checksum(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False).encode()).hexdigest()


def verify(actual, ordinary, products, profile, expected_changes):
    expected = deepcopy(ordinary)
    changes = []
    for row in expected_changes:
        piece = expected['definition_sources']['source_pieces'][row['piece']]
        matches = [(i, u) for i, u in enumerate(piece['assembly_uses']) if u['unit'] == row['unit']]
        assert len(matches) == 1
        index, use = matches[0]
        assert use['role'] == row['retained_role']
        use['role'] = row['current_role']
        changes.append({'piece': row['piece'], 'use': index, 'unit': row['unit'],
                        'before': row['retained_role'], 'after': row['current_role']})
    expected['definition_role_projection'] = {
        'version': 'definition-current-roles.v1', 'profile_sha256': checksum(profile),
        'products_sha256': checksum(products), 'ordinary_answer_sha256': checksum(ordinary),
        'prior_definition_report_sha256': checksum(ordinary['definition_sources']),
        'current_definition_report_sha256': checksum(expected['definition_sources']),
        'assembly_sha256': checksum(products['P2']['payload']['assembly']),
        'structural_profile_sha256': profile['structural_profile_sha256'], 'changes': changes,
        'source_text_preserved': True, 'meaning_and_scope_preserved': True, 'legal_truth_established': False}
    expected['report_sha256'] = checksum({k: v for k, v in expected.items() if k != 'report_sha256'})
    assert actual == expected, 'Complete answer differs from frozen independent expected delta'
    return {'status': 'PASS', 'independent_full_answer_delta': True, 'role_changes': len(changes),
            'units': len({r['unit'] for r in changes})}
