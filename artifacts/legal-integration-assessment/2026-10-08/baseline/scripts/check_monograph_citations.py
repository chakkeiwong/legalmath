"""Validate existing reading judgments and quotations; never create a judgment."""
from pathlib import Path
import hashlib
import html
import json
import re
import unicodedata
import fitz
from prepare_monograph_citation_packets import source_sections
from bind_monograph_citation_claims import bind_claims

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT/'docs/monograph/review/revision'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized(text):
    text = unicodedata.normalize('NFKD', html.unescape(text)).lower()
    return ''.join(c for c in text if c.isalnum())


def main():
    inv = json.loads((REVIEW/'inventory.json').read_text())
    archive = json.loads((ROOT/'docs/papers/monograph-citation-archive.json').read_text())
    reading = json.loads((REVIEW/'citation-reading.json').read_text())['sources']
    claims = json.loads((REVIEW/'citation-claims.json').read_text())
    rows = {c['id']:c for c in claims['occurrences']}
    errors, quotes = [], []
    if set(rows) != {c['id'] for c in inv['citation_occurrences']}:
        errors.append('Citation occurrence set changed')
    sources = {a['key']:a for a in archive['sources']}
    try:
        reviews = json.loads((REVIEW/'citation-occurrence-review.json').read_text())
        expected_claims = bind_claims(inv, reading, sources, reviews)
        if claims != expected_claims:
            errors.append('Binding differs from the separately retained occurrence review')
    except (ValueError, KeyError, FileNotFoundError) as exc:
        errors.append(str(exc))
    for c in inv['citation_occurrences']:
        previous = rows.get(c['id'], {})
        if previous.get('context_sha256') != hashlib.sha256(c['context_tex'].encode()).hexdigest():
            errors.append('Claim changed or unreviewed: '+c['id'])
        if previous.get('support_status') != 'supported_with_recorded_scope_after_author_review':
            errors.append('Missing support judgment: '+c['id'])
        if previous.get('source_sha256') != sources[c['key']]['sha256']:
            errors.append('Source edition changed: '+c['id'])
    for key in inv['cited_keys']:
        a = sources[key]
        p = ROOT/a['path']
        if digest(p) != a['sha256']:
            errors.append('Archive hash mismatch: '+key)
        expected = '_'+a['author_filename']+'('+str(a['year'])+')'
        if expected not in p.name:
            errors.append('Filename mismatch: '+key)
        if key not in reading or not reading[key]['quotes']:
            errors.append('Missing reading/quotation: '+key)
            continue
        sections = source_sections(p)
        full = normalized('\n'.join(t for _,t in sections))
        for quote in reading[key]['quotes']:
            match = normalized(quote['text']) in full
            page = re.search(r'PDF\s+p\.?\s*(\d+)',quote['location'])
            if p.suffix == '.pdf' and page:
                match = match and normalized(quote['text']) in normalized(sections[int(page[1])-1][1])
            quotes.append({'key':key, **quote, 'exact_after_typographic_normalization':match})
            if not match:
                errors.append('Quotation or page mismatch: '+key)
    result = {'status':'PASS' if not errors else 'FAIL','errors':errors,
              'documents':len(inv['cited_keys']),'occurrences':len(inv['citation_occurrences']),
              'quotes':quotes,'limits':'Validates recorded judgments and exact text/page identity, not independent source entailment or legal authority.'}
    (REVIEW/'citation-validation.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'quotes'},indent=2))
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
