"""Assemble the inspected public-source library; no network or model calls."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / '.localresources/literature-review'
LIB = ROOT / 'docs/papers'

# Identity fields are checked against the downloaded title pages, not inferred
# from citation-provider rankings. Notes distinguish preprint and journal years.
ROWS = [
 ('catala2021','../literature/catala-2021.pdf','Catala: A Programming Language for the Law','Merigoux',2021,'Denis Merigoux and Nicolas Chataing and Jonathan Protzenko','https://arxiv.org/pdf/2103.03198v2','10.1145/3473582','Proceedings of the ACM on Programming Languages, 5 (ICFP)','arXiv v2, 2 July 2021'),
 ('sergot1986','../literature/sergot-1986-british-nationality-act.pdf','The British Nationality Act as a Logic Program','Sergot',1986,'M. J. Sergot and F. Sadri and R. A. Kowalski and F. Kriwaczek and P. Hammond and H. T. Cory','https://www.doc.ic.ac.uk/~rak/papers/British%20Nationality%20Act.pdf','10.1145/5689.5920','Communications of the ACM, 29(5), 370--386','Author-hosted scan'),
 ('arc2025','2511.09008.pdf','A Neurosymbolic Approach to Natural Language Formalization and Verification','An',2025,'Chenyang An and others','https://arxiv.org/pdf/2511.09008v2','','arXiv:2511.09008','First posted 2025; reviewed v2, 13 July 2026'),
 ('slaw2024','2401.14511.pdf','Automated legal reasoning with discretion to act using s(LAW)','Arias',2024,'Joaquín Arias and Mar Moreno-Rebato and José A. Rodríguez-García and Sascha Ossowski','https://arxiv.org/pdf/2401.14511','10.1007/s10506-023-09376-5','Artificial Intelligence and Law','2024 arXiv copy; journal first published online in 2023'),
 ('jurayj2026','aaai-41212.pdf','Language Models and Logic Programs for Trustworthy Tax Reasoning','Jurayj',2026,'William Jurayj and Nils Holzenberger and Benjamin Van Durme','https://ojs.aaai.org/index.php/AAAI/article/download/41212/45173','10.1609/aaai.v40i45.41212','Proceedings of AAAI, 40(45), 38688--38698','Published proceedings copy'),
 ('jurayj2025extended','aaai-extended.pdf','Language Models and Logic Programs for Trustworthy Tax Reasoning','Jurayj',2025,'William Jurayj and Nils Holzenberger and Benjamin Van Durme','https://arxiv.org/pdf/2508.21051v3','','arXiv:2508.21051','Alternate extended version of jurayj2026, v3, 5 February 2026; first posted 2025'),
 ('stipula2021','2110.11069.pdf','Pacta sunt servanda: legal contracts in Stipula','Crafa',2021,'Silvia Crafa and Cosimo Laneve and Giovanni Sartor','https://arxiv.org/pdf/2110.11069','','arXiv:2110.11069','Reviewed three-author 2021 preprint; later journal version has a different author list'),
 ('stipulakey2025','2509.20421.pdf','Formal Verification of Legal Contracts: A Translation-based Approach (Extended Version)','Hähnle',2025,'Reiner Hähnle and Cosimo Laneve and Adele Veschetti','https://arxiv.org/pdf/2509.20421v2','','arXiv:2509.20421','Extended version, v2, 26 September 2025'),
 ('reachability2026','springer-00841.pdf','Clause-reachability is undecidable in legal contracts','Delzanno',2026,'Giorgio Delzanno and Cosimo Laneve and Arnaud Sangnier and Gianluigi Zavattaro','https://link.springer.com/content/pdf/10.1007/s10009-026-00841-5.pdf','10.1007/s10009-026-00841-5','International Journal on Software Tools for Technology Transfer, 28, 255--275','Published 19 March 2026; June issue'),
 ('dates2024','date-arithmetic.pdf','Formalizing Date Arithmetic and Statically Detecting Ambiguities for the Law','Monat',2024,'Raphaël Monat and Aymeric Fromherz and Denis Merigoux','https://link.springer.com/content/pdf/10.1007/978-3-031-57267-8_16.pdf','10.1007/978-3-031-57267-8_16','Programming Languages and Systems (ESOP 2024)','Publisher open-access chapter'),
 ('cutecat2025','cutecat.pdf','CUTECat: Concolic Execution for Computational Law','Goutagny',2025,'Pierre Goutagny and Aymeric Fromherz and Raphaël Monat','https://link.springer.com/content/pdf/10.1007/978-3-031-91121-7_2.pdf','10.1007/978-3-031-91121-7_2','Programming Languages and Systems (ESOP 2025)','Publisher open-access chapter'),
 ('contractcheck2025','consistency-contracts.pdf','Automated consistency analysis for legal contracts','Khoja',2025,'Alan Khoja and Martin Kölbl and Stefan Leue and Rüdiger Wilhelmi','https://link.springer.com/content/pdf/10.1007/s10506-025-09456-8.pdf','10.1007/s10506-025-09456-8','Artificial Intelligence and Law','Publisher version'),
 ('eflint2026','eflint.pdf','Reflections on the design, applications and implementations of the normative specification language eFLINT','van Binsbergen',2026,'L. Thomas van Binsbergen and Christopher A. Esterhuyse and Tim Müller','https://arxiv.org/pdf/2511.12276v3','10.1016/j.cola.2026.101411','Journal of Computer Languages','Reviewed arXiv v3, 4 August 2026; journal title differs slightly; first preprint 2025'),
 ('crafa2022','legal-calculi.pdf','From Legal Contracts to Legal Calculi: the code-driven normativity','Crafa',2022,'Silvia Crafa','https://arxiv.org/pdf/2209.02353','10.4204/EPTCS.368.2','Electronic Proceedings in Theoretical Computer Science, 368','Author preprint'),
 ('connecting2023','connecting-statutes.pdf','Connecting Symbolic Statutory Reasoning with Legal Information Extraction','Holzenberger',2023,'Nils Holzenberger and Benjamin Van Durme','https://aclanthology.org/2023.nllp-1.12.pdf','10.18653/v1/2023.nllp-1.12','Proceedings of the Natural Legal Language Processing Workshop','ACL Anthology proceedings copy'),
 ('logicalenglish2023','logical-english.pdf','Logical English for Law and Education','Kowalski',2023,'Robert Kowalski and Jacinto Dávila and Galileo Sator and Miguel Calejo','https://www.doc.ic.ac.uk/~rak/papers/Logical%20English%20for%20Law%20and%20Education%20.pdf','10.1007/978-3-031-35254-6_24','Prolog: The Next 50 Years','Author-hosted version; third author is Galileo Sator as on title page'),
 ('huttner2022','catala-expert-author.pdf','Catala: Moving Towards the Future of Legal Expert Systems','Huttner',2022,'Liane Huttner and Denis Merigoux','https://inria.hal.science/hal-02936606/document','10.1007/s10506-022-09328-5','Artificial Intelligence and Law','Accepted manuscript, 10 August 2022'),
 ('logiclm2023','logic-lm.pdf','Logic-LM: Empowering Large Language Models with Symbolic Solvers for Faithful Logical Reasoning','Pan',2023,'Liangming Pan and Alon Albalak and Xinyi Wang and William Yang Wang','https://aclanthology.org/2023.findings-emnlp.248.pdf','10.18653/v1/2023.findings-emnlp.248','Findings of EMNLP 2023','ACL Anthology proceedings copy'),
 ('linc2023','linc.pdf','LINC: A Neurosymbolic Approach for Logical Reasoning by Combining Language Models with First-Order Logic Provers','Olausson',2023,'Theo X. Olausson and Alex Gu and Benjamin Lipkin and Cedegao E. Zhang and Armando Solar-Lezama and Joshua B. Tenenbaum and Roger Levy','https://aclanthology.org/2023.emnlp-main.313.pdf','10.18653/v1/2023.emnlp-main.313','Proceedings of EMNLP 2023','ACL Anthology proceedings copy'),
 ('contractnli2021','contractnli.pdf','ContractNLI: A Dataset for Document-level Natural Language Inference for Contracts','Koreeda',2021,'Yuta Koreeda and Christopher D. Manning','https://aclanthology.org/2021.findings-emnlp.164.pdf','10.18653/v1/2021.findings-emnlp.164','Findings of EMNLP 2021','ACL Anthology proceedings copy'),
 ('limits2026','know-limits.pdf','Know Your Limits: On the Faithfulness of LLMs as Solvers and Autoformalizers in Legal Reasoning','Wang',2026,'Olivia Peiyu Wang and Sanna Wong-Toropainen and Daneshvar Amrollahi and Ryan Bai and Tashvi Bansal and Arush Garg and Leilani H. Gilpin','https://arxiv.org/pdf/2606.16118v2','','arXiv:2606.16118','v2, 19 June 2026; under review; methodological caveats retained'),
 ('sara2020','sara.pdf','A Dataset for Statutory Reasoning in Tax Law Entailment and Question Answering','Holzenberger',2020,'Nils Holzenberger and Andrew Blair-Stanek and Benjamin Van Durme','https://arxiv.org/pdf/2005.05257','','arXiv:2005.05257','Dataset uses simplified statutes, not current operative US tax law'),
 ('ghose2007','auditing-compliance.pdf','Auditing Business Process Compliance','Ghose',2007,'Aditya Ghose and George Koliadis','https://link.springer.com/content/pdf/10.1007/978-3-540-74974-5_14.pdf','10.1007/978-3-540-74974-5_14','Business Process Management (BPM 2007)','Publisher chapter'),
 ('legalinterpretations2014','legal-interpretations.pdf','Legal Interpretations in LegalRuleML','Athan',2014,'Tara Athan and Guido Governatori and Monica Palmirani and Adrian Paschke and Adam Wyner','https://ceur-ws.org/Vol-1296/paper2.pdf','','CEUR Workshop Proceedings, 1296','Workshop paper'),
 ('compliancehard2015','compliance-hard.pdf','Business Process Regulatory Compliance is Hard','Tosatto',2015,'Silvano Colombo Tosatto and Guido Governatori and Pierre Kelsen','https://eprints.qut.edu.au/100964/1/ComProof%202.pdf','10.1109/TSC.2014.2341236','IEEE Transactions on Services Computing, 8(6), 958--970','Author manuscript; DOI online year 2014, issue year 2015'),
]

def tex(s):
    return s.replace('&',r'\&').replace('%',r'\%').replace('_',r'\_')

records = []
bib = []
for key, source, title, surname, year, authors, url, doi, venue, note in ROWS:
    src = REVIEW / source
    raw = src.read_bytes()
    if not raw.startswith(b'%PDF'):
        raise ValueError(f'Not a PDF: {src}')
    safe_title = re.sub(r'[/:*?"<>|]', ' - ', title)
    safe_title = re.sub(r'\s+', ' ', safe_title).strip()
    filename = f'{safe_title}, {surname}({year}).pdf'
    dest = LIB / filename
    shutil.copyfile(src, dest)
    info = subprocess.check_output(['pdfinfo',str(dest)],text=True)
    pages = int(re.search(r'^Pages:\s+(\d+)',info,re.M).group(1))
    records.append(dict(id=key,title=title,first_author_surname=surname,year=year,
                        authors=authors,source_url=url,doi=doi,venue=venue,version_note=note,
                        filename=filename,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
                        pages=pages,downloaded_on='2026-09-21',
                        local_staging_source=str(src.relative_to(ROOT)),
                        alternate_version_of='jurayj2026' if key=='jurayj2025extended' else None))
    fields={'title':'{'+tex(title)+'}','author':tex(authors),'year':str(year),
            'howpublished':tex(venue),'url':url,'note':tex(note)}
    if doi: fields['doi']=doi
    bib.append('@misc{'+key+',\n'+',\n'.join('  '+k+' = {'+v+'}'for k,v in fields.items())+'\n}\n')

manifest={'schema_version':1,'access_date':'2026-09-21',
          'filename_policy':'Title, FirstAuthorSurname(year).pdf; filesystem-unsafe punctuation replaced by spaced hyphen. Year follows the cited edition, with preprint revisions recorded separately.',
          'paper_pdf_count':len(records),'distinct_work_count':len(records)-1,'papers':records}
(LIB/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
(ROOT/'docs/proposal/papers.bib').write_text('\n'.join(bib))
lines=['# Paper library','',f'{len(records)} full-text PDFs representing {len(records)-1} distinct works. All seven links supplied by the user have local full texts. The Jurayj paper is retained in both proceedings and extended preprint editions.','',
       'Files use the requested `Title, FirstAuthorSurname(year).pdf` convention. Colons and other cross-platform filename punctuation are replaced by a spaced hyphen. The manifest records exact titles, source URLs, versions, DOI identities, page counts and SHA-256 digests. Dates in filenames follow the cited edition; a later arXiv revision is explicitly identified.','',
       'The [product proposal](../proposal/proposal.pdf) explains the technical findings and their limits. The [reading notes](reading-notes.md) identify the sections inspected and design implications. PDFs are retained for local study; public availability is not a blanket redistribution license.','']
for r in sorted(records,key=lambda r:(r['first_author_surname'].lower(),r['year'],r['title'])):
    lines += [f"- [{r['title']}]({quote(r['filename'])}) — {r['authors']}, {r['year']}. {r['version_note']}. {r['pages']} pages."]
lines += ['', '## Coverage and retrieval limits', '',
 'Discovery used ResearchAssistant (OpenAlex and Crossref), direct OpenAlex citation neighborhoods, backward references, and official project sources. The preserved citation queries returned 52 Catala-citing records and 13 records citing the later Stipula journal paper; these overlap and include duplicate editions. They are discovery observations, not an exhaustive census or evidence of popularity. The broad ResearchAssistant query yielded 215 candidates; automated ranking included irrelevant results and was not used as a quality judgment.', '',
 'Semantic Scholar was unavailable in the discovery run, and the browser search service returned upstream errors. Direct public HTTPS retrieval supplied the sources. Full text of Lawsky’s *A Logic for Statutes* and the additional Stipula workbench/amendment chapters could not be obtained through the attempted publisher/repository routes; those papers are discovery leads, not primary technical evidence in this review. Their accessible official software documentation is reviewed separately. The Huttner–Merigoux paper was retrieved from HAL after the publisher PDF route returned HTML.', '',
 'ResearchAssistant PDF parsing is retained in `.localresources/literature-review/text`. Its extraction path was pdftotext and reported low confidence/manual review; the proposal therefore uses source-page and section checks, not automatic extraction scores as correctness evidence.']
(LIB/'README.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'paper_pdfs':len(records),'distinct_works':len(records)-1,'pages':sum(x['pages']for x in records)},indent=2))
