"""Acceptance controls use genuine small products; no native subprocesses."""
from copy import deepcopy
import gzip
import hashlib
import json

import pytest

from legalmath.prospectus import native_binding_acceptance as acceptance
from legalmath.prospectus.execution_authority import write
from legalmath.prospectus.successor import service, sealed_runtime as runtime
from legalmath.prospectus.successor.contracts import VERSION, digest


def pack(path, value):
    path.write_bytes(gzip.compress(json.dumps(value).encode(), mtime=0))


def actual_products(tmp_path):
    source = tmp_path / 'source.txt'
    source.write_text('The Notes will be redeemed at maturity.\nAn unresolved condition remains.')
    date = '2026-01-01T00:00:00Z'
    request = {'version': VERSION, 'bundle': {'instrument_id': 'synthetic', 'purpose': 'review',
        'issue_date': date, 'effective_at': date, 'known_at': date, 'documents': [{
            'id': 'd', 'path': str(source), 'format': 'text', 'sha256': digest(source.read_bytes()),
            'language': 'en', 'authority': 'Synthetic acceptance control'}]}}
    p1 = service.source_product(request, tmp_path)
    p2 = service.construction_product(p1, tmp_path)
    p3 = service.interpretation_product(p1, p2)
    values = {'P1': p1, 'P2': p2, 'P3': p3, 'P4': service.law_product(p1, p3),
              'P5': service.financial_product(p1, p2, p3)}
    answer = service.consume(values, tmp_path, include_artifacts=True)
    for name, value in {**values, 'answer': answer}.items():
        pack(tmp_path / (name + '.json.gz'), value)
    return values, answer


def test_actual_small_products_are_verified_and_reconsumed(tmp_path):
    values, answer = actual_products(tmp_path)
    assert acceptance.products(tmp_path) == (values, answer)
    acceptance.consumer(tmp_path, values, answer)


def test_compressed_file_and_internal_product_identities_are_distinct(tmp_path):
    values, _ = actual_products(tmp_path)
    path = tmp_path / 'P1.json.gz'
    file_sha, product_sha = acceptance.file_hash(path), values['P1']['sha256']
    assert file_sha != product_sha
    assert acceptance.protected_source(path, file_sha, product_sha) == values['P1']
    with pytest.raises(ValueError, match='compressed file'):
        acceptance.protected_source(path, product_sha, product_sha)
    with pytest.raises(ValueError, match='internal product'):
        acceptance.protected_source(path, file_sha, file_sha)


@pytest.mark.parametrize('missing', ['P1', 'P3', 'P5', 'answer'])
def test_missing_matrix_cell_or_consumer_refuses(tmp_path, missing):
    actual_products(tmp_path)
    (tmp_path / (missing + '.json.gz')).unlink()
    write(tmp_path / 'result.json', {'status': 'PASS'})
    with pytest.raises(FileNotFoundError):
        acceptance.products(tmp_path)


def test_forged_pass_without_evidence_refuses(tmp_path):
    write(tmp_path / 'result.json', {'status': 'PASS', 'all_cells_pass': True})
    write(tmp_path / 'verification.json', {'status': 'PASS'})
    with pytest.raises((FileNotFoundError, ValueError)):
        acceptance.evidence(tmp_path, tmp_path)


@pytest.mark.parametrize('change', ['whitespace', 'unknown', 'P4', 'answer'])
def test_complete_semantics_preserve_whitespace_and_unknowns(tmp_path, change):
    original = actual_products(tmp_path)
    modified = deepcopy(original)
    if change == 'whitespace':
        modified[1]['source_map']['units'][0]['raw'] += ' '
    elif change == 'unknown':
        modified[1]['source_map']['unresolved'].append({'unit': 'unrecorded'})
    elif change == 'P4':
        modified[0]['P4']['payload']['question']['status'] = 'FABRICATED'
    else:
        modified[1]['questions']['Q1']['status'] = 'FABRICATED'
    with pytest.raises(ValueError, match='changed'):
        acceptance.compare_products(original, modified)


