"""Retain discovered official B1 inputs; build source-bound development catalog.

No network or model invocation. Inputs are complete files downloaded from the
listed official links, verified by signatures/extraction before use. Never infer
a historical FAQ edition from a current page's original publication date.
"""
from datetime import datetime, timezone
from pathlib import Path
import re
from legalmath.canonical import raw_digest
from legalmath.interpretation.assurance.sources import extract_document
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.assurance.authorities import AuthorityCatalog

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'.localresources/sfc-authorities/b1'
PREFIX = 'https://www.sfc.hk/-/media/EN/assets/components/codes/files-current/web/codes/code-of-conduct-for-persons-licensed-by-or-registered-with-the-securities-and-futures-commission/'
URLS = {
    'index': ('sfc-codes.html', 'https://www.sfc.hk/en/Rules-and-standards/Codes-and-guidelines/Codes', 'text/html'),
    'code.current': ('code-current.pdf', PREFIX + 'Code_of_conduct-Dec-2025_Eng-Final-with-Bookmark_Jan-2026.pdf?rev=8768a10c17c44385ab1ad8c0a29d2844', 'application/pdf'),
    'code.2023': ('code-sep2023.pdf', PREFIX + 'Code_of_conduct-Sep-2023_Eng-Final-with-Bookmark.pdf?rev=209e9f3b717e4d70b45bfe45a0bb6288', 'application/pdf'),
    'faq.2010': ('faq-2010.html', 'https://www.sfc.hk/en/faqs/intermediaries/supervision/Code-of-Conduct/30-Sep-2010---Code-of-Conduct', 'text/html'),
}
TITLE = 'Code of Conduct for Persons Licensed by or Registered with the Securities and Futures Commission'


