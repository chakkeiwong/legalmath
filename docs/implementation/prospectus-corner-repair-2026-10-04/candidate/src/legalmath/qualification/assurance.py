"""Execute shared-model assurance and issue mechanically derived qualifications."""
from pathlib import Path
import subprocess

from ..canonical import canonical, digest, loads, raw_digest
from ..errors import LegalMathError
from ..translation import pipeline, verification
from ..translation.model import validate, blockers, walk
from ..translation.policy import prepare
from ..translation.resources import preflight
from . import POLICY, proof, oracle, registry


def method_manifest():
    package = Path(__file__).resolve().parents[1]
    files = []
    for directory in ('qualification', 'translation', 'catala', 'ir', 'java'):
        files.extend(p for p in (package/directory).rglob('*') if p.is_file() and p.suffix in ('.py', '.java', '.lean', '.json'))
    files.extend(package/p for p in ('canonical.py', 'errors.py', 'domain.py'))
    files.extend(package/p for p in ('interpretation/contracts.py','interpretation/search/models.py','sources/anchors.py'))
    files.extend((package/'schemas').glob('*.json'))
    return {str(p.relative_to(package)): raw_digest(p.read_bytes()) for p in sorted(files)}


def identity(model):
    m, _ = validate(model)
    return {'model_hash': digest(m), 'source_hash': digest(m['review']['packet']),
            'method_hash': digest(method_manifest()), 'policy': POLICY}


def write(path, value):
    Path(path).write_bytes(canonical(value))


def check_cases(cases):
    if not isinstance(cases, list) or len(cases) > 256:
        raise LegalMathError('E_RESOURCE_LIMIT')
    ids = set()
    for c in cases:
        # No label, expected answer, grading, reviewer, certificate or approval input.
        if (not isinstance(c, dict) or set(c) != {'id', 'snapshot', 'valid_at', 'known_at'}
                or not isinstance(c['id'], str) or not c['id'] or c['id'] in ids):
            raise LegalMathError('E_SCHEMA', details='Cases contain factual inputs and times only; quality judgments are forbidden')
        ids.add(c['id'])


def limitations(model):
    calls = sorted({n['name'] for r in model['rules'] for field in ('scope', 'body')
                    for n, _ in walk(r[field]) if n['op'] == 'library'} |
                   {n['name'] for h in model.get('helpers', []) for n, _ in walk(h['body']) if n['op'] == 'library'})
    return {'resource_preflight': preflight(model), 'libraries_used': calls, 'library_registry': registry.manifest(),
            'library_policy': 'Closed typed vocabulary; arbitrary imports are unsupported. Each extension requires pinned dependency, independent semantics and challenge checks.',
            'recursion': 'Recursive types are rejected by the pinned Catala compiler; recursive helpers and rule cycles are unsupported.',
            'trace': {'observed': ['Emitted Java branch/option/variant choices', 'Scope assignments'],
                      'unobserved': ['Optimized-away source choices', 'External library internals'],
                      'whole_trace_correctness': 'NOT_PROVED'},
            'performance': 'No backend ranking; this report measures correctness evidence only.',
            'source_quality': 'Source anchors and model criticism do not establish legal meaning or completeness.',
            'future_publications': 'NOT_ESTABLISHED', 'human_quality_evidence': 'FORBIDDEN'}


def checked_proof(model, out):
    try:
        return proof.produce(model, out)
    except LegalMathError as exc:
        if exc.code != 'E_UNSUPPORTED_PROFILE':
            raise
        return {'status': 'UNSUPPORTED', 'reason': exc.details, 'legal_correctness': 'NOT_ESTABLISHED'}


def check_execution(model, directory, case, result, jdk, compiler):
    boundary = prepare(model, case['snapshot'], case['valid_at'], case['known_at'])
    reading = model['review']['reading']
    reference = None; reason = 'No retained formal proposal'
    if reading is not None and not boundary['reason']:
        try:
            reference = oracle.evaluate(reading['formalization'], case['snapshot'])
        except LegalMathError as exc:
            if exc.code != 'E_UNSUPPORTED_PROFILE': raise
            reason = exc.details
    elif boundary['reason']:
        reason = 'Evidence/time boundary: ' + boundary['reason']
    expected = reference if reference is not None else {
        k: {'status': r['status'], 'type': r['type'], 'value': r['value']}
        for k, r in result['results'].items()}
    scalar = result['results'] and next(iter(result['results'].values())).get('execution_identity_map') is not None
    if scalar and reference is not None:
        # The scalar projection carries error details in the nested execution;
        # its top-level reason is always None. Status/value remain comparable.
        expected={k:{a:b for a,b in r.items() if a!='reason'} for k,r in reference.items()}
    checks = verification.verify_executions(directory, case['snapshot'], result, expected, jdk, compiler=compiler)
    return {'runtime_checks': checks,
            'independent_formal_evaluation': 'MATCH' if reference is not None else 'UNSUPPORTED',
            'qualification': None if reference is not None else reason,
            'reference': reference}


