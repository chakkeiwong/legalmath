"""Construction-derived obligations and adversarial complete-reader checks."""
from copy import deepcopy
from itertools import product
import json
from pathlib import Path

import pytest

from legalmath.prospectus.common import digest
from legalmath.prospectus.loss_absorption_derivation import check
from legalmath.prospectus.loss_absorption_reader import analyze_issue, joined
from legalmath.prospectus.loss_absorption_witnesses import exact_repayment
from tests.prospectus.test_loss_absorption import fixture,ORDINARY


def read_case(tmp_path,clause,title='Example senior notes'):
    issue,docs,document=fixture(tmp_path,[ORDINARY.replace('Example senior notes',title)+' '+clause],title=title)
    row=analyze_issue(issue,docs,tmp_path)
    return row,{'document':{'text':joined(document)[0],'sha256':document['source_sha256']}}


@pytest.mark.parametrize('case',json.loads((Path(__file__).resolve().parents[2]/
    'docs/implementation/bond-loss-absorption-classification/execution/reader-gap-diagnostic.json').read_text())['cases'],ids=lambda c:c['case'])
def test_preserved_full_reader_failures(tmp_path,case):
    issue,docs,_=fixture(tmp_path,[case['text']])
    row=analyze_issue(issue,docs,tmp_path)
    obligation=case['construction_obligation']
    if obligation=='must_not_establish_positive':assert row['answer'] is not True
    elif obligation=='must_not_establish_negative':assert row['answer'] is not False
    else:assert row['answer'] is True
    assert row['derivation_check']['status']=='CHECKED'
    assert row['certified_legal_answer'] is None


@pytest.mark.parametrize('verb,modal,negated',product(['notify holders whether','confirm that','report whether'],['shall','must','will'],[False,True]))
def test_obligation_to_report_does_not_create_mechanism(tmp_path,verb,modal,negated):
    embedded='cannot be written down' if negated else 'may be converted into ordinary shares'
    row,_=read_case(tmp_path,f'The issuer {modal} {verb} the Notes {embedded}.')
    assert row['answer'] is not True


@pytest.mark.parametrize('modal,action,negated',product(['shall','will','must'],['convert into ordinary shares','be written down to zero'],[False,True]))
def test_direct_formal_action_and_polarity(tmp_path,modal,action,negated):
    # The formal construction specifies event -> action, or its explicit
    # prohibition. Test expectations are derived from this polarity slot.
    row,_=read_case(tmp_path,f'Upon a Trigger Event, the Notes {modal} '+('not ' if negated else '')+action+'.')
    if negated:assert row['answer'] is not True
    else:assert row['answer'] is True


@pytest.mark.parametrize('wording',[
    'Following insolvency, the principal repayment claim is permanently extinguished.',
    'Loss absorption of the Notes follows Schedule Z, whose provisions are unavailable.',
    'Upon a solvency trigger, holders permanently forfeit their entire claim to repayment of the face value of the Notes.',
])
def test_unknown_or_alternative_loss_wording_cannot_produce_negative(tmp_path,wording):
    row,_=read_case(tmp_path,wording)
    assert row['answer'] is not False


def test_explicit_other_series_cannot_supply_positive(tmp_path):
    title='Example Series A Notes due 2034'
    row,_=read_case(tmp_path,'Series B Notes shall automatically convert into ordinary shares.',title)
    assert row['answer'] is not True
    assert any(e['disposition']=='other_issue' for e in row['evidence'])


def test_other_maturity_cannot_supply_repayment(tmp_path):
    title='Example Notes due 2054'
    issue,docs,_=fixture(tmp_path,['Example issuer. '+title+'. The Notes are unsecured obligations. '
        'The 2034 Notes will be redeemed at maturity at 100% of principal.'],title=title)
    assert analyze_issue(issue,docs,tmp_path)['answer'] is None


