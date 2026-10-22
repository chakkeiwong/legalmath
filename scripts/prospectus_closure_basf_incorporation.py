"""Retained BASF P3 review with margin scope and unresolved incorporation."""
from pathlib import Path

REL = 'docs/implementation/prospectus-execution-authority/attempts/basf-incorporation/attempt-001'
PACKET_SHA256 = 'a49932fd9aa7a75e1c98af3cb09acb3ef42d0152e8b99301b066ffa9ac87691c'


def interpretation_input(root, source, construction):
    from scripts.prospectus_closure_basf_margin_scope import interpretation_input as margin_input
    from legalmath.prospectus.successor import basf_incorporation, service
    from legalmath.prospectus.successor.contracts import digest, read
    root = Path(root)
    path = root / REL / 'review.json'
    if digest(path.read_bytes()) != PACKET_SHA256:
        raise ValueError('Retained BASF incorporation packet changed')
    bindings = read(root / REL / 'source-review-bindings.json')
    for name, expected in bindings['images'].items():
        if digest((root / name).read_bytes()) != expected:
            raise ValueError('Reviewed BASF incorporation image changed')
    result = margin_input(root, source, construction)
    packet = read(path)
    graph = service.verify(source, 'P1')['graph']
    selected = service.verify(construction, 'P2')['selected_contract']
    basf_incorporation.admit(graph, selected, packet)
    return {**result, 'incorporation_admission': packet}
