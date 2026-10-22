"""Reusable P3 input for the retained BASF page-132 listed-notice scope."""
from pathlib import Path

REL = 'docs/implementation/prospectus-execution-authority/attempts/basf-margins/attempt-001'
PACKET_SHA256 = 'ad8b27c6803ff8363333341a6398a8eedb3c075575a220810984677b3cc4e095'


def interpretation_input(root, source, construction):
    from legalmath.prospectus.successor import basf_margin_scope, service
    from legalmath.prospectus.successor.contracts import digest, read
    root = Path(root)
    retained = root / REL
    packet_path = retained / 'scope-review.json'
    if digest(packet_path.read_bytes()) != PACKET_SHA256:
        raise ValueError('Retained BASF margin packet changed')
    packet = read(packet_path)
    for name, expected in packet['images'].items():
        if digest((root / name).read_bytes()) != expected:
            raise ValueError('Reviewed BASF margin page changed')
    payload = service.verify(source, 'P1')
    request, graph = payload['request'], payload['graph']
    service.verify(source, 'P1', request['bundle'], {'request': digest(request)})
    selected = service.verify(construction, 'P2', request['bundle'], {'P1': source['sha256']})
    return {'governing_admission': basf_margin_scope.admit(graph, selected['assembly'], request, packet)}
