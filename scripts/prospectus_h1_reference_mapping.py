"""Prepare and compare the finite reference view against reviewed source evidence."""
from copy import deepcopy
from pathlib import Path
from scripts import prospectus_h1_reference_map as source
from scripts import prospectus_h1_current_relationships_mapping as links

common=source.common
ROOT=common.ROOT
MODULE='src/legalmath/prospectus/h1_reference_availability.py'
WRAPPER=links.WRAPPER
TEMPLATE='.localresources/prospectus-preparation/h1-reference-closure/h1_reference_availability.py'
VERSION='bes-h1-reference-availability.v1'
ADDED={'h1_reference_availability_review','h1_reference_availability_explanation'}
CASES=('stale-prior','changed-pin','wrong-target','shifted-boundary','lost-plural-target',
    'lost-second-note-token','shifted-split-source','changed-history','invented-reconciliation',
    'topical-as-explicit','suppressed-discrepancy','missing-link-review','missing-profile')
REFUSALS={case:'H1 reference map differs from reviewed original addresses and current fields' for case in CASES}
REFUSALS.update({'stale-prior':'Pinned H1 reference profile, graph or complete prior answer changed',
    'changed-pin':'Pinned H1 reference profile, graph or complete prior answer changed',
    'invented-reconciliation':'H1 reference availability cannot prove financial or legal correctness',
    'missing-link-review':'Current H1 source relationships required for reference availability',
    'missing-profile':'H1 reference profile missing for supplied identity'})


def profile(graph, prior, audit):
    common.require(audit['status']=='FINITE_REFERENCE_ADDRESSES_AND_CURRENT_STATES_REVIEWED','Successful reference audit required')
    return {'version':VERSION,'graph_sha256':common.digest(graph),'prior_sha256':common.digest(prior),'map':deepcopy(audit['map'])}


def candidates(value):
    module=(ROOT/TEMPLATE).read_text()
    for token,replacement in {'__GRAPH_SHA256__':value['graph_sha256'],'__PRIOR_SHA256__':value['prior_sha256'],
        '__MAP_SHA256__':common.compact_digest(value['map'])}.items():
        common.require(module.count(token)==1,'Unreviewed placeholder')
        module=module.replace(token,replacement)
    wrapper=(ROOT/WRAPPER).read_text()
    changes=[('            expected_relationship_profile_sha256=None):',
        '            expected_relationship_profile_sha256=None, reference_profile=None,\n'
        '            expected_reference_profile_sha256=None):'),
        ("        return answer", "        if reference_profile is not None or expected_reference_profile_sha256 is not None:\n"
         "            raise ValueError('Current H1 source relationships required for reference availability')\n        return answer"),
        ("    return {**answer, 'h1_source_relationship_review': relationships,\n"
         "            'h1_source_relationship_explanation': h1_source_relationships.explain(relationships)}",
         "    answer = {**answer, 'h1_source_relationship_review': relationships,\n"
         "              'h1_source_relationship_explanation': h1_source_relationships.explain(relationships)}\n"
         "    if reference_profile is None:\n"
         "        if expected_reference_profile_sha256 is not None:\n"
         "            raise ValueError('H1 reference profile missing for supplied identity')\n"
         "        return answer\n"
         "    from . import h1_reference_availability\n"
         "    references = h1_reference_availability.evaluate(products['P1']['payload']['graph'],\n"
         "        answer, reference_profile, expected_profile_sha256=expected_reference_profile_sha256)\n"
         "    return {**answer, 'h1_reference_availability_review': references,\n"
         "            'h1_reference_availability_explanation': h1_reference_availability.explain(references)}")]
    for index,(old,new) in enumerate(changes):
        common.require(wrapper.count(old)==(2 if index==1 else 1),'Public wrapper baseline changed')
        wrapper=wrapper.replace(old,new)
    return {MODULE:module,WRAPPER:wrapper}


