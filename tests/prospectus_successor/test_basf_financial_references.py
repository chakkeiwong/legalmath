from copy import deepcopy
import gzip
import json
from pathlib import Path

import pytest
from legalmath.prospectus.successor import basf_financial_references as core
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.reviewed_references import admit

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'


@pytest.fixture(scope='module')
def original():
    p = json.loads(gzip.decompress((AUTH / 'attempts/basf-meanings/attempt-019/installed-construct/products.json.gz').read_bytes()))
    packet = json.loads((AUTH / 'reviews/financial-references-278/packet.json').read_text())
    spec = core.specification()
    ids = {r['source']['unit'] for r in spec['references']}
    ids |= {r['unit'] for r in spec['contexts']}
    for rows in spec['selection'].values():
        for r in rows:
            ids.add(r['use'])
            ids |= {m['source']['unit'] for m in r['segments']}
    for name in ('basf_call_references_spec.json', 'basf_payment_references_spec.json',
                 'basf_legacy_references_spec.json', 'basf_governance_references_spec.json',
                 'basf_default_references_spec.json', 'basf_substitution_references_spec.json',
                 'basf_internal_references_spec.json'):
        other = json.loads((ROOT / 'src/legalmath/prospectus/successor' / name).read_text())
        ids |= {r['source']['unit'] for r in other['references']}
        ids |= {r['unit'] for r in other.get('contexts', []) + other.get('split_contexts', [])}
    graph = p['P1']['payload']['graph']
    graph = {**graph, 'units': [u for u in graph['units'] if u['id'] in ids],
             'references': [r for r in graph['references'] if r['unit'] in ids]}
    assembly = p['P2']['payload']['assembly']
    assembly = {**assembly, 'units': [u for u in assembly['units'] if u['unit'] in ids]}
    packet['assembly_sha256'] = digest(assembly)
    return graph, assembly, packet


def test_complete_definitions_preserve_dates_qualification_and_unknown_heading(original):
    graph, assembly, packet = original
    deps, edges = admit(graph, assembly, packet)
    assert [len(d['targets']) for d in deps] == [8, 8, 15, 5, 3]
    assert len(edges) == 39
    assert [d['status'] for d in deps] == ['RESOLVED', 'RESOLVED', 'UNRESOLVED', 'RESOLVED', 'RESOLVED']
    assert deps[2]['source_binding'] == 'RESOLVED'
    assert deps[2]['unknown_target_uses'] == ['basf-base-september-2022-exchange:p111:l24']
    maturity = ' '.join(t['source']['quote'] for t in deps[0]['targets'])
    assert 'Soweit nicht zuvor' in maturity and '8. März 2032' in maturity and 'Nennbetrag' in maturity
    assert deps[0]['discovery_ids'] and deps[2]['discovery_ids']
    assert core.check(graph, assembly, packet)['actual_payment_and_tax_call_compliance'] == 'UNKNOWN'


@pytest.mark.parametrize('mutation', [
    'truncated-maturity', 'missing-section', 'missing-paragraph', 'wrong-tax-branch',
    'missing-coupon-date', 'missing-formula', 'rename', 'question', 'edition', 'duplicate',
    'promote-heading', 'scalar-operation', 'scalar-source', 'reference-period', 'rmb-alternative',
    'excluded-whitespace', 'source-context', 'target-language', 'swap-discovery'])
def test_incomplete_pair_wrong_branch_and_plausible_provenance_refused(original, mutation):
    graph, assembly, packet = deepcopy(original)
    row = packet['references'][0]
    selected = {u['unit'].split(':', 1)[1]: u for u in assembly['units']}
    if mutation == 'truncated-maturity':
        row['targets'] = row['targets'][-1:]
    elif mutation == 'missing-section':
        packet['references'].pop(0)
    elif mutation == 'missing-paragraph':
        packet['references'].pop(1)
    elif mutation == 'wrong-tax-branch':
        packet['references'][4]['targets'] = row['targets']
    elif mutation == 'missing-coupon-date':
        packet['references'][2]['targets'] = packet['references'][2]['targets'][:-3]
    elif mutation == 'missing-formula':
        packet['references'][3]['targets'] = packet['references'][3]['targets'][:3]
    elif mutation == 'rename':
        row['id'] = 'hidden'
    elif mutation == 'question':
        row['questions'] = ['Q1']
    elif mutation == 'edition':
        row['source']['source_sha256'] = '0' * 64
    elif mutation == 'duplicate':
        packet['references'].append(deepcopy(row))
    elif mutation == 'promote-heading':
        selected['p111:l24']['role'] = 'OPERATIVE'
    elif mutation == 'scalar-operation':
        selected['p111:l35']['character_map'][1]['scalar_operation_sha256'] = '0' * 64
    elif mutation == 'scalar-source':
        selected['p118:l21']['character_map'][1]['operation'] = 'Text'
    elif mutation == 'reference-period':
        selected['p112:l85']['role'] = 'OPERATIVE'
    elif mutation == 'rmb-alternative':
        selected['p118:l19']['role'] = 'OPERATIVE'
    elif mutation == 'excluded-whitespace':
        selected['p111:l61']['text'] = ''
    elif mutation == 'source-context':
        next(u for u in graph['units'] if u['id'].endswith(':p111:l35'))['raw'] = 'Wrong paragraph'
    elif mutation == 'target-language':
        row['targets'][0]['language'] = 'en'
    else:
        row['discovery_ids'] = packet['references'][2]['discovery_ids']
    packet['assembly_sha256'] = digest(assembly)
    with pytest.raises(ValueError):
        admit(graph, assembly, packet)


def test_complete_omission_remains_uncertain_in_each_question(original):
    graph, assembly, packet = original
    packet = {**packet, 'references': []}
    deps = core.missing_dependencies(core.check(graph, assembly, packet))
    missing = [d['id'] for d in deps]
    assert len(missing) == 5
    semantic = {'dependencies': deps, 'questions': {q: {'unresolved': missing.copy(),
        'subquestions': {'a': {'unresolved': missing.copy()}}} for q in ('Q1', 'Q2')}}
    core.verify_consumed(graph, assembly, {'reference_admission': packet}, semantic)
    semantic['questions']['Q2']['subquestions']['a']['unresolved'].pop()
    with pytest.raises(ValueError, match='hides or invents'):
        core.verify_consumed(graph, assembly, {'reference_admission': packet}, semantic)