def test_rehashed_answer_still_requires_actual_consumer(tmp_path):
    values, answer = actual_products(tmp_path)
    answer = deepcopy(answer)
    answer['questions']['Q1']['status'] = 'FABRICATED'
    answer['report_sha256'] = digest({k: v for k, v in answer.items() if k != 'report_sha256'})
    pack(tmp_path / 'answer.json.gz', answer)
    acceptance.products(tmp_path)
    with pytest.raises(ValueError, match='actual consumer'):
        acceptance.consumer(tmp_path, values, answer)


def test_rehashed_wrong_parent_refuses(tmp_path):
    values, _ = actual_products(tmp_path)
    p = values['P3']
    p['inputs']['P1'] = '0'*64
    p['sha256'] = digest({k: v for k, v in p.items() if k != 'sha256'})
    pack(tmp_path / 'P3.json.gz', p)
    with pytest.raises(ValueError, match='parent'):
        acceptance.products(tmp_path)


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'launched', 'empty-count'])
def test_missing_control_refuses(tmp_path, change):
    rows = [{'input': a, 'mutation': b, 'refused': True, 'processes_before': 3, 'processes_after': 3,
             'reason': 'Required native input absent or different: /case'}
            for a in ('source', 'model', 'worker', 'executable') for b in ('wrong-hash', 'missing')]
    write(tmp_path / 'actual-input-refusals.json', rows)
    assert acceptance.check_controls(tmp_path) == 8
    if change == 'missing':
        rows.pop()
    elif change == 'duplicate':
        rows[-1] = rows[0]
    elif change == 'launched':
        rows[0]['processes_after'] = 4
    else:
        rows[0].pop('processes_before')
        rows[0].pop('processes_after')
    write(tmp_path / 'actual-input-refusals.json', rows)
    with pytest.raises(ValueError, match='control|refusal'):
        acceptance.check_controls(tmp_path)


def test_changed_receipt_refuses(tmp_path):
    manifest = {'version': runtime.VERSION, 'files': [{'path': '/case/worker', 'mode': 0o555,
        'size': 3, 'sha256': hashlib.sha256(b'abc').hexdigest()}], 'directories': [],
        'environment': dict(runtime.ENVIRONMENT), 'native_reuse_allowed': False}
    streams = {'stdin': b'', 'stdout': b'actual', 'stderr': b''}
    row = {'version': 'sealed-native-execution.v2', 'returncode': 0, 'manifest_sha256': runtime.digest(manifest),
        'argv': ['/case/worker'], 'trusted_runtime': runtime.trusted_runtime(),
        'file_namespace': 'sealed explicit files; private proc/dev/tmp; no host directory mounts',
        'native_reuse_allowed': False, 'limits': {'max_stream_bytes': 1024},
        **{k: {'sha256': hashlib.sha256(v).hexdigest(), 'bytes': len(v)} for k, v in streams.items()}}
    row['receipt_sha256'] = runtime.digest(row)
    write(tmp_path / 'receipt.json', row)
    for name, data in streams.items():
        (tmp_path / name).write_bytes(data)
    acceptance.receipt(tmp_path, manifest)
    (tmp_path / 'stdout').write_bytes(b'forged')
    with pytest.raises(ValueError, match='stream mismatch'):
        acceptance.receipt(tmp_path, manifest)


def test_stale_method_refuses(tmp_path):
    source = tmp_path / 'method.py'
    source.write_text('old')
    rows = {'method.py': acceptance.file_hash(source)}
    acceptance.verify_files(tmp_path, rows)
    source.write_text('new')
    with pytest.raises(ValueError, match='Changed bound file'):
        acceptance.verify_files(tmp_path, rows)


def test_binding_does_not_allow_evidence_path_escape(tmp_path):
    root = tmp_path / 'root'
    root.mkdir()
    outside = tmp_path / 'outside'
    outside.write_text('bad')
    with pytest.raises(ValueError, match='escapes root'):
        acceptance.verify_files(root, {'../outside': acceptance.file_hash(outside)})


