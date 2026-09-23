"""Whole-round offline acceptance; new evidence, preserved historical oracles."""
import argparse
from copy import deepcopy
import importlib.util
from itertools import product
import json
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from legalmath.canonical import canonical,digest,loads,raw_digest
from legalmath.storage import Database
from legalmath.review.lifecycle import Lifecycle
from legalmath.review.releases import Releases
from legalmath.sources.intake import import_source
from legalmath.sources.dependencies import record_dependency
from legalmath.interpretation import Interpretations
from legalmath.interpretation.controller import Controller
from legalmath.interpretation.actions import Actions
from legalmath.interpretation.reports import Reports
from legalmath.interpretation.review import MeaningReview,guard
from legalmath.interpretation.contracts import reference_policy
from legalmath.interpretation.service import later
from legalmath.interpretation.comparison import compare_candidates
from legalmath.java.manifest import build_candidate,run_java
from legalmath.storage.archive import export_history,import_history
from legalmath.errors import LegalMathError
from tests.helpers import prepare_release,IDENTITIES

JDK=ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1'


def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(canonical(value))


def blocked(fn):
    try: fn()
    except LegalMathError as e: return e.code
    raise AssertionError('Expected a block')


def members(p):
    return {role:{'adapter':'scripted','proposals':[] if role=='inventory' else [deepcopy(p)]} for role in ('inventory','normative','controlled-language','alternatives')}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);out=Path(parser.parse_args().out)
    out.mkdir(parents=True,exist_ok=False)
    db=Database(out/'database');lc=Lifecycle(db);lc.register(IDENTITIES);s=Interpretations(db)
    # Import utilities, not the historical verification command: that command checks old runtime hashes.
    ex=ROOT/'examples/second-circular-23ec46';sys.path.insert(0,str(ex))
    from verify import request,FIELDS,AT
    from truth_oracle import expected_status
    bundle=loads((ex/'gift-control.bundle.json').read_bytes());oracle=loads((ex/'oracle.json').read_bytes());freeze=loads((ex/'oracle-freeze.json').read_bytes())
    assert raw_digest((ex/'oracle.json').read_bytes())==freeze['oracle_sha256']
    raw=(ex/'source-fetched.json').read_bytes();text=(ex/'source.txt').read_text()
    with db.transaction() as con:
        src=import_source(db,con,'23EC46',raw,'application/json',freeze['official_url'],freeze['recorded_at_utc'].replace('+00:00','Z'),authority='RETAINED_PUBLIC_SOURCE')
        for dep in ('code.paragraph3.11','code.faq1'):
            record_dependency(db,con,dict(from_revision_id=src['revision_id'],locator=dep,target_revision_id=None,relation='references',resolution_status='unresolved',resolution_note='Versioned authority is still missing'))
    real_bh=lc.create('author','real.bundle',bundle)['bundle_hash']
    packet=dict(source_key='sfc.23ec46.paragraph10',authority='RETAINED_SOURCE',selected_slice='Paragraph 10 gift prohibition; unreviewed classification',
        units=[dict(unit_id=span['id'],locator=span['id'],text=text[span['start']:span['end']],normative=True,span=span) for span in bundle['source_spans']],
        dependencies=[dict(dependency_id=d,source_hash=None) for d in ('code.paragraph3.11','code.faq1')],family_ids=['specific-product','product-type'])
    r=s.create('author','real.run',packet)
    proposal=dict(source_packet_hash=r['source_packet_hash'],source_unit_ids=[u['unit_id'] for u in packet['units']],family_ids=packet['family_ids'],subject_unit='Incentive component',
        controlled_language='Gift and (specific product promotion or product-type promotion), unless fee discount only',bundle_hash=real_bh,assumptions=[],arguments=[],parent_id=None,revision_reason='Retained manually authored candidate')
    for issue_id in bundle['interpretations'][0]['issue_ids']:
        s.raise_issue('author','real.'+issue_id,r['run_id'],'DEFINITION',[],[],issue_id,'Unreviewed legal issue from retained second-circular candidate')
    ctl=Controller(s);ctl.configure('author','real.cfg',r['run_id'],members(proposal));real_report=ctl.drive(r['run_id'])
    assert len(real_report['missing_dependency_ids'])==2
    assert len(real_report['material_unresolved_issue_ids'])==7  # Five legal issues plus two missing sources.
    with db.connect() as con:
        assert lc.state(con,real_bh)['state']=='DRAFT'
        assert con.execute('SELECT count(*) FROM issues WHERE bundle_hash=? AND resolved=0',(real_bh,)).fetchone()[0]==5
        assert blocked(lambda:guard(db,con,real_bh))=='E_RELEASE_BLOCKED'
    dump(out/'real-circular-report.json',s.read('meaning',r['run_id']))

    # Repair demonstration uses the real retained words with visibly synthetic executable scope.
    synthetic=deepcopy(bundle);synthetic['bundle_id']='synthetic.gift.correct'
    for i in synthetic['interpretations']: i.update(basis='synthetic_test',issue_ids=[],statement='Synthetic encoding test; no legal meaning approval')
    mutant=deepcopy(synthetic);mutant['bundle_id']='synthetic.gift.omitted-type';mutant['rules'][0]['body']['args'][1]=deepcopy(mutant['rules'][0]['body']['args'][1]['args'][0])
    old=lc.create('author','mutant.bundle',mutant)['bundle_hash'];new=lc.create('author','correct.bundle',synthetic)['bundle_hash']
    p=deepcopy(packet);p.update(source_key='synthetic.gift.repair',dependencies=[])
    rr=s.create('author','repair.run',p);oldp={**proposal,'source_packet_hash':rr['source_packet_hash'],'bundle_hash':old,'controlled_language':'Gift linked only to a specific product; type route omitted'}
    c=s.propose('author','repair.seed',rr['run_id'],oldp)
    discrepancy=s.raise_issue('author','repair.discrepancy',rr['run_id'],'FORMAL_MISMATCH',['fund.p10'],[c['candidate_id']],'Does product-type promotion also trigger the prohibition?','Omitted explicit alternative in paragraph 10')
    corrected={**oldp,'bundle_hash':new,'parent_id':c['candidate_id'],'controlled_language':proposal['controlled_language'],'revision_reason':'Restore the explicit product-type disjunct in paragraph 10'}
    ctl.configure('author','repair.cfg',rr['run_id'],members(oldp),[dict(adapter='scripted',proposals=[corrected])])
    # Frozen independent-representation oracle is reused without rewriting its expected outcomes.
    cases=[request(synthetic,x['id'],{**oracle['defaults'],**x['overrides']},x['expected']) for x in oracle['cases']]
    cases += [request(synthetic,'table.'+''.join(states).lower(),dict(zip(FIELDS,states)),expected_status(dict(zip(FIELDS,states)))) for states in product('TFU',repeat=6)]
    rel=Releases(db);build=rel.build('engineer','repair.build',new,out/'repair-java',JDK,cases)
    oldbuild=build_candidate(mutant,out/'omitted-java',JDK)
    wrong=run_java(oldbuild['jar'],cases[:22],JDK,oldbuild['class_name']);detected=[x['id'] for x,y in zip(cases,wrong) if x['expected']['status']!=y['status']]
    assert 'g02' in detected
    repair_report=ctl.drive(rr['run_id']);cs=s.read('meaning',rr['run_id'])['records']['candidate'];fixed=[x for x in cs if x['bundle_hash']==new][0]
    # Comparison operates before a report in a fresh explicit investigation, retaining a distinguishing witness.
    cr=s.create('author','comparison.run',{**p,'source_key':'synthetic.gift.comparison'})
    ca=s.propose('author','comparison.a',cr['run_id'],{**oldp,'source_packet_hash':cr['source_packet_hash']})
    cb=s.propose('author','comparison.b',cr['run_id'],{**corrected,'source_packet_hash':cr['source_packet_hash'],'parent_id':None})
    comparison=compare_candidates(s,'author',cr['run_id'],ca['candidate_id'],cb['candidate_id'],synthetic['rules'][0]['id'],{f['name']:{'states':['T','F','U']} for f in synthetic['facts']},AT,AT,java_jar=oldbuild['jar'],jdk=JDK)
    assert comparison['result']['status']=='COUNTEREXAMPLE'
    dump(out/'repair-evidence.json',dict(report=repair_report,initial_hash=digest(c),repaired_hash=digest(fixed),compiled_mutant_detected_by=detected,named_cases=22,exhaustive_cases=729,comparison=comparison,interpretation=s.read('meaning',rr['run_id'])))

    # A fully resolved synthetic scenario exercises actual separate meaning and engineering roles.
    base=loads((ROOT/'docs/specs/v0.1/fixtures/decision-cases.json').read_bytes())['cases'][0]
    positive_db=Database(out/'positive-database');prepared=prepare_release(positive_db,ROOT,out/'positive',base,approve=False)
    ps=Interpretations(positive_db);sp=dict(source_key='synthetic.financial',authority='SYNTHETIC_FIXTURE',selected_slice='Synthetic financial subcondition',units=[dict(unit_id='financial',locator='Synthetic condition',text='Either declared threshold suffices.',normative=True,span=None)],dependencies=[],family_ids=['literal'])
    pr=ps.create('author','i.create',sp);pp=dict(source_packet_hash=pr['source_packet_hash'],source_unit_ids=['financial'],family_ids=['literal'],subject_unit='Synthetic customer',controlled_language='Either declared threshold suffices',bundle_hash=prepared['state']['bundle_hash'],assumptions=[],arguments=[],parent_id=None,revision_reason='Synthetic workflow demonstration')
    pc=Controller(ps);pc.configure('author','i.cfg',pr['run_id'],members(pp),verification_hashes=[prepared['build']['verification_report_hash']]);report=pc.drive(pr['run_id']);assert report['run_status']=='READY_FOR_REVIEW'
    candidate=ps.read('meaning',pr['run_id'])['records']['candidate'][0]
    MeaningReview(ps).decide('meaning','i.accept',pr['run_id'],candidate['candidate_id'],digest(candidate),digest(report),pr['source_packet_hash'],'ACCEPT_MEANING','Synthetic condition reviewed','Independent legal accuracy is outside this fixture',['financial'])
    state=prepared['state'];plc=prepared['lifecycle'];bh=state['bundle_hash']
    for caller in ('meaning','engineer'):
        role='meaning' if caller=='meaning' else 'engineering'
        state=plc.transition(caller,'i.approve.'+caller,bh,'approve_'+role,state['revision'],manifest_hash=prepared['manifest'])
    released=prepared['releases'].release('engineer','i.release',bh,prepared['manifest'],state['revision'],base['known_at'])
    prepared['releases'].export_java(released['release_hash'],out/'java-export')
    # A separately compiled host calls the generated policy class through its public interface.
    java_source='public class ExternalHost { public static void main(String[] args) throws Exception { System.out.print('+prepared['build']['class_name']+'.evaluate(java.nio.file.Files.readString(java.nio.file.Path.of(args[0])),args[1],args[2],args[3],"replay")); }}'
    (out/'ExternalHost.java').write_text(java_source)
    dump(out/'host-snapshot.json',prepared['case']['snapshot'])
    subprocess.run([str(JDK/'bin/javac'),'-cp',str(out/'java-export/policy.jar'),'-d',str(out),str(out/'ExternalHost.java')],check=True,capture_output=True,timeout=30)
    host=subprocess.run([str(JDK/'bin/java'),'-cp',str(out)+':'+str(out/'java-export/policy.jar'),'ExternalHost',str(out/'host-snapshot.json'),base['rule_id'],base['valid_at'],base['known_at']],capture_output=True,timeout=30)
    (out/'host-stderr.log').write_bytes(host.stderr)
    host.check_returncode()
    host_result=loads(host.stdout);assert host_result['status']==base['expected']['status'];dump(out/'host-result.json',host_result)
    # Export/restore before source invalidation; tokens remain disabled in the portable copy.
    archive=out/'history.zip';export_history(positive_db,archive);restored=import_history(archive,out/'restored');assert restored.verify()
    assert Interpretations(restored).read('meaning',pr['run_id'])==ps.read('meaning',pr['run_id'])
    updated=deepcopy(sp);updated['units'][0]['text']+=' Changed footnote, same current Boolean expression.'
    ps.invalidate_source('meaning','i.invalidate',sp['source_key'],updated,'Retained source changed')
    assert blocked(lambda:prepared['releases'].export_java(released['release_hash'],out/'stale'))=='E_RELEASE_BLOCKED'

    # Cancellation/failure report and last-slot race evidence, independent of the Java example.
    ambiguous=deepcopy(pp);ar=s.create('author','ambiguity.run',{**sp,'source_key':'synthetic.ambiguity'});ambiguous.update(source_packet_hash=ar['source_packet_hash'],bundle_hash=None,assumptions=[dict(assumption_id='definition',statement='Which product type classification applies?',provenance_refs=[],status='DISPUTED')])
    configs=members(ambiguous);repairs=[dict(adapter='scripted',proposals=[{**ambiguous,'revision_reason':'Investigate source wording '+str(i)}]) for i in range(3)]
    ctl.configure('author','ambiguity.cfg',ar['run_id'],configs,repairs);ambiguity_report=ctl.drive(ar['run_id']);assert ambiguity_report['processing_stop']=='NO_PROGRESS' and ambiguity_report['rounds_issued']==2
    cancelled=s.create('author','cancel.run',{**sp,'source_key':'synthetic.cancel'});Reports(s).cancel('author','cancel',cancelled['run_id']);assert s.read('meaning',cancelled['run_id'])['run']['status']=='CANCELLED'
    failed=s.create('author','failure.run',{**sp,'source_key':'synthetic.failure'});fp={**pp,'source_packet_hash':failed['source_packet_hash'],'bundle_hash':None};fc=members(fp);fc['alternatives']['adapter']='malformed';ctl.configure('author','failure.cfg',failed['run_id'],fc);failure_report=ctl.drive(failed['run_id']);assert failure_report['missing_initial_roles']==['alternatives']
    race=s.create('author','race.run',{**sp,'source_key':'synthetic.race'},{**reference_policy(),'max_actions_total':4,'max_resolution_rounds':10,'max_actions_per_issue_root':10})
    with db.transaction() as con:
        value=s._run(con,race['run_id']);value['status']='RESOLVING';s._save_run(con,value)
    issue=s.raise_issue('author','race.issue',race['run_id'],'DEFINITION',[],[],'Unresolved question','Unknown definition');actions=Actions(s)
    def reserve(n):
        try: return actions.reserve(race['run_id'],kind='REPAIR',issue_id=issue['issue_id'],inputs=[race['source_packet_hash']],question='Question '+str(n))
        except LegalMathError: return None
    for i in range(3): assert reserve(i)
    with ThreadPoolExecutor(2) as pool: raced=list(pool.map(reserve,[3,4]))
    assert sum(v is not None for v in raced)==1
    action=next(v for v in raced if v);owned=actions.claim(race['run_id'],action['action_id'],'worker.old');actions.dispatch(race['run_id'],action['action_id'],'worker.old',owned['fencing_token'])
    at=s.clock();s.clock=lambda:later(at,31);actions.recover(race['run_id']);assert not actions.complete(race['run_id'],action['action_id'],'worker.old',owned['fencing_token'],{'success':True})
    assert s.read('meaning',race['run_id'])['run']['actions_issued']==4
    dump(out/'bounded-uncertainty.json',dict(ambiguity=s.read('meaning',ar['run_id']),failure=s.read('meaning',failed['run_id']),race=s.read('meaning',race['run_id'])))
    dump(out/'local-identities.json',IDENTITIES)
    summary=dict(status='PASSED',authority='LOCAL_SYNTHETIC',real_circular_run_id=r['run_id'],repair_run_id=rr['run_id'],ambiguity_run_id=ar['run_id'],positive_run_id=pr['run_id'],positive_release_hash=released['release_hash'],
        named_cases=22,exhaustive_cases=729,compiled_omission_detected=True,java_external_host=True,source_change_blocked=True,last_slot_reservations=1,dispatch_refund=0,archive_restored=True,real_circular_open_legal_issues=5,real_circular_missing_dependencies=2,
        english_accuracy_measured=False,independent_legal_review=False,bank_ready=False)
    dump(out/'result.json',summary);print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
