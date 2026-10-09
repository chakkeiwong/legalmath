"""Fixed offline restoration and installed source-to-report exercise."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from email.parser import BytesParser

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT / '.localresources/prospectus/closure-runtime'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')


def check_evidence_budget(folder, limit=200_000_000, metadata_reserve=1_048_576):
    size = sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())
    if size + metadata_reserve > limit:
        raise ValueError(f'Evidence budget exceeded: {size} bytes plus {metadata_reserve} reserved; limit {limit}')
    return size


def wheel_lock(directory):
    rows = []
    for path in sorted(directory.glob('*.whl')):
        with zipfile.ZipFile(path) as archive:
            name = next(n for n in archive.namelist() if n.endswith('.dist-info/METADATA'))
            data = BytesParser().parsebytes(archive.read(name))
        rows.append(f"{data['Name']}=={data['Version']} --hash=sha256:{sha(path)}")
    if not rows:
        raise ValueError('Download pinned wheels before offline restoration')
    return '\n'.join(rows) + '\n'


def successful_attempt(directory, required):
    """Use the latest successful evidence; corruption must not cause fallback."""
    completed = [p for p in sorted(directory.glob('attempt-*'))
                 if (p/'result.json').is_file() and
                 json.loads((p/'result.json').read_text()).get('status') == 'PASS']
    if not completed:
        raise ValueError('Run the reviewed consumer before installed verification: '+str(directory))
    folder = completed[-1]
    manifest = json.loads((folder/'manifest.json').read_text())['files']
    actual = {str(p.relative_to(folder)) for p in folder.rglob('*')
              if p.is_file() and p != folder/'manifest.json'}
    if not set(required).issubset(manifest) or actual != set(manifest):
        raise ValueError('Consumer evidence manifest is incomplete: '+str(folder))
    for relative, expected in manifest.items():
        path = (folder/relative).resolve()
        if not path.is_relative_to(folder.resolve()) or sha(path) != expected:
            raise ValueError('Consumer evidence changed: '+str(folder))
    return folder


def application(folder, run, *, basf_notices=False, basf_agents=False):
    wheelhouse = RESOURCES / 'wheels'
    locks = folder / 'dependencies.lock'
    locks.write_text(wheel_lock(wheelhouse))
    with tempfile.TemporaryDirectory(prefix='prospectus-closure-installed-') as temporary:
        base = Path(temporary)
        staging = base / 'source'
        staging.mkdir()
        shutil.copy2(ROOT/'pyproject.toml', staging/'pyproject.toml')
        shutil.copytree(ROOT/'src', staging/'src', ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.egg-info'))
        builder = base/'builder'
        run('create-build-environment', [sys.executable, '-m', 'venv', str(builder)], base)
        build_python = str(builder/'bin/python')
        run('install-build-dependencies', [build_python, '-m', 'pip', 'install', '--no-index', '--find-links', str(wheelhouse),
            '--require-hashes', '-r', str(locks)], base)
        wheels = folder/'wheel'
        wheels.mkdir()
        run('build-wheel', [build_python, '-m', 'pip', 'wheel', '--no-deps', '--no-build-isolation', '--wheel-dir', str(wheels), str(staging)], base)
        complete_lock = folder/'application.lock'
        complete_lock.write_text(locks.read_text() + wheel_lock(wheels))
        fixture = base/'fixtures.py'
        shutil.copy2(ROOT/'scripts/prospectus_closure_fixtures.py', fixture)
        check = base/'installed_check.py'
        shutil.copy2(ROOT/'scripts/prospectus_closure_installed_check.py', check)
        shutil.copy2(ROOT/'scripts/prospectus_closure_basf.py', base/'basf_consumer.py')
        if basf_notices:
            shutil.copy2(ROOT/'scripts/prospectus_closure_basf_notices.py', base/'basf_notices_consumer.py')
        if basf_agents:
            shutil.copy2(ROOT/'scripts/prospectus_closure_basf_agent_notices.py', base/'basf_agents_consumer.py')
        run('create-runtime', [sys.executable, '-m', 'venv', str(base/'runtime')], base)
        runtime = str(base/'runtime/bin/python')
        install = [runtime, '-m', 'pip', 'install', '--no-index', '--find-links', str(wheelhouse), '--find-links', str(wheels),
                   '--require-hashes', '-r', str(complete_lock)]
        run('install-locked-runtime', install, base)
        run('dependency-consistency', [runtime, '-m', 'pip', 'check'], base)
        evidence = ROOT/'docs/implementation/prospectus-integration-closure'
        compass_attempt = successful_attempt(evidence/'packages/compass',
                                            {'request.json','report.json','comparisons.json','result.json'})
        compass = json.loads((compass_attempt/'request.json').read_text())
        case = base/'cases/compass'
        case.mkdir(parents=True)
        save(case/'request.json',compass)
        for document in compass['bundle']['documents']:
            destination = case/document['path']
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/document['path'],destination)
        save(folder/'compass-inputs.json', {'request':str((compass_attempt/'request.json').relative_to(ROOT)),
             'request_sha256':sha(compass_attempt/'request.json'), 'manifest_sha256':sha(compass_attempt/'manifest.json'),
             'files':{d['path']:sha(ROOT/d['path']) for d in compass['bundle']['documents']}})
        request_name = 'request.json.gz' if basf_notices else 'request.json'
        basf_profile = 'basf-agent-notices' if basf_agents else ('basf-notices' if basf_notices else 'basf-consumer')
        basf_attempt = successful_attempt(evidence/basf_profile,
                                          {request_name,'consumer.json','result.json'})
        request_path = basf_attempt/request_name
        basf=json.loads(gzip.decompress(request_path.read_bytes()) if basf_notices else request_path.read_bytes())
        if basf_notices:
            canonical = json.dumps(basf, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
            if hashlib.sha256(canonical).hexdigest() != json.loads((basf_attempt/'result.json').read_text())['request_sha256']:
                raise ValueError('Decompressed notice request differs from consumer input')
        case=base/'cases/basf'
        case.mkdir(parents=True)
        save(case/'request.json',basf)
        if basf_notices:
            packet_path = evidence/basf_profile/'review.json'
            packet = json.loads(packet_path.read_text())
            # The consumer binds the canonical packet; do not silently install
            # a newer review next to an older successful request.
            canonical = json.dumps(packet, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
            expected = json.loads((basf_attempt/'meaning-evidence.json').read_text())['packet_sha256']
            if hashlib.sha256(canonical).hexdigest() != expected:
                raise ValueError('Notice review changed since successful consumer')
            shutil.copy2(packet_path, case/('agent-review.json' if basf_agents else 'notice-review.json'))
            if basf_agents:
                notice_path = evidence/'basf-notices/review.json'
                notice_packet = json.loads(notice_path.read_text())
                notice_bytes = json.dumps(notice_packet['clauses'], sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
                if hashlib.sha256(notice_bytes).hexdigest() != packet['notice_clauses_sha256']:
                    raise ValueError('Prior notice review changed since agent consumer')
                shutil.copy2(notice_path, case/'notice-review.json')
        inputs={basf['construction']['admission_path']}
        for document in basf['bundle']['documents']:
            inputs.add(document['path'])
            inputs.add(document['acquisition']['path'])
        for relative in inputs:
            destination=case/relative
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/relative,destination)
        save(folder/'basf-inputs.json', {'request':str(request_path.relative_to(ROOT)),
             'request_sha256':sha(request_path), 'manifest_sha256':sha(basf_attempt/'manifest.json'),
             'files':{p:sha(ROOT/p) for p in sorted(inputs)}})
        run('fresh-installed-assess', [runtime, '-I', str(check), str(fixture), str(base/'cases'), str(base/'results.json')], base)
        result = json.loads((base/'results.json').read_text())
        shutil.copytree(base/'cases', folder/'cases')
        save(folder/'installed-results.json', result)
        moved = base/'relocated'
        shutil.move(str(base/'cases'), moved)
        run('relocated-assess', [runtime, '-I', str(check), str(fixture), str(moved), str(base/'relocated-results.json'), '--existing'], base)
        relocated = json.loads((base/'relocated-results.json').read_text())
        if result['questions'] != relocated['questions']:
            raise ValueError('Relocation changed the installed answers')
        save(folder/'relocated-results.json', relocated)
        # Delete only this action's newly created temporary venv. The wheelhouse
        # and previous evidence remain intact; restoring repeats locked resolution.
        shutil.rmtree(base/'runtime')
        if (base/'runtime/bin/python').exists():
            raise ValueError('Restoration fixture did not remove its runtime')
        run('restore-missing-runtime', [sys.executable, '-m', 'venv', str(base/'runtime')], base)
        run('restore-locked-dependencies', install, base)
        run('restored-assess', [runtime, '-I', str(check), str(fixture), str(moved), str(base/'restored-results.json'), '--existing'], base)
        restored = json.loads((base/'restored-results.json').read_text())
        if result['questions'] != restored['questions']:
            raise ValueError('Restoration changed installed answers')
        save(folder/'restored-results.json', restored)
        return {'status': 'PASS', 'fresh_assess': True, 'relocation': True, 'missing_runtime_restored': True,
                'lock_sha256': sha(complete_lock), 'question_payloads_equal': True,
                'scope': 'Core service on nine development cases, including real BASF reviewed scalar occurrences/references and conditional Compass coupon; BASF CLI builds P1-P5 and preserves partial meaning. Optional package/OS restoration remains separate',
                'basf_notice_meanings': 'Four complete qualified readings checked through P3 in all stages' if basf_notices else 'NOT_REQUESTED',
                'basf_agent_meanings': 'Four qualified agent readings, B54 unresolved, checked in all stages' if basf_agents else 'NOT_REQUESTED'}


def optional(folder, run):
    lock = folder/'optional.lock'
    wheels = RESOURCES/'optional-wheels'
    lock.write_text(wheel_lock(wheels))
    with tempfile.TemporaryDirectory(prefix='prospectus-optional-restore-') as temporary:
        base=Path(temporary)
        run('create-optional-runtime',[sys.executable,'-m','venv',str(base/'runtime')],base)
        python=str(base/'runtime/bin/python')
        run('restore-optional-locked',[python,'-m','pip','install','--no-index','--find-links',str(wheels),
            '--require-hashes','-r',str(lock)],base)
        run('optional-dependency-consistency',[python,'-m','pip','check'],base)
        probe=base/'probe.py'
        probe.write_text('''import json,sys,io
from pathlib import Path
import cassis,QuantLib as ql,fitz
raw,types,scan,models=sys.argv[1:]
ts=cassis.load_typesystem(io.BytesIO(Path(types).read_bytes()))
cas=cassis.load_cas_from_xmi(io.BytesIO(Path(raw).read_bytes()),typesystem=ts)
relations=list(cas.select('webanno.custom.DraftRelation'))
assert len(relations)==1 and relations[0].kind=='exceptions'
assert ql.ActualActual(ql.ActualActual.ISMA).yearFraction(ql.Date(1,1,2024),ql.Date(1,1,2025),ql.Date(1,1,2024),ql.Date(1,1,2025))==1.0
doc=fitz.open(scan)
pix=doc[0].get_pixmap(dpi=300)
ocr=fitz.open(stream=pix.pdfocr_tobytes(language='eng',tessdata=models),filetype='pdf')
assert 'unsecured obligations' in ocr[0].get_text()
print(json.dumps({'cassis_exception_relation':True,'QuantLib':ql.__version__,'PyMuPDF':fitz.VersionBind,'ocr_phrase':True,'prefix':sys.prefix}))
''')
        package=ROOT/'docs/implementation/prospectus-integration-closure/packages'
        codec=package/'codec/attempt-003'
        scan=package/'scan/attempt-002/new-scan.pdf'
        models=ROOT/'docs/prospectus/closure-2026-10-05/tools'
        run('restored-optional-consumers',[python,'-I',str(probe),str(codec/'authored.xmi'),str(codec/'TypeSystem.xml'),str(scan),str(models)],base)
        save(folder/'input-bindings.json',{str(p.relative_to(ROOT)):sha(p) for p in [codec/'authored.xmi',codec/'TypeSystem.xml',scan,models/'eng.traineddata']})
        return {'status':'PASS','lock_sha256':sha(lock),
            'scope':'Separate Cassis/QuantLib/PyMuPDF profile restored; Docling/server/browser profiles pending',
            'optional_dependency_resolution':'Separate profile: Cassis attrs<26 is not installed into core attrs26 environment'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['application','optional'])
    parser.add_argument('--basf-notices', action='store_true', help='Use the completed BASF notice consumer in the application exercise')
    parser.add_argument('--basf-agents', action='store_true', help='Use the combined BASF agent and notice consumer')
    args = parser.parse_args()
    if args.basf_agents:
        args.basf_notices = True
    if args.basf_notices and args.action != 'application':
        parser.error('--basf-notices requires application')
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    base = ROOT/'docs/implementation/prospectus-integration-closure/installed'
    folder = base / f'attempt-{len(list(base.glob("attempt-*")))+1:03d}'
    folder.mkdir(parents=True)
    started = time.monotonic()
    source_paths = [ROOT/'pyproject.toml', *sorted((ROOT/'src/legalmath').rglob('*.py')),
                    Path(__file__), ROOT/'scripts/prospectus_closure_installed_check.py', ROOT/'scripts/prospectus_closure_fixtures.py',
                    ROOT/'scripts/prospectus_closure_basf.py', ROOT/'scripts/prospectus_closure_basf_notices.py',
                    ROOT/'scripts/prospectus_closure_basf_agent_notices.py']
    initial_method = {str(p.relative_to(ROOT)):sha(p) for p in source_paths}
    save(folder/'started.json', {'action':args.action, 'basf_notices':args.basf_notices, 'basf_agents':args.basf_agents, 'method':initial_method, 'timeout_seconds':1200,
         'evidence_limit_bytes':200_000_000, 'metadata_reserve_bytes':1_048_576})
    env = {k:v for k,v in os.environ.items() if k not in {'PYTHONPATH', 'PYTHONHOME'}}
    env.update(CUDA_VISIBLE_DEVICES='-1', PYTHONNOUSERSITE='1', PIP_NO_INDEX='1', PIP_DISABLE_PIP_VERSION_CHECK='1')
    commands = []
    def run(name, argv, cwd):
        tick = time.monotonic()
        result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=600)
        (folder/(name+'.log')).write_bytes(result.stdout + result.stderr)
        commands.append({'name':name, 'argv':argv, 'cwd':str(cwd), 'returncode':result.returncode, 'wall_seconds':time.monotonic()-tick})
        if result.returncode:
            raise ValueError(name + ' failed; see preserved log')
        check_evidence_budget(folder)
        if time.monotonic() - started > 1200:
            raise TimeoutError('Restoration exceeded 20-minute budget')
    try:
        result = application(folder, run, basf_notices=args.basf_notices, basf_agents=args.basf_agents) if args.action == 'application' else optional(folder, run)
        if initial_method != {str(p.relative_to(ROOT)):sha(p) for p in source_paths}:
            raise ValueError('Installation method changed during execution')
        result['evidence_payload_bytes'] = check_evidence_budget(folder)
        result['evidence_limit_bytes'] = 200_000_000
        result['evidence_budget'] = 'PASS_WITH_ONE_MIB_METADATA_RESERVE'
    except Exception as exc:
        result = {'status':'FAIL', 'error':type(exc).__name__+': '+str(exc)}
    result.update(action=args.action, basf_notices=args.basf_notices, basf_agents=args.basf_agents, commands=commands, wall_seconds=time.monotonic()-started,
        plan=('docs/plans/prospectus-basf-agent-notices-2026-10-10.md' if args.basf_agents else
              'docs/plans/prospectus-basf-notices-2026-10-09.md' if args.basf_notices else 'docs/plans/prospectus-closure-runtime-2026-10-09.md'),
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        python=sys.version, cpu_gpu='CPU; CUDA_VISIBLE_DEVICES=-1', seeds='Deterministic',
        wheels={str(p.relative_to(RESOURCES)):sha(p) for p in RESOURCES.glob('*wheels/*.whl')},
        method=initial_method)
    save(folder/'result.json', result)
    save(folder/'manifest.json', {'files':{str(p.relative_to(folder)):sha(p) for p in folder.rglob('*') if p.is_file()}})
    print(json.dumps({'directory':str(folder.relative_to(ROOT)), 'status':result['status'], 'error':result.get('error')}))
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
