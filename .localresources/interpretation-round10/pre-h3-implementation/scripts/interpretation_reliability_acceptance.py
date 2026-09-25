"""Revalidate retained development evidence; never dispatch a model or edit it."""
from argparse import ArgumentParser
from collections import Counter
from pathlib import Path
from legalmath.canonical import digest, loads, raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.assurance.quality import inspect_reading, presentation
from legalmath.interpretation.assurance.semantics import (
    representation, validate_fidelity, validate_fidelity_aggregate)
from legalmath.interpretation.search.models import validate_generation

ROOT = Path(__file__).resolve().parents[1]
A7 = ROOT/'artifacts/interpretation/round3/A7'
BASELINE = ROOT/'.localresources/interpretation-round4/baseline.json'


def require(condition, message):
    if not condition:
        raise LegalMathError('E_INTEGRITY', details=message)


def verified(directory):
    directory = directory.resolve()
    manifest = loads((directory/'manifest.json').read_bytes())
    for name, expected in manifest['files'].items():
        path = (directory/name).resolve()
        require(path.is_relative_to(directory), 'Unsafe retained path')
        require(raw_digest(path.read_bytes()) == expected, 'Retained bytes changed: ' + name)
    report = loads((directory/'report.json').read_bytes())
    require(digest(report) == manifest['report_hash'], 'Retained report hash mismatch')
    return report


