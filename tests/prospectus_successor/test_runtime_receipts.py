from copy import deepcopy
import hashlib
import json
import subprocess
import sys

import pytest

from legalmath.prospectus.successor import sealed_runtime as runtime, process_ledger


def receipt_fixture():
    manifest = {'version': runtime.VERSION, 'files': [{'path': '/case/worker', 'mode': 0o555,
        'size': 3, 'sha256': hashlib.sha256(b'abc').hexdigest()}], 'directories': [],
        'environment': dict(runtime.ENVIRONMENT), 'native_reuse_allowed': False}
    argv, stdin, out, err = ['/case/worker'], b'{"page":88}', b'actual output', b'actual diagnostic'
    streams = {k: {'sha256': hashlib.sha256(v).hexdigest(), 'bytes': len(v)}
               for k, v in [('stdin', stdin), ('stdout', out), ('stderr', err)]}
    receipt = {'version': 'sealed-native-execution.v1', 'returncode': 0, 'manifest_sha256': runtime.digest(manifest),
        'argv': argv, **streams, 'trusted_runtime': runtime.trusted_runtime(),
        'file_namespace': 'sealed explicit files; private proc/dev/tmp; no host directory mounts',
        'native_reuse_allowed': False}
    receipt['receipt_sha256'] = runtime.digest(receipt)
    return receipt, manifest, argv, stdin, out, err


@pytest.mark.parametrize('field', ['manifest', 'argv', 'stdin', 'stdout', 'stderr', 'exit', 'runtime', 'hash', 'reuse'])
def test_receipt_rejects_changed_evidence(field):
    receipt, manifest, argv, stdin, out, err = receipt_fixture()
    assert runtime.verify_receipt(receipt, manifest, argv, stdin, out, err)
    if field == 'manifest': manifest['files'][0]['sha256'] = '0' * 64
    if field == 'argv': argv = [*argv, '--different-page']
    if field == 'stdin': stdin += b' '
    if field == 'stdout': out += b' '
    if field == 'stderr': err += b' '
    if field == 'exit': receipt['returncode'] = 1
    if field == 'runtime': receipt['trusted_runtime']['kernel_release'] = 'different'
    if field == 'hash': receipt['receipt_sha256'] = '0' * 64
    if field == 'reuse': receipt['native_reuse_allowed'] = True
    with pytest.raises(ValueError): runtime.verify_receipt(receipt, manifest, argv, stdin, out, err)


def test_rehashed_old_runtime_still_refuses_current_check():
    values = list(receipt_fixture())
    receipt = values[0]
    receipt['trusted_runtime']['launcher_method_sha256'] = '0' * 64
    receipt['receipt_sha256'] = runtime.digest({k: v for k, v in receipt.items() if k != 'receipt_sha256'})
    with pytest.raises(ValueError, match='method/tool/kernel'):
        runtime.verify_receipt(*values)
    assert runtime.verify_receipt(*values, require_current=False)


@pytest.mark.parametrize('cap',[0,True,64*1024*1024+1,1])
def test_receipt_v2_refuses_invalid_or_insufficient_cap(cap):
    values=list(receipt_fixture());receipt=values[0]
    receipt.update(version='sealed-native-execution.v2',limits={'max_stream_bytes':4096})
    receipt['receipt_sha256']=runtime.digest({k:v for k,v in receipt.items() if k!='receipt_sha256'})
    assert runtime.verify_receipt(*values)
    receipt['limits']['max_stream_bytes']=cap
    receipt['receipt_sha256']=runtime.digest({k:v for k,v in receipt.items() if k!='receipt_sha256'})
    with pytest.raises(ValueError,match='bound'):
        runtime.verify_receipt(*values)


def test_ledger_refuses_actual_second_launch_before_marker_write(tmp_path):
    ledger = tmp_path / 'ledger.json'
    marker = tmp_path / 'should-not-exist'
    process_ledger.create(ledger, 1, 18, 'actual finite child control')
    with process_ledger.observe(ledger):
        first = subprocess.run([sys.executable, '-c', 'print("first")'], capture_output=True, text=True, check=True)
        with pytest.raises(ValueError, match='budget exhausted'):
            subprocess.run([sys.executable, '-c', 'from pathlib import Path;Path(' + repr(str(marker)) + ').write_text("bad")'])
    assert first.stdout.strip() == 'first' and not marker.exists()
    assert len(process_ledger.checked(ledger)['reservations']) == 1


def test_failed_launch_consumes_reservation_and_corruption_refuses(tmp_path):
    ledger = tmp_path / 'ledger.json'
    process_ledger.create(ledger, 1, 18, 'failed launch is not free')
    with process_ledger.observe(ledger):
        with pytest.raises(FileNotFoundError): subprocess.Popen(['/prospectus-no-such-executable'])
    assert process_ledger.checked(ledger)['reservations'][0]['state'] == 'SPAWN_FAILED'
    with pytest.raises(ValueError, match='budget exhausted'): process_ledger.reserve(ledger, ['/bin/true'])
    data = json.loads(ledger.read_text())
    data['reservations'].clear()
    ledger.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='Invalid'): process_ledger.checked(ledger)
