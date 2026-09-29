#!/usr/bin/env python3
"""Bounded offline phases, immutable attempts, causal repair and refreshed plans."""
from copy import deepcopy
from pathlib import Path
import argparse
import json
import os
import platform
import subprocess
import sys
import time
import traceback
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.prospectus import eligibility, eligibility_checks, legal_review, purchaser_cases
from legalmath.prospectus.common import JDK, LEAN, TOOLCHAIN, now, read, sha, write
from legalmath.prospectus.models import AT, make_model, cases_for
from legalmath.qualification import assurance, proof, gregorian
from legalmath.transaction import engine, intake, prospective

OUT = ROOT/'docs/implementation/eligibility-gap-closure'
PHASES = ('G0', 'G1', 'G2', 'G3', 'G4', 'G5')


def identity():
    paths = [Path(__file__), ROOT/'docs/plans/eligibility-gap-closure.md']
    for prefix, suffixes in (('src', {'.py', '.java', '.lean', '.json'}), ('tests', {'.py'})):
        paths.extend(p for p in (ROOT/prefix).rglob('*') if p.suffix in suffixes and p.is_file())
    paths += legal_review.dossier_files(ROOT)
    for relative in ('docs/prospectus/manifest.json', 'docs/compliance/sources/manifest.json',
                     'docs/compliance/feeds/manifest.json', 'docs/prospectus/coco-cases/sources.json',
                     'docs/prospectus/coco-cases/cases.json', 'docs/implementation/catala/toolchain-lock.json'):
        paths.append(ROOT/relative)
    # Include all retained input bytes used by intake and the date-reading replay.
    for prefix in ('docs/prospectus/text', 'docs/prospectus/originals', 'docs/compliance/sources',
                   'docs/compliance/feeds', 'docs/prospectus/coco-cases/sources'):
        paths.extend(p for p in (ROOT/prefix).rglob('*') if p.is_file())
    retained = ROOT/'artifacts/assurance-continuation/2026-09-29/retained-reading-qualification/attempt-02'
    paths.extend(retained.glob('*/machine/model.json'))
    paths.extend(retained.glob('*/qualification.json'))
    paths.extend(retained.glob('*/inputs.json'))
    capacity = ROOT/'artifacts/assurance-capacity/2026-09-29/D1/attempt-01/checks/result.json'
    paths.append(capacity)
    return {'files': {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sorted(set(paths))},
            'tools': {str(p): sha(p.read_bytes()) for p in (LEAN, TOOLCHAIN['compiler'], JDK/'bin/java', JDK/'bin/javac')}}


