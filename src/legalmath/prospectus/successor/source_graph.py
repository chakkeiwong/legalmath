"""Retained page/line evidence; extraction completeness always requires review."""
import math
import re
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET
from .contracts import TextUnit, bound_path, digest, timestamp, read

REFERENCE = re.compile(r"\b(?:Condition|Section|Clause|Article)\s+(\d+(?:\.\d+)*(?:\([a-z0-9]+\))?)|§\s*(\d+(?:\([a-z0-9]+\))?)", re.I)


def pdf_units(path, document):
    from .sealed_source import current, file_digest
    runtime = current()
    receipt = None
    if runtime is None:
        run = subprocess.run(["pdftotext", "-bbox-layout", "-enc", "UTF-8", str(path), "-"],
                             capture_output=True, timeout=90, check=True)
    else:
        executable = str(Path(shutil.which('pdftotext')).resolve(strict=True))
        argv = [executable, "-bbox-layout", "-enc", "UTF-8", str(path), "-"]
        result = runtime.execute(argv, b'', {executable: file_digest(executable), str(path): document['sha256']},
                                 max_stream=runtime.native_text_max_stream)
        run = subprocess.CompletedProcess(argv, result['returncode'], result['stdout'], result['stderr'])
        receipt = result['receipt']
    raw_xml = run.stdout.decode("utf-8")
    illegal = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
    removed = [{"offset": m.start(), "codepoint": ord(m.group())} for m in illegal.finditer(raw_xml)]
    tree = ET.fromstring(illegal.sub("", raw_xml))
    ns = {"x": "http://www.w3.org/1999/xhtml"}
    pages = tree.findall(".//x:page", ns)
    units = []
    for p, page in enumerate(pages, 1):
        order = 0
        for b, block in enumerate(page.findall(".//x:block", ns)):
            for line in block.findall("x:line", ns):
                words, offset = [], 0
                for word in line.findall("x:word", ns):
                    text = "".join(word.itertext())
                    words.append({"text": text, "start": offset, "end": offset + len(text),
                                  "bbox": [float(word.attrib[k]) for k in ("xMin", "yMin", "xMax", "yMax")]})
                    offset += len(text) + 1
                raw = " ".join(w["text"] for w in words)
                box = [float(line.attrib[k]) for k in ("xMin", "yMin", "xMax", "yMax")]
                units.append(TextUnit(f"{document['id']}:p{p}:l{order}", document["id"],
                    document["sha256"], p, order, raw, box, f"{document['id']}:p{p}:b{b}", document["language"],
                    "pdftotext-bbox-layout").json())
                units[-1]["words"] = words
                order += 1
        if order == 0:
            units.append(TextUnit(f"{document['id']}:p{p}:blank", document["id"], document["sha256"],
                p, 0, "", None, f"{document['id']}:p{p}", document["language"], "blank-or-unread").json())
    if not pages:
        raise ValueError("No PDF pages extracted")
    return units, len(pages), {"extractor": "pdftotext-bbox-layout",
        "executable_sha256": digest(Path(shutil.which('pdftotext')).resolve().read_bytes()),
        "dependency_assurance": "DECLARED_EXECUTABLE; native libraries not confined; current assessment reruns extraction",
        "raw_xml_sha256": digest(run.stdout), "xml_illegal_characters": removed, "geometry_review": "PENDING",
        **({'sealed_execution': receipt, 'dependency_assurance': 'SEALED_EXPLICIT_NATIVE_FILES; kernel/proc/dev trusted; reuse disabled'} if receipt else {})}


