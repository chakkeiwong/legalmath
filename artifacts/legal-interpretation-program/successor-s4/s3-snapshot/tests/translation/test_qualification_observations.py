"""Simulated acquisition chronology tests; not a prospective legal study."""
from copy import deepcopy
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.qualification import assurance, prospective
from tests.catala.backend_support import JDK,TOOLCHAIN
from .support import AT,fixture,snapshot
from legalmath.translation.model import from_reading


@pytest.fixture(scope='module')
def retained(tmp_path_factory):
    # Only the source-acquisition marker is simulated. Real proof/runtime checks
    # execute and the result continues to deny legal or prospective correctness.
    t,g=fixture();t['packet']['authority']='RETAINED_SOURCE'
    m=from_reading(g['readings'][0],t['packet'],AT,coverage=g['coverage'],dimensions=g['dimensions'])
    case={'id':'conditional','snapshot':snapshot(m,{'months':'7'}),'valid_at':AT,'known_at':AT}
    out=tmp_path_factory.mktemp('observed-qualification')/'run'
    report=assurance.run(m,[case],out,JDK,toolchain=TOOLCHAIN)
    assert report['summary']['status']=='QUALIFIED'
    return m,out,report


def selected(tmp_path,monkeypatch,retained,*,question=None):
    m,out,report=retained
    monkeypatch.setattr(prospective,'now',lambda:'2030-01-01T00:00:00Z')
    d=tmp_path/'window'
    frozen=prospective.freeze(d,report['identity']['method_hash'],['simulated'],ends_at='2030-03-01T00:00:00Z')
    monkeypatch.setattr(prospective,'now',lambda:'2030-02-01T00:00:00Z')
    item={'task_id':'one','family':'simulated','source_hash':report['identity']['source_hash'],
          'question_hash':question or digest(m['review']['reading']['statement']),
          'published_at':'2030-01-02T00:00:00Z','first_seen_at':'2030-01-03T00:00:00Z'}
    prospective.admit(d,frozen['window_hash'],item,method_hash=report['identity']['method_hash'])
    return d,frozen['window_hash']


def test_observation_rechecks_actual_machine_evidence_and_stays_qualified(tmp_path,monkeypatch,retained):
    m,out,_=retained;d,h=selected(tmp_path,monkeypatch,retained)
    row=prospective.observe(d,h,'one',out,m,JDK,compiler=TOOLCHAIN['compiler'])
    r=prospective.report(d,h,expected_head=row['event_hash'])
    assert (r['submitted'],r['observed'],r['pending'])==(1,1,0)
    assert r['unknown_future_legal_generalization']=='NOT_ESTABLISHED'
    assert row['summary']['legal_correctness']=='NOT_ESTABLISHED'


def test_wrong_question_cannot_reuse_other_execution(tmp_path,monkeypatch,retained):
    m,out,_=retained;d,h=selected(tmp_path,monkeypatch,retained,question='f'*64)
    with pytest.raises(LegalMathError):prospective.observe(d,h,'one',out,m,JDK,compiler=TOOLCHAIN['compiler'])
    assert prospective.report(d,h)['pending']==1


def test_repair_and_current_source_change_block_observation(tmp_path,monkeypatch,retained):
    m,out,report=retained;d,h=selected(tmp_path,monkeypatch,retained)
    prospective.repair(d,h,new_method_hash=report['identity']['method_hash'],reason='Changed candidate after seeing a counterexample')
    with pytest.raises(LegalMathError):prospective.observe(d,h,'one',out,m,JDK,compiler=TOOLCHAIN['compiler'])
    changed=deepcopy(m);changed['review']['questions']=['Unresolved amendment']
    with pytest.raises(LegalMathError):prospective.observe(d,h,'one',out,changed,JDK,compiler=TOOLCHAIN['compiler'])
