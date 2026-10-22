"""Bounded normal-consumer integration of the retained comparative reading."""
import argparse
from copy import deepcopy
import gzip
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
sys.dont_write_bytecode = True
from legalmath.prospectus.execution_authority import Authority, REL, read, write, file_hash, digest as authority_digest
from legalmath.prospectus.execution_acceptance import checked_tests
from legalmath.prospectus import bes_comparative_basis as basis
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest
from scripts.prospectus_comparative_oracle import verify, require

SOURCE = REL+'/attempts/source-bes-dep-06'
NORMAL, PRIOR = SOURCE+'/attempt-003', SOURCE+'/attempt-008'
REVIEW = REL+'/reviews/comparative-production-213-r2'
PREPARATION_PRIOR = REL+'/reviews/comparative-production-213/preparation.json'
RECORD = REL+'/continuation-reviews/comparative-production-213-record'
PLAN = 'docs/plans/prospectus-comparative-production-2026-10-17.md'
FIXTURE = 'tests/prospectus_successor/fixtures/bes_comparative_basis.json.gz'
TESTS = ('tests/prospectus/test_bes_comparative_basis.py', 'tests/prospectus/test_build_contract.py',
         'tests/prospectus_successor/test_report_scope.py')
METHODS = ('pyproject.toml', 'scripts/prospectus_comparative_production.py', 'scripts/prospectus_comparative_oracle.py',
    'src/legalmath/prospectus/bes_comparative_basis.py', 'src/legalmath/prospectus/bes_comparative_spec.json',
    'src/legalmath/prospectus/successor/service.py', 'src/legalmath/prospectus/build_contract.py', *TESTS, FIXTURE)
ADDED = ('comparative_accounting_review', 'comparative_accounting_explanation')
SELECTOR = {'version': 'comparative-production.v1', 'preparation_seconds': 90, 'candidate_seconds': 180,
    'validation_seconds': 180, 'cumulative_seconds': 1530, 'new_bytes': 40*1024**2,
    'cumulative_bytes': 220*1024**2, 'reserve_bytes': 262144, 'extraction_OCR_network_render_GPU_install': 0}


def load(path):
    with gzip.open(path, 'rt') as stream: return json.load(stream)


