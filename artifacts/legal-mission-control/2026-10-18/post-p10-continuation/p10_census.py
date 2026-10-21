"""Separate processed, validated and failed accounts; test existing local repair."""
from diagnose import *
from legalmath.interpretation.assurance.phased import account_recovery
from legalmath.interpretation.assurance.answer_acceptance import MENTION, BRACKET_NUMBER
from legalmath.interpretation.assurance.phased.account_contract import prose_fields

folder = WORK / 'p10-census'
folder.mkdir(exist_ok=False)
began = time.monotonic()
program = read(ROOT / PROGRAM)
service = provider()
service.complete = service.fork = service.allowance.reserve = forbidden
p = product('p10', service, folder, program)
directory = ROOT / 'artifacts/legal-mission-control/2026-10-17/gap-refresh/settled-recovery/live/common/p10'
snapshots = {}
for name in ('requirement-details.json', 'calls/dispatch.json'):
    path = directory / name
    data = path.read_bytes()
    target = folder / ('snapshot-' + path.name)
    target.write_bytes(data)
    snapshots[name] = {'original_path': str(path.relative_to(ROOT)), 'snapshot': ref(ROOT, target)}
details = read(folder / 'snapshot-requirement-details.json')
dispatch = read(folder / 'snapshot-dispatch.json')
applicable = {r['id']: (i, r) for i, r in enumerate(r for r in p.route.records.values()
    if r['kind'] in ('obligation', 'reading', 'case')) if p.applicable(r, 'p10')}
require(len({r['id'] for r in details}) == len(details) and set(r['id'] for r in details) <= set(applicable),
    'Duplicate or foreign processed account')
failures = []
references = []
for row in details:
    if row['result']['status'] == 'VALIDATED':
        continue
    index, record = applicable[row['id']]
    key = f'detail-{index}'
    leaf_rows = []
    for call, state in dispatch['calls'].items():
        if not (call == key or call.startswith(key + '-part-')) or state['status'] != 'FAILED':
            continue
        call_dir = directory / 'calls' / call
        refs = {name: ref(ROOT, call_dir / (name + '.json')) for name in ('request', 'schema', 'result')}
        references.extend(refs.values())
        request, schema, result = (read(ROOT / refs[name]['path']) for name in ('request', 'schema', 'result'))
        require(digest(result) == state['result_hash'] and digest(request) == result['request_hash'],
            'Changed failure fixture')
        failure = {'key': call, 'result': result, 'inputs': refs,
                   'prior_correction': 'account_correction' in request}
        if result.get('reason') == 'Numbered assertion has no document/proposition binding':
            raw_ref = ref(ROOT, call_dir / 'raw.json')
            references.append(raw_ref)
            value = read(ROOT / raw_ref['path'])['value']
            fields = [path for path, text in prose_fields(value) if MENTION.search(text) or BRACKET_NUMBER.search(text)]
            annotation = account_recovery.correction_value({'raw': raw_ref, 'prose_fields': fields,
                                                          'required_source_gaps': value['source_gaps']})
            original, _ = account_recovery.baseline_request(request, schema, root=ROOT)
            failure['existing_correction_validation'] = checked(lambda:
                account_recovery.validate_retained_correction(ROOT, annotation, original))
            failure['prose_fields'] = fields
        leaf_rows.append(failure)
    require(leaf_rows, 'Failed account lacks a reproduced failed dispatch')
    failures.append({'root': key, 'requirement_id': row['id'], 'failed_dispatches': leaf_rows})
for reference in references:
    verify(ROOT, reference)
require(not attempted, 'Zero-call diagnostic attempted external operation')
report = {'profile': 'post-p10-account-census.v1', 'at_utc': datetime.now(timezone.utc).isoformat(),
    'applicable': len(applicable), 'processed': len(details),
    'validated': sum(r['result']['status'] == 'VALIDATED' for r in details),
    'failed': len(failures), 'unprocessed': len(applicable) - len(details),
    'unprocessed_roots': [f'detail-{i}' for rid, (i, _) in applicable.items() if rid not in {r['id'] for r in details}],
    'failures': failures, 'snapshots': snapshots, 'immutable_failure_inputs': references,
    'provider_calls': 0, 'production_state_modified': False, 'legal_acceptance': False,
    'environment': sys.executable, 'devices': 'CPU only; CUDA_VISIBLE_DEVICES=-1',
    'command': [sys.executable, str(Path(__file__).relative_to(ROOT))],
    'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'source': ref(ROOT, Path(__file__)), 'diagnostic_library': ref(ROOT, WORK / 'diagnose.py'),
    'plan': 'docs/implementation/legal-mission-control/results/post-p10-continuation-2026-10-18.md',
    'wall_seconds': time.monotonic() - began}
save(folder / 'result.json', report)
print(json.dumps({k: report[k] for k in ('applicable', 'processed', 'validated', 'failed', 'unprocessed', 'provider_calls')}))
