"""Exact retained-source comparison against the frozen pre-repair validators."""
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

FAMILIES = ('call', 'payment', 'legacy', 'governance', 'default', 'substitution', 'financial', 'internal')


def load_before(prep, name):
    path = prep / 'before' / (name + '.py')
    bindings = json.loads((prep / 'before.json').read_text())
    key = 'src/legalmath/prospectus/successor/' + name + '.py'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == bindings[key]
    if name.startswith('basf_'):
        resources = json.loads((prep / 'before-resources.json').read_text())
        resource = path.with_name(name + '_spec.json')
        assert hashlib.sha256(resource.read_bytes()).hexdigest() == resources[
            'src/legalmath/prospectus/successor/' + resource.name]
    spec = importlib.util.spec_from_file_location('legalmath.prospectus.successor.before372_' + name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def old_families(prep, graph, assembly, request, semantic):
    # The frozen functions import admit from the current module. Its function
    # source must remain identical; comparison does not substitute the repair.
    import inspect
    from legalmath.prospectus.successor import reviewed_references
    original = load_before(prep, 'reviewed_references')
    assert inspect.getsource(original.admit) == inspect.getsource(reviewed_references.admit)
    reports = {}
    for name in FAMILIES:
        if name == 'internal': original.verify_consumed(graph, assembly, request, semantic)
        module = load_before(prep, 'basf_' + name + '_references')
        reports[name] = module.verify_consumed(graph, assembly, request, semantic)
    return reports


def main():
    root, prep, here = map(Path, sys.argv[1:])
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'; sys.path.insert(0, str(root / 'src'))
    from legalmath.prospectus.successor import reviewed_references
    from legalmath.prospectus.successor.contracts import digest
    def read(path):
        return json.loads(gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes())
    config = read(prep / 'config.json')
    products = {k: read(root / row['path']) for k, row in read(root / config['products'])['products'].items()}
    graph, assembly = products['P1']['payload']['graph'], products['P2']['payload']['assembly']
    semantic = products['P3']['payload']
    request = {**products['P1']['payload']['request'], **(semantic.get('interpretation_input') or {})}
    before = digest((graph, assembly, request, semantic)); timings = {}
    began = time.monotonic(); expected = old_families(prep, graph, assembly, request, semantic)
    timings['frozen_seconds'] = time.monotonic() - began
    original_admit = reviewed_references.admit
    began = time.monotonic()
    with patch.object(reviewed_references, 'admit', wraps=original_admit) as observed:
        actual = reviewed_references.verify_consumed_families(graph, assembly, request, semantic)
        calls = observed.call_count
    timings['candidate_seconds'] = time.monotonic() - began
    assert actual == expected and calls == 1
    assert digest((graph, assembly, request, semantic)) == before
    result = {'status': 'PASS', 'exact_complete_reports_equal': True, 'inputs_unchanged': True,
        'family_count': len(actual), 'packet_references': len(request['reference_admission']['references']),
        'complete_packet_admissions_in_candidate': calls, 'report_sha256': digest(actual),
        'input_sha256': before, 'timings_descriptive_only': timings,
        'cpu_gpu': 'CPU;GPU intentionally hidden'}
    with (here / 'comparison.json').open('x') as output: json.dump(result, output, indent=2)
    print(json.dumps(result))


if __name__ == '__main__': main()
