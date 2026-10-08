"""Executed round-12 source, formal, generated-runtime and evaluation routes."""
from argparse import ArgumentParser
from collections import Counter
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from legalmath.interpretation.assurance.diversity import save, identity
from legalmath.interpretation.assurance.workflow import EvidenceJournal
from legalmath.interpretation.assurance.regions import reconcile_page, choose_region_action
from legalmath.canonical import raw_digest
JDK = ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1'


def sources(out):
    from PIL import Image
    from assurance_source_routes import ocr
    retained = ROOT/'artifacts/interpretation/round11/M2/attempt-04/sources'
    pages = []; counts = Counter()
    for name in ('23EC35-annex1', '23EC35-annex2', '23EC49-appendix'):
        report = json.loads((retained/name/'report.json').read_text())
        for old in report['pages']:
            work = out/name/f"page-{old['page']:02}"; work.mkdir(parents=True)
            routes = {route: Path(row['text_path']).read_text() for route, row in old['routes'].items()}
            raster = retained/name/f"page-{old['page']:02}"/'raster.png'
            if raw_digest(raster.read_bytes()) != old['raster_sha256']: raise ValueError('Retained raster changed')
            layout = json.loads((retained/name/f"pdfplumber-{old['page']:02}.json").read_text())
            boxes = {route: [0, 0, layout['width'], layout['height']] for route in routes}
            regions = reconcile_page(report['source_sha256'], old['page'], routes,
                                     raster_sha256=old['raster_sha256'], boxes=boxes)
            from legalmath.interpretation.assurance.region_actions import investigate
            recovery = investigate(regions, raster, layout, work/'actions', ocr)
            evidence = recovery['actions']
            counts.update(c['status'] for c in regions['comparisons'])
            result = {'document': name, 'regions': regions, 'new_evidence': evidence,
                      'status': regions['status'], 'release_eligible': False}
            save(work/'page.json', result); pages.append(result)
    # A positive extraction control and common-mode omission control are both required.
    clean = reconcile_page('a'*64, 1, {'text': 'Not\n permitted.', 'pixels': 'Not permitted.'}, raster_sha256='b'*64)
    faulty = reconcile_page('a'*64, 1, {'text1': 'Gifts prohibited.', 'text2': 'Gifts prohibited.',
                                      'pixels': 'Gifts prohibited. Except fee discounts.'}, raster_sha256='b'*64)
    if clean['status'] != 'OBSERVED_SOURCE_AGREEMENT' or not faulty['issues'] or len(pages) != 12:
        raise ValueError('Source acceptance contract failed')
    return {'engineering_status': 'PASS', 'pages': pages, 'comparison_counts': dict(counts),
            'resolved_page_count': sum(p['status'] == 'OBSERVED_SOURCE_AGREEMENT' for p in pages),
            'unresolved_page_count': sum(p['status'] != 'OBSERVED_SOURCE_AGREEMENT' for p in pages),
            'fault_controls': {'wrapping_resolved': True, 'common_text_omission_retained': True},
            'actions_executed': sum(len(p['new_evidence']) for p in pages), 'release_eligible': False}


