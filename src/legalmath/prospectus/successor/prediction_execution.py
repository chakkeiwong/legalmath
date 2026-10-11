"""Current-method execution for evaluation; supplied report hashes are insufficient."""
import importlib.metadata
from pathlib import Path
import sys
from .contracts import digest


def method():
    package = Path(__file__).resolve().parents[2]
    return {'python': sys.version,
        'code': {str(p.relative_to(package)): digest(p.read_bytes()) for p in sorted(package.rglob('*.py'))},
        'packages': {name: importlib.metadata.version(name) for name in ('legalmath', 'pypdf', 'z3-solver')}}


def execute(cohort, inputs):
    from .service import assess
    if set(inputs) != {c['id'] for c in cohort}:
        raise ValueError('Execution inputs differ from frozen cohort')
    fingerprint = digest(method())
    records, graphs = {}, {}
    for case in cohort:
        row = inputs[case['id']]
        if set(row) != {'request', 'root'} or digest(row['request']) != case.get('request_sha256'):
            raise ValueError('Execution request differs from frozen cohort')
        if row['request'].get('bank'):
            raise ValueError('Independent evaluation currently requires an immutable source-only request')
        report = assess(row['request'], row['root'])
        records[case['id']] = {'method_sha256': fingerprint, 'report': report}
        graphs[case['id']] = report['source_map']
    if digest(method()) != fingerprint:
        raise ValueError('Method changed during prediction execution')
    return records, graphs
