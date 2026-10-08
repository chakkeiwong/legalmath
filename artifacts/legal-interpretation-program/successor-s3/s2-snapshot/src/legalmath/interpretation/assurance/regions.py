"""Conservative source-region reconciliation; semantic changes never normalise away."""
from collections import Counter
from difflib import SequenceMatcher
import math
import re

from ...errors import LegalMathError
from .diversity import identity


def normal(text):
    return re.sub(r'\s+', ' ', text).strip()


def validate_region(region):
    if (not isinstance(region.get('text'), str) or not region.get('source_sha256') or
        not region.get('route') or type(region.get('page')) is not int or region['page'] < 1):
        raise LegalMathError('E_SCHEMA')
    box = region.get('bbox')
    if box is not None and (len(box) != 4 or any(type(x) not in (int, float) or not math.isfinite(x) for x in box)
                            or box[2] <= box[0] or box[3] <= box[1]):
        raise LegalMathError('E_SCHEMA', details='Invalid source region geometry')
    return region


def compare_regions(left, right):
    validate_region(left); validate_region(right)
    if (left['source_sha256'], left['page']) != (right['source_sha256'], right['page']):
        raise LegalMathError('E_STALE_REVIEW', details='Region editions or pages differ')
    a, b = normal(left['text']), normal(right['text'])
    # Sequence tokens retain punctuation, inequality signs, case and units.
    at, bt = a.split(), b.split()
    changes = [{'kind': kind, 'left_tokens': at[i:j], 'right_tokens': bt[k:l],
                'left_interval': [i, j], 'right_interval': [k, l]}
               for kind, i, j, k, l in SequenceMatcher(None, at, bt, autojunk=False).get_opcodes()
               if kind != 'equal']
    return {'status': 'WHITESPACE_EQUIVALENT' if a and a == b else 'MATERIALITY_UNRESOLVED',
            'left': left, 'right': right, 'changes': changes,
            'same_token_multiset': Counter(at) == Counter(bt),
            'empty_evidence': not a or not b, 'meaning_established': False,
            'shared_dependencies': ['retained source'], 'release_eligible': False}


def reconcile_page(source_sha256, page, routes, *, raster_sha256=None, boxes=None, links=()):
    """Preserve every route, including failures and unique content.

    Boxes locate comparison regions; they do not assert paragraph or footnote
    attachment. Table/footnote links require explicit source-bound evidence.
    """
    if len(routes) < 2 or any(not isinstance(t, str) for t in routes.values()):
        raise LegalMathError('E_SCHEMA')
    names = list(routes); anchor = names[0]
    region = lambda name: {'source_sha256': source_sha256, 'page': page, 'route': name,
                           'text': routes[name], 'bbox': (boxes or {}).get(name)}
    comparisons = [compare_regions(region(anchor), region(name)) for name in names[1:]]
    issues = []
    for row in comparisons:
        if row['status'] == 'WHITESPACE_EQUIVALENT': continue
        for change in row['changes'] or [{'kind': 'empty', 'left_tokens': [], 'right_tokens': [],
                                         'left_interval': [0, 0], 'right_interval': [0, 0]}]:
            text = ' '.join(change['left_tokens'] + change['right_tokens'])
            kind = ('NUMBER_OR_UNIT' if re.search(r'\d|[%$<>≥≤]', text) else
                    'QUALIFIER_OR_NEGATION' if re.search(r'\b(not|unless|except|only|other than|footnote)\b', text, re.I)
                    else 'TEXT_OR_ORDER')
            issue = {'source_sha256': source_sha256, 'page': page,
                     'routes': [anchor, row['right']['route']], 'change': change,
                     'kind': kind, 'status': 'UNRESOLVED', 'raster_sha256': raster_sha256}
            issue['issue_id'] = 'region.' + identity(issue)[:24]
            issue['eligible_actions'] = ['INSPECT_REGION', 'OCR_REGION', 'COMPARE_OFFICIAL_TEXT']
            issues.append(issue)
    link_findings = []
    for link in links:
        if (link.get('source_sha256') != source_sha256 or link.get('page') != page or
            link.get('kind') not in ('FOOTNOTE_ATTACHMENT', 'TABLE_HEADER') or
            not link.get('evidence') or link.get('status') != 'SOURCE_SUPPORTED'):
            link_findings.append({'kind': 'UNRESOLVED_LAYOUT_RELATION', 'proposal': link})
    if raster_sha256 is None:
        link_findings.append({'kind': 'VISUAL_ROUTE_UNAVAILABLE'})
    return {'source_sha256': source_sha256, 'page': page, 'raster_sha256': raster_sha256, 'comparisons': comparisons,
            'issues': issues, 'layout_links': list(links), 'findings': link_findings,
            'status': 'UNCERTAINTY_RETAINED' if issues or link_findings else 'OBSERVED_SOURCE_AGREEMENT',
            'materiality_classification': 'Conservative diagnostic; no model vote resolves meaning',
            'release_eligible': False}


def choose_region_action(issue, attempted):
    """Choose new evidence by failure, without retrying until a vote agrees."""
    order = (['INSPECT_REGION', 'OCR_REGION', 'COMPARE_OFFICIAL_TEXT']
             if issue['kind'] in ('NUMBER_OR_UNIT', 'QUALIFIER_OR_NEGATION') else
             ['COMPARE_OFFICIAL_TEXT', 'INSPECT_REGION', 'OCR_REGION'])
    return next((a for a in order if a not in attempted), None)
