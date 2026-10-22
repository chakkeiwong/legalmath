"""Offline adversarial checks for acquisition evidence, never legal acceptance."""
import json
from pathlib import Path
import subprocess
import tempfile
import time
from unittest.mock import patch
from scripts import prospectus_statutory_sources_accounted as s


def refused(function, *args):
    try:
        function(*args)
    except (AssertionError, ValueError, FileExistsError):
        return
    raise AssertionError('Required refusal did not occur')


def main():
    began = time.monotonic()
    checks = []
    for url in ('http://www.govinfo.gov/test', 'https://example.org/test',
                'https://user@www.govinfo.gov/test', 'https://www.govinfo.gov:8443/test'):
        refused(s.checked_url, url)
    checks.append('Nonofficial, insecure, credential-bearing and unreviewed-port URLs refused')
    requests = s.read(s.PREP / 'requests.json')['requests']
    assert len(requests) == 15 and len({r['id'] for r in requests}) == 15
    for row in requests:
        s.checked_url(row['url'])
    checks.append('All15 initial exact HTTPS candidates have approved official hosts')
    with tempfile.TemporaryDirectory(prefix='prospectus-source-probe-') as scratch:
        root = Path(scratch)
        here, prep = root / 'attempt', root / 'review'
        original_prep = root / 'original-review'
        authority = root / 'authority'
        for name in (s.PLAN, s.METHOD, s.PREFLIGHT_METHOD, s.ORIGINAL_PLAN, s.ORIGINAL_METHOD, s.ORIGINAL_PREFLIGHT_METHOD):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('Offline budget-accounting fixture only\n')
        s.save(prep / 'baseline.json', {'resources': {'probe_only': True}, 'accounting_start': {'active_program_bytes': 0, 'history_names': []}})
        rows = [{'id': key, 'url': 'https://www.govinfo.gov/' + key, 'purpose': 'OFFLINE'}
                for key in ('redirect', 'valid', 'timeout', 'bad-encoding', 'stage-expiry')]
        s.save(prep / 'requests.json', {'requests': rows})

        def fake_curl(command, **kwargs):
            assert '--location' not in command and '-L' not in command and '--retry' not in command
            body = Path(command[command.index('--output') + 1])
            headers = Path(command[command.index('--dump-header') + 1])
            if command[-1].endswith('/timeout'):
                raise subprocess.TimeoutExpired(command, 25)
            code = 302 if command[-1].endswith('/redirect') else 200
            body.write_bytes(b'<html><p>\xff</p></html>' if command[-1].endswith('/bad-encoding')
                             else b'<html><title>Offline source</title><p>A &amp; B</p></html>')
            headers.write_text('HTTP/2 ' + str(code) + '\n')
            return subprocess.CompletedProcess(command, 0,
                json.dumps({'http_code': code, 'url_effective': command[-1]}).encode(), b'')

        with patch.multiple(s, ROOT=root, HERE=here, PREP=prep, ORIGINAL_PREP=original_prep, AUTH=authority), patch.object(s, 'frozen', lambda: None), \
             patch.object(s.subprocess, 'run', fake_curl):
            # The real budget and receipt code runs; admission is irrelevant to
            # this isolated offline test and is bypassed only in this process.
            result = s.acquire('redirect')
            assert result['status'] == 'UNAVAILABLE_RESPONSE_RETAINED'
            refused(s.extract, 'redirect')
            refused(s.acquire, 'redirect')
            checks.append('302 retained once, never followed, not accepted for extraction; unchanged retry refused')
            s.acquire('valid')
            s.extract('valid')
            assert (here / 'local/extract-valid/text.txt').read_text().strip().endswith('A & B')
            (here / 'requests/valid/body').write_bytes(b'altered')
            refused(s.extract, 'valid')
            checks.append('Actual retained raw bytes required; tampering refused before extraction')
            result = s.acquire('timeout')
            assert result['status'] == 'UNAVAILABLE_RESPONSE_RETAINED'
            assert s.costs()['GET_attempts'] == 3
            checks.append('Timeout retained and counted together with successes and redirects')
            s.acquire('bad-encoding')
            try:
                s.extract('bad-encoding')
            except UnicodeDecodeError:
                pass
            else:
                raise AssertionError('Corrupt encoding accepted')
            failed = s.read(here / 'local/extract-bad-encoding/receipt.json')
            assert failed['status'] == 'FAIL' and failed['wall_seconds'] >= 0
            refused(s.extract, 'bad-encoding')
            checks.append('Extraction decoding failure retained and counted; unchanged retry refused')
            s.acquire('stage-expiry')
            with patch.object(s.SourceHTML, 'feed', side_effect=TimeoutError('Bound probe')):
                try:
                    s.extract('stage-expiry')
                except TimeoutError:
                    pass
                else:
                    raise AssertionError('Whole-stage timeout swallowed')
            failed = s.read(here / 'local/extract-stage-expiry/receipt.json')
            assert failed['status'] == 'FAIL' and failed['error_type'] == 'TimeoutError'
            assert s.costs()['GET_attempts'] == 5
            checks.append('Local-stage timeout retained and accounted without another acquisition')
            with patch.object(s, 'contexts', lambda: {'status': 'PASS', 'probe_only': True}):
                assert s.local('contexts')['status'] == 'PASS'
            assert s.read(here / 'local/contexts/receipt.json')['status'] == 'PASS'
            with patch.object(s, 'seal', lambda: {'status': 'PASS', '_manifest': {'probe_only': True}}):
                assert s.local('seal')['status'] == 'PASS'
            assert s.read(here / 'result.json')['resources']['GET_attempts'] == 5
            assert (here / 'outputs.json').is_file()
            checks.append('Local completion receipt precedes final cost accounting and exclusive seal; no self-interruption refusal')
            before = s.costs()['additional_bytes']
            revision = authority / 'revisions/0282.json'
            revision.parent.mkdir(parents=True)
            revision.write_bytes(b'r' * 31)
            history = authority / 'history/000001.json'
            history.parent.mkdir()
            history.write_bytes(b'h' * 17)
            (authority / 'program.json').write_bytes(b'p' * 23)
            assert s.costs()['additional_bytes'] - before == 31 + 17 + 23
            assert revision in s.retained_paths() and history in s.retained_paths()
            checks.append('New retained revision, new history and active-program growth counted exactly once')
    s.save(s.PREP / 'preflight-accounted.json', {'status': 'PASS', 'network_calls': 0,
        'actual_consumer_calls': 0, 'checks': checks, 'wall_seconds': time.monotonic() - began})
    print(json.dumps({'status': 'PASS', 'network_calls': 0, 'checks': len(checks)}))


if __name__ == '__main__':
    main()
