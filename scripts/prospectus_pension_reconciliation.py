"""Admitted production-consumer check with a separate integer-scaled oracle."""
import argparse
from copy import deepcopy
import gzip
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus import basf_pension_note as note
from legalmath.prospectus import basf_pension_reconciliation as reconciliation
from legalmath.prospectus.execution_authority import Authority, REL, file_hash, read, write
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor

PRIOR = REL + '/attempts/basf-references/attempt-005'
ROUNDING = REL + '/attempts/basf-references/attempt-007'
REVIEW = REL + '/reviews/pension-production-206'
PLAN = 'docs/plans/prospectus-pension-occurrences-repair-2026-10-17.md'
DOCUMENT = 'basf-annual-2022-exchange'
ADDED = ('pension_reconciliation_review', 'pension_reconciliation_explanation')
TESTS = ('tests/prospectus/test_rounding_enclosure.py',
         'tests/prospectus/test_basf_pension_reconciliation.py',
         'tests/prospectus/test_basf_pension_note.py',
         'tests/prospectus/test_build_contract.py', 'tests/prospectus/test_execution_authority.py')
METHODS = ('scripts/prospectus_pension_reconciliation.py',
           'src/legalmath/prospectus/rounding_enclosure.py',
           'src/legalmath/prospectus/basf_pension_reconciliation.py',
           'src/legalmath/prospectus/basf_pension_note.py',
           'src/legalmath/prospectus/build_contract.py',
           'src/legalmath/prospectus/execution_authority.py', *TESTS)
OUTPUT_CONTROLS = ('residual', 'interval', 'boundary', 'unknown-as-zero', 'lost-relation',
                   'coefficient', 'source', 'cause', 'scope', 'algorithm', 'incorporation',
                   'whole-answer', 'prose', 'boolean-amount')
PROFILE_CONTROLS = ('algorithm', 'incorporation', 'hypothesis', 'policy-context',
                    'source-edition', 'image', 'consumer', 'graph')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    with gzip.open(path, 'rt') as stream:
        return json.load(stream)


def compressed(path, value):
    with path.open('xb') as stream:
        stream.write(gzip.compress((json.dumps(value, sort_keys=True, ensure_ascii=False,
                                               allow_nan=False) + '\n').encode(), mtime=0))


def inputs(root):
    base = root / PRIOR
    return (load(base / 'products.json.gz'), read(base / 'prior-profiles.json'),
            read(base / 'hedge-profile.json'), read(base / 'profile.json'),
            load(base / 'pension-consumer.json.gz'))


def make_profile(root, products, baseline):
    graph = products['P1']['payload']['graph']
    units = {u['id']: u for u in graph['units']}
    source = read(root / PRIOR / 'original-source.json')
    image = next(r for r in read(root / ROUNDING / 'images.json') if r['page'] == 209)
    return {'version': 'basf-pension-reconciliation.v1', 'graph_sha256': digest(graph),
        'consumer_sha256': digest(baseline),
        'source': {'document': DOCUMENT, 'path': source['path'], 'sha256': source['sha256'],
                   'image_path': image['path'], 'image_sha256': image['sha256'], 'page': 209},
        'policy': [anchor(units[DOCUMENT + ':p209:l' + str(n)]) for n in range(24, 29)],
        'hypotheses': [{'id': 'half-million-error', 'error_bound': '1/2', 'basis': 'SUPPLIED_HYPOTHESIS'},
                       {'id': 'one-million-error', 'error_bound': '1', 'basis': 'SUPPLIED_HYPOTHESIS'}],
        'actual_rounding_algorithm_established': False, 'selected_incorporation_reading': None}


def consume(root, values, profile=None):
    products, prior, hedge, pension, _ = values
    kw = {} if profile is None else {'reconciliation_profile': profile,
            'expected_reconciliation_profile_sha256': digest(profile)}
    return note.consume(products, prior, hedge, pension, root,
        expected_prior_profiles_sha256=digest(prior), expected_hedge_profile_sha256=digest(hedge),
        expected_profile_sha256=digest(pension), **kw)


