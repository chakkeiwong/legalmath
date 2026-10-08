"""Offline replay of retained judgments through the optional product transport.

No live provider is constructed. Exact source/expression text is selected from
the new request; no label or rationale is generated or repaired by this driver.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

from legalmath.canonical import digest, raw_digest
from legalmath.interpretation.assurance import candidate_responses, fidelity_v2
from legalmath.interpretation.assurance import executable_references_v2, scoped_investigation
from legalmath.interpretation.assurance.integrated import implementation_identity
from legalmath.interpretation.search.models import Settings
from legalmath.interpretation.search.providers import Completion

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'artifacts/legal-integration-coverage/2026-10-08/additional-200-calls-100-repairs'
OUT = ROOT/'artifacts/legal-candidate-response-product/2026-10-09/replay'
PLAN = ROOT/'docs/plans/legal-candidate-response-product-integration.md'
CHECKPOINT = 'd1743a5ce'


def require(condition, detail):
    if not condition:
        raise RuntimeError(detail)


def read(path):
    return json.loads(Path(path).read_bytes())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def ref(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': raw_digest(path.read_bytes())}


class Evidence:
    def __init__(self):
        self.files = {}

    def checked(self, reference):
        path = (ROOT/reference['path']).resolve()
        require(path.is_relative_to(ROOT), 'Historical reference leaves evidence root')
        require(raw_digest(path.read_bytes()) == reference['sha256'], 'Historical file changed: '+str(path))
        self.files[str(path.relative_to(ROOT))] = reference['sha256']
        return path

    def value(self, reference):
        return read(self.checked(reference))

    def verify(self):
        for path, sha in self.files.items():
            self.checked({'path': path, 'sha256': sha})


def retained(evidence):
    manifest_path = BASE/'completion-manifest.json'
    committed = subprocess.check_output(['git', 'show', CHECKPOINT+':'+str(manifest_path.relative_to(ROOT))], cwd=ROOT)
    require(committed == manifest_path.read_bytes(), 'Completion manifest differs from checkpoint')
    evidence.checked(ref(manifest_path))
    manifest = read(manifest_path)
    for value in manifest.values():
        for entry in value if isinstance(value, list) else [value]:
            if isinstance(entry, dict) and set(entry) == {'path', 'sha256'}:
                evidence.checked(entry)
    inputs = evidence.value(manifest['data_version'])
    partition = evidence.value(manifest['partition'])
    pair_rows = evidence.value(manifest['pairs'])
    concerns = evidence.value(manifest['concerns'])
    summary = evidence.value(manifest['summary'])
    proposals = {}
    for index, batch in enumerate(partition['batches']):
        pairs = {tuple(p) for p in batch}
        rows = [row for row in pair_rows if row['batch'] == index]
        require({(r['claim_id'], r['candidate_id']) for r in rows} == pairs, 'Retained batch denominator changed')
        for role in scoped_investigation.PERSPECTIVES:
            references = [r['provenance'][role]['receipt'] for r in rows]
            require(all(r == references[0] for r in references), 'Mixed receipt identities within a retained role')
            receipt = evidence.value(references[0])
            for item in receipt.get('evidence', []):
                evidence.checked(item)
            if receipt.get('proposal') is not None:
                require(receipt['role'] == role and receipt['batch'] == index, 'Role receipt changed target')
                proposal = receipt['proposal']
            else:
                result = evidence.value(receipt['result'])
                require(len(result['batches']) == 1, 'Unexpected historical receipt partition')
                old = result['batches'][0]
                valid = iter(old['proposals']); latest = {}
                for attempt in old['attempts']:
                    if attempt['status'] == 'VALIDATED_PROPOSAL':
                        latest[attempt['role']] = next(valid)
                proposal = latest[role]
            fidelity_v2.validate(proposal, inputs['packet'], inputs['claims'], inputs['candidates'], inputs['questions'], batch)
            require({(r['claim_id'], r['candidate_id']): r for r in proposal['checks']} ==
                    {(r['claim_id'], r['candidate_id']): r['perspectives'][role] for r in rows},
                    'Pair report differs from retained full proposal')
            require(proposal['additional_concerns'] == [r['concern'] for r in concerns if
                r['batch'] == index and r['role'] == role], 'Retained concerns differ from full proposal')
            proposals[(index, role)] = proposal
    require(len(pair_rows) == 492 and len(proposals) == 82, 'Wrong baseline denominator')
    return inputs, partition, proposals, summary


def encode_exact(proposal, wire):
    units = {u['unit_id']: u['text'] for u in wire['source_packet']['units']}
    source_keys = {(s['unit_id'], units[s['unit_id']][s['start_codepoint']:s['end_codepoint']]): s['span_id']
                   for s in wire['source_references']['spans']}
    candidates = {c['candidate_id']: c for c in wire['candidates']}
    executable_keys = {}
    for span in wire['executable_references']['spans']:
        text = candidates[span['candidate_id']]['representation']
        executable_keys[(span['candidate_id'], text[span['start_codepoint']:span['end_codepoint']])] = span['span_id']
    pair_keys = {(t['claim_id'], t['candidate_id']): t['pair'] for t in wire['pair_targets']}
    value = deepcopy(proposal)
    for row in value['checks']:
        cid = row['candidate_id']
        require(row['question_relation']['question_hash'] == candidates[cid]['question_hash'], 'Question changed')
        for field in ('source_support', 'question_relation'):
            row[field]['evidence'] = [{'span_ids': [source_keys[(q['unit_id'], q['quote'])]]}
                                      for q in row[field]['evidence']]
        row['executable_correspondence']['representation_quotes'] = [executable_keys[(cid, text)]
            for text in row['executable_correspondence']['representation_quotes']]
        row['pair'] = pair_keys[(row.pop('claim_id'), row.pop('candidate_id'))]
        row['question_relation'].pop('question_hash')
    return value


class RetainedProvider:
    provider_id = 'local.retained-candidate-response-replay.v1'
    live = False

    def __init__(self, proposals):
        self.proposals = proposals
        self.calls = 0
        self.routing = {'mode': 'OFFLINE_REPLAY', 'retained_proposals': digest([
            {'batch': key[0], 'role': key[1], 'value': value} for key, value in sorted(proposals.items())])}

    def complete(self, request, schema, settings):
        require(request.get('candidate_response_profile') == candidate_responses.PROFILE, 'Product option was bypassed')
        require(request['response_schema'] == schema, 'Provider schema differs from actual request')
        spec = request['investigation']
        proposal = self.proposals[(spec['batch'], spec['perspective'])]
        value = encode_exact(proposal, request)
        self.calls += 1
        return Completion(value, {'provider': self.provider_id, 'mode': 'OFFLINE_REPLAY',
            'request_hash': digest(request), 'response_hash': digest(value),
            'retained_proposal_hash': digest(proposal), 'new_legal_evidence': False})


def check_result(result, partition, proposals, summary):
    require(scoped_investigation.execution_complete(result), 'Replay left pending or unassessed pairs')
    require(result['assessment_coverage'] == summary['coverage'], 'Coverage changed')
    require([b['required_pairs'] for b in result['batches']] == partition['batches'], 'Product partition changed')
    checked = 0
    for index, batch in enumerate(result['batches']):
        require([a['role'] for a in batch['attempts']] == list(scoped_investigation.PERSPECTIVES), 'Perspectives changed')
        for role, proposal in zip(scoped_investigation.PERSPECTIVES, batch['proposals']):
            require(proposal == proposals[(index, role)], 'Replay changed retained proposal content or order')
            checked += len(proposal['checks'])
    require(checked == 984, 'Not every retained assessment was checked')
    return checked


def main():
    started = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    evidence = Evidence()
    inputs, partition, proposals, summary = retained(evidence)
    implementation = implementation_identity()
    provider = RetainedProvider(proposals)
    expected_calls = 0 if (OUT/'scoped/model/journal.json').exists() else 82
    options = dict(required_pairs=[p for b in partition['batches'] for p in b], batch_size=12,
        maximum_rounds=1, maximum_actions=82, deadline_seconds=3600, pair_order='candidate-first',
        reference_protocol=executable_references_v2.PROTOCOL, response_profile=candidate_responses.PROFILE,
        settings=Settings(timeout_seconds=300, max_input_bytes=200000, max_output_bytes=200000))
    result = scoped_investigation.investigate(inputs['packet'], inputs['claims'], inputs['candidates'],
        inputs['questions'], provider, OUT/'scoped', **options)
    count = check_result(result, partition, proposals, summary)
    require(provider.calls == expected_calls, 'Unexpected offline dispatch count')
    before_restart = provider.calls
    restarted = scoped_investigation.investigate(inputs['packet'], inputs['claims'], inputs['candidates'],
        inputs['questions'], provider, OUT/'scoped', **options)
    check_result(restarted, partition, proposals, summary)
    require(provider.calls == before_restart, 'Restart dispatched another provider call')
    evidence.verify()
    require(implementation_identity() == implementation, 'Implementation changed during replay')
    report = {'status': 'PASS', 'mode': 'OFFLINE_REPLAY', 'pairs': 492, 'assessments': count,
        'perspectives': list(scoped_investigation.PERSPECTIVES), 'full_proposals_equal': True,
        'concerns_preserved': sum(len(p['additional_concerns']) for p in proposals.values()),
        'coverage': result['assessment_coverage'], 'offline_provider_calls': provider.calls,
        'restart_provider_calls': provider.calls-before_restart, 'new_live_calls': 0,
        'historical_files_unchanged': len(evidence.files), 'default_changed': False,
        'legal_obligations_open': 46, 'legal_accuracy_established': False, 'release_eligible': False,
        'allowances': {'completed_calls': 49, 'call_ceiling': 200, 'completed_repairs': 7,
            'local_integration_repairs': 1, 'cumulative_repairs': 8, 'repair_ceiling': 100,
            'original_deadline_epoch': 1791519402.34676, 'sealed_ledgers_modified': False}}
    save(OUT/'result.json', report)
    save(OUT/'historical-inputs.json', [{'path': p, 'sha256': h} for p, h in sorted(evidence.files.items())])
    save(OUT/'run-manifest.json', {'git_commit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
        'baseline_checkpoint': CHECKPOINT, 'command': [sys.executable, *sys.argv],
        'environment': sys.executable, 'python': sys.version, 'CPU_GPU': 'CPU only; CUDA_VISIBLE_DEVICES=-1 intentionally hides GPU devices',
        'seeds': 'N/A: deterministic replay of retained proposals; no stochastic ranking',
        'implementation': implementation, 'script': ref(Path(__file__).resolve()),
        'data_version': ref(OUT/'historical-inputs.json'), 'plan': ref(PLAN),
        'wall_seconds': time.time()-started, 'result': ref(OUT/'result.json')})
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
