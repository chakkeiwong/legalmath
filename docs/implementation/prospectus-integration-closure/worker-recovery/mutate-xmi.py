"""Remove one semantic draft relation from an isolated authored XMI copy."""
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.successor import annotation_authoring, annotation_xmi  # noqa: E402


def main():
    if len(sys.argv) != 5:
        raise SystemExit('source.json authored.xmi TypeSystem.xml output.xmi required')
    source_path, xmi_path, types_path, output_path = map(Path, sys.argv[1:])
    data = json.loads(source_path.read_text())
    types = types_path.read_bytes()
    original = annotation_authoring.decode(xmi_path.read_bytes(), data['source'], data['text'], types=types)['packet']
    cas = annotation_xmi.load_export(xmi_path.read_bytes(), types)
    edges = list(cas.select(annotation_authoring.RELATION))
    if len(edges) != 1 or edges[0].relationId != 'authored-exception' or (
            [row['id'] for row in original['relations']] != ['authored-exception']):
        raise ValueError('Exactly one authored exception relation required')
    cas.remove(edges[0])
    changed = cas.to_xmi().encode()
    decoded = annotation_authoring.decode(changed, data['source'], data['text'], types=types)['packet']
    expected = deepcopy(original)
    expected['relations'] = []
    if decoded != expected:
        raise ValueError('Changed XMI differs beyond authored relation removal')
    output_path.write_bytes(changed)
    print(json.dumps({'status': 'RELATION_REMOVED', 'relations': decoded['relations']}))


if __name__ == '__main__':
    main()
