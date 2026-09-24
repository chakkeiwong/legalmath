from html.parser import HTMLParser
from io import BytesIO
from importlib.metadata import version
import json

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from ..errors import LegalMathError


def normalize_text(text):
    return text.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_endtag(self, tag):
        if tag in ("p", "li", "ol", "h1", "h2", "br"):
            self.parts.append("\n")


def extract(raw, media_type):
    if media_type == "application/pdf":
        if not raw.startswith(b"%PDF-"):
            raise LegalMathError("E_SCHEMA")
        try:
            reader = PdfReader(BytesIO(raw))
            if reader.is_encrypted or len(reader.pages) > 1000:
                raise LegalMathError("E_RESOURCE_LIMIT")
            text = "\f".join(page.extract_text() or "" for page in reader.pages)
        except (ValueError, TypeError, PdfReadError) as exc:
            raise LegalMathError("E_SCHEMA") from exc
        if len(text.encode("utf-8")) > 20 * 1024 * 1024:
            raise LegalMathError("E_RESOURCE_LIMIT")
        return normalize_text(text), {"name": "pypdf", "version": version("pypdf"), "configuration": {"page_separator": "\f"}}
    if media_type in ("application/json", "text/html"):
        try:
            html = json.loads(raw)["html"] if media_type == "application/json" else raw.decode("utf-8")
            if not isinstance(html, str): raise ValueError("Non-text HTML")
        except (ValueError, KeyError, TypeError) as exc:
            raise LegalMathError("E_SCHEMA") from exc
        parser = TextParser()
        parser.feed(html)
        return normalize_text("".join(parser.parts)), {"name": "sfc-html-parser", "version": "0.1", "configuration": {}}
    if media_type == "text/plain":
        try: text = raw.decode("utf-8")
        except UnicodeDecodeError as exc: raise LegalMathError("E_SCHEMA") from exc
        return normalize_text(text), {"name": "utf8-lf", "version": "0.1", "configuration": {}}
    raise LegalMathError("E_SCHEMA")