def conclusion(proposition, targets, cases):
    rows = [c for t in targets.values() for c in t.get('cases', [])]
    failed = any(t['status'] == 'FAILED' for t in targets.values())
    return {'status': 'FAILED' if failed else 'QUALIFIED',
            'formal_lowering': proposition['status'],
            'selected_cases': len(cases), 'selected_targets': len(targets),
            'executed_target_cases': len(rows),
            'independent_formal_matches': sum(r['checks']['independent_formal_evaluation'] == 'MATCH' for r in rows),
            'legal_correctness': 'NOT_ESTABLISHED', 'unknown_future_legal_generalization': 'NOT_ESTABLISHED',
            'human_quality_evidence': False,
            'statement': 'Checked formal and executable properties apply only to their recorded premises and domains. Legal source meaning, completeness and unknown future legal situations remain qualified.'}


def run(model, cases, directory, jdk, *, toolchain=None):
    m, _ = validate(model); check_cases(cases)
    out = Path(directory).resolve()
    out.mkdir(parents=True, exist_ok=False)
    bound = identity(m); methods = method_manifest()
    write(out/'model.json', m); write(out/'cases.json', cases); write(out/'method.json', methods)
    proposition = checked_proof(m, out/'proof')
    targets = {}
    for target in ('ruleir', 'catala'):
        # Both targets are always retained, including unsupported rich RuleIR.
        try:
            translation = pipeline.translate(m, target)
            if translation['status'] != 'TRANSLATED':
                targets[target] = {'status': translation['status'], 'translation': translation, 'cases': []}
                continue
            if target == 'catala' and toolchain is None:
                targets[target] = {'status': 'UNAVAILABLE', 'reason': 'Explicit pinned Catala toolchain required', 'cases': []}
                continue
            build = pipeline.build(m, target, out/target, jdk, catala_toolchain=toolchain)
            target_rows = []
            targets[target] = {'status': 'CHECKED', 'build_hash': digest(build), 'route': translation['output']['route'], 'cases': target_rows}
            for case in cases:
                result = pipeline.execute_all(out/target, case['snapshot'], case['valid_at'], case['known_at'], jdk,
                                              expected_hash=digest(build))
                checks = check_execution(m, out/target, case, result, jdk, toolchain['compiler'] if toolchain else None)
                target_rows.append({'id': case['id'], 'result': result, 'checks': checks})
        except (LegalMathError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
            prior = targets.get(target, {})
            targets[target] = {**prior, 'status': 'FAILED', 'error': getattr(exc, 'code', type(exc).__name__),
                               'detail': str(getattr(exc, 'details', exc)), 'cases': prior.get('cases', [])}
    if bound != identity(m):
        raise LegalMathError('E_STALE_REVIEW', details='Implementation changed during assurance')
    report = {'policy': POLICY, 'identity': bound, 'cases_hash': digest(cases),
              'proof': proposition, 'targets': targets, 'unresolved': blockers(m),
              'limits': limitations(m), 'summary': conclusion(proposition, targets, cases)}
    report['report_hash'] = digest(report); write(out/'qualification.json', report)
    return report


def verify(directory, current_model, jdk, *, compiler=None):
    """Require the current source/method identity, then rerun proof and executions."""
    out = Path(directory); m, _ = validate(current_model)
    report = loads((out/'qualification.json').read_bytes()); cases = loads((out/'cases.json').read_bytes())
    check_cases(cases)
    expected_keys = {'policy', 'identity', 'cases_hash', 'proof', 'targets', 'unresolved', 'limits', 'summary', 'report_hash'}
    if (set(report) != expected_keys or report['policy'] != POLICY or
            report['report_hash'] != digest({k: v for k, v in report.items() if k != 'report_hash'})):
        raise LegalMathError('E_INTEGRITY')
    if report['identity'] != identity(m):
        raise LegalMathError('E_STALE_REVIEW', details='Source, model, method or policy revision changed')
    if (loads((out/'model.json').read_bytes()) != m or report['cases_hash'] != digest(cases)
            or loads((out/'method.json').read_bytes()) != method_manifest()):
        raise LegalMathError('E_INTEGRITY')
    import tempfile
    with tempfile.TemporaryDirectory(prefix='legalmath-proof-recheck-') as temp:
        if checked_proof(m, Path(temp)) != report['proof']:
            raise LegalMathError('E_INTEGRITY', details='Changed proof proposition or evidence')
    if set(report['targets']) != {'ruleir', 'catala'}:
        raise LegalMathError('E_INTEGRITY', details='Missing target')
    for name, target in report['targets'].items():
        translation = pipeline.translate(m, name)
        if target['status'] in ('UNSUPPORTED', 'UNRESOLVED'):
            if target != {'status': translation['status'], 'translation': translation, 'cases': []}:
                raise LegalMathError('E_INTEGRITY')
            continue
        if target['status'] != 'CHECKED':
            raise LegalMathError('E_INTEGRITY', details='Incomplete/failed run is not verified evidence')
        _, _, build = pipeline.verify_build(out/name, expected_hash=target['build_hash'])
        if target['route'] != translation['output']['route'] or len(target['cases']) != len(cases):
            raise LegalMathError('E_INTEGRITY')
        for case, record in zip(cases, target['cases']):
            if record['id'] != case['id']:
                raise LegalMathError('E_INTEGRITY')
            checks = check_execution(m, out/name, case, record['result'], jdk, compiler)
            if checks != record['checks']:
                raise LegalMathError('E_INTEGRITY', details='Changed independent evaluation or runtime evidence')
    if (report['unresolved'] != blockers(m) or report['limits'] != limitations(m)
            or report['summary'] != conclusion(report['proof'], report['targets'], cases)):
        raise LegalMathError('E_INTEGRITY', details='Unsupported qualification or correctness claim')
    return report
