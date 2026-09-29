from copy import deepcopy
import pytest
from legalmath.canonical import canonical,digest,loads
from legalmath.errors import LegalMathError
from legalmath.qualification import prospective as p


@pytest.fixture
def window(tmp_path,monkeypatch):
    monkeypatch.setattr(p,'now',lambda:'2030-01-01T00:00:00Z')
    directory=tmp_path/'window'
    spec=p.freeze(directory,'a'*64,['family'],ends_at='2030-03-01T00:00:00Z',development_sources=['d'*64])
    monkeypatch.setattr(p,'now',lambda:'2030-02-01T00:00:00Z')
    return directory,spec['window_hash']


def item(name='new',**kwargs):
    return {'task_id':name,'family':'family','source_hash':'b'*64,'question_hash':'c'*64,
            'published_at':'2030-01-02T00:00:00Z','first_seen_at':'2030-01-03T00:00:00Z',**kwargs}


def test_unknown_tasks_remain_in_full_denominator(window):
    d,h=window
    p.admit(d,h,item(),method_hash='a'*64)
    p.admit(d,h,item('development',source_hash='d'*64),method_hash='a'*64)
    report=p.report(d,h)
    assert (report['submitted'],report['eligible'],report['pending'],report['ineligible'])==(2,1,1,1)
    assert report['unknown_future_legal_generalization']=='NOT_ESTABLISHED'
    assert report['inventory_completeness']=='NOT_ESTABLISHED'


@pytest.mark.parametrize('extra',[{'human_label':True},{'expected':{'value':True}},{'reviewer':'lawyer'},
                                  {'rating':5},{'model_consensus':'correct'},{'approved':True}])
def test_human_and_asserted_quality_inputs_are_forbidden(window,extra):
    with pytest.raises(LegalMathError):p.admit(*window,{**item(),**extra},method_hash='a'*64)


@pytest.mark.parametrize('changes,method,reason',[
    ({'published_at':'2029-12-31T00:00:00Z'},'a'*64,'OUTSIDE_PUBLICATION_WINDOW'),
    ({'first_seen_at':'2029-12-31T00:00:00Z'},'a'*64,'INVALID_ENCOUNTER_CHRONOLOGY'),
    ({'family':'other'},'a'*64,'OUTSIDE_FROZEN_FAMILIES'),
    ({},'e'*64,'METHOD_CHANGED'),
    ({'source_hash':'d'*64},'a'*64,'DEVELOPMENT_SOURCE')])
def test_contaminated_and_ineligible_sources_are_retained_not_promoted(window,changes,method,reason):
    row=p.admit(*window,item(**changes),method_hash=method)
    assert row['status']=='INELIGIBLE' and reason in row['reasons']
    assert p.report(*window)['submitted']==1


def test_repair_preserves_old_result_and_requires_new_confirmation_window(window):
    d,h=window
    p.admit(d,h,item(),method_hash='a'*64)
    before=(d/'events/000000.json').read_bytes()
    p.repair(d,h,new_method_hash='e'*64,reason='Machine counterexample requires repair')
    row=p.admit(d,h,item('after'),method_hash='a'*64)
    assert 'WINDOW_USED_FOR_REPAIR' in row['reasons']
    assert before==(d/'events/000000.json').read_bytes()
    assert p.report(d,h)['repaired']


def test_protocol_and_event_edits_fail_external_commitment(window):
    d,h=window;p.admit(d,h,item(),method_hash='a'*64)
    path=d/'events/000000.json';event=loads(path.read_bytes());event['item']['source_hash']='e'*64
    path.write_bytes(canonical(event))
    with pytest.raises(LegalMathError):p.report(d,h)
    spec=loads((d/'freeze.json').read_bytes());spec['development_sources']=[]
    spec['window_hash']=digest({k:v for k,v in spec.items() if k!='window_hash'})
    (d/'freeze.json').write_bytes(canonical(spec))
    with pytest.raises(LegalMathError):p.report(d,h)


def test_selected_task_cannot_be_replaced(window):
    p.admit(*window,item(),method_hash='a'*64)
    with pytest.raises(LegalMathError):p.admit(*window,item(source_hash='e'*64),method_hash='a'*64)


def test_renamed_identical_source_question_cannot_inflate_eligible_count(window):
    p.admit(*window, item(), method_hash='a'*64)
    duplicate = p.admit(*window, item('renamed'), method_hash='a'*64)
    assert duplicate['status'] == 'INELIGIBLE'
    assert 'DUPLICATE_SOURCE_QUESTION' in duplicate['reasons']
    result = p.report(*window)
    assert result['submitted'] == 2 and result['eligible'] == 1 and result['ineligible'] == 1


def test_late_encounter_cannot_enter_closed_window(window, monkeypatch):
    monkeypatch.setattr(p, 'now', lambda: '2030-04-02T00:00:00Z')
    result = p.admit(*window, item(first_seen_at='2030-04-01T00:00:00Z'), method_hash='a'*64)
    assert result['status'] == 'INELIGIBLE' and 'OUTSIDE_ENCOUNTER_WINDOW' in result['reasons']


def test_different_question_is_retained_without_claiming_an_independent_source(window):
    p.admit(*window, item(), method_hash='a'*64)
    row = p.admit(*window, item('second.question', question_hash='e'*64), method_hash='a'*64)
    assert row['status'] == 'PENDING'


def test_external_event_head_detects_a_rehashed_rewritten_history(window):
    d,h=window;event=p.admit(d,h,item(),method_hash='a'*64)
    assert p.report(d,h,expected_head=event['event_hash'])['external_head_checked']
    path=d/'events/000000.json';changed=loads(path.read_bytes())
    changed['item']['source_hash']='e'*64
    changed['event_hash']=digest({k:v for k,v in changed.items() if k!='event_hash'})
    path.write_bytes(canonical(changed))
    with pytest.raises(LegalMathError):p.report(d,h,expected_head=event['event_hash'])
