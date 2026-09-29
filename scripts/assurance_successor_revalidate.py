"""Keep historical receipts separate from executed current-code conformance."""
from pathlib import Path

from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.complete_investigation import verify
from legalmath.interpretation.assurance.integration_contract import read_evidence
from legalmath.interpretation.assurance.integration_execution import implementation_files, run_replay
from legalmath.interpretation.search.formal import project
from assurance_successor_scheduling import historical_replay


def projected_evidence(root, dossier):
    """Compare the actual unchanged programs, cases and executed answers."""
    rows = {}
    for method in dossier['methods']:
        mid = method['method_id']
        if mid not in ('method.types', 'method.java', 'method.catala'):
            continue
        payload = read_evidence(method['evidence'], root)['payload']
        values = []
        for row in payload['rows']:
            value = {key: row[key] for key in ('candidate_id', 'status')}
            if 'error' in row:
                value['error'] = row['error']
            if 'bundle' in row:
                value['bundle_hash'] = digest(read_evidence(row['bundle'], root))
            if 'cases' in row:
                value['cases'] = read_evidence(row['cases'], root)
                results = read_evidence(row['results'], root)
                value['results'] = [{'id': r['id'], 'python': project(r['python']),
                                     'java': project(r['java'])} for r in results]
            values.append(value)
        rows[mid] = {'status': method['status'], 'rows': values}
    if set(rows) != {'method.types', 'method.java', 'method.catala'}:
        raise LegalMathError('E_INTEGRITY', details='Missing retained runtime or type evidence')
    return rows


def verify_retained(root, dossier, archive, output, jdk, *, catala=None):
    root = Path(root).resolve()
    if not dossier.get('replay'):
        return {'status': 'CURRENT_FILES_VERIFIED', 'verification': verify(root, dossier),
                'new_runtime_execution': False}
    old = read_evidence(dossier['replay']['dossier'], root)
    prior = {r['path']: r['sha256'] for r in old['upstream_inputs']
             if r['path'].startswith('src/legalmath/')}
    current = {r['path']: r['sha256'] for r in implementation_files(root)}
    if prior == current:
        return {'status': 'CURRENT_FILES_VERIFIED', 'verification': verify(root, dossier),
                'new_runtime_execution': False}
    historical = historical_replay(root, dossier, archive)
    # run_replay executes the selected backends; it is not just a new manifest.
    fresh = run_replay(root, root/old['input_manifest']['path'], output, jdk, catala=catala)
    new = read_evidence(fresh['dossier'], root)
    if old['target'] != new['target'] or old['target_hash'] != new['target_hash']:
        raise LegalMathError('E_INTEGRITY', details='Current replay changed the retained target')
    previous = projected_evidence(root, old)
    rebuilt = projected_evidence(root, new)
    if previous != rebuilt:
        raise LegalMathError('E_INTEGRITY', details='Current programs, cases or answers differ from historical replay')
    return {'status': 'HISTORICAL_FILES_AND_CURRENT_RUNTIME_VERIFIED',
            'historical': historical, 'current_replay': fresh,
            'changed_sources': sorted(n for n in prior.keys() & current.keys() if prior[n] != current[n]),
            'added_sources': sorted(current.keys() - prior.keys()),
            'removed_sources': sorted(prior.keys() - current.keys()),
            'replayed_projection_sha256': digest(rebuilt),
            'runtime_cases': {m: sum(len(r.get('cases', [])) for r in v['rows'])
                              for m, v in rebuilt.items() if m != 'method.types'},
            'new_runtime_execution': True, 'original_dossier_modified': False,
            'scope': 'Unchanged source/question/proposals and declared finite cases; not source-meaning proof',
            'release_eligible': False}
