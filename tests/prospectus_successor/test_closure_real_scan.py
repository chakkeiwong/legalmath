"""Original BES scan occurrences and full qualifications reach the real service."""
import importlib.util
import json
from pathlib import Path

from legalmath.prospectus.successor import service

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'docs/implementation/prospectus-integration-closure/real-scan'


def source_reading(**controls):
    # Use the reviewed packet authoring route to rebind each current parent;
    # the assertions below come from the independently retained printed oracle.
    spec = importlib.util.spec_from_file_location('bes_consumer', PACKAGE / 'consumer.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    review = module.load_review()
    return review, service.assess(module.request(review, **controls), ROOT)


def test_real_scan_corrections_keep_raw_identifiers_and_full_qualifications():
    review, report = source_reading()
    original = json.loads((PACKAGE / 'baseline/attempt-001/service-report.json').read_text())
    assert report['source_map']['units'] == original['source_map']['units']
    assert {q: r['status'] for q, r in report['questions'].items()} == {
        'Q1': 'UNKNOWN', 'Q2': 'UNKNOWN', 'Q3': 'PARTIAL',
        'Q4': 'UNKNOWN', 'Q5': 'UNSUPPORTED', 'Q6': 'UNKNOWN'}
    corrections = report['source_map']['corrections']['entries']
    isin = next(row for row in corrections if row['id'] == 'isin-segment-0')
    assert isin['source']['quote'] == 'PTBEQBOMO0010'
    assert isin['text'] == 'PTBEQBOM0010'
    assert all(row['bbox'] is None and len(row['image_sha256']) == 64 for row in corrections)
    nodes = {n['id']: n for n in report['clause_graph']['nodes']}
    assert len(nodes) == 23
    for identity in ('eligibility-qualification', 'ratings-qualification'):
        target = next(t for t in review['targets'] if t['id'] == identity)
        assert nodes['bes:' + identity]['quote'] == ' '.join(s['source']['quote'] for s in target['segments'])
    assert nodes['bes:intended-value']['quote'] == 'Yes'
    assert len([d for d in report['dependencies'] if d['id'].startswith('governing:bes-') and d['status'] == 'RESOLVED']) == 16
    assert report['mode'] == 'ASSISTED' and not report['independent_legal_acceptance']


def test_real_scan_layout_requires_whole_qualification_even_when_yes_survives():
    _, report = source_reading(exclude_target='eligibility-qualification')
    nodes = {n['id']: n for n in report['clause_graph']['nodes']}
    assert nodes['bes:intended-value']['quote'] == 'Yes'
    assert 'bes:eligibility-qualification' not in nodes
    dependencies = {d['id']: d for d in report['dependencies']}
    for question in ('Q1', 'Q2'):
        identity = 'governing:bes-eligibility-qualified:' + question
        assert dependencies[identity]['status'] == 'UNRESOLVED'
        assert identity in report['questions'][question]['unresolved']
        assert report['questions'][question]['status'] == 'UNKNOWN'
