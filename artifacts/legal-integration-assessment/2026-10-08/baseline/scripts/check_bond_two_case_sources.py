#!/usr/bin/env python3
"""Reject actual-source corruption without editing the preserved originals."""
from copy import deepcopy
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from legalmath.prospectus.common import ROOT, now, read, sha, write
from legalmath.prospectus.loss_absorption_reader import analyze_issue


def main():
    started=time.monotonic()
    inventory=read(ROOT/'docs/prospectus/classification-reader-v2-repair/issue-inventory.json')
    faults=[]
    for ident in ('santander-at1-eur-2025','unilever-capital-2030'):
        original=next(i for i in inventory['issues'] if i['id']==ident)
        source_key=original['documents'][-1]['id']
        for fault in ('original_bytes','missing_page','reordered_pages','wrong_edition',
                      'wrong_issuer','omitted_dependency','missing_named_supplement'):
            issue=deepcopy(original);docs=deepcopy(inventory['documents'])
            with tempfile.TemporaryDirectory(prefix='bond-two-case-source-fault-') as tmp:
                path=Path(tmp);doc=docs[source_key]
                original_path=path/'source.pdf';text_path=path/'text.json'
                shutil.copyfile(ROOT/doc['original'],original_path)
                data=read(ROOT/doc['text'])
                doc['original']=str(original_path);doc['text']=str(text_path)
                if fault=='original_bytes':original_path.write_bytes(original_path.read_bytes()+b'altered')
                elif fault=='missing_page':data['pages'].pop(1)
                elif fault=='reordered_pages':data['pages'][1:3]=reversed(data['pages'][1:3])
                elif fault=='wrong_edition':
                    date='25 June 2025' if ident.startswith('santander') else '16 May 2025'
                    data['pages'][0]['text']=data['pages'][0]['text'].replace(date,'16 May 2024')
                    # Required cover date is checked even if text hashes are recomputed.
                    issue['documents'][-1].setdefault('required_page_markers',[]).append({'page':1,'text':date})
                elif fault=='wrong_issuer':doc['identity_markers']=['A Different Issuer Limited']
                elif fault=='omitted_dependency':docs.pop(source_key)
                elif fault=='missing_named_supplement':issue['documents'].append({'id':'required-supplement-not-retained'})
                write(text_path,data);doc['text_sha256']=sha(text_path.read_bytes())
                row=analyze_issue(issue,docs,ROOT)
                if row['answer'] is not None or row['derivation_check']['status']!='SOURCE_INCOMPLETE':
                    raise ValueError('Source fault accepted: '+ident+':'+fault)
                faults.append({'issue':ident,'fault':fault,'answer':row['answer'],
                               'status':row['derivation_check']['status'],'reason':row['open_issues']})
    output=ROOT/'docs/implementation/bond-two-case-repair/source-faults.json'
    write(output,{'status':'PASS','recorded_at':now(),'faults':faults,'wall_seconds':time.monotonic()-started,
        'command':sys.argv,'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'environment':sys.executable,'cpu_gpu':'CPU only; no GPU framework imported','seeds':'N/A deterministic',
        'inventory_sha256':sha((ROOT/'docs/prospectus/classification-reader-v2-repair/issue-inventory.json').read_bytes()),
        'plan':'docs/plans/bond-two-case-repair.md','result':str(output.relative_to(ROOT)),
        'limit':'Source integrity and required dependency rejection; no proof of English meaning or omitted-law completeness'})
    print('Rejected',len(faults),'real-source mutations; archived originals preserved.')


if __name__=='__main__':main()
