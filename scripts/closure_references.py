"""Replay frozen authored cases only through explicitly reviewed fact bindings."""
from pathlib import Path
import json
import os
import subprocess

from legalmath.canonical import digest, raw_digest
from legalmath.interpretation.assurance.diversity import save
from legalmath.interpretation.search.formal import bundle, RULE, project
from legalmath.java.manifest import build_candidate, verify_candidate


def snapshot(reading, binding, at):
    definitions = {f['name']: f for f in reading['formalization']['facts']}
    if set(binding['fact_values']) != set(definitions):
        raise ValueError('Reference mapping must supply every declared fact explicitly')
    facts = {}
    for name, value in binding['fact_values'].items():
        typ = definitions[name]['type']
        if value is not None and ((typ == 'bool' and type(value) is not bool) or
                                  (typ != 'bool' and not isinstance(value, str))):
            raise ValueError('Reference fact type differs from candidate definition')
        facts[name] = ({'status': 'unknown', 'type': typ, 'reason': 'MISSING'} if value is None else
                       {'status': 'known', 'type': typ, 'value': value,
                        'evidence_ids': ['authored.reference.' + binding['reference_id']],
                        'valid_from': at, 'valid_until': None, 'recorded_at': at})
    return {'subject_id': 'authored.reference.' + binding['reference_id'], 'facts': facts}


