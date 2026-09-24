"""Inventory and verify document evidence; never certify source truth or prose.

The literal tree and occurrence lists are starting points for human/model review.
No automatically generated row is marked semantically reviewed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

import fitz

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "docs/monograph"
BASE = ROOT / ".localresources/monograph-revision/baseline"
REVIEW = BOOK / "review/revision"
INPUT = re.compile(r"\\(?:input|include)\{(?:\\LegalMathRoot\s*)?([^}]+)\}")
HEADING = re.compile(r"^\\(chapter|section|subsection|subsubsection)(\*)?(?:\[[^\]]*\])?\{([^\n]+)\}", re.M)
CITE = re.compile(r"\\cite\w*\*?(?:\[[^\]]*\])*\{([^}]+)\}")
EQUATION = re.compile(r"\\begin\{(equation\*?|align\*?|gather\*?|multline\*?|displaymath)\}.*?\\end\{\1\}|\\\[.*?\\\]", re.S)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expand(path, book=BOOK, stack=()):
    if path in stack:
        raise ValueError(f"Recursive TeX input: {path}")
    return INPUT.sub(lambda m: expand(book / (m[1] + ("" if m[1].endswith(".tex") else ".tex")), book, (*stack, path)), path.read_text())


def cited(text):
    return {k.strip() for m in CITE.finditer(text) for k in m[1].split(",")}


def inventory():
    REVIEW.mkdir(parents=True, exist_ok=True)
    text = expand(BOOK / "monograph.tex")
    (REVIEW / "expanded.tex").write_text(text)
    nodes = [{"id": "document", "kind": "document", "title": "LegalMath", "parent": None}]
    stack = {0: "document"}
    occurrences, equations, figures = [], [], []
    def visit(path):
        nonlocal stack
        raw = path.read_text()
        local = str(path.relative_to(ROOT))
        events = [(m.start(), "heading", m) for m in HEADING.finditer(raw)]
        events += [(m.start(), "equation", m) for m in EQUATION.finditer(raw)]
        events += [(m.start(), "citation", m) for m in CITE.finditer(raw)]
        events += [(m.start(), "input", m) for m in INPUT.finditer(raw)]
        for pos, kind, m in sorted(events):
            if kind == "input":
                visit(BOOK / (m[1] + ("" if m[1].endswith(".tex") else ".tex")))
                continue
            line = raw.count("\n", 0, pos) + 1
            ident = f"{local}:{line}"
            parent = stack[max(stack)]
            if kind == "heading":
                level = {"chapter": 1, "section": 2, "subsection": 3, "subsubsection": 4}[m[1]]
                stack = {n: v for n, v in stack.items() if n < level}
                parent = stack[max(stack)]
                stack[level] = ident
                nodes.append({"id": ident, "kind": m[1], "title": m[3], "parent": parent,
                              "source": local, "line": line, "review_status": "not_reviewed"})
            elif kind == "equation":
                labels = re.findall(r"\\label\{([^}]+)\}", m[0])
                row = {"id": labels[0] if labels else ident, "labels": labels, "kind": "equation", "parent": parent,
                       "source": local, "line": line, "tex": m[0], "review_status": "not_reviewed"}
                equations.append(row)
                nodes.append(row)
            else:
                start = raw.rfind("\n\n", 0, pos) + 2
                end = raw.find("\n\n", m.end())
                claim = raw[start:end if end >= 0 else len(raw)].strip()
                if '\\begin{longtable}' in claim or '\\begin{tabularx}' in claim:
                    row_start = raw.rfind('\\\\', start, pos)
                    row_end = raw.find('\\\\', m.end())
                    if row_start >= start and row_end >= 0:
                        claim = raw[row_start+2:row_end].strip()
                claim = re.sub(r'% (?:BEGIN|END) (?:SOURCE UNIT|REVISION ADDITION)[^\n]*\n?', '', claim)
                for key in m[1].split(","):
                    occurrences.append({"id": f"{ident}:{key.strip()}", "key": key.strip(),
                                        "source": local, "line": line, "context_tex": claim,
                                        "support_status": "not_checked"})
    visit(BOOK / "monograph.tex")
    with fitz.open(BOOK / "monograph.pdf") as pdf:
        pages = [{"pdf_page": i + 1, "sha256_text": hashlib.sha256(p.get_text().encode()).hexdigest(),
                  "continuous_read": "not_recorded", "human_acceptance": "pending"} for i, p in enumerate(pdf)]
        (REVIEW / "rendered-text.txt").write_text("\n".join(f"\n=== PDF PAGE {i+1} ===\n{p.get_text()}" for i, p in enumerate(pdf)))
        figure_pages = [i + 1 for i, p in enumerate(pdf) if re.search(r"Figure\s+\d+\.\d+:", p.get_text())]
        toc = pdf.get_toc()
    result = {"tex_sha256": sha(BOOK / "monograph.tex"), "expanded_sha256": hashlib.sha256(text.encode()).hexdigest(),
              "pdf_sha256": sha(BOOK / "monograph.pdf"), "pages": pages, "tree": nodes,
              "equations": equations, "citation_occurrences": occurrences,
              "cited_keys": sorted(cited(text)), "figure_pages": figure_pages, "toc": toc,
              "limits": "Structure and locations only; all semantic review starts unchecked."}
    (REVIEW / "inventory.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"pages": len(pages), "nodes": len(nodes), "displays": len(equations),
                      "citation_occurrences": len(occurrences), "cited_documents": len(cited(text)),
                      "figure_pages": len(figure_pages)}, indent=2))


def verify():
    before = expand(BASE / "docs/monograph/monograph.tex", BASE / "docs/monograph")
    after = expand(BOOK / "monograph.tex")
    manifest = json.loads((BASE / "manifest.json").read_text())
    errors = [f"Baseline identity changed: {name}" for name, item in manifest["files"].items()
              if sha(BASE / name) != item["sha256"]]
    missing = sorted(cited(before) - cited(after))
    if missing:
        errors.append("Removed citations: " + ", ".join(missing))
    labels = lambda t: set(re.findall(r"\\label\{([^}]+)\}", t))
    if labels(before) - labels(after):
        errors.append("Baseline labels removed")
    features = {}
    for env in ["equation", "lstlisting", "figure"]:
        get = lambda t: Counter(re.sub(r"\s+", " ", m).strip() for m in re.findall(r"\\begin\{" + env + r"\}(.*?)\\end\{" + env + r"\}", t, re.S))
        old, new = get(before), get(after)
        features[env] = {"before": sum(old.values()), "after": sum(new.values()), "changed_or_missing": sum((old-new).values())}
        if old-new:
            errors.append(f"{env} changes need explicit semantic review")
    with fitz.open(BASE / "docs/monograph/monograph.pdf") as pdf:
        n_before = len(pdf)
    with fitz.open(BOOK / "monograph.pdf") as pdf:
        n_after = len(pdf)
        toc = pdf.get_toc()
        start = next(page for level, title, page in toc if title.startswith("A correct program"))
        end = next((i for i,p in enumerate(pdf) if p.get_text().lstrip().startswith('Bibliography\n')), n_after)
        figure_pages = [i+1 for i,p in enumerate(pdf) if re.search(r"Figure\s+\d+\.\d+:",p.get_text())]
        gaps = [[p, p+1] for p in range(start, end) if p not in figure_pages and p+1 not in figure_pages]
    if n_after < n_before:
        errors.append("Page count below protected baseline")
    result = {"mechanical_status": "PASS" if not errors else "FAIL", "errors": errors,
              "pages_before": n_before, "pages_after": n_after, "features": features,
              "figure_free_two_page_windows": gaps, "figure_pages": figure_pages,
              "source_files": {str(p.relative_to(ROOT)): sha(p) for p in sorted(BOOK.rglob("*.tex")) if "review" not in p.parts},
              "pdf_sha256": sha(BOOK / "monograph.pdf"),
              "semantic_preservation": "requires_review", "citation_support": "requires_occurrence_review",
              "legal_use_approval": "not_established", "human_acceptance": "pending"}
    (REVIEW / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k:v for k,v in result.items() if k not in {"source_files", "figure_pages", "figure_free_two_page_windows"}}, indent=2))
    print(f"Figure-free two-page body windows: {len(gaps)}")
    return bool(errors)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["inventory", "verify"])
    args = parser.parse_args()
    raise SystemExit(inventory() if args.action == "inventory" else verify())
