"""Archive the corrected candidate without changing bound live source files."""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import difflib
import json
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path('/home/chakwong/python/legalmath')
OUT = Path(__file__).resolve().parent
CANDIDATE = Path('/tmp/legalmath-baselines-corpus-hardened')

def read(p): return json.loads(p.read_text())
def digest(p): return sha256(p.read_bytes()).hexdigest()
def ref(p): return {'path':str(p.relative_to(ROOT)),'sha256':digest(p)}
def save(p, data):
    if p.exists(): assert p.read_bytes() == data, str(p)
    else:
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(data)
def save_json(p, value):
    save(p,(json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode())

previous = read(OUT/'candidate-manifest.json')
paths = sorted({r['path'] for r in previous['files']} | {'tests/assurance/test_corpus_passage_attribution.py'})
files, patches = [], []
for name in paths:
    live, source, archived = ROOT/name, CANDIDATE/name, OUT/'candidate-hardened'/name
    original = live.read_bytes() if live.exists() else b''
    data = source.read_bytes()
    save(archived,data)
    files.append({'path':name,'candidate_sha256':digest(source),
        'live_sha256':digest(live) if live.exists() else None,'artifact':str(archived.relative_to(ROOT))})
    patches.extend(difflib.unified_diff(original.decode().splitlines(keepends=True),data.decode().splitlines(keepends=True),
        fromfile='a/'+name if live.exists() else '/dev/null',tofile='b/'+name))
save(OUT/'candidate-hardened.patch',''.join(patches).encode())
subprocess.run(['git','apply','--check',str(OUT/'candidate-hardened.patch')],cwd=ROOT,check=True)
protected = read(ROOT/'artifacts/legal-mission-control/2026-10-25/offline-unblock/protected-before.json')['files']
assert len(protected) == 364
for name, expected in protected.items(): assert digest(ROOT/name) == expected, name
candidate = {'profile':'baseline-corpus-hardened-candidate.v1','deployment':'NOT_DEPLOYED',
    'files':files,'patch':ref(OUT/'candidate-hardened.patch'),'supersedes':ref(OUT/'candidate-manifest.json'),
    'review':ref(OUT/'attribution-review-addendum.md'),'protected_live_files_verified':len(protected),
    'protected_mismatches':[],'provider_calls':0,'legal_acceptance':False}
save_json(OUT/'candidate-hardened-manifest.json',candidate)
tests = [s.attrib for s in ET.parse(OUT/'tests-attribution-qualified.xml').iter('testsuite')]
assert sum(int(s['tests']) for s in tests) == 130
assert all(int(s['failures']) == int(s['errors']) == 0 for s in tests)
proof = read(OUT/'corpus-attribution-hardened.json')
assert proof['total_actual_passages'] == 965 and proof['unrelated_passage']['status'] == 'REJECTED'
assert proof['actual_handler']['_node_status'] == 'BLOCKED'
manifest_path = OUT/'run-manifest-hardened.json'
if not manifest_path.exists():
    manifest = {'profile':'baseline-corpus-hardened-run-manifest.v1',
        'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
        'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'baseline':'Dirty protected worktree plus immutable first candidate; file hashes identify exact implementation.',
        'environment':str(ROOT/'.venv-context/bin/python'),
        'cpu_gpu':'CPU-only exact-text and schema validation; no GPU framework or probe used.',
        'seeds':'N/A: deterministic retained-input checks; no provider invocation.',
        'plan':ref(ROOT/'docs/plans/legal-failed-baselines-corpus-repair-2026-10-26.md'),
        'reviewed_addendum':ref(OUT/'attribution-review-addendum.md'),
        'result':ref(OUT/'final-result.md'),'candidate':ref(OUT/'candidate-hardened-manifest.json'),
        'predecessor':ref(OUT/'run-manifest.json'),
        'commands':[
            '.venv/bin/python artifacts/legal-mission-control/2026-10-26/baselines-corpus-repair/audit_p14_targets.py',
            '.venv-context/bin/python artifacts/legal-mission-control/2026-10-26/baselines-corpus-repair/run_hardened_tests.py',
            '.venv-context/bin/python artifacts/legal-mission-control/2026-10-26/baselines-corpus-repair/check_hardened_corpus.py',
            '.venv/bin/python artifacts/legal-mission-control/2026-10-26/baselines-corpus-repair/archive_hardened.py',
            'git apply --check artifacts/legal-mission-control/2026-10-26/baselines-corpus-repair/candidate-hardened.patch'],
        'tests':tests,'wall_time':{'suite_seconds':sum(float(s['time']) for s in tests),
            'whole_session_seconds':None,'reason':'Not instrumented; no speed claim.'},
        'actual_passages_verified':965,'unqualified_legacy_rows_rejected':len(proof['unqualified_legacy_rows_rejected']),
        'prior_failures':'Initial candidate accepted an unrelated passage. Two test collections had isolated import setup errors. First actual corpus check correctly rejected an older unqualified paragraph; qualified complete-component support was then added.',
        'receipts':[ref(OUT/n) for n in ('corpus-unrelated-passage-probe.json','corpus-attribution-hardened.json',
            'p14-target-location-audit.json','tests-attribution-hardened.xml','tests-attribution-hardened-final.xml',
            'tests-attribution-before-component.xml','tests-attribution-qualified.xml')],
        'scripts':[ref(OUT/n) for n in ('audit_p14_targets.py','run_hardened_tests.py','check_hardened_corpus.py','archive_hardened.py')],
        'protected_live_files_verified':364,'protected_changes':[],
        'provider_calls':0,'live_attempts':0,'deployment':'NOT_DEPLOYED','legal_acceptance':False,
        'continuation':'Active dispatcher unchanged. Safe checkpoint/rebind, finite continuation and substantive reviews remain prerequisites.'}
    save_json(manifest_path,manifest)
latest = {'profile':'baseline-corpus-current-local-candidate.v1','candidate':ref(OUT/'candidate-hardened-manifest.json'),
    'manifest':ref(manifest_path),'result':ref(OUT/'final-result.md'),'deployment':'NOT_DEPLOYED'}
save_json(OUT/'latest-candidate.json',latest)
print(json.dumps({'candidate_files':len(files),'patch_bytes':(OUT/'candidate-hardened.patch').stat().st_size,
    'tests':130,'protected_files':364,'manifest':ref(manifest_path),'deployment':'NOT_DEPLOYED'}))