def execute(out):
    # The phase supervisor independently checks these before and after execution.
    baseline = loads(BASELINE.read_bytes())
    for name, expected in baseline['protected_evidence'].items():
        path = (ROOT/name).resolve()
        require(path.is_relative_to(ROOT), 'Unsafe baseline path')
        require(raw_digest(path.read_bytes()) == expected, 'Protected input changed: ' + name)
    allowance = ROOT/'artifacts/interpretation/round2/live-allowance.json'
    allowance_hash = raw_digest(allowance.read_bytes())
    out = Path(out).resolve()
    require(out.is_relative_to(ROOT/'artifacts/interpretation/round4') and not out.exists(),
            'Use a new round4 acceptance output directory')
    out.mkdir(parents=True)
    summaries = {}
    accepted = {}
    for ref, expected_rows, expected_concerns in (('23EC46', 90, 19), ('24EC16', 384, 24)):
        directory = A7/'attempt-08/pilot'/ref
        report = verified(directory)
        packet = loads((directory/'packet.json').read_bytes())
        claims = loads((directory/'claims.json').read_bytes())
        candidates = loads((directory/'candidates.json').read_bytes())
        value = validate_fidelity_aggregate(report['fidelity'], packet, claims, candidates)
        require(value == report['fidelity'], 'Revalidation changed judgments or evidence')
        require(len(value['checks']) == expected_rows and len(value['additional_concerns']) == expected_concerns,
                'Unexpected retained workload')
        diagnostics, view = presentation(candidates, packet)
        save(out/ref/'prose-quality.json', diagnostics)
        save(out/ref/'candidate-presentation.json', view)
        flagged = [cid for cid, q in diagnostics.items() if q['status'] == 'FLAGGED']
        summaries[ref] = {'source_packet_hash': digest(packet), 'fidelity_hash': digest(value),
                          'checks': len(value['checks']), 'concerns': len(value['additional_concerns']),
                          'labels': dict(Counter(c['label'] for c in value['checks'])),
                          'flagged_candidate_ids': flagged, 'original_status': report['status'],
                          'original_manifest_sha256': raw_digest((directory/'manifest.json').read_bytes())}
        accepted[ref] = candidates
    require(not summaries['23EC46']['flagged_candidate_ids'], 'Unexpected pattern in 23EC46 control')
    require(bool(summaries['24EC16']['flagged_candidate_ids']), 'Known 24EC16 corruption missed')

    bad_directory = A7/'attempt-05/pilot/24EC16'
    verified(bad_directory)
    call = bad_directory/'calls/call-002'
    request = loads((call/'request.json').read_bytes())
    response = loads((call/'response.json').read_bytes())['value']
    # Demonstrate the specific distinction: valid structural contract, bad prose.
    generation = validate_generation(response, request['source_packet'])
    corruption = {r['local_id']: inspect_reading(r, request['source_packet']) for r in generation['readings']}
    findings = [f for d in corruption.values() for f in d['findings']]
    require(any(f['kind'] == 'SELF_REPAIR_CHATTER' and f['field_path'][0] == 'questions' for f in findings),
            'Actual model self-repair chatter missed')
    require(any(f['kind'] == 'PLACEHOLDER_ONLY' and f['field_path'] == ['subject'] for f in findings),
            'Actual placeholder subject missed')
    save(out/'actual-corrupt-generation.json', {'response_sha256': raw_digest((call/'response.json').read_bytes()),
                                              'structural_contract': 'VALID', 'diagnostics': corruption})

    pair_directory = A7/'attempt-07/pilot/23EC46'
    verified(pair_directory)
    bad = pair_directory/'calls/call-008'
    fixed = pair_directory/'calls/call-009'
    request = loads((bad/'request.json').read_bytes())
    bad_value = loads((bad/'response.json').read_bytes())['value']
    fixed_request = loads((fixed/'request.json').read_bytes())
    fixed_value = loads((fixed/'response.json').read_bytes())['value']
    require(fixed_request['invalid_response'] == bad_value, 'Wrong historical correction')
    require(all(fixed_request[k] == request[k] for k in ('claims', 'candidates', 'required_pairs', 'source_packet')),
            'Correction changed the checked input')
    candidates = {r['candidate_id']: accepted['23EC46'][r['candidate_id']] for r in request['candidates']}
    require(all(representation(candidates[r['candidate_id']]) == r['representation'] for r in request['candidates']),
            'Historical candidate meaning mismatch')
    pairs = [(p['claim_id'], p['candidate_id']) for p in request['required_pairs']]
    diagnostic = None
    try:
        validate_fidelity(bad_value, request['source_packet'], request['claims'], candidates, pairs)
    except LegalMathError as exc:
        require(exc.code == 'E_REFERENCE' and isinstance(exc.details, dict), 'Wrong error for actual extra pair')
        diagnostic = exc.details
    require(diagnostic is not None, 'Actual extra pair was accepted')
    require(diagnostic['counts'] == {'missing_pairs': 0, 'unexpected_pairs': 1, 'repeated_pairs': 0},
            'Wrong historical pair classification')
    require(diagnostic['unexpected_pairs'] == [{
        'claim_id': 'claim.dcb73daa28eff2bd1dfaddf5', 'candidate_id': 'deferred.1be0c966c249ce5c69da8936',
        'occurrences': 1}], 'Wrong extra pair identity')
    corrected = validate_fidelity(fixed_value, request['source_packet'], request['claims'], candidates, pairs)
    require(corrected == fixed_value and len(corrected['checks']) == 32, 'Corrected response changed or failed')
    save(out/'actual-pair-repair.json', {'bad_response_sha256': raw_digest((bad/'response.json').read_bytes()),
                                      'corrected_response_sha256': raw_digest((fixed/'response.json').read_bytes()),
                                      'diagnostic': diagnostic, 'corrected_status': 'VALIDATED_CONTRACT_ONLY',
                                      'replayed_new_repair_request': False})
    require(raw_digest(allowance.read_bytes()) == allowance_hash, 'Offline acceptance spent live allowance')
    summary = {'status': 'PASS', 'evidence_class': 'DETERMINISTIC_REVALIDATION_OF_RETAINED_DEVELOPMENT_RESPONSES',
               'baseline_sha256': raw_digest(BASELINE.read_bytes()), 'circulars': summaries,
               'known_corrupt_response_flagged': True, 'actual_extra_pair_identified': True,
               'unchanged_corrected_response_valid': True, 'new_live_calls': 0,
               'allowance_used': len(loads(allowance.read_bytes())['calls']), 'allowance_sha256': allowance_hash,
               'legal_accuracy_evaluated': False, 'independent_new_model_judgment': False,
               'limits': ['Known development failures; no future error rate',
                          'Original legal uncertainty and all source-fidelity judgments retained']}
    save(out/'summary.json', summary)
    save(out/'manifest.json', {'files': {str(p.relative_to(out)): raw_digest(p.read_bytes())
                                       for p in sorted(out.rglob('*.json'))}})
    return summary


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    result = execute(parser.parse_args().out)
    print('PASS: 474 unchanged fidelity checks; known prose corruption and extra pair identified; zero new live calls.')
