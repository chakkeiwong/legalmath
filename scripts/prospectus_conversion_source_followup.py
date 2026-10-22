"""Reviewed continuation of frozen source-primary controls after a test repair."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
from scripts import prospectus_conversion_source_primary as controls
from legalmath.prospectus.execution_authority import Authority, REL, read, file_hash

PLAN = 'docs/plans/prospectus-conversion-source-followup-2026-10-18.md'
REVIEW = ROOT / REL / 'reviews/conversion-source-followup-252'
HERE = ROOT / REL / 'attempts/entitlement/attempt-008'
PRIOR = ROOT / REL / 'attempts/entitlement/attempt-007'
ORIGINAL_REVIEW = controls.REVIEW


def methods_unchanged():
    frozen = read(REVIEW / 'freeze.json')
    current = {str(p.relative_to(ROOT)) for p in (ROOT / 'src/legalmath').rglob('*')
               if p.is_file() and '__pycache__' not in p.parts}
    controls.require(current == set(frozen['production']), 'Production file set changed')
    for name, expected in {**frozen['methods'], **frozen['retained']}.items():
        controls.require(file_hash(ROOT / name) == expected, 'Frozen evidence/method changed: ' + name)


def measured_seconds():
    return (read(ORIGINAL_REVIEW / 'preparation-result.json')['seconds']
            + sum(read(p)['seconds'] for folder in (PRIOR, HERE)
                  for p in (folder / 'stages').glob('*/result.json')))


def storage():
    paths = [ORIGINAL_REVIEW, REVIEW, PRIOR, HERE, ROOT / PLAN,
             ROOT / 'docs/plans/prospectus-conversion-source-primary-2026-10-18.md',
             ROOT / 'scripts/prospectus_conversion_source_primary.py', Path(__file__),
             ROOT / 'tests/prospectus_successor/test_conversion_source_primary.py',
             ROOT / 'tests/prospectus/test_closure_mechanisms.py']
    for revision, name in ((251, 'conversion-source-primary'), (252, 'conversion-source-followup')):
        paths.extend([ROOT / REL / f'proposals/{name}-{revision}.json',
                      ROOT / REL / f'proposals/{name}-{revision}-review.json',
                      ROOT / REL / f'revisions/{revision:04d}.json',
                      ROOT / REL / f'closure-routes-2026-10-18-{name}-{revision}.json'])
    files = set()
    for path in paths:
        if path.is_dir():
            files.update(p for p in path.rglob('*') if p.is_file())
        elif path.exists():
            files.add(path)
    return sum(p.stat().st_size for p in files)


def authenticate():
    auth = Authority(ROOT)
    program, tasks, _ = auth.spec()
    admission = read(HERE / 'admission.json')
    controls.require(program['revision'] == 252 and admission['task'] == 'entitlement', 'Wrong admission')
    controls.require(admission['binding'] == auth.binding(tasks['entitlement']), 'Admission binding changed')
    event = next(e for e in reversed(auth.events()) if e.get('task') == 'entitlement')
    controls.require(event['kind'] == 'ADMIT' and event['attempt'] == str(HERE.relative_to(ROOT)),
                     'No active source follow-up admission')
    methods_unchanged()
    for name, expected in read(ORIGINAL_REVIEW / 'source-bindings.json').items():
        controls.require(file_hash(ROOT / name) == expected, 'Original source changed: ' + name)
    controls.require(measured_seconds() < 480 and storage() + 1024**2 < 80 * 1024**2,
                     'Original cumulative resource ceiling')
    return admission


# Preserve all original semantic controls and stage dependencies. The original
# main reports __file__; bind it to the wrapper actually invoked by the caller.
controls.PLAN = PLAN
controls.HERE = HERE
controls.__file__ = __file__
controls.methods_unchanged = methods_unchanged
controls.measured_seconds = measured_seconds
controls.storage = storage
controls.authenticate = authenticate

if __name__ == '__main__':
    controls.main()
