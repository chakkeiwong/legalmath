"""Verify the retained ordinary-command run and its zero-dispatch resume."""
from argparse import ArgumentParser
from pathlib import Path
from legalmath.canonical import loads,digest,raw_digest
from legalmath.interpretation.assurance.public_issue import run_public_issue
from legalmath.interpretation.assurance.checkpoints import check_manifest
from legalmath.interpretation.assurance.monitor import save

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/'artifacts/interpretation/round7/live-allowance.json'


def audit(out):
    directory=ROOT/'artifacts/interpretation/round10/issue'
    public=loads((ROOT/'examples/interpretation-assurance/declared-issue.json').read_bytes())
    before=LEDGER.read_bytes()
    report=run_public_issue(public,directory,LEDGER,ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1',resume=True)
    if LEDGER.read_bytes()!=before:raise ValueError('A completed resume consumed another call')
    result=report['result']
    if result['profile']!='declared-predicate-methods.v2':raise ValueError('Wrong method version')
    if result['status']!='COMPLETE' or report['release_eligible'] or report['legal_accuracy_evaluated']:
        raise ValueError('Unsupported completion or release claim')
    compared=loads((directory/report['executed_comparison']).read_bytes())
    if compared['candidates_hash']!=digest(result['merged']['candidates']):raise ValueError('Changed candidate comparison')
    for rows in compared['outputs'].values():
        for row in rows:
            if row['python']!=row['java']:raise ValueError('Java/Python discrepancy')
    if len(compared['behavior_groups'])>1 and (result['cycles']!=1 or report['status']!='UNCERTAINTY_RETAINED'):
        raise ValueError('Behavioral disagreement did not trigger reconsideration and uncertainty')
    value={'status':'PASSED','public_hash':digest(public),'model_calls':report['model_calls'],
        'zero_additional_calls_on_resume':True,'allowance_hash':raw_digest(before),
        'reconsideration_cycles':result['cycles'],'behavior_groups':result['behavior_groups'],
        'java_cases':result['java_cases'],'uncertainty_status':report['status'],
        'method_manifest_hash':digest(check_manifest(directory/'work')),
        'legal_accuracy_evaluated':False,'release_eligible':False}
    save(Path(out),value);print(value)


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__);parser.add_argument('--out',required=True)
    audit(parser.parse_args().out)
