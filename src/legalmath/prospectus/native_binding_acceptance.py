"""Finite supported native binding evidence; never accepts a submitted PASS."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from .execution_authority import file_hash, read
from .successor import corrections, process_ledger, sealed_runtime as runtime, service
from .successor.contracts import digest

VERSION = 'native-binding-files.v1'
BASE = 'docs/implementation/prospectus-execution-authority/attempts/native-binding/'
PROTECTED = ('docs/implementation/prospectus-integration-closure/'
             'ocr-geometry-repair-2026-10-12/consumer/attempt-002/evidence/source-product.json.gz')
PROTECTED_HASH = '8ec9f35d664c5ef491093ce333c39f6c1ec7a4bf1ad5d1f3af8243e01360a69a'
PROTECTED_FILE_HASH = 'd6c43e6e24b310f1a26c6067ac79ec8431aa45df60213b16ab38ad6f310bf33f'
MODES = ('default', 'fresh', 'retained')
STAGES = ('prepare', 'tests', 'probe', 'controls',
          *[a + '-' + b for b in MODES for a in ('source', 'construct', 'finish')])
TESTS = ('tests/prospectus_successor/test_sealed_source.py',
         'tests/prospectus_successor/test_native_inputs.py',
         'tests/prospectus_successor/test_sealed_runtime.py',
         'tests/prospectus_successor/test_runtime_receipts.py',
         'tests/prospectus/test_native_binding_acceptance.py')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unpack(path):
    with gzip.open(path, 'rt') as stream:
        return json.load(stream)


def protected_source(path, file_sha256=PROTECTED_FILE_HASH, product_sha256=PROTECTED_HASH):
    require(file_hash(path) == file_sha256, 'Protected compressed file identity changed')
    value = unpack(path)
    service.verify(value, 'P1')
    require(value['sha256'] == product_sha256, 'Protected internal product identity changed')
    return value


def contained(root, name):
    require(isinstance(name, str), 'Evidence path is not text')
    path = (root / name).resolve(strict=True)
    require(path.is_relative_to(root.resolve()), 'Evidence path escapes root')
    return path


def verify_files(root, rows):
    require(isinstance(rows, dict) and bool(rows), 'Missing file bindings')
    for name, expected in rows.items():
        require(file_hash(contained(root, name)) == expected, 'Changed bound file: ' + name)


def snapshot(folder):
    manifest = runtime.validate(read(folder / 'manifest.json'))
    for row in manifest['files']:
        blob = contained(folder, 'blobs/' + row['sha256'])
        require(blob.stat().st_size == row['size'] and file_hash(blob) == row['sha256'],
                'Snapshot blob identity changed')
    return manifest


def receipt(folder, manifest):
    row = read(folder / 'receipt.json')
    streams = [(folder / name).read_bytes() for name in ('stdin', 'stdout', 'stderr')]
    runtime.verify_receipt(row, manifest, row['argv'], *streams)
    require(row['returncode'] == 0 and row['file_namespace'] ==
            'sealed explicit files; private proc/dev/tmp; no host directory mounts',
            'Native command failed or namespace claim changed')
    return row, streams


def products(folder):
    values = {k: unpack(folder / (k + '.json.gz')) for k in ('P1', 'P2', 'P3', 'P4', 'P5')}
    p1, p2, p3, p4, p5 = (values[k] for k in values)
    request = service.verify(p1, 'P1')['request']
    bundle = request['bundle']
    parents = {'P1': {'request': digest(request)}, 'P2': {'P1': p1['sha256']},
        'P3': {'P1': p1['sha256'], 'P2': p2['sha256']},
        'P4': {'P1': p1['sha256'], 'P3': p3['sha256']},
        'P5': {'P2': p2['sha256'], 'P3': p3['sha256']}}
    for key, value in values.items():
        service.verify(value, key, bundle, parents[key])
    graph, assembly, clauses = p1['payload']['graph'], p2['payload']['assembly'], p3['payload']['clauses']
    require(graph['bundle_sha256'] == digest(bundle), 'Graph bundle parent differs')
    require(assembly['source_graph_sha256'] == digest(graph), 'Assembly parent differs')
    require(clauses['assembly_sha256'] == digest(assembly), 'Clause parent differs')
    answer = unpack(folder / 'answer.json.gz')
    require(answer['report_sha256'] == digest({k: v for k, v in answer.items() if k != 'report_sha256'}),
            'Delivered answer identity differs')
    require(answer['consumed_products'] == {k: v['sha256'] for k, v in values.items()},
            'Delivered answer did not consume own products')
    require(answer['source_map'] == graph and answer['assembly'] == assembly and answer['clause_graph'] == clauses,
            'Delivered artifacts differ from products')
    require(answer['request_sha256'] == digest(request) and answer['source_graph_sha256'] == digest(graph),
            'Delivered request/graph parent differs')
    require(answer['independent_legal_acceptance'] is False and answer['may_execute_transaction'] is False,
            'Unsupported independent legal or transaction claim')
    return values, answer


def without(value, *fields):
    return {k: v for k, v in value.items() if k not in fields}


def semantic_products(values, answer):
    p2 = deepcopy(values['P2']['payload'])
    p2['assembly'].pop('source_graph_sha256')
    if 'source_report_readings' in p2:
        p2['source_report_readings'].pop('graph_sha256')
        p2['source_report_readings'].pop('input_sha256')
    p3 = deepcopy(values['P3']['payload'])
    p3['clauses'].pop('assembly_sha256')
    rest = without(answer, 'report_sha256', 'request_sha256', 'source_graph_sha256',
                   'consumed_products', 'source_map', 'assembly', 'clause_graph')
    return {'P2': p2, 'P3': p3, 'P4': values['P4']['payload'],
            'P5': values['P5']['payload'], 'answer': rest}


def compare_products(left, right):
    lv, la = left
    rv, ra = right
    require(la['source_map']['units'] == ra['source_map']['units'], 'Complete source units changed')
    require(semantic_products(lv, la) == semantic_products(rv, ra), 'Complete downstream semantics changed')
    for key in ('references', 'unresolved', 'context', 'source_authenticity', 'unit_count'):
        require(la['source_map'][key] == ra['source_map'][key], 'Source graph semantics changed: ' + key)


def source_request(original, mode):
    value = deepcopy(original)
    if mode == 'fresh':
        value['bundle']['documents'][0].pop('hybrid_ocr')
    value.pop('correction_admission')
    return value


def rebind(raw, original):
    graph = deepcopy(raw['payload']['graph'])
    request = deepcopy(raw['payload']['request'])
    packet = deepcopy(original['correction_admission'])
    packet['graph_sha256'] = digest(graph)
    graph['corrections'] = corrections.admit(graph, packet)
    request['correction_admission'] = packet
    request['source_report_readings']['graph_sha256'] = digest(graph)
    return service.seal('P1', request['bundle'], {'request': digest(request)},
                        {'request': request, 'graph': graph})


def check_request(values, folder, original, mode):
    from .successor.report_scope import readings
    raw = unpack(folder / 'raw-P1.json.gz')
    expected = source_request(original, mode)
    service.verify(raw, 'P1', expected['bundle'], {'request': digest(expected)})
    require(raw['payload']['request'] == expected, 'Original request instructions changed')
    require(values['P1'] == rebind(raw, original), 'Correction/readings parent rebind differs')
    request, graph = values['P1']['payload']['request'], values['P1']['payload']['graph']
    require(values['P2']['payload']['source_report_readings'] == readings(graph, request['source_report_readings']),
            'Actual report reading differs')


def check_geometry(graph, protected):
    require(graph['units'] == protected['units'], 'Protected original source units changed')
    units = [u for u in graph['units'] if u.get('geometry_issues')]
    require(len(units) == 1 and units[0]['id'] == 'bes-report-2009-pt:p177:ocr50'
            and units[0]['raw'] == ':' and units[0]['bbox'] is None
            and units[0]['words'][0]['bbox'] is None, 'Known unknown geometry was lost or fabricated')
    require(graph['corrections']['entries'] == protected['corrections']['entries'],
            'Original punctuation corrections changed')


def check_native(folder, manifest, values, mode, original_worker):
    graph = values['P1']['payload']['graph']
    doc = graph['documents'][0]
    first, fs = receipt(folder / 'native/0', manifest)
    second, ss = receipt(folder / 'native/1', manifest)
    expected_argv = ['/usr/bin/pdftotext', '-bbox-layout', '-enc', 'UTF-8']
    # The actual source path is checked by the worker stdin and manifest below.
    require(len(first['argv']) == 6 and first['argv'][:4] == expected_argv and first['argv'][-1] == '-'
            and first['argv'][4].endswith('/' + doc['path']) and fs[0] == b'', 'Wrong native text command')
    rows = {r['path']: r for r in manifest['files']}
    require(rows[first['argv'][4]]['sha256'] == doc['sha256'], 'Native text source unbound')
    require(first['limits']['max_stream_bytes'] == 64 * 1024 * 1024
            and second['limits']['max_stream_bytes'] == 20 * 1024 * 1024, 'Native capacities changed')
    require(first == doc['native_extraction']['sealed_execution'], 'Native text receipt not delivered')
    target = doc['runtime'] if mode == 'fresh' else doc['image_verification']['verification_runtime']
    require(second == target['sealed_execution'], 'OCR/verifier receipt not delivered')
    require(first['stdout']['sha256'] == doc['native_extraction']['raw_xml_sha256'], 'XML identity differs')
    spec, worker = json.loads(ss[0]), json.loads(ss[1])
    profile = doc['hybrid_profile']
    require(spec['source'] == first['argv'][4] and spec['source_sha256'] == doc['sha256']
            and spec['selected_pages'] == profile['pages'] and spec['page_count'] == profile['page_count']
            and spec['dpi'] == profile['dpi'] and spec['language'] == profile['language'],
            'OCR/verifier source profile differs')
    require(second['argv'] == ['/home/chakwong/miniconda3/envs/tfgpu/bin/python',
            first['argv'][4].split('/docs/')[0] + '/src/legalmath/prospectus/successor/ocr_worker.py'],
            'Wrong OCR/verifier executable')
    image_keys = ('page', 'image_sha256', 'image_width', 'image_height', 'width_points', 'height_points')
    if mode == 'fresh':
        require(not spec.get('verify_images_only') and worker['pages'] == original_worker['pages'],
                'Complete raw OCR words/text/images differ')
    else:
        require(spec.get('verify_images_only') is True and worker.get('verification_only') is True
                and worker['pages'] == [{k: p[k] for k in image_keys} for p in original_worker['pages']],
                'Complete verified images differ')
    require(worker['source_sha256'] == doc['sha256'] and worker['page_count'] == profile['page_count'],
            'Worker source identity differs')
    require(read(folder / 'receipts.json') == [first, second], 'Receipt inventory differs')


def check_controls(folder):
    rows = read(folder / 'actual-input-refusals.json')
    expected = {(a, b) for a in ('source', 'model', 'worker', 'executable') for b in ('wrong-hash', 'missing')}
    require(len(rows) == 8 and {(r['input'], r['mutation']) for r in rows} == expected,
            'Missing actual prelaunch control')
    for row in rows:
        require(row.get('refused') is True and type(row.get('processes_before')) is int
                and row.get('processes_before') == row.get('processes_after')
                and row.get('reason', '').startswith('Required native input absent or different:'),
                'Invalid actual prelaunch refusal')
    return len(rows)


def check_probe(folder, manifest):
    row, streams = receipt(folder / 'probe', manifest)
    value = json.loads(streams[1])
    evidence = read(folder / 'probe/control.json')
    require(value['environment'] == runtime.ENVIRONMENT and value['host_errno'] == 2
            and value['write_errno'] in (1, 13, 30) and value['sentinel'] == 'before-capture\n',
            'Actual namespace/environment/race control failed')
    require(evidence['host_existed'] is True and evidence['host_extra_environment'] == 'PROSPECTUS_HOST_ONLY'
            and evidence['before_sha256'] == digest(b'before-capture\n')
            and evidence['after_capture_sha256'] == digest(b'after-capture!\n')
            and evidence['restored_sha256'] == evidence['before_sha256'], 'Capture mutation evidence missing')
    require(evidence['host_path'] not in {r['path'] for r in manifest['files']}
            and evidence['sentinel_path'] in {r['path'] for r in manifest['files']}
            and row['argv'][1] == '-c' and evidence['program'] == row['argv'][2], 'Probe declaration differs')
    return row['receipt_sha256']


def current_methods(root, folder):
    methods = read(folder / 'frozen-methods.json')
    required = {str(p.relative_to(root)) for p in (root / 'src/legalmath/prospectus/successor').glob('*.py')}
    required |= {'src/legalmath/prospectus/native_binding_acceptance.py',
                 'scripts/prospectus_native_profile.py', *TESTS}
    require(required <= methods.keys(), 'Production/validator method inventory incomplete')
    verify_files(folder / 'method-final', methods)
    # The prototype was frozen before the real diagnostic. Acceptance code has
    # its own current admission; actual product/driver methods remain exact.
    acceptance_only = {'src/legalmath/prospectus/native_binding_acceptance.py',
                       'tests/prospectus/test_native_binding_acceptance.py'}
    verify_files(root, {k: v for k, v in methods.items() if k not in acceptance_only})
    historical = read(root / BASE / 'attempt-006/frozen-methods.json')
    verify_files(root, {k: v for k, v in historical.items() if k.startswith('src/')})
    return methods


def check_stages(folder):
    for stage in STAGES:
        start = read(folder / 'invocations' / stage / 'started.json')
        result = read(folder / 'invocations' / stage / 'result.json')
        require(result['status'] == ('FAIL' if stage == 'probe' else 'PASS')
                and 0 <= result['wall_seconds'] <= 120,
                'Required stage missing, failed or timed out: ' + stage)
        require(start['cpu_gpu'] == 'CPU only; GPUs intentionally hidden', 'CPU-only policy missing')
    suites = list(ET.parse(folder / 'tests.xml').getroot().iter('testsuite'))
    require(suites and sum(int(s.get('tests', 0)) for s in suites) >= 64
            and all(int(s.get(k, 0)) == 0 for s in suites for k in ('failures', 'errors', 'skipped')),
            'Required focused checks failed')
    names = {n.get('name', '').split('[')[0] for n in ET.parse(folder / 'tests.xml').getroot().iter('testcase')}
    require({'test_missing_matrix_cell_or_consumer_refuses', 'test_forged_pass_without_evidence_refuses',
             'test_complete_semantics_preserve_whitespace_and_unknowns', 'test_missing_control_refuses',
             'test_changed_receipt_refuses', 'test_stale_method_refuses'} <= names,
            'Required validator refusal tests missing')
    return sum(int(s.get('tests', 0)) for s in suites)


def check_default(folder, values, worker):
    doc = values['P1']['payload']['graph']['documents'][0]
    first, second = folder / 'native/0', folder / 'native/1'
    command = read(first / 'command.json')
    require(command['argv'] == ['pdftotext', '-bbox-layout', '-enc', 'UTF-8',
            str(folder).split('/docs/')[0] + '/' + doc['path'], '-']
            and command['timeout'] == 60 and (first / 'stdin').read_bytes() == b'',
            'Default native text command changed')
    require(file_hash(first / 'stdout') == doc['native_extraction']['raw_xml_sha256']
            and read(first / 'result.json')['returncode'] == 0
            and 'sealed_execution' not in doc['native_extraction'], 'Default native text evidence differs')
    command = read(second / 'command.json')
    spec, actual = read(second / 'stdin'), read(second / 'stdout')
    require(command['timeout'] == 60 and command['environment']['CUDA_VISIBLE_DEVICES'] == '-1'
            and read(second / 'result.json')['returncode'] == 0
            and spec['verify_images_only'] is True and actual['verification_only'] is True,
            'Default image verification was not executed')
    keys = ('page', 'image_sha256', 'image_width', 'image_height', 'width_points', 'height_points')
    require(actual['pages'] == [{k: p[k] for k in keys} for p in worker['pages']],
            'Default original images differ')
    require('sealed_execution' not in doc['image_verification']['verification_runtime'],
            'Default incorrectly claims selected runtime')


def consumer(root, values, answer):
    require(service.consume(values, root, include_artifacts=True) == answer,
            'Delivered answer differs from actual consumer')


def boundary_pair(failed, failed_streams, good, good_streams, manifest, control):
    runtime.verify_receipt(failed, manifest, failed['argv'], *failed_streams)
    runtime.verify_receipt(good, manifest, good['argv'], *good_streams)
    require(failed['returncode'] == 1 and
            b'loopback: Failed to create NETLINK_ROUTE socket: Operation not permitted' in failed_streams[2]
            and failed_streams[1] == b'' and good['returncode'] == 0
            and failed['argv'] == good['argv'] and failed['manifest_sha256'] == good['manifest_sha256'],
            'Unexplained failed/trusted boundary diagnostic')
    require(failed_streams[0] == good_streams[0] == b'', 'Probe stdin differs')
    value = json.loads(good_streams[1])
    require(value['environment'] == runtime.ENVIRONMENT and value['host_errno'] == 2
            and value['write_errno'] in (1, 13, 30) and value['sentinel'] == 'before-capture\n',
            'Trusted namespace/environment/race control failed')
    require(control['host_existed'] is True
            and control['before_sha256'] == digest(b'before-capture\n')
            and control['after_capture_sha256'] == digest(b'after-capture!\n')
            and control['restored_sha256'] == control['before_sha256'], 'Capture mutation evidence differs')
    rows = {r['path']: r for r in manifest['files']}
    require(control['host_path'] not in rows and control['sentinel_path'] in rows
            and rows[control['sentinel_path']]['sha256'] == control['before_sha256']
            and good['argv'][1] == '-c' and good['argv'][2] == control['program'], 'Probe declaration differs')
    return good['receipt_sha256']


def check_boundary_diagnostic(folder, manifest):
    failed = read(folder / 'probe/receipt.json')
    good = read(folder / 'trusted-permission-diagnostic/receipt.json')
    streams = lambda part: [(folder / part / n).read_bytes() for n in ('stdin', 'stdout', 'stderr')]
    control = read(folder / 'probe/control.json')
    hashed = boundary_pair(failed, streams('probe'), good, streams('trusted-permission-diagnostic'), manifest, control)
    require((folder / 'host-only-sentinel').read_bytes() == b'host-only\n', 'Host-only sentinel not retained')
    require(file_hash(folder / 'snapshot/blobs' / control['before_sha256']) == control['restored_sha256'],
            'Sentinel blob was not restored')
    diagnostic = folder / 'trusted-permission-diagnostic'
    start, result = read(diagnostic / 'started.json'), read(diagnostic / 'result.json')
    require(file_hash(diagnostic / 'method.py') == start['script_sha256'] and result['status'] == 'PASS'
            and result['returncode'] == 0 and result['wall_seconds'] <= 60
            and start['before'] == 4 and result['after'] == 5, 'Trusted diagnostic execution record differs')
    return hashed


def check_process_campaign(ledger):
    rows = ledger['reservations']
    require(ledger['limit'] == 12 and ledger['historical_lower_bound'] == 39 and len(rows) == 11
            and all(r['state'] == 'STARTED' for r in rows), 'Native process denominator differs')
    require([r['argv'][0] == '/usr/bin/bwrap' for r in rows] ==
            [False, False, False, True, True, False, False, True, True, True, True],
            'Actual source/probe launch sequence differs')
    return rows


def evidence(root, folder):
    """Recompute acceptance from retained products and bytes; no native launch."""
    root, folder = Path(root).resolve(), Path(folder).resolve()
    methods = current_methods(root, folder)
    test_count = check_stages(folder)
    manifest = snapshot(folder / 'snapshot')
    protected = protected_source(root / PROTECTED)
    original = protected['payload']['request']
    doc = original['bundle']['documents'][0]
    require(file_hash(root / doc['path']) == doc['sha256'], 'Original PDF changed')
    require(file_hash(root / doc['hybrid_ocr']['path']) == doc['hybrid_ocr']['sha256'], 'Retained OCR changed')
    worker = read(root / doc['hybrid_ocr']['path'])
    baseline = products(folder / 'default')
    check_request(baseline[0], folder / 'default', original, 'default')
    check_geometry(baseline[1]['source_map'], protected['payload']['graph'])
    check_default(folder / 'default', baseline[0], worker)
    consumer(root, *baseline)
    for mode in ('fresh', 'retained'):
        actual = products(folder / mode)
        check_request(actual[0], folder / mode, original, mode)
        check_geometry(actual[1]['source_map'], protected['payload']['graph'])
        check_native(folder / mode, manifest, actual[0], mode, worker)
        compare_products(baseline, actual)
        require(file_hash(folder / mode / 'native/0/stdout') == file_hash(folder / 'default/native/0/stdout'),
                'Complete default/selected XML bytes differ')
        consumer(root, *actual)
        require(actual[1]['source_map']['documents'][0]['scan_pages'] ==
                protected['payload']['graph']['documents'][0]['scan_pages'], 'Original page metadata changed')
    prior = root / BASE / 'attempt-006'
    verify_files(prior, read(prior / 'outputs.json'))
    old_manifest = snapshot(prior / 'snapshot')
    old_base = products(root / BASE / 'attempt-004')
    old_doc = old_base[0]['P1']['payload']['request']['bundle']['documents'][0]
    old_worker = read(root / old_doc['hybrid_ocr']['path'])
    for mode in ('fresh', 'retained'):
        old = products(prior / mode)
        check_native(prior / mode, old_manifest, old[0], mode, old_worker)
        compare_products(old_base, old)
        consumer(root, *old)
    controls = check_controls(folder)
    probe = check_boundary_diagnostic(folder, manifest)
    ledger = process_ledger.checked(folder / 'process-ledger.json')
    prior_ledger = process_ledger.checked(root / BASE / 'attempt-007/process-ledger.json')
    require(not prior_ledger['reservations'] and prior_ledger['limit'] == 12,
            'Previous failed preparation campaign changed')
    rows = check_process_campaign(ledger)
    return {'version': VERSION, 'scope': 'Finite Linux CPU explicit-file binding; three supported call sites',
            'matrix': ['2010-fresh-reused006', '2010-retained-reused006', '2009-default',
                       '2009-fresh', '2009-retained', 'actual-boundary-probe', 'eight-prelaunch-refusals'],
            'complete_source_units': len(protected['payload']['graph']['units']),
            'unknown_geometry_preserved': True, 'focused_tests': test_count, 'prelaunch_refusals': controls,
            'probe_receipt_sha256': probe, 'manifest_sha256': runtime.digest(manifest),
            'production_run_methods_sha256': digest(methods),
            'current_validator_sha256': file_hash(Path(__file__)),
            'native_processes': len(rows), 'cumulative_lower_bound': 39 + len(rows),
            'sandbox_refusal_retained': True, 'trusted_context_required': True,
            'native_reuse_allowed': False, 'independent_legal_acceptance': False,
            'portability_established': False, 'production_lifecycle_established': False, 'whole_program_complete': False}