def prepare():
    if OUT.exists():
        raise ValueError('Keep the frozen catalog; create a successor rather than overwrite')
    OUT.mkdir(parents=True)
    now = datetime.now(timezone.utc).isoformat(); documents = {}; editions = []
    for eid, (filename, url, media) in URLS.items():
        raw = (Path('/tmp')/('legalmath-' + filename)).read_bytes()
        doc = {'url': url, 'data': raw, 'media_type': media}
        extracted = extract_document(doc); documents[eid] = {**doc, **extracted}
        (OUT/filename).write_bytes(raw); (OUT/(filename+'.txt')).write_text(extracted['text'])
        save(OUT/(filename+'.extraction.json'), {k:v for k,v in extracted.items() if k not in ('text', 'secondary_text')})
        editions.append({'edition_id': eid, 'authority_id': 'sfc.code' if eid.startswith('code.') else 'sfc.'+eid.split('.')[0],
                         'url': url, 'raw_sha256': raw_digest(raw), 'text_sha256': extracted['text_sha256'],
                         'media_type': media, 'path': filename, 'retrieved_at': now,
                         'published_on': None, 'effective_from': None, 'effective_until': None,
                         'temporal_evidence': [], 'temporal_status': 'UNKNOWN'})
    def anchor(eid, text):
        start = documents[eid]['text'].index(text)
        return {'edition_id': eid, 'start': start, 'end': start + len(text), 'quote': text}
    identity = anchor('index', TITLE)
    for e in editions:
        if e['edition_id'] == 'code.2023':
            e.update(published_on='2023-09-25', effective_from='2023-09-25', effective_until='2024-01-19',
                     temporal_status='DOCUMENTED_INTERVAL', temporal_evidence=[anchor('index', '25 Sep 2023 - 18 Jan 2024')])
        elif e['edition_id'] == 'code.current':
            e.update(published_on='2026-01-02', effective_from='2026-01-02', temporal_status='DOCUMENTED_INTERVAL',
                     temporal_evidence=[anchor('index', '2 Jan 2026')])
        elif e['edition_id'] == 'faq.2010':
            # The retained page explicitly says Q2/Q4 were updated in 2024.
            # Its 2010 last-update label is not a full historical-version proof.
            e.update(published_on='2010-09-30', temporal_evidence=[anchor('faq.2010', 'Last update: 30 Sep 2010')])
    authorities = [{'authority_id': aid, 'issuer': 'Securities and Futures Commission', 'jurisdiction': 'Hong Kong',
                    'kind': kind, 'title': title, 'identity_evidence': [evidence]}
                   for aid, kind, title, evidence in (
                       ('sfc.code', 'CODE', TITLE, identity),
                       ('sfc.index', 'SOURCE_INDEX', 'SFC codes index', identity),
                       ('sfc.faq', 'FAQ', 'Code of Conduct FAQ, 30 September 2010', anchor('faq.2010', TITLE)))]
    provisions = []
    for eid in ('code.2023', 'code.current'):
        text = documents[eid]['text']
        paragraphs = list(re.finditer(r'3\.11\s+Use of gifts.*?In promoting.*?fees or charges\.', text, re.S))
        # Restrict the retained paragraph to its actual normative page, not the TOC.
        match = next(m for m in paragraphs if '\f' not in m.group()) if any('\f' not in m.group() for m in paragraphs) else None
        if match is None:
            start = text.rfind('3.11', 0, text.find('fees or charges.'))
            end = text.find('fees or charges.', start) + len('fees or charges.')
        else:
            start, end = match.span()
        if not 0 <= start < end:
            raise ValueError('Cannot locate actual paragraph 3.11')
        # The Code's interpretation/application pages carry remote definitions.
        pages = text.split('\f'); offset = 0; regions = []
        for page_no, page in enumerate(pages, 1):
            if (re.search(r'Unless\s+otherwise\s+specified', page) and 'Schedule 1' in page or
                    re.search(r'1\.1\s+Definition', page) and re.search(r'1\.3\s+Persons', page)):
                regions.append({'region_id': 'context.'+str(page_no), 'role': 'CONTEXT',
                    'anchor': {'edition_id': eid, 'start': offset, 'end': offset+len(page), 'quote': page}})
            offset += len(page) + 1
        regions.insert(0, {'region_id': 'paragraph.3.11', 'role': 'PROVISION',
                          'anchor': {'edition_id': eid, 'start': start, 'end': end, 'quote': text[start:end]}})
        provisions.append({'provision_id': eid+'.3.11', 'authority_id': 'sfc.code', 'edition_id': eid, 'locator': '3.11',
            'regions': regions, 'requires': [],
            'unresolved_references': ['SFO Schedule 1 definitions; SFO section 167 and Banking Ordinance section 20(10) referenced in interpretation/application context'],
            'context_status': 'PROPOSED_SELECTION',
            'selection_basis': 'Actual paragraph 3.11 plus interpretation/definition pages inspected locally; remote statutory definitions remain unresolved.'})
    text = documents['faq.2010']['text']; start = text.index('Q1'); end = text.index('Q2', start)
    provisions.append({'provision_id': 'faq.2010.q1', 'authority_id': 'sfc.faq', 'edition_id': 'faq.2010', 'locator': 'Question 1',
        'regions': [{'region_id': 'q1', 'role': 'PROVISION', 'anchor': {'edition_id': 'faq.2010', 'start': start, 'end': end, 'quote': text[start:end]}}],
        'requires': [], 'unresolved_references': ['Paragraph 3.11, edition applicable at the requested date'],
        'context_status': 'PROPOSED_SELECTION',
        'selection_basis': 'Complete Q1/A1 block in currently retained official page; historical edition and external Code context unresolved.'})
    aliases = [{'locator': title, 'authority_id': aid, 'provision_locator': ploc, 'evidence': [evidence],
                'basis': 'Exact locator declared from the retained A7 source inventories, supported by official title/section text.'}
               for title, aid, ploc, evidence in (
                   ('Paragraph 3.11, '+TITLE, 'sfc.code', '3.11', identity),
                   ('SFC frequently asked questions on the Code of Conduct, issued 30 September 2010, answer to question 1', 'sfc.faq', 'Question 1', anchor('faq.2010', 'Last update: 30 Sep 2010')),
                   ('Answer to question 1, SFC frequently asked questions on the Code of Conduct, issued 30 September 2010', 'sfc.faq', 'Question 1', anchor('faq.2010', 'Last update: 30 Sep 2010')))]
    value = {'version': 'authority-catalog.v1', 'authorities': authorities, 'editions': editions,
             'provisions': provisions, 'aliases': aliases, 'relationships': []}
    AuthorityCatalog(value, documents)
    save(OUT/'catalog.json', value)
    finalize()


def finalize():
    catalog = AuthorityCatalog.load(OUT/'catalog.json')
    for edition in catalog.value['editions']:
        if raw_digest((OUT/edition['path']).read_bytes()) != edition['raw_sha256']:
            raise ValueError('Retained input changed before finalization')
    if (OUT/'manifest.json').exists():
        raise ValueError('Already finalized; preserve the existing snapshot')
    save(OUT/'acquisition.json', {'retrieved_at': catalog.value['editions'][0]['retrieved_at'],
        'sources': {k:list(v) for k,v in URLS.items()}, 'evidence_class': 'RETAINED_OFFICIAL_PUBLIC_DOCUMENTS',
        'discovery': 'Official codes index and official supervision FAQ index',
        'failed_discovery': ['Web search returned HTTP 502 twice', 'Guessed circular API URLs returned 404',
                             'Guessed PDF URL returned soft 404 HTML; it was rejected'],
        'limits': ['Publisher edition-date ranges do not establish legal applicability of every provision',
                   'The currently retained 2010 FAQ page is not an independently archived 2010 version']})
    save(OUT/'manifest.json', {'files': {str(p.relative_to(OUT)): raw_digest(p.read_bytes()) for p in sorted(OUT.iterdir()) if p.is_file()}})
    print('Retained four complete official sources with exact spans and explicit version/context uncertainties:', OUT)


if __name__ == '__main__':
    prepare()
