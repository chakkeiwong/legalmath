"""Render one declared original annual page with a retained bounded receipt."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prospectus_annual_policy_source import WORK
from scripts.prospectus_annual_basis_source import PDF, save, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('page', type=int, choices=[104, 105, 107, 187])
    page = parser.parse_args().page
    assert sha(PDF) == 'f6c1196ffcbaed34dc4068b4fbc095b4494e421e224977bfa54b215134e32f25'
    binary = shutil.which('pdftoppm')
    assert binary
    prefix = WORK / ('page-' + str(page))
    assert not prefix.with_suffix('.png').exists()
    cmd = [binary, '-f', str(page), '-l', str(page), '-scale-to', '2000', '-singlefile', '-png', str(PDF), str(prefix)]
    started = time.monotonic()
    with (WORK / ('render-' + str(page) + '.log')).open('x') as log:
        try:
            result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=10,
                                    env={**os.environ, 'CUDA_VISIBLE_DEVICES': '-1'})
            code = result.returncode
        except subprocess.TimeoutExpired:
            code = -1
    save(WORK / ('render-' + str(page) + '.json'), {'argv': cmd, 'exit_code': code,
        'seconds': time.monotonic() - started, 'source_sha256': sha(PDF), 'renderer_sha256': sha(Path(binary)),
        'image_sha256': sha(prefix.with_suffix('.png')) if prefix.with_suffix('.png').exists() else None,
        'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1'})
    assert code == 0, 'Retain render failure; no unchanged retry'
    print(json.dumps({'status': 'PASS', 'page': page}))


if __name__ == '__main__':
    main()
