"""Reconstruct mutable summaries from the checked immutable phase journal."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from resolution_support import read,save,sha
from legalmath.interpretation.assurance.workflow import EvidenceJournal

OUT=ROOT/'artifacts/interpretation/round15'


def main():
    destination=OUT/'summary-repair.json'
    if destination.exists():raise RuntimeError('Repair already recorded; inspect the retained result')
    previous=OUT/'pre-summary-repair'
    for name in ('phase-results.json','final-report.json','next-phase-plan.json'):
        assert sha(OUT/name)==sha(previous/name)
    b=read(OUT/'execution/journal.json')['value']['binding']
    report=EvidenceJournal(OUT/'execution',b['inputs'],maximum_actions=b['maximum_actions'],
        maximum_per_issue=b['maximum_per_issue'],deadline_seconds=b['deadline_seconds']).report()
    journal_hash=sha(OUT/'execution/journal.json');phases=read(OUT/'phase-results.json')
    changes=[]
    for phase,row in phases.items():
        receipt=row.get('receipt',row['manifest'].get('receipt'))
        action=report['actions'][receipt['sequence']]
        assert action['status']=='EXECUTED' and action['result_hash']==receipt['result_hash']
        stored=read(OUT/'execution'/action['result_file'])
        if phase=='P6':assert stored==row['result'];continue
        before=row['manifest'];assert set(before)==set(stored)
        assert {k:v for k,v in before.items() if k!='inputs'}=={k:v for k,v in stored.items() if k!='inputs'}
        assert {k:v for k,v in before['inputs'].items() if k!='preceding'}=={k:v for k,v in stored['inputs'].items() if k!='preceding'}
        assert stored['inputs']==action['spec']['inputs']
        changes.append({'phase':phase,'before_preceding':before['inputs']['preceding'],
                        'after_preceding':stored['inputs']['preceding']})
        row['manifest']=stored
    save(OUT/'phase-results.json',phases)
    final=read(OUT/'final-report.json');final['phase_results']=phases;save(OUT/'final-report.json',final)
    next_plan=read(OUT/'next-phase-plan.json');next_plan['final_report_sha256']=sha(OUT/'final-report.json');save(OUT/'next-phase-plan.json',next_plan)
    assert sha(OUT/'execution/journal.json')==journal_hash
    save(destination,{'status':'SUMMARIES_RECONSTRUCTED_FROM_IMMUTABLE_JOURNAL','changes':changes,
        'journal_sha256':journal_hash,'before_directory':str(previous.relative_to(ROOT)),
        'after':{n:sha(OUT/n) for n in ('phase-results.json','final-report.json','next-phase-plan.json')},
        'code_repairs':{n:{'executed_sha256':sha(previous/n),'repaired_sha256':sha(ROOT/n)} for n in
            ('scripts/run_assurance_round15.py','tests/assurance/test_round15.py')},
        'phase_results_changed':False,'new_model_calls':0,'release_eligible':False})
    print('Summaries repaired; immutable phase/model results unchanged')


if __name__=='__main__':main()
