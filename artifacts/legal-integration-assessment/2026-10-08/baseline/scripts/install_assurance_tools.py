"""Fixed local tool installation: no sudo, main-env mutation or model API."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / '.localresources/assurance-tools'
PY = BASE / 'venv/bin/python'
REQUIREMENTS = ROOT / 'docs/implementation/interpretation-round11/tool-requirements.in'


def install_environment():
    env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1','PIP_DISABLE_PIP_VERSION_CHECK':'1','PYTHONNOUSERSITE':'1'}
    env.pop('PYTHONPATH',None)
    return env


def run(argv, cwd=ROOT, timeout=1200):
    print(json.dumps({'install_argv': list(map(str, argv)), 'cwd': str(cwd)}), flush=True)
    subprocess.run(list(map(str, argv)), cwd=cwd, check=True, timeout=timeout,
                   env=install_environment())


def main():
    if len(sys.argv) != 1:
        raise SystemExit('No installation arguments accepted')
    BASE.mkdir(parents=True, exist_ok=True)
    if not PY.exists():
        run([sys.executable, '-m', 'venv', BASE/'venv'])
    lock = BASE/'requirements.lock'
    if lock.exists() and any(line.startswith('legalmath==') for line in lock.read_text().splitlines()):
        raise ValueError('Lock includes inherited project metadata; retain failed lock and regenerate in isolated environment')
    if lock.exists():
        run([PY, '-m', 'pip', 'install', '--requirement', lock,
             '--extra-index-url', 'https://download.pytorch.org/whl/cpu'])
    else:
        run([PY, '-m', 'pip', 'install', 'torch==2.8.0+cpu', 'torchvision==0.23.0+cpu',
             '--index-url', 'https://download.pytorch.org/whl/cpu'])
        run([PY, '-m', 'pip', 'install', '--requirement', REQUIREMENTS])
        lock.write_bytes(subprocess.check_output([str(PY), '-m', 'pip', 'freeze'],env=install_environment(),cwd=BASE))
    run([PY, '-m', 'pip', 'check'])
    debs = BASE/'debs'; debs.mkdir(exist_ok=True)
    run(['apt-get', 'download', 'tesseract-ocr', 'tesseract-ocr-eng',
         'tesseract-ocr-osd', 'libtesseract4', 'liblept5'], cwd=debs, timeout=300)
    for path in sorted(debs.glob('*.deb')):
        run(['dpkg-deb', '--extract', path, BASE/'ocr'])
    jars = BASE/'jars'; jars.mkdir(exist_ok=True)
    versions = {'pitest': '1.20.3', 'junit': '4.13.2', 'hamcrest-core': '1.3',
                'commons-text':'1.13.1','commons-lang3':'3.17.0'}
    for group, artifact, version in [
        ('org/pitest', 'pitest', versions['pitest']),
        ('org/pitest', 'pitest-entry', versions['pitest']),
        ('org/pitest', 'pitest-command-line', versions['pitest']),
        ('junit', 'junit', versions['junit']),
        ('org/hamcrest', 'hamcrest-core', versions['hamcrest-core']),
        ('org/apache/commons','commons-text',versions['commons-text']),
        ('org/apache/commons','commons-lang3',versions['commons-lang3']),
    ]:
        name = f'{artifact}-{version}.jar'; dest = jars/name
        if not dest.exists():
            url = f'https://repo.maven.apache.org/maven2/{group}/{artifact}/{version}/{name}'
            print('Download '+url, flush=True)
            with urllib.request.urlopen(url, timeout=60) as response:
                raw = response.read(30 * 1024 * 1024 + 1)
            if len(raw) > 30 * 1024 * 1024 or not raw.startswith(b'PK'):
                raise ValueError('Invalid or oversized Maven artifact')
            dest.write_bytes(raw)
    manifest = {'schema': 'legalmath.assurance-tool-lock.v1', 'python': str(PY),
                'cpu_only': True, 'requirements_sha256': hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest(),
                'packages': lock.read_text().splitlines(), 'jars': versions,
                'files': {str(p.relative_to(BASE)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for folder in (debs, jars) for p in sorted(folder.iterdir()) if p.is_file()},
                'limits': ['Versions identify the installation; they do not measure accuracy.']}
    (BASE/'tool-lock.json').write_text(json.dumps(manifest, indent=2)+'\n')


if __name__ == '__main__':
    main()
