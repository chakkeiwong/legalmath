"""Narrow printed scope cues for review; no governing relation is admitted."""
from collections import defaultdict
import math
import re
from statistics import median

from .contracts import digest
from .occurrences import anchor
from .relation_discovery import _spans, _valid_box

_RATINGS = re.compile(r"(?:Credit\s+)?Ratings?\s*:", re.I)
_GRADE = re.compile(r"[^:\n]{1,80}:\s*(?:[A-Ca-c]{1,3}[1-3]?[+-]?|D|NR|WR|Not Rated)")
_SECTION = re.compile(r"\d+[.,)]")
_MARGIN_START = re.compile(r"^Folgendes\s+gilt\s+für\b")
_MARGIN = re.compile(
    r"Folgendes\s+gilt\s+für\s+alle\s+Optionen\s+von\s+"
    r"([A-Za-z0-9][\w/+.-]*(?:\s+[\w/+.-]+){0,4})[.:]?")


def _lines(units, height):
    lines = []
    for unit in sorted(units, key=lambda u: (u['bbox'][1], u['bbox'][0], u['id'])):
        if not lines or unit['bbox'][1] - lines[-1][0]['bbox'][1] > .5 * height:
            lines.append([])
        lines[-1].append(unit)
    return [sorted(line, key=lambda u: (u['bbox'][0], u['id'])) for line in lines]


def _text(units):
    return ' '.join(u['raw'].strip() for u in units)


def _connected(line, height):
    # Separated simultaneous columns are not one fragmented printed line.
    return all(0 <= b['bbox'][0] - a['bbox'][2] <= 2 * height
               for a, b in zip(line, line[1:]))


def _paragraph(lines, index, height):
    block = []
    bottom = min(u['bbox'][1] for u in lines[index])
    for line in lines[index:]:
        top = min(u['bbox'][1] for u in line)
        if top - bottom > .8 * height:
            break
        if not _connected(line, height):
            return []
        block.extend(line)
        bottom = max(u['bbox'][3] for u in line)
    return block


def _complete(units):
    return bool(units and re.search(r'[.!?][\]”"]*$', _text(units)))


def _proposal(kind, left, right, marker, scope, rule):
    edge = {'kind': kind, 'from': _spans(left), 'to': _spans(right),
            'scope_marker': anchor(marker, 0, len(marker['raw'])),
            'scope': scope, 'rule': rule,
            'basis': 'RAW_TEXT_AND_GEOMETRY; NO REVIEWED_TARGET_INPUT',
            'status': 'REQUIRES_REVIEW', 'legal_scope_established': False}
    return {'id': 'relation-candidate:' + digest(edge), **edge}


def _ratings(content, height):
    labels = [u for u in content if _RATINGS.fullmatch(u['raw'].strip())]
    if len(labels) != 1:
        return [], 'NO_UNIQUE_RATINGS_LABEL'
    label = labels[0]
    top = label['bbox'][1]
    stop = min((u['bbox'][1] for u in content
                if u['bbox'][1] > top + height and u['bbox'][0] <= label['bbox'][2] + height
                and _SECTION.fullmatch(u['raw'].strip())), default=math.inf)
    intros = [u for u in content if abs(u['bbox'][1] - top) <= .5 * height
              and u['bbox'][0] > label['bbox'][2] + height
              and re.search(r'\brated\s*:\s*$', u['raw'], re.I)]
    if len(intros) != 1:
        return [], 'NO_UNIQUE_RATING_INTRODUCTION'
    intro = intros[0]
    lines = _lines([u for u in content
                    if u['bbox'][0] >= intro['bbox'][0] - .5 * height
                    and top - .5 * height <= u['bbox'][1] < stop - .5 * height], height)
    if not lines or lines[0] != [intro]:
        return [], 'AMBIGUOUS_RATING_COLUMN'
    grades = []
    bottom = intro['bbox'][3]
    index = 1
    while index < len(lines):
        line = lines[index]
        if (not _connected(line, height) or not _GRADE.fullmatch(_text(line))
                or min(u['bbox'][1] for u in line) - bottom > 2.25 * height):
            break
        grades.extend(line)
        bottom = max(u['bbox'][3] for u in line)
        index += 1
    if not grades:
        return [], 'NO_CONTIGUOUS_PRINTED_GRADES'
    candidates = []
    for position in range(index, len(lines)):
        if not re.match(r'^In\s+general\b', _text(lines[position]), re.I):
            continue
        block = _paragraph(lines, position, height)
        text = _text(block)
        if (_complete(block) and re.search(r'\bare\s+restricted\b', text, re.I)
                and re.search(r'\bratings?\b', text, re.I)
                and re.search(r'\bregulatory\b', text, re.I)):
            candidates.append(_proposal('qualifies', block, grades, label,
                'Regulatory use of the stated credit ratings (candidate)', 'explicit-ratings-restriction.v1'))
    return candidates, 'PRINTED_RATINGS_SCOPE_ONLY'


def _margins(content, height):
    candidates = []
    for seed in content:
        if not _MARGIN_START.match(seed['raw'].strip()):
            continue
        column = _lines([u for u in content
                         if abs(u['bbox'][0] - seed['bbox'][0]) <= .5 * height
                         and u['bbox'][1] >= seed['bbox'][1] - .5 * height], height)
        if not column or column[0] != [seed]:
            continue
        margin = _paragraph(column, 0, height)
        match = _MARGIN.fullmatch(_text(margin))
        if not match:
            continue
        right = max(u['bbox'][2] for u in margin)
        starts = _lines([u for u in content if u['bbox'][0] > right + height
                         and abs(u['bbox'][1] - seed['bbox'][1]) <= height], height)
        if len(starts) != 1 or not _connected(starts[0], height):
            continue
        left = min(u['bbox'][0] for u in starts[0])
        top = min(u['bbox'][1] for u in starts[0])
        lines = _lines([u for u in content if u['bbox'][0] >= left - .5 * height
                        and u['bbox'][1] >= top - .5 * height], height)
        body = _paragraph(lines, 0, height)
        if not _complete(body):
            continue
        subject = match[1].rstrip('.:')
        candidates.append(_proposal('governs', margin, body, seed,
                                    f'all {subject} options', 'explicit-german-option-scope.v1'))
    return candidates


def scoped_candidates(graph):
    """Called after the common discovery source/hash and JSON checks."""
    pages = defaultdict(list)
    for unit in graph['units']:
        pages[(unit['document'], unit['source_sha256'], unit['page'])].append(unit)
    candidates, diagnostics = [], []
    for (document, source, page), units in sorted(pages.items()):
        info = {'document': document, 'source_sha256': source, 'page': page}
        if any(not _valid_box(u.get('bbox')) or
               any(not _valid_box(w.get('bbox')) for w in u.get('words', [])) for u in units):
            diagnostics.append({**info, 'reason': 'SCOPE_REFUSED_UNKNOWN_GEOMETRY', 'proposed': 0})
            continue
        content = [u for u in units if any(c.isalnum() for c in u['raw'])]
        if not content:
            continue
        height = median(u['bbox'][3] - u['bbox'][1] for u in content)
        ratings, reason = _ratings(content, height)
        margins = _margins(content, height)
        candidates.extend(ratings + margins)
        diagnostics.append({**info, 'reason': reason, 'rating_candidates': len(ratings),
                            'margin_candidates': len(margins), 'proposed': len(ratings) + len(margins)})
    return candidates, diagnostics
