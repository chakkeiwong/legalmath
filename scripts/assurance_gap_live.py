"""A source-bound integrated development run within the original 500-call grant."""
from pathlib import Path
import sys
import time
from run_assurance_gap_master import ROOT,OUT,GRANT,PYTHON,save,read,receipt,sha,command


def configuration():
    from legalmath.interpretation.assurance.engine import AssuranceSettings
    from legalmath.interpretation.search.models import Settings
    return AssuranceSettings(investigate_abstractions=True,total_model_calls=18,deadline_seconds=7200,
        output_repairs=1,semantic_repair_rounds=1,max_derived_comparisons=1,
        max_documents=4,max_reference_depth=0,max_context_passes=1,max_question_partitions=2,
        max_question_replays=32,search=Settings(scheduler='uct',max_model_calls=6,max_rounds=1,
            max_candidates=6,reconstruction_required=False,timeout_seconds=300,
            max_input_bytes=200000,max_output_bytes=200000))


def runner(repo,directory,allowance):
    from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation
    from legalmath.interpretation.assurance.executable_references_v2 import PROTOCOL
    from legalmath.interpretation.search.providers import CodexProvider
    tools={'compiler':repo/'.localresources/catala-toolchain/opam-root/catala-clean-1.2.1/bin/catala',
        'upstream':repo/'.localresources/catala-toolchain/catala-0f895e048d19dbe72f24cdd6d5f3398bfe1335fa',
        'lock':repo/'docs/implementation/catala/toolchain-lock.json'}
    return CompleteInvestigation(repo,directory,CodexProvider(allowance=allowance),
        repo/'.localresources/java-toolchain/jdk-17.0.20.1+1','2026-09-30T00:00:00.000000Z',
        settings=configuration(),catala=tools,maximum_scoped_actions=8,scoped_rounds=1,
        scoped_batch_size=12,scoped_schedule='round-first',reference_protocol=PROTOCOL,
        input_profile='readable-tables.v1',machine_qualification=True,
        challenge_options={'batch_size':12,'rounds':1,'maximum_actions':22,'input_profile':'readable-challenges.v1'})


def worker(repo,work):
    from legalmath.errors import LegalMathError
    from legalmath.interpretation.assurance.grants import GrantSlice
    from legalmath.interpretation.assurance.complete_investigation import verify
    from legalmath.interpretation.assurance.evidence_identity import verify_acquisition
    repo=Path(repo);work=Path(work)
    live_grant=repo/'artifacts/assurance-new-grant/2026-09-29/grant.json'
    allowance=GrantSlice(live_grant,live_grant.parent/'gap-closure-allowance.json',48,global_ceiling=381)
    start=allowance.verify();acquisition=repo/'artifacts/assurance-gap-closure/2026-09-30/G5/attempt-02/sources/26ec22'
    source=verify_acquisition(acquisition)
    instance=runner(repo,work/'investigation',allowance)
    selected=('Determine the actor, scope and meaning of the ultimate responsibility requirement in paragraph 10 '
        'of circular 26EC22, including the effect of an outsourcing arrangement and its footnote. '
        'Preserve competing readings, distinctions between responsibility and performance, and every missing '
        'definition or authority. Other obligations in the complete circular remain context and must be accounted for; '
        'do not turn a selected control into a claim of overall compliance.')
    save(work/'live-contract.json',{'source':{'url':source['url'],'sha256':source['sha256'],'media_type':'text/html'},
        'selected_question':selected,'settings':instance.settings.model_dump(),
        'challenge_options':instance.challenge_options,'global_grant':start,'arm_maximum':48,
        'study_class':'DEVELOPMENT_EXISTING_SOURCE_NEW_METHOD','prospective_observation':False,
        'baseline':'Attempt-2 complete source and 14 retained interpretations; upstream stages retain their old method identity',
        'primary_criterion':'Actual dispatcher continuation validates both blind roles, retains full context and original spending; every unresolved obligation remains visible.',
        'veto':'Changed source or snapshot, unaccounted allowance, invalid response accepted, lost candidate or evidence.',
        'explanatory_only':['number of candidate readings','agreement','test counts','response counts'],
        'nonconclusions':['legal accuracy','statistical independence','future-source generalization']})
    result={'status':'STARTED','before':start}
    try:
        previous=repo/'artifacts/assurance-gap-closure/2026-09-30/G7/attempt-02'
        dossier=instance.continue_challenges(previous/'dossier.json',predecessor_snapshot=previous/'snapshot.json')
        save(work/'dossier.json',dossier)
        verification=verify(repo,dossier)
        result.update(status='INTEGRATED_INVESTIGATION_RECORDED',verification=verification,
            execution_complete=dossier['execution_complete'],
            challenges={k:dossier['challenges'][k] for k in ('rounds_executed','journal_actions','missing_perspectives',
                'unresolved_obligation_ids','response_differences','alternative_readings','formal_checks','followup_limit_reached')},
            legal_correctness='NOT_ESTABLISHED')
    except LegalMathError as exc:
        result.update(status='INCOMPLETE_WITH_RETAINED_EVIDENCE',error=exc.code,details=exc.details)
        if exc.code in ('E_INTEGRITY','E_AUTHORITY'):raise
    except BaseException as exc:
        result.update(status='INTERRUPTED_OR_FAILED',error=type(exc).__name__)
        raise
    finally:
        result.update(after=allowance.verify(),new_calls=allowance.verify()['used']-start['used'])
        save(work/'live-result.json',result)
    return result


def execute(work):
    from run_executable_reference_master import snapshot,material
    target,frozen=snapshot(work,'gap-live-'+work.name)
    # Code executes in the frozen snapshot. Outputs and the original grant stay
    # in the original repository, so their receipts survive snapshot removal.
    command([PYTHON,'scripts/assurance_gap_live.py','worker',ROOT,work],work,'live',cwd=target,timeout=14400)
    if any(sha(target/n)!=h for n,h in frozen['inputs'].items()):raise RuntimeError('Live snapshot changed')
    result=read(work/'live-result.json')
    result['snapshot']=str(target)
    result['study_class']='DEVELOPMENT_EXISTING_SOURCE_NEW_METHOD'
    save(work/'result.json',result)
    if result['status']!='INTEGRATED_INVESTIGATION_RECORDED':
        raise RuntimeError('Pilot did not reach the integrated challenge dossier; retain evidence and execute a causal repair')
    panel=read(work/'dossier.json')['challenges']
    roles={r['role'] for r in panel['history'] if r['status']=='VALIDATED'}
    if roles!={'structure-reader','exception-challenger'}:
        raise RuntimeError('Live pilot did not validate both reader roles; preserve result and stop expansion')
    return result


if __name__=='__main__':
    if len(sys.argv)!=4 or sys.argv[1]!='worker':raise SystemExit('Use the reviewed master wrapper')
    worker(Path(sys.argv[2]),Path(sys.argv[3]))
