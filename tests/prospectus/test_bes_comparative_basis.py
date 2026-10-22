"""Wrong adoption, cause, time, conditions and source identities must be refused."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import pytest
from legalmath.prospectus import bes_comparative_basis as basis
from legalmath.prospectus.successor.contracts import digest
from scripts.prospectus_comparative_oracle import verify

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def f():
    with gzip.open(ROOT/'tests/prospectus_successor/fixtures/bes_comparative_basis.json.gz', 'rt') as stream:
        return json.load(stream)


def output(f):
    return basis.evaluate(f['graph'], f['baseline'], f['profile'], ROOT,
                          expected_profile_sha256=digest(f['profile']))


def proof(f, value, explanation):
    return verify(value, explanation, f['profile'], f['graph'], f['baseline'], f['original'],
                  f['sources'], ROOT, f['prose_sha256'])


def test_original_alternatives_preserve_conditions_and_missing_cause(f):
    value = output(f)
    assert proof(f, value, basis.explain(value))['conditional_mechanisms'] == 4
    assert value['selected_mechanism'] is None
    assert value['mechanisms']['estimate']['retrospective_rewrite_from_estimate_alone'] is False
    choices = {r['id']: r for r in value['reported_adoptions']}
    assert choices['IAS1_revised']['impact'] == 'presentation_only'
    assert choices['IFRIC17']['status'] == 'not_yet_adopted'
    assert choices['improvement_IFRS5']['impact'] == 'prospective_2010_01_01'


PROFILE_CASES = ['cause', 'compliance', 'arithmetic-basis', 'estimate-retrospective', 'hindsight',
    'disclosure-omitted', 'transition-omitted', 'authorization-omitted', 'impracticability',
    'unapplied-adopted', 'impact-association', 'adoption-boundary', 'early-adoption',
    'edition-collapsed', 'source-role', 'standard-quote', 'report-quote', 'missing-context',
    'missing-standard', 'image', 'independent', 'graph', 'baseline', 'unknown-field']


def profile_change(profile, name):
    p = deepcopy(profile); r = p['reading']
    if name == 'cause': r['findings']['property_reason'] = 'IAS1_adoption'
    elif name == 'compliance': r['findings']['accounting_compliance'] = 'COMPLIANT'
    elif name == 'arithmetic-basis': r['findings']['arithmetic_proves_basis'] = True
    elif name == 'estimate-retrospective': r['estimate']['application'] = 'retrospective'
    elif name == 'hindsight': r['impracticability']['hindsight_allowed'] = True
    elif name == 'disclosure-omitted': r['presentation']['disclosures'].remove('reason')
    elif name == 'transition-omitted': r['policy']['transition'] = 'retrospective_always'
    elif name == 'authorization-omitted': r['error']['definition'].remove('available_at_original_authorization')
    elif name == 'impracticability': r['impracticability']['effort'] = 'inconvenient'
    elif name == 'unapplied-adopted': r['adoptions'][-1]['status'] = 'adopted'
    elif name == 'impact-association': r['adoptions'][2]['anchors'] = r['adoptions'][3]['anchors']
    elif name == 'adoption-boundary': r['adoption_boundaries']['unapplied'] = r['adoption_boundaries']['applied']
    elif name == 'early-adoption': r['temporal']['july_date_proves_BES_early_adoption'] = True
    elif name == 'edition-collapsed': r['edition']['guidance']['original'] = r['edition']['guidance']['consolidated']
    elif name == 'source-role': r['source_roles']['eu1126_20091227'] = 'controlling_law'
    elif name == 'standard-quote': r['sections']['eu1126_original'][0]['text'] += ' altered'
    elif name == 'report-quote': r['report_context'][0]['raw'] += ' altered'
    elif name == 'missing-context': r['report_context'].pop()
    elif name == 'missing-standard': r['sections']['eu1126_20091227'].pop()
    elif name == 'image': r['images'][0]['sha256'] = '0'*64
    elif name == 'independent': p['review']['independent'] = True
    elif name in ('graph', 'baseline'): p[name+'_sha256'] = '0'*64
    else: p['invented_permission'] = True
    return p


@pytest.mark.parametrize('name', PROFILE_CASES)
def test_freshly_repinned_semantic_profile_is_refused(f, name):
    p = profile_change(f['profile'], name)
    with pytest.raises(ValueError):
        basis.evaluate(f['graph'], f['baseline'], p, ROOT, expected_profile_sha256=digest(p))


OUTPUT_CASES = ['selected-cause', 'established-cause', 'violation', 'compliance', 'estimate',
    'no-hindsight', 'missing-condition', 'missing-branch', 'missing-evidence', 'adoption',
    'source', 'image', 'authority', 'boolean-number', 'prose']


def output_change(value, explanation, name):
    a = deepcopy(value)
    if name == 'selected-cause': a['selected_mechanism'] = 'presentation'
    elif name == 'established-cause': a['mechanisms']['presentation']['specific_cause_established'] = True
    elif name in ('violation', 'compliance'): a['findings']['accounting_compliance'] = name.upper()
    elif name == 'estimate': a['mechanisms']['estimate']['retrospective_rewrite_from_estimate_alone'] = True
    elif name == 'no-hindsight': a['qualifications']['impracticability']['hindsight_allowed'] = True
    elif name == 'missing-condition': a['mechanisms']['error']['conditions']['definition'].pop()
    elif name == 'missing-branch': a['mechanisms'].pop('policy')
    elif name == 'missing-evidence': a['missing_evidence'] = []
    elif name == 'adoption': a['reported_adoptions'][-1]['status'] = 'adopted'
    elif name == 'source': a['source_evidence']['standards']['eu1126_original'].pop()
    elif name == 'image': a['source_evidence']['images'][0]['sha256'] = '0'*64
    elif name == 'authority': a['may_execute_transaction'] = True
    elif name == 'boolean-number': a['findings']['arithmetic_proves_basis'] = 0
    elif name == 'prose': explanation += ' Therefore IAS 1 proves the reclassification valid.'
    return a, explanation


@pytest.mark.parametrize('name', OUTPUT_CASES)
def test_independent_verifier_rejects_changed_result(f, name):
    value = output(f); a, prose = output_change(value, basis.explain(value), name)
    with pytest.raises(ValueError): proof(f, a, prose)


def test_actual_graph_change_is_not_hidden_by_fresh_profile_pin(f):
    f['graph']['units'][0]['raw'] += ' changed'
    f['profile']['graph_sha256'] = digest(f['graph'])
    with pytest.raises(ValueError, match='report occurrence'): output(f)


def test_actual_source_file_bytes_are_checked(f, tmp_path):
    p = basis.SPEC
    spec = json.loads(p.read_text())
    for source in spec['standards'].values():
        path = tmp_path/source['path']; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'changed standard source')
    with pytest.raises(ValueError, match='standard bytes'):
        basis.evaluate(f['graph'], f['baseline'], f['profile'], tmp_path,
                       expected_profile_sha256=digest(f['profile']))
