"""Freeze source destination readings without importing the candidate resolver."""
from datetime import datetime, timezone
import time
from scripts import prospectus_reference_scope_header_repair as prior
from legalmath.prospectus.successor.contracts import digest

ROOT, AUTH = prior.ROOT, prior.AUTH
PREP = AUTH / 'reviews/reference-addresses-345'
PLAN = 'docs/plans/prospectus-reference-addresses-2026-10-19.md'

# Source readings: each interval ends at its next printed peer/ancestor.
# These are manually enumerated from the selected source, not generated targets.
TARGETS = [
 ('1', ['4'], 2597, 4818, 'p109:l1'),
 ('1', ['3', 'b'], 1322, 2597, 'p108:l59'),
 ('6', ['2'], 23736, 24810, 'p124:l48'),
 ('5', ['1'], 11144, 11500, 'p118:l17'),
 ('4', ['2'], 8587, 9200, 'p114:l29'),
 ('3', ['1'], 6470, 6871, 'p111:l24'),
 ('5', ['2'], 11500, 13468, 'p118:l31'),
 ('5', ['3'], 13468, 17242, 'p119:l24'),
 ('5', ['4', 'b'], 17856, 18498, 'p120:l51'),
 ('5', ['5', 'b'], 19278, 19848, 'p121:l8'),
 ('5', ['5'], 18874, 20226, 'p120:l90'),
 ('2', ['2'], 5381, 6459, 'p110:l54'),
 ('9', ['1', 'a'], 28525, 28642, 'p126:l44'),
 ('9', ['1', 'b'], 28642, 28908, 'p126:l46'),
 ('9', ['1', 'c'], 28908, 30278, 'p126:l50'),
 ('9', ['1', 'd'], 30278, 30380, 'p127:l6'),
 ('9', ['1', 'e'], 30380, 30629, 'p127:l8'),
 ('9', ['1', 'f'], 30629, 30996, 'p127:l12'),
 ('9', ['1', 'g'], 30996, 31459, 'p127:l17'),
 ('9', ['1'], 28281, 31459, 'p126:l41'),
 ('10', ['1', 'a'], 32632, 32747, 'p128:l75'),
 ('10', ['1', 'b'], 32747, 33208, 'p128:l77'),
 ('10', ['1', 'c'], 33208, 33416, 'p129:l2'),
 ('10', ['1', 'd'], 33416, 33774, 'p129:l12'),
 ('11', ['2'], 35396, 35814, 'p129:l63'),
 ('11', ['7', 'a', 'ii'], 37462, 37977, 'p130:l46'),
 ('11', ['7', 'a', 'iii'], 37977, 38970, 'p130:l53'),
 ('13', ['1'], 42695, 42959, 'p132:l20'),
 ('14', ['4'], 44330, 46125, 'p132:l67'),
]

# Ordinal refers to the manually written destination table above.
ROWS = [
 ([425], [0]), ([2371, 2393], [1]), ([2557], [2]), ([6661], [3]),
 ([7891], [4]), ([8123], [4]), ([8385], [4]), ([8571], [1]),
 ([12522], [5]), ([13856], [6]), ([15056], []), ([15993], [7]),
 ([17340], [8]), ([18972], [9]), ([21362], [6]), ([21506], [10]),
 ([28161], []), ([28957], [11]), ([31489], [13, 14]),
 ([31593], [12, 15, 16, 17, 18]), ([31981], [19]),
 ([33951], [20, 21, 22, 23]), ([34965], [24]), ([35663], []),
 ([39303], [25, 26]), ([40687], []), ([43076], [27]),
 ([43200], [27]), ([43640], [28]),
]


def main():
    start = time.monotonic()
    assert not (PREP / 'candidate/reference_addresses.py').exists()
    manifest = prior.read(prior.PRODUCTS)
    products = {k: prior.read(ROOT / r['path']) for k, r in manifest['products'].items()}
    answer = prior.read(prior.HERE / 'ordinary-answer.json.gz')
    text = products['P2']['payload']['assembly']['continuous_text']
    pieces = answer['definition_sources']['source_pieces']
    rows = {r['paragraph_start']: r for r in answer['reference_scope_context']['contexts']}
    targets = []
    for section, path, a, b, unit in TARGETS:
        piece = next(p for p in pieces if p['start'] == a and p.get('raw_binding'))
        assert piece['raw_binding']['unit'].endswith(':' + unit)
        assert 0 <= a < b <= len(text)
        targets.append({'section': section, 'path': path, 'start': a, 'end': b,
            'unit': piece['raw_binding']['unit'], 'text_sha256': digest(text[a:b].encode()),
            'heading_source': piece['raw_binding']})
    expected = []
    for starts, indices in ROWS:
        a = min(rows[i]['start'] for i in starts)
        b = max(rows[i]['end'] for i in starts)
        expected.append({'paragraph_starts': starts, 'start': a, 'end': b,
            'raw': text[a:b], 'statute': rows[starts[0]]['statute'],
            'target_indices': indices})
    assert sorted(i for r in expected for i in r['paragraph_starts']) == sorted(rows)
    prior.save(PREP / 'expected.json', {'targets': targets, 'references': expected,
        'lexical_expressions': 30, 'logical_expressions': 29,
        'legal_truth_established': False, 'whole_task_complete': False})
    prior.save(PREP / 'source-freeze.json', {'created_at': datetime.now(timezone.utc).isoformat(),
        'candidate_absent': True, 'products_sha256': digest(products),
        'ordinary_answer_sha256': digest(answer), 'plan_sha256': prior.sha(ROOT / PLAN),
        'expected_sha256': prior.sha(PREP / 'expected.json'),
        'wall_seconds': time.monotonic() - start})
    print('Frozen 29 manually enumerated reference readings, 29 target containers; candidate absent')


if __name__ == '__main__':
    main()
