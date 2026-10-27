"""Attribution tests use fixtures; passing does not establish legal applicability."""
from copy import deepcopy
import json
import importlib.util
from pathlib import Path
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import corpus_review as corpus
_spec = importlib.util.spec_from_file_location('corpus_fixture_helpers',
    Path(__file__).with_name('test_baseline_corpus_repairs.py'))
_fixtures = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fixtures)
corpus_setup, put = _fixtures.corpus_setup, _fixtures.put

def owned_fixture(root, profile='judgment'):
    expected, bundle = corpus_setup(root)
    source = expected['sources']['s']
    if profile == 'judgment':
        ownership = {'profile': 'judgment-rendered-fidelity.v2', 'source': source,
            'full_document_qualified': True, 'unresolved': [], 'remaining': [],
            'main_paragraphs': [{'locator': 'P1', 'rendered_label_verified': True, 'text': 'Owned paragraph text.'}],
            'full_components': [{'owner':'P1','region':'reasons','full_text_and_label_verified':True,'text':'Owned component text.'}],
            'full_footnotes': [{'display': '2', 'full_text_and_label_verified': True, 'text': 'Owned footnote text.'}]}
        pointer, locator, quote = '/main_paragraphs/0/text', 'P1', 'Owned paragraph text.'
    else:
        ownership = {'profile': 'handbook-passage-fidelity.v2', 'source': source,
            'source_passages_qualified': True, 'cross_page_delivery_gaps': [],
            'clauses': [{'section': 'OPS', 'label': '1.1', 'fully_delivered_pages': True, 'text': 'Owned clause text.'}]}
        pointer, locator, quote = '/clauses/0/text', 'OPS:1.1', 'Owned clause text.'
    reference = put(root, 'ownership.json', ownership)
    fidelity = {'fidelity_reconciled': True, 'evidence': [source, reference]}
    expected['fidelity'] = put(root, 'owned-fidelity.json', fidelity)
    row = {'source_id':'s', 'source':source, 'passage':reference,
        'passage_pointer':pointer, 'locator':locator, 'quote':quote}
    return expected, bundle, ownership, fidelity, row

@pytest.mark.parametrize('kind', ['paragraph','component','footnote','handbook'])
def test_registered_qualified_owned_passage_accepted(tmp_path, kind):
    expected, _, _, fidelity, row = owned_fixture(tmp_path, 'handbook' if kind == 'handbook' else 'judgment')
    if kind == 'footnote':
        row.update(passage_pointer='/full_footnotes/0/text', locator='FN2', quote='Owned footnote text.')
    elif kind == 'component':
        row.update(passage_pointer='/full_components/0/text', locator='P1', quote='Owned component text.')
    corpus.support(tmp_path, [row], expected['sources'], {'s'}, fidelity)

@pytest.mark.parametrize('damage', ['unregistered','source','profile','qualification','pointer',
    'locator','text','flag','leading_zero','no_pointer','wrong_collection'])
def test_owned_passage_adverse_controls(tmp_path, damage):
    expected, _, ownership, fidelity, row = owned_fixture(tmp_path)
    if damage == 'unregistered': fidelity['evidence'].pop()
    elif damage == 'source': ownership['source'] = put(tmp_path,'other.txt','Other source.')
    elif damage == 'profile': ownership['profile'] = 'unreviewed-extraction.v1'
    elif damage == 'qualification': ownership['full_document_qualified'] = False
    elif damage == 'pointer': row['passage_pointer'] = '/main_paragraphs/9/text'
    elif damage == 'locator': row['locator'] = 'P9'
    elif damage == 'text': row['quote'] = 'Not in this paragraph.'
    elif damage == 'flag': ownership['main_paragraphs'][0]['rendered_label_verified'] = False
    elif damage == 'leading_zero': row['passage_pointer'] = '/main_paragraphs/00/text'
    elif damage == 'no_pointer': row.pop('passage_pointer')
    else:
        ownership['unreviewed'] = [{'text':'Owned paragraph text.'}]
        row['passage_pointer'] = '/unreviewed/0/text'
    if damage in ('source','profile','qualification','flag','wrong_collection'):
        row['passage'] = put(tmp_path,'altered-ownership.json',ownership)
        fidelity['evidence'][-1] = row['passage']
    with pytest.raises(LegalMathError):
        corpus.support(tmp_path,[row],expected['sources'],{'s'},fidelity)

def test_unrelated_hashed_passage_cannot_qualify_corpus(tmp_path):
    expected, bundle = corpus_setup(tmp_path)
    row = bundle['applicability'][0]['applicability']['primary_evidence'][0]
    row['passage'] = put(tmp_path,'unrelated.txt','Unrelated document assertion.')
    row['quote'] = 'Unrelated document assertion.'
    with pytest.raises(LegalMathError):
        corpus.evaluate(tmp_path,expected,put(tmp_path,'bundle.json',bundle))

def test_owned_support_can_complete_the_explicit_review_fixture(tmp_path):
    expected, bundle, _, _, row = owned_fixture(tmp_path)
    for finding in bundle['applicability']:
        for duty in ('applicability','later_treatment'):
            finding[duty]['primary_evidence'] = [deepcopy(row)]
    for answer in bundle['answer_use']:
        answer['propositions'][0]['primary_evidence'] = [deepcopy(row)]
    bundle['context_hash'] = digest(expected)
    for name, reference in bundle['controls'].items():
        control = json.loads((tmp_path/reference['path']).read_text())
        control['context_hash'] = digest(expected)
        bundle['controls'][name] = put(tmp_path,name+'-owned.json',control)
    outcome = corpus.evaluate(tmp_path,expected,put(tmp_path,'owned-bundle.json',bundle))
    assert outcome['status'] == 'SUCCEEDED'
    assert outcome['legal_correctness_established'] is False
