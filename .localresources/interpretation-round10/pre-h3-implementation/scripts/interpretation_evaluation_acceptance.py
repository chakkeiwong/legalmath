"""B4 complete scripted adapter study and real allowance refusal, without live calls."""
from argparse import ArgumentParser
from pathlib import Path
from types import SimpleNamespace
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from legalmath.canonical import canonical,loads,raw_digest
from legalmath.interpretation.assurance.evaluation import freeze,execute_study,execute_cli
from tests.assurance.test_evaluation import contract,cases,provider


def main(out):
    out=Path(out).resolve()
    if out.exists() or not out.is_relative_to(ROOT/'artifacts/interpretation/round4'):
        raise ValueError('Use a new round4 output directory')
    out.mkdir(parents=True);frozen=out/'frozen';study=freeze(contract(),cases(),frozen)
    jdk=ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1'
    ledger=ROOT/'artifacts/interpretation/round2/live-allowance.json';before=raw_digest(ledger.read_bytes())
    result=execute_cli(SimpleNamespace(frozen=frozen,out=out/'live-admission',jdk=jdk,allowance=ledger,
                                      total_calls=100,replay_responses=None))
    assert result['status']=='UNDER_BUDGETED' and result['required_calls']==64 and result['available_calls']==22
    summary=execute_study(frozen,out/'scripted',provider(),jdk,available_calls=64)
    assert not summary['ranking_supported'] and not summary['legal_accuracy_evaluated']
    assert all(c['missing']==0 for c in summary['counts'].values())
    assert before==raw_digest(ledger.read_bytes())
    (out/'summary.json').write_bytes(canonical({'engineering_status':'PASS','empirical_status':'UNDER_BUDGETED',
        'scripted_cases':2,'arms':4,'complete_pairs':8,'new_live_calls':0,'allowance_used':78,
        'required_live_reservation':64,'remaining_live_allowance':22,'rankings_established':False,
        'development_corpus':True,'review_cost_saving_measured':False}))
    (out/'manifest.json').write_bytes(canonical({'files':{str(p.relative_to(out)):raw_digest(p.read_bytes())
        for p in sorted(out.rglob('*')) if p.is_file() and '/work/' not in str(p)}}))
    print('B4 engineering PASS: all four adapters and hidden scoring executed; empirical study UNDER_BUDGETED, ledger unchanged.')


if __name__=='__main__':
    p=ArgumentParser(description=__doc__);p.add_argument('--out',required=True);main(p.parse_args().out)
