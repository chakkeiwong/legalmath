from copy import deepcopy
import gzip
import json
from pathlib import Path

import pytest

from legalmath.prospectus.successor import basf_legacy_references as core
from legalmath.prospectus.successor import reviewed_references, service, source_graph, contract_assembly
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'


@pytest.fixture(scope='module')
def original():
    p = json.loads(gzip.decompress((AUTH / 'attempts/basf-meanings/attempt-019/installed-construct/products.json.gz').read_bytes()))
    spec = core.specification()
    ids = {r['source']['unit'] for r in spec['references']}
    ids |= {t['source']['unit'] for r in spec['references'] for t in r['targets']}
    ids |= {s['unit'] for s in spec['split_contexts']}
    for name in ('basf_call_references_spec.json', 'basf_payment_references_spec.json', 'basf_governance_references_spec.json'):
        other = json.loads((ROOT / 'src/legalmath/prospectus/successor' / name).read_text())
        ids |= {r['source']['unit'] for r in other['references']}
        ids |= {r['unit'] for r in other.get('contexts', [])}
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
    graph = {**graph, 'units': [u for u in graph['units'] if u['id'] in raw_ids],
             'references': [r for r in graph['references'] if r['unit'] in ids]}
    assembly = p['P2']['payload']['assembly']
    assembly = {**assembly, 'units': [u for u in assembly['units'] if u['unit'] in ids]}
    packet = deepcopy(p['P1']['payload']['request']['reference_admission'])
    packet['assembly_sha256'] = digest(assembly)
    return graph, assembly, packet


def test_twenty_original_complete_reference_mappings(original):
    graph, assembly, packet = original
    deps, edges = reviewed_references.admit(graph, assembly, packet)
    assert len(deps) == 20 and len(edges) == sum(len(r['targets']) for r in packet['references'])
    semantic = {'dependencies': deps}
    reviewed_references.verify_consumed(graph, assembly, {'reference_admission': packet}, semantic)
    assert core.check(graph, assembly, packet)['missing'] == []


def test_separate_citation_on_same_line_is_not_misclassified(original):
    graph, assembly, packet = deepcopy(original)
    source = next(u for u in graph['units'] if u['id'].endswith(':p131:l17'))
    phrase = '§ 50'
    start = source['raw'].index(phrase)
    row = deepcopy(next(r for r in packet['references'] if r['id'] == 'prose-notice-131-17'))
    row.update(id='separate-statutory-citation', source=anchor(source, start, start+len(phrase)))
    packet['references'].append(row)
    # This checks source separation only; the invented row is not admitted
    # here and establishes no statutory interpretation or target authority.
    assert core.check(graph, assembly, packet)['missing'] == []


@pytest.mark.parametrize('index', range(20))
def test_every_original_target_cannot_be_truncated(original, index):
    graph, assembly, packet = deepcopy(original)
    row = packet['references'][index]
    row['targets'] = row['targets'][:1]
    with pytest.raises(ValueError, match='original complete reviewed target'):
        reviewed_references.admit(graph, assembly, packet)


@pytest.mark.parametrize('mutation', ['drop', 'change', 'invent', 'duplicate'])
def test_every_reviewed_dependency_is_recomputed(original, mutation):
    graph, assembly, packet = original
    deps, _ = reviewed_references.admit(graph, assembly, packet)
    if mutation == 'drop': deps.pop()
    elif mutation == 'change': deps[0]['targets'].pop()
    elif mutation == 'invent': deps.append({**deepcopy(deps[0]), 'id': 'reviewed-reference:invented'})
    else: deps.append(deepcopy(deps[0]))
    with pytest.raises(ValueError, match='dependencies differ'):
        reviewed_references.verify_consumed(graph, assembly, {'reference_admission': packet}, {'dependencies': deps})


def test_missing_older_relative_links_are_visible(original):
    graph, assembly, packet = deepcopy(original)
    packet['references'] = [r for r in packet['references'] if r['discovery_ids']]
    report = core.check(graph, assembly, packet)
    deps = core.missing_dependencies(report)
    assert report['missing'] == ['clearing-publication-25', 'clearing-publication-27', 'holding-proof-information']
    unresolved = [d['id'] for d in deps]
    semantic = {'dependencies': deps, 'questions': {q: {'unresolved': unresolved.copy(),
        'subquestions': {'a': {'unresolved': unresolved.copy()}}} for q in ('Q1', 'Q2')}}
    core.verify_consumed(graph, assembly, {'reference_admission': packet}, semantic)
    semantic['questions']['Q2']['subquestions']['a']['unresolved'].pop()
    with pytest.raises(ValueError, match='hides or invents'):
        core.verify_consumed(graph, assembly, {'reference_admission': packet}, semantic)


@pytest.mark.parametrize('mutation', ['rename', 'question', 'edition', 'source-omitted', 'split-context'])
def test_identity_and_split_context_are_checked(original, mutation):
    graph, assembly, packet = deepcopy(original)
    row = packet['references'][0]
    if mutation == 'rename': row['id'] = 'unknown'
    elif mutation == 'question': row['questions'] = ['Q1']
    elif mutation == 'edition': row['source']['source_sha256'] = '0'*64
    elif mutation == 'source-omitted': assembly['units'] = [u for u in assembly['units'] if u['unit'] != row['from_use']]
    else:
        next(u for u in graph['units'] if u['id'].endswith(':p114:l2'))['raw'] = 'not the citation continuation'
    with pytest.raises(ValueError):
        core.check(graph, assembly, packet)


def test_non_basf_consumer_preserves_valid_reference_and_refuses_tampering(tmp_path):
    from scripts.prospectus_closure_fixtures import cross_document_fixture, REVIEW
    req = cross_document_fixture(tmp_path)
    graph = source_graph.build(req['bundle'], tmp_path)
    assembly = contract_assembly.assemble(graph, req['assembly'])
    a, b = [anchor(u) for u in graph['units']]
    req['reference_admission'] = {'version': 'reviewed-references.v1', 'assembly_sha256': digest(assembly),
        'review': REVIEW, 'references': [{'id': 'other-document', 'form': 'external', 'source': a,
        'from_use': a['unit'], 'language': 'en', 'targets': [{'source': b, 'use': b['unit'], 'language': 'en'}],
        'authority': a, 'questions': ['Q1', 'Q2'], 'reason': 'Synthetic explicit cross-document control'}]}
    p1 = service.source_product(req, tmp_path)
    p2 = service.construction_product(p1, tmp_path)
    p3 = service.interpretation_product(p1, p2)
    products = {'P1': p1, 'P2': p2, 'P3': p3,
        'P4': service.law_product(p1, p3), 'P5': service.financial_product(p1, p2, p3)}
    service.consume(products, tmp_path, mode='frozen')
    payload = deepcopy(p3['payload'])
    payload['dependencies'] = [d for d in payload['dependencies'] if not d['id'].startswith('reviewed-reference:')]
    products['P3'] = service.seal('P3', req['bundle'], p3['inputs'], payload)
    for stage in ('P4', 'P5'):
        old = products[stage]
        products[stage] = service.seal(stage, req['bundle'], {**old['inputs'], 'P3': products['P3']['sha256']}, old['payload'])
    with pytest.raises(ValueError, match='Consumed reviewed-reference dependencies differ'):
        service.consume(products, tmp_path, mode='frozen')
