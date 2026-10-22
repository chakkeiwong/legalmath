"""Freeze the inspected source readings before the new candidate exists."""
from datetime import datetime, timezone
import signal
import time
from scripts import prospectus_rating_label as prior
from scripts import prospectus_cycle_disposition_oracle as oracle

ROOT, AUTH = prior.ROOT, prior.AUTH
PREP = AUTH / 'reviews/cycle-dispositions-337'
PLAN = 'docs/plans/prospectus-cycle-dispositions-2026-10-19.md'
METHOD = 'scripts/prospectus_cycle_disposition_cases.py'
ORACLE = 'scripts/prospectus_cycle_disposition_oracle.py'


def main():
    assert not PREP.exists()
    assert not (ROOT / 'src/legalmath/prospectus/successor/cycle_dispositions.py').exists()
    start = time.monotonic()
    PREP.mkdir()
    prior.save(PREP / 'cases-started.json', {'command': ['.venv/bin/python', '-m', 'scripts.prospectus_cycle_disposition_cases'],
        'started_at': datetime.now(timezone.utc).isoformat(), 'seconds_bound': 90})
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Cycle source preparation bound')))
    signal.alarm(90)
    try:
        for name, checksum in prior.read(prior.HERE / 'outputs.json').items():
            assert prior.sha(prior.HERE / name) == checksum, name
        products, _ = prior.baseline()
        ordinary = prior.read(prior.HERE / 'ordinary-answer.json.gz')
        references = {r['id']: r for r in products['P3']['payload']['interpretation_input']['reference_admission']['references']}
        nodes = {r['id']: r for r in products['P3']['payload']['clauses']['nodes']}
        actual = {r['id']: r for name in ('internal_references', 'financial_references') for r in ordinary[name]['references']}
        for name in oracle.ROLES:
            assert {k: v for k, v in actual[name].items() if k != 'reason'} == {k: v for k, v in references[name].items() if k != 'reason'}
        raw = {r['id']: r for r in products['P1']['payload']['graph']['units']}
        for reference in [references[k] for k in oracle.ROLES]:
            for source in [reference['source'], reference['authority'], *[t['source'] for t in reference['targets']]]:
                unit = raw[source['unit']]
                assert unit['raw'][source['start']:source['end']] == source['quote']
                assert unit['source_sha256'] == source['source_sha256']
        pages = ['docs/implementation/prospectus-basf-scope-repair/source-review-001/base-%d.png' % n for n in (108, 118, 123, 125, 132, 133)]
        decisions = {'readings': [{'id': name, 'role': role, 'reading': oracle.READINGS[name]} for name, role in oracle.ROLES.items()],
            'references': [references[k] for k in oracle.ROLES], 'nodes': [nodes[k] for k in oracle.NODES],
            'source_pages': {name: prior.sha(ROOT / name) for name in pages}}
        expected = oracle.content(products, ordinary, decisions)
        wanted = [["basf-base-september-2022-exchange:p108:l79"], ["basf-base-september-2022-exchange:p125:l49"]]
        assert all(q['dependency_cycles'] == wanted and len(q['prior_dependency_cycles']) == 4 for q in expected['questions'].values())
        prior.save(PREP / 'source-decisions.json', decisions)
        prior.save(PREP / 'expected-content.json', expected)
        prior.save(PREP / 'cases-freeze.json', {'created_at': datetime.now(timezone.utc).isoformat(), 'candidate_absent': True,
            'source_decisions_sha256': prior.sha(PREP / 'source-decisions.json'),
            'expected_file_sha256': prior.sha(PREP / 'expected-content.json'), 'expected_content_sha256': oracle.digest(expected),
            'products_sha256': oracle.digest(products), 'ordinary_answer_sha256': oracle.digest(ordinary),
            'plan_sha256': prior.sha(ROOT / PLAN), 'oracle_sha256': prior.sha(ROOT / ORACLE), 'method_sha256': prior.sha(ROOT / METHOD)})
        result = {'status': 'PASS', 'readings': 5, 'components_reviewed': 4, 'substantive_cycles_retained': 2,
            'wall_seconds': time.monotonic() - start}
        prior.save(PREP / 'case-preparation.json', result)
        print(result)
    except BaseException as error:
        prior.save(PREP / 'case-failure.json', {'type': type(error).__name__, 'message': str(error), 'wall_seconds': time.monotonic() - start})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
