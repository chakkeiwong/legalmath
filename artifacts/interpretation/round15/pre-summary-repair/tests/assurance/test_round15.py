"""Round-15 exact-accounting and mutation-harness checks."""
from copy import deepcopy
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

from run_assurance_round15 import (
    validate_pair_inventory, pair_data, BATCH_SIZE, mutate_bundle, ROUND14_FORMAL,
    read, evaluate, AT, project, review_claims, CircuitReader,
)
from legalmath.interpretation.assurance.semantics import fidelity_request
from legalmath.errors import LegalMathError
from legalmath.interpretation.contracts import Strict
from assurance_round15_checks import exact_ratio, rational_bundle, footer_evidence


def test_round15_exact_inventory_preserves_context_and_unencoded_rows():
    inventory = validate_pair_inventory()
    assert inventory["counts"] == {
        "restored": 232, "executable": 231, "unencoded": 1,
        "assessable": 231, "historical_context": 48,
    }
    keys = lambda rows: {(r["case_id"], r["claim_id"], r["candidate_id"]) for r in rows}
    assert keys(inventory['context']) <= keys(inventory['assessable'])
    assert keys(inventory['assessable']) == keys(inventory['executable'])
    assert keys(inventory["executable"]) | keys(inventory["unencoded"]) == keys(inventory["rows"])


def test_round15_batches_never_cross_source_packets_or_invent_fidelity_pairs():
    inventory = validate_pair_inventory()
    covered = []
    for cid, (data, _) in pair_data(inventory).items():
        rows = [r for r in inventory["assessable"] if r["case_id"] == cid]
        for start in range(0, len(rows), BATCH_SIZE):
            pairs = [(r["claim_id"], r["candidate_id"]) for r in rows[start:start + BATCH_SIZE]]
            claims = review_claims(data, {p[0] for p in pairs})
            candidates = {k: data["candidates"][k] for k in {p[1] for p in pairs}}
            request = fidelity_request(data["packet"], claims, candidates, pairs)
            assert len(request["required_pairs"]) == len(pairs)
            assert all(c["relevance"] != "CONTEXT" for c in claims)
            covered.extend((cid, *p) for p in pairs)
    assert len(covered) == 231 == len(set(covered))
    assert {(r['case_id'],r['claim_id'],r['candidate_id']) for r in inventory['context']} <= set(covered)


def test_round15_declared_mutations_have_distinguishing_witnesses():
    rows = {r["id"]: r for r in read(ROUND14_FORMAL)["cases"]}
    base = rows["controlled-language.0.at"]["bundle"]
    for mutation, suffix in (
        ("or_to_and", "objective_only"),
        ("inclusive_to_strict", "at"),
        ("threshold_shift", "at"),
    ):
        snap = rows["controlled-language.0." + suffix]["snapshot"]
        original = project(evaluate(base, snap, "selected.control", AT, AT))
        changed = project(evaluate(mutate_bundle(base, mutation), snap, "selected.control", AT, AT))
        assert original != changed
        assert original == {"status": "TRUE", "type": "bool", "value": True}
        assert changed == {"status": "FALSE", "type": "bool", "value": False}


def test_round15_tokenised_binding_is_a_distinct_input_error():
    rows = {r["id"]: r for r in read(ROUND14_FORMAL)["cases"]}
    case = rows["controlled-language.0.tokenised_only"]
    wrong = deepcopy(case["snapshot"])
    wrong["facts"]["intended_va_bps"]["value"] = "1000"
    correct = project(evaluate(case["bundle"], case["snapshot"], "selected.control", AT, AT))
    changed = project(evaluate(case["bundle"], wrong, "selected.control", AT, AT))
    assert correct == {"status": "FALSE", "type": "bool", "value": False}
    assert changed == {"status": "TRUE", "type": "bool", "value": True}


@pytest.mark.parametrize('value',['9.999','10','10.001','9.999999999999','10.000000000001','-1.25'])
def test_exact_ratio_preserves_decimal_without_binary_rounding(value):
    from fractions import Fraction
    ratio=exact_ratio(value)
    assert int(ratio['va_bps_denominator'])>0
    assert Fraction(int(ratio['va_bps_numerator']),int(ratio['va_bps_denominator']))==Fraction(value)*100


@pytest.mark.parametrize('value',[10.0,True,'nan','1e3','01','0/0','1'*65])
def test_ratio_rejects_ambiguous_or_unbounded_input(value):
    with pytest.raises(LegalMathError):exact_ratio(value)


