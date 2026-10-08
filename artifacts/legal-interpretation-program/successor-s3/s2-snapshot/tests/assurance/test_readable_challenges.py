from copy import deepcopy
import pytest
from legalmath.canonical import canonical, digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import readable_challenges as codec, source_references
from legalmath.interpretation.assurance import challenge_panel as panel, challenge_contract as contract
from .test_challenge_contract import inputs
from .test_challenge_panel import response, decode as old_decode
from tests.search.support import FunctionProvider


def prepared():
    p,r,q,_=inputs()
    # Many retained candidates share source evidence; every alias still survives.
    r={f'candidate.c{i}':{**deepcopy(next(iter(r.values()))),'distinction':('Shared exact explanation '*20)+str(i), 'local_id':f'candidate.c{i}'} for i in range(14)}
    q={cid:deepcopy(next(iter(q.values()))) for cid in r}
    bound={'contract':contract.build(p,r,q),'formal_obligations':{}}
    selected=[o['obligation_id'] for o in bound['contract']['obligations']][:12]
    request=panel.investigation_request(bound,p,r,q,selected,panel.ROLES[0],1,None)
    expanded,_,_=source_references.prepare(request,contract.ChallengeResponse.model_json_schema())
    return expanded


def test_all_context_round_trip_and_table_tampering():
    original=prepared();wire=codec.encode(original)
    assert codec.decode(wire,expected_request_hash=digest(original))==original
    assert wire['source_packet']==original['source_packet']
    assert wire['response_schema']==original['response_schema']
    assert len(canonical(wire))<len(canonical(original))
    for defect in ('text','row','source','reference','marker','unused'):
        bad=deepcopy(wire)
        if defect=='text':bad['context_texts'][0]+=' changed'
        elif defect=='row':bad['obligations']['rows'].pop()
        elif defect=='source':bad['source_packet']['units'][0]['text']+=' changed'
        elif defect=='reference':bad['obligations']['rows'][0][0]={'text_ref':True}
        elif defect=='marker':bad['challenge_encoding']['fields'].pop()
        else:bad['context_texts'].append('Unattached instruction')
        with pytest.raises(LegalMathError):codec.decode(bad,expected_request_hash=digest(original))


def test_original_reference_shaped_object_is_rejected():
    original=prepared();original['questions']['injected']={'text_ref':0}
    with pytest.raises(LegalMathError):codec.encode(original)
