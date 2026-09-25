from copy import deepcopy
from itertools import product
from pathlib import Path

import pytest

from legalmath.errors import LegalMathError
from legalmath.ir.evaluate import evaluate
from legalmath.interpretation.outputs import descriptor, validate_descriptor
from legalmath.interpretation.assurance.semantics import representation
from legalmath.interpretation.assurance.repair import normalized_result
from legalmath.interpretation.search.formal import bundle
from legalmath.java.manifest import build_candidate, verify_candidate
from legalmath.java.host_package import prepare_interpretation, verify_package, run
from legalmath.canonical import canonical,loads,raw_digest

AT='2026-09-24T00:00:00.000000Z'
JDK=Path('/home/chakwong/python/legalmath/.localresources/java-toolchain/jdk-17.0.20.1+1')


def inputs():
    p={'source_key':'fixture.trigger','authority':'SYNTHETIC_FIXTURE','selected_slice':'Whether three trigger conditions are satisfied',
       'units':[{'unit_id':'p1','locator':'fixture','text':'All three conditions must hold.','normative':True,'span':None}],
       'dependencies':[],'family_ids':['scope']}
    r={'local_id':'trigger','family':'scope','subject':'Fixture licensing trigger',
       'statement':'[TRUE_IS_SATISFIED] True means the three supplied trigger conditions hold; false means that conjunction does not hold.',
       'distinction':'Predicate satisfaction is distinct from compliance.', 'assumptions':[], 'questions':[],
       'citations':[{'unit_id':'p1','quote':p['units'][0]['text']}],
       'formalization':{'facts':[{'name':name,'type':'bool','meaning':meaning,'unit':'truth value','source_unit_ids':['p1'],
           'requires_judgment':True} for name,meaning in [('regulated','Assessed regulated activity'),('business','Assessed business status'),('hong_kong','Assessed territory')]],
           'scope':'true','result':'(and regulated business hong_kong)','result_type':'bool'}}
    return p,r


def snapshot(states):
    facts={}
    for name,state in zip(('regulated','business','hong_kong'),states):
        if state=='U': value={'type':'bool','status':'unknown','reason':'MISSING'}
        elif state=='C':value={'type':'bool','status':'conflict','evidence_ids':['a','b']}
        else:value={'type':'bool','status':'known','value':state=='T','evidence_ids':['a'],
            'valid_from':AT,'valid_until':None,'recorded_at':AT}
        facts[name]=value
    return {'subject_id':'fixture','facts':facts}


def test_predicate_descriptor_is_bound_to_question_reading_and_result_type():
    p,r=inputs();d=descriptor(r,p['selected_slice'])
    assert d['meaning']=='TRUE_IS_SATISFIED' and not d['release_eligible']
    assert validate_descriptor(d,r,p['selected_slice'])==d
    with pytest.raises(LegalMathError):validate_descriptor(d,r,'Does the entity comply with law?')
    bad=deepcopy(r);bad['formalization']['result_type']='integer'
    with pytest.raises(LegalMathError):descriptor(bad,p['selected_slice'])


def test_predicate_cannot_be_silently_normalized_to_prohibition():
    with pytest.raises(LegalMathError):
        normalized_result({'status':'TRUE','type':'bool','value':True},'TRUE_IS_SATISFIED')


def test_fidelity_representation_exposes_judgment_boundary_and_real_runtime():
    _,r=inputs();text=representation(r)
    assert text.startswith('Declared output convention: TRUE_IS_SATISFIED')
    assert 'Supplied classifications requiring judgment: regulated, business, hong_kong' in text
    assert 'Their assessment is not implemented by this formula' in text
    assert 'FALSE dominates UNKNOWN' in text and 'CONFLICT' in text


def test_java_and_python_match_all_64_ternary_plus_conflict_inputs(tmp_path):
    p,r=inputs();compiled=bundle(r,p,AT);cases=[]
    for states in product(('T','F','U','C'),repeat=3):
        expected='CONFLICT' if 'C' in states else 'FALSE' if 'F' in states else 'UNKNOWN' if 'U' in states else 'TRUE'
        snap=snapshot(states);actual=evaluate(compiled,snap,'selected.control',AT,AT)
        assert actual['status']==expected
        cases.append({'id':'.'.join(states),'bundle':compiled,'snapshot':snap,'rule_id':'selected.control',
                      'valid_at':AT,'known_at':AT,'expected':{'status':expected}})
    built=build_candidate(compiled,tmp_path/'java',JDK)
    checked=verify_candidate(built,cases,JDK)
    assert checked['passed'] is True


def test_java_host_package_binds_predicate_meaning_to_actual_program(tmp_path):
    p,r=inputs();compiled=bundle(r,p,AT);snap=snapshot(('T','T','T'))
    cases=[{'id':'all.true','bundle':compiled,'snapshot':snap,'rule_id':'selected.control',
            'valid_at':AT,'known_at':AT,'expected':{'status':'TRUE'}}]
    out=tmp_path/'package';source=p['units'][0]['text'].encode()
    meta=prepare_interpretation(r,p,cases,{'https://example.invalid/fixture':source},out,JDK,AT)
    assert meta['output_descriptor']['meaning']=='TRUE_IS_SATISFIED'
    assert verify_package(out)[0]==meta
    assert run(out,snap,'selected.control',AT,JDK)['status']=='TRUE'
    # Even a rehashed package cannot assign another reading's semantics to this
    # bundle; this is an internal consistency check, not an authenticity signature.
    meaning=loads((out/'package.json').read_bytes());meaning['output_descriptor']['meaning']='TRUE_IS_COMPLIANT'
    (out/'package.json').write_bytes(canonical(meaning))
    manifest=loads((out/'manifest.json').read_bytes());manifest['files']['package.json']=raw_digest((out/'package.json').read_bytes())
    (out/'manifest.json').write_bytes(canonical(manifest))
    with pytest.raises(LegalMathError):verify_package(out)
