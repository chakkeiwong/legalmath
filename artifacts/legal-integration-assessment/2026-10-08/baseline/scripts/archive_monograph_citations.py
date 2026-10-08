"""Retain named copies of the monograph's existing cited sources.

This records provenance and byte identity. It does not assert that a source was
read, that an old retrieval is current, or that a citation supports its claim.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PAPERS = ROOT / "docs/papers"
REVIEW = ROOT / "docs/monograph/review/revision"


def bibliography():
    entries = {}
    for m in re.finditer(r"@\w+\{([^,]+),(.*?)(?=\n@|\Z)", (ROOT / "docs/monograph/references.bib").read_text(), re.S):
        fields = {}
        for key in ["title", "author", "year", "url", "note"]:
            f = re.search(r"\b" + key + r"\s*=\s*\{(.*?)\}\s*[,}]", m[2], re.S)
            fields[key] = f[1].replace("{", "").replace("}", "") if f else ""
        entries[m[1]] = fields
    return entries


def safe(value):
    return re.sub(r"[/:*?\"<>|]", " - ", value).strip().rstrip(".")


def main():
    bib = bibliography()
    library = {p["id"]: p for p in json.loads((PAPERS / "manifest.json").read_text())["papers"]}
    other = {
        "legalfictions2024": ("Dahl", [".localresources/monograph-revision/sources/legal-fictions-arxiv-v2.pdf"]),
        "legalrag2024": ("Magesh", [".localresources/monograph-revision/sources/legal-rag-arxiv-v1.pdf"]),
        "sfcgenai2024": ("SFC", [".localresources/monograph-revision/sources/sfc-24EC55.json"]),
        "sfcgenaiappendix2024": ("SFC", [".localresources/monograph-revision/sources/sfc-24EC55-appendix.pdf"]),
        "hkmagenai2024": ("HKMA", [".localresources/monograph-revision/sources/hkma-genai-20240819.pdf"]),
        "sfcindex": ("SFC", [".localresources/sfc/product-index.json"]),
        "sfcspi": ("SFC-HKMA", [".localresources/sfc/23EC35.json"]),
        "sfcspiannex1": ("SFC-HKMA", [".localresources/sfc/23EC35-annex1.pdf"]),
        "sfcspiannex2": ("SFC-HKMA", [".localresources/sfc/23EC35-annex2.pdf"]),
        "sfctoken2023": ("SFC", [".localresources/sfc/23EC53.json"]),
        "sfctoken2026": ("SFC", [".localresources/sfc/26EC22.json"]),
        "sfcmarketing": ("SFC", [".localresources/sfc/23EC46.json"]),
        "sfcreview2025": ("SFC-HKMA", [".localresources/sfc/25EC48.json"]),
        "dmn2024": ("Object Management Group", [".localresources/literature-review/dmn-1.5.pdf"]),
        "legalruleml2021": ("OASIS", [".localresources/projects/legalruleml.html"]),
        "catalacode": ("Catala contributors", [".localresources/projects/catala-README.md", ".localresources/projects/catala-formalization.md", ".localresources/projects/catala-translation.fst", ".localresources/projects/catala-conditions.ml"]),
        "stipulacode": ("Stipula contributors", [".localresources/literature-review/stipula-workbench-README.md", ".localresources/literature-review/stipula-README.md", ".localresources/literature-review/metadata/stipula-workbench-tree.json", ".localresources/monograph-revision/sources/stipula-liquidity-README.md", ".localresources/monograph-revision/sources/stipula-liquidity-analyzer.py"]),
        "stipulakeycode": ("Stipula contributors", [".localresources/literature-review/stipula-key-README.md", ".localresources/literature-review/stipula-Translator.java", ".localresources/literature-review/metadata/stipula-key-tree.json", ".localresources/monograph-revision/sources/stipula-key-Deposit.java"]),
        "droolscode": ("Apache KIE contributors", [".localresources/projects/drools-README.md"]),
        "blawxcode": ("Lexpedite", [".localresources/projects/blawx-README.md"]),
        "openfiscacode": ("OpenFisca contributors", [".localresources/projects/openfisca-README.md", ".localresources/monograph-revision/sources/openfisca-variable.py", ".localresources/monograph-revision/sources/openfisca-revision.json"]),
        "z3code": ("Z3 contributors", [".localresources/projects/z3-README.md"]),
        "opadocs": ("Open Policy Agent contributors", [".localresources/literature-review/pages/opa.html"]),
        "cicerocode": ("Accord Project", [".localresources/literature-review/cicero-README.md"]),
        "localrepos": ("LegalMath", ["docs/sfc-rule-translator-design.md", ".localresources/source-manifest.json"]),
        "libraryreview": ("LegalMath", ["docs/papers/README.md", "docs/papers/reading-notes.md", "docs/papers/manifest.json"]),
        "l4code": ("Legalese contributors", [".localresources/literature-v2/metadata/l4-deontic.md", ".localresources/literature-v2/metadata/l4.json", ".localresources/literature-v2/metadata/l4-tree.json", ".localresources/monograph-revision/sources/l4-README.md"]),
        "symboleocode": ("University of Ottawa", [".localresources/literature-v2/metadata/symboleo-readme.md", ".localresources/literature-v2/metadata/symboleo-checker.md"]),
        "eflintartifact": ("Esterhuyse", [".localresources/literature-v2/metadata/eflint-artifact.zip"]),
        "semanticcode2023": ("Kuhn", [".localresources/monograph/semantic-code.py"]),
        "debertaconfig": ("Microsoft", [".localresources/monograph/deberta-mnli-config.json"]),
    }
    result = []
    sys.path.insert(0, "/home/chakwong/python/ResearchAssistant/src")
    from research_assistant.ingest.pdf_extract import extract_pdf_text
    texts = REVIEW / "source-text"
    texts.mkdir(parents=True, exist_ok=True)
    for key, entry in bib.items():
        if key in library:
            old = library[key]
            author, paths = old["first_author_surname"], ["docs/papers/" + old["filename"]]
        elif key in other:
            author, paths = other[key]
        else:
            result.append({"key": key, "status": "missing", "title": entry["title"]})
            continue
        extension = Path(paths[0]).suffix if len(paths) == 1 else ".zip"
        name = safe(entry["title"]) + "_" + safe(author) + "(" + entry["year"] + ")" + extension
        dest = PAPERS / name
        if len(paths) == 1:
            if not dest.exists():
                shutil.copyfile(ROOT / paths[0], dest)
            if dest.read_bytes() != (ROOT / paths[0]).read_bytes():
                raise ValueError(f"Existing archive differs: {name}")
        elif not dest.exists():
            with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as archive:
                for source in paths:
                    archive.write(ROOT / source, source)
        else:
            with zipfile.ZipFile(dest) as archive:
                present = set(archive.namelist())
                for source in paths:
                    if source in present and archive.read(source) != (ROOT / source).read_bytes():
                        raise ValueError(f"Archived source changed: {source}")
            if set(paths) - present:
                previous = REVIEW / 'archive-history'
                previous.mkdir(exist_ok=True)
                old_hash = hashlib.sha256(dest.read_bytes()).hexdigest()
                shutil.copyfile(dest, previous / (key + '-' + old_hash[:12] + '.zip'))
                with zipfile.ZipFile(dest, 'a', zipfile.ZIP_DEFLATED) as archive:
                    for source in paths:
                        if source not in present:
                            archive.write(ROOT / source, source)
        row = {"key": key, "title": entry["title"], "author_filename": author, "year": entry["year"],
               "path": str(dest.relative_to(ROOT)), "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
               "source_url": entry["url"], "retained_inputs": paths,
               "status": "local_copy_retained", "claim_support": "not_reaudited",
               "currentness": "historical_snapshot_not_current_authority_determination"}
        if key in library:
            row.update({"publication_status": library[key].get("version_note"),
                        "original_retrieved_on": library[key].get("downloaded_on"),
                        "retraction_check": "not_rechecked", "citation_count": "not available",
                        "venue_metric": "not available"})
        elif "code" in key or key in {"symboleocode", "l4code"}:
            row["scope"] = "Retained inspected documentation/source files; not a full repository clone."
        if extension == ".pdf":
            output = texts / f"{key}.txt"
            if not output.exists():
                output.write_text(extract_pdf_text(dest))
            row["extracted_text"] = str(output.relative_to(ROOT))
            row["extraction_tool"] = "ResearchAssistant.ingest.pdf_extract (pdftotext backend)"
        result.append(row)
    manifest = {"date": "2026-09-23", "filename_format": "Title_FirstAuthorSurname(year).extension",
                "corporate_authors": "Corporate source uses the named organisation.",
                "limits": "Archive availability does not establish claim support, full reading or current legal applicability.",
                "sources": result}
    (PAPERS / "monograph-citation-archive.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"sources": len(result), "retained": sum(r["status"] == "local_copy_retained" for r in result),
                      "missing": [r["key"] for r in result if r["status"] == "missing"]}, indent=2))


if __name__ == "__main__":
    main()
