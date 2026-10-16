"""Run approved Writer packages locally without modifying the system installation."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/legal-mission-control/2026-10-13/master/corpus-work'


def run():
    local = BASE / 'local-renderer'
    runtime = local / 'runtime'
    packages = list((local / 'packages').glob('*.deb'))
    shutil.copytree('/etc/libreoffice', runtime / 'etc/libreoffice', dirs_exist_ok=True)
    # Overlay Writer's registration files after the installed core was copied.
    for package in packages:
        subprocess.run(['dpkg-deb', '-x', str(package), str(runtime)], check=True)
    for path in (runtime / 'usr/lib/libreoffice/share/.registry').glob('*.xcd'):
        shutil.copyfile(path, runtime / 'etc/libreoffice/registry' / path.name)
    # Ubuntu's bootstrap paths are absolute. Rebind only the local copied
    # installation and registry; the system installation stays unchanged.
    for path in (runtime / 'usr/lib/libreoffice/program').glob('*rc'):
        content = path.read_text()
        path.write_text(content.replace('file:///usr/lib/libreoffice',
            (runtime / 'usr/lib/libreoffice').as_uri()).replace('file:///etc/libreoffice',
            (runtime / 'etc/libreoffice').as_uri()))
    environment = {**os.environ, 'LD_LIBRARY_PATH': str(runtime / 'usr/lib/x86_64-linux-gnu'),
        'XDG_RUNTIME_DIR': '/tmp/legalmath-render-runtime', 'DCONF_PROFILE': '/dev/null',
        'SAL_USE_VCLPLUGIN': 'svp'}
    Path(environment['XDG_RUNTIME_DIR']).mkdir(mode=0o700, exist_ok=True)
    command = [str(runtime / 'usr/lib/libreoffice/program/soffice'),
        '-env:UserInstallation=file:///tmp/legalmath-master-local-writer', '--headless',
        '--convert-to', 'pdf', '--outdir', str(BASE),
        str(BASE / 'gatecoin-2023.docx'), str(BASE / 'gatecoin-2025.docx')]
    result = subprocess.run(command, capture_output=True, text=True, env=environment, timeout=90)
    (BASE / 'local-renderer.log').write_text(result.stdout + result.stderr)
    evidence = {'command': command, 'exit_code': result.returncode, 'output': result.stdout + result.stderr,
        'packages': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in packages},
        'system_installation': 'Unchanged; approved packages extracted within worktree',
        'pdfs': []}
    for name in ('gatecoin-2023', 'gatecoin-2025'):
        pdf = BASE / (name + '.pdf')
        if pdf.exists():
            subprocess.run(['pdftotext', '-layout', str(pdf), str(BASE / (name + '.rendered.txt'))], check=True)
            evidence['pdfs'].append({'path': str(pdf.relative_to(ROOT)),
                                    'sha256': hashlib.sha256(pdf.read_bytes()).hexdigest()})
    (BASE / 'local-renderer-result.json').write_text(json.dumps(evidence, indent=2) + '\n')
    return evidence


def later_treatment():
    """Read-only conversion of already retained additional judgment originals."""
    prior = ROOT/'artifacts/legal-mission-control/2026-10-12/remaining-work'
    directory = BASE/'later-treatment'
    directory.mkdir(exist_ok=True)
    runtime = BASE/'local-renderer/runtime'
    environment = {**os.environ, 'LD_LIBRARY_PATH':str(runtime/'usr/lib/x86_64-linux-gnu'),
        'XDG_RUNTIME_DIR':'/tmp/legalmath-render-runtime','DCONF_PROFILE':'/dev/null','SAL_USE_VCLPLUGIN':'svp'}
    originals = [prior/'hip-hing-2024-original.doc',prior/'jpex-2024-official.docx',prior/'tang-2026-official.docx']
    command = [str(runtime/'usr/lib/libreoffice/program/soffice'),
        '-env:UserInstallation=file:///tmp/legalmath-master-local-writer','--headless',
        '--convert-to','pdf','--outdir',str(directory),*[str(p) for p in originals]]
    result = subprocess.run(command,capture_output=True,text=True,env=environment,timeout=90)
    evidence = {'command':command,'exit_code':result.returncode,'output':result.stdout+result.stderr,'sources':[]}
    for original in originals:
        pdf = directory/(original.stem+'.pdf')
        if pdf.exists():
            subprocess.run(['pdftotext','-layout',str(pdf),str(pdf.with_suffix('.txt'))],check=True)
        evidence['sources'].append({'original':str(original.relative_to(ROOT)),
            'original_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),
            'pdf':str(pdf.relative_to(ROOT)) if pdf.exists() else None,
            'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest() if pdf.exists() else None})
    (directory/'render-result.json').write_text(json.dumps(evidence,indent=2)+'\n')
    return evidence


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',nargs='?',choices=['gatecoin','later-treatment'],default='gatecoin')
    print(json.dumps(later_treatment() if parser.parse_args().action=='later-treatment' else run(),indent=2))