def retained_ocr_units(document, root, *, data=None, selected_pages=None, geometry_issues=None):
    """Consume a pinned existing CPU OCR result, retaining raw word geometry.

    Reviewed transcriptions are a separate interpretation; raw boxes are never
    silently assigned to corrected text with different characters or word order.
    """
    if data is None:
        spec=document["ocr"]
        path=bound_path(root,spec["path"])
        if digest(path.read_bytes())!=spec["sha256"]:
            raise ValueError("OCR extraction changed")
        data=read(path)
    else:
        spec={"sha256": digest(data)}
    if data["source_sha256"]!=document["sha256"]:
        raise ValueError("OCR source identity or page count differs")
    count = data["page_count"]
    expected = list(range(1, count + 1)) if type(count) is int and count > 0 and selected_pages is None else selected_pages
    if (type(count) is not int or count <= 0 or
            not isinstance(expected, list) or not expected or
            any(type(p) is not int or not 1 <= p <= count for p in expected) or
            expected != sorted(set(expected)) or
            any(type(page.get("page")) is not int for page in data["pages"]) or
            [page["page"] for page in data["pages"]] != expected or
            document.get("page_count", count) != count):
        raise ValueError("OCR pages must cover the exact ordered source sequence or selected original pages")
    language = document.get("hybrid_profile", document.get("scan_profile", {})).get("language", "eng")
    if data["runtime"].get("dpi")!=300 or data["runtime"].get("language")!=language:
        raise ValueError("Unsupported retained OCR settings; review a new profile")
    units=[]
    for p in data["pages"]:
        groups={}
        for word_index, w in enumerate(p.get("words",[])):
            issue = (geometry_issues or {}).get((p['page'], word_index))
            if len(w)!=8 or not all(isinstance(v,(int,float)) for v in w[:4]):
                raise ValueError("Invalid OCR word geometry")
            # PyMuPDF occasionally emits a sub-pixel negative/overrun at a page
            # edge. It is numerical noise, not evidence that the OCR box is
            # outside the page. Keep the raw extraction hash, but clamp only
            # values within the declared tolerance and record the normalization.
            tolerance = 1e-3
            if issue is None and not (-tolerance <= w[0] < w[2] <= 10000 + tolerance and
                    -tolerance <= w[1] < w[3] <= 10000 + tolerance):
                raise ValueError("Invalid OCR word geometry")
            w = list(w)
            if issue is None:
                w[:4] = [min(10000.0, max(0.0, float(v))) for v in w[:4]]
            if not (w[0] < w[2] and w[1] < w[3]):
                raise ValueError("Invalid OCR word geometry")
            groups.setdefault((w[5],w[6]),[]).append((w, issue))
        for order,((block,line),entries) in enumerate(groups.items()):
            entries.sort(key=lambda pair:pair[0][7])
            words = [w for w, issue in entries]
            raw=" ".join(w[4] for w in words)
            box = (None if any(issue for w, issue in entries) else
                   [min(w[0] for w in words),min(w[1] for w in words),max(w[2] for w in words),max(w[3] for w in words)])
            unit=TextUnit(f"{document['id']}:p{p['page']}:ocr{order}",document["id"],document["sha256"],
                          p["page"],order,raw,box,f"{document['id']}:p{p['page']}:b{block}",document["language"],
                          "retained-pymupdf-tesseract").json()
            offset=0;unit["words"]=[]
            for w, issue in entries:
                word = {"text":w[4],"start":offset,"end":offset+len(w[4]),"bbox":None if issue else w[:4]}
                if issue:
                    word['geometry_issue'] = issue
                    unit.setdefault('geometry_issues', []).append({**issue, 'start':offset, 'end':offset+len(w[4])})
                unit["words"].append(word)
                offset+=len(w[4])+1
            units.append(unit)
        if not groups:
            units.append(TextUnit(f"{document['id']}:p{p['page']}:ocr-page",document["id"],document["sha256"],
                                  p["page"],0,p["text"],None,f"{document['id']}:p{p['page']}",
                                  document["language"],"retained-original-text-or-blank").json())
    images = {p['page']:p.get('image_sha256') for p in data['pages']}
    for unit in units:
        if images[unit['page']]:
            unit['image_sha256'] = images[unit['page']]
    return units,data["page_count"],{"extractor":"retained-ocr","runtime":data["runtime"],
                "ocr_sha256":spec["sha256"],
                "geometry_normalization":"clamp boundary noise <=1e-3 to [0,10000]",
                "geometry_review":"RAW_GEOMETRY; transcription corrections require separate maps"}


