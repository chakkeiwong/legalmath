"""Add inspected editions without replacing the protected v1 library records."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
LIB = ROOT / 'docs/papers'
ROWS = [
 ('symboleo2020','pdfs/symboleo2020.pdf','Symboleo: Towards a Specification Language for Legal Contracts','Sharifi',2020,'Sepehr Sharifi and Alireza Parvizimosaed and Daniel Amyot and Luigi Logrippo and John Mylopoulos','https://drive.google.com/uc?export=download&id=1WXwXeLrZdaJjhSJcCrt_wBXxDvhFkq2k','10.1109/RE48521.2020.00049','IEEE International Requirements Engineering Conference 2020','Author preprint linked by official Symboleo repository; some ancillary semantics references remain anonymized'),
 ('defeasible2000','pdfs/defeasible-foundation.pdf','Representation Results for Defeasible Logic','Antoniou',2000,'Grigoris Antoniou and David Billington and Guido Governatori and Michael J. Maher','https://arxiv.org/pdf/cs/0003082','10.1145/371316.371517','arXiv:cs/0003082','Reviewed 2000 preprint; journal version published in 2001'),
 ('permissions2012','pdfs/permissions2013.pdf','Computing Strong and Weak Permissions in Defeasible Logic','Governatori',2012,'Guido Governatori and Francesco Olivieri and Antonino Rotolo and Simone Scannapieco','https://arxiv.org/pdf/1212.0079','10.1007/s10992-013-9295-1','arXiv:1212.0079','Reviewed December 2012 preprint; later journal DOI'),
 ('normative2016','pdfs/normative2016.pdf','Normative requirements for regulatory compliance: An abstract formal framework','Hashmi',2016,'Mustafa Hashmi and Guido Governatori and Moe Thandar Wynn','https://eprints.qut.edu.au/83732/23/Main.pdf','10.1007/s10796-015-9558-1','Information Systems Frontiers, 18, 429--455','Author manuscript; online publication 2015, issue 2016'),
 ('violations2006','pdfs/logicviolations.pdf','Logic of Violations: A Gentzen System for Reasoning with Contrary-To-Duty Obligations','Governatori',2006,'Guido Governatori and Antonino Rotolo','https://ojs.victoria.ac.nz/ajl/article/download/1780/6684','10.26686/ajl.v4i0.1780','Australasian Journal of Logic, 4, 193--215','Title-page publication 2006; migrated index year 2018 is not used'),
 ('eflint2020','pdfs/eflint2020.pdf','eFLINT: a Domain-Specific Language for Executable Norm Specifications','van Binsbergen',2020,'L. Thomas van Binsbergen and Lu-Chi Liu and Robert van Doesburg and Tom van Engers','https://ir.cwi.nl/pub/29922/29922.pdf','10.1145/3425898.3426958','GPCE 2020','CWI author copy'),
 ('eflintstable2025','pdfs/eflintstable2025.pdf','A Stable Model Semantics for eFLINT Norm Specifications and Model Checking Scenarios','Esterhuyse',2025,'Christopher A. Esterhuyse and Tim Müller and L. Thomas van Binsbergen','https://pure.uva.nl/ws/files/270385564/3742876.3742882.pdf','10.1145/3742876.3742882','GPCE 2025, 80--93','University repository copy with cover; distinct semantics from the earlier interpreter'),
 ('semanticcompliance2016','pdfs/legalsemantic2016.pdf','Semantic Business Process Regulatory Compliance Checking Using LegalRuleML','Governatori',2016,'Guido Governatori and Mustafa Hashmi and Ho-Pun Lam and Serena Villata and Monica Palmirani','https://inria.hal.science/hal-01572441/document','10.1007/978-3-319-49004-5_48','EKAW 2016, 746--761','HAL author manuscript'),
 ('inputoutput2000','metadata/logic-io-source','Input/Output Logics','Makinson',2000,'David Makinson and Leendert van der Torre','https://icr.uni.lu/leonvandertorre/papers/jpl00.pdf','10.1023/A:1004748624537','Journal of Philosophical Logic, 29, 383--408','Author-hosted manuscript'),
 ('legalbench2023','metadata/legalbench-source','LegalBench: A Collaboratively Built Benchmark for Measuring Legal Reasoning in Large Language Models','Guha',2023,'Neel Guha and others','https://arxiv.org/pdf/2308.11462','','arXiv:2308.11462','Reviewed v1 including detailed task and evaluation appendices; no benchmark rerun'),
 ('amending2023','pdfs/amending.pdf','Legal Contracts Amending with Stipula','Laneve',2023,'Cosimo Laneve and Alessandro Parenti and Giovanni Sartor','https://www.cs.unibo.it/~laneve/papers/HO_Stipula_llncs.pdf','','Author-hosted manuscript','2023 author-hosted edition; do not identify this PDF with the different 2024 chapter Programming Contract Amending'),
 ('liquidity2023','pdfs/liquidity.pdf','Liquidity analysis in resource-aware programming','Laneve',2023,'Cosimo Laneve','https://www.cs.unibo.it/~laneve/papers/Stipula_LiquidityFULL.pdf','10.1016/j.jlamp.2023.100889','Journal of Logical and Algebraic Methods in Programming, 135, 100889','Reviewed author preprint dated 5 October 2022; journal edition 2023'),
 ('stipulaplatform2026','pdfs/platform.pdf','The Stipula Platform: A Workbench for Programming and Analyzing Legal Contracts','Laneve',2026,'Cosimo Laneve','https://www.cs.unibo.it/~laneve/papers/StipulaPlatform.pdf','10.1007/978-3-032-12484-5_9','Formal Methods for Industrial Critical Systems','Author-hosted manuscript available September 2025; publisher chapter indexed 2026'),
]

manifest = json.loads((LIB/'manifest.json').read_text())
existing = {r['id'] for r in manifest['papers']}
bib_path = ROOT/'docs/proposal/papers.bib'
bib = bib_path.read_text()
for key,src,title,surname,year,authors,url,doi,venue,note in ROWS:
    raw=(HERE/src).read_bytes()
    assert raw.startswith(b'%PDF')
    name=re.sub(r'[/:*?"<>|]', ' - ', title)
    name=re.sub(r'\s+', ' ',name).strip()+f', {surname}({year}).pdf'
    shutil.copyfile(HERE/src,LIB/name)
    pages=int(re.search(r'^Pages:\s+(\d+)',subprocess.check_output(['pdfinfo',str(LIB/name)],text=True),re.M).group(1))
    record=dict(id=key,title=title,first_author_surname=surname,year=year,authors=authors,
                source_url=url,doi=doi,venue=venue,version_note=note,filename=name,
                sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),pages=pages,
                downloaded_on='2026-09-21',local_staging_source=str((HERE/src).relative_to(ROOT)),alternate_version_of=None)
    if key not in existing:
        manifest['papers'].append(record)
        fields={'title':'{'+title+'}','author':authors,'year':str(year),'howpublished':venue,'url':url,'note':note}
        if doi: fields['doi']=doi
        bib+='\n@misc{'+key+',\n'+',\n'.join('  '+k+' = {'+v.replace('&',r'\&')+'}' for k,v in fields.items())+'\n}\n'
    else:
        manifest['papers']=[record if r['id']==key else r for r in manifest['papers']]
manifest['paper_pdf_count']=len(manifest['papers'])
manifest['distinct_work_count']=len(manifest['papers'])-1
(LIB/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
bib_path.write_text(bib)
lines=['# Research paper library','',f"{manifest['paper_pdf_count']} PDF editions representing {manifest['distinct_work_count']} works; {sum(r['pages'] for r in manifest['papers'])} PDF pages. All seven user-supplied links are retained.",'',
'The filename convention is `Title, FirstAuthorSurname(year).pdf`. Title punctuation unsafe across filesystems is replaced by a spaced hyphen. The manifest records original titles, exact URLs, version notes, dates and SHA-256 hashes. Publication and preprint dates are distinguished; two Jurayj editions count as one work.','',
'Read the [proposal](../proposal/proposal.pdf), [original technical notes](reading-notes.md), [expanded technical notes](reading-notes-v2.md), and [search/disposition ledger](coverage.md). The ledger distinguishes inspected mechanisms, background sources and unresolved retrievals. Downloading is not counted as technical reading.','']
for r in sorted(manifest['papers'],key=lambda r:(r['first_author_surname'].lower(),r['year'],r['title'])):
    lines.append(f"- [{r['title']}]({quote(r['filename'])}) — {r['year']}; {r['version_note']}. {r['pages']} pages.")
lines+=['','Full texts are retained for local research. Public availability does not grant blanket redistribution rights. No downloaded implementation or published experiment was replayed merely by constructing this library.']
(LIB/'README.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({k:manifest[k] for k in ['paper_pdf_count','distinct_work_count']}))
