"""Regression checks for misleading witnesses in a multi-series source report."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT=Path(__file__).resolve().parents[2]/'scripts/check_bond_feature_delivery.py'
spec=importlib.util.spec_from_file_location('bond_report_presentation',SCRIPT)
report=importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


def evidence(identifier,kind,text,page=1,end_page=None):
    return {'id':identifier,'kind':kind,'quote':text,'scope':'operative',
            'disposition':'applicable','origin':'contractual','document':'terms',
            'page':page,'end_page':end_page or page}


def test_reorganisation_clause_does_not_displace_direct_write_down():
    row={'id':'synthetic','answer':True,'title':'Example perpetual securities','evidence':[
        evidence('reorganisation','mandatory_common_conversion',
                 'In the event of a Newco Scheme the issuer shall ensure the Securities may be converted into ordinary shares.'),
        evidence('trigger','principal_write_down',
                 'Following a Trigger Event the principal amount of the Securities shall be written down to zero.',2,3)]}
    reason,ids=report.report_reason(row,{'terms':{}})
    assert ids==['trigger']
    assert 'PDF pp.2–3' in reason
    assert 'principal can be reduced' in reason


def test_maturity_specific_witness_and_metadata_change():
    row={'id':'synthetic','answer':False,'title':'Example 5% Notes due 2054','evidence':[
        evidence('short','cash_repayment','The 2034 Notes may be redeemed at 100% of principal.'),
        evidence('long','cash_repayment','The 2054 Notes may be redeemed at 100% of principal.') ]}
    assert report.report_witness(row)['id']=='long'
    row.update(title='Renamed issuer 5% Notes due 2034',id='unseen')
    assert report.report_witness(row)['id']=='short'


def test_wrong_series_only_cannot_supply_reason():
    row={'id':'synthetic','answer':False,'title':'Example Notes due 2054','evidence':[
        evidence('short','cash_repayment','The 2034 Notes may be redeemed at 100% of principal.')]}
    with pytest.raises(ValueError,match='No adequate summary witness'):
        report.report_witness(row)


def test_unresolved_stays_unresolved():
    row={'answer':None,'summary_reason':'Repayment unit is unresolved','evidence':[]}
    assert report.report_reason(row,{})==('Repayment unit is unresolved',[])