def compressed(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(gzip.compress(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode(), mtime=0))


def products(root):
    ref = load(root/NORMAL/'candidate-P1-reference.json.gz')
    require(file_hash(root/ref['original_P1']) == ref['file_sha256'], 'Original P1 file changed')
    raw = load(root/ref['original_P1'])
    request = ref['request']
    p1 = service.seal('P1', request['bundle'], {'request': digest(request)},
                      {'request': request, 'graph': raw['payload']['graph']})
    require(p1['sha256'] == ref['expected_sha256'], 'Selected original003 P1 differs')
    ps = {'P1': p1, **load(root/NORMAL/'candidate-P2-P5.json.gz')}
    service.verify(p1, 'P1', request['bundle'], {'request': digest(request)})
    for stage, parents in [('P2', ['P1']), ('P3', ['P1', 'P2']), ('P4', ['P1', 'P3']), ('P5', ['P2', 'P3'])]:
        service.verify(ps[stage], stage, request['bundle'], {k: ps[k]['sha256'] for k in parents})
    return ps


def consume(root, ps, profile=None):
    return service.consume(ps, root, include_artifacts=True, comparative_profile=profile,
        expected_comparative_profile_sha256=digest(profile) if profile is not None else None)


def compose(root, path, inputs=None):
    if inputs is not None: inputs.add(str(Path(path)))
    meta = read(root/path)
    if 'baseline_composition' in meta:
        ref = meta['baseline_composition']
        require(file_hash(root/ref['path']) == ref['sha256'], 'Previous composition file changed')
        before = compose(root, ref['path'], inputs)
        require(authority_digest(before) == ref['complete_composed_answer_sha256'], 'Previous composed value changed')
    else:
        ref = meta['baseline']
        require(file_hash(root/ref['path']) == ref['file_sha256'], 'Previous complete answer file changed')
        before = load(root/ref['path'])
        require(authority_digest(before) == ref['content_sha256'], 'Previous complete answer value changed')
        if inputs is not None: inputs.add(ref['path'])
    ref = meta['overlay']
    require(file_hash(root/ref['path']) == ref['file_sha256'], 'Previous overlay file changed')
    extra = load(root/ref['path'])
    require(authority_digest(extra) == ref['content_sha256'] and not set(before)&set(extra), 'Previous overlay changed')
    if inputs is not None: inputs.add(ref['path'])
    result = {**before, **extra}
    require(authority_digest(result) == meta['complete_composed_answer_sha256'], 'Previous entire composition changed')
    return result


def original(root): return read(root/PRIOR/'profile.json')


def source_files(root): return read(root/PRIOR/'sources.json')


def control_helpers(root):
    spec = importlib.util.spec_from_file_location('comparative_adverse', root/TESTS[0])
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def refuse_outputs(value, prose, verifier, cases):
    rows = []
    for name in cases.OUTPUT_CASES:
        a, e = cases.output_change(value, prose, name)
        try: verifier(a, e)
        except ValueError: rows.append({'case': 'output:'+name, 'rejected': True})
        else: raise ValueError('Incorrect output accepted: '+name)
    return rows


def controls(root):
    f = load(root/FIXTURE); cases = control_helpers(root); p = f['profile']
    value = basis.evaluate(f['graph'], f['baseline'], p, root, expected_profile_sha256=digest(p))
    prose = basis.explain(value)
    verifier = lambda a, e: verify(a, e, p, f['graph'], f['baseline'], f['original'], f['sources'], root, f['prose_sha256'])
    rows = []
    for name in cases.PROFILE_CASES:
        changed = cases.profile_change(p, name)
        try: basis.evaluate(f['graph'], f['baseline'], changed, root, expected_profile_sha256=digest(changed))
        except ValueError: rows.append({'case': 'repinned-profile:'+name, 'rejected': True})
        else: raise ValueError('Incorrect semantic profile accepted: '+name)
    rows += refuse_outputs(value, prose, verifier, cases)
    detected = False
    try: refuse_outputs(value, prose, lambda _a, _e: True, cases)
    except ValueError as exc: detected = str(exc).startswith('Incorrect output accepted:')
    require(detected, 'Permissive verifier undetected')
    return {'cases': rows, 'permissive_checker_detected': detected}


def historical(root):
    paths = [root/SOURCE/'attempt-009', root/REL/'reviews/comparative-controls-203',
        root/'docs/plans/prospectus-comparative-control-repair-2026-10-17.md',
        root/'scripts/prospectus_comparative_control_repair.py',
        root/REL/'closure-routes-2026-10-17-comparative-controls-203.json',
        root/REL/'proposals/comparative-controls-203.json', root/REL/'proposals/comparative-controls-203-review.json',
        root/REL/'revisions/0203.json', root/REL/'program.json']
    files = {f for p in paths for f in (p.rglob('*') if p.is_dir() else [p]) if f.is_file()}
    return {'seconds': 630.9543050872162,
            'bytes': max(182140513, 165135276+sum(p.stat().st_size for p in files))}


def storage(root, attempt, enforce=True):
    old = historical(root)
    files = {root/n for n in (*METHODS, PLAN)}
    files |= {p for folder in (root/REVIEW, root/REL/'reviews/comparative-production-213', attempt, root/RECORD)
              for p in folder.rglob('*') if p.is_file()}
    files |= set((root/REL/'proposals').glob('comparative-production-213*.json'))
    files.add(root/REL/'revisions/0213.json')
    added = sum(p.stat().st_size for p in files if p.is_file())
    if enforce:
        require(added < SELECTOR['new_bytes']-262144 and old['bytes']+added < SELECTOR['cumulative_bytes']-262144,
                'Comparative cumulative storage ceiling')
    return {'historical_seconds': old['seconds'], 'historical_bytes': old['bytes'],
            'new_bytes': added, 'combined_bytes': old['bytes']+added, 'failure_reserve_bytes': 262144}


def frozen(root):
    f = read(root/REVIEW/'frozen.json')
    require(f['methods'] == {n: file_hash(root/n) for n in METHODS}, 'Frozen comparative methods changed')
    require(f['inputs'] == {n: file_hash(root/n) for n in f['inputs']}, 'Frozen comparative source/answer changed')
    return f


def evaluate_result(root):
    ps = products(root); baseline = load(root/NORMAL/'candidate-answer.json.gz'); p = read(root/REVIEW/'profile.json')
    actual = consume(root, ps, p)
    require(set(actual) == set(baseline)|set(ADDED), 'Added comparative fields changed')
    require(digest({k: actual[k] for k in baseline if k != 'report_sha256'}) ==
            digest({k: v for k, v in baseline.items() if k != 'report_sha256'}), 'Whole previous normal answer changed')
    require(actual['report_sha256'] == digest({k: v for k, v in actual.items() if k != 'report_sha256'}),
            'Whole report digest does not cover the new result')
    proof = verify(actual[ADDED[0]], actual[ADDED[1]], p, ps['P1']['payload']['graph'], baseline,
                   original(root), source_files(root), root, read(root/REVIEW/'prose-review.json')['sha256'])
    delta = {k: actual[k] for k in (*ADDED, 'report_sha256')}
    normal_hash, baseline_hash = digest(actual), digest(baseline)
    del ps, baseline, actual
    previous = compose(root, PRIOR+'/answer-composition.json')
    previous_hash = authority_digest(previous)
    require(not set(ADDED)&set(previous), 'Existing reading collides with new consumer fields')
    combined = {**previous, **{k: delta[k] for k in ADDED}}
    require(authority_digest({k: combined[k] for k in previous}) == previous_hash, 'Entire previous reading changed')
    combined_hash = authority_digest(combined)
    del previous, combined
    eps_ref = read(root/PRIOR/'EPS-composition-reference.json')
    require(file_hash(root/eps_ref['path']) == eps_ref['sha256'], 'EPS composition file changed')
    eps = compose(root, eps_ref['path'])
    require(authority_digest(eps) == eps_ref['complete_composed_answer_sha256'], 'Entire separate EPS evidence changed')
    return delta, proof, {'normal_baseline': NORMAL+'/candidate-answer.json.gz', 'normal_baseline_sha256': baseline_hash,
        'normal_answer_sha256': normal_hash, 'normal_hash_convention': 'product default-spaced sorted JSON',
        'previous_complete_answer': PRIOR+'/answer-composition.json', 'previous_complete_sha256': previous_hash,
        'composed_evidence_sha256': combined_hash, 'composition_hash_convention': 'authority compact sorted JSON',
        'EPS_full_composed_sha256': authority_digest(eps), 'previous_readings_preserved': True,
        'changed_normal_fields': ['report_sha256'], 'large_answer_copies': 0}


def validate_submission(root, attempt, task):
    root, attempt = Path(root), Path(attempt); start = time.monotonic(); passed = False
    old = signal.getsignal(signal.SIGALRM)
    def expired(_s, _f): raise ValueError('Comparative acceptance180second ceiling')
    signal.signal(signal.SIGALRM, expired); signal.alarm(180)
    try:
        require(task['id'] == 'source-bes-dep-06' and task.get('comparative_production') == SELECTOR, 'Wrong comparative admission')
        f = frozen(root)
        require(set(METHODS)|set(f['inputs'])|{REVIEW+'/frozen.json'} <= set(task['inputs']), 'Unbound comparative evidence')
        result, manifest = read(attempt/'result.json'), read(attempt/'run-manifest.json')
        require(result['status'] == 'PASS' and result['task_complete'] is False and result['whole_program_complete'] is False
                and manifest['methods'] == f['methods'] and manifest['data_version'] == f['inputs'], 'Invalid comparative submission')
        checked_tests(root/REVIEW/'tests.xml', f['focused_tests'])
        delta, proof, composition = evaluate_result(root)
        require(digest(load(attempt/'answer-delta.json.gz')) == digest(delta)
                and digest(read(attempt/'verification.json')) == digest(proof)
                and digest(read(attempt/'composition.json')) == digest(composition)
                and digest(read(attempt/'controls.json')) == digest(controls(root)), 'Retained comparative result differs')
        elapsed = time.monotonic()-start; state = storage(root, attempt)
        prep = read(root/REVIEW/'preparation.json')['seconds']
        charged = state['historical_seconds']+prep+manifest['wall_seconds']+elapsed
        print(json.dumps({'stage': 'comparative-validation', 'seconds': elapsed, 'cumulative_seconds': charged}), flush=True)
        require(elapsed <= 180 and prep <= 90 and manifest['wall_seconds'] <= 180 and charged <= 1530, 'Comparative cumulative time ceiling')
        passed = True
        return True
    finally:
        signal.alarm(0); signal.signal(signal.SIGALRM, old)
        print(json.dumps({'stage': 'comparative-validation-clock', 'seconds': time.monotonic()-start, 'passed': passed}), flush=True)


def prepare():
    import xml.etree.ElementTree as ET
    start = time.monotonic(); folder = ROOT/REVIEW; folder.mkdir(parents=True, exist_ok=True)
    ledger = folder/'preparation.json'
    prep = read(ledger) if ledger.exists() else {
        'seconds': read(ROOT/PREPARATION_PRIOR)['seconds'], 'stages': [],
        'retained_previous_preparation': {'path': PREPARATION_PRIOR, 'sha256': file_hash(ROOT/PREPARATION_PRIOR)}}
    error = None; index = len(prep['stages'])
    try:
        o = original(ROOT); r = o['reading']; sources = source_files(ROOT)
        spec = {'reading_fields': {k: digest(v) for k, v in r.items()},
                'standards': {k: {'path': v['units_path'], 'sha256': v['units_sha256']} for k, v in sources.items()}}
        if basis.SPEC.exists(): require(read(basis.SPEC) == spec, 'Existing finite source specification changed')
        else: write(basis.SPEC, spec, exclusive=True)
        prose = basis.explain({'findings': r['findings']})
        prose_review = {'sha256': digest(prose.encode()), 'text': prose,
            'basis': 'Exact text reviewed against retained008 source reading; prose hash checks integrity, not legal truth'}
        write(folder/'prose-review.json', prose_review)
        graph = {'units': r['report_context']}; tiny_baseline = {'fixture': 'source binding only; full answer checked by admitted run'}
        fixture = {'graph': graph, 'baseline': tiny_baseline, 'profile': basis.make_profile(graph, tiny_baseline, r),
                   'original': o, 'sources': sources, 'prose_sha256': prose_review['sha256']}
        if (ROOT/FIXTURE).exists(): require(digest(load(ROOT/FIXTURE)) == digest(fixture), 'Existing source fixture changed')
        else: compressed(ROOT/FIXTURE, fixture)
        ps = products(ROOT); baseline = load(ROOT/NORMAL/'candidate-answer.json.gz')
        profile = basis.make_profile(ps['P1']['payload']['graph'], baseline, r)
        write(folder/'profile.json', profile)
        inputs = {PLAN, PREPARATION_PRIOR, REL+'/reviews/comparative-production-213/PACKAGING-REVIEW.md',
                  PRIOR+'/profile.json', PRIOR+'/sources.json', PRIOR+'/EPS-composition-reference.json',
                  NORMAL+'/candidate-P1-reference.json.gz', NORMAL+'/candidate-P2-P5.json.gz', NORMAL+'/candidate-answer.json.gz',
                  SOURCE+'/attempt-001/source-product.json.gz', SOURCE+'/attempt-009/result.json',
                  REVIEW+'/preparation.json', REVIEW+'/profile.json', REVIEW+'/prose-review.json'}
        inputs |= {d['path'] for d in ps['P1']['payload']['request']['bundle']['documents']}
        inputs |= {i['path'] for i in r['images']} | {v['units_path'] for v in sources.values()}
        # Walk composition references without repeatedly decoding their large answers.
        def collect(path):
            inputs.add(path); m = read(ROOT/path); inputs.add(m['overlay']['path'])
            if 'baseline_composition' in m: collect(m['baseline_composition']['path'])
            else: inputs.add(m['baseline']['path'])
        collect(PRIOR+'/answer-composition.json'); collect(read(ROOT/PRIOR/'EPS-composition-reference.json')['path'])
        del ps, baseline
        log, xml = folder/f'tests-{index:02d}.log', folder/f'tests-{index:02d}.xml'
        with log.open('x') as stream:
            subprocess.run([sys.executable, '-m', 'pytest', *TESTS, '-q', '--junitxml='+str(xml)], cwd=ROOT,
                env={**os.environ, 'PYTHONPATH': str(ROOT/'src'), 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONDONTWRITEBYTECODE': '1'},
                stdout=stream, stderr=subprocess.STDOUT, timeout=max(1, 90-prep['seconds']-(time.monotonic()-start)), check=True)
        tests = sum(int(s.attrib.get('tests', 0)) for s in ET.parse(xml).getroot().iter('testsuite'))
        (folder/'tests.xml').write_bytes(xml.read_bytes())
    except Exception as exc:
        error = type(exc).__name__+': '+str(exc)
        (folder/f'preparation-{index:02d}-failure.txt').write_text(traceback.format_exc(limit=8))
    elapsed = time.monotonic()-start; prep['seconds'] += elapsed
    prep['stages'].append({'seconds': elapsed, 'status': 'FAIL' if error else 'PASS', 'error': error})
    prep.update(command=[sys.executable, '-m', 'scripts.prospectus_comparative_production', 'prepare'],
                cpu_gpu='CPU_ONLY; CUDA_VISIBLE_DEVICES=-1', exclusions='Authoring/reading excluded; preparation/tests charged')
    write(ledger, prep)
    if error:
        print(json.dumps({'stage': 'preparation', 'error': error, 'seconds': prep['seconds']})); return 1
    require(prep['seconds'] <= 90, 'Comparative preparation time ceiling')
    f = {'methods': {n: file_hash(ROOT/n) for n in METHODS}, 'inputs': {n: file_hash(ROOT/n) for n in sorted(inputs)},
         'focused_tests': tests, 'selector': SELECTOR, 'parent_bindings_verified': True}
    write(folder/'frozen.json', f, exclusive=True)
    state = storage(ROOT, ROOT/SOURCE/'attempt-010')
    require(state['new_bytes']+16*1024**2+262144 < SELECTOR['new_bytes']
            and state['combined_bytes']+16*1024**2+262144 < SELECTOR['cumulative_bytes'], 'Comparative authority-copy forecast')
    write(folder/'preflight.json', {**state, 'additional_forecast_bytes': 16*1024**2, 'preparation_seconds': prep['seconds']}, exclusive=True)
    proposal, review = proposal213(f, inputs)
    write(ROOT/REL/'proposals/comparative-production-213-r2.json', proposal, exclusive=True)
    write(ROOT/REL/'proposals/comparative-production-213-r2-review.json', review, exclusive=True)
    print(json.dumps({'stage': 'prepared213', 'tests': tests, 'seconds': prep['seconds'], **state})); return 0


def proposal213(f, inputs):
    auth = Authority(ROOT); program, _, _ = auth.spec(); require(program['revision'] == 212, 'Expected212 baseline')
    proposal = deepcopy(program); proposal['revision'] = 213
    task = next(t for t in proposal['tasks'] if t['id'] == 'source-bes-dep-06')
    old_dossier = task['dossier']
    task.update(dossier=PLAN, timeout_seconds=210, comparative_production=SELECTOR,
        reason='Integrate original conditional accounting alternatives and reported adoptions through normal003consumer; preserve full008/EPS, unresolved cause and original obligations.')
    task['inputs'] = sorted(set(task['inputs'])|set(METHODS)|inputs|{old_dossier, REVIEW+'/frozen.json', REVIEW+'/preflight.json'})
    proposal['budgets'][task['budget_key']]['maximum_new_attempts'] = 10
    proposal['build_contract']['criteria'][task['id']] = [
        {'id': 'comparative-accounting-basis', 'basis': 'NAMED_CONDITIONAL_CHECK', 'validator': 'bes-comparative-basis.v1',
         'description': 'Original conditional accounting mechanisms and reported adoptions reach normal consumer without selecting a cause'},
        {'id': 'remaining-source-coverage', 'basis': 'ORIGINAL_TASK_ACCEPTANCE', 'validator': None,
         'description': 'All original source06 obligations remain; finite conditional integration cannot complete them'}]
    review = {'baseline': authority_digest(program),
        'changes': ['Optional normal consumer with whole-report digest covering added evidence',
                    'Separate original-source/reading verifier and semantic adverse controls',
                    'Retain all original obligations, attempts and cumulative costs'],
        'skeptical_audit': {'verdict': 'PASS_AFTER_SOURCE_AND_PARENT_REVIEW', 'plan': PLAN,
            'findings': ['Saved003selected-request parents checked before admission',
                         'Original008reading preserves IAS1/IAS8 conditions, date/edition differences and adoption headings',
                         'Numerical equality cannot supply a cause; estimate revision alone is prospective',
                         'Full normal fields preserved except recomputed report digest; complete008/EPS decoded by run',
                         'Finite supplied interpretation is not automatic legal classification; no external-opinion prerequisite',
                         'Realistic bounded candidate and acceptance; source corruption and frozen drift veto the run',
                         'Pre-admission revision binds pyproject package data; all earlier preparation seconds and all superseded proposals charged']},
        'evidence_contract': {'question': 'Does the ordinary answer preserve source-bound comparative mechanisms without inventing a cause?',
            'baseline': NORMAL+'/candidate-answer.json.gz', 'primary': 'Actual complete consumer on/off plus original-source verifier',
            'promotion_veto': 'Dropped condition/edition, fabricated cause/compliance, changed prior answer or accepted adverse input',
            'continuation_veto': 'Invalid baseline, corrupt evidence, frozen method drift or explicit cumulative ceilings',
            'explanatory': ['counts', 'time', 'storage'],
            'not_concluded': ['specific accounting cause', 'compliance', 'automatic discovery', 'original task or build completion'],
            'artifacts': SOURCE+'/attempt-010'},
        'scope_unchanged': True, 'budget_unchanged': False, 'delivery_scope_changed': True,
        'delivery_authorization': proposal['build_contract']['authorization'], 'original_obligations_preserved': True,
        'budget_revision': {'budget_key': task['budget_key'], 'previous_maximum': 9, 'new_maximum': 10,
            'retained_attempts': [e['attempt'] for e in auth.events() if e['kind'] == 'ADMIT' and e['budget_key'] == task['budget_key']],
            'reason': 'First normal-consumer integration of the detached comparative accounting reading',
            'next_discriminating_check': 'Actual whole answer and source-condition preservation under fresh semantic perturbations',
            'stop_condition': '90seconds prep/180candidate/180acceptance;1530cumulative;40MiB new/220MiB cumulative; no unchanged retry',
            'same_scope_authorization': 'User requests refreshed general build and continued execution without external advisers'}}
    return proposal, review


def run(attempt_name):
    auth = Authority(ROOT); attempt = auth.path(attempt_name); admission = read(attempt/'admission.json')
    program, tasks, _ = auth.spec(); task = tasks['source-bes-dep-06']
    require(admission['binding'] == auth.binding(task) and admission['task_spec'] == task
            and admission['program_sha256'] == authority_digest(program) and task['comparative_production'] == SELECTOR,
            'Current comparative admission required')
    latest = next(e for e in reversed(auth.events()) if e.get('task') == task['id'])
    require(latest['kind'] == 'ADMIT' and latest['attempt'] == attempt_name, 'Comparative attempt is not newly admitted')
    start = time.monotonic(); f = frozen(ROOT)
    manifest = {'command': [sys.executable, '-m', 'scripts.prospectus_comparative_production', 'run', '--attempt', attempt_name],
        'git_commit': admission['git_commit'], 'environment': {'python': sys.version, 'executable': sys.executable, 'service': service.__file__},
        'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1', 'random_seeds': 'N/A; deterministic conditional source comparison',
        'methods': f['methods'], 'data_version': f['inputs'], 'plan': PLAN, 'result': attempt_name+'/RESULT.md',
        'accounting': SELECTOR, 'preparation_seconds': read(ROOT/REVIEW/'preparation.json')['seconds']}
    write(attempt/'started.json', manifest, exclusive=True)
    def expired(_s, _f): raise TimeoutError('Comparative candidate180second ceiling')
    signal.signal(signal.SIGALRM, expired); signal.alarm(180)
    status, error, proof = 'PASS', None, {}
    try:
        storage(ROOT, attempt)
        ps = products(ROOT); off = consume(ROOT, ps); baseline = load(ROOT/NORMAL/'candidate-answer.json.gz')
        require(digest(off) == digest(baseline), 'Unconfigured complete original003consumer changed')
        del ps, off, baseline
        print(json.dumps({'stage': 'normal-consumer-off', 'status': 'PASS'}), flush=True)
        delta, proof, composition = evaluate_result(ROOT); adverse = controls(ROOT)
        compressed(attempt/'answer-delta.json.gz', delta)
        for name, value in [('verification', proof), ('composition', composition), ('controls', adverse)]:
            write(attempt/(name+'.json'), value, exclusive=True)
        frozen(ROOT)
    except Exception as exc:
        status, error = 'FAIL', type(exc).__name__+': '+str(exc)
        (attempt/'failure-trace.txt').write_text(traceback.format_exc(limit=10)[-8192:])
    signal.alarm(0)
    manifest.update(status=status, error=error, wall_seconds=time.monotonic()-start)
    try: manifest['storage'] = storage(ROOT, attempt)
    except Exception as exc:
        status, error = 'FAIL', str(exc); manifest.update(status=status, error=error, storage=storage(ROOT, attempt, False))
    write(attempt/'run-manifest.json', manifest, exclusive=True)
    write(attempt/'result.json', {'task': task['id'], 'status': status, 'error': error, 'summary': proof,
                                'task_complete': False, 'whole_program_complete': False}, exclusive=True)
    (attempt/'RESULT.md').write_text('# Comparative accounting integration\n\nStatus: '+status+'.\n\n'
        +'| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Limit |\n'
        +'| --- | --- | --- | --- | --- | --- |\n'
        +('| Retain conditional integration pending acceptance | Normal consumer and original source verifier passed | No adverse case accepted | Specific accounting cause and applicable transition basis | Record, refresh, continue master | Original task/build incomplete |\n'
          if status == 'PASS' else '| Reject candidate | Failed | See failure trace | Local implementation or source mismatch | Reviewed discriminating repair | No package-direction rejection |\n')
        +'\nThe complete008 reading and separate EPS composition are preserved. Full normal fields survive except the report digest, which now covers the addition. No cause, compliance or violation is selected.\n\n'
        +'Post-run red team: production and verifier preserve a supplied interpretation; they cannot prove exhaustive legal interpretation. The original source-specific cause remains absent from inspected passages. A dated specific explanation could change that conclusion. Source hashes and prose hashes establish identity only. Exact method, data, timing and environment identities are in run-manifest.json.\n')
    write(attempt/'outputs.json', {p.name: file_hash(p) for p in attempt.iterdir() if p.is_file() and p.name != 'outputs.json'}, exclusive=True)
    print(json.dumps({'stage': 'comparative-candidate', 'status': status, 'error': error, 'seconds': manifest['wall_seconds']}), flush=True)
    return 0 if status == 'PASS' else 1


def record(attempt_name):
    folder = ROOT/RECORD; folder.mkdir(parents=True, exist_ok=True); start = time.monotonic(); error = None; result = None
    try:
        with (folder/'command.log').open('x') as log:
            result = subprocess.run([sys.executable, '-m', 'scripts.prospectus_control', 'record', '--attempt', attempt_name],
                cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=210, check=False)
    except Exception as exc: error = type(exc).__name__+': '+str(exc)
    event = next(e for e in reversed(Authority(ROOT).events()) if e.get('attempt') == attempt_name)
    receipt = {'wall_seconds': time.monotonic()-start, 'error': error, 'exit_code': result.returncode if result else None,
        'kind': event['kind'], 'reason': event.get('reason'), 'build_acceptances': event.get('build_acceptances', []),
        'event_sha256': event['sha256'], 'command_log_sha256': file_hash(folder/'command.log')}
    write(folder/'receipt.json', receipt, exclusive=True); print(json.dumps(receipt))
    return 0 if 'comparative-accounting-basis' in receipt['build_acceptances'] else 1


def main():
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'run', 'record']); parser.add_argument('--attempt'); a = parser.parse_args()
    if a.action == 'prepare': return prepare()
    if not a.attempt: parser.error('--attempt required')
    return run(a.attempt) if a.action == 'run' else record(a.attempt)


if __name__ == '__main__': raise SystemExit(main())