def hybrid_units(path, document, root):
    """Keep native occurrences and add a bounded, explicit original-page layer."""
    from .extraction import scan, scan_profile, verify_hybrid_images
    from .ocr_geometry import hybrid_word_issue
    profile, _ = scan_profile(document, root, hybrid=True)
    native, count, native_meta = pdf_units(path, document)
    if count != profile['page_count']:
        raise ValueError('Hybrid original PDF page count differs')
    retained = document.get('hybrid_ocr')
    if retained is not None:
        if not isinstance(retained, dict) or set(retained) != {'path','sha256'}:
            raise ValueError('Hybrid retained evidence needs exact path and hash')
        data_path = bound_path(root, retained['path'])
        if digest(data_path.read_bytes()) != retained['sha256']:
            raise ValueError('Hybrid OCR extraction changed')
        data = read(data_path)
    else:
        data = scan(document, root, hybrid=True)
    if (data.get('version') != 'hybrid-ocr.v1' or
            data.get('source_sha256') != document['sha256'] or
            type(data.get('page_count')) is not int or data['page_count'] != count or
            data.get('selected_pages') != profile['pages'] or
            not isinstance(data.get('pages'), list) or
            [p.get('page') for p in data['pages']] != profile['pages'] or
            data.get('runtime', {}).get('language_models') != profile['models']):
        raise ValueError('Hybrid source, selected pages or model identity differs')
    geometry_issues = {}
    for page in data['pages']:
        image = page.get('image_sha256')
        if (not isinstance(image, str) or not re.fullmatch('[0-9a-f]{64}', image) or
                any(type(page.get(k)) is not int or page[k] <= 0 for k in ('image_width', 'image_height')) or
                any(type(page.get(k)) not in (int, float) or not math.isfinite(page[k]) or
                    not 0 < page[k] <= 10000 for k in ('width_points', 'height_points'))):
            raise ValueError('Hybrid page image identity or dimensions missing')
        if not isinstance(page.get('text'), str) or not isinstance(page.get('words'), list):
            raise ValueError('Hybrid page text and words required')
        for index, word in enumerate(page['words']):
            issue = hybrid_word_issue(word, page, allow_unknown=profile['version'] == 'pymupdf-hybrid.v2')
            if issue:
                geometry_issues[page['page'], index] = {**issue, 'word_index':index}
    image_verification = (
        verify_hybrid_images(document, root, data) if retained is not None else
        {'verified_image_pages': profile['pages'], 'verification_mode':'FRESH_WORKER_RENDER'})
    ocr, _, ocr_meta = retained_ocr_units(document, root, data=data, selected_pages=profile['pages'],
                                        geometry_issues=geometry_issues)
    if profile['version'] == 'pymupdf-hybrid.v2':
        ocr_meta.update(geometry_policy=profile['geometry_policy'], geometry_issues=list(geometry_issues.values()),
                        geometry_review='Invalid boxes withheld; text/image evidence retained; spatial review required')
    selected = set(profile['pages'])
    coverage = [{'page': p, 'status': 'NATIVE_AND_OCR_REQUIRES_REVIEW' if p in selected
                 else 'NATIVE_ONLY_IMAGE_COVERAGE_UNREVIEWED'} for p in range(1, count+1)]
    return native + ocr, count, {'extractor': 'native-plus-selected-page-ocr.v1',
        'native_extraction': native_meta, 'native_units_sha256': digest(native),
        'ocr_extraction': ocr_meta, 'runtime': data['runtime'],
        'image_verification': image_verification,
        'fresh_extraction': retained is None, 'selected_pages': profile['pages'],
        'scan_pages': [{k:v for k,v in p.items() if k not in {'words','text'}} for p in data['pages']],
        'page_coverage': coverage, 'text_coverage': 'UNREVIEWED; explicit selection is not whole-document completeness',
        'duplicate_text_policy': 'NATIVE_AND_OCR_PRESERVED; explicit assembly dispositions required',
        'geometry_review': 'RAW_GEOMETRY; corrected text requires image-bound maps'}


def native_text_gaps(graph):
    """Describe retained native omissions without guessing blankness or image text."""
    page_methods = {}
    for unit in graph['units']:
        if unit['raw'].strip():
            page_methods.setdefault((unit['document'], unit['page']), set()).add(unit['method'])
    return [
        {'document': unit['document'], 'source_sha256': unit['source_sha256'],
         'page': unit['page'], 'unit': unit['id'], 'visible': unit.get('visible', False),
         'status': 'NO_NATIVE_TEXT_REQUIRES_IMAGE_REVIEW',
         'additional_text_methods': sorted(page_methods.get((unit['document'], unit['page']), ())),
         'qualification': 'No native text was retained; this does not distinguish a blank page from unread image/vector content. Additional text does not establish complete coverage.'}
        for unit in graph['units']
        if unit.get('method') == 'blank-or-unread' and not unit['raw'].strip()
    ]


def _document_times(doc):
    result = {}
    for key in ("document_date", "known_from", "valid_from", "valid_until"):
        value = doc.get(key)
        if value is None:
            result[key] = None
            continue
        if not isinstance(value, str):
            raise ValueError("Document " + key + " requires a timezone-aware timestamp string")
        result[key] = timestamp(value)
    return result


def acquisition_status(doc, root):
    """Recheck supplied receipt bytes without inferring source authenticity."""
    if not doc.get("acquisition"):
        return "NOT_SUPPLIED"
    receipt = doc["acquisition"]
    if digest(bound_path(root, receipt["path"]).read_bytes()) != receipt["sha256"]:
        raise ValueError("Acquisition receipt changed")
    return "BYTES_BOUND; AUTHENTICITY_REQUIRES_REVIEW"


