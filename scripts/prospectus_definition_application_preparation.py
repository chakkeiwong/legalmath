"""Independent exact-source application judgments; never run candidate code."""
from copy import deepcopy
from pathlib import Path
import hashlib
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts import prospectus_definition_integration as old

HERE=old.AUTH/'reviews/definition-scope-repair-289'
METHOD='scripts/prospectus_definition_application_preparation.py'


def main():
    started=time.monotonic()
    assert not (HERE/'application-spec.json.gz').exists()
    for name,value in old.read(HERE/'source-freeze.json').items():
        assert old.sha(HERE/name)==value,name
    text=(old.SOURCE/'selected-text.txt').read_text()
    spec=old.read(old.PREP/'expected-spec.json.gz')
    assert hashlib.sha256(text.encode()).hexdigest()==spec['bindings']['selected_text_sha256']
    records={r['id']:r for r in spec['records']}

    def quote(a,b):
        assert 0<=a<b<=len(text)
        return {'start':a,'end':b,'quote':text[a:b]}

    def declaration(identity):
        return [deepcopy(spec['intervals'][i]) for i in records[identity]['declarations']]

    rules=[
        {'id':'tax','record':'U06-tax-early-amount',
         'premises':declaration('U06-tax-early-amount'),
         'extents':[[11500,13468],[21298,21482]],
         'meaning':{'relation':'EQUAL','amount':'early_redemption_amount','value':'redemption_amount'},
         'condition':'Section 5(2) tax-call context; entitlement and tax facts not established'},
        {'id':'makewhole','record':'U07-makewhole-early-amount',
         'premises':declaration('U07-makewhole-early-amount'),
         'extents':[[18874,20226],[21483,23020]],
         'meaning':{'relation':'MAXIMUM','amount':'early_redemption_amount',
                    'values':['redemption_amount','discounted_market_value']},
         'condition':'Section 5(5) issuer option; valuation-date interpretation and market inputs unresolved'},
        {'id':'holder','record':'D31-holder-redemption-day',
         'premises':[quote(14052,14081),*declaration('D31-holder-redemption-day')],
         'extents':[[13468,17242]],
         'meaning':{'relation':'DATE_OFFSET','base':'last_day_of_exercise_period','calendar_days':15},
         'condition':'Section 5(3) holder option; exercise and triggering facts not established'},
        {'id':'affiliate','record':'D41-affiliate',
         'premises':declaration('D41-affiliate'),'extents':[[32176,34657]],
         'meaning':{'relation':'STATUTORY_REFERENCE','law':'Aktiengesetz','section':'15'},
         'condition':'Section 10 only; affiliation facts and historical statutory application unresolved'},
        {'id':'custodian','record':'D45-custodian',
         'premises':declaration('D45-custodian'),'extents':[[44330,45919]],
         'meaning':{'relation':'CONJUNCTION',
                    'requirements':['bank_or_recognized_financial_institution',
                                    'authorized_securities_custody','holder_account_for_these_notes'],
                    'included':'clearing_system'},
         'condition':'Preceding section 14(4) enforcement context; actual institution facts not established'}
    ]
    assert rules[2]['premises'][0]['quote']=='Für Zwecke dieses Wahlrechts:'
    by_rule={r['id']:r for r in rules}
    cases=[]

    def case(group,a,b,role,rule=None,remaining=()):
        current=by_rule.get(rule)
        cases.append({'id':group+':'+str(a), 'group':group,**quote(a,b),'role':role,
            'rule':rule,'meaning':deepcopy(current['meaning']) if current else None,
            'condition':current['condition'] if current else None,'remaining':list(remaining)})

    case('amount',10213,10243,'UNRESOLVED',remaining=('GENERAL_CAPITAL_REFERENCE_DOES_NOT_SELECT_AMOUNT',))
    case('amount',11831,11861,'OPERATIVE_USE','tax')
    case('amount',19119,19149,'OPERATIVE_USE','makewhole')
    case('amount',21403,21432,'DECLARATION','tax')
    case('amount',21547,21576,'DECLARATION','makewhole')
    case('holder',14004,14019,'OPERATIVE_USE','holder')
    case('holder',15619,15634,'DECLARATION','holder')
    # These seven source spellings are components of a different dash term.
    for a in (17433,17517,17737,19090,19202,19681,22997):
        case('holder',a,a+15,'COMPOUND_COMPONENT',
             remaining=('HOLDER_DEFINITION_DOES_NOT_GOVERN_COMPOUND',))
    for a in (17664,18238,21229):
        case('holder',a,a+15,'OUTSIDE_EXPRESS_SCOPE',
             remaining=('ISSUER_CALL_DATE_NOT_HOLDER_FIFTEENTH_DAY',))
    case('affiliate',32403,32426,'OPERATIVE_USE','affiliate')
    case('affiliate',34040,34063,'DECLARATION','affiliate')
    case('affiliate',34069,34092,'STATUTORY_REFERENT',
         remaining=('REFERENCE_IS_NOT_PROOF_OF_AFFILIATION',))
    for a in (26168,38657):
        case('custodian',a,a+9,'OUTSIDE_EXPRESS_SCOPE',
             remaining=('EARLIER_CUSTODIAN_MEANING_UNRESOLVED',))
    for a in (44711,45051):
        case('custodian',a,a+9,'OPERATIVE_USE','custodian')
    case('custodian',45657,45666,'DECLARATION','custodian')
    cases.sort(key=lambda c:(c['start'],c['group']))
    assert len(cases)==25 and len({c['id'] for c in cases})==25
    for c in cases:
        if c['rule']:
            assert any(a<=c['start']<c['end']<=b for a,b in by_rule[c['rule']]['extents'])
    preservation=[
        'D18-payment-day','D37-calculation-day','M01-interest-period',
        *[r['id'] for r in spec['records'] if 'placeholder' in r['reading'].lower()]
    ]
    prepared={'version':'definition-application-spec.v1','profile':'basf-definition-applications.v1',
        'bindings':deepcopy(spec['bindings']),'rules':rules,'cases':cases,
        'source_supplement':old.read(HERE/'source-supplement.json.gz'),
        'original_records':62,'original_use_associations':610,'original_references':60,
        'preserve_unresolved_records':list(dict.fromkeys(preservation)),
        'original_record_status_changes':False,'general_recall_established':False}
    old.save(HERE/'application-spec.json.gz',prepared)
    # Extra independently fixed cases for flaws found during the pre-run audit.
    boundary=[
        {'id':'split-prefix','text':'pre-\nAlpha Beta','expected':[]},
        {'id':'split-suffix','text':'Alpha Beta\n-extra','expected':[]},
        {'id':'soft-hyphen','text':'pre\u00adAlpha Beta','expected':[]},
        {'id':'combining-prefix','text':'\u0301Alpha Beta','expected':[]},
        {'id':'unicode-dash','text':'pre\u2013Alpha Beta','expected':[]},
        {'id':'crlf-prefix','text':'pre-\r\nAlpha Beta','expected':[]},
        {'id':'paragraph-separated-dash','text':'pre-\n\nAlpha Beta','expected':[[6,16]]}
    ]
    for c in boundary:
        assert all(c['text'][a:b]=='Alpha Beta' for a,b in c['expected'])
    old.save(HERE/'boundary-cases.json',boundary)
    old.save(HERE/'application-preparation.json',{'status':'PASS','candidate_evaluated':False,
        'expected_application_decisions':25,'additional_boundary_cases':len(boundary),
        'wall_seconds':time.monotonic()-started,'method_sha256':old.sha(ROOT/METHOD),
        'command':['.venv/bin/python','-m','scripts.prospectus_definition_application_preparation']})
    old.save(HERE/'application-expected-freeze.json',{name:old.sha(HERE/name) for name in
        ('application-spec.json.gz','boundary-cases.json','application-preparation.json')})
    print({'status':'PASS','independent_source_decisions':25,'candidate_evaluated':False})


if __name__=='__main__':
    main()
