"""Pinned builds and exact native verification, independent of RuleIR evaluators."""
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import tempfile
import zipfile
from . import PROFILE
from .semantics import profile, commitment
from .dependencies import library, trace_tools, interpreter_library
from .contracts import fail, literal, program, source_map, validate_candidate, validate_task, validate_value, outside_domain
from .boundary import prepare
from ..backend import _pinned
from ...canonical import canonical, digest, loads, raw_digest
from ...java.manifest import toolchain

ROOT = Path(__file__).resolve().parent


def implementation_hash():
    return digest({p.name: raw_digest(p.read_bytes()) for p in sorted(ROOT.iterdir()) if p.suffix in ('.py', '.java')})


def run_command(command, cwd, *, input_bytes=None, timeout=120):
    """Bound wall time and log bytes; no model-supplied commands or filenames."""
    def limits():
        resource.setrlimit(resource.RLIMIT_FSIZE, (8_000_000, 8_000_000))
        resource.setrlimit(resource.RLIMIT_CPU, (timeout, timeout + 1))
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        try:
            proc = subprocess.run(list(map(str, command)), cwd=cwd, input=input_bytes,
                                  stdout=stdout, stderr=stderr, timeout=timeout, preexec_fn=limits)
        except subprocess.TimeoutExpired:
            fail('E_RESOURCE_LIMIT', 'Native command deadline')
        stdout.seek(0); stderr.seek(0)
        out, err = stdout.read(8_000_001), stderr.read(8_000_001)
    if len(out) > 8_000_000 or len(err) > 8_000_000:
        fail('E_RESOURCE_LIMIT', 'Native command output limit')
    return {'command': list(map(str, command)), 'exit_code': proc.returncode,
            'stdout': out.decode('utf-8', errors='replace'), 'stderr': err.decode('utf-8', errors='replace')}


def _require(record):
    if record['exit_code']:
        fail('E_DEPENDENCY', (record['stderr'] or record['stdout'])[-12000:])
    return record


