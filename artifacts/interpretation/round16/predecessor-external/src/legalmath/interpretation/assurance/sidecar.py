"""Narrow CPU adapters for the installed independent tools."""
from argparse import ArgumentParser
from pathlib import Path
import json
import sys

from ...canonical import raw_digest
from .diversity import save, clingo_extensions
from .cvc5_ruleir import evaluate_snapshot


def run(kind, value, output):
    if kind == 'formal-cases':
        from ...ir.evaluate import evaluate
        from ...java.manifest import run_java
        from ..search.formal import project
        groups = {}
        for case in value['cases']: groups.setdefault((case['jar'], case['class_name']), []).append(case)
        rows = []
        for (jar, class_name), cases in groups.items():
            actual = run_java(jar, cases, value['jdk'], class_name)
            for case, java in zip(cases, actual):
                kwargs = {k: case[k] for k in ('bundle', 'snapshot', 'rule_id', 'valid_at', 'known_at')}
                python = project(evaluate(**kwargs)); independent = evaluate_snapshot(**kwargs)
                rows.append({'id': case['id'], 'cvc5': independent, 'python': python, 'java': project(java),
                             'passed': independent == python == project(java)})
        return {'status': 'PASS' if rows and all(r['passed'] for r in rows) else 'INCOMPLETE_OR_DIFFERENT',
                'comparisons': rows, 'target': 'status/type/value', 'whole_compiler_proof': False}
    if kind == 'arguments':
        from ..search.arguments import evaluate_arguments
        proposal = (value.get('criticism') or {}).get('proposal')
        if proposal is None: return {'status': 'UNAVAILABLE'}
        ids = [a['argument_id'] for a in proposal['arguments']]
        if len(ids) > 12 or len(set(ids)) != len(ids):
            return {'status': 'UNSUPPORTED_GRAPH_LIMIT', 'argument_count': len(ids),
                    'maximum': 12, 'complete': False}
        # Compare raw attack semantics only; premise admissibility and proposed
        # preferences remain in the main argument evaluator and are not proved here.
        attacks = sorted({(a['attacker'], a['target']) for a in proposal['attacks']})
        from itertools import combinations
        oracle = []
        for size in range(len(ids)+1):
            for subset in combinations(ids, size):
                selected = set(subset)
                if any(a in selected and b in selected for a, b in attacks): continue
                if all(any(a in selected and b == outside for a, b in attacks) for outside in set(ids)-selected):
                    oracle.append(sorted(selected))
        actual = clingo_extensions(ids, attacks)
        return {'status': 'PASS' if actual['complete'] and sorted(actual['extensions']) == sorted(oracle) else 'INCOMPLETE_OR_DIFFERENT',
                'clingo': actual, 'exhaustive': sorted(oracle), 'premises_verified': False,
                'scope': 'Raw attack graph stable extensions; no legal priority decision'}
    if kind == 'source':
        root = Path(__file__).parents[4]; sys.path.insert(0, str(root/'scripts'))
        from assurance_source_routes import extract_one, ocr
        from .regions import reconcile_page
        from .region_actions import investigate
        path = Path(value['path'])
        if raw_digest(path.read_bytes()) != value['sha256']: raise ValueError('Source changed')
        extracted = extract_one(path, output.parent/'extraction')
        pages = []; actions = []
        for page in extracted['pages']:
            routes = {name: Path(row['text_path']).read_text() for name, row in page['routes'].items()}
            regions = reconcile_page(value['sha256'], page['page'], routes, raster_sha256=page['raster_sha256'])
            layout = json.loads((output.parent/'extraction'/f"pdfplumber-{page['page']:02}.json").read_text())
            raster = output.parent/'extraction'/f"page-{page['page']:02}"/'raster.png'
            actions.append(investigate(regions, raster, layout,
                output.parent/f"region-actions-{page['page']:02}", ocr))
            pages.append(regions)
        return {'status': 'UNCERTAINTY_RETAINED' if any(p['issues'] or p['findings'] for p in pages) else 'OBSERVED_SOURCE_AGREEMENT',
                'extraction': extracted, 'regions': pages, 'adaptive_actions': actions, 'release_eligible': False}
    raise ValueError('Unknown fixed adapter')


def main():
    p = ArgumentParser(__doc__); p.add_argument('kind', choices=('formal-cases', 'arguments', 'source'))
    p.add_argument('--input', required=True); p.add_argument('--output', required=True); args = p.parse_args()
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    result = run(args.kind, json.loads(Path(args.input).read_text()), output)
    save(output, result)


if __name__ == '__main__': main()
