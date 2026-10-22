"""Finite installed-profile acceptance from complete retained local evidence."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import zipfile

from . import native_binding_acceptance as common, native_profile as product
from .execution_authority import read, file_hash
from .successor import process_ledger, sealed_runtime
from .successor.contracts import digest

VERSION = 'native-installed-profile.v1'
BASE = 'docs/implementation/prospectus-execution-authority/attempts'
MODES = ('fresh', 'retained')
COMMANDS = ('build', 'install', 'capture', 'check',
            *[s+'-'+m for m in MODES for s in ('source','construct','finish','verify')], 'controls')
STAGES = {'prepare', 'inventory', *COMMANDS, 'compare-fresh', 'compare-retained'}
ERRORS = {
    'wrong-profile-pin': 'Pinned profile identity differs',
    'blob-changed': 'Snapshot blob hash/size mismatch',
    'blob-missing': 'FileNotFoundError:',
    'manifest-changed': 'Snapshot manifest identity differs',
    'method-changed': 'Installed product methods changed',
    'runtime-changed': 'Trusted runtime changed',
    'wrong-request-source': 'Source bytes changed',
    'duplicate-source-stage': 'FileExistsError:',
    'failed-predecessor': 'Predecessor stage did not pass: source',
    'rehashed-forged-answer': 'Delivered answer differs from actual consumer',
    'missing-native-stream': 'FileNotFoundError:',
}
require = common.require


def installed_proof(proof, environment, methods):
    environment = Path(environment)
    package = environment / 'lib/python3.11/site-packages/legalmath'
    require(proof.get('module_path') == str(package/'prospectus/native_profile.py')
            and proof.get('python') == str(environment/'bin/python'),
            'Installed module/interpreter location differs')
    require(proof.get('methods') == methods, 'Installed method identities differ')
    if 'sys_path' in proof:
        require(str(package.parent) in proof['sys_path']
                and all(not str(p).endswith('/src') for p in proof['sys_path']),
                'Installed import path includes an editable source checkout')
    return package


def control_evidence(value, environment, methods):
    installed_proof(value, environment, methods)
    rows = value.get('cases', [])
    require(value.get('status') == 'PASS' and value.get('native_starts') == 0,
            'Installed controls failed or launched native work')
    require(len(rows) == len(ERRORS) and {r.get('case') for r in rows} == set(ERRORS),
            'Installed control denominator differs')
    for row in rows:
        require(row.get('refused') is True and ERRORS[row['case']] in row.get('error',''),
                'Installed control did not refuse for the expected reason')
    return len(rows)


def wheel_evidence(folder, methods):
    wheel = read(folder/'built-wheel.json')
    path = common.contained(folder, wheel['file'])
    require(file_hash(path) == wheel['sha256'], 'Installed wheel identity changed')
    with zipfile.ZipFile(path) as archive:
        for name, expected in methods.items():
            require(hashlib.sha256(archive.read('legalmath/'+name)).hexdigest() == expected,
                    'Installed wheel method differs: '+name)
    return wheel['sha256']


def campaign(folder):
    prior = folder.parent/'attempt-001'
    common.verify_files(prior, read(prior/'outputs.json'))
    require(read(prior/'result.json')['status']=='FAIL'
            and read(prior/'invocations/capture/result.json')['status']=='FAIL'
            and 'Invalid or reserved snapshot destination' in (prior/'commands/capture/stderr').read_text(),
            'Original reserved-path refusal was not retained')
    old_outer = process_ledger.checked(prior/'command-ledger.json')
    old_native = process_ledger.checked(prior/'native-ledger.json')
    outer = process_ledger.checked(folder/'command-ledger.json')
    native = process_ledger.checked(folder/'native-ledger.json')
    require(old_outer['limit']==18 and len(old_outer['reservations'])==5
            and old_native['limit']==6 and not old_native['reservations']
            and outer['limit']==13 and outer['historical_lower_bound']==5
            and len(outer['reservations'])==13 and native['limit']==6
            and native['historical_lower_bound']==50 and len(native['reservations'])==4,
            'Cumulative installed campaign allowances or starts differ')
    require(all(r['state']=='STARTED' for r in old_outer['reservations']+outer['reservations']+native['reservations']),
            'Unresolved installed process reservation')
    require({p.name for p in (folder/'commands').iterdir()} == set(COMMANDS),
            'Installed command denominator differs')
    for name, row in zip(COMMANDS, outer['reservations']):
        command = read(folder/'commands'/name/'command.json')
        require(command['argv']==row['argv'] and command['timeout']==120
                and read(folder/'commands'/name/'result.json')['returncode']==0,
                'Actual installed command differs or failed: '+name)
        require(command['environment']=={'CUDA_VISIBLE_DEVICES':'-1','PYTHONPATH':'','PYTHONNOUSERSITE':'1'},
                'Installed CPU environment differs')
    return native


def stages(folder, methods):
    require({p.name for p in (folder/'invocations').iterdir()}==STAGES, 'Installed stage denominator differs')
    for name in STAGES:
        start=read(folder/'invocations'/name/'started.json')
        result=read(folder/'invocations'/name/'result.json')
        require(start['methods']==methods and start['cpu_gpu']=='CPU only; GPUs intentionally hidden'
                and start['command']==['.venv/bin/python','-m','scripts.prospectus_native_install',name]
                and result['status']=='PASS' and 0 <= result['wall_seconds'] <= 120,
                'Installed stage is stale, failed or over bound: '+name)
    product.checked_stage(folder/'profile','capture')
    product.checked_stage(folder/'profile-check','check')
    for mode in MODES:
        for name in ('source','construct','finish','verify'):
            product.checked_stage(folder/mode,name)


def installed_requirements(required, manifest, environment):
    """Translate only the two byte-identical installed worker module paths."""
    expected=dict(required)
    files={r['path']:r['sha256'] for r in manifest['files']}
    installed=environment/'lib/python3.11/site-packages/legalmath/prospectus/successor'
    for name in ('ocr_worker.py','native_inputs.py'):
        source=str(Path(product.extraction.__file__).with_name(name).resolve())
        target=str(installed/name)
        require(source in expected and target not in expected,
                'Required worker source mapping is missing or ambiguous')
        hashed=expected.pop(source)
        require(files.get(target)==hashed, 'Installed worker declaration bytes differ')
        expected[target]=hashed
    return expected


def native_source(root, folder, mode, manifest, profile, values, answer, environment, baseline_worker):
    job=folder/mode
    execution=read(job/'execution.json')
    installed_proof(execution, environment, product.methods())
    request=read(folder/(mode+'-request.json'))
    require(values['P1']['payload']['request']==request and execution['request_sha256']==digest(request),
            'Installed source request differs')
    require(execution['profile']==str(folder/'profile')
            and execution['profile_sha256']==digest(profile) and execution['native_reuse_allowed'] is False,
            'Installed source profile selection differs')
    expected_required=installed_requirements(product.preflight(request,profile,manifest),manifest,environment)
    require(execution['required_files']==expected_required,
            'Required source declarations differ')
    doc=answer['source_map']['documents'][0]
    first, text_streams=common.receipt(job/'native/0',manifest)
    second, ocr_streams=common.receipt(job/'native/1',manifest)
    expected_text=['/usr/bin/pdftotext','-bbox-layout','-enc','UTF-8',str(root/doc['path']),'-']
    worker=str(environment/'lib/python3.11/site-packages/legalmath/prospectus/successor/ocr_worker.py')
    require(first['argv']==expected_text and text_streams[0]==b''
            and second['argv']==[profile['ocr_python'],worker], 'Wrong installed native command')
    require(first['limits']['max_stream_bytes']==64*1024*1024
            and second['limits']['max_stream_bytes']==20*1024*1024, 'Native capacities differ')
    require(execution['native_receipts']==[first,second], 'Installed receipt inventory differs')
    target=doc['runtime'] if mode=='fresh' else doc['image_verification']['verification_runtime']
    require(doc['native_extraction']['sealed_execution']==first and target['sealed_execution']==second
            and first['stdout']['sha256']==doc['native_extraction']['raw_xml_sha256'],
            'Installed receipts were not delivered in source graph')
    spec=json.loads(ocr_streams[0]); result=json.loads(ocr_streams[1]); hp=doc['hybrid_profile']
    require(spec['source']==expected_text[4] and spec['source_sha256']==doc['sha256']
            and spec['selected_pages']==hp['pages'] and spec['page_count']==hp['page_count']
            and spec['dpi']==hp['dpi'] and spec['language']==hp['language'], 'Installed OCR request differs')
    require(result['source_sha256']==doc['sha256'] and result['page_count']==hp['page_count'],
            'Installed worker source identity differs')
    if mode=='fresh':
        require(not spec.get('verify_images_only') and result['pages']==baseline_worker['pages'],
                'Complete installed OCR words/text/images differ')
    else:
        keys=('page','image_sha256','image_width','image_height','width_points','height_points')
        require(spec.get('verify_images_only') is True and result.get('verification_only') is True
                and result['pages']==[{k:p[k] for k in keys} for p in baseline_worker['pages']],
                'Complete installed verified images differ')
    verification=read(job/'verification.json')
    require(verification=={'version':product.VERSION,'profile_sha256':digest(profile),
        'answer_sha256':answer['report_sha256'],'consumed_products':answer['consumed_products'],
        'native_calls':2,'native_reuse_allowed':False,'independent_legal_acceptance':False},
        'Installed verification differs from actual consumer')
    return [first,second]


def evidence(root, folder):
    root=Path(root).resolve(); folder=Path(folder).resolve()
    common.verify_files(folder,read(folder/'outputs.json'))
    frozen=read(folder/'frozen-methods.json')
    required={str(p.relative_to(root)) for p in (root/'src/legalmath/prospectus/successor').glob('*.py')}
    required|={'src/legalmath/prospectus/native_profile.py','scripts/prospectus_native_install.py',
               'scripts/prospectus_native_installed_controls.py','tests/prospectus/test_native_profile.py'}
    require(required<=frozen.keys(),'Installed frozen method inventory incomplete')
    common.verify_files(root,frozen); common.verify_files(folder/'method',frozen)
    methods=read(folder/'installed-methods.json')
    require(methods==product.methods(),'Installed source methods changed')
    workspace=Path(read(folder/'workspace.json')['directory'])
    require(workspace.is_relative_to(root/'.localresources/prospectus') and not str(workspace).startswith('/tmp/'),
            'Unsupported installation destination')
    environment=workspace/'environment'
    package=environment/'lib/python3.11/site-packages/legalmath'
    common.verify_files(package,methods)
    relocation=read(folder/'relocated-installation.json')
    require(relocation['to']==str(environment), 'Relocated environment identity differs')
    common.verify_files(environment,relocation['dependency_metadata'])
    common.verify_files(root,read(folder/'wheel-inputs.json'))
    require(len(read(folder/'wheel-inputs.json'))==28, 'Pinned dependency wheel inventory differs')
    wheel=wheel_evidence(folder,methods)
    for name in COMMANDS[2:-1]:
        installed_proof(read(folder/'commands'/name/'installed-proof.json'),environment,methods)
    stages(folder,frozen)
    ledger=campaign(folder)
    pin=read(folder/'profile/capture-result.json')['profile_sha256']
    profile,manifest=product.load_profile(folder/'profile',pin)
    require(manifest==read(folder/'expected-snapshot.json') and len(manifest['files'])==343,
            'Installed explicit manifest differs')
    require(len(manifest['files'])<=2048 and sum(r['size'] for r in manifest['files'])<=512*1024*1024,
            'Installed snapshot exceeds its reviewed bounds')
    seen=set(); physical=0
    for directory in (folder.parent/'attempt-001',folder):
        for path in directory.rglob('*'):
            if path.is_file():
                stat=path.stat(); key=(stat.st_dev,stat.st_ino)
                if key not in seen:
                    physical+=stat.st_blocks*512; seen.add(key)
    require(physical<=450*1024*1024, 'Cumulative installed evidence exceeds its reviewed bound')
    prior=root/BASE/'native-binding/attempt-004'
    common.verify_files(prior,read(prior/'outputs.json'))
    baseline=common.products(prior)
    common.consumer(root,*baseline)
    baseline_worker=read(prior/'worker.json')
    controls=control_evidence(read(folder/'installed-controls/result.json'),environment,methods)
    from .execution_acceptance import checked_tests
    focused=checked_tests(folder/'tests.xml',21)
    cases=[]; receipts=[]
    for mode in MODES:
        expected=deepcopy(read(prior/'request.json'))
        if mode=='fresh': expected['bundle']['documents'][0].pop('hybrid_ocr')
        require(read(folder/(mode+'-request.json'))==expected,'Original installed request changed')
        values,answer=common.products(folder/mode)
        common.compare_products(baseline,(values,answer))
        common.consumer(root,values,answer)
        require(len(answer['source_map']['units'])==36176,'Complete source unit denominator differs')
        rows=native_source(root,folder,mode,manifest,profile,values,answer,environment,baseline_worker)
        receipts.extend(rows)
        cases.append({'mode':mode,'units':36176,'answer_sha256':answer['report_sha256'],
                      'receipts':[r['receipt_sha256'] for r in rows]})
    for reservation, receipt in zip(ledger['reservations'],receipts):
        argv=reservation['argv']
        require('--' in argv and argv[argv.index('--')+1:]==receipt['argv'],
                'Native ledger command differs from delivered receipt')
    return {'version':VERSION,'evidence_attempt':str(folder.relative_to(root)),
        'installed_methods':methods,'wheel_sha256':wheel,'profile_sha256':pin,
        'matrix':cases,'installed_adverse_controls':controls,'focused_tests':focused,
        'cumulative_outer_starts':18,'native_starts':4,'historical_native_lower_bound':54,
        'scope':'Installed optional Linux CPU explicit-file profile on this host',
        'independent_legal_acceptance':False,'portability_established':False,'whole_program_complete':False}
