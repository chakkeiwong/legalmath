"""Fixed stage entry points for the multiple-assurance master program."""
from argparse import ArgumentParser
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\n')


def document(out):
    import fitz
    out.mkdir(parents=True,exist_ok=False)
    book=ROOT/'docs/monograph'
    before=fitz.open(book/'monograph.pdf');old_pages=len(before);before.close()
    # Build both directions of external references and all historical aliases.
    subprocess.run([sys.executable,str(ROOT/'scripts/build_reader_facing_monograph.py')],cwd=ROOT,check=True,timeout=420)
    for name in ('check_monograph.py','check_monograph_citations.py','check_monograph_mathematics.py'):
        subprocess.run([sys.executable,str(ROOT/'scripts'/name)],cwd=ROOT,check=True,timeout=180)
    result=json.loads((book/'review/reader-facing/document-check.json').read_text())
    pages=result['documents']['monograph']['pages']
    result.update(previous_pages=old_pages,current_pages=pages,proposal_alias_identical=(book/'monograph.pdf').read_bytes()==(ROOT/'docs/proposal/proposal.pdf').read_bytes())
    shutil.copyfile(book/'monograph.pdf',out/'monograph.pdf')
    shutil.copyfile(book/'review/document-check.json',out/'canonical-document-check.json')
    shutil.copytree(book/'review/revision/math-obligations',out/'math-obligations')
    save(out/'result.json',result)
    if result['status']!='PASS' or not result['proposal_alias_identical']:raise ValueError('Document acceptance failed')
    return result


def summary(out):
    out.mkdir(parents=True,exist_ok=False)
    base=ROOT/'artifacts/interpretation/round11';state=json.loads((base/'state.json').read_text())
    results={};issues=[]
    toolbase=ROOT/'.localresources/assurance-tools'
    for name in ('tool-lock.json','model-lock.json','requirements.lock'):
        shutil.copyfile(toolbase/name,out/name)
    for phase in ('M0','M1','M2','M3','M4'):
        row=state['phases'][phase]
        if row['status']!='PASSED':raise ValueError('Required predecessor absent')
        manifest=ROOT/row['attempts'][-1]['path'];data=json.loads(manifest.read_text())
        results[phase]={'manifest':str(manifest),'sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'status':data['status']}
        if phase=='M2':
            sources=json.loads((manifest.parent/'sources/result.json').read_text());issues.extend(sources['issues'])
    successor={'next_phase':'M6: source-region adjudication and host integration',
        'tasks':['Classify each retained page discrepancy against raster and source edition; preserve unresolved material regions.',
                 'Extend cvc5 from Boolean bodies to scoped full RuleIR and four-state conflict semantics under independent encoding.',
                 'Apply PIT to generated runtime/host integration, using surviving mutants as required regression cases.',
                 'Integrate the Catala worktree after its owner review and combined regression.',
                 'Run a source-family held-out live study through the existing counted provider with externally labelled references.',
                 'Specify KeY/JML obligations and acquire an eligible calibration corpus before MAPIE confidence claims.'],
        'acceptance':['No unexplained material source discrepancies','No shared-input agreement treated as English proof',
                      'Complete live calls and missing outputs recorded','Held-out unsafe-acceptance and useful coverage measured with uncertainty'],
        'refresh_from':results,'release_eligible':False}
    result={'engineering_status':'PASS','phase_evidence':results,'unresolved_issues':issues,'next_phase_plan':successor,
            'assurance_status':'UNCERTAINTY_RETAINED','model_calls':0,'legal_correctness_established':False,'release_eligible':False,
            'scope':'Selected source/tool integration plus existing regression; no production deployment'}
    save(out/'result.json',result);save(out/'next-phase-plan.json',successor)
    return result


if __name__=='__main__':
    p=ArgumentParser();p.add_argument('route',choices=['document','sources','formal','evaluation','summary']);p.add_argument('--out',required=True);args=p.parse_args()
    out=Path(args.out).resolve()
    permitted = [ROOT/'artifacts/interpretation/round11']
    if args.route == 'document': permitted.append(ROOT/'artifacts/interpretation/round12')
    if not any(out.is_relative_to(p) for p in permitted):raise ValueError('Round-local output required')
    if args.route=='document':result=document(out)
    elif args.route=='summary':result=summary(out)
    else:
        module=__import__('assurance_'+{'sources':'source','formal':'formal','evaluation':'evaluation'}[args.route]+'_routes')
        result=module.run(out)
    print(json.dumps({'route':args.route,'status':result.get('engineering_status',result.get('status')),'release_eligible':False}))
