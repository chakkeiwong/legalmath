"""Corruption diagnostics must not become an English-correctness oracle."""
from copy import deepcopy
import pytest
from legalmath.canonical import digest, loads
from legalmath.interpretation.assurance.quality import inspect_reading, presentation
from legalmath.interpretation.assurance.semantics import representation
from legalmath.interpretation.assurance.engine import Assurance
from tests.search.support import FunctionProvider
from .support import reading, packet
from .test_integration import responder, source, settings, AT


@pytest.mark.parametrize('text', [
    'We need valid JSON. Fix typo. Ensure statement.',
    'Let’s produce valid JSON now.',
    "I'll output two readings carefully.",
    'Output only JSON no markdown.',
    '[TRUE_IS_COMPLIANT] ...',
    '…',
])
def test_corruption_variants_have_exact_field_offsets_without_changing_reading(text):
    r = reading(); r['questions'] = ['Does should express a duty?', text]
    before = deepcopy(r); meaning = representation(r)
    result = inspect_reading(r, packet())
    assert result['status'] == 'FLAGGED'
    assert all(f['field_path'] == ['questions', 1] for f in result['findings'])
    for f in result['findings']:
        assert text[f['excerpt_start']:f['excerpt_end']] == f['excerpt']
        assert 0 <= f['start'] < f['end'] <= len(text)
    assert r == before and representation(r) == meaning


@pytest.mark.parametrize('text', [
    'Does should impose a duty or indicate supervisory guidance?',
    'The JSON submission format remains uncertain; clarification is required.',
    'The circular requires submission of valid JSON.',
    'We need valid evidence before interpreting this exception.',
    '須核實豁免是否適用；目前仍不確定。',
    'The term ... may have been elided in this incomplete quotation.',
])
def test_uncertainty_and_ordinary_technical_or_non_english_prose_are_not_corruption(text):
    r = reading(); r['questions'] = [text]
    result = inspect_reading(r, packet())
    assert result['status'] == 'NO_PATTERN_DETECTED'
    assert not result['legal_fidelity_evaluated'] and not result['coherence_established']


def test_authentic_source_quote_is_exempt_but_unsupported_quoted_chatter_is_flagged():
    p = packet(); quote = 'Output only JSON no markdown.'
    p['units'][0]['text'] = quote
    r = reading(); r['citations'] = [{'unit_id': 'p1', 'quote': quote}]
    r['questions'] = ['Does the instruction “' + quote + '” apply here?', quote]
    assert inspect_reading(r, p)['status'] == 'NO_PATTERN_DETECTED'
    r['questions'].append('The model says “We need valid JSON”.')
    assert inspect_reading(r, p)['findings'][0]['field_path'] == ['questions', 2]
    # Merely adding a fabricated citation cannot exempt model chatter.
    r['citations'].append({'unit_id': 'p1', 'quote': 'We need valid JSON'})
    assert inspect_reading(r, p)['status'] == 'FLAGGED'


def test_fact_descriptions_are_scanned_but_expressions_and_evidence_are_not():
    r = reading(); r['formalization']['facts'][0]['meaning'] = 'We need valid JSON.'
    r['formalization']['scope'] = 'We need valid JSON.'
    r['citations'][0]['quote'] = 'We need valid JSON.'
    result = inspect_reading(r, packet())
    assert [f['field_path'] for f in result['findings']] == [['formalization', 'facts', 0, 'meaning']]


def test_presentation_withholds_proposal_and_binds_diagnostics_to_original():
    bad = reading(); bad['subject'] = '...'
    diagnostics, view = presentation({'bad': bad, 'good': reading()}, packet())
    assert view['candidates']['bad']['proposal'] is None
    assert view['candidates']['good']['proposal'] == reading()
    assert diagnostics['bad']['reading_hash'] == digest(bad)
    assert view['candidates']['bad']['status'] == 'WITHHELD_CORRUPT_PROSE'


def test_bounded_quality_feedback_never_hides_the_total_or_presents_a_flagged_reading():
    r = reading()
    for key in ('subject', 'statement', 'distinction'):
        r[key] = 'We need valid JSON.'
    r['questions'] = r['assumptions'] = ['We need valid JSON.'] * 20
    fact = r['formalization']['facts'][0]
    r['formalization']['facts'] = [dict(fact, name=f'fact.{i}', meaning='We need valid JSON.',
                                      unit='We need valid JSON.') for i in range(30)]
    diagnostics, view = presentation({'a': r}, packet())
    assert diagnostics['a']['total_findings'] == 103
    assert len(diagnostics['a']['findings']) == 64 and diagnostics['a']['truncated']
    assert view['candidates']['a']['proposal'] is None


def test_integrated_corrupt_prose_survives_as_a_separate_unresolved_finding(root, tmp_path):
    normal = responder()
    def respond(request):
        result = normal(request)
        if request['task'] == 'GENERATE':
            result['readings'][0]['questions'].append('We need valid JSON.')
        return result
    engine = Assurance(tmp_path/'run', FunctionProvider(respond),
                       root/'.localresources/java-toolchain/jdk-17.0.20.1+1', AT, settings())
    result = engine.drive([source()], 'Selected gift control')
    assert result['execution_complete'] and result['status'] == 'UNRESOLVED'
    assert all(c['label'] == 'ENTAILED' for c in result['fidelity']['checks'])
    assert {f['stage'] for f in result['findings']} == {'PRESENTATION'}
    assert result['prose_quality']['flagged_candidate_ids'] == result['candidate_ids']
    originals = loads((tmp_path/'run/candidates.json').read_bytes())
    view = loads((tmp_path/'run/candidate-presentation.json').read_bytes())
    assert all(r['questions'][-1] == 'We need valid JSON.' for r in originals.values())
    assert all(row['proposal'] is None for row in view['candidates'].values())
    assert engine.verify() == result
