"""Source-specific maturity cash flows, independent entitlement and retained unknowns."""
from copy import deepcopy
from fractions import Fraction
import gzip
import json
from pathlib import Path

import pytest

from legalmath.prospectus.successor import contract_terms
from legalmath.prospectus.successor.contracts import digest
from scripts import prospectus_shell_maturity_checks as checks

PREP=Path(__file__).resolve().parents[2]/'docs/implementation/prospectus-execution-authority/reviews/shell-maturity-361'
NAMES=json.loads((PREP/'cases.json').read_text())


@pytest.fixture(scope='module')
def packets():
    return {name:json.loads(gzip.decompress((PREP/(name+'-packet.json.gz')).read_bytes())) for name in NAMES}


def run(packet):
    return contract_terms.scenario(packet['admitted'],packet['request']['contract_calculation'],packet['graph'],packet['assembly'])


@pytest.mark.parametrize('name',NAMES)
def test_all_cash_flows_equal_independent_frozen_integer_calculation(packets,name):
    packet=packets[name];value=run(packet)
    assert value['coupons']==packet['baseline_answer']['questions']['Q5']['value']
    assert value['cash_flows']==packet['expected']['cash_flows']
    assert value['totals']==packet['expected']['totals']
    assert value['calculation_inputs']==packet['request']['contract_calculation']
    assert value['redemption']['source_applicability']=='CONDITIONAL_ON_SUPPLIED_PROFILE'
    assert value['redemption']['source_applicability_established'] is False
    assert not value['legal_entitlement_established'] and not value['full_settlement_supported']
    assert value['actual_event']=='NOT_ESTABLISHED'
    roles={u['unit']:u['role'] for u in packet['assembly']['units']}
    groups=value['redemption']['source_occurrences']
    assert set(groups)==set(packet['request']['contract_calculation']['redemption']['source_profile']['groups'])
    for rows in groups.values():
        for row in rows:
            assert row['role']==roles[row['unit']]
    assert any(r['role']=='UNKNOWN' for r in groups['scheduled_redemption'])


@pytest.mark.parametrize('form',['global','definitive'])
def test_principal_and_coupon_entitlement_are_independent(packets,form):
    interest=run(packets[form+'-coupon-only']);principal=run(packets[form+'-principal-only'])
    neither=run(packets[form+'-excluded'])
    assert {f['kind'] for f in interest['cash_flows']}=={'COUPON'}
    assert {f['kind'] for f in principal['cash_flows']}=={'PRINCIPAL'}
    assert neither['cash_flows']==neither['totals']==[]
    regular=run(packets[form+'-plain']);holiday=run(packets[form+'-maturity-holiday'])
    assert regular['totals']==holiday['totals']
    assert holiday['redemption']['payment_date']=='2030-12-11'
    assert holiday['redemption']['additional_interest_for_payment_day_delay']=='0'
    assert {f['kind'] for f in holiday['cash_flows'] if f['payment_date']=='2030-12-11'}=={'COUPON','PRINCIPAL'}
    assert Fraction(regular['totals'][0]['total_amount'])==(Fraction('551243169.40') if form=='global' else 110249)


def test_declared_separate_definitive_recipients_are_not_one_global_allocation(packets):
    result=run(packets['definitive-two-recipients'])
    assert len(result['redemption']['transfers'])==2
    assert sorted(int(t['amount']) for t in result['redemption']['transfers'])==[100000,199000]
    assert len(result['cash_flows'])==22


def test_all_independent_adverse_packets_refuse(packets):
    packet=deepcopy(packets['global-plain']);refused=[]
    for name,bad in checks.bad_calculations(packet['request']['contract_calculation']):
        with pytest.raises(ValueError):
            contract_terms.scenario(packet['admitted'],bad,packet['graph'],packet['assembly'])
        refused.append(name)
    assert len(refused)==46


@pytest.mark.parametrize('defect',['excluded','missing','duplicate','quote','numeric-profile-offset'])
def test_rehashed_source_and_assembly_changes_do_not_validate(packets,defect):
    packet=deepcopy(packets['global-plain']);assembly=packet['assembly'];graph=packet['graph']
    source='shell-2020-base:p47:l9';row=next(u for u in assembly['units'] if u['unit']==source)
    if defect=='excluded':row['role']='EXCLUDED'
    elif defect=='missing':assembly['units'].remove(row)
    elif defect=='duplicate':assembly['units'].append(deepcopy(row))
    elif defect=='quote':next(u for u in graph['units'] if u['id']==source)['raw']='altered'
    else:packet['request']['contract_calculation']['redemption']['source_profile']['groups']['scheduled_redemption'][0]['start']=False
    admitted=packet['admitted'];admitted['assembly_sha256']=digest(assembly);admitted['graph_sha256']=digest(graph)
    packet['request']['contract_calculation']['terms_sha256']=digest(admitted)
    packet['request']['contract_calculation']['coupon_term']['terms_sha256']=digest(admitted)
    with pytest.raises(ValueError):run(packet)


@pytest.mark.parametrize('defect',['duplicate-id','duplicate-kind','numeric-order','offset-time','presentation-after-payment','extra-event','empty-reason'])
def test_payment_event_and_evidence_boundaries(packets,defect):
    packet=deepcopy(packets['global-plain']);r=packet['request']['contract_calculation']['redemption']
    if defect=='duplicate-id':r['events'][1]['id']=r['events'][0]['id']
    elif defect=='duplicate-kind':r['events'][1]['kind']='redemption_due'
    elif defect=='numeric-order':r['events'][0]['order']=False
    elif defect=='offset-time':r['events'][0]['at']='2030-12-10T00:00:00+01:00'
    elif defect=='presentation-after-payment':r['events'][1]['order']=3
    elif defect=='extra-event':r['events'].append(deepcopy(r['events'][0]))
    else:r['evidence']['events']['reason']=' '
    with pytest.raises(ValueError):run(packet)


def test_input_and_output_are_detached(packets):
    packet=deepcopy(packets['global-plain']);before=deepcopy(packet);result=run(packet)
    assert packet==before
    result['redemption']['source_profile']['groups']['final_amount'][0]['quote']='changed'
    result['redemption']['assumptions']['unamended_terms']=False
    result['calculation_inputs']['coupon_term']['premises']['holdings'][0]['principal']='1'
    assert packet==before
    assert result['coupons']['calculations'][0]['calculation_inputs']['holdings'][0]['principal']=='500000000'
    packet['request']['contract_calculation']['redemption']['events'][0]['id']='changed'
    assert result['redemption']['events'][0]['id']=='maturity-redemption_due'