def consume(products, profiles, value, case=None):
    from legalmath.prospectus import h1_incorporation_scope as scope
    argument=deepcopy(value)
    relationships=profiles['relationships']
    relation_pin=common.digest(relationships)
    pin=None
    mutations={
        'wrong-target':lambda b:b['references'][0].update(destinations=['12']),
        'shifted-boundary':lambda b:b['registry'][0].update(end_exclusive=b['registry'][2]['heading']),
        'lost-plural-target':lambda b:next(r for r in b['references'] if r['id'].endswith(':p103:l60'))['destinations'].pop(),
        'lost-second-note-token':lambda b:next(r for r in b['references'] if r['id'].endswith(':p107:l70'))['destinations'].pop(),
        'shifted-split-source':lambda b:next(r for r in b['references'] if r['id'].endswith(':p95:l19'))['sources'].pop(),
        'changed-history':lambda b:b['historical_states'][0]['historical_flag'].update(value=True),
        'invented-reconciliation':lambda b:b['limits'].update(financial_reconciliation_established=True),
        'topical-as-explicit':lambda b:next(r for r in b['historical_states'] if r['id']=='judgments-tax-pension').update(association_kind='EXPLICIT_NUMBERED_REFERENCE'),
        'suppressed-discrepancy':lambda b:b['discrepancies'].pop(),
    }
    if case in mutations:
        mutations[case](argument['map'])
    elif case=='stale-prior':
        argument['prior_sha256']='0'*64
    elif case=='changed-pin':
        pin='0'*64
    elif case=='missing-link-review':
        relationships,relation_pin=None,None
    elif case=='missing-profile':
        pin,argument=common.digest(argument),None
    common.require(case is None or case in CASES,'Unknown reference corruption')
    return scope.consume(products,profiles['cash'],profiles['risk'],profiles['scope'],ROOT,
        expected_cash_profile_sha256=common.digest(profiles['cash']),expected_risk_profile_sha256=common.digest(profiles['risk']),
        expected_profile_sha256=common.digest(profiles['scope']),unit_profile=profiles['unit'],
        expected_unit_profile_sha256=common.digest(profiles['unit']),relationship_profile=relationships,
        expected_relationship_profile_sha256=relation_pin,reference_profile=argument,
        expected_reference_profile_sha256=pin if pin is not None else common.digest(argument))


def verify(answer, baseline, value, audit):
    common.require(set(answer)==set(baseline)|ADDED and
        {k:v for k,v in answer.items() if k not in ADDED}==baseline,'Complete065 answer changed')
    source.compare_map(value['map'],audit['map'])
    expected={'version':VERSION,'status':'SUPPLIED_REFERENCE_ADDRESS_AVAILABILITY',
        'graph_sha256':value['graph_sha256'],'prior_sha256':value['prior_sha256'],
        'profile_sha256':common.digest(value),'map_sha256':common.compact_digest(audit['map']),'map':audit['map']}
    common.require(answer['h1_reference_availability_review']==expected,'Current reference result differs')
    explanation=answer['h1_reference_availability_explanation']
    common.require(explanation=={
        'meaning':'The report references below identify printed note or policy addresses and the current readings available for them.',
        'historical_statuses':'Earlier unresolved labels describe earlier readings and remain unchanged. The following explanations identify later material and the questions it leaves open.',
        'current_states':audit['map']['historical_states'],'source_discrepancies':audit['map']['discrepancies'],
        'scope':'This supplied review covers explicit note mentions on pages51–173 and delivered statement-note fields. Implicit references and complete meaning remain outside this finite inventory.',
        'remaining':'Source authority, controlling-language priority, incorporation alternatives, clipped equity values and the individual-statement unit conflict remain unresolved. Reference availability does not establish financial reconciliation or legal effect.',
        'limits':source.LIMITS},'Current reference explanation differs')
    return {'whole_065_preserved':True,'previous_48_links_preserved':True,**audit['checks'],
        'source_truth_established':False}
