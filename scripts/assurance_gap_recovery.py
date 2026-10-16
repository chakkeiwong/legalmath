"""Offline closure of the interrupted live panel; no provider dispatch."""
from pathlib import Path
import shutil
import sys
from run_assurance_gap_master import ROOT,OUT,PYTHON,read,save,receipt,checked,state,command,sha


def worker(repo,work):
    from legalmath.interpretation.assurance import challenge_panel,challenge_continuation
    from legalmath.interpretation.assurance.integration_contract import read_evidence
    repo=Path(repo);work=Path(work);base=repo/'artifacts/assurance-gap-closure/2026-09-30'
    # The full manifest includes every retained file of the failed live attempt.
    from legalmath.canonical import raw_digest
    state_value=read(base/'state.json');ref=state_value['phases']['G7'][-1]
    manifest=read_evidence(ref,repo)
    for name,expected in manifest['outputs'].items():
        if raw_digest((repo/name).read_bytes())!=expected:raise RuntimeError('Live evidence changed: '+name)
    previous=read(base/'G7/attempt-02/dossier.json')
    predecessor={'path':str((base/'G7/attempt-02/dossier.json').relative_to(repo)),
                 'sha256':sha(base/'G7/attempt-02/dossier.json')}
    snapref={'path':str((base/'G7/attempt-02/snapshot.json').relative_to(repo)),
             'sha256':sha(base/'G7/attempt-02/snapshot.json')}
    challenge_continuation.verify_predecessor(repo,previous,predecessor,snapref)
    source=base/'G7/attempt-03/investigation/challenges'
    destination=work/'recovered-panel'
    shutil.copytree(source,destination)
    packet,candidates,questions=challenge_continuation.context(repo,previous)
    result=challenge_panel.recover_partial(destination,packet,candidates,questions)
    roles={r['role'] for r in result['history'] if r['status']=='VALIDATED'}
    if roles!=set(challenge_panel.ROLES):raise RuntimeError('Both pilot roles did not validate')
    output={'status':'PARTIAL_LIVE_EXECUTION_VERIFIED','original_attempt':ref,
        'historical_predecessor':predecessor,'historical_snapshot':snapref,
        'recovered_panel':{'path':str((destination/'result.json').relative_to(repo)),
                           'sha256':sha(destination/'result.json')},
        'validated_actions':sum(r['status']=='VALIDATED' for r in result['history']),
        'failed_actions':len(result['failed_actions']),'unsubmitted_actions':22-result['journal_actions'],
        'missing_perspectives':len(result['missing_perspectives']),
        'unresolved_obligations':len(result['unresolved_obligation_ids']),
        'alternative_readings':len(result['alternative_readings']),
        'response_differences':len(result['response_differences']),
        'execution_complete':False,'new_model_calls':0,'fresh_whole_method_execution':False,
        'legal_correctness':'NOT_ESTABLISHED'}
    save(work/'recovery-result.json',output)
    return output


def execute(work):
    from run_executable_reference_master import snapshot
    target,frozen=snapshot(work,'gap-recovery-'+work.name)
    command([PYTHON,'scripts/assurance_gap_recovery.py','worker',ROOT,work],work,'recovery',cwd=target,timeout=300)
    value=read(work/'recovery-result.json')
    ref=state()['phases']['G7'][-1]
    save(OUT/'reviews'/(ref['sha256']+'.json'),{'prior':ref,'status':'PARTIAL_VERIFIED',
        'reason':'Verified offline recovery preserves 16 validated responses, three rejected calls and missing work; no new model calls.',
        'evidence':receipt(work/'recovery-result.json')})
    return value


if __name__=='__main__':
    if len(sys.argv)!=4 or sys.argv[1]!='worker':raise SystemExit('Use reviewed master')
    worker(sys.argv[2],sys.argv[3])
