"""Known corruption patterns in proposed prose; no legal or coherence oracle.

Keep exact originals for diagnosis. Only the presentation view is withheld;
source support, candidate commitments and executable comparisons are untouched.
"""
import re
from ...canonical import digest, raw_digest

PROFILE = 'legalmath.prose-patterns.v1'
PATTERNS = (
    ('SELF_REPAIR_CHATTER', re.compile(
        r"\b(?:we\s+need\s+valid\s+json|let['’]s\s+(?:produce|return|output)\s+"
        r"(?:valid\s+)?json|(?:i['’]ll|i\s+will)\s+(?:recompose|output)\s+"
        r"(?:two\s+)?readings|my\s+prior\s+(?:output\s+was\s+)?malformed)\b", re.I)),
    ('OUTPUT_INSTRUCTION_CHATTER', re.compile(
        r'\b(?:output\s+only\s+json\s*[,;:]?\s*no\s+markdown|final\s+only\s+json)\b', re.I)),
    ('PLACEHOLDER_ONLY', re.compile(
        r'^\s*(?:\[(?:TRUE_IS_PROHIBITED|TRUE_IS_COMPLIANT|TRUE_IS_SATISFIED|VALUE)\]\s*)?(?:\.{3,}|…+)\s*$')),
)


def narrative_fields(reading):
    for field in ('subject', 'statement', 'distinction'):
        yield [field], reading[field]
    for field in ('assumptions', 'questions'):
        for index, text in enumerate(reading[field]):
            yield [field, index], text
    if reading['formalization']:
        for index, fact in enumerate(reading['formalization']['facts']):
            for field in ('meaning', 'unit'):
                yield ['formalization', 'facts', index, field], fact[field]


def quoted_source_ranges(text, reading, packet):
    """Exempt authentic source quotations, not arbitrary quoted model chatter."""
    units = {u['unit_id']: u['text'] for u in packet['units']}
    ranges = []
    for citation in reading['citations']:
        quote = citation['quote']
        if not quote or units.get(citation['unit_id'], '').count(quote) != 1:
            continue
        start = text.find(quote)
        while start >= 0:
            end = start + len(quote)
            if (text.strip() == quote or
                    (start > 0 and end < len(text) and
                     (text[start - 1], text[end]) in (('"', '"'), ('“', '”'), ('‘', '’'), ("'", "'")))):
                ranges.append((start, end))
            start = text.find(quote, end)
    return ranges


def inspect_reading(reading, packet):
    findings = []
    fields = list(narrative_fields(reading))
    for path, text in fields:
        source_ranges = quoted_source_ranges(text, reading, packet)
        for kind, pattern in PATTERNS:
            # One finding per rule/field; retain the first non-source match.
            match = next((m for m in pattern.finditer(text)
                          if not any(a <= m.start() and m.end() <= b for a, b in source_ranges)), None)
            if match is None:
                continue
            start, end = max(0, match.start() - 60), min(len(text), match.end() + 80)
            findings.append({'kind': kind, 'field_path': path,
                             'field_sha256': raw_digest(text.encode('utf-8')),
                             'start': match.start(), 'end': match.end(),
                             'excerpt_start': start, 'excerpt_end': end, 'excerpt': text[start:end]})
    return {'profile': PROFILE, 'reading_hash': digest(reading),
            'status': 'FLAGGED' if findings else 'NO_PATTERN_DETECTED',
            'scanned_fields': len(fields), 'total_findings': len(findings),
            'findings': findings[:64], 'truncated': len(findings) > 64,
            'offset_units': 'Unicode code points in the original field',
            'legal_fidelity_evaluated': False, 'coherence_established': False}


def presentation(candidates, packet):
    """A consumer-facing view and a separate diagnostic record for raw readings."""
    diagnostics = {cid: inspect_reading(reading, packet) for cid, reading in candidates.items()}
    view = {cid: {'reading_hash': diagnostics[cid]['reading_hash'],
                  'status': 'WITHHELD_CORRUPT_PROSE' if diagnostics[cid]['total_findings'] else 'NO_PATTERN_DETECTED',
                  'proposal': None if diagnostics[cid]['total_findings'] else reading}
            for cid, reading in candidates.items()}
    return diagnostics, {'profile': PROFILE, 'candidates': view,
                         'limits': 'Pattern diagnostics only; readable prose and legal correctness are not established.'}