def test_definition_in_foreign_section_cannot_supply_common_shares(tmp_path):
    issue,docs,_=fixture(tmp_path,[ORDINARY+' The Notes shall convert into Conversion Shares.',
        'Conversion Shares means ordinary shares.'],operative=[[1,1]])
    assert analyze_issue(issue,docs,tmp_path)['answer'] is None


def test_selected_definition_replays_without_importing_foreign_meaning(tmp_path):
    issue,docs,_=fixture(tmp_path,[ORDINARY+' The Notes shall convert into Conversion Shares. '
        'Conversion Shares means ordinary shares.', 'Conversion Shares means preference shares.'],operative=[[1,1]])
    row=analyze_issue(issue,docs,tmp_path)
    assert row['answer'] is True
    assert row['derivation_check']['status']=='CHECKED'


@pytest.mark.parametrize('definition',[
    'Conversion Shares means preference shares.',
    'Conversion Shares means ordinary shares. Conversion Shares means preference shares.',
    'A conversion price is computed using ordinary shares.',
])
def test_missing_or_conflicting_share_definition(tmp_path,definition):
    row,_=read_case(tmp_path,'The Notes shall convert into Conversion Shares. '+definition)
    assert row['answer'] is None


@pytest.mark.parametrize('left,right,currency',product(['1,000','999.99'],['1,000','500'],['£','€']))
def test_exact_redemption_units(left,right,currency):
    text=f'Calculation Amount: £{left}. Final Redemption Amount: {currency}{right} per Calculation Amount.'
    result=exact_repayment(text)
    assert (result['status']=='equal') is (left==right and currency=='£')


def test_coupon_and_issue_price_are_not_calculation_amount():
    assert exact_repayment('Issue Price: £1,000. Coupon Amount: £1,000. Final Redemption Amount: £1,000 per Calculation Amount.')['status']=='unresolved'


@pytest.mark.parametrize('wording',[
    'The holder may waive a default in the payment of interest.',
    'Each missing coupon must be surrendered for payment.',
    'The Notes rank equally with additional notes having the same terms on waivers and amendments.',
])
def test_other_rights_and_missing_coupons_do_not_invent_principal_loss(tmp_path,wording):
    row,_=read_case(tmp_path,wording)
    assert row['answer'] is False


def test_unsupported_principal_waiver_blocks_negative(tmp_path):
    row,_=read_case(tmp_path,'Holders waive their rights to principal repayment upon the specified event.')
    assert row['answer'] is None


@pytest.mark.parametrize('class_name',['ordinary shares','preference shares'])
def test_settlement_conversion_class_is_material(tmp_path,class_name):
    row,_=read_case(tmp_path,'Upon a Trigger Event, each Note shall, subject to Condition 8, be redeemed and settled '
        '(the "Conversion") on the Conversion Date by (x) the delivery of new fully paid '+class_name+' to the depository.')
    assert (row['answer'] is True) is (class_name=='ordinary shares')


def test_resolution_power_binds_principal_action(tmp_path):
    row,_=read_case(tmp_path,'Holders consent to the exercise of any UK bail-in power by the relevant UK authority '
        'which may result in (i) the reduction or cancellation of all, or a portion, of the principal amount of, or interest on, the Notes.')
    assert row['answer'] is True


@pytest.mark.parametrize('wording',[
    'The issue of other securities may reduce the amount recoverable by Noteholders.',
    'The Notes shall be cancelled after delivery of the Conversion Shares to holders.',
    'The nominal amount of the Notes may reduce the number of securities available for trading.',
])
def test_intransitive_reduction_and_post_settlement_cancellation_are_not_write_down(tmp_path,wording):
    row,_=read_case(tmp_path,wording)
    assert row['facts']['principal_write_down'] is not True