def build(bundle, root):
    units, records, unresolved = [], [], []
    for doc in bundle["documents"]:
        path = bound_path(root, doc["path"])
        if digest(path.read_bytes()) != doc["sha256"]:
            raise ValueError("Source bytes changed: " + doc["id"])
        visible, issues = True, []
        times = _document_times(doc)
        issued = times["document_date"]
        if issued is None:
            issues.append("document date not established")
        elif bundle["purpose"] == "issue_formation" and issued > timestamp(bundle["issue_date"]):
            visible = False
            issues.append("post-issue source excluded from issue formation")
        if times["known_from"] is None:
            issues.append("knowledge time not established")
        elif times["known_from"] > timestamp(bundle["known_at"]):
            visible = False
            issues.append("source not known at query knowledge time")
        if times["valid_from"] is not None and times["valid_from"] > timestamp(bundle["effective_at"]):
            visible = False
            issues.append("source not yet effective")
        if times["valid_until"] is not None and timestamp(bundle["effective_at"]) >= times["valid_until"]:
            visible = False
            issues.append("source outside recorded effective interval")
        receipt_status = acquisition_status(doc, root)
        if doc.get('hybrid_profile') or doc.get('hybrid_ocr'):
            if not doc.get('hybrid_profile') or doc.get('scan_profile') or doc.get('ocr') or doc.get('format') == 'text':
                raise ValueError('Hybrid intake requires one PDF hybrid profile and no competing extraction mode')
            extracted, count, extraction = hybrid_units(path, doc, root)
            issues.append('hybrid text coverage not established; selected OCR and native-only pages require review')
        elif doc.get("scan_profile"):
            if doc.get("ocr"):
                raise ValueError("Choose current scan intake or retained OCR")
            from .extraction import scan
            data = scan(doc, root)
            extracted, count, extraction = retained_ocr_units(doc, root, data=data)
            extraction["scan_pages"] = [{k:v for k,v in page.items() if k not in {"words", "text"}} for page in data["pages"]]
            extraction["fresh_extraction"] = True
        elif doc.get("ocr"):
            extracted, count, extraction = retained_ocr_units(doc, root)
            if doc.get('format') != 'text':
                from pypdf import PdfReader
                if len(PdfReader(path).pages) != count:
                    raise ValueError('OCR page count differs from original PDF')
        elif doc.get("format") == "text":
            pages = path.read_text().split("\f")
            extracted = [TextUnit(f"{doc['id']}:p{p}:l0", doc["id"], doc["sha256"], p, 0,
                text, None, f"{doc['id']}:p{p}", doc["language"], "plain-text").json()
                for p, text in enumerate(pages, 1)]
            count, extraction = len(pages), {"geometry_review": "NOT_APPLICABLE_TEXT"}
        else:
            try:
                extracted, count, extraction = pdf_units(path, doc)
            except (OSError, subprocess.SubprocessError) as exc:
                from .extraction import ExtractionUnavailable
                raise ExtractionUnavailable("Poppler extraction unavailable; check pdftotext and the declared PDF") from exc
        if doc.get("page_count", count) != count:
            raise ValueError("Source page count changed")
        units.extend({**u, "visible": visible} for u in extracted)
        records.append({**doc, "page_count": count, "visible": visible, "issues": issues,
                        "acquisition_status": receipt_status, **extraction})
        unresolved.extend({"document": doc["id"], "reason": i} for i in issues)
    if len({u["id"] for u in units}) != len(units):
        raise ValueError("Duplicate source occurrence identity")
    references = []
    for unit in units:
        for m in REFERENCE.finditer(unit["raw"]):
            references.append({"id": unit["id"] + f":ref:{m.start()}", "document": unit["document"],
                               "source_sha256": unit["source_sha256"], "unit": unit["id"], "text": m.group(), "target": m.group(1) or m.group(2),
                               "start": m.start(), "end": m.end(), "status": "UNRESOLVED"})
    # Candidate headings preserve edition and occurrence identity. They are not
    # automatically resolved: a repeated number can designate another instrument.
    headings = {}
    for unit in units:
        match = REFERENCE.match(unit["raw"].lstrip())
        if match:
            headings.setdefault((unit["document"], match.group(1) or match.group(2)), []).append(unit["id"])
    for ref in references:
        ref["candidates"] = [u for u in headings.get((ref["document"], ref["target"]), []) if u != ref["unit"]]
    return {"version": "source-graph.v2", "instrument_id": bundle["instrument_id"],
            "context": {k:bundle[k] for k in ("purpose", "issue_date", "effective_at", "known_at")},
            "bundle_sha256": digest(bundle), "documents": records, "units": units,
            "references": references, "unresolved": unresolved,
            "source_authenticity": "CONDITIONAL_ON_RETAINED_ACQUISITION",
            "unit_count": len(units)}
