"""Reusable BASF request with the retained source-specific prose reference packet."""
from pathlib import Path
import gzip
import json

REL = 'docs/implementation/prospectus-execution-authority/attempts/basf-references/attempt-001'


def prepared_request(root, graph=None):
    from legalmath.prospectus.successor import basf, basf_prose_references, jobs, source_graph
    from legalmath.prospectus.successor.admissions import dispositions
    from legalmath.prospectus.successor.contracts import digest, read
    root = Path(root)
    packet = read(root / REL / 'review.json')
    for path, expected in packet['images'].items():
        if digest((root / path).read_bytes()) != expected:
            raise ValueError('BASF prose reviewed page changed')
    graph = source_graph.build(jobs.basf_request(root)['bundle'], root) if graph is None else graph
    if digest(graph) != packet['graph_sha256']:
        raise ValueError('BASF prose source graph changed')
    # Reuse the immutable latest request instead of recursively reconstructing
    # every earlier review package. Validate its full identity before use.
    prior = root / 'docs/implementation/prospectus-integration-closure/basf-status-pledge/attempt-001/request.json.gz'
    binding = read(root / REL / 'prepare-started.json')
    if digest(prior.read_bytes()) != binding['baseline_sha256']:
        raise ValueError('Retained BASF status/pledge request changed')
    request = json.loads(gzip.decompress(prior.read_bytes()))
    if digest(request) != packet['request_sha256']:
        raise ValueError('BASF prose request differs from reviewed comparator')
    construction = basf.construct(graph, read(root / jobs.BASF))
    assembly = basf.as_assembly(graph, construction, request['construction']['scalar_admission'])
    assembly = dispositions(graph, assembly, request['reviewed_dispositions'])
    result, _ = basf_prose_references.prepare(graph, assembly, request, packet)
    return result