def test_fractional_boundary_runs_through_actual_ruleir():
    base=read(ROUND14_FORMAL)['cases'][0]['bundle'];b=rational_bundle(base)
    for p,expected in [('9.999999999999',False),('10',True),('10.000000000001',True)]:
        vals={'fund_manager':True,'va_objective':False,**exact_ratio(p)}
        facts={f['name']:{'type':f['type'],'status':'known','value':vals[f['name']],
            'evidence_ids':['test.fraction'],'valid_from':AT,'valid_until':None,'recorded_at':AT} for f in b['facts']}
        result=evaluate(b,{'subject_id':'test.fraction','facts':facts},'selected.control',AT,AT)
        assert result['value'] is expected
        assert result['status']==('TRUE' if expected else 'FALSE')


def footer_fixture():
    words=[{'text':s,'x0':i*10+10,'x1':i*10+19,'top':950,'bottom':960} for i,s in enumerate(['Page','1','of','7'])]
    page={'height':1000,'raster_sha256':'h','footer':{'visual_inspection':True,'raster_sha256':'h',
          'text':'Page 1 of 7','bbox':[0,940,100,970]}}
    issue={'original':{'change':{'left_tokens':['Page','1','of','7'],'right_tokens':[],'kind':'delete'}}}
    return issue,page,{'words':words}


def test_unique_footer_is_layout_and_body_numbers_are_not():
    issue,page,layout=footer_fixture()
    assert footer_evidence(issue,page,layout)['rule']=='EXACT_UNIQUE_LOCATED_PAGE_FOOTER'
    for tokens in (['not'],['10','%'],['unless'],['HK$','40','million'],['3.11'],['Page','1','of','8']):
        bad=deepcopy(issue);bad['original']['change']['left_tokens']=tokens
        assert footer_evidence(bad,page,layout) is None
    assert footer_evidence(issue,page,{'words':layout['words']*2}) is None
    bad=deepcopy(layout);bad['words'][0]['top']=500
    assert footer_evidence(issue,page,bad) is None


@pytest.mark.parametrize('code,details',[
    ('E_DEPENDENCY','HTTP 503 service unavailable'),
    ('E_DEPENDENCY','overloaded'),
    ('E_DEPENDENCY','stream disconnected'),
    ('E_RESOURCE_LIMIT','Codex call deadline'),
])
def test_transport_failure_is_one_attempt_and_stops_following_requests(tmp_path,code,details):
    class Shape(Strict): ok: bool
    class Provider:
        provider_id='fixture.round15';live=False;routing={'model':'fixture'};calls=0
        def complete(self,*args):
            self.calls+=1
            raise LegalMathError(code,details=details)
    provider=Provider();reader=CircuitReader(provider,tmp_path,{'fixture':True},maximum_actions=4)
    from run_assurance_round15 import SingleAttemptProvider
    assert isinstance(reader.provider,SingleAttemptProvider)
    assert reader.call({'request':1},Shape,lambda v:v) is None
    assert reader.call({'request':2},Shape,lambda v:v) is None
    assert provider.calls==1
    assert len(reader.provider.journal.report()['actions'])==1
    assert reader.stopped_reason.startswith('DISPATCH_BLOCKED')


def test_master_resume_reuses_completed_actions_and_rejects_changed_evidence(tmp_path,monkeypatch):
    import run_assurance_round15 as m
    from legalmath.interpretation.assurance.diversity import save
    counts={}
    def phase(name):
        def call(out):
            counts[name]=counts.get(name,0)+1
            return {'status':'FIXTURE_DONE','execution_complete':True}
        return call
    monkeypatch.setattr(m,'OUT',tmp_path)
    monkeypatch.setattr(m,'EXECUTION',tmp_path/'execution')
    monkeypatch.setattr(m,'relative',lambda p:str(p))
    monkeypatch.setattr(m,'audit',lambda:{'status':'FIXTURE_AUDIT'})
    monkeypatch.setattr(m,'code_binding',lambda:{'fixture':'same'})
    monkeypatch.setattr(m,'used',lambda:487+counts.get('P1',0))
    for name in ('P1','P2','P3','P4','P5'):monkeypatch.setattr(m,'run_'+name.lower(),phase(name))
    save(tmp_path/'baseline.json',{'fixture':True})
    first=m.execute('P5');second=m.execute('P5')
    assert first['status']==second['status']=='CHECKPOINT'
    assert counts=={p:1 for p in ('P1','P2','P3','P4','P5')}
    record=tmp_path/'execution/action-0000/result.json'
    record.write_text('{}')
    with pytest.raises(LegalMathError):m.execute('P5')
