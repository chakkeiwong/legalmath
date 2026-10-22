"""Freeze source occurrence expectations before authoring the binding candidate."""
from datetime import datetime, timezone
import json
import time
from scripts import prospectus_definition_semantics as prior
from scripts import prospectus_definition_binding_oracle as oracle

ROOT, AUTH = prior.ROOT, prior.AUTH
PREP = AUTH / 'reviews/definition-bindings-331'
PLAN = 'docs/plans/prospectus-definition-use-bindings-2026-10-19.md'
METHOD = 'scripts/prospectus_definition_binding_cases.py'
ORACLE = 'scripts/prospectus_definition_binding_oracle.py'


def main():
    assert not (PREP / 'cases-freeze.json').exists()
    assert not (PREP / 'candidate.py').exists(), 'Cases must precede candidate'
    assert prior.read(prior.HERE / 'result.json')['status'] == 'PASS'
    start = time.monotonic()
    for name, checksum in prior.read(prior.HERE / 'outputs.json').items():
        assert prior.sha(prior.HERE / name) == checksum
    products, ordinary, _, _, _ = prior.baseline()
    coverage = prior.read(prior.HERE / 'coverage.json')
    content = oracle.expected_content(ordinary, coverage)
    assert len(content['records']) == 62 and len(content['uses']) == 612
    assert sum(u['binding'] is not None for u in content['uses']) == 11
    oracle.question_links(ordinary, content)
    prior.save(PREP / 'expected-content.json', content)
    prior.save(PREP / 'cases-freeze.json', {'frozen_at': datetime.now(timezone.utc).isoformat(),
        'source_matrix': prior.rel(prior.HERE / 'coverage.json'), 'source_matrix_sha256': prior.sha(prior.HERE / 'coverage.json'),
        'original_answer_sha256': oracle.digest(ordinary), 'products_sha256': oracle.digest(products),
        'expected_content_sha256': prior.sha(PREP / 'expected-content.json'),
        'plan_sha256': prior.sha(ROOT / PLAN), 'method_sha256': prior.sha(ROOT / METHOD),
        'oracle_sha256': prior.sha(ROOT / ORACLE), 'candidate_absent': True})
    prior.save(PREP / 'case-preparation.json', {'command': ['.venv/bin/python', '-m', 'scripts.prospectus_definition_binding_cases'],
        'wall_seconds': time.monotonic() - start, 'status': 'PASS'})
    print(json.dumps({'status': 'PASS', 'records': 62, 'original_associations': 610,
                      'supplemental_associations': 2, 'conditional_bindings': 11}))


if __name__ == '__main__':
    main()
