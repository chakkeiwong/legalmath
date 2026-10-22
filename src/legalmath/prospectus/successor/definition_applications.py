"""Conditional applications of explicit purpose clauses in an exact source.

The registered readings are assisted. Lexical proposals do not independently
establish a legal meaning, applicability to client facts, or general recall.
"""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path

from .contracts import digest
from .definition_forms import discover_forms

PROFILE_SHA256='fd22b465f3a6345f572d647f6416ec305dd4f89849df3cc5ae268d10f09cf016'


def require(condition,message):
    if not condition:
        raise ValueError(message)


def specification(structural=False):
    if structural:
        from .structural_roles import definition_specification
        return definition_specification('applications')
    spec=json.loads(gzip.decompress(Path(__file__).with_name('definition_applications_spec.json.gz').read_bytes()))
    require(digest(spec)==PROFILE_SHA256,'Definition application registered profile changed')
    return spec


def packet(structural=False):
    spec=specification(structural)
    return {'profile':spec['profile'],'profile_sha256':digest(spec)}


def applications(text,spec,lexical):
    found={(r['start'],r['end']) for r in lexical['uses']}
    required={(r['start'],r['end']) for r in spec['occurrences'] if r['role']!='COMPOUND_COMPONENT'}
    require(found==required,'Definition application lexical coverage differs from reviewed source')
    output=[]
    for rule in spec['rules']:
        for premise in rule['premises']:
            require(text[premise['start']:premise['end']]==premise['quote'],
                    'Definition application premise differs from source')
    for occurrence in spec['occurrences']:
        row=deepcopy(occurrence)
        a,b=row['start'],row['end']
        require(text[a:b]==row['quote'],'Definition application occurrence differs from source')
        candidates=[r for r in spec['rules'] if r['group']==row['group']
                    and any(x<=a<b<=y for x,y in r['extents'])]
        active=row['role'] in {'OPERATIVE_USE','DECLARATION'}
        if active:
            require(len(candidates)==1,'Definition application scope is not uniquely supported')
            rule=candidates[0]
            row.update(rule=rule['id'],meaning=deepcopy(rule['meaning']),
                       condition=rule['condition'],remaining=[])
        else:
            reasons={
                'UNRESOLVED':'GENERAL_CAPITAL_REFERENCE_DOES_NOT_SELECT_AMOUNT',
                'COMPOUND_COMPONENT':'HOLDER_DEFINITION_DOES_NOT_GOVERN_COMPOUND',
                'STATUTORY_REFERENT':'REFERENCE_IS_NOT_PROOF_OF_AFFILIATION'}
            if row['role']=='OUTSIDE_EXPRESS_SCOPE':
                require(not candidates,'Definition application outside-scope label contradicts its extent')
                reason=('ISSUER_CALL_DATE_NOT_HOLDER_FIFTEENTH_DAY' if row['group']=='holder'
                        else 'EARLIER_CUSTODIAN_MEANING_UNRESOLVED')
            else:
                require(row['role'] in reasons,'Unsupported definition application role')
                reason=reasons[row['role']]
            row.update(rule=None,meaning=None,condition=None,remaining=[reason])
        output.append(row)
    return output


def admit(text,request,base_report):
    structural=isinstance(request,dict) and str(request.get('profile','')).endswith('.structural-v1')
    spec=specification(structural)
    require(isinstance(request,dict) and request==packet(structural),
            'Definition application requires the exact reviewed profile')
    require(base_report['bindings']==spec['bindings']
            and hashlib.sha256(text.encode()).hexdigest()==spec['bindings']['selected_text_sha256'],
            'Definition application source differs from reviewed evidence')
    from .definition_scope_evidence import check_rules
    check_rules(text,base_report['source_pieces'],spec['rules'])
    lexical=discover_forms({'text':text,'text_sha256':spec['bindings']['selected_text_sha256'],
                             'forms':spec['forms'],'regions':[[0,len(text)]]})
    rows=applications(text,spec,lexical)
    return {'version':'definition-application-supplement.v1','assistance':'EXACT_SOURCE_REVIEWED',
        'profile':spec['profile'],'profile_sha256':digest(spec),
        'bindings':deepcopy(spec['bindings']),'source_supplement':deepcopy(spec['source_supplement']),
        'rules':deepcopy(spec['rules']),'form_discovery':lexical,'applications':rows,
        'preserve_unresolved_records':deepcopy(spec['preserve_unresolved_records']),
        'original_records':62,'original_use_associations':610,'original_references':60,
        'supplemental_occurrences':1,'supplemental_record_associations':2,
        'original_record_status_changes':False,'general_recall_established':False,
        'client_facts_established':False,'historical_law_resolved':False,
        'automatic_legal_interpretation_established':False}
