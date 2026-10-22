"""Retain the reproduced attempt-084 projection failure without rerunning it."""
from datetime import datetime, timezone
import time
import xml.etree.ElementTree as ET
from scripts import prospectus_reference_addresses as run

started = time.monotonic()
here = run.HERE
assert not (here / 'outputs.json').exists()
failure = run.read(here / 'stages/tests/failure.json')
suites = list(ET.parse(here / 'pytest.xml').getroot().iter('testsuite'))
counts = {k: sum(int(s.attrib.get(k, 0)) for s in suites) for k in ('tests', 'failures', 'errors', 'skipped')}
assert counts == {'tests': 112, 'failures': 9, 'errors': 0, 'skipped': 0}
products, old = run.baseline()
supplied = [p for p in old['definition_sources']['source_pieces']
            if p['kind'] == 'SUPPLIED_OR_TRANSFORMED']
assert len(supplied) == 18
run.save(here / 'projection-diagnostic.json', {'status': 'REPRODUCED',
    'failure': failure, 'counts': counts, 'supplied_piece_count': len(supplied),
    'supplied_pieces': supplied,
    'root_cause': 'The citation-only projector rejects supplied/transformed text inside whole paragraph bodies',
    'classification': 'IMPLEMENTATION_ERROR',
    'repair': 'Preserve distinct exact-copy, generated-separator and transformation provenance in body projections',
    'expectations_unchanged': True, 'full_consumer_executed': False, 'package_executed': False})
run.save(here / 'stages/diagnostic/result.json', {'status': 'PASS', 'wall_seconds': time.monotonic() - started,
    'command': ['.venv/bin/python', '-m', 'scripts.prospectus_reference_addresses_failure'],
    'finished_at': datetime.now(timezone.utc).isoformat()})
result = {'status': 'FAIL', 'task': 'basf-references', 'original_task_complete': False,
    'result_kind': 'BODY_PROJECTION_IMPLEMENTATION_FAILURE', 'tests': counts, 'resources': run.costs(),
    'next_action': 'Reviewed repair of transformed paragraph-body provenance with unchanged source destination expectations'}
run.save(here / 'result.json', result)
run.save(here / 'run-manifest.json', {'git_commit': run.read(here / 'admission.json')['git_commit'],
    'commands': [run.read(here / 'stages' / name / 'started.json')['command'] for name in ('install', 'tests')],
    'environment': str(run.ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU; GPU intentionally hidden',
    'seeds': 'N/A deterministic', 'data_version': run.sha(run.PRODUCTS), 'wall_time': run.costs(),
    'plan': run.PLAN, 'result': run.rel(here / 'result.json')})
(here / 'RESULT.md').write_text('''# Paragraph projection rejected before full execution

103 tests passed and nine failed because the citation-only source projector
cannot represent supplied final-term substitutions within complete paragraph
bodies. Eighteen such source pieces already exist in the frozen baseline. Their
presence is valid retained construction evidence, not a PDF extraction failure.
No complete consumer or package was run.

| Decision | Primary criterion | Veto | Uncertainty | Next action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Reject attempt 084 | Source test failed | Unsupported body projection | Downstream address comparison not reached | Repair the projection with retained transformation provenance | Package defect or failure of structural reference resolution |

All original expected destinations and tests remain unchanged. A reviewed repair
must retain exact source copies separately from transformations; it must not
invent a raw quotation for transformed text or relax citation projection.
''')
run.save(here / 'outputs.json', {str(p.relative_to(here)): run.sha(p) for p in here.rglob('*') if p.is_file()})
print('Sealed FAIL attempt084: 103 passed / 9 failed; full consumers not run')
