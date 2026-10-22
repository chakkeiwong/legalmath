"""Prevent literal exceptions and a local802 construction from becoming false law."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from legalmath.prospectus.successor import bgb_onward as module
from legalmath.prospectus.successor.contracts import digest

ROOT = Path(__file__).resolve().parents[2]
PREP = ROOT/'docs/implementation/prospectus-execution-authority/reviews/bgb-onward-integration-354'


@pytest.fixture
def context(monkeypatch):
    profile = json.loads((PREP/'profile.json').read_text())
    products = {'test': 'source-binding diagnostic only'}
    h28 = json.loads((PREP/'h28-baseline.json').read_text())
    base = {'statutory_references': {'records': [h28]}, 'questions': {'Q1': {'status': 'UNKNOWN'}}}
    base['report_sha256'] = digest(base)
    profile.update(products_sha256=digest(products), ordinary_answer_sha256=digest(base))
    monkeypatch.setattr(module, 'REGISTERED_PROFILE_SHA256', digest(profile))
    return products, base, profile


def run(context):
    products, ordinary, profile = context
    return module.evaluate(products, ordinary, profile, ROOT, expected_profile_sha256=digest(profile))[module.KEY]


def test_complete_literal_rules_scoped_construction_and_uncertainties(context):
    report = run(context)
    assert report['scope']['antecedent'] == 'BGB802_PRE_INITIATION_SIX_MONTH_PERIOD'
    assert report['scope']['status'] == 'LOCAL_GRAMMATICAL_CONSTRUCTION'
    assert report['scope']['application_to_all_clocks_proved'] is False
    rows = {r['section']: r for r in report['readings']}
    assert rows['206']['literal_rule']['effect'] == 'SUSPENSION_WHILE_PREVENTED'
    assert rows['210']['literal_rule']['effect'] == rows['211']['literal_rule']['effect'] == 'PREVENTION_OF_EXPIRY'
    assert '(2) Absatz 1 findet keine Anwendung' in rows['210']['source']['excerpts'][0]['quote']
    assert len(rows['211']['literal_rule']['alternative_events']) == 3
    assert report['unresolved'] == ['HISTORICAL_WORDING', 'CORRESPONDING_APPLICATION', 'PERSON_AND_CLAIM_FACTS', 'EVENT_DATES', 'CIVIL_COUNTING_CONVENTIONS']
    assert report['actual_deadline_computed'] is report['historical_application_proved'] is False


@pytest.mark.parametrize('kind', ['210-exclusion', '210-shorter', '211-shorter', '211-trigger',
    '206-effect', '206-time', 'broaden-scope', 'scope-proved', 'correspondence-proved',
    'historical', 'deadline', 'complete', 'missing-reading', 'quote', 'offset', 'text-hash',
    'raw-hash', 'receipt', 'unresolved', 'h28', 'wrong-scope-source', 'short-210-quote'])
def test_repinned_bad_reading_still_refused(context, monkeypatch, kind):
    products, ordinary, profile = context
    a, b, c = profile['readings']
    if kind == '210-exclusion': b['literal_rule']['exceptions'].pop()
    elif kind == '210-shorter': b['literal_rule']['exceptions'].pop(0)
    elif kind == '211-shorter': c['literal_rule']['exceptions'] = []
    elif kind == '211-trigger': c['literal_rule']['alternative_events'].pop()
    elif kind == '206-effect': a['literal_rule']['effect'] = 'AUTOMATIC_SIX_MONTH_ADDITION'
    elif kind == '206-time': a['literal_rule']['conditions'].pop()
    elif kind == 'broaden-scope': profile['scope']['antecedent'] = 'ALL_PRESENTATION_AND_LIMITATION_CLOCKS'
    elif kind == 'scope-proved': profile['scope']['application_to_all_clocks_proved'] = True
    elif kind == 'correspondence-proved': a['local_corresponding_application']['application_proved'] = True
    elif kind == 'historical': profile['historical_application_proved'] = True
    elif kind == 'deadline': profile['actual_deadline_computed'] = True
    elif kind == 'complete': profile['whole_build_complete'] = True
    elif kind == 'missing-reading': profile['readings'].pop()
    elif kind == 'quote': b['source']['excerpts'][0]['quote'] += ' changed'
    elif kind == 'offset': b['source']['excerpts'][0]['start'] += 1
    elif kind == 'text-hash': b['source']['text_sha256'] = '0'*64
    elif kind == 'raw-hash': b['source']['raw_sha256'] = '0'*64
    elif kind == 'receipt': b['source']['receipt_sha256'] = '0'*64
    elif kind == 'unresolved': profile['unresolved'].pop()
    elif kind == 'h28': profile['h28_record_sha256'] = '0'*64
    elif kind == 'wrong-scope-source': profile['scope']['source'] = deepcopy(a['source'])
    else:
        source = b['source']; part = source['excerpts'][0]
        text = (ROOT/source['text_path']).read_text()
        end = text.index('\n(2)')
        part.update(end=end, quote=text[part['start']:end])
    monkeypatch.setattr(module, 'REGISTERED_PROFILE_SHA256', digest(profile))
    with pytest.raises(ValueError, match='BGB onward'):
        run((products, ordinary, profile))


def test_original_answer_unchanged_and_profile_identity_required(context):
    products, ordinary, profile = context
    before = deepcopy(ordinary)
    run(context)
    assert ordinary == before
    with pytest.raises(ValueError, match='identity'):
        module.evaluate(products, ordinary, profile, ROOT, expected_profile_sha256='0'*64)


def test_unavailable_original_primary_reading_cannot_be_promoted(context, monkeypatch):
    products, ordinary, profile = context
    ordinary['statutory_references']['records'][0]['availability'] = 'NOT_SUPPLIED'
    ordinary['report_sha256'] = digest({k: v for k, v in ordinary.items() if k != 'report_sha256'})
    profile.update(ordinary_answer_sha256=digest(ordinary),
                   h28_record_sha256=digest(ordinary['statutory_references']['records'][0]))
    monkeypatch.setattr(module, 'REGISTERED_PROFILE_SHA256', digest(profile))
    with pytest.raises(ValueError, match='H28 retained'):
        run(context)
