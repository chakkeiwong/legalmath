"""Validate reviewed attributions against retained evidence, without guessing causes."""
import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REL = Path('docs/implementation/prospectus-integration-closure')


def verified_evidence(root, records):
    if not records:
        raise ValueError('Attribution requires named inspected evidence')
    for row in records:
        path = (root/row['path']).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError('Attribution evidence unavailable or outside repository')
        if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Attribution evidence changed: '+row['path'])
    return records


def report(root=ROOT):
    ledger = json.loads((root/REL/'gap-status.json').read_text())
    review = json.loads((root/REL/'attribution-review.json').read_text())
    expected = {g['id'] for g in ledger['gaps']}
    rows = review['gaps']
    if len(rows)!=len(expected) or {g['id'] for g in rows} != expected:
        raise ValueError('Reviewed attribution must cover each current gap once')
    for row in [*rows, *review['packages']]:
        if not row['finding'] or not row['remaining'] or not row['next_action']:
            raise ValueError('Attribution requires a finding, limits and repair action')
        verified_evidence(root,row['evidence'])
        if row.get('fundamental_limitation_established'):
            raise ValueError('No inspected fundamental-limit study is registered in this program')
    return {'version':'prospectus-closure-attribution.v2',
        'classification_basis':'IMPLEMENTER_REVIEW_OF_NAMED_CODE_AND_EXECUTION_RECORDS',
        'automatic_causal_inference':False, 'independent_review':False,
        'source_review_sha256':hashlib.sha256((root/REL/'attribution-review.json').read_bytes()).hexdigest(),
        'gaps':rows,'packages':review['packages'],
        'package_verdict':'NO_WHOLE_PACKAGE_UNSUITABILITY_ESTABLISHED', 'program_complete':False,
        'limits':['Passing finite controls does not establish general legal correctness',
                  'Local unimplemented work is distinct from missing external review',
                  'Retained runs are evidence at their recorded methods; currentness is reported separately']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    result = json.dumps(report(),indent=2)+'\n'
    if args.output:
        args.output.write_text(result)
    else:
        print(result,end='')