def evaluate(root, out, live, at):
    doc = root/'docs/implementation/interpretation-round12'
    reference_path = doc/'transfer-reference-packets.json'
    references = json.loads(reference_path.read_text())
    case_rows = {c['case_id']: c for c in live['cases']}
    rows = []
    for reference in references['transfer_references']:
        cid = reference['case_id']; mapping_path = doc/'transfer-bindings'/(cid+'.json')
        live_case = case_rows[cid]
        if not mapping_path.exists() or 'report' not in live_case:
            rows.append({'case_id': cid, 'status': 'UNALIGNED_REFERENCE_BINDINGS',
                         'denominator': len(reference['cases']), 'executed': 0})
            continue
        mapping = json.loads(mapping_path.read_text())
        if (mapping['reference_sha256'] != raw_digest(reference_path.read_bytes()) or
                mapping['source_sha256'] != reference['source_sha256']):
            raise ValueError('Reference or source changed after explicit mapping review')
        report_path = Path(live_case['report']); report = json.loads(report_path.read_text())
        original = Path(report['interpretation']['directory'])
        # Phase snapshots retain the original absolute paths for provenance.
        # Read the immutable copy, not a later mutable top-level live report.
        if original.parent.parent.name != 'actions':
            raise ValueError('Unexpected investigation path')
        directory = report_path.parent/original.relative_to(original.parents[2])
        candidates_path = directory/'candidates.json'
        candidates = json.loads(candidates_path.read_text()) if candidates_path.exists() else {}
        reading = candidates.get(mapping['candidate_id'])
        if reading is None or digest(reading) != mapping['reading_sha256']:
            rows.append({'case_id': cid, 'status': 'RETAINED_CANDIDATE_CHANGED_OR_ABSENT',
                         'denominator': len(reference['cases']), 'executed': 0})
            continue
        expected = {c['id']: c for c in reference['cases']}
        if (len(mapping['cases']) != len(expected) or
                {c['reference_id'] for c in mapping['cases']} != set(expected)):
            raise ValueError('Reference mapping silently dropped or duplicated a case')
        packet = json.loads((directory/'packet.json').read_text())
        compiled = bundle(reading, packet, at)
        build = next((b['build'] for b in report['independent']['binaries']
                      if b['candidate_id'] == mapping['candidate_id']), None)
        if build is None:
            rows.append({'case_id': cid, 'status': 'BINARY_UNAVAILABLE',
                         'denominator': len(reference['cases']), 'executed': 0})
            continue
        jar = report_path.parent/Path(build['jar']).relative_to(original.parents[2])
        if (digest(compiled) != build['manifest']['bundle_hash'] or
                raw_digest(jar.read_bytes()) != build['manifest']['jar_sha256']):
            raise ValueError('Reference replay bundle or binary differs from its build manifest')
        cases = []
        for binding in mapping['cases']:
            if (binding['reference_expected'] != expected[binding['reference_id']]['expected'] or
                    not binding['explanation']):
                raise ValueError('Mapping changed the frozen answer or lost its explanation')
            cases.append({'id': cid+'.'+binding['reference_id'], 'bundle': compiled,
                          'snapshot': snapshot(reading, binding, at), 'rule_id': RULE,
                          'valid_at': at, 'known_at': at, 'jar': str(jar),
                          'class_name': build['class_name']})
        work = out/cid; work.mkdir(parents=True)
        request = work/'input.json'; result_path = work/'output.json'
        save(request, {'cases': cases, 'jdk': str(root/'.localresources/java-toolchain/jdk-17.0.20.1+1')})
        argv = [str(root/'.localresources/assurance-tools/venv/bin/python'), '-m',
                'legalmath.interpretation.assurance.sidecar', 'formal-cases',
                '--input', str(request), '--output', str(result_path)]
        with (work/'execution.log').open('w') as log:
            subprocess.run(argv, cwd=root, env={**os.environ, 'PYTHONPATH': str(root/'src'),
                'CUDA_VISIBLE_DEVICES': '-1'}, stdout=log, stderr=subprocess.STDOUT, timeout=180, check=True)
        result = json.loads(result_path.read_text())
        if result['status'] != 'PASS': raise ValueError('Reference binary/solver disagreement')
        catala = build_candidate(compiled, work/'catala',
            root/'.localresources/java-toolchain/jdk-17.0.20.1+1', backend='catala', catala_toolchain={
                'compiler': root/'.localresources/catala-toolchain/opam-root/catala-clean-1.2.1/bin/catala',
                'upstream': root/'.localresources/catala-toolchain/catala-0f895e048d19dbe72f24cdd6d5f3398bfe1335fa',
                'lock': root/'docs/implementation/catala/toolchain-lock.json'})
        verification = verify_candidate(catala, [{**case, 'expected': {}} for case in cases],
                                        root/'.localresources/java-toolchain/jdk-17.0.20.1+1')
        save(work/'catala-verification.json', verification)
        catala_results = json.loads((work/'catala/verification-results.json').read_text())
        outcomes = []
        for binding, actual, alternate in zip(mapping['cases'], result['comparisons'], catala_results, strict=True):
            catala_result = project(alternate['java'])
            if catala_result != actual['java']:
                raise ValueError('Catala and ordinary generated Java disagree on the reference case')
            outcomes.append({'reference_id': binding['reference_id'], 'expected_status': binding['expected_status'],
                             'actual': actual, 'catala': catala_result,
                             'matches': actual['java']['status'] == binding['expected_status']})
        rows.append({'case_id': cid, 'status': 'CONDITIONAL_REFERENCE_AGREEMENT' if all(o['matches'] for o in outcomes)
                     else 'CANDIDATE_REJECTED_BY_AUTHORED_REFERENCE', 'denominator': len(expected),
                     'executed': len(outcomes), 'outcomes': outcomes, 'mapping_sha256': raw_digest(mapping_path.read_bytes()),
                     'jar_sha256': raw_digest(jar.read_bytes()), 'command': argv,
                     'catala_build': catala, 'catala_full_result_verification': str(work/'catala-verification.json'),
                     'additional_assumptions': mapping['additional_assumptions'],
                     'binding_review': mapping['review_basis']})
    result = {'cases': rows, 'denominator': sum(len(r['cases']) for r in references['transfer_references']),
              'executed': sum(r['executed'] for r in rows), 'independent_legal_reference': False,
              'candidate_selection': 'Explicit post-generation mapping; not a blind accuracy estimate',
              'legal_correctness_established': False, 'release_eligible': False}
    save(out/'result.json', result)
    return result