def formal(out):
    from legalmath.interpretation.assurance.cvc5_ruleir import evaluate_snapshot, compare_bundles
    from legalmath.ir.evaluate import evaluate
    from legalmath.java.manifest import build_candidate, run_java
    from legalmath.interpretation.search.formal import project
    corpus = out/'corpus.json'
    command = [str(ROOT/'.venv/bin/python'), str(ROOT/'scripts/closure_corpus.py'), '--out', str(corpus)]
    exported = subprocess.run(command, capture_output=True, text=True, timeout=60, check=True)
    (out/'corpus-export.log').write_text(exported.stdout+exported.stderr)
    rows = []; groups = json.loads(corpus.read_text())
    for index, cases in enumerate(groups):
        built = build_candidate(cases[0]['bundle'], out/f'group-{index}', JDK)
        java = run_java(built['jar'], cases, JDK, built['class_name'])
        for case, binary in zip(cases, java):
            kwargs = {k: case[k] for k in ('bundle', 'snapshot', 'rule_id', 'valid_at', 'known_at')}
            actual = evaluate_snapshot(**kwargs); expected = project(evaluate(**kwargs))
            row = {'id': case['id'], 'cvc5': actual, 'python': expected, 'java': project(binary),
                   'passed': actual == expected == project(binary)}
            rows.append(row)
            if not row['passed']:
                save(out/'partial.json', rows); raise ValueError('Independent evaluator differs: '+str(row))
    seed = deepcopy(groups[0][0]); left = seed['bundle']; right = deepcopy(left)
    def mutate(value):
        if isinstance(value, dict):
            if value.get('cmp') == 'ge': value['cmp'] = 'gt'; return True
            return any(mutate(v) for v in value.values())
        if isinstance(value, list): return any(mutate(v) for v in value)
        return False
    if not mutate(right): raise ValueError('Boundary mutant absent')
    domain = {f['name']: {'states': ['T', 'F', 'U', 'C']} if f['type'] == 'bool' else
              {'states': ['V', 'U', 'C'], 'min': '0', 'max': '100000000000'} for f in left['facts']}
    compared = compare_bundles(left, right, seed['rule_id'], domain, seed['valid_at'], seed['known_at'])
    if compared['status'] != 'DIFFERENT': raise ValueError('Missing separating cvc5 boundary witness')
    replay = []
    for name, b in (('original', left), ('mutant', right)):
        built = build_candidate(b, out/name, JDK)
        case = {**seed, 'bundle': b, 'snapshot': compared['witness']}
        replay.append(project(run_java(built['jar'], [case], JDK, built['class_name'])[0]))
    if replay[0] == replay[1]: raise ValueError('SMT witness does not distinguish actual binary')
    equal = compare_bundles(left, left, seed['rule_id'], domain, seed['valid_at'], seed['known_at'])
    if equal['status'] != 'EQUIVALENT_WITHIN_DOMAIN': raise ValueError('Identity comparison invalid')
    return {'engineering_status': 'PASS', 'comparisons': rows, 'count': len(rows),
            'corpus_command': command, 'corpus_sha256': raw_digest(corpus.read_bytes()),
            'counterexample': compared, 'java_replay': replay, 'identity': equal,
            'scope': 'Valid RuleIR status/type/value; shared validator, separate traces tested in regression',
            'whole_compiler_proof': False, 'release_eligible': False}


def mutations(out):
    from legalmath.java.emit import emit, runtime_sources
    from legalmath.java.manifest import run_java
    from legalmath.ir.evaluate import evaluate
    from tests.conformance.test_java import spi_cases
    from tests.catala.backend_support import interaction_cases
    base = spi_cases()
    cases = base + json.loads((ROOT/'docs/specs/v0.1/fixtures/decision-cases.json').read_text())['cases'] + interaction_cases()
    name, generated = emit(base[0]['bundle'])
    runtime = runtime_sources(); original = runtime['Policy.java']
    changes = {
        'inclusive_boundary': ('cmp>=0', 'cmp>0'),
        'future_evidence': ('s(f,"recorded_at").compareTo(cutoff)<=0', 'true'),
        'multiple_exception': ('.count()>1', '.count()>2'),
        'version_end': ('at.compareTo((String)end)<0', 'at.compareTo((String)end)<=0'),
    }
    # Preserve exact faults; absence of a target is a failed challenge, not a skip.
    rows = []
    for mutation, (old, new) in changes.items():
        if old not in original: raise ValueError('Mutation target absent: '+mutation)
        work = out/mutation; src = work/'src'; classes = work/'classes'; src.mkdir(parents=True); classes.mkdir()
        altered = original.replace(old, new)
        for filename, text in {**runtime, 'Policy.java': altered, name+'.java': generated}.items():
            (src/filename).write_text(text)
        command = [str(JDK/'bin/javac'), '--release', '17', '-d', str(classes), *map(str, sorted(src.glob('*.java')))]
        result = subprocess.run(command, capture_output=True, text=True, timeout=90)
        (work/'compile.log').write_text(result.stdout+result.stderr)
        if result.returncode: raise ValueError('Mutant compilation failed: '+mutation)
        jar = work/'mutant.jar'
        with zipfile.ZipFile(jar, 'w') as z:
            for p in classes.rglob('*.class'): z.write(p, p.relative_to(classes))
        actual = run_java(jar, cases, JDK)
        killed = []; witnesses = []
        for case, java in zip(cases, actual):
            python = evaluate(**{k: case[k] for k in ('bundle', 'snapshot', 'rule_id', 'valid_at', 'known_at')})
            projection = lambda r: {k: v for k, v in r.items() if k not in ('engine_version', 'result_hash')}
            if projection(python) != projection(java):
                killed.append(case['id'])
                if len(witnesses) < 2:
                    witnesses.append({'case': case, 'python': python, 'mutant_java': java})
        row = {'mutation': mutation, 'command': command, 'jar_sha256': raw_digest(jar.read_bytes()),
               'changed_text': [old, new], 'detected_by': killed, 'witnesses': witnesses,
               'status': 'KILLED' if killed else 'SURVIVED'}
        rows.append(row); save(out/'partial.json', rows)
        if not killed: raise ValueError('Material runtime fault survived: '+mutation)
    from closure_pit import run as pit_runtime
    pit = pit_runtime(out/'pit-runtime', cases, base[0]['bundle'])
    return {'engineering_status': 'PASS', 'mutants': rows, 'cases_per_mutant': len(cases), 'pit': pit,
            'scope': 'Actual shared Java runtime source compiled with generated policy; finite targeted faults',
            'release_eligible': False}


