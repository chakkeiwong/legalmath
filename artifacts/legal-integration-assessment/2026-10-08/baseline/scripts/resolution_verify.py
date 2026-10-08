"""Independent installed evaluators on the freshly generated policies."""
import os
import subprocess
from resolution_support import *
from legalmath.java.manifest import build_candidate,verify_candidate


def run(out):
    source=ROOT/read(OUT/'phase-results.json')['R5']['directory']
    data=read(source/'formal-input.json');cases=data['cases']
    if not cases:
        value={'status':'NO_EXECUTABLE_NEW_POLICY','comparisons':0,'release_eligible':False}
        save(out/'result.json',value);return value
    save(out/'formal-input.json',data)
    argv=[str(ROOT/'.localresources/assurance-tools/venv/bin/python'),'-m',
          'legalmath.interpretation.assurance.sidecar','formal-cases',
          '--input',str(out/'formal-input.json'),'--output',str(out/'formal-result.json')]
    subprocess.run(argv,cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT/'src'),'CUDA_VISIBLE_DEVICES':'-1'},check=True,timeout=180)
    cvc5=read(out/'formal-result.json')
    if cvc5['status']!='PASS':raise LegalMathError('E_INTEGRITY')
    groups={}
    for c in cases:groups.setdefault(digest(c['bundle']),[]).append(c)
    catala=[]
    for ident,selected in groups.items():
        built=build_candidate(selected[0]['bundle'],out/'catala'/ident,JDK,backend='catala',catala_toolchain={
            'compiler':ROOT/'.localresources/catala-toolchain/opam-root/catala-clean-1.2.1/bin/catala',
            'upstream':ROOT/'.localresources/catala-toolchain/catala-0f895e048d19dbe72f24cdd6d5f3398bfe1335fa',
            'lock':ROOT/'docs/implementation/catala/toolchain-lock.json'})
        verified=verify_candidate(built,selected,JDK)
        catala.append({'build':built,'verification':verified,'cases':len(selected)})
    value={'status':'DIVERSE_EXECUTABLE_AGREEMENT','comparisons':len(cases),'cvc5':cvc5,'catala':catala,
           'source_interpretation_proved':False,'release_eligible':False}
    save(out/'result.json',value);return value
