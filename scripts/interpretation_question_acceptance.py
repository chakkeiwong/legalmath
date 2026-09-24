"""Executed B2b witness, bounded partitions and retained-source nonclaims."""
from argparse import ArgumentParser
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from legalmath.canonical import canonical,loads,raw_digest
from legalmath.interpretation.search.formal import Comparisons
from legalmath.interpretation.assurance.questions import execute_partitions,annotate_actions
from legalmath.interpretation.assurance.resolution import choose_action
from tests.assurance.test_questions import fixture
from tests.search.test_formal import AT


def main(out):
    out=Path(out).resolve()
    if out.exists() or not out.is_relative_to(ROOT/'artifacts/interpretation/round4'):
        raise ValueError('Use a new round4 output directory')
    out.mkdir(parents=True)
    checker,candidates,packet,comparisons=fixture(ROOT,out/'java')
    checked=execute_partitions(comparisons,candidates,packet,checker)
    assert checked['partitions'][0]['separated_pairs']==[['good','missing']]
    actions=annotate_actions([{'kind':'REPAIR_STAGE','issue_key':'exception','stage':'FORMALIZATION',
        'candidate_id':'missing','inputs':{}}],checked,candidates,packet,AT)
    action=choose_action(actions,set(),actions[0]['score_scope'],remaining_cost=5)
    assert action['separated_pairs']==1
    (out/'controlled-question.json').write_bytes(canonical(checked))
    (out/'scheduled-action.json').write_bytes(canonical(action))
    actual={}
    for ref in ('23EC46','24EC16'):
        root=ROOT/'artifacts/interpretation/round3/A7/attempt-08/pilot'/ref
        state=loads((root/'search-state.json').read_bytes());p=loads((root/'packet.json').read_bytes())
        c=loads((root/'candidates.json').read_bytes());at=loads((root/'request.json').read_bytes())['at']
        actual[ref]=execute_partitions(state['comparisons'],c,p,Comparisons(out/ref/'java',checker.jdk,at))
        assert actual[ref]['status']=='NO_CHECKED_DISTINCTIONS'
    (out/'retained-source-questions.json').write_bytes(canonical(actual))
    (out/'summary.json').write_bytes(canonical({'status':'PASS_WITH_SCOPE_LIMITS','new_live_calls':0,
        'executed_controlled_pair_count':1,'retained_sources_without_comparable_witnesses':list(actual),
        'legal_accuracy_evaluated':False,'actual_source_gain_claimed':False}))
    (out/'manifest.json').write_bytes(canonical({'files':{str(p.relative_to(out)):raw_digest(p.read_bytes())
        for p in sorted(out.rglob('*')) if p.is_file()}}))
    print('B2b PASS: executed Java partitions drive scheduling; retained circulars lack unconditional comparable witnesses.')


if __name__=='__main__':
    p=ArgumentParser(description=__doc__);p.add_argument('--out',required=True);main(p.parse_args().out)
