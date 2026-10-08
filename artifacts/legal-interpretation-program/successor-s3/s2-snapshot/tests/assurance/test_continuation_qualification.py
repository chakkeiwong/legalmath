from copy import deepcopy
import json
import shutil

import pytest

from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import qualification_adapter as adapter, comparison_domains as domains
from legalmath.interpretation.search.formal import Comparisons
from tests.catala.backend_support import JDK, TOOLCHAIN
from tests.translation.support import AT, fixture, snapshot
from legalmath.translation.model import from_reading
from .test_repair import mapped_pair
from .support import packet


@pytest.fixture(scope='module')
def qualified(tmp_path_factory):
    task, gen = fixture(); r = gen['readings'][0]; r['formalization'].pop('types')
    q = {'control_id': 'months.question', 'question': r['statement'], 'actor': r['subject'],
         'unit_of_assessment': 'One fund under declared month facts', 'temporal_basis': AT,
         'result_kind': 'REQUIREMENT_SATISFIED', 'true_means': 'Threshold met', 'false_means': 'Threshold unmet',
         'source_evidence': r['citations']}
    m = from_reading(r, task['packet'], AT)
    cases = [{'id': 'mathematical.'+str(n), 'snapshot': snapshot(m, {'months': str(n)}),
              'valid_at': AT, 'known_at': AT} for n in (-1, 0, 6, 10**35)]
    out = tmp_path_factory.mktemp('adapter')/'run'
    result = adapter.run(task['packet'], r, q, cases, out, JDK, AT, toolchain=TOOLCHAIN)
    return task['packet'], r, q, out, result


def test_investigation_question_attached_to_actual_machine_evidence(qualified):
    p, r, q, out, result = qualified
    assert result['summary']['executed_target_cases'] == 8
    assert adapter.verify(out, p, r, q, JDK, compiler=TOOLCHAIN['compiler']) == result
    assert result['unresolved_premises']['reading_answers_declared_question'] == 'PROPOSED'
    assert result['summary']['legal_correctness'] == 'NOT_ESTABLISHED'


@pytest.mark.parametrize('mutation', ['question', 'source', 'assumption', 'premise', 'assertion'])
def test_changed_question_or_suppressed_uncertainty_cannot_reuse_proof(qualified, tmp_path, mutation):
    p, r, q, original, _ = qualified; p, r, q = deepcopy((p, r, q))
    out = tmp_path/'mutated'; shutil.copytree(original, out)
    if mutation == 'question': q['question'] = 'Another question with the same result type'
    elif mutation == 'source': p['units'][0]['text'] += ' An amendment.'
    elif mutation == 'assumption': r['assumptions'].append('New factual assumption')
    else:
        path = out/'qualification.json'; value = json.loads(path.read_text())
        if mutation == 'premise': value['unresolved_premises']['source_meaning'] = 'PROVED'
        else: value['legal_correctness'] = 'PROVED'
        path.write_text(json.dumps(value))
    with pytest.raises(LegalMathError): adapter.verify(out, p, r, q, JDK, compiler=TOOLCHAIN['compiler'])


def domain_record():
    a, b, m = mapped_pair(); p = packet()
    record = {'profile': 'legalmath.comparison-domain.v1', 'packet_hash': digest(p), 'mapping_hash': digest(m),
        'scope': 'PROBE_SET', 'facts': [{'name': f['name'], 'type': f['type'], 'unit': f['unit'],
            'values': [False, True], 'origin': 'MATHEMATICAL_PROBE',
            'justification': 'Declared complete Boolean valuations for this engineering comparison; not legal fact labels.',
            'evidence': []} for f in m['common_facts']]}
    return a, b, m, p, record


def test_explicit_domain_executes_original_java_and_limits_equivalence_claim(tmp_path):
    a, b, m, p, record = domain_record()
    result = domains.compare(a, b, p, m, Comparisons(tmp_path, JDK, AT), record)
    assert result['comparison']['cases'] == 8
    assert result['comparison']['status'] == 'CONDITIONAL_EQUIVALENT_IN_DECLARED_DOMAIN'
    assert result['scope'] == 'PROBE_SET' and result['equivalence_outside_listed_domain'] == 'NOT_ESTABLISHED'
    assert not result['source_premises_established']


@pytest.mark.parametrize('mutation', ['source', 'mapping', 'unit', 'missing', 'duplicate', 'value', 'source_claim', 'human_label'])
def test_unjustified_or_malformed_domain_rejected(mutation):
    _, _, m, p, record = domain_record()
    if mutation == 'source': record['packet_hash'] = '0'*64
    elif mutation == 'mapping': record['mapping_hash'] = '0'*64
    elif mutation == 'unit': record['facts'][0]['unit'] = 'Different unit'
    elif mutation == 'missing': record['facts'].pop()
    elif mutation == 'duplicate': record['facts'][0]['values'] = [True, True]
    elif mutation == 'value': record['facts'][0]['values'] = ['true']
    elif mutation == 'source_claim': record['facts'][0]['origin'] = 'SOURCE_PREMISE'
    else: record['human_label'] = True
    with pytest.raises(LegalMathError): domains.validate(record, p, m)
