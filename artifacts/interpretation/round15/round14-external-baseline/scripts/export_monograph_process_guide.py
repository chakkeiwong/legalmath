"""Extract the illustrated front guide, preserving its navigation links."""
from pathlib import Path
from urllib.parse import unquote

import fitz

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "docs/monograph"


def named_destination(document, name):
    target = document.resolve_names()[name]
    page = target["page"]
    # Named PDF destinations use bottom-origin coordinates. Link insertion uses
    # PyMuPDF's top-origin page coordinates.
    point = fitz.Point(target["to"]) * document[page].transformation_matrix
    return page, point


def main():
    with fitz.open(BOOK / "monograph.pdf") as source, fitz.open() as guide:
        start = next(row[2] - 1 for row in source.get_toc()
                     if row[:2] == [1, "From the circular to Java"])
        end = next(i for i in range(start + 1, len(source))
                   if source[i].get_text().lstrip().startswith("Contents\n"))
        # Rebuild annotations explicitly: a normal slice drops named internal
        # links and can misinterpret a relative file with a named destination.
        guide.insert_pdf(source, from_page=start, to_page=end - 1, links=False)
        for original_page in range(start, end):
            for link in source[original_page].get_links():
                outgoing = {"from": link["from"]}
                if link.get("nameddest"):
                    page, point = named_destination(source, link["nameddest"])
                elif link["kind"] == fitz.LINK_GOTO:
                    page, point = link["page"], link.get("to", fitz.Point())
                elif link.get("file"):
                    filename, _, fragment = unquote(link["file"]).partition("#")
                    with fitz.open(BOOK / filename) as target:
                        if fragment.startswith("nameddest="):
                            page, point = named_destination(
                                target, fragment[len("nameddest="):])
                        else:
                            page, point = link["page"], link.get("to", fitz.Point())
                    outgoing.update(kind=fitz.LINK_GOTOR, file=filename,
                                    page=page, to=point)
                    guide[original_page - start].insert_link(outgoing)
                    continue
                elif link["kind"] == fitz.LINK_URI:
                    outgoing.update(kind=fitz.LINK_URI, uri=link["uri"])
                    guide[original_page - start].insert_link(outgoing)
                    continue
                else:
                    raise ValueError(f"Unsupported guide link: {link}")
                if start <= page < end:
                    outgoing.update(kind=fitz.LINK_GOTO, page=page - start, to=point)
                else:
                    outgoing.update(kind=fitz.LINK_GOTOR, file="monograph.pdf",
                                    page=page, to=point)
                guide[original_page - start].insert_link(outgoing)
        guide.set_metadata({"title": "LegalMath: From the circular to Java",
                            "author": "Chak Wong",
                            "subject": "Illustrated process and technology guide"})
        guide.save(BOOK / "process-guide.pdf", garbage=4, deflate=True)
        print(f"Exported process-guide.pdf: {end - start} pages", flush=True)


if __name__ == "__main__":
    main()