def build(task, candidate, output, jdk, *, compiler, upstream, lock):
    t = validate_task(task)
    c = validate_candidate(t, candidate)
    src = program(t, c)
    compiler, locked, runtime, license_bytes = _pinned(compiler, upstream, lock)
    jdk, java_version = toolchain(jdk)
    out = Path(output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if (out / 'build.json').exists():
        fail('E_JOB_STATE', 'Build directory already contains a sealed build')
    logs = []

    def command(argv, cwd):
        r = run_command(argv, cwd)
        logs.append(r)
        (out / 'build-commands.json').write_bytes(canonical(logs))
        return _require(r)

    scopes = sorted(set(re.findall(r'\bdeclaration\s+scope\s+([A-Z][a-zA-Z0-9]*)\s*:', src)))
    if t['entry_scope'] not in scopes:
        fail('E_REFERENCE')
    source_locations = source_map(t, c)
    core = {'record_type': 'NativeCatalaBuild', 'profile': profile(t), 'task_hash': digest(t),
            'candidate_hash': digest(c), 'source_sha256': raw_digest(src.encode()),
            'compiler_sha256': locked['compiler_sha256'], 'compiler_version': locked['compiler_version'],
            'lock_sha256': raw_digest(Path(lock).read_bytes()), 'upstream_commit': locked['upstream_commit'],
            'implementation_hash': implementation_hash(), 'java_version': java_version,
            'runtime_sha256': digest(runtime), 'source_map': source_locations,
            'trace_kind': 'JAVA_SCOPE_OUTPUT_ASSIGNMENTS', 'stdlib_profile': 'PINNED_BUILTINS_NO_IMPORTS'}
    core.update(commitment(t))
    traced = profile(t).endswith('v2')
    if traced:
        tracer, trace_lock = trace_tools()
        if trace_lock['base_compiler_sha256'] != locked['compiler_sha256']:
            fail('E_HASH_MISMATCH', 'Trace compiler base')
        core.update(trace_toolchain=trace_lock, trace_kind='SOURCE_POSITION_DECISIONS_AND_SCOPE_OUTPUTS',
                    trace_invariant_check='original_and_instrumented')
    jars = {}
    with tempfile.TemporaryDirectory(prefix='legalmath-native-') as temp:
        staging = Path(temp)
        (staging / 'Native.catala_en').write_text(src)
        dependencies, libraries = library(t, upstream, {**locked, 'compiler_path_resolved': str(compiler)}, staging, command)
        includes = ['-I', 'stdlib'] if libraries else []
        if traced:
            core['dependencies'] = dependencies
            core['stdlib_profile'] = 'PINNED_DECLARED_LIBRARY_CLOSURE'
        for name in dependencies.get('interpreter_plugins', {}):
            p = out / name; p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes((staging / name).read_bytes())
        command([compiler, 'java', 'Native.catala_en', '--no-stdlib', *includes, '--check-invariants', '--output', 'Native.java'], staging)
        plain = (staging / 'Native.java').read_text()
        observed = plain
        if traced:
            # Observe Java emission after the ordinary invariant-checked passes.
            command([tracer, 'java', 'Native.catala_en', '--no-stdlib', *includes, '--trace', '--check-invariants', '--output', 'Native.java'], staging)
            observed = (staging / 'Native.java').read_text()
        # Only compiler-emitted final field assignments are instrumented. The runtime
        # filters owners to declared scopes; record constructors are not scope events.
        # Copy constructors assign result.field and must not count as another
        # calculation. Capture only assignment of the computed local variable.
        instrumented, count = re.subn(r'(?m)^(\s*this\.([A-Za-z][A-Za-z0-9_]*) = \2;)$',
            lambda m: m[1] + '\n            NativeBridge.capture(this, "' + m[2] + '", this.' + m[2] + ');', observed)
        if count == 0:
            fail('E_UNSUPPORTED_PROFILE', 'No scope assignments found for instrumentation')
        (out / 'Native.catala_en').write_text(src)
        (out / 'Native.java').write_text(plain)
        (out / 'Native.instrumented.java').write_text(instrumented)
        sources = {**runtime, 'NativeBridge.java': (ROOT / 'NativeBridge.java').read_text(),
                   'NativeTrace.java': (ROOT / 'NativeTrace.java').read_text(),
                   'Json.java': (ROOT.parents[1] / 'java/runtime/Json.java').read_text()}
        for name, text in sources.items():
            p = staging / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        classes = staging / 'classes'
        classes.mkdir()
        flags = ['--release', '17', '-encoding', 'UTF-8', '-g:none', '-parameters']
        command([jdk / 'bin/javac', *flags, '-d', 'classes', *sorted(runtime), 'Json.java', 'NativeTrace.java'], staging)
        for mode, generated in (('plain', plain), ('instrumented', instrumented)):
            (staging / 'Native.java').write_text(generated)
            command([jdk / 'bin/javac', *flags, '-cp', 'classes', '-d', 'classes', 'Native.java', 'NativeBridge.java', *libraries], staging)
            entries = {p.relative_to(classes).as_posix(): p.read_bytes() for p in classes.rglob('*.class')}
            entries.update({'META-INF/legalmath/native-build.json': canonical({**core, 'instrumented': mode == 'instrumented'}),
                            'META-INF/legalmath/native-task.json': canonical(t),
                            'META-INF/legalmath/native-candidate.json': canonical(c),
                            'META-INF/legalmath/native-scopes.json': canonical(scopes),
                            'META-INF/legalmath/Catala-LICENSE.txt': license_bytes,
                            'META-INF/legalmath/Native.catala_en': src.encode(),
                            'META-INF/legalmath/Native.java': generated.encode()})
            path = out / (mode + '.jar')
            with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_STORED) as archive:
                for name, data in sorted(entries.items()):
                    info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, data)
            jars[mode] = {'filename': path.name, 'sha256': raw_digest(path.read_bytes())}
    manifest = {**core, 'jars': jars}
    (out / 'task.json').write_bytes(canonical(t))
    (out / 'candidate.json').write_bytes(canonical(c))
    (out / 'build.json').write_bytes(canonical(manifest))
    return manifest


