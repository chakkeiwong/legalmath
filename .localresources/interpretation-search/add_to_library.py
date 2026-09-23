"""Register the locally inspected interpretation-search papers.

This script is deliberately offline: it copies already downloaded files, records
their exact digests and page counts, and preserves the existing paper manifest.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "docs/papers"
HERE = Path(__file__).parent

ROWS = [
    ("agatha2005", "agatha.pdf", "AGATHA: Using heuristic search to automate the construction of case law theories", "Chorley", 2005, "Alison Chorley and Trevor Bench-Capon", "https://www.csc.liv.ac.uk/~tbc/publications/agatha.pdf", "10.1007/s10506-006-9004-2", "Artificial Intelligence and Law, 13, 9--51", "Author PDF title page is dated 2006; Crossref records print publication 2005 and online publication 2006; cited as volume 13 (2005)."),
    ("theories2003", "theories.pdf", "A Model of Legal Reasoning with Cases Incorporating Theories and Values", "Bench-Capon", 2003, "Trevor Bench-Capon and Giovanni Sartor", "https://www.csc.liv.ac.uk/~tbc/publications/aijsartor.pdf", "10.1016/S0004-3702(03)00108-5", "Artificial Intelligence, 150, 97--143", "Author-hosted full text; publication year and DOI follow the journal record."),
    ("hypolegacy2017", "hypo-legacy.pdf", "HYPO's Legacy: Introduction to the Virtual Special Issue", "Bench-Capon", 2017, "T.J.M. Bench-Capon", "https://www.csc.liv.ac.uk/~tbc/publications/hypoLegacy.pdf", "10.1007/s10506-017-9201-1", "Artificial Intelligence and Law, 25, 205--250", "Author manuscript; virtual-special-issue introduction."),
    ("treeofthoughts2023", "tree-of-thoughts-2305.10601.pdf", "Tree of Thoughts: Deliberate Problem Solving with Large Language Models", "Yao", 2023, "Shunyu Yao and Dian Yu and Jeffrey Zhao and Izhak Shafran and Thomas L. Griffiths and Yuan Cao and Karthik Narasimhan", "https://arxiv.org/abs/2305.10601v2", "", "arXiv:2305.10601", "Reviewed arXiv v2 (3 December 2023); the method explores partial thoughts with breadth-first and depth-first search."),
    ("lats2024", "lats.pdf", "Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models", "Zhou", 2024, "Andy Zhou and Kai Yan and Michal Shlapentokh-Rothman and Haohan Wang and Yu-Xiong Wang", "https://arxiv.org/abs/2310.04406v3", "", "Proceedings of ICML 2024, PMLR 235", "Reviewed arXiv v3 (6 June 2024); first posted 2023."),
    ("gbs2011", "nowak.pdf", "The Geometry of Generalized Binary Search", "Nowak", 2011, "Robert D. Nowak", "https://arxiv.org/abs/0910.4397v5", "10.1109/TIT.2011.2169298", "IEEE Transactions on Information Theory, 57(12), 7893--7906", "Reviewed arXiv v5 (25 June 2013); journal publication 2011."),
    ("carneades2007", "carneades.pdf", "The Carneades model of argument and burden of proof", "Gordon", 2007, "Thomas F. Gordon and Henry Prakken and Douglas Walton", "https://webspace.science.uu.nl/~prakk101/pubs/GordonPrakkenWalton2007a.pdf", "10.1016/j.artint.2007.04.010", "Artificial Intelligence, 171, 875--896", "Author-hosted full text; inspected formal definitions and burden-of-proof sections."),
    ("aspic2010", "aspic.pdf", "An abstract framework for argumentation with structured arguments", "Prakken", 2010, "Henry Prakken", "https://webspace.science.uu.nl/~prakk101/pubs/aspicAF.pdf", "10.1080/19462160903564592", "Argument and Computation, 1, 93--124", "Author-hosted full text; correction page retained in the staging directory."),
]

manifest_path = LIB / "manifest.json"
manifest = json.loads(manifest_path.read_text())
existing = {p["id"] for p in manifest["papers"]}
for key, source_name, title, surname, year, authors, url, doi, venue, note in ROWS:
    src = HERE / source_name
    raw = src.read_bytes()
    assert raw.startswith(b"%PDF"), src
    safe_title = re.sub(r"[/:*?\"<>|]", " - ", title)
    safe_title = re.sub(r"\s+", " ", safe_title).strip()
    filename = f"{safe_title}, {surname}({year}).pdf"
    dest = LIB / filename
    shutil.copyfile(src, dest)
    info = subprocess.check_output(["pdfinfo", str(dest)], text=True)
    pages = int(re.search(r"^Pages:\s+(\d+)", info, re.M).group(1))
    record = dict(id=key, title=title, first_author_surname=surname, year=year,
                  authors=authors, source_url=url, doi=doi, venue=venue,
                  version_note=note, filename=filename,
                  sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw),
                  pages=pages, downloaded_on="2026-09-22",
                  local_staging_source=str(src.relative_to(ROOT)),
                  alternate_version_of=None)
    if key in existing:
        manifest["papers"] = [record if p["id"] == key else p for p in manifest["papers"]]
    else:
        manifest["papers"].append(record)

manifest["paper_pdf_count"] = len(manifest["papers"])
manifest["distinct_work_count"] = len({p["id"] for p in manifest["papers"]}) - 1
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

bib_path = ROOT / "docs/research/interpretation-search.bib"
bib = bib_path.read_text() if bib_path.exists() else ""
for key, _, title, surname, year, authors, url, doi, venue, note in ROWS:
    if f"@misc{{{key}," in bib:
        continue
    fields = [
        ("title", "{" + title.replace("&", r"\\&") + "}"),
        ("author", authors.replace("&", r"\\&")),
        ("year", str(year)), ("howpublished", venue.replace("&", r"\\&")),
        ("url", url), ("note", note.replace("&", r"\\&")),
    ]
    if doi:
        fields.insert(5, ("doi", doi))
    bib += "\n@misc{" + key + ",\n" + ",\n".join(f"  {k} = {{{v}}}" for k, v in fields) + "\n}\n"
bib_path.write_text(bib)

lines = [
    "# Research paper library", "",
    f"{manifest['paper_pdf_count']} PDF editions representing {manifest['distinct_work_count']} works; {sum(p['pages'] for p in manifest['papers'])} PDF pages. All seven user-supplied links are retained.", "",
    "The filename convention is `Title, FirstAuthorSurname(year).pdf`. Title punctuation unsafe across filesystems is replaced by a spaced hyphen. The manifest records original titles, exact URLs, version notes, dates and SHA-256 hashes. Publication and preprint dates are distinguished; duplicate editions are identified by `alternate_version_of`.", "",
    "Read the [proposal](../proposal/proposal.pdf), [original technical notes](reading-notes.md), [expanded technical notes](reading-notes-v2.md), and [search/disposition ledger](coverage.md). The ledger distinguishes inspected mechanisms, background sources and unresolved retrievals. Downloading is not counted as technical reading.", "",
    "The [English interpretation assurance note](../research/english-interpretation-assurance.md) addresses source-to-specification correctness. The [competing-interpretations research note](../research/interpretation-search.md) adds a technical reading of eight papers on legal theory construction, argumentation and search, with an implementation design and explicit transfer limits.", "",
]
for p in sorted(manifest["papers"], key=lambda x: (x["first_author_surname"].lower(), x["year"], x["title"])):
    lines.append(f"- [{p['title']}]({quote(p['filename'])}) — {p['year']}; {p['version_note']}. {p['pages']} pages.")
lines += ["", "Full texts are retained for local research. Public availability does not grant blanket redistribution rights. No downloaded implementation or published experiment was replayed merely by constructing this library."]
(LIB / "README.md").write_text("\n".join(lines) + "\n")
print(json.dumps({"paper_pdf_count": manifest["paper_pdf_count"], "distinct_work_count": manifest["distinct_work_count"], "pages": sum(p["pages"] for p in manifest["papers"])}))
