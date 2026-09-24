"""Labelled source edits and executable mutants; no invented legal ground truth."""
from copy import deepcopy
import re
from ...canonical import digest
from .sources import normalized


def source_challenges(packet):
    cases = []
    for unit in packet['units']:
        text = unit['text']
        patterns = [('EXCEPTION_REMOVED', r'\s*\(other than [^)]*\)', ''),
                    ('MODALITY_CHANGED', r'\bmust\b', 'may'),
                    ('THRESHOLD_CHANGED', r'(?<=at least )\d+', None),
                    ('DATE_CHANGED', r'\b\d{4}-\d{2}-\d{2}\b', '2099-12-31')]
        for kind, pattern, replacement in patterns:
            match = re.search(pattern, text, re.I)
            if match is None:
                continue
            replacement = str(int(match.group()) + 1) if replacement is None else replacement
            changed = text[:match.start()] + replacement + text[match.end():]
            if changed == text:
                continue
            cases.append({'kind': kind, 'unit_id': unit['unit_id'], 'before': text, 'after': changed,
                          'expected_relation': 'MATERIAL_TEXT_CHANGE', 'label_basis': 'CONTROLLED_EDIT_NOT_LEGAL_OUTCOME',
                          'source_packet_hash': digest(packet)})
        cases.append({'kind': 'WHITESPACE_CONTROL', 'unit_id': unit['unit_id'], 'before': text,
                      'after': re.sub(r'\s+', '  ', text), 'expected_relation': 'SAME_NORMALIZED_TEXT',
                      'label_basis': 'WHITESPACE_ONLY', 'source_packet_hash': digest(packet)})
    return cases


def run_source_challenges(packet, check):
    """Run a caller-specified source-change checker, keeping detection distinct from accuracy."""
    results = []
    for case in source_challenges(packet):
        detected = check(case['before'], case['after'])
        if type(detected) is not bool:
            raise ValueError('Challenge detector must return a Boolean change finding')
        expected = case['expected_relation'] == 'MATERIAL_TEXT_CHANGE'
        results.append({**case, 'detected': detected, 'passed': detected == expected})
    return {'cases': results, 'passed': bool(results) and all(r['passed'] for r in results),
            'target': 'SENSITIVITY_TO_CONTROLLED_TEXT_CHANGES', 'legal_accuracy_evaluated': False}


def meaning_sensitive_change(before, after):
    # This only detects non-whitespace changes. A semantic checker must separately
    # decide their legal consequence; harmless paraphrases are not assumed equal.
    return normalized(before) != normalized(after)


def formula_mutants(reading):
    if not reading['formalization']:
        return []
    text = reading['formalization']['result']; values = []
    patterns = [('BOUNDARY_STRICT', r'\(>= ', '(> '),
                ('EXCEPTION_OMITTED', r'\(not ([a-z][a-z0-9_.-]*)\)', 'true'),
                ('CONJUNCTION_WEAKENED', r'\(and ', '(or ')]
    for kind, pattern, replacement in patterns:
        for match in list(re.finditer(pattern, text))[:6]:
            r = deepcopy(reading)
            r['formalization']['result'] = text[:match.start()] + replacement + text[match.end():]
            r['distinction'] = 'Seeded engineering mutation: ' + kind
            values.append({'kind': kind, 'reading': r, 'source_interpretation': False})
    return values


def executable_campaign(reading, packet, checker):
    rows = []
    for mutant in formula_mutants(reading):
        result = checker.compare(reading, mutant['reading'], packet)
        rows.append({'kind': mutant['kind'], 'mutant': mutant['reading'], 'comparison': result,
                     'behavior_changed': result['status'] == 'DIFFERENT'})
    return {'mutants': rows, 'legal_accuracy_evaluated': False,
            'interpretation': 'Differences are source-unreviewed fault probes, not rival legal readings'}
