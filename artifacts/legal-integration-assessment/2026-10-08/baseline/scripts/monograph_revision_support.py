"""Reversible manuscript edits layered over the protected unification record.

This proves which text changed. Semantic preservation remains a review judgment.
"""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'docs/monograph/review/revision'
ADDITION = re.compile(r'% BEGIN REVISION ADDITION ([^\n]+)\n(.*?)% END REVISION ADDITION \1\n', re.S)


def restore_revision(text, path):
    """Remove only registered additions and reverse exact registered prose edits."""
    registry = REVIEW / 'text-edits.json'
    if not registry.exists():
        return text
    data = json.loads(registry.read_text())
    local = str(Path(path).resolve().relative_to(ROOT))
    def remove(match):
        record = data['additions'][match[1]]
        assert record['path'] == local, f'Addition moved: {match[1]}'
        assert hashlib.sha256(match[2].encode()).hexdigest() == record['sha256'], f'Changed addition: {match[1]}'
        return ''
    text = ADDITION.sub(remove, text)
    for edit in reversed(data['edits']):
        if edit['path'] == local and edit['new'] in text:
            assert edit['reason'].strip()
            text = text.replace(edit['new'], edit['old'], 1)
    return text
