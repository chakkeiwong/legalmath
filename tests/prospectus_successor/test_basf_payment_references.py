from copy import deepcopy
import gzip
import json
from pathlib import Path

import pytest

from legalmath.prospectus.successor import basf_payment_references as core
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.reviewed_references import admit

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'


@pytest.fixture(scope='module')
def original():
    p = json.loads(gzip.decompress((AUTH / 'attempts/basf-meanings/attempt-019/installed-construct/products.json.gz').read_bytes()))
    packet = json.loads((AUTH / 'reviews/basf-payment-references-273/packet.json').read_text())
    spec = core.specification()
    ids = {r['source']['unit'] for r in packet['references']}
    ids |= {r['raw_source']['unit'] for r in spec['target_selection']}
    # Complete the context required by the separate call-reference checker.
    call = json.loads((ROOT / 'src/legalmath/prospectus/successor/basf_call_references_spec.json').read_text())
    ids |= {r['source']['unit'] for r in call['references']}
    ids |= {r['unit'] for r in call['contexts']}
    legacy = json.loads((ROOT / 'src/legalmath/prospectus/successor/basf_legacy_references_spec.json').read_text())
    ids |= {r['source']['unit'] for r in legacy['references']}
    ids |= {r['unit'] for r in legacy['split_contexts']}
    governance = json.loads((ROOT / 'src/legalmath/prospectus/successor/basf_governance_references_spec.json').read_text())
    ids |= {r['source']['unit'] for r in governance['references']}
    ids |= {r['unit'] for r in governance['contexts']}
    graph = p['P1']['payload']['graph']
    ids.add(next(u['id'] for u in graph['units'] if u['document'] == 'basf-2032-final'))
    default = json.loads((ROOT / 'src/legalmath/prospectus/successor/basf_default_references_spec.json').read_text())
    ids |= {r['source']['unit'] for r in default['references']}
    ids |= {r['unit'] for r in default['contexts']}
    financial = json.loads((ROOT / 'src/legalmath/prospectus/successor/basf_financial_references_spec.json').read_text())
    ids |= {r['source']['unit'] for r in financial['references']}
    ids |= {r['unit'] for r in financial['contexts']}
    internal = json.loads((ROOT / 'src/legalmath/prospectus/successor/basf_internal_references_spec.json').read_text())
    ids |= {r['source']['unit'] for r in internal['references']}
    ids |= {r['unit'] for r in internal['contexts']}
    substitution = json.loads((ROOT / 'src/legalmath/prospectus/successor/basf_substitution_references_spec.json').read_text())
    ids |= {r['source']['unit'] for r in substitution['references']}
    ids |= {r['unit'] for r in substitution['contexts']}
    raw_ids = ids | {m['source']['unit'] for u in p['P2']['payload']['assembly']['units']
                     if u['unit'] in ids for m in (u.get('character_map') or [])}
    graph = {**graph, 'units': [u for u in graph['units'] if u['id'] in raw_ids]}
    assembly = p['P2']['payload']['assembly']
    assembly = {**assembly, 'units': [u for u in assembly['units'] if u['unit'] in ids]}
    packet['assembly_sha256'] = digest(assembly)
    return graph, assembly, packet


def test_complete_selected_paragraph_preserves_tax_qualification(original):
    graph, assembly, packet = original
    deps, edges = admit(graph, assembly, packet)
    assert len(edges) == 27 and [len(d['targets']) for d in deps] == [9, 9, 9]
    text = ' '.join(t['source']['quote'] for t in deps[0]['targets'])
    assert 'Section 1471' in text and 'Regierungszusammenarbeit' in text
    assert 'Renminbi' not in text and 'USD' not in text
    assert core.check(graph, assembly, packet)['external_tax_law_application'] == 'UNKNOWN'


@pytest.mark.parametrize('mutation', ['currency-only', 'missing-tax', 'raw-renminbi',
    'duplicate', 'rename', 'language', 'question', 'edition', 'use', 'boolean-offset', 'discovery'])
def test_wrong_but_locatable_target_or_identity_is_refused(original, mutation):
    graph, assembly, packet = deepcopy(original)
    row = packet['references'][0]
    if mutation == 'currency-only': row['targets'] = row['targets'][-1:]
    elif mutation == 'missing-tax': row['targets'].pop(2)
    elif mutation == 'raw-renminbi':
        from legalmath.prospectus.successor.occurrences import anchor
        raw = next(u for u in graph['units'] if u['id'].endswith(':p114:l35'))
        row['targets'][6]['source'] = anchor(raw)
    elif mutation == 'duplicate': packet['references'].append(deepcopy(row))
    elif mutation == 'rename': row['id'] = 'concealed'
    elif mutation == 'language': row['language'] = 'en'
    elif mutation == 'question': row['questions'] = ['Q1']
    elif mutation == 'edition': row['source']['source_sha256'] = '0' * 64
    elif mutation == 'use': row['targets'][0]['use'] = row['from_use']
    elif mutation == 'boolean-offset': row['targets'][0]['source']['start'] = False
    elif mutation == 'discovery': row['discovery_ids'] = ['invented']
    with pytest.raises(ValueError, match='BASF payment reference'):
        admit(graph, assembly, packet)


def test_restored_excluded_branch_cannot_hide_behind_correct_target_list(original):
    graph, assembly, packet = deepcopy(original)
    next(u for u in assembly['units'] if u['unit'].endswith(':p114:l36'))['role'] = 'OPERATIVE'
    with pytest.raises(ValueError, match='target selection changed'):
        core.check(graph, assembly, packet)


def test_missing_links_and_hidden_subquestion_uncertainty(original):
    graph, assembly, packet = original
    packet = {**packet, 'references': []}
    report = core.check(graph, assembly, packet)
    deps = core.missing_dependencies(report)
    unresolved = [d['id'] for d in deps]
    assert len(unresolved) == 3
    semantic = {'dependencies': deps, 'questions': {q: {'unresolved': unresolved.copy(),
        'subquestions': {'payment': {'unresolved': unresolved.copy()}}} for q in ('Q1', 'Q2')}}
    assert core.verify_consumed(graph, assembly, {'reference_admission': packet}, semantic)['status'] == 'UNREVIEWED'
    semantic['questions']['Q2']['subquestions']['payment']['unresolved'].pop()
    with pytest.raises(ValueError, match='hides or invents'):
        core.verify_consumed(graph, assembly, {'reference_admission': packet}, semantic)


def test_resealed_dependency_cannot_drop_qualifications(original):
    graph, assembly, packet = original
    deps, _ = admit(graph, assembly, packet)
    semantic = {'dependencies': deps, 'questions': {q: {'unresolved': []} for q in ('Q1', 'Q2')}}
    core.verify_consumed(graph, assembly, {'reference_admission': packet}, semantic)
    semantic['dependencies'][0]['targets'] = semantic['dependencies'][0]['targets'][-1:]
    with pytest.raises(ValueError, match='dependencies differ'):
        core.verify_consumed(graph, assembly, {'reference_admission': packet}, semantic)


def test_source_selection_cannot_be_deleted_to_remove_obligation(original):
    graph, assembly, packet = deepcopy(original)
    identity = packet['references'][0]['from_use']
    assembly['units'] = [u for u in assembly['units'] if u['unit'] != identity]
    with pytest.raises(ValueError, match='source selection unavailable'):
        core.check(graph, assembly, {**packet, 'references': []})
