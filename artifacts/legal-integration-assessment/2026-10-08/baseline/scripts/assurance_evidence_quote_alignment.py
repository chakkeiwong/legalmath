"""Explicit, uniquely located ASCII capitalization repairs; original responses retained."""
from copy import deepcopy
import re
from legalmath.canonical import digest


def align(value, task, aliases):
    units = {u['unit_id']: u['text'] for u in task['request']['source_packet']['units']}
    repaired = deepcopy(value)
    records = []
    def visit(node, path):
        if isinstance(node, list):
            for i, item in enumerate(node):
                visit(item, path+[i])
        elif isinstance(node, dict):
            if set(node) == {'unit_id', 'quote'} and isinstance(node['quote'], str):
                uid = aliases['tokens'].get(node['unit_id'], node['unit_id'])
                source, quote = units.get(uid), node['quote']
                if source is not None and quote and source.count(quote) == 0:
                    matches = list(re.finditer(re.escape(quote), source, re.IGNORECASE|re.ASCII))
                    if len(matches) == 1:
                        match = matches[0]
                        literal = source[match.start():match.end()]
                        admissible = len(literal) == len(quote) and all(
                            a == b or (a.isascii() and b.isascii() and a.isalpha() and b.isalpha() and a.lower() == b.lower())
                            for a, b in zip(quote, literal))
                        if admissible and source.count(literal) == 1:
                            records.append({'path': path+['quote'], 'unit_id': uid,
                                'original_quote': quote, 'source_exact_quote': literal,
                                'source_text_hash': digest(source), 'start': match.start(), 'end': match.end(),
                                'rule': 'Unique contiguous source match; ASCII letter capitalization only; no other character changed.'})
                            node['quote'] = literal
            for key, item in node.items():
                visit(item, path+[key])
    visit(repaired, [])
    return repaired, records
