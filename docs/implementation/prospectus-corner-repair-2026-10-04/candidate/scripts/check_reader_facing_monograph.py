"""Check the two-document edition without certifying prose or legal meaning.

The protected repetition checkpoint supplies exact equations, listings, source
labels and citation keys. Relocation is permitted; mathematical displays must
remain in the main volume. Changed prose needs a separate editorial review.
"""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

import fitz
from bind_monograph_citation_claims import bind_claims

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "docs/monograph"
BASE = ROOT / ".localresources/monograph-repetition/baseline/docs/monograph"
REVIEW = BOOK / "review/reader-facing"
INPUT = re.compile(r"\\(?:input|include)\{(?:\\LegalMathRoot\s*)?([^}]+)\}")
CITE = re.compile(r"\\cite\w*\*?(?:\[[^\]]*\])*\{([^}]+)\}")
DISPLAY = re.compile(
    r"\\begin\{(equation\*?|align\*?|gather\*?|multline\*?|displaymath)\}"
    r".*?\\end\{\1\}|\\\[.*?\\\]", re.S,
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def expand(path, book, stack=()):
    if path in stack:
        raise ValueError(f"Cyclic input: {path}")
    return INPUT.sub(
        lambda m: expand(book / (m[1] if m[1].endswith(".tex") else m[1] + ".tex"),
                         book, (*stack, path)), path.read_text(),
    )


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


def labels(text):
    return re.findall(r"\\label\{([^}]+)\}", text)


def features(text, pattern):
    return Counter(normalize(m[0]) for m in pattern.finditer(text))


def occurrences(path, book):
    """Locations and contexts, with no automatically assigned support verdict."""
    raw = path.read_text()
    events = sorted([(m.start(), "cite", m) for m in CITE.finditer(raw)] +
                    [(m.start(), "input", m) for m in INPUT.finditer(raw)])
    rows = []
    for pos, kind, match in events:
        if kind == "input":
            child = book / (match[1] if match[1].endswith(".tex") else match[1] + ".tex")
            rows.extend(occurrences(child, book))
            continue
        start = raw.rfind("\n\n", 0, pos) + 2
        end = raw.find("\n\n", match.end())
        context = raw[start:end if end >= 0 else len(raw)].strip()
        if "\\begin{longtable}" in context or "\\begin{tabularx}" in context:
            row_start = raw.rfind("\\\\", start, pos)
            row_end = raw.find("\\\\", match.end())
            if row_start >= start and row_end >= 0:
                context = raw[row_start+2:row_end].strip()
        context = re.sub(r"% (?:BEGIN|END) (?:SOURCE UNIT|REVISION ADDITION)[^\n]*\n?", "", context)
        source = str(path.relative_to(ROOT))
        line = raw.count("\n", 0, pos) + 1
        for key in match[1].split(","):
            rows.append({"id": f"{source}:{line}:{key.strip()}", "key": key.strip(),
                         "source": source, "line": line, "context_tex": context,
                         "context_sha256": digest(context.encode())})
    return rows


def main():
    REVIEW.mkdir(parents=True, exist_ok=True)
    errors = []
    baseline_root = ROOT / ".localresources/monograph-repetition/baseline"
    baseline_manifest = json.loads((baseline_root / "manifest.json").read_text())
    for row in baseline_manifest["files"]:
        path = baseline_root / row["path"]
        if not path.exists() or digest(path.read_bytes()) != row["sha256"]:
            errors.append(f"Protected baseline changed: {row['path']}")
    before = expand(BASE / "monograph.tex", BASE)
    texts = {name: expand(BOOK / f"{name}.tex", BOOK)
             for name in ("monograph", "technical-companion")}
    after = "\n".join(texts.values())
    listing = re.compile(r"\\begin\{lstlisting\}.*?\\end\{lstlisting\}", re.S)
    missing_displays = features(before, DISPLAY) - features(texts["monograph"], DISPLAY)
    missing_listings = features(before, listing) - features(after, listing)
    missing_labels = sorted(set(labels(before)) - set(labels(after)))
    duplicate_labels = [label for label, count in Counter(labels(after)).items() if count > 1]
    references = set(re.findall(r"\\(?:ref|eqref)\{([^}]+)\}", after))
    missing_references = sorted(references - set(labels(after)))
    keys = lambda text: {key.strip() for m in CITE.finditer(text) for key in m[1].split(",")}
    missing_keys = sorted(keys(before) - keys(after))
    for name, items in (("mathematical displays from main volume", missing_displays),
                        ("original listings across the two documents", missing_listings),
                        ("original labels", missing_labels), ("reference targets", missing_references),
                        ("citation keys", missing_keys), ("duplicate labels", duplicate_labels)):
        if items:
            errors.append(f"Check failed: {name}: {len(items)}")
    chapters = re.findall(r"\\chapter(?:\[[^\]]*\])?\{", texts["monograph"])
    if len(chapters) != 10:
        errors.append(f"Expected ten main chapters, found {len(chapters)}")
    archive = json.loads((ROOT / "docs/papers/monograph-citation-archive.json").read_text())
    by_key = {row["key"]: row for row in archive["sources"]}
    for key in keys(after):
        row = by_key.get(key)
        if not row or digest((ROOT / row["path"]).read_bytes()) != row["sha256"]:
            errors.append(f"Citation archive identity missing or changed: {key}")
    documents = {}
    for name, text in texts.items():
        (REVIEW / f"{name}-expanded.tex").write_text(text)
        log = (BOOK / f"{name}.log").read_text()
        diagnostics = re.findall(r"^.*(?:Overfull|undefined|multiply defined|LaTeX Error|Missing character).*$", log, re.M)
        if diagnostics:
            errors.append(f"{name}: {len(diagnostics)} unresolved LaTeX diagnostics")
        pdf_path = BOOK / f"{name}.pdf"
        with fitz.open(pdf_path) as pdf:
            pages = []
            for i, page in enumerate(pdf):
                page_text = page.get_text()
                outside = [s["text"] for b in page.get_text("dict")["blocks"] if "lines" in b
                           for line in b["lines"] for s in line["spans"]
                           if s["bbox"][0] < -1 or s["bbox"][2] > page.rect.width + 1
                           or s["bbox"][1] < -1 or s["bbox"][3] > page.rect.height + 1]
                if outside or len(page_text.strip()) < 20:
                    errors.append(f"{name}: clipped or empty page {i+1}")
                pages.append({"page": i+1, "text": page_text,
                              "text_sha256": digest(page_text.encode()), "outside": outside})
            documents[name] = {"pages": len(pdf), "pdf_sha256": digest(pdf_path.read_bytes()),
                               "toc": pdf.get_toc(), "latex_diagnostics": diagnostics,
                               "displays": sum(features(text, DISPLAY).values()),
                               "listings": sum(features(text, listing).values())}
            (REVIEW / f"{name}-pages.json").write_text(json.dumps(pages, indent=2) + "\n")
            (REVIEW / f"{name}-text.txt").write_text("\n\f\n".join(p["text"] for p in pages))
    citations = [row for name in texts for row in occurrences(BOOK / f"{name}.tex", BOOK)]
    (REVIEW / "citation-contexts.json").write_text(json.dumps(citations, indent=2) + "\n")
    citation_review = REVIEW / "citation-occurrence-review.json"
    citation_status = "pending author review"
    if citation_review.exists():
        reading = json.loads((BOOK / "review/revision/citation-reading.json").read_text())["sources"]
        try:
            reviewed = json.loads(citation_review.read_text())
            identity = lambda row: (row["key"], row["context_sha256"])
            if Counter(map(identity, citations)) != Counter(map(identity, reviewed["occurrences"])):
                raise ValueError("Citation key/context set changed: author review required")
            by_context = defaultdict(list)
            for row in reviewed["occurrences"]:
                by_context[identity(row)].append(row)
            # Renumbering or relocation changes an occurrence ID, not its
            # judgment. Only exact key/context matches may carry that judgment.
            migrated = [{**by_context[identity(row)].pop(0), "id": row["id"]}
                        for row in citations]
            bound = bind_claims({"citation_occurrences": citations}, reading, by_key,
                                {**reviewed, "occurrences": migrated})
            bound["frozen_review_sha256"] = digest(citation_review.read_bytes())
            bound["location_binding"] = "Exact key/context multiset; line numbers and paths may move."
        except ValueError as exc:
            errors.append(f"Citation review binding failed: {exc}")
            citation_status = "FAIL"
        else:
            (REVIEW / "citation-claims.json").write_text(json.dumps(bound, indent=2, ensure_ascii=False) + "\n")
            citation_status = "PASS: existing scoped author judgments bound to exact contexts"
    result = {
        "status": "PASS" if not errors else "FAIL", "errors": errors, "documents": documents,
        "baseline": str(BASE.relative_to(ROOT)), "missing_displays": list(missing_displays),
        "baseline_files_verified": len(baseline_manifest["files"]),
        "missing_listings": list(missing_listings), "missing_labels": missing_labels,
        "missing_references": missing_references, "missing_citation_keys": missing_keys,
        "source_unit_labels_retained": sum(label.startswith("merge:") for label in set(labels(before))),
        "citation_documents": len(keys(after)), "citation_occurrences": len(citations),
        "citation_review_binding": citation_status,
        "source_hashes": {str(p.relative_to(ROOT)): digest(p.read_bytes())
                          for p in sorted(BOOK.rglob("*.tex")) if "review" not in p.parts},
        "human_acceptance": "pending",
        "limits": "Checks source identity, exact displays/listings, reference resolution and page geometry. Changed prose and citation contexts need author review; no legal or reader acceptance is inferred.",
    }
    (REVIEW / "document-check.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("status", "errors", "citation_documents", "citation_occurrences", "source_unit_labels_retained")}, indent=2))
    print("Pages:", {name: record["pages"] for name, record in documents.items()})
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
