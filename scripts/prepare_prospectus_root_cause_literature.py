"""Retain local paper readings via ResearchAssistant's bounded PDF adapter."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RA = Path("/home/chakwong/python/ResearchAssistant")
OUT = ROOT / "docs/implementation/prospectus-root-cause-2026-10-06/literature"
PAPERS = {
    "contractnli": "ContractNLI - A Dataset for Document-level Natural Language Inference for Contracts, Koreeda(2021).pdf",
    "catala": "Catala - A Programming Language for the Law, Merigoux(2021).pdf",
    "date-arithmetic": "Formalizing Date Arithmetic and Statically Detecting Ambiguities for the Law, Monat(2024).pdf",
}
RETAINED = {
    "information-extraction": "Connecting Symbolic Statutory Reasoning with Legal Information Extraction, Holzenberger(2023).pdf",
    "know-your-limits": "Know Your Limits - On the Faithfulness of LLMs as Solvers and Autoformalizers in Legal Reasoning, Wang(2026).pdf",
    "legalruleml-interpretations": "Legal Interpretations in LegalRuleML, Athan(2014).pdf",
    "aspic": "An abstract framework for argumentation with structured arguments, Prakken(2010).pdf",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    start = time.monotonic()
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(RA / "src"))
    from research_assistant.ingest.pdf_extract import extract_pdf_text
    from research_assistant.ingest.parser_command import ParserExecutionPolicy
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for key, filename in {**PAPERS, **RETAINED}.items():
        pdf = ROOT / "docs/papers" / filename
        if key in PAPERS:
            text = extract_pdf_text(pdf, policy=ParserExecutionPolicy(timeout_seconds=30))
            path = OUT / (key + ".txt")
            path.write_text(text)
            parser = "ResearchAssistant extract_pdf_text / pdftotext"
        else:
            path = ROOT / ".localresources/legal-interpretation-reuse-2026-10-05" / (key + ".txt")
            text = path.read_text()
            parser = "Previously retained paper extraction"
        records.append({"id": key, "pdf": str(pdf.relative_to(ROOT)), "pdf_sha256": digest(pdf),
                        "text": str(path.relative_to(ROOT)), "text_sha256": digest(path),
                        "parser": parser, "physical_pages": text.count("\f")})
    manifest = {"command": [sys.executable, "-m", "scripts.prepare_prospectus_root_cause_literature"],
                "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "research_assistant_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=RA, text=True).strip(),
                "parser_files": {str(RA / "src/research_assistant/ingest" / name): digest(RA / "src/research_assistant/ingest" / name)
                                 for name in ("pdf_extract.py", "parser_command.py")},
                "new_network_requests": 0, "new_installations": 0, "wall_seconds": time.monotonic() - start,
                "scope": "Local literature preparation; parser success does not establish source correctness or method quality",
                "records": records}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
