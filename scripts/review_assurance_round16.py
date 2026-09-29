"""Verify the final delivery against executed receipts and preserved predecessors."""
from collections import Counter
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from resolution_support import read,save,sha,LEDGER
from legalmath.canonical import digest
from run_assurance_round16 import OUT, OLD, PHASES, audit, journal, code_binding


def check():
    audit();history=journal().report();results=read(OUT/'phase-results.json');bindings=code_binding()
    assert set(results)==set(PHASES)
    assert not any(a['status']=='RESERVED' for a in history['actions'])
    preceding=[];directories={}
    for phase in PHASES:
        row=results[phase];receipt=row['receipt'];action=history['actions'][receipt['sequence']]
        assert action['status']=='EXECUTED' and action['result_hash']==receipt['result_hash']
        assert action['spec']['inputs']['implementation']==bindings
        assert action['spec']['inputs']['preceding']==preceding
        result_path=OUT/'execution'/action['result_file'];directories[phase]=result_path.parent
        assert read(result_path)==row['result'] and row['result']['status']=='PASS'
        assert row['result']['manifest']['code_unchanged'] is True
        assert row['result']['manifest']['implementation']==bindings
        preceding.append(receipt['result_hash'])
    assert read(OUT/'next-phase-plan.json')['remaining_phases']==[]
    counts={k:sum(int(s.get(k,0)) for s in ET.parse(directories['N5']/'tests.xml').getroot().iter('testsuite'))
            for k in ('tests','failures','errors','skipped')}
    assert counts['tests']>845 and all(counts[k]==0 for k in ('failures','errors','skipped'))
    assert results['N5']['result']['output']['tests']==counts
    old=read(OLD/'remaining-work.json');remaining=read(directories['N5']/'remaining-work.json')
    assert old==remaining
    migration=read(directories['N1']/'lossless-migration.json')
    assert [r['pair'] for r in migration]==old['restored_pair_rows'] and len(migration)==232
    accepted=[r for r in migration if r['scoped_assessment']]
    assert len(accepted)==140
    for row in accepted:
        value=row['scoped_assessment']
        assert value['legacy']==row['pair']['assessment'] and value['legacy_hash']==digest(value['legacy'])
        assert set(value['dimensions'].values())=={'UNASSESSED'}
    automatic=read(directories['N1']/'automatic-followups/result.json')
    assert automatic['status']=='UNCERTAINTY_REPORTED' and automatic['journal_actions']==6
    assert automatic['live_calls']==0 and not automatic['pruned_pairs']
    assert len(automatic['batches'][0]['proposals'])==6
    assert not automatic['batches'][0]['missing_perspectives']
    java=read(directories['N3']/'results.json');built=read(directories['N3']/'build.json')
    assert len(java)==30 and sum(r['java']['boundary_status']=='REJECTED' for r in java)==17
    assert sha(Path(built['jar']))==built['manifest']['jar_sha256']
    packet=read(directories['N4']/'selected-packet.json')
    assert len(packet['packet']['units'])==4 and packet['selected_edition']['kind']=='CLEAN'
    assert packet['source_effectiveness']=='NOT_ESTABLISHED' and packet['release_eligible'] is False
    assert len(read(directories['N4']/'contamination-tests.json'))==4
    documents=read(OUT/'document-build.json');review=read(OUT/'document-review.json')
    assert review['status']=='BUILT_AND_AUTHOR_INSPECTED'
    assert documents['pdf_sha256']==review['pdf_sha256']==sha(ROOT/'docs/monograph/monograph.pdf')
    assert documents['pages']==review['pages']>=273 and documents['companion_pages']==76
    assert documents['later_pages_preserved'] and not documents['later_text_differences_excluding_page_numbers']
    for path in ('docs/proposal/proposal.pdf','docs/proposal/monograph.pdf'):
        assert sha(ROOT/path)==documents['pdf_sha256']
    for row in read(OUT/'document-render/pages.json'):
        assert sha(ROOT/row['image'])==row['sha256']
    assert review['inspected_pdf_pages']==[r['pdf_page'] for r in read(OUT/'document-render/pages.json')]
    for p in ('docs/monograph/review/document-check.json','docs/monograph/review/reader-facing/document-check.json'):
        assert read(ROOT/p)['status'] in ('PASS','PASSED')
    for name,h in read(ROOT/'docs/monograph/review/document-check.json')['source_sha256'].items():
        assert sha(ROOT/name)==h
    inclusion='\n\\input{chapters/06f-input-meaning}\n'
    for name,h in read(OUT/'baseline.json')['manuscript_files'].items():
        if Path(name).suffix not in ('.tex','.bib'):continue
        current=(ROOT/name).read_text()
        if name.endswith('/06-ensemble.tex'):current=current.replace(inclusion,'')
        assert current==(OUT/'manuscript-baseline'/name).read_text()
    earlier=read(OUT/'pre-controller-repair/manifest.json')
    for name,h in earlier['code_hashes'].items():assert sha(OUT/'pre-controller-repair'/name)==h
    repair=read(OUT/'pre-perspective-repair/review.json')
    for name,h in repair['code_hashes'].items():assert sha(OUT/'pre-perspective-repair'/name)==h
    assert any(a['spec']['stage']=='n5' and read(OUT/'execution'/a['result_file'])['status']=='FAILED'
               for a in history['actions'] if a['status']=='EXECUTED')
    data={'status':'ROUND16_ENGINEERING_DELIVERY_VERIFIED','tests':counts,'new_model_calls':0,
        'live_calls_used':len(read(LEDGER)['calls']),'phases':PHASES,
        'phase_attempts':dict(Counter(a['spec']['stage'] for a in history['actions'])),
        'legacy_assessments_preserved':140,'restored_pairs_preserved':232,
        'new_source_judgments':0,'legacy_pending_pairs':91,'legacy_unencoded_pairs':1,
        'retained_parents':len(old['parents']),'authority_questions':len(old['authority_questions']),
        'unresolved_pdf_materiality_ids':len(old['pdf_pending_ids']),
        'automatic_followups':'Six local invocations; both perspectives retained; final uncertainty report',
        'java_external_cases':30,'rejected_external_cases':17,
        'monograph_pages':documents['pages'],'companion_pages':documents['companion_pages'],
        'full_regression_directory':str(directories['N5'].relative_to(ROOT)),
        'full_regression_wall_seconds':results['N5']['result']['manifest']['wall_seconds'],
        'engineering_results_only':True,'legal_accuracy_established':False,'release_eligible':False}
    save(OUT/'post-execution-review.json',data)
    external=set(bindings)|{'scripts/review_assurance_round16.py','scripts/assurance_round16_documents.py',
        'docs/implementation/START-HERE.md','docs/monograph/README.md','docs/plans/assurance-after-round16.md',
        'docs/monograph/monograph.pdf','docs/monograph/technical-companion.pdf','docs/monograph/process-guide.pdf',
        'docs/proposal/proposal.pdf','docs/proposal/monograph.pdf','docs/proposal/technical-companion.pdf',
        'docs/monograph/chapters/06-ensemble.tex','docs/monograph/chapters/06f-input-meaning.tex',
        'docs/monograph/review/document-check.json','docs/monograph/review/reader-facing/document-check.json'}
    external|={str(p.relative_to(ROOT)) for p in (ROOT/'docs/implementation/interpretation-round16').rglob('*') if p.is_file()}
    files={str(p.relative_to(OUT)):sha(p) for p in sorted(OUT.rglob('*'))
           if p.is_file() and p.name not in ('delivery-manifest.json','.lock') and '__pycache__' not in p.parts}
    save(OUT/'delivery-manifest.json',{'status':data['status'],'files':files,
        'external_files':{p:sha(ROOT/p) for p in sorted(external)},'release_eligible':False})
    print(json.dumps(data,indent=2))
    return data


if __name__=='__main__':check()
