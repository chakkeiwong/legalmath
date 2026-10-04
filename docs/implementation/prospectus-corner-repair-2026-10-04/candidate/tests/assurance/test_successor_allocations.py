from pathlib import Path
import sys
import pytest
from legalmath.errors import LegalMathError
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from assurance_successor_allocations import effective_allocation,amend_slice
from run_assurance_successor import save,read,sha


def fixture(tmp_path):
    d=tmp_path/'study';d.mkdir();grant=tmp_path/'grant.json';grant.write_text('controlled grant')
    budget={'arm_ceiling':60,'global_ceiling':500,'reserve_for_evaluation':40}
    save(d/'allocation.json',budget);review=tmp_path/'review.md';review.write_text('Controlled reviewed repair')
    xml=tmp_path/'tests.xml';xml.write_text('<testsuite tests="2" failures="0" errors="0" skipped="0"/>')
    amendment={'original_allocation_sha256':sha(d/'allocation.json'),'old_arm_ceiling':60,'new_arm_ceiling':120,
        'refund_reservations':False,'equal_ceiling_for_both_arms':True,
        'review':{'path':review.name,'sha256':sha(review)},'focused_tests':{'path':xml.name,'sha256':sha(xml)}}
    save(d/'allocation-amendment-001.json',amendment)
    return d,grant,budget,amendment


def test_slice_amendment_preserves_every_old_reservation_and_is_idempotent(tmp_path):
    d,grant,budget,_=fixture(tmp_path);budget=effective_allocation(d,budget,tmp_path)
    path=d/'single-allowance.json';old={'grant_hash':sha(grant),'maximum':60,
        'reservations':[{'request_hash':'a'*64,'global_slot':1,'status':'GLOBALLY_RESERVED'}]}
    save(path,old);original=path.read_bytes();amend_slice(path,budget,grant);new=read(path)
    assert new['maximum']==120 and new['reservations']==old['reservations']
    assert Path(new['planning_amendment']['prior_path']).read_bytes()==original
    before=path.read_bytes();amend_slice(path,budget,grant);assert path.read_bytes()==before
    new['reservations']=[];save(path,new)
    with pytest.raises(LegalMathError):amend_slice(path,budget,grant)


def test_altered_review_or_unbounded_amendment_is_rejected(tmp_path):
    d,grant,budget,a=fixture(tmp_path);a['new_arm_ceiling']=501;save(d/'allocation-amendment-001.json',a)
    with pytest.raises(LegalMathError):effective_allocation(d,budget,tmp_path)
    a['new_arm_ceiling']=120;save(d/'allocation-amendment-001.json',a)
    (tmp_path/'review.md').write_text('Changed after reviewed hash')
    with pytest.raises(LegalMathError):effective_allocation(d,budget,tmp_path)


def test_native_reviewed_slice_retains_all_spent_slots_and_resumes(tmp_path):
    d,grant,budget,_=fixture(tmp_path);save(grant,{'ledger':'allowance.json'})
    save(tmp_path/'allowance.json',{'calls':[{'request_hash':'a'*64}]})
    budget=effective_allocation(d,budget,tmp_path)
    p=d/'new-task-allowance.json';value={'grant_hash':sha(grant),'maximum':120,
        'reservations':[{'request_hash':'a'*64,'global_slot':1,'status':'GLOBALLY_RESERVED'}]}
    save(p,value);before=p.read_bytes();amend_slice(p,budget,grant);after=read(p)
    assert after['reservations']==value['reservations'] and after['maximum']==120
    assert after['planning_amendment']['origin']=='CREATED_WITH_REVIEWED_LIMIT'
    assert Path(after['planning_amendment']['prior_path']).read_bytes()==before
    stable=p.read_bytes();amend_slice(p,budget,grant);assert p.read_bytes()==stable


@pytest.mark.parametrize('mutation',['wrong_reservation','duplicate_reservation','missing_migration'])
def test_native_slice_cannot_hide_detached_or_migrated_history(tmp_path,mutation):
    d,grant,budget,_=fixture(tmp_path);save(grant,{'ledger':'allowance.json'})
    save(tmp_path/'allowance.json',{'calls':[{'request_hash':'a'*64}]})
    budget=effective_allocation(d,budget,tmp_path);p=d/'arm-allowance.json'
    row={'request_hash':'a'*64,'global_slot':1,'status':'GLOBALLY_RESERVED'}
    value={'grant_hash':sha(grant),'maximum':120,'reservations':[row]}
    if mutation=='wrong_reservation':row['request_hash']='b'*64
    elif mutation=='duplicate_reservation':value['reservations'].append(dict(row))
    else:save(d/'allocation-history/arm-allowance-old.json',{'maximum':60})
    save(p,value)
    with pytest.raises(LegalMathError):amend_slice(p,budget,grant)