def independent_hypothesis(values, half_units):
    """Twice-EUR-million integer lattice, independent of Fraction/enclose."""
    known = values[0] - sum(v for v in values[1:] if v is not None)
    unknown = [i for i, v in enumerate(values) if v is None]
    radius2 = len(values) * half_units
    def text2(number):
        return str(number // 2) if number % 2 == 0 else str(number) + '/2'
    interval = None if unknown else [text2(2 * known - radius2), text2(2 * known + radius2)]
    return {'status': 'UNKNOWN_COMPONENT' if unknown else 'CONDITIONAL_ENCLOSURE',
        'known_residual_part': known, 'unknown_term_indices': unknown,
        'displayed_residual': None if unknown else known, 'maximum_relation_error': text2(radius2),
        'underlying_residual_enclosure': interval,
        'rounding_only_explanation': 'UNDETERMINED_UNKNOWN_COMPONENT' if unknown else
            'NOT_EXCLUDED_UNDER_ASSUMPTIONS' if abs(2 * known) <= radius2 else 'EXCLUDED_UNDER_ASSUMPTIONS',
        'actual_rounding_cause_established': False, 'underlying_relation_established': False}


def verify(actual, baseline, profile, graph):
    """Check source cells and all numerical results without production helpers."""
    require(set(actual) == set(baseline) | set(ADDED), 'Actual consumer coverage changed')
    require(digest({k: actual[k] for k in baseline}) == digest(baseline), 'Complete baseline changed')
    require(profile['graph_sha256'] == digest(graph) and profile['consumer_sha256'] == digest(baseline),
            'Original graph/consumer binding changed')
    review = actual[ADDED[0]]
    require(set(review) == {'version', 'profile_sha256', 'source', 'policy', 'relations',
        'actual_rounding_algorithm_established', 'source_error_established',
        'selected_incorporation_reading', 'financial_values_validated', 'answer'}, 'Review coverage changed')
    require(review['version'] == 'basf-pension-reconciliation.v1' and review['profile_sha256'] == digest(profile)
            and digest(review['source']) == digest(profile['source']), 'Profile/source identity changed')
    for flag in ('actual_rounding_algorithm_established', 'source_error_established', 'financial_values_validated'):
        require(review[flag] is False, 'Unsupported source promotion: ' + flag)
    require(review['selected_incorporation_reading'] is None, 'Unresolved incorporation selected')
    index = {u['id']: u for u in graph['units']}
    require(len(index) == len(graph['units']), 'Duplicate source identity')
    policy = []
    for n, supplied in zip(range(24, 29), profile['policy']):
        u = index[DOCUMENT + ':p209:l' + str(n)]
        expected = {'unit': u['id'], 'document': DOCUMENT, 'source_sha256': u['source_sha256'],
                    'start': 0, 'end': len(u['raw']), 'quote': u['raw']}
        require(digest(supplied) == digest(expected), 'Policy occurrence changed')
        policy.append({**expected, 'page': 209, 'bbox': u.get('bbox')})
    require(len(profile['policy']) == 5 and digest(review['policy']) == digest(policy), 'Policy context lost')
    statement = {r['id']: r for r in baseline['statement_review']['rows']}
    net = {r['id']: r for r in baseline['pension_note_review']['tables']['net']['rows']}
    require(len(review['relations']) == 4, 'A dated relation is missing')
    checks = []
    for offset, year in enumerate(('2022', '2021')):
        rows = review['relations'][2 * offset:2 * offset + 2]
        for subtotal, row in enumerate(rows):
            name = ('statement-nonreclassifiable-subtotal:' if subtotal else 'candidate-remeasurement-bridge:') + year
            labels = (['nonreclassifiable-subtotal', 'pensions', 'pension-tax', 'equity-method'] if subtotal else
                      ['statement-remeasurement', 'actuarial', 'return-deviation', 'signed-ceiling'])
            if subtotal:
                keys = ('nonrec', 'pensions', 'pension_tax', 'equity_nonrec')
                cells = [statement[k]['cells'][year] for k in keys]
                quantities = [{'value': q['integer_millions'], 'unit': 'million EUR', 'kind': 'million_eur',
                               'literal': q['literal'], 'source': q['source']} for q in cells]
            else:
                q = statement['pensions']['cells'][year]
                quantities = [{'value': q['integer_millions'], 'unit': 'million EUR', 'kind': 'million_eur',
                               'literal': q['literal'], 'source': q['source']}] + [
                    deepcopy(net[k]['cells'][year]) for k in ('actuarial', 'return_deviation', 'ceiling')]
            for position, q in enumerate(quantities):
                source = q['source']
                table_cell = not subtotal and position > 0
                require(isinstance(source, list) if table_cell else isinstance(source, dict),
                        'Original cell source schema changed')
                occurrences = source if table_cell else [source]
                require(bool(occurrences) and all(isinstance(s, dict) for s in occurrences),
                        'Nonempty cell source occurrences required')
                fragments = []
                for occurrence in occurrences:
                    require(occurrence.get('unit') in index, 'Unknown cell source unit')
                    u = index[occurrence['unit']]
                    start, end = occurrence.get('start'), occurrence.get('end')
                    require(type(start) is int and type(end) is int
                            and 0 <= start < end <= len(u['raw']), 'Invalid cell source offsets')
                    text = u['raw'][start:end]
                    expected_source = {'unit': u['id'], 'document': u['document'],
                        'source_sha256': u['source_sha256'], 'start': start, 'end': end,
                        'quote': text, 'page': u['page'], 'bbox': u.get('bbox')}
                    require(digest(occurrence) == digest(expected_source), 'Cell source identity changed')
                    fragments.append(text)
                text = ' '.join(fragments)
                require(q['literal'] == text, 'Complete cell literal changed')
                literal = text.strip().replace(',', '').replace('–', '-')
                value = None if literal == '-' else int(literal)
                require(q['value'] is None if value is None else type(q['value']) is int and q['value'] == value,
                        'Printed dash, sign or amount changed')
            values = [q['value'] for q in quantities]
            hypotheses = [{**h, **independent_hypothesis(values, bound)}
                          for h, bound in zip(profile['hypotheses'], (1, 2))]
            expected = {'id': name, 'quantities': quantities, 'coefficients': [1, -1, -1, -1], 'labels': labels,
                'scope_equivalence_established': bool(subtotal),
                'scope': 'Same printed statement subtotal and its three printed components' if subtotal else
                         'Candidate common complete scope with the statement; not established by the note',
                'hypotheses': hypotheses,
                'symbolic_residual': {'known_part': independent_hypothesis(values, 1)['known_residual_part'],
                    'unknown_terms': [{'label': labels[i], 'coefficient': -1} for i, v in enumerate(values) if v is None]},
                'rounding_cause_established': False, 'residual_attributed': False}
            require(digest(row) == digest(expected), 'Independent dated relation differs: ' + name)
            checks.append({'relation': name, 'known_part': expected['symbolic_residual']['known_part'],
                           'unknown_components': sum(v is None for v in values), 'hypotheses_checked': 2})
    require([r['known_part'] for r in checks] == [30, 1, 45, 0], 'Retained original numerical baseline differs')
    answer = review['answer']
    require(digest(actual[ADDED[1]]) == digest(answer), 'Normal explanation is detached from checked review')
    expected_answer = {
        'status': 'CONDITIONAL_SOURCE_BOUND_ARITHMETIC',
        '2022_candidate_bridge': 'The displayed difference is EUR30 million. If these amounts have the proposed complete common scope, per-amount errors bounded by half a million permit at most EUR2 million, and errors bounded by one million permit at most EUR4 million. Neither hypothesis explains EUR30 million. The common scope and actual rounding method remain unestablished.',
        '2022_statement_subtotal': 'The separate EUR1 million subtotal difference is within both error enclosures. This does not establish that rounding caused it.',
        '2021_candidate_bridge': 'The residual is EUR45 million minus the unknown signed ceiling amount. The printed dash remains unknown. A separate EUR45 million acquisitions/divestitures entry does not establish a reconciliation.',
        '2021_statement_subtotal': 'The printed subtotal agrees exactly with its three printed components.',
        'unresolved': ['Cause and complete scope of the EUR30 million difference',
                       'Meaning and amount of the 2021 signed-ceiling dash',
                       'Actual rounding method', 'Controlling incorporation reading'],
        'actual_rounding_cause_established': False, 'unique_complete_bridge_established': False,
        'source_error_established': False, 'financial_values_validated': False}
    require(digest(answer) == digest(expected_answer), 'Answer omits or changes a necessary qualification')
    return {'version': 'independent-pension-rounding.v1', 'relations': checks,
        'complete_baseline_preserved': True, 'source_questions_resolved': False,
        'original_task_complete': False}


def controls(actual, baseline, profile, graph, root, *, verifier=verify, test_acceptor=True):
    out = []
    for name in OUTPUT_CONTROLS:
        altered = deepcopy(actual)
        review = altered[ADDED[0]]
        row = review['relations'][0]
        if name == 'residual': row['hypotheses'][0]['displayed_residual'] = 0
        elif name == 'interval': row['hypotheses'][0]['underlying_residual_enclosure'] = ['-2', '2']
        elif name == 'boundary': review['relations'][1]['hypotheses'][0]['rounding_only_explanation'] = 'EXCLUDED_UNDER_ASSUMPTIONS'
        elif name == 'unknown-as-zero': review['relations'][2]['quantities'][3]['value'] = 0
        elif name == 'lost-relation': review['relations'].pop()
        elif name == 'coefficient': row['coefficients'][3] = 1
        elif name == 'source': row['quantities'][0]['source']['source_sha256'] = '0' * 64
        elif name == 'cause': row['rounding_cause_established'] = True
        elif name == 'scope': row['scope_equivalence_established'] = True
        elif name == 'algorithm': review['actual_rounding_algorithm_established'] = True
        elif name == 'incorporation': review['selected_incorporation_reading'] = 'operative'
        elif name == 'whole-answer': altered['answer'] = {'status': 'ALL_CLEAR'}
        elif name == 'prose': review['answer']['2022_candidate_bridge'] = 'Rounding explains the difference.'
        elif name == 'boolean-amount': row['quantities'][0]['value'] = True
        try:
            verifier(altered, baseline, profile, graph)
        except ValueError:
            out.append({'mutation': name, 'rejected': True})
        else:
            raise ValueError('Permissive output accepted: ' + name)
    for name in PROFILE_CONTROLS:
        p = deepcopy(profile)
        if name == 'algorithm': p['actual_rounding_algorithm_established'] = True
        elif name == 'incorporation': p['selected_incorporation_reading'] = 'operative'
        elif name == 'hypothesis': p['hypotheses'][0]['error_bound'] = '10'
        elif name == 'policy-context': p['policy'].pop(0)
        elif name == 'source-edition': p['source']['sha256'] = '0' * 64
        elif name == 'image': p['source']['image_sha256'] = '0' * 64
        elif name == 'consumer': p['consumer_sha256'] = '0' * 64
        elif name == 'graph': p['graph_sha256'] = '0' * 64
        try:
            reconciliation.evaluate(graph, baseline, p, root, expected_profile_sha256=digest(p))
        except ValueError:
            out.append({'mutation': 'repinned-profile:' + name, 'rejected': True})
        else:
            raise ValueError('Repinned invalid source profile accepted: ' + name)
    if test_acceptor:
        try:
            controls(actual, baseline, profile, graph, root, verifier=lambda *_a: True, test_acceptor=False)
        except ValueError as exc:
            require('Permissive output accepted' in str(exc), 'Acceptor control failed for another reason')
        else:
            raise ValueError('Permissive checker escaped its adverse controls')
    return {'controls': out, 'permissive_checker_detected': test_acceptor}


def run(root, attempt):
    values = inputs(root)
    products, _, _, _, baseline = values
    graph = products['P1']['payload']['graph']
    profile = read(root / REVIEW / 'profile.json')
    require(digest(profile) == digest(make_profile(root, products, baseline)), 'Reviewed source profile changed')
    off = consume(root, values)
    require(digest(off) == digest(baseline), 'Normal unconfigured consumer differs from whole baseline')
    actual = consume(root, values, profile)
    checked = verify(actual, baseline, profile, graph)
    adverse = controls(actual, baseline, profile, graph, root)
    compressed(attempt / 'consumer.json.gz', actual)
    write(attempt / 'profile.json', profile, exclusive=True)
    write(attempt / 'verification.json', checked, exclusive=True)
    write(attempt / 'controls.json', adverse, exclusive=True)
    return {'relations': len(checked['relations']), 'conditional_enclosures': 8,
            'mutations_rejected': len(adverse['controls']), 'normal_consumer_on_off_checked': True,
            'complete_baseline_preserved': True, 'source_questions_resolved': False}


def validate_submission(root, attempt, task):
    from legalmath.prospectus.execution_acceptance import checked_tests
    root, attempt = Path(root), Path(attempt)
    require(task['id'] == 'basf-references' and task.get('pension_reconciliation') == 'pension-rounding.v1',
            'Named pension evidence outside reviewed task')
    checked_tests(attempt / 'tests.xml', 65)
    values = inputs(root)
    graph = values[0]['P1']['payload']['graph']
    profile = make_profile(root, values[0], values[-1])
    require(digest(read(attempt / 'profile.json')) == digest(profile)
            and digest(read(root / REVIEW / 'profile.json')) == digest(profile), 'Retained profile differs')
    actual = load(attempt / 'consumer.json.gz')
    require(digest(consume(root, values, profile)) == digest(actual), 'Retained answer is not the actual normal consumer')
    require(read(attempt / 'verification.json') == verify(actual, values[-1], profile, graph), 'Independent result differs')
    require(read(attempt / 'controls.json') == controls(actual, values[-1], profile, graph, root), 'Adverse results differ')
    result, manifest = read(attempt / 'result.json'), read(attempt / 'run-manifest.json')
    require(result.get('status') == 'PASS' and result.get('scope') == 'CONDITIONAL_PENSION_ARITHMETIC'
            and result.get('whole_program_complete') is False, 'Invalid result disposition')
    require(manifest['methods'] == {n: file_hash(root / n) for n in METHODS}
            and set(METHODS) | {REVIEW + '/profile.json'} <= set(task['inputs'])
            and manifest['status'] == 'PASS' and 0 <= manifest['wall_seconds'] <= 180
            and manifest['cpu_gpu'] == 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1; no GPU framework used',
            'Frozen methods/environment/resource evidence differs')
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', required=True)
    args = parser.parse_args()
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    authority = Authority(ROOT)
    attempt = authority.path(args.attempt)
    admission = read(attempt / 'admission.json')
    require(admission['task'] == 'basf-references' and admission['binding'] == authority.binding(admission['task_spec'])
            and admission['task_spec'].get('pension_reconciliation') == 'pension-rounding.v1', 'Current frozen pension admission required')
    start = time.monotonic()
    def expired(_signum, _frame):
        raise TimeoutError('180-second package ceiling')
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(180)
    manifest = {'command': [sys.executable, '-m', 'scripts.prospectus_pension_reconciliation', '--attempt', args.attempt],
        'git_commit': admission['git_commit'], 'environment': {'python': sys.version, 'executable': sys.executable,
        'PYTHONPATH': str(ROOT / 'src')}, 'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1; no GPU framework used',
        'data_version': {'products': file_hash(ROOT / PRIOR / 'products.json.gz'),
                         'profile': file_hash(ROOT / REVIEW / 'profile.json')},
        'random_seeds': 'N/A; deterministic exact arithmetic',
        'methods': {n: file_hash(ROOT / n) for n in METHODS}, 'plan': PLAN,
        'result': args.attempt + '/RESULT.md', 'outputs': args.attempt,
        'historical_cost': 'All eight earlier admissions retained, including failed008; unknown earlier wall time remains unknown',
        'retained_failure': {'attempt': REL + '/attempts/basf-references/attempt-008',
            'manifest_sha256': file_hash(ROOT / REL / 'attempts/basf-references/attempt-008/run-manifest.json'),
            'wall_seconds': read(ROOT / REL / 'attempts/basf-references/attempt-008/run-manifest.json')['wall_seconds']}}
    write(attempt / 'started.json', manifest, exclusive=True)
    status, error, summary = 'PASS', None, {}
    try:
        command = [sys.executable, '-m', 'pytest', *TESTS, '-q', '--junitxml=' + str(attempt / 'tests.xml')]
        manifest['test_command'] = command
        with (attempt / 'tests.log').open('x') as log:
            subprocess.run(command, cwd=ROOT, env={**os.environ, 'PYTHONPATH': str(ROOT / 'src')},
                           stdout=log, stderr=subprocess.STDOUT, timeout=60, check=True)
        print(json.dumps({'stage': 'focused-tests', 'status': 'PASS'}), flush=True)
        summary = run(ROOT, attempt)
        require(manifest['methods'] == {n: file_hash(ROOT / n) for n in METHODS}, 'Methods changed during run')
        print(json.dumps({'stage': 'normal-consumer-and-independent-checks', 'status': 'PASS', **summary}), flush=True)
    except Exception as exc:
        status, error = 'FAIL', type(exc).__name__ + ': ' + str(exc)
        (attempt / 'failure-trace.txt').write_text(traceback.format_exc(limit=12)[-8192:])
    signal.alarm(0)
    size = sum(p.stat().st_size for p in attempt.rglob('*') if p.is_file())
    if size > 24 * 1024**2 or time.monotonic() - start > 180:
        status, error = 'FAIL', 'Artifact/time ceiling exceeded;8MiB reserved for authority/docs'
    manifest.update(status=status, error=error, wall_seconds=time.monotonic() - start, retained_bytes_before_seal=size)
    write(attempt / 'run-manifest.json', manifest, exclusive=True)
    write(attempt / 'result.json', {'task': 'basf-references', 'status': status,
        'scope': 'CONDITIONAL_PENSION_ARITHMETIC', 'whole_program_complete': False,
        'summary': summary, 'error': error}, exclusive=True)
    (attempt / 'RESULT.md').write_text('# Production pension reconciliation\n\nStatus: ' + status + '.\n\n'
        + (json.dumps(summary, sort_keys=True) if status == 'PASS' else str(error)) + '\n\n'
        + '| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Limit |\n'
        + '| --- | --- | --- | --- | --- | --- |\n'
        + ('| Accept conditional component | Actual normal consumer, independent arithmetic and whole baseline pass | Declared alterations refused | Complete accounting scope and source causes | Continue remaining source-to-answer work | Original task and build incomplete |\n' if status == 'PASS' else
           '| Reject current implementation | Failed | See error/log | Implementation or evidence defect | Review changed repair | No fundamental package rejection |\n')
        + '\nThe EUR30 million bridge remains unexplained. Common scope and actual rounding algorithm are unknown; '
          'the2021 dash remains unknown. A feasible enclosure does not establish rounding cause. '
          'No adviser opinion, source error, final financial correctness or exhaustive legal interpretation is established.\n\n'
          'Post-run red team: a source-consistent calculation can still compare incomplete accounting scopes. '
          'A complete original scope bridge could overturn the proposed comparison; it would not invalidate '
          'the conditional enclosure theorem. Source-scope interpretation remains the weakest evidence.\n')
    write(attempt / 'outputs.json', {str(p.relative_to(attempt)): file_hash(p)
        for p in sorted(attempt.rglob('*')) if p.is_file() and p.name != 'outputs.json'}, exclusive=True)
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
