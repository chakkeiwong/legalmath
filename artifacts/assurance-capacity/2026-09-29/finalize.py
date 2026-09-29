"""Deliver checked capacity results without modifying historical phase evidence."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT/'src')]
import run_assurance_capacity as runner
from legalmath.interpretation.assurance.grants import GrantedAllowance

OUT = ROOT/'artifacts/assurance-capacity/2026-09-29'
start = time.monotonic()


def read(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p): return {'path': str(Path(p).relative_to(ROOT)), 'sha256': sha(p)}
def save(p, value): Path(p).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')


state = read(OUT/'state.json'); phases = {}
for name in ('D0', 'D1', 'verify'):
    receipt = state['phases'][name][-1]
    if not runner.valid(receipt): raise RuntimeError('Phase is not current and passing: '+name)
    phases[name] = {**receipt, 'manifest': read(ROOT/receipt['path'])}
verification = phases['verify']['manifest']; work = (ROOT/phases['verify']['path']).parent
snapshot = read(work/'snapshot.json')
if any(sha(Path(snapshot['path'])/p) != h for p, h in snapshot['inputs'].items()):
    raise RuntimeError('Tested snapshot has changed')
baseline = read((ROOT/phases['D0']['path']).parent/'checks/inherited-state.json')
for name, expected in baseline['immutable'].items():
    if sha(ROOT/name) != expected: raise RuntimeError('Inherited evidence changed: '+name)
for task in baseline['tasks']:
    for arm in task['arms'].values():
        if sha(ROOT/arm['path']) != arm['sha256']: raise RuntimeError('Local allowance changed')
for name, row in baseline['native_issue_histories'].items():
    if sha(ROOT/name) != row['sha256']: raise RuntimeError('Original issue history changed')
grant = GrantedAllowance(ROOT/'artifacts/assurance-successor/2026-09-28/grant.json').verify()
if grant != baseline['grant']: raise RuntimeError('Original global grant changed')
preservation = read(OUT/'manuscript-preservation.json')
if preservation['status'] not in ('PRESERVED', 'PRESERVED_WITH_RECORDED_CONCURRENT_BASELINE'):
    raise RuntimeError('Manuscript preservation unresolved')
if preservation['status'] == 'PRESERVED_WITH_RECORDED_CONCURRENT_BASELINE' and not preservation[
        'concurrent_process_map']['all_baseline_lines_preserved_in_order']:
    raise RuntimeError('Concurrent manuscript baseline not preserved')
if 'concurrent_process_map' in preservation:
    before = preservation['concurrent_process_map']
    with ZipFile(ROOT/before['baseline_archive']) as archive:
        data = archive.read(before['baseline_file'])
    if hashlib.sha256(data).hexdigest() != before['baseline_sha256']:
        raise RuntimeError('Concurrent map baseline changed')
    current_lines = iter((ROOT/before['baseline_file']).read_text().splitlines(keepends=True))
    if not all(any(line == candidate for candidate in current_lines) for line in data.decode().splitlines(keepends=True)):
        raise RuntimeError('Capacity edit removed a prior map line')
rendered = read(OUT/'rendered-review.json')
if rendered['status'] != 'INSPECTED_WITHOUT_LAYOUT_DEFECTS': raise RuntimeError('Rendered document review incomplete')
if rendered['pdf_sha256'] != sha(work/'documents/monograph.pdf'): raise RuntimeError('Wrong document reviewed')
current = runner.material(ROOT)
differences = {p: {'tested': snapshot['inputs'].get(p), 'current': current.get(p)}
    for p in sorted(set(current) | set(snapshot['inputs']))
    if p in current or p.startswith(('src/', 'tests/', 'scripts/', 'docs/monograph/'))
    if current.get(p) != snapshot['inputs'].get(p)}
manuscript_differences = {p: v for p, v in differences.items()
    if p.startswith('docs/monograph/') and p.endswith(('.tex', '.bib')) or
       p.startswith('scripts/') and any(s in p for s in ('monograph', 'reader_facing'))}
copied = []
if not manuscript_differences:
    for filename in ('monograph.pdf', 'technical-companion.pdf', 'process-guide.pdf'):
        source = work/'documents'/filename; target = ROOT/'docs/monograph'/filename
        shutil.copy2(source, target); copied.append(ref(target))
    for filename, source in [('proposal.pdf', 'monograph.pdf'), ('monograph.pdf', 'monograph.pdf'),
                             ('technical-companion.pdf', 'technical-companion.pdf')]:
        target = ROOT/'docs/proposal'/filename
        shutil.copy2(work/'documents'/source, target); copied.append(ref(target))
capacity = phases['D1']['manifest']['result']
report = {'schema': 'legalmath.assurance-capacity-assessment.v1',
    'status': 'D0_D1_VERIFIED_LIVE_INTERPRETATION_INCOMPLETE', 'at': runner.now(),
    'phase_receipts': {p: {k: v for k, v in r.items() if k != 'manifest'} for p, r in phases.items()},
    'regression': verification['regression'], 'documents': verification['documents'],
    'tested_input_count': len(snapshot['inputs']), 'tested_archive': ref(work/'tested-inputs.zip'),
    'snapshot': snapshot['path'], 'snapshot_manifest': ref(work/'snapshot.json'),
    'capacity': capacity, 'inherited': phases['D0']['manifest']['result'],
    'grant': grant, 'original_issue_histories_unchanged': True,
    'workspace_differences': differences, 'live_workspace_verified': not differences,
    'published_document_copies': copied, 'manuscript_copy_blockers': manuscript_differences,
    'manuscript_preservation': ref(OUT/'manuscript-preservation.json'),
    'rendered_review': ref(OUT/'rendered-review.json'),
    'next_plan': ref(ROOT/'docs/implementation/assurance-capacity/next-phase-plan.md'),
    'next_phase': 'D2', 'live_calls': 0, 'historical_study_complete': False,
    'model_comprehension_of_encoding': 'NOT_TESTED', 'legal_correctness': 'NOT_ESTABLISHED',
    'unknown_future_legal_generalization': 'NOT_ESTABLISHED', 'release_eligible': False,
    'human_quality_evidence': False, 'cpu_only': True,
    'finalizer': {'argv': [sys.executable, *sys.argv], 'sha256': sha(__file__),
                  'elapsed_seconds': round(time.monotonic()-start, 3)}}
save(OUT/'final-report.json', report)
print(json.dumps({k: report[k] for k in ('status', 'regression', 'tested_input_count', 'documents', 'next_phase')}, indent=2))
