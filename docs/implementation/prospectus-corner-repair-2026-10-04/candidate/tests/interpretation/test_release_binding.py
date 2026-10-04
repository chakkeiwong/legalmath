from copy import deepcopy
import pytest
from legalmath.interpretation import Interpretations
from legalmath.interpretation.controller import Controller
from legalmath.interpretation.review import MeaningReview, guard
from legalmath.interpretation.reports import Reports
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from tests.helpers import prepare_release
from .test_controller import config


def ready_investigation(db,root,tmp_path,case,packet):
    prepared=prepare_release(db,root,tmp_path,case,approve=False)
    s=Interpretations(db);r=s.create('author','interpretation.create',packet)
    proposal=dict(source_packet_hash=r['source_packet_hash'],source_unit_ids=['p10','fn1'],family_ids=['literal','alternative'],subject_unit='Synthetic customer',
        controlled_language='Synthetic financial condition only',bundle_hash=prepared['state']['bundle_hash'],assumptions=[],arguments=[],parent_id=None,revision_reason='Explicit synthetic test scope')
    ctl=Controller(s);ctl.configure('author','cfg',r['run_id'],config(proposal),verification_hashes=[prepared['build']['verification_report_hash']])
    report=ctl.drive(r['run_id'])
    assert report['run_status']=='READY_FOR_REVIEW'
    c=s.read('meaning',r['run_id'])['records']['candidate'][0]
    return s,r,c,report,prepared


def approve(s,r,c,report):
    return MeaningReview(s).decide('meaning','interpretation.accept',r['run_id'],c['candidate_id'],digest(c),digest(report),r['source_packet_hash'],'ACCEPT_MEANING','Scoped synthetic example is consistent','No claim of real circular interpretation accuracy',['p10','fn1'])


def test_positive_release_and_source_invalidation(db,root,tmp_path,case,packet):
    s,r,c,report,p=ready_investigation(db,root,tmp_path,case,packet)
    bh=c['bundle_hash'];lc=p['lifecycle'];state=p['state']
    with pytest.raises(LegalMathError): lc.transition('meaning','old-api-bypass',bh,'approve_meaning',state['revision'],manifest_hash=p['manifest'])
    approve(s,r,c,report)
    state=lc.transition('meaning','m-review',bh,'approve_meaning',state['revision'],manifest_hash=p['manifest'])
    state=lc.transition('engineer','e-review',bh,'approve_engineering',state['revision'],manifest_hash=p['manifest'])
    release=p['releases'].release('engineer','release',bh,p['manifest'],state['revision'],case['known_at'])
    exported=p['releases'].export_java(release['release_hash'],tmp_path/'export')
    assert (tmp_path/'export/interpretation-reviews.json').is_file()
    from legalmath.java.manifest import run_java
    actual=run_java(tmp_path/'export/policy.jar',[p['case']],root/'.localresources/java-toolchain/jdk-17.0.20.1+1')
    assert actual[0]['status']==p['case']['expected']['status']
    packet=deepcopy(packet);packet['units'][1]['text']='Changed source footnote without changing the encoded predicate.'
    s.invalidate_source('meaning','changed-footnote',packet['source_key'],packet,'New source version')
    with pytest.raises(LegalMathError): p['releases'].export_java(release['release_hash'],tmp_path/'stale-export')
    from legalmath.review.lifecycle import scope_key
    with db.connect() as con:
        with pytest.raises(LegalMathError): p['releases'].select(con,scope_key(db.get(con,p['app']['applicability_hash'])),case['valid_at'],case['known_at'])
    assert Reports(s).verify('meaning',r['run_id'])==digest(report)  # History remains intact.


def test_exact_hash_and_authority(db,root,tmp_path,case,packet):
    s,r,c,report,p=ready_investigation(db,root,tmp_path,case,packet)
    args=(r['run_id'],c['candidate_id'],digest(c),digest(report),r['source_packet_hash'],'ACCEPT_MEANING','Because','Objection',['p10'])
    with pytest.raises(LegalMathError): MeaningReview(s).decide('author','forge',*args)
    bad=list(args);bad[3]='0'*64
    with pytest.raises(LegalMathError): MeaningReview(s).decide('meaning','stale',*bad)
    approve(s,r,c,report)
    # A new bound incomplete run must not be hidden by the approved old run.
    next_run=s.create('author','second-run',packet)
    proposal={k:c[k] for k in ('source_packet_hash','source_unit_ids','family_ids','subject_unit','controlled_language','bundle_hash','assumptions','arguments','parent_id','revision_reason')}
    s.propose('author','new-bind',next_run['run_id'],proposal)
    with db.connect() as con:
        with pytest.raises(LegalMathError): guard(db,con,c['bundle_hash'])


def test_report_omission_detected(db,root,tmp_path,case,packet):
    s,r,c,report,p=ready_investigation(db,root,tmp_path,case,packet)
    with db.transaction() as con:
        s._save(con,'report',{**report,'candidate_ids':[]})
    with pytest.raises(LegalMathError): Reports(s).verify('meaning',r['run_id'])
    with pytest.raises(LegalMathError): approve(s,r,c,report)
