"""Verify round-15 delivery without rerunning a model or rewriting old evidence."""
from collections import Counter
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from resolution_support import read,save,sha,LEDGER
from run_assurance_round15 import code_binding,validate_pair_inventory
from legalmath.canonical import digest
from legalmath.interpretation.assurance.workflow import EvidenceJournal
from legalmath.interpretation.search.providers import verify_allowance_checkpoint

OUT=ROOT/'artifacts/interpretation/round15'


def journal(path):
    b=read(path/'journal.json')['value']['binding']
    return EvidenceJournal(path,b['inputs'],maximum_actions=b['maximum_actions'],
        maximum_per_issue=b['maximum_per_issue'],deadline_seconds=b['deadline_seconds']).report()


def check():
    final=read(OUT/'final-report.json');phases=read(OUT/'phase-results.json')
    assert final['phase_results']==phases
    assert final['release_eligible'] is False and final['legal_accuracy_established'] is False
    execution=journal(OUT/'execution');model=journal(OUT/'fidelity/model/model')
    assert not any(a['status']=='RESERVED' for j in (execution,model) for a in j['actions'])
    bindings=code_binding()
    summary_repair=read(OUT/'summary-repair.json')
    assert sha(OUT/'execution/journal.json')==summary_repair['journal_sha256']
    executed_bindings=dict(bindings)
    for name,change in summary_repair['code_repairs'].items():
        assert sha(ROOT/name)==change['repaired_sha256']
        assert sha(OUT/'pre-summary-repair'/name)==change['executed_sha256']
        executed_bindings[name]=change['executed_sha256']
    for name,h in summary_repair['after'].items():assert sha(OUT/name)==h
    for phase,row in phases.items():
        receipt=row.get('receipt',row['manifest'].get('receipt'))
        action=execution['actions'][receipt['sequence']]
        assert action['status']=='EXECUTED' and action['result_hash']==receipt['result_hash']
        stored=read(OUT/'execution'/action['result_file'])
        assert stored==(row['result'] if phase=='P6' else row['manifest'])
        assert action['spec']['inputs']['implementation']==executed_bindings
        for name,h in row['manifest'].get('external_evidence',{}).items():assert sha(ROOT/name)==h
    base=read(OUT/'baseline.json');grant=read(LEDGER)
    verify_allowance_checkpoint(LEDGER,base['allowance_sha256'])
    assert grant['maximum']==500 and len(grant['calls'])<=500
    assert len(grant['calls'])==final['calls_after']
    assert grant['calls'][:487]==base['allowance_prefix']['calls']
    # Every new reservation must identify one of this round's actual requests.
    reserved=Counter(c['request_hash'] for c in grant['calls'][487:])
    actions=Counter(digest(a['spec']['inputs']['request']) for a in model['actions'])
    assert reserved==actions
    inventory=validate_pair_inventory();fidelity=phases['P1']['result']
    expected={(r['claim_id'],r['candidate_id']) for r in inventory['executable']}
    done={(r['claim_id'],r['candidate_id']) for r in fidelity['checks']}
    pending={tuple(p) for p in fidelity['pending_pair_ids']}
    assert len(done)==fidelity['completed_pairs'] and len(pending)==fidelity['pending_pairs']
    assert not done&pending and done|pending==expected and len(expected)==231
    assert len(fidelity['unencoded_rows'])==1 and len(fidelity['context_rows_retained'])==48
    assert fidelity['execution_complete']==(not pending)
    assert ('PARTIAL' in final['status'])==bool(pending)
    assert Counter(c['label'] for c in fidelity['checks'])==fidelity['label_counts']
    # The published book supersedes the old external paths. Its preserved bytes,
    # not an edited historical manifest, discharge the earlier delivery identity.
    old=read(ROOT/'artifacts/interpretation/round14/delivery-manifest.json')
    old_archive=OUT/'round14-external-baseline'
    assert read(old_archive/'manifest.json')['files']==old['external_files']
    for name,h in old['external_files'].items():assert sha(old_archive/name)==h
    for name,h in old['files'].items():assert sha(ROOT/'artifacts/interpretation/round14'/name)==h
    regression=read(OUT/'full-regression-manifest.json')
    assert regression['status']=='PASS' and regression['code_unchanged'] is True
    for name,h in regression['code_hashes'].items():assert sha(ROOT/name)==h
    suites=ET.parse(OUT/'full-regression.xml').getroot()
    counts={k:sum(int(s.get(k,0)) for s in suites.iter('testsuite')) for k in ('tests','failures','errors','skipped')}
    assert counts['failures']==counts['errors']==counts['skipped']==0
    witnesses=read(OUT/'child-witnesses/result.json')
    wmanifest=read(OUT/'child-witnesses/run-manifest.json')
    for name,h in wmanifest['files'].items():assert sha(OUT/'child-witnesses'/name)==h
    assert witnesses['case_count']==9 and witnesses['status']=='CHILD_LIMITATIONS_REPRODUCED'
    documents=read(OUT/'document-review.json')
    assert documents['status']=='BUILT_AND_AUTHOR_INSPECTED'
    assert documents['pages']>=documents['baseline_pages']==270
    assert sha(ROOT/'docs/monograph/monograph.pdf')==sha(ROOT/'docs/proposal/proposal.pdf')==documents['pdf_sha256']
    for name in ('review/document-check.json','review/reader-facing/document-check.json'):
        assert read(ROOT/'docs/monograph'/name)['status'] in ('PASS','PASSED')
    preservation=read(OUT/'page-preservation.json')
    assert preservation['post_extension_page_count_preserved']
    assert preservation['later_page_text_mismatches_excluding_page_number']==[]
    for row in read(OUT/'document-render/final/pages.json'):
        assert sha(ROOT/row['image'])==row['raster_sha256']
    result={'status':'ROUND15_ENGINEERING_DELIVERY_VERIFIED','tests':counts,
        'calls_before':487,'calls_after':len(grant['calls']),'new_reservations':sum(reserved.values()),
        'completed_pairs':len(done),'pending_pairs':len(pending),'unencoded_pairs':1,
        'model_action_status':dict(Counter(a['status'] for a in model['actions'])),
        'phase_action_status':dict(Counter(a['status'] for a in execution['actions'])),
        'summary_repair':'Exact reconstruction from unchanged immutable journal',
        'executing_code_preserved':True,'repaired_code_regression_verified':True,
        'monograph_pages':documents['pages'],'main_limit':'No independently adjudicated legal accuracy estimate',
        'prior_runtime_crash':'Retained; cause not established. Final full suite passed with timed dumps disabled.',
        'legal_accuracy_established':False,'release_eligible':False,
        'final_report_sha256':sha(OUT/'final-report.json')}
    save(OUT/'post-execution-review.json',result)
    files={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()
           and p.name not in ('delivery-manifest.json','.lock') and '__pycache__' not in p.parts}
    external=set(bindings)|{
        'scripts/assurance_round15_witnesses.py','scripts/review_assurance_round15.py',
        'scripts/repair_round15_summary.py','scripts/run_round15_regression.py',
        'scripts/assurance_round15_documents.py',
        'docs/monograph/chapters/06-ensemble.tex','docs/monograph/chapters/06e-executed-assurance.tex',
        'docs/monograph/monograph.pdf','docs/monograph/technical-companion.pdf',
        'docs/proposal/proposal.pdf','docs/proposal/monograph.pdf','docs/proposal/technical-companion.pdf',
        'docs/implementation/START-HERE.md','docs/monograph/README.md',
        'docs/plans/assurance-after-round15.md'}
    external.update(str(p.relative_to(ROOT)) for p in (ROOT/'docs/implementation/interpretation-round15').rglob('*') if p.is_file())
    save(OUT/'delivery-manifest.json',{'files':files,'external_files':{n:sha(ROOT/n) for n in sorted(external)},
        'review_sha256':sha(OUT/'post-execution-review.json'),'historical_document_bytes_preserved':True,
        'release_eligible':False})
    return result


if __name__=='__main__':print(json.dumps(check(),indent=2))
