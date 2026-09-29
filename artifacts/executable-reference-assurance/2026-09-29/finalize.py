"""Bind the repaired D2 delivery and separately identified D3/D4 continuations."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[3]; OUT = Path(__file__).parent
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT/'src')]
import run_executable_reference_master as runner
from legalmath.interpretation.assurance.grants import GrantedAllowance

def read(p): return json.loads(Path(p).read_bytes())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p): return {'path': str(Path(p).relative_to(ROOT)), 'sha256': sha(p)}
def save(p, value): Path(p).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
def retained_manifest(receipt):
    p = ROOT/receipt['path']
    if sha(p) != receipt['sha256']: raise RuntimeError('Changed manifest: '+str(p))
    value = read(p)
    if value['status'] != 'PASSED' or any(sha(ROOT/n) != h for n,h in value['outputs'].items()):
        raise RuntimeError('Incomplete or changed evidence: '+str(p))
    return value

state = runner.state(); phases = {}
for name in runner.PHASES:
    receipt = state['phases'][name][-1]
    if not runner.valid(receipt): raise RuntimeError('Stale or failed current D2 phase: '+name)
    phases[name] = retained_manifest(receipt)
work = (ROOT/state['phases']['verify'][-1]['path']).parent
snapshot = read(work/'snapshot.json'); frozen = Path(snapshot['path'])
if any(sha(frozen/p) != h for p,h in snapshot['inputs'].items()): raise RuntimeError('Changed tested snapshot')
with ZipFile(work/'tested-inputs.zip') as archive:
    if set(archive.namelist()) != set(snapshot['inputs']): raise RuntimeError('Archive denominator changed')
    if any(hashlib.sha256(archive.read(p)).hexdigest() != h for p,h in snapshot['inputs'].items()):
        raise RuntimeError('Archive content changed')
baseline = read((ROOT/state['phases']['D2'][-1]['path']).parent/'checks/inherited/inherited-state.json')
for name, expected in baseline['immutable'].items():
    if sha(ROOT/name) != expected: raise RuntimeError('Historical evidence changed: '+name)
for task in baseline['tasks']:
    for arm in task['arms'].values():
        if sha(ROOT/arm['path']) != arm['sha256']: raise RuntimeError('Original task allowance changed')
for name,row in baseline['native_issue_histories'].items():
    if sha(ROOT/name) != row['sha256']: raise RuntimeError('Original issue history changed')
grant = GrantedAllowance(ROOT/'artifacts/assurance-successor/2026-09-28/grant.json').verify()
if grant != baseline['grant']: raise RuntimeError('Grant changed')
d3root = ROOT/'artifacts/gregorian-profile-audit/2026-09-29'
d3ref = read(d3root/'state.json')['attempts'][-1]; d3 = retained_manifest(d3ref)
d4path = ROOT/'artifacts/authority-source-revision/2026-09-29/attempt-01/manifest.json'
d4ref = ref(d4path); d4 = retained_manifest(d4ref)
preservation = read(OUT/'manuscript-preservation.json')
if preservation['status'] != 'PRESERVED_WITH_EXPLAINED_REVISIONS' or preservation['snapshot_manifest_sha256'] != sha(work/'snapshot.json'):
    raise RuntimeError('Manuscript preservation not checked against this snapshot')
rendered = read(OUT/'rendered-review.json')
if rendered['status'] != 'INSPECTED_WITHOUT_LAYOUT_DEFECTS' or rendered['pdf_sha256'] != sha(work/'documents/monograph.pdf'):
    raise RuntimeError('Actual final PDF has not been inspected')
current = runner.material(ROOT)
differences = {p: {'tested': snapshot['inputs'].get(p), 'current': current.get(p)}
    for p in sorted(set(current) | set(snapshot['inputs']))
    if p.startswith(('src/', 'tests/', 'scripts/', 'docs/monograph/')) and current.get(p) != snapshot['inputs'].get(p)}
doc_changes = {p:v for p,v in differences.items() if p.startswith('docs/monograph/') and p.endswith(('.tex','.bib'))
    or p.startswith('scripts/') and any(s in p for s in ('monograph','reader_facing'))}
copies = []
if not doc_changes:
    for filename in ('monograph.pdf','technical-companion.pdf','process-guide.pdf'):
        target = ROOT/'docs/monograph'/filename; shutil.copy2(work/'documents'/filename, target); copies.append(ref(target))
    for filename, original in (('proposal.pdf','monograph.pdf'), ('monograph.pdf','monograph.pdf'),
                               ('technical-companion.pdf','technical-companion.pdf')):
        target = ROOT/'docs/proposal'/filename; shutil.copy2(work/'documents'/original, target); copies.append(ref(target))
continuation = {'at': runner.now(), 'D2': 'VERIFIED_OPTIONAL_PROTOCOL', 'D3': 'SCOPED_PROFILE_REPRODUCED',
    'D4': 'SOURCE_REVISION_PASSED; SIX_AUTHORITY_QUESTIONS_OPEN', 'D5': 'LIVE_AUTHORIZATION_EXHAUSTED',
    'D6': 'WHOLE_INVESTIGATION_OBSERVATION_BINDING_REQUIRED; NO_NEW_FUTURE_OBSERVATIONS',
    'next_phase': 'D4_UNRESOLVED_SOURCES_AND_ELIGIBLE_D5_CONTINUATION',
    'D3_receipt': d3ref, 'D4_receipt': d4ref,
    'plan': ref(ROOT/'docs/implementation/executable-reference-assurance/next-phase-plan.md'),
    'no_issue_or_allowance_reset': True, 'new_live_calls': 0, 'legal_correctness': 'NOT_ESTABLISHED'}
save(OUT/'delivery-next-phase-plan.json', continuation)
result = {'schema': 'legalmath.executable-reference-delivery.v1', 'status': 'D2_VERIFIED_D3_REPRODUCED_D4_PARTIAL',
    'at': runner.now(), 'current_phase_receipts': {p:state['phases'][p][-1] for p in runner.PHASES},
    'all_phase_attempts': state['phases'], 'regression': phases['verify']['regression'],
    'documents': phases['verify']['documents'], 'tested_input_count': len(snapshot['inputs']),
    'tested_archive': ref(work/'tested-inputs.zip'), 'snapshot_manifest': ref(work/'snapshot.json'),
    'snapshot': snapshot['path'], 'historical_replay': phases['D2']['result'], 'grant': grant,
    'D3': {'manifest': d3ref, 'snapshot': d3['snapshot'], 'result': ref(ROOT/d3['result'])},
    'D4': {'manifest': d4ref, 'snapshot': d4['snapshot'], 'result': ref(d4path.parent/'result.json')},
    'manuscript_preservation': ref(OUT/'manuscript-preservation.json'), 'rendered_review': ref(OUT/'rendered-review.json'),
    'published_document_copies': copies, 'manuscript_copy_blockers': doc_changes,
    'workspace_differences': differences, 'live_workspace_verified': not differences,
    'next_plan': ref(OUT/'delivery-next-phase-plan.json'), 'live_calls': 0, 'original_histories_unchanged': True,
    'live_protocol_comprehension': 'NOT_TESTED', 'historical_study_complete': False,
    'legal_correctness': 'NOT_ESTABLISHED', 'unknown_future_legal_generalization': 'NOT_ESTABLISHED',
    'release_eligible': False, 'human_quality_evidence': False,
    'finalizer': {'argv': [sys.executable,*sys.argv], 'sha256': sha(__file__)}}
save(OUT/'final-report.json', result)
print(json.dumps({k:result[k] for k in ('status','regression','documents','tested_input_count','live_workspace_verified')}, indent=2))