def evaluation(out):
    state = json.loads((ROOT/'artifacts/interpretation/round12/state.json').read_text())
    evidence = {}
    for phase in ('P1', 'P3', 'P4'):
        entry = state['phases'][phase]['attempts'][-1]; path = ROOT/entry['path']
        if raw_digest(path.read_bytes()) != entry['sha256']: raise ValueError('Phase manifest changed')
        evidence[phase] = entry
    live_path = (ROOT/evidence['P4']['path']).parent/'live/result.json'
    live = json.loads(live_path.read_text())
    from closure_evaluation import fault_matrix, reference_demonstration
    faults = fault_matrix(out/'faults', (ROOT/evidence['P3']['path']).parent/'mutations/result.json')
    references = reference_demonstration(out/'reference-demonstration')
    from closure_references import evaluate as evaluate_transfer
    at = json.loads((ROOT/'docs/implementation/interpretation-round12/case-contract.json').read_text())['at']
    transfer = evaluate_transfer(ROOT, out/'transfer-references', live, at)
    live_counts = Counter('incomplete' if not r.get('execution_complete') else
        'uncertainty_retained' if r['status'] == 'UNCERTAINTY_RETAINED' else 'no_discrepancy_in_profile'
        for r in live['cases'])
    return {'engineering_status': 'PASS', 'phase_evidence': evidence, 'live': live,
            'fault_matrix': faults, 'reference_demonstration': references,
            'transfer_references': transfer,
            'live_dispositions': {'denominator': len(live['cases']), **dict(live_counts),
                'independently_verified_legal_acceptances': 0, 'legal_error_rate': None},
            'product_validation': 'NOT_ESTABLISHED: useful conditional fixture results do not establish legal automation accuracy',
            'reference_status': 'Source-bound authored engineering references; independent legal adjudication absent',
            'statistically_supported_method_ranking': False,
            'human_review_observations': 0, 'review_cost_saving_measured': False,
            'remaining_requirements': ['independent reference assessment', 'additional model family error comparison',
                'representative held-out family corpus', 'actual human review-time observations'],
            'release_eligible': False}


def main():
    parser = ArgumentParser(__doc__); parser.add_argument('route', choices=('sources', 'formal', 'mutations', 'evaluation'))
    parser.add_argument('--out', required=True); args = parser.parse_args(); out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    result = globals()[args.route](out); save(out/'result.json', result)
    print(json.dumps({k: v for k, v in result.items() if k in ('engineering_status', 'count', 'actions_executed', 'comparison_counts')}))


if __name__ == '__main__': main()