def tests(out, paths, *, timeout=300):
    argv = [sys.executable, '-m', 'pytest', '-q', *paths, '--junitxml=' + str(out/'tests.xml')]
    with (out/'pytest.log').open('w') as log:
        run = subprocess.run(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
    suites = ET.parse(out/'tests.xml').getroot()
    counts = {key: sum(int(x.get(key, '0')) for x in suites.findall('testsuite'))
              for key in ('tests', 'failures', 'errors', 'skipped')}
    result = {'command': argv, 'exit_code': run.returncode, **counts}
    write(out/'test-result.json', result)
    if run.returncode or counts['failures'] or counts['errors'] or counts['skipped']:
        raise ValueError('Incomplete or failed regression; inspect pytest.log')
    return result


def check_native(report, inputs):
    if report['proof']['status'] != 'KERNEL_CHECKED':
        raise ValueError('Formal preservation not checked')
    for target, row in report['targets'].items():
        if row['status'] != 'CHECKED' or len(row['cases']) != len(inputs):
            raise ValueError('Native target incomplete: ' + target + ': ' + str(row.get('detail')))
    return report['summary']


def G0(out):
    legal = legal_review.verify_dossier(ROOT)
    sources = read(purchaser_cases.DOSSIER/'sources.json')
    pair = purchaser_cases.validate_dossier(read(purchaser_cases.DOSSIER/'cases.json'), sources)
    capacity = read(ROOT/'artifacts/assurance-capacity/2026-09-29/D1/attempt-01/checks/result.json')
    versions = {}
    for label, argv in (('lean', [str(LEAN), '--version']), ('java', [str(JDK/'bin/java'), '-version']),
                        ('catala', [str(TOOLCHAIN['compiler']), '--version'])):
        run = subprocess.run(argv, capture_output=True, text=True, timeout=20, check=True)
        versions[label] = (run.stdout + run.stderr).strip()
    # Verify literal provenance against the retained source, without upgrading it
    # into a certified interpretation or a current-law assertion.
    anchors = []
    for name, spec in eligibility.specifications().items():
        for key, quote in spec['anchors']:
            if key is None:
                continue
            path = ROOT/'docs/prospectus/legal/text'/f'{key}.txt'
            if ' '.join(quote.split()) not in ' '.join(path.read_text().split()):
                raise ValueError('Changed HKMA source quotation: ' + name)
            anchors.append({'model': name, 'source': str(path.relative_to(ROOT)),
                            'sha256': sha(path.read_bytes()), 'quotation': quote, 'entailment': 'NOT_ESTABLISHED'})
    return {'legal_dossier': legal, 'purchaser_dossier': pair, 'capacity_baseline': capacity,
            'source_bindings': anchors, 'versions': versions, 'live_calls': 0}


def joined_cases(name, spec):
    inputs = cases_for('joined_' + name, spec)
    # Complete-profile abstention is challenged in the actual native path.
    for status in ('unknown', 'conflict'):
        c = deepcopy(inputs[0]); c['id'] += '.' + status
        field = spec['facts'][0][0]
        c['snapshot']['facts'][field] = ({'type': 'bool', 'status': 'unknown', 'reason': 'MISSING'}
            if status == 'unknown' else {'type': 'bool', 'status': 'conflict', 'evidence_ids': ['a', 'b']})
        if status == 'conflict':
            c['snapshot']['evidence']['/' + field] = ['a', 'b']
        inputs.append(c)
    return inputs


def G1(out):
    equations = eligibility_checks.prove(out/'equations')
    results = {}
    for name, spec in eligibility.specifications().items():
        inputs = joined_cases(name, spec)
        report = assurance.run(eligibility.models()[name], inputs, out/name, JDK, toolchain=TOOLCHAIN)
        summary = check_native(report, inputs)
        for target in report['targets'].values():
            if any(row['result']['status'] != 'ABSTAIN' for row in target['cases'][-2:]):
                raise ValueError('Missing/conflicting native facts did not abstain')
        results[name] = summary
        print('G1 ' + name + ': native/formal checked', flush=True)
    return {'independent_equations': equations, 'models': results,
            'native_executions': sum(r['executed_target_cases'] for r in results.values())}


def G2(out):
    bank_request, store = intake.bootstrap(ROOT, out/'bank', at=now())
    records = store.json(bank_request['registry_sha256'])
    for row in read(ROOT/'docs/prospectus/legal/manifest.json')['sources']:
        if row.get('use_for_applicable_law') is False:
            continue
        key = Path(row['text_path']).stem
        raw = row['key'] + '.legal-original'
        recorded = legal_recorded_at(row['retrieved_on'])
        records[raw] = intake.record(store.put((ROOT/row['path']).read_bytes()), 'law', row['source_url'], recorded,
                                     media_type='application/octet-stream')
        records[key] = intake.record(store.put((ROOT/row['text_path']).read_bytes()), 'law', row['source_url'], recorded,
                                     dependencies=[raw])
    source_map = read(purchaser_cases.DOSSIER/'sources.json')
    for key, row in source_map.items():
        raw = key + '.original'
        records[raw] = intake.record(store.put((ROOT/row['path']).read_bytes()), 'law', row['url'], row['retrieved_at'], media_type='application/pdf')
        doc = read(ROOT/row['text_path'])
        text = '\n\n'.join(p['text'] for p in doc['pages']).encode()
        records[key] = intake.record(store.put(text), 'law', row['url'], row['retrieved_at'], dependencies=[raw])
    bank_request['registry_sha256'] = store.put(records)
    instruments = ['ubs-sgd-at1-2024-final-published', 'barclays-at1-2025', 'standard-chartered-at1-2025-january']
    reports = []
    for key in instruments:
        bank = deepcopy(bank_request)
        bank['context']['instrument_id'] = key
        # No Swiss basis is substituted for UK issuers. The missing UK basis is
        # itself an explicit dependency, not an assumed absence of powers.
        bases = ['swiss-cao-20250101-de'] if key.startswith('ubs') else ['uk-instrument-specific-resolution-basis-not-established']
        request = {'profile': eligibility.PROFILE, 'bank_request': bank,
            'product_assertions_sha256': store.put({}), 'issuer_basis_source_ids': bases,
            'prospectus_source_ids': [key], 'contract_event_source_id': None}
        receipt = eligibility.investigate(request, store)
        eligibility.revalidate(receipt, request, store)
        if len(receipt['inventory']) != 14 or receipt['may_execute_transaction']:
            raise ValueError('Missing obligation or false clearance')
        write(out/(key + '.json'), {'request': request, 'receipt': receipt})
        reports.append({'instrument': key, 'bank_obligations': 14, 'decision': receipt['decision'],
            'source_issues': len(receipt['source_issues']), 'contractual_loss': receipt['contractual_loss'],
            'may_execute_transaction': False})
    return {'real_documents': reports, 'tests': tests(out, ['tests/prospectus/test_joined_eligibility.py',
        'tests/prospectus/test_purchaser_cases.py', 'tests/compliance']),
        'actual_private_bank_approval': 'NOT_ESTABLISHED'}


def legal_recorded_at(value):
    # Retain precise timestamps where supplied. A date-only archive entry has
    # only day resolution; this normalization does not establish legal force.
    from legalmath.transaction.evidence import instant
    result = value if 'T' in value else value + 'T00:00:00Z'
    instant(result)
    return result


def G3(out):
    return tests(out, ['tests/assurance/test_executable_references.py',
        'tests/assurance/test_continuation_references.py', 'tests/assurance/test_continuation_scheduling.py',
        'tests/assurance/test_capacity_tables.py'])


def date_fixture():
    spec = {'facts': [('left', 'date'), ('right', 'date')],
        'outputs': [('after', 'bool', '(> left right)'), ('on_or_after', 'bool', '(>= left right)'),
                    ('same', 'bool', '(= left right)'), ('cutoff', 'bool', '(>= left (date 2000-02-29))')],
        'meaning': 'Hypothetical canonical Gregorian comparisons; no legal date-selection or business-day premise.'}
    dates = ['0001-01-01', '0001-01-02', '1900-02-28', '1900-03-01', '1999-12-31', '2000-01-01',
             '2000-02-28', '2000-02-29', '2000-03-01', '2023-02-28', '2023-03-01',
             '2024-02-29', '2024-03-01', '2100-02-28', '2100-03-01', '9999-12-30', '9999-12-31']
    pairs = [(d, d) for d in dates] + list(zip(dates, dates[1:])) + list(zip(dates[1:], dates))
    inputs = []
    for i, (left, right) in enumerate(pairs):
        snapshot = {'subject_id': 'synthetic-calendar', 'evidence': {}, 'facts': {}}
        for key, value in (('left', left), ('right', right)):
            ids = ['synthetic-calendar:' + str(i) + ':' + key]
            snapshot['evidence']['/' + key] = ids
            snapshot['facts'][key] = {'type': 'date', 'status': 'known', 'value': value, 'evidence_ids': ids,
                'complete': True, 'valid_from': AT, 'valid_until': None, 'recorded_at': AT}
        inputs.append({'id': 'calendar.' + str(i), 'snapshot': snapshot, 'valid_at': AT, 'known_at': AT})
    return make_model('gregorian_order', spec), inputs


def G4(out):
    theorem = gregorian.produce(out/'calendar-theorem', LEAN)
    codec = gregorian.exhaustive_codec_check()
    write(out/'codec.json', codec)
    m, inputs = date_fixture()
    native = assurance.run(m, inputs, out/'native', JDK, toolchain=TOOLCHAIN)
    check_native(native, inputs)
    for target in native['targets'].values():
        for case, row in zip(inputs, target['cases']):
            facts = case['snapshot']['facts']
            a, b = (gregorian.ordinal(facts[k]['value']) for k in ('left', 'right'))
            expected = {'after': a > b, 'on_or_after': a >= b, 'same': a == b,
                        'cutoff': a >= gregorian.ordinal('2000-02-29')}
            if any(row['result']['results'][k]['value'] != value for k, value in expected.items()):
                raise ValueError('Native date result differs from independent Gregorian ordinal')
    retained = ROOT/'artifacts/assurance-continuation/2026-09-29/retained-reading-qualification/attempt-02'
    replay = []
    for prior_path in sorted(retained.glob('*/qualification.json')):
        prior = read(prior_path)
        path = prior_path.parent/'machine/model.json'
        if not path.exists():
            if prior['summary']['status'] != 'UNENCODED':
                raise ValueError('Missing model for an encoded retained reading')
            replay.append({'qualification_path': str(prior_path.relative_to(ROOT)),
                'qualification_sha256': sha(prior_path.read_bytes()), 'identity': prior['identity'],
                'status': 'UNENCODED_OR_UNSUPPORTED', 'legal_meaning': 'NOT_ESTABLISHED',
                'invented_runtime_facts': False})
            continue
        model = read(path)
        try:
            cert = proof.produce(model, out/'retained-readings'/path.parent.parent.name)
            state = cert['status']
        except LegalMathError as exc:
            if exc.code != 'E_UNSUPPORTED_PROFILE': raise
            state = 'UNENCODED_OR_UNSUPPORTED'
        replay.append({'model_path': str(path.relative_to(ROOT)), 'model_sha256': sha(path.read_bytes()),
                       'retained_question_and_reading_identity': prior['identity'],
                       'status': state, 'legal_meaning': 'NOT_ESTABLISHED', 'invented_runtime_facts': False})
    if len(replay) != 9 or sum(r['status'] == 'KERNEL_CHECKED' for r in replay) != 8:
        raise ValueError('Retained date-reading accounting differs from the audited baseline')
    return {'calendar_theorem': theorem, 'codec': codec, 'native': native['summary'], 'retained_readings': replay,
            'tests': tests(out, ['tests/translation/test_gregorian_proof.py', 'tests/translation/test_qualification_proof.py'])}


def G5(out):
    result = tests(out, ['tests/prospectus', 'tests/compliance', 'tests/translation/test_qualification_proof.py',
        'tests/translation/test_qualification_windows.py', 'tests/translation/test_gregorian_proof.py',
        'tests/assurance/test_executable_references.py', 'tests/assurance/test_continuation_references.py',
        'tests/assurance/test_continuation_scheduling.py', 'tests/assurance/test_capacity_tables.py',
        'tests/assurance/test_round16.py'])
    bound = identity()
    write(out/'future-freeze.json', {'at': now(), 'method_and_inputs': bound, 'hash': digest(bound),
        'development_cases_are_future_observations': False, 'future_observations': [],
        'prospective_legal_accuracy': 'NOT_ESTABLISHED', 'human_quality_evidence': False})
    return {'regression': result, 'future_series': 'FROZEN_WITH_NO_FUTURE_OBSERVATIONS',
            'legal_correctness': 'NOT_ESTABLISHED', 'document_delivery': 'RECORDED_SEPARATELY_AFTER_BUILD'}


def execute(phase, *, output=OUT, repair_note=None):
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    bound = identity(); input_hash = digest(bound)
    directory = output/phase; directory.mkdir(exist_ok=True)
    prior = sorted(directory.glob('attempt-*/manifest.json'))
    predecessors = {}
    for earlier in PHASES[:PHASES.index(phase)]:
        manifests = sorted((output/earlier).glob('attempt-*/manifest.json'))
        if not manifests:
            raise ValueError('Missing predecessor ' + earlier)
        predecessor = read(manifests[-1])
        if predecessor['status'] != 'PASS' or predecessor['input_hash'] != input_hash:
            raise ValueError('Stale or failed predecessor ' + earlier)
        for relative, expected in predecessor['output_hashes'].items():
            if sha((manifests[-1].parent/relative).read_bytes()) != expected:
                raise ValueError('Changed predecessor output ' + earlier + ': ' + relative)
        predecessors[earlier] = sha(manifests[-1].read_bytes())
    if prior:
        last = read(prior[-1])
        if last['status'] == 'PASS' and last['input_hash'] == input_hash and last['predecessors'] == predecessors:
            result = prior[-1].parent/'result.json'
            if sha(result.read_bytes()) != last['result_sha256']:
                raise ValueError('Prior phase result was altered')
            for relative, expected in last['output_hashes'].items():
                if sha((prior[-1].parent/relative).read_bytes()) != expected:
                    raise ValueError('Prior phase output was altered: ' + relative)
            return {'phase': phase, 'status': 'PASS', 'reused': True, 'manifest': str(prior[-1])}
        if last['status'] != 'PASS' and not repair_note:
            raise ValueError('Prior failed/interrupted phase requires a causal repair note')
        if len(prior) >= 3:
            raise ValueError('Bounded retry limit reached; revise the recorded plan')
    attempt = directory/f'attempt-{len(prior)+1:03d}'; attempt.mkdir()
    write(attempt/'inputs.json', bound)
    if phase == 'G0':
        with zipfile.ZipFile(attempt/'method-snapshot.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for relative in bound['files']:
                if relative.startswith(('src/', 'tests/', 'scripts/')):
                    archive.write(ROOT/relative, relative)
    start = time.monotonic()
    manifest = {'phase': phase, 'status': 'RESERVED', 'input_hash': input_hash, 'predecessors': predecessors,
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'command': sys.argv, 'python': sys.version, 'platform': platform.platform(),
        'cpu_gpu': 'CPU only; CUDA_VISIBLE_DEVICES=-1', 'seeds': 'N/A: deterministic',
        'plan': 'docs/plans/eligibility-gap-closure.md', 'started_at': now(), 'live_calls': 0,
        'repair_note': repair_note, 'previous_attempt': str(prior[-1]) if prior else None}
    write(attempt/'manifest.json', manifest)
    write(output/'next-phase-plan.json', {'phase': phase, 'status': 'RESERVED', 'attempt': str(attempt),
        'instruction': 'Finish this phase or record a causal repair; no silent retries or live calls'})
    try:
        result = globals()[phase](attempt)
        write(attempt/'result.json', result)
        if identity() != bound:
            raise ValueError('Method or inputs changed during execution')
        manifest.update(status='PASS', result_sha256=sha((attempt/'result.json').read_bytes()))
    except Exception as exc:
        (attempt/'failure.log').write_text(traceback.format_exc())
        manifest.update(status='FAILED', error=type(exc).__name__, detail=str(exc))
        raise
    finally:
        manifest.update(wall_seconds=round(time.monotonic()-start, 3), finished_at=now())
        manifest['output_hashes'] = {str(p.relative_to(attempt)): sha(p.read_bytes()) for p in sorted(attempt.rglob('*'))
            if p.is_file() and p.name != 'manifest.json'}
        write(attempt/'manifest.json', manifest)
        index = PHASES.index(phase)
        write(output/'next-phase-plan.json', {'last_phase': phase, 'status': manifest['status'],
            'input_hash': input_hash, 'next_phase': PHASES[index+1] if manifest['status'] == 'PASS' and index+1 < len(PHASES) else None,
            'repair_required': manifest['status'] != 'PASS', 'error': manifest.get('detail'),
            'next_action': 'Proceed with bound successor; retain legal qualifications' if manifest['status'] == 'PASS' else
                           'Diagnose retained failure, execute repair reproducer, then retry with a causal repair note',
            'remaining': ['Private factual and policy evidence', 'Complete jurisdictional interpretation',
                          'English entailment proof', 'Actual future observations', 'Document build and rendered review'],
            'human_quality_evidence': False, 'live_calls_authorized': 0})
    return {'phase': phase, 'status': 'PASS', 'reused': False, 'manifest': str(attempt/'manifest.json')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=(*PHASES, 'all'), default='all')
    parser.add_argument('--repair-note')
    args = parser.parse_args()
    for phase in PHASES if args.phase == 'all' else (args.phase,):
        print(json.dumps(execute(phase, repair_note=args.repair_note)), flush=True)


if __name__ == '__main__':
    main()