def boundary_fixture():
    control = {'host_existed': True, 'host_path': '/host-only', 'sentinel_path': '/sentinel',
        'before_sha256': digest(b'before-capture\n'), 'after_capture_sha256': digest(b'after-capture!\n'),
        'restored_sha256': digest(b'before-capture\n'), 'program': 'synthetic boundary control'}
    manifest = {'version': runtime.VERSION, 'files': [{'path': '/sentinel', 'mode': 0o444,
        'size': len(b'before-capture\n'), 'sha256': control['before_sha256']}], 'directories': [],
        'environment': dict(runtime.ENVIRONMENT), 'native_reuse_allowed': False}
    argv = ['/worker', '-c', control['program']]
    out = json.dumps({'environment': runtime.ENVIRONMENT, 'host_errno': 2,
        'write_errno': 30, 'sentinel': 'before-capture\n'}).encode()
    fs = [b'', b'', b'bwrap: loopback: Failed to create NETLINK_ROUTE socket: Operation not permitted\n']
    gs = [b'', out, b'']
    def row(code, streams):
        value = {'version': 'sealed-native-execution.v2', 'returncode': code,
            'manifest_sha256': runtime.digest(manifest), 'argv': list(argv),
            'trusted_runtime': runtime.trusted_runtime(), 'native_reuse_allowed': False,
            'file_namespace': 'sealed explicit files; private proc/dev/tmp; no host directory mounts',
            'limits': {'max_stream_bytes': 4096},
            **{n: {'sha256': digest(s), 'bytes': len(s)} for n, s in zip(('stdin','stdout','stderr'),streams)}}
        value['receipt_sha256'] = runtime.digest(value)
        return value
    return row(1, fs), fs, row(0, gs), gs, manifest, control


@pytest.mark.parametrize('mutation', ['wrong-error', 'different-command', 'failed-trusted',
                                      'environment-leak', 'host-visible', 'race-lost', 'host-declared'])
def test_boundary_diagnostic_refuses_false_explanations(mutation):
    failed, fs, good, gs, manifest, control = boundary_fixture()
    acceptance.boundary_pair(failed, fs, good, gs, manifest, control)
    if mutation == 'wrong-error':
        fs[2] = b'unrelated worker crash'
    elif mutation == 'different-command':
        good['argv'][2] = 'different diagnostic'
    elif mutation == 'failed-trusted':
        good['returncode'] = 1
    elif mutation == 'host-declared':
        control['host_path'] = '/sentinel'
    else:
        output = json.loads(gs[1])
        if mutation == 'environment-leak':
            output['environment']['HOST_LEAK'] = 'bad'
        elif mutation == 'host-visible':
            output['host_errno'] = 0
        else:
            output['sentinel'] = 'after-capture!\n'
        gs[1] = json.dumps(output).encode()
    for row, streams in ((failed, fs), (good, gs)):
        row.update({n: {'sha256': digest(s), 'bytes': len(s)}
                    for n, s in zip(('stdin','stdout','stderr'),streams)})
        row['receipt_sha256'] = runtime.digest({k: v for k, v in row.items() if k != 'receipt_sha256'})
    with pytest.raises(ValueError):
        acceptance.boundary_pair(failed, fs, good, gs, manifest, control)


@pytest.mark.parametrize('mutation', ['lost-failure', 'extra-start', 'larger-budget', 'wrong-order', 'not-started'])
def test_campaign_preserves_failed_launch_and_allowance(mutation):
    sequence = [False,False,False,True,True,False,False,True,True,True,True]
    ledger = {'limit': 12, 'historical_lower_bound': 39,
        'reservations': [{'state':'STARTED','argv':['/usr/bin/bwrap' if selected else '/python']}
                         for selected in sequence]}
    assert len(acceptance.check_process_campaign(ledger)) == 11
    if mutation == 'lost-failure':
        ledger['reservations'].pop(3)
    elif mutation == 'extra-start':
        ledger['reservations'].append(deepcopy(ledger['reservations'][-1]))
    elif mutation == 'larger-budget':
        ledger['limit'] = 13
    elif mutation == 'wrong-order':
        ledger['reservations'][5]['argv'][0] = '/usr/bin/bwrap'
    else:
        ledger['reservations'][0]['state'] = 'RESERVED'
    with pytest.raises(ValueError):
        acceptance.check_process_campaign(ledger)