def verify_build(directory, *, expected_hash=None):
    directory = Path(directory)
    manifest = loads((directory / 'build.json').read_bytes())
    if expected_hash is not None and digest(manifest) != expected_hash:
        fail('E_HASH_MISMATCH', 'Native build approval')
    task = validate_task(loads((directory / 'task.json').read_bytes()))
    candidate = validate_candidate(task, loads((directory / 'candidate.json').read_bytes()))
    if manifest['profile'] != profile(task) or manifest['task_hash'] != digest(task) or manifest['candidate_hash'] != digest(candidate) or manifest['source_sha256'] != raw_digest(program(task, candidate).encode()):
        fail('E_INTEGRITY', 'Native build commitments')
    if any(manifest.get(k) != v for k,v in commitment(task).items()):
        fail('E_INTEGRITY', 'Native semantics')
    if manifest['source_map'] != source_map(task, candidate):
        fail('E_INTEGRITY', 'Native source map')
    core = {k: v for k, v in manifest.items() if k != 'jars'}
    for mode in ('plain', 'instrumented'):
        jar = manifest['jars'][mode]
        if jar['filename'] != mode + '.jar':
            fail('E_INTEGRITY')
        path = directory / jar['filename']
        if raw_digest(path.read_bytes()) != jar['sha256']:
            fail('E_HASH_MISMATCH', 'Native JAR')
        with zipfile.ZipFile(path) as archive:
            for name, expected in (('native-build.json', {**core, 'instrumented': mode == 'instrumented'}), ('native-task.json', task), ('native-candidate.json', candidate)):
                if loads(archive.read('META-INF/legalmath/' + name)) != expected:
                    fail('E_INTEGRITY', 'Embedded native commitment')
    return task, candidate, manifest


def execute_values(directory, inputs, jdk, *, instrumented=True, expected_hash=None):
    task, candidate, manifest = verify_build(directory, expected_hash=expected_hash)
    if set(inputs) != {f['name'] for f in task['inputs']}:
        fail('E_SCHEMA')
    for f in task['inputs']:
        validate_value(task, f['type'], inputs[f['name']])
    if outside_domain(task, inputs):
        fail('E_TYPE', 'Input is outside its declared source domain')
    mode = 'instrumented' if instrumented else 'plain'
    # Execute exactly the bytes checked against this build, even if the caller's
    # package directory changes while Java starts.
    jar_bytes = (Path(directory) / manifest['jars'][mode]['filename']).read_bytes()
    if raw_digest(jar_bytes) != manifest['jars'][mode]['sha256']:
        fail('E_HASH_MISMATCH')
    with tempfile.TemporaryDirectory(prefix='native-execute-') as execution:
        jar = Path(execution) / 'policy.jar'; jar.write_bytes(jar_bytes)
        r = _require(run_command([Path(jdk).resolve() / 'bin/java', '-Xmx256m', '-XX:MaxMetaspaceSize=128m', '-cp',
              str(jar), 'catala.stdlib.NativeBridge'], execution, input_bytes=canonical(inputs), timeout=15))
    result = loads(r['stdout'].encode())
    keys = {'value', 'trace', 'decisions'} if profile(task).endswith('v2') else {'value', 'trace'}
    if set(result) != keys or set(result['value']) != {f['name'] for f in task['outputs']}:
        fail('E_INTEGRITY', 'Compiled output differs from declared interface')
    for f in task['outputs']:
        validate_value(task, f['type'], result['value'][f['name']])
    if instrumented:
        entry = {row['field']: row['value'] for row in result['trace'] if row['scope'] == task['entry_scope']}
        if entry != result['value']:
            fail('E_INTEGRITY', 'Executed entry observations disagree with returned value')
    elif result['trace']:
        fail('E_INTEGRITY', 'Uninstrumented program emitted observations')
    if 'decisions' in result:
        if not instrumented and result['decisions']:
            fail('E_INTEGRITY', 'Plain program emitted decisions')
        for event in result['decisions']:
            lines = program(task,candidate).splitlines()
            if (event['file'] != 'Native.catala_en' or not (1 <= event['start_line'] <= event['end_line'] <= len(lines))
                    or not 0 <= event['start_column'] <= len(lines[event['start_line']-1].encode())+1
                    or not 0 <= event['end_column'] <= len(lines[event['end_line']-1].encode())+1):
                fail('E_INTEGRITY', 'Decision has no retained source position')
            event['program_sha256'] = manifest['source_sha256']
    return result


def evaluate(directory, snapshot, jdk, *, expected_hash=None):
    task, candidate, manifest = verify_build(directory, expected_hash=expected_hash)
    boundary = prepare(task, snapshot)
    reason = 'UNRESOLVED_INTERPRETATION' if candidate['unresolved'] else boundary['reason']
    result = {'record_type': 'NativeCatalaEvaluation', 'profile': profile(task),
              'build_hash': digest(manifest), 'task_hash': digest(task), 'candidate_hash': digest(candidate),
              'snapshot_hash': digest(snapshot), 'source_map': manifest['source_map'],
              'evidence': boundary['evidence'], 'status': 'ABSTAIN' if reason else 'VALUE',
              'reason': reason, 'missing_inputs': boundary['missing_inputs'], 'blocking_inputs': boundary['blocking_inputs'],
              'value': None, 'trace': [], 'trace_kind': manifest['trace_kind']}
    result.update(commitment(task))
    if profile(task).endswith('v2'):
        result['decisions'] = []
    if 'bounds' in task:
        result['invalid_inputs'] = boundary['invalid_inputs']
    if not reason:
        result.update(execute_values(directory, boundary['inputs'], jdk, expected_hash=digest(manifest)))
    result['result_hash'] = digest(result)
    return result


