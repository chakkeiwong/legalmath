"""Re-evaluate the four frozen consumers under the changed product method."""
import argparse
import shutil
from pathlib import Path
from scripts import prospectus_report_scope as cohort
from scripts.prospectus_geometry_program import BASE, read, seal, verify, write


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    old = BASE / 'source-report-scope-2026-10-12'
    verify(old)
    args.output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(old / 'freeze-002', args.output / 'freeze-002')
    cohort.HERE = args.output
    results = {}
    for name in cohort.CASES:
        if cohort.consume_case(name, 'freeze-002', 'attempt-001'):
            raise ValueError('Matched consumer failed: ' + name)
        prior = old / 'cases' / name / 'attempt-001'
        current = args.output / 'cases' / name / 'attempt-001'
        checks = {file: read(prior / file) == read(current / file)
                  for file in ('answer.json', 'dependencies.json', 'selected-reading.json')}
        results[name] = checks
        if not all(checks.values()):
            raise ValueError('Matched answer, source map or dependencies changed: ' + name)
    write(args.output / 'result.json', {'status':'PASS','cases':results,
        'scope':'Exact matched final answers, readings and dependencies; exposed development cases'})
    seal(args.output)


if __name__ == '__main__':
    main()
