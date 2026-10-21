"""Report failed return values and nested phase refusals without authorizing work."""
from pathlib import Path
import json
from ..integration_contract import evidence_file


def diagnose(root, directory, question, *, result=None, exception=None):
    root, directory = Path(root), Path(directory)
    result_path = directory/'result.json'
    if result is None and result_path.exists():
        result = json.loads(result_path.read_text())
    answer = (result or {}).get('answers', {}).get(question, {})
    failures = []
    if exception is not None:
        failures.append(dict(origin='exception', error=getattr(exception, 'code', type(exception).__name__),
            reason=str(getattr(exception, 'details', None) or exception)))
    if answer.get('status') == 'FAILED':
        failures.append(dict(origin='returned_answer', error=answer.get('error', 'UNKNOWN'),
            reason=answer.get('reason', 'Preparation returned FAILED')))
    phases = []
    paths = list((directory/'phases').glob('*/outcome.json'))
    if (directory/'capacity-phases').exists():
        # A failed leaf may have been successfully decomposed. Diagnose the
        # complete logical result; leaf failures stay retained as evidence.
        paths = [p for p in paths if not p.parent.name.startswith('capacity-')]
        paths += list((directory/'capacity-phases').glob('*/outcome.json'))
    for path in sorted(paths):
        value = json.loads(path.read_text())
        if value.get('execution_complete') is True:
            continue
        refusal = value.get('resource_refusal')
        failed = [dict(key=row['key'], error=row['result'].get('error', 'UNKNOWN'),
            reason=row['result'].get('reason', 'Phase call failed'))
            for row in value.get('results', []) if row['result'].get('status') != 'VALIDATED']
        phases.append(dict(phase=value.get('phase', path.parent.name),
            evidence=evidence_file(path, root), resource_refusal=refusal, failed_calls=failed))
    optional_names = {'call-candidates-' + question, 'call-criticism-' + question}
    optional = [p for p in phases if p['phase'] in optional_names
        and all(r.get('error') not in ('E_AUTHORITY', 'E_INTEGRITY') for r in p['failed_calls'])
        and (p.get('resource_refusal') or {}).get('error') not in ('E_AUTHORITY', 'E_INTEGRITY')]
    required = [p for p in phases if p not in optional]
    prepared = answer.get('status') == 'PREPARED' and not failures and not required
    incomplete = not prepared
    if incomplete and not failures and not phases:
        failures.append(dict(origin='missing_preparation', error='E_DEPENDENCY',
            reason='No PREPARED result was retained'))
    return dict(profile='preparation-diagnosis.v1', question=question, prepared=prepared,
        failures=failures, incomplete_phases=phases, required_incomplete_phases=required,
        optional_incomplete_phases=optional, provider_calls_authorized=0,
        result=evidence_file(result_path, root) if result_path.exists() else None,
        legal_acceptance=False)
