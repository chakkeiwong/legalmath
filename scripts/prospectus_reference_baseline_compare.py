"""Compare a fresh full reference result to the verified complete answer."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

FIELDS = {'call': 'relative_call_notices', 'payment': 'payment_method_references',
    'legacy': 'original_reference_review', 'governance': 'governance_references',
    'default': 'default_references', 'substitution': 'substitution_references',
    'financial': 'financial_references', 'internal': 'internal_references'}


def main():
    root, prep, here = map(Path, sys.argv[1:])
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'; sys.path.insert(0, str(root / 'src'))
    from legalmath.prospectus.successor import reviewed_references as core
    from legalmath.prospectus.successor.contracts import digest
    def read(path): return json.loads(gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes())
    def save(name, data):
        with (here / name).open('x') as output: json.dump(data, output, indent=2)
    config = read(prep / 'config.json'); binding = read(prep / 'baseline-binding.json')
    manifest = read(root / config['products'])
    for row in manifest['products'].values():
        assert hashlib.sha256((root / row['path']).read_bytes()).hexdigest() == row['sha256']
    products = {k: read(root / row['path']) for k, row in manifest['products'].items()}
    baseline = read(root / config['baseline'])
    assert digest(baseline) == binding['baseline_digest']
    assert baseline['consumed_products'] == {k: p['sha256'] for k, p in products.items()}
    graph, assembly = products['P1']['payload']['graph'], products['P2']['payload']['assembly']
    semantic = products['P3']['payload']
    request = {**products['P1']['payload']['request'], **(semantic.get('interpretation_input') or {})}
    before = digest((graph, assembly, request, semantic))
    save('comparison-loaded.json', {'input_sha256': before, 'baseline_digest': digest(baseline),
        'packet_references': len(request['reference_admission']['references'])})
    began = time.monotonic()
    with patch.object(core, 'admit', wraps=core.admit) as observed:
        actual = core.verify_consumed_families(graph, assembly, request, semantic)
        calls = observed.call_count
    expected = {name: baseline[field] for name, field in FIELDS.items()}
    assert actual == expected and calls == 1
    assert digest((graph, assembly, request, semantic)) == before
    result = {'status': 'PASS', 'exact_complete_reports_equal': True, 'inputs_unchanged': True,
        'families': list(actual), 'packet_references': len(request['reference_admission']['references']),
        'complete_packet_admissions': calls, 'report_sha256': digest(actual),
        'wall_seconds': time.monotonic() - began, 'runtime_role': 'DESCRIPTIVE_ONLY',
        'baseline': config['baseline'], 'cpu_gpu': 'CPU;GPU intentionally hidden'}
    save('comparison.json', result); print(json.dumps(result))


if __name__ == '__main__': main()