def verify_result(directory, snapshot, result, jdk):
    """Replay actual Java; a self-consistent rewritten hash is insufficient."""
    expected = evaluate(directory, snapshot, jdk)
    if result != expected:
        fail('E_INTEGRITY', 'Native result/evidence replay mismatch')
    return True


def interpreter_check(task, candidate, inputs, expected, *, compiler, directory=None):
    """Exact equality is evaluated by Catala before exporting one Boolean.

    This avoids the pinned interpreter's lossy decimal/money JSON encoding.
    Expected values never appear in generation or repair requests.
    """
    t = validate_task(task)
    if set(expected) != {f['name'] for f in t['outputs']} or set(inputs) != {f['name'] for f in t['inputs']}:
        fail('E_SCHEMA')
    args = ' '.join('-- ' + f['name'] + ': ' + literal(t, f['type'], inputs[f['name']]) for f in t['inputs'])
    comparisons = ['(actual.' + f['name'] + ' = ' + literal(t, f['type'], expected[f['name']]) + ')' for f in t['outputs']]
    check = '\n```catala\ndeclaration scope NativeCheck:\n  output matches condition\nscope NativeCheck:\n  definition matches equals\n    let actual equals output of ' + t['entry_scope'] + ' with { ' + args + ' } in\n    ' + ' and '.join(comparisons) + '\n```\n'
    with tempfile.TemporaryDirectory(prefix='legalmath-native-check-') as temp:
        p = Path(temp) / 'Native.catala_en'
        p.write_text(program(t, candidate) + check)
        includes = []
        if t.get('imports'):
            if directory is None: fail('E_REFERENCE', 'Imported checks require a sealed build')
            _, _, manifest = verify_build(directory)
            includes = interpreter_library(manifest, directory, temp)
        r = _require(run_command([Path(compiler).resolve(), 'interpret', 'Native.catala_en', '--no-stdlib', *includes, '--scope=NativeCheck', '--output-format=json'], temp, timeout=15))
    value = loads(r['stdout'].encode())
    if value != {'matches': True}:
        fail('E_INTEGRITY', 'Native interpreter disagrees with exact reference')
    return {'exact_match': True, 'check_source_sha256': raw_digest(check.encode()), 'command': r['command'], 'stderr': r['stderr']}


def verify_cases(directory, cases, jdk, *, compiler):
    task, candidate, manifest = verify_build(directory)
    records = []
    if not cases:
        fail('E_SCHEMA', 'Verification requires independently specified cases')
    for case in cases:
        boundary = prepare(task, case['snapshot'])
        result = evaluate(directory, case['snapshot'], jdk)
        expected = case['expected']
        if result['status'] != expected['status'] or result['value'] != expected.get('value'):
            fail('E_INTEGRITY', 'Independent reference mismatch: ' + case['id'])
        if 'reason' in expected and result['reason'] != expected['reason']:
            fail('E_INTEGRITY', 'Independent abstention reason mismatch: ' + case['id'])
        record = {'case_id': case['id'], 'snapshot_hash': digest(case['snapshot']), 'result': result}
        if result['status'] == 'VALUE':
            plain = execute_values(directory, boundary['inputs'], jdk, instrumented=False)
            if plain['value'] != result['value']:
                fail('E_INTEGRITY', 'Instrumentation changes results')
            record['interpreter'] = interpreter_check(task, candidate, boundary['inputs'], expected['value'], compiler=compiler, directory=directory)
            record['instrumentation_preserves_value'] = True
        records.append(record)
    report = {'record_type': 'NativeCatalaVerification', 'profile': profile(task), 'build_hash': digest(manifest),
              'cases_hash': digest(cases), 'passed': len(records), 'records': records,
              'claim': 'Finite development cases, conditional on the independent reference; no source-correctness certification'}
    report['report_hash'] = digest(report)
    return report
