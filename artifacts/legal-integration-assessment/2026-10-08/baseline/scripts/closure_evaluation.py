"""Separate deterministic failure detection from claims about legal accuracy."""
from copy import deepcopy
from pathlib import Path
import json

from legalmath.canonical import raw_digest
from legalmath.interpretation.assurance.diversity import save
from legalmath.interpretation.assurance.regions import reconcile_page
from legalmath.interpretation.assurance.abstractions import collect


def fault_matrix(out, runtime_path):
    from tests.assurance.support import packet, reading
    from tests.assurance.test_investigation import abstraction
    out.mkdir(parents=True)
    rows = []
    original = 'Do not offer gifts below 6 HKD. Except fee discounts.'
    for name, altered in [('negation', original.replace('not ', '')),
                          ('amount', original.replace('6 ', '60 ')),
                          ('unit', original.replace('HKD', 'USD')),
                          ('exception', original.split(' Except')[0])]:
        text_pair = reconcile_page('a'*64, 1, {'text.a': altered, 'text.b': altered}, raster_sha256='b'*64)
        raster_check = reconcile_page('a'*64, 1, {'text.a': altered, 'text.b': altered, 'raster.ocr': original}, raster_sha256='b'*64)
        rows.append({'fault': name, 'class': 'Synthetic shared text-extraction omission',
            'detected': {'two_text_extractors': bool(text_pair['issues']),
                         'text_and_raster': bool(raster_check['issues'])},
            'text_result': text_pair, 'raster_result': raster_check})
    for name, field, alternate in [('component', 'unit_of_assessment', 'individual benefit component'),
                                    ('actor', 'actors', ['issuer', 'distributor']),
                                    ('time', 'temporal_basis', 'transaction date rather than publication date')]:
        a = abstraction(reading()); b = deepcopy(a); b[field] = alternate
        compared = collect({'first': {'proposals': [a], 'unresolved': []},
                            'challenge': {'proposals': [b], 'unresolved': []}}, packet())
        same_formula = a['reading']['formalization'] == b['reading']['formalization']
        rows.append({'fault': name, 'class': 'Synthetic missing factual distinction',
            'detected': {'formula_identity_only': not same_formula,
                         'explicit_abstraction_comparison': any(p['status'] == 'INCOMPARABLE_ABSTRACTIONS' for p in compared['pairs'])},
            'evidence': compared})
    runtime = json.loads(Path(runtime_path).read_text())
    for mutant in runtime['mutants']:
        if not mutant.get('witnesses'):
            raise ValueError('Runtime fault has no retained separating case')
        rows.append({'fault': mutant['mutation'], 'class': 'Actual compiled Java runtime defect',
            'detected': {'compiled_runtime_reference_comparison': mutant['status'] == 'KILLED'},
            'evidence': {'path': str(runtime_path), 'sha256': raw_digest(Path(runtime_path).read_bytes()),
                         'witness_ids': [w['case']['id'] for w in mutant['witnesses']]}})
    if any(not any(r['detected'].values()) for r in rows):
        raise ValueError('A required controlled fault was missed by every applicable route')
    paired = []
    for first, second in [('two_text_extractors', 'text_and_raster'),
                          ('formula_identity_only', 'explicit_abstraction_comparison')]:
        cells = [r for r in rows if first in r['detected'] and second in r['detected']]
        paired.append({'routes': [first, second], 'denominator': len(cells),
                       'both_miss': sum(not r['detected'][first] and not r['detected'][second] for r in cells),
                       'second_only_detects': sum(not r['detected'][first] and r['detected'][second] for r in cells)})
    result = {'rows': rows, 'paired_detection': paired, 'controlled_faults': len(rows),
        'live_model_comparison': False, 'statistical_independence_established': False,
        'statistically_supported_ranking': False,
        'interpretation': 'Controlled complementary detection only; source and schema evidence are authored challenges, not observed model error rates.'}
    save(out/'result.json', result)
    return result


def reference_demonstration(out):
    """Run positive, negative and uncertainty controls through the actual workflow.

    Proposal/fidelity responses are controlled fixtures. Java decisions and
    repairs actually execute. These results establish engineering behaviour.
    """
    from tests.assurance.test_integration import responder, source, settings
    from tests.search.support import FunctionProvider
    from tests.search.test_formal import AT
    from legalmath.interpretation.assurance.integrated import IntegratedInvestigation
    from legalmath.interpretation.search.formal import bundle, RULE, project
    from legalmath.java.manifest import run_java
    from legalmath.ir.evaluate import evaluate
    root = Path(__file__).resolve().parents[1]
    out.mkdir(parents=True)
    rows = []
    for label, omitted, repair_rounds in [('clear', False, 0), ('repaired_omission', True, 1), ('unresolved_omission', True, 0)]:
        result = IntegratedInvestigation(out/label, FunctionProvider(responder(omitted)),
            root/'.localresources/java-toolchain/jdk-17.0.20.1+1', AT,
            settings=settings(repair_rounds)).run([source()], 'Selected gift control')
        clean = not result['residual_questions']
        if not result['execution_complete'] or clean != (label != 'unresolved_omission'):
            raise ValueError('Declared clear/uncertainty control failed: '+label)
        interpretation = Path(result['interpretation']['directory'])
        readings = json.loads((interpretation/'candidates.json').read_text())
        packet = json.loads((interpretation/'packet.json').read_text())
        active = result['interpretation']['report']['active_candidate_ids']
        cid = active[0]; compiled = bundle(readings[cid], packet, AT)
        build = next(b['build'] for b in result['independent']['binaries'] if b['candidate_id'] == cid)
        cases = []
        for gift, discount, expected in [(True, False, 'TRUE'), (True, True, 'FALSE'), (False, False, 'FALSE'), (None, False, 'UNKNOWN')]:
            facts = {}
            for f in compiled['facts']:
                value = {'gift': gift, 'discount': discount}[f['name']]
                facts[f['name']] = ({'status': 'unknown', 'type': 'bool', 'reason': 'MISSING'} if value is None else
                    {'status': 'known', 'type': 'bool', 'value': value, 'evidence_ids': ['controlled.fixture'],
                     'valid_from': AT, 'valid_until': None, 'recorded_at': AT})
            cases.append({'bundle': compiled, 'snapshot': {'subject_id': 'control', 'facts': facts},
                          'rule_id': RULE, 'valid_at': AT, 'known_at': AT, 'expected_status': expected})
        actual = run_java(build['jar'], cases, root/'.localresources/java-toolchain/jdk-17.0.20.1+1', build['class_name'])
        outcomes = [{'expected': c['expected_status'], 'java': project(a)} for c, a in zip(cases, actual)]
        if clean and any(r['expected'] != r['java']['status'] for r in outcomes):
            raise ValueError('Clear/repaired fixture produced a wrong Java decision')
        rows.append({'case': label, 'conditional_fixture_accepted': clean, 'outcomes': outcomes,
                     'semantic_repairs': len(result['interpretation']['report']['repairs']),
                     'report': str(out/label/'report.json'), 'release_eligible': False})
    result = {'cases': rows, 'denominator': 3, 'correct_conditional_acceptances': 2,
              'unsafe_conditional_acceptances': 0, 'required_abstentions': 1,
              'reference_basis': 'Authored synthetic source and scripted proposals; actual engines and binaries',
              'legal_accuracy_evaluated': False, 'legal_error_probability_upper_bound': None}
    save(out/'result.json', result)
    return result
