"""Explicit signed exact-percentage input profile for rational RuleIR policies.

This boundary imposes a representation limit, not a permissible exposure range.
Hosts select it explicitly; legacy raw-snapshot policies keep their old API.
"""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

from ..canonical import canonical, digest, raw_digest, loads
from ..errors import LegalMathError
from ..ir.evaluate import evaluate
from ..ir.typecheck import validate_bundle
from .emit import emit, runtime_sources
from .manifest import toolchain

PROFILE = 'signed-exact-percent-v1'
EXTERNAL = {'fund_manager': 'bool', 'va_objective': 'bool', 'intended_va_percent': 'decimal_percent'}
INTERNAL = {'fund_manager': 'bool', 'va_objective': 'bool',
            'va_bps_numerator': 'integer', 'va_bps_denominator': 'integer'}


def ratio(value):
    if type(value) is not str or len(value) > 64 or not re.fullmatch(r'-?(0|[1-9][0-9]*)(\.[0-9]+)?', value):
        raise LegalMathError('E_SCHEMA')
    f = Fraction(value) * 100
    return str(f.numerator), str(f.denominator)


def snapshot(request):
    if type(request) is not dict or set(request) != {'profile', 'subject_id', 'facts', 'valid_at', 'known_at', 'mode'}:
        raise LegalMathError('E_SCHEMA')
    if request['profile'] != PROFILE or request['mode'] != 'draft':
        raise LegalMathError('E_SCHEMA')
    facts = request['facts']
    if type(facts) is not dict or not set(facts) <= set(EXTERNAL):
        raise LegalMathError('E_SCHEMA', details='Internal numerator/denominator and arbitrary fields are forbidden')
    result = {}
    for name, typ in EXTERNAL.items():
        f = deepcopy(facts.get(name, {'type': typ, 'status': 'unknown', 'reason': 'MISSING'}))
        if type(f) is not dict or f.get('type') != typ:
            raise LegalMathError('E_SCHEMA')
        keys = {'known': {'type', 'status', 'value', 'evidence_ids', 'valid_from', 'valid_until', 'recorded_at'},
                'unknown': {'type', 'status', 'reason'}, 'conflict': {'type', 'status', 'evidence_ids'}}
        if f.get('status') not in keys or set(f) != keys[f['status']]:
            raise LegalMathError('E_SCHEMA')
        if name != 'intended_va_percent':
            result[name] = f
        else:
            values = ratio(f['value']) if f['status'] == 'known' else (None, None)
            for target, val in zip(('va_bps_numerator', 'va_bps_denominator'), values):
                converted = deepcopy(f); converted['type'] = 'integer'
                if val is not None:
                    converted['value'] = val
                result[target] = converted
    return {'subject_id': request['subject_id'], 'facts': result}


def validate_profile(bundle, profile):
    if profile != PROFILE or validate_bundle(bundle):
        raise LegalMathError('E_UNSUPPORTED_PROFILE')
    if {f['name']: f['type'] for f in bundle['facts']} != INTERNAL or len(bundle['facts']) != 4:
        raise LegalMathError('E_UNSUPPORTED_PROFILE')
    if not any(r['id'] == 'selected.control' for r in bundle['rules']):
        raise LegalMathError('E_REFERENCE')


def evaluate_request(bundle, request):
    try:
        validate_profile(bundle, PROFILE)
        s = snapshot(request)
        result = evaluate(bundle, s, 'selected.control', request['valid_at'], request['known_at'], request['mode'])
        # Validation errors are rejected at this external boundary. A legitimate
        # historical refusal stays an accepted input with an ERROR decision.
        if result['status'] == 'ERROR' and result['reason_codes'] != ['E_VERSION_TIME']:
            raise LegalMathError('E_SCHEMA')
        return {'boundary_status': 'ACCEPTED', 'profile': PROFILE, 'snapshot': s,
                'result': result, 'release_eligible': False}
    except (LegalMathError, TypeError, KeyError, ValueError):
        return {'boundary_status': 'REJECTED', 'error': 'E_SCHEMA', 'release_eligible': False}


def build(bundle, output, jdk, *, profile):
    """Build a JAR whose declared entry point accepts only this external profile."""
    validate_profile(bundle, profile)
    jdk, version = toolchain(jdk)
    name, source = emit(bundle)
    entry = 'Percent_' + digest({'bundle': bundle, 'profile': profile})[:20]
    wrapper = '''package hk.legalmath;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
public final class ENTRY {
    private ENTRY() {}
    public static String evaluate(String request) {
        return ExactPercentageBoundary.evaluate(request, POLICY::evaluate);
    }
    public static void main(String[] args) throws Exception {
        if (args.length != 0) throw new IllegalArgumentException("No raw-policy parameters accepted");
        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        String line;
        while ((line = reader.readLine()) != null) System.out.println(evaluate(line));
    }
}
'''.replace('ENTRY', entry).replace('POLICY', name)
    sources = {**runtime_sources(), name + '.java': source, entry + '.java': wrapper}
    flags = ['--release', '17', '-encoding', 'UTF-8', '-g:none', '-Xlint:all', '-Werror']
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='legalmath-percent-') as td:
        td = Path(td); classes = td/'classes'; classes.mkdir()
        for filename, text in sources.items():
            (td/filename).write_text(text)
        subprocess.run([str(jdk/'bin/javac'), *flags, '-d', str(classes),
                        *map(str, sorted(td.glob('*.java')))], check=True, capture_output=True, timeout=60)
        jar = td/'policy.jar'
        with zipfile.ZipFile(jar, 'w', compression=zipfile.ZIP_STORED) as archive:
            manifest = f'Manifest-Version: 1.0\r\nMain-Class: hk.legalmath.{entry}\r\n\r\n'.encode()
            entries = {'META-INF/MANIFEST.MF': manifest,
                       **{str(p.relative_to(classes)): p.read_bytes() for p in classes.rglob('*.class')}}
            for path, data in sorted(entries.items()):
                info = zipfile.ZipInfo(path, (1980, 1, 1, 0, 0, 0)); info.external_attr = 0o100644 << 16
                archive.writestr(info, data)
        jar_bytes = jar.read_bytes()
    jar_hash = raw_digest(jar_bytes); target = output/(jar_hash+'.jar'); target.write_bytes(jar_bytes)
    record = {'record_type': 'ExactPercentageBuild', 'profile': profile, 'bundle_hash': digest(bundle),
        'jar_sha256': jar_hash, 'entry_class': 'hk.legalmath.'+entry, 'compiler': version,
        'source_hashes': {k: raw_digest(v.encode()) for k, v in sources.items()},
        'command': ['javac', *flags, '-d', 'classes', *sorted(sources)],
        'permissible_financial_domain_established': False, 'release_eligible': False}
    (output/'build-manifest.json').write_bytes(canonical(record))
    (output/(entry+'.java')).write_text(wrapper)
    (output/'bundle.json').write_bytes(canonical(bundle))
    return {'jar': str(target), 'manifest': record}


def run(build_record, requests, jdk):
    jdk, _ = toolchain(jdk)
    jar = Path(build_record['jar'])
    if raw_digest(jar.read_bytes()) != build_record['manifest']['jar_sha256']:
        raise LegalMathError('E_HASH_MISMATCH')
    p = subprocess.run([str(jdk/'bin/java'), '-jar', str(jar)],
        input=b'\n'.join(canonical(r) for r in requests)+b'\n', capture_output=True, check=True, timeout=60)
    rows = [loads(line) for line in p.stdout.splitlines()]
    if len(rows) != len(requests):
        raise LegalMathError('E_INTEGRITY')
    return rows