@pytest.mark.parametrize('definition',['the outstanding principal amount of the Notes','unpaid interest on the Notes'])
def test_defined_bail_in_amount_requires_principal(definition,tmp_path):
    row,_=read_case(tmp_path,'Holders agree to the exercise of the Bail-In Power by the Relevant Resolution Authority, '
        'which may include and result in any of the following: (1) the reduction of all, or a portion, of the Amounts Due. '
        'Amounts Due means '+definition+'.')
    assert (row['answer'] is True) is ('principal' in definition)


def test_release_is_exchange_for_defined_common_shares(tmp_path):
    row,_=read_case(tmp_path,'On the trigger date all of our obligations under the Securities will be irrevocably and automatically '
        'released in consideration of our issuance of the Conversion Shares. Conversion Shares means ordinary shares. '
        'Conversion Shares are sold in an offer.')
    assert row['answer'] is True


@pytest.mark.parametrize('alias',['Specified Denominations','Minimum Denomination'])
def test_explicit_unit_alias_required(alias):
    text='Specified Denominations: EUR 100,000. Calculation Amount (see Conditions): '+alias+'. Final Redemption Amount: EUR 100,000 per Calculation Amount.'
    assert (exact_repayment(text)['status']=='equal') is (alias=='Specified Denominations')


def test_unrelated_identifier_between_cash_fields_is_not_a_field_binding(tmp_path):
    issue,docs,document=fixture(tmp_path,['Example issuer. Example senior notes. The Notes are unsecured obligations. '
        'Calculation Amount: £1,000. Optional redemption benchmark bond DE000BU2Z015. '
        'Final Redemption Amount: £1,000 per Calculation Amount.'])
    issue['identifiers']=['XS3201918409']
    row=analyze_issue(issue,docs,tmp_path)
    assert row['answer'] is False
    damaged=deepcopy(row)
    e=next(e for e in damaged['evidence'] if 'repayment_derivation' in e)
    e['repayment_derivation']['amount']='500'
    with pytest.raises(ValueError):check(damaged,{'document':{'text':joined(document)[0],'sha256':document['source_sha256']}})


def test_cross_page_unit_fields_support_repayment(tmp_path):
    issue,docs,_=fixture(tmp_path,['Example issuer. Example senior notes. The Notes are unsecured obligations. Calculation Amount: £1,000.',
        'Final Redemption Amount: £1,000 per Calculation Amount.'])
    row=analyze_issue(issue,docs,tmp_path)
    assert row['answer'] is False
    assert any('repayment_derivation' in e for e in row['evidence'])


@pytest.mark.parametrize('field',['answer','issue','source','mechanism','explanation','definition','premise','evidence_link'])
def test_independent_derivation_rejects_mutations(tmp_path,field):
    row,docs=read_case(tmp_path,'Upon a Trigger Event, the Notes shall convert into Conversion Shares. Conversion Shares means ordinary shares.')
    assert row['answer'] is True
    damaged=deepcopy(row)
    witness=next(e for e in damaged['evidence'] if e.get('semantic_witness'))
    if field=='answer':damaged['answer']=False
    elif field=='issue':witness['issue_id']='different'
    elif field=='source':witness['quote']=witness['quote'].replace('shall','may')
    elif field=='mechanism':witness['kind']='principal_write_down'
    elif field=='explanation':damaged['summary_reason']='No mechanism.'
    elif field=='definition':witness['semantic_witness']['definitions'][0]['quote']='Conversion Shares means preference shares'
    elif field=='premise':damaged['facts']['mandatory_common_conversion']=False
    else:damaged['derivation']['evidence_ids']=[]
    # Rehash deliberate forgeries too: a content hash is not semantic checking.
    old=witness['id'];witness['id']=digest({k:v for k,v in witness.items() if k!='id'})[:24]
    damaged['derivation']['evidence_ids']=[witness['id'] if i==old else i for i in damaged['derivation']['evidence_ids']]
    damaged['derivation']['sha256']=digest({k:v for k,v in damaged['derivation'].items() if k!='sha256'})
    with pytest.raises(ValueError):check(damaged,docs)
