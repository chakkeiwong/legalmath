from copy import deepcopy
import gzip
import json
from pathlib import Path

import pytest

from legalmath.prospectus.successor import basf_call_references as core
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.reviewed_references import admit

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'


@pytest.fixture(scope='module')
def original():
    donor = AUTH / 'attempts/basf-meanings/attempt-019/installed-construct/products.json.gz'
    p = json.loads(gzip.decompress(donor.read_bytes()))
    packet = json.loads((AUTH / 'reviews/basf-relative-notices-270/packet.json').read_text())
    ids = {row['source']['unit'] for row in packet['references']}
    ids |= {t['source']['unit'] for row in packet['references'] for t in row['targets']}
    ids |= {'basf-base-september-2022-exchange:p120:l22',
            'basf-base-september-2022-exchange:p120:l90',
            'basf-base-september-2022-exchange:p120:l67',
            'basf-base-september-2022-exchange:p121:l22'}
    # The admission service also verifies the independently reviewed payment
    # references. Retain their sources in this reduced source fixture.
    ids |= {f'basf-base-september-2022-exchange:p113:l{n}' for n in (78, 82, 90)}
    legacy = json.loads((ROOT / 'src/legalmath/prospectus/successor/basf_legacy_references_spec.json').read_text())
    ids |= {r['source']['unit'] for r in legacy['references']}
    ids |= {r['unit'] for r in legacy['split_contexts']}
    governance = json.loads((ROOT / 'src/legalmath/prospectus/successor/basf_governance_references_spec.json').read_text())
    ids |= {r['source']['unit'] for r in governance['references']}
    ids |= {r['unit'] for r in governance['contexts']}
    g = p['P1']['payload']['graph']
    final = next(u['id'] for u in g['units'] if u['document'] == 'basf-2032-final')
    ids.add(final)
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
    graph = {**g, 'units': [u for u in g['units'] if u['id'] in raw_ids]}
    assembly = {**p['P2']['payload']['assembly'], 'units': [u for u in p['P2']['payload']['assembly']['units'] if u['unit'] in ids]}
    packet['assembly_sha256'] = digest(assembly)
    return graph, assembly, packet


def test_distinct_complete_notice_paragraphs(original):
    graph, assembly, packet = original
    deps, edges = admit(graph, assembly, packet)
    assert [len(d['targets']) for d in deps] == [16, 14]
    assert deps[0]['targets'][-1]['unit'].endswith(':p120:l66')
    assert deps[1]['targets'][-1]['unit'].endswith(':p121:l21')
    assert len(edges) == 30
    assert core.check(graph, assembly, packet)['actual_notice_compliance'] == 'UNKNOWN'


@pytest.mark.parametrize('mutation', ['swap', 'truncate', 'extend-c', 'duplicate', 'rename',
    'language', 'question', 'source', 'edition', 'use', 'boolean-offset', 'discovery'])
def test_wrong_but_locatable_references_refused(original, mutation):
    graph, assembly, packet = deepcopy(original)
    row = packet['references'][0]
    if mutation == 'swap': row['targets'] = packet['references'][1]['targets']
    elif mutation == 'truncate': row['targets'].pop()
    elif mutation == 'extend-c':
        from legalmath.prospectus.successor.occurrences import anchor
        raw = next(u for u in graph['units'] if u['id'].endswith(':p120:l67'))
        row['targets'].append({'source': anchor(raw), 'use': raw['id'], 'language': raw['language']})
    elif mutation == 'duplicate': packet['references'].append(deepcopy(row))
    elif mutation == 'rename': row['id'] = 'concealed-identity'
    elif mutation == 'language': row['language'] = 'en'
    elif mutation == 'question': row['questions'] = ['Q1']
    elif mutation == 'source': row['source'] = deepcopy(packet['references'][1]['source'])
    elif mutation == 'edition': row['source']['source_sha256'] = '0' * 64
    elif mutation == 'use': row['targets'][0]['use'] = row['from_use']
    elif mutation == 'boolean-offset': row['targets'][0]['source']['start'] = False
    elif mutation == 'discovery': row['discovery_ids'] = ['invented']
    with pytest.raises(ValueError, match='BASF relative notice|BASF relative notice reference'):
        admit(graph, assembly, packet)


def test_missing_links_are_explicit_and_consumer_rejects_hidden_uncertainty(original):
    graph, assembly, packet = original
    packet = {**packet, 'references': []}
    report = core.check(graph, assembly, packet)
    deps = core.missing_dependencies(report)
    missing = ['relative-notice:par-call-notice', 'relative-notice:early-call-notice']
    assert [d['id'] for d in deps] == missing
    semantic = {'dependencies': deps, 'questions': {q: {'unresolved': missing.copy(),
                'subquestions': {'repayment': {'unresolved': missing.copy()}}} for q in ('Q1', 'Q2')}}
    assert core.verify_consumed(graph, assembly, {'reference_admission': packet}, semantic)['missing'] == [
        'par-call-notice', 'early-call-notice']
    semantic['questions']['Q2']['subquestions']['repayment']['unresolved'].pop()
    with pytest.raises(ValueError, match='hides or invents'):
        core.verify_consumed(graph, assembly, {'reference_admission': packet}, semantic)


def test_resealed_dependency_mutation_is_not_provenance(original):
    graph, assembly, packet = original
    deps, _ = admit(graph, assembly, packet)
    semantic = {'dependencies': deps, 'questions': {q: {'unresolved': []} for q in ('Q1', 'Q2')}}
    assert core.verify_consumed(graph, assembly, {'reference_admission': packet}, semantic)['missing'] == []
    semantic['dependencies'][0]['targets'].pop()
    with pytest.raises(ValueError, match='dependencies differ'):
        core.verify_consumed(graph, assembly, {'reference_admission': packet}, semantic)


def test_missing_source_selection_cannot_remove_obligation(original):
    graph, assembly, packet = deepcopy(original)
    source_id = packet['references'][0]['from_use']
    assembly['units'] = [u for u in assembly['units'] if u['unit'] != source_id]
    with pytest.raises(ValueError, match='source selection unavailable'):
        core.check(graph, assembly, {**packet, 'references': []})


def test_excluded_branch_cannot_supply_an_operative_link(original):
    graph, assembly, packet = deepcopy(original)
    next(u for u in assembly['units'] if u['unit'] == packet['references'][0]['from_use'])['role'] = 'EXCLUDED'
    with pytest.raises(ValueError, match='inapplicable'):
        core.check(graph, assembly, packet)
