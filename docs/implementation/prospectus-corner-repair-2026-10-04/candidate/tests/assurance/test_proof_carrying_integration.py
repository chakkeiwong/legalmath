"""Attack the dossier boundary using actual recorded tool executions."""
import copy
import json
from pathlib import Path
import tempfile
import subprocess

import pytest

from legalmath.canonical import digest, canonical
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.integration_contract import (
    dossier_digest, parse_dossier, validate_dossier, evidence_file, read_evidence,
)
from legalmath.interpretation.assurance.integration_execution import run_replay, load_inputs, ReplayInput
from legalmath.interpretation.contracts import parse

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT/'docs/implementation/proof-carrying-assurance/replay-input.json'
JDK = ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1'
CATALA = {'compiler': ROOT/'.localresources/catala-toolchain/opam-root/catala-clean-1.2.1/bin/catala',
          'upstream': ROOT/'.localresources/catala-toolchain/catala-0f895e048d19dbe72f24cdd6d5f3398bfe1335fa',
          'lock': ROOT/'docs/implementation/catala/toolchain-lock.json'}


@pytest.fixture(scope='module')
def replay():
    with tempfile.TemporaryDirectory(prefix='dossier-tests-', dir=ROOT/'artifacts') as temporary:
        path = Path(temporary)
        result = run_replay(ROOT, CONFIG, path/'executed', JDK, catala=CATALA)
        dossier = read_evidence(result['dossier'], ROOT)
        yield dossier, path


def mutate(replay): return copy.deepcopy(replay[0])


def replace_method_payload(dossier, mid, path, payload_change):
    method = next(m for m in dossier['methods'] if m['method_id'] == mid)
    evidence = read_evidence(method['evidence'], ROOT)
    payload_change(evidence)
    path.write_bytes(canonical(evidence)); ref = evidence_file(path, ROOT)
    method['evidence'] = ref
    for o in dossier['obligations']:
        if o['method_id'] == mid: o['evidence'] = ref


def test_actual_java_and_catala_are_bound_to_replayed_source_and_cases(replay):
    d, _ = replay
    result = validate_dossier(d, ROOT)
    assert result['evidence_files_verified']
    assert result['status'] == 'BLOCKED_UNRESOLVED'
    assert not result['release_eligible'] and not result['legal_correctness_established']
    methods = {m['method_id']: m for m in d['methods']}
    assert methods['method.java']['status'] == methods['method.catala']['status'] == 'AGREES'
    search = read_evidence(methods['method.search']['evidence'], ROOT)['payload']
    assert len(search['visits']) == 5 and len(search['pairs']) == 10
    assert sum(p['result']['status'] == 'DIFFERENT' for p in search['pairs']) == 2
    assert sum(p['result']['status'] == 'NOT_COMPARABLE' for p in search['pairs']) == 8
    assert len(d['artifacts']) == 15
    assert {'method.java', 'method.catala'} <= set(result['shared_dependency_groups']['shared.facts'])
    assert dossier_digest(d) == dossier_digest(dict(reversed(list(d.items()))))


def test_schema_acceptance_alone_never_verifies_evidence(replay):
    result = validate_dossier(replay[0])
    assert not result['evidence_files_verified']
    assert {'kind': 'EVIDENCE_FILES_NOT_VERIFIED'} in result['blocking_reasons']


def test_product_cli_exposes_execution_and_file_verification(replay):
    result = subprocess.run([str(ROOT/'.venv/bin/python'), '-m', 'legalmath.cli',
                             'assurance-dossier-verify', '--dossier', str(replay[1]/'executed/dossier.json'),
                             '--repository', str(ROOT)], capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['evidence_files_verified'] is True
    help_result = subprocess.run([str(ROOT/'.venv/bin/python'), '-m', 'legalmath.cli',
                                  'assurance-dossier', '--help'], capture_output=True, text=True, timeout=10)
    assert help_result.returncode == 0 and '--catala-compiler' in help_result.stdout


@pytest.mark.parametrize('mutation', ['question', 'target', 'source', 'bundle', 'parent', 'discrepancy', 'required'])
def test_cross_record_bindings_reject_wrong_targets(replay, mutation):
    d = mutate(replay)
    if mutation == 'question': d['methods'][0]['target_id'] = 'question.wrong'
    if mutation == 'target': d['methods'][0]['input_hash'] = '0'*64
    if mutation == 'source': d['hypotheses'][0]['source_packet_hash'] = '0'*64
    if mutation == 'bundle': d['artifacts'][0]['bundle_hash'] = '0'*64
    if mutation == 'parent': d['hypotheses'][0]['parent_id'] = d['hypotheses'][0]['hypothesis_id']
    if mutation == 'discrepancy': d['discrepancies'][0]['method_ids'] = ['method.nonexistent']
    if mutation == 'required': d['required_method_ids'].append('method.nonexistent')
    with pytest.raises(LegalMathError): parse_dossier(d)


@pytest.mark.parametrize('name', ['release_eligible', 'legal_correctness_established'])
def test_engineering_cannot_grant_legal_or_release_authority(replay, name):
    d = mutate(replay); d[name] = True
    with pytest.raises(LegalMathError): parse_dossier(d)


def test_description_hash_cannot_stand_in_for_executed_evidence(replay):
    d = mutate(replay); d['methods'][0]['evidence']['sha256'] = digest({'description': 'Everything passed'})
    with pytest.raises(LegalMathError): validate_dossier(d, ROOT)


def test_rehashed_fabrication_cannot_claim_backend_success(replay):
    d = mutate(replay)
    replace_method_payload(d, 'method.java', replay[1]/'fake-replay.json',
                           lambda e: e['payload'].update(rows=[]))
    with pytest.raises(LegalMathError): validate_dossier(d, ROOT)


def test_rehashed_argument_verdict_is_recomputed(replay):
    d = mutate(replay)
    replace_method_payload(d, 'method.arguments', replay[1]/'fake-arguments.json',
                           lambda e: e['payload']['evaluation'].update(status='ARGUMENT_CHECKS_COMPLETED', questions=[]))
    with pytest.raises(LegalMathError): validate_dossier(d, ROOT)


def test_rehashed_search_cannot_erase_alternatives(replay):
    d = mutate(replay)
    replace_method_payload(d, 'method.search', replay[1]/'pruned-search.json',
                           lambda e: e['payload']['visits'].pop())
    with pytest.raises(LegalMathError): validate_dossier(d, ROOT)


def test_same_model_wrappers_cannot_invent_method_families(replay):
    d = mutate(replay)
    for m in d['methods']: m['family_id'] = 'family.shared'
    with pytest.raises(LegalMathError): parse_dossier(d)
    d = mutate(replay); d['methods'][0]['family_id'] = 'family.independent'
    with pytest.raises(LegalMathError): validate_dossier(d, ROOT)


def test_backend_shared_inputs_cannot_be_hidden(replay):
    d = mutate(replay)
    next(m for m in d['methods'] if m['method_id'] == 'method.catala')['shared_dependencies'] = []
    with pytest.raises(LegalMathError): validate_dossier(d, ROOT)


def test_unknown_obligation_blocks_even_when_all_methods_agree(replay):
    d = mutate(replay)
    for m in d['methods']: m['status'] = 'AGREES'
    d['open_questions'] = []; d['discrepancies'] = []
    d['obligations'][0]['status'] = 'UNKNOWN'
    assert any(x.get('status') == 'UNKNOWN' for x in validate_dossier(d)['blocking_reasons'])
    with pytest.raises(LegalMathError): validate_dossier(d, ROOT)


def test_hash_is_not_a_registered_proof_certificate(replay):
    d = mutate(replay); d['obligations'][0]['status'] = 'PROVED'
    with pytest.raises(LegalMathError): parse_dossier(d)


def test_missing_required_obligation_cannot_be_silently_discharged(replay):
    d = mutate(replay)
    d['obligations'] = [o for o in d['obligations'] if o['obligation_id'] != 'obligation.proof']
    with pytest.raises(LegalMathError): validate_dossier(d, ROOT)


def test_exact_quotation_is_checked_against_current_source(replay):
    d = mutate(replay); d['hypotheses'][0]['source_quotes'][0]['text'] += ' invented qualification'
    with pytest.raises(LegalMathError): validate_dossier(d, ROOT)


def test_missing_authority_question_cannot_be_erased(replay):
    d = mutate(replay); d['open_questions'] = []
    with pytest.raises(LegalMathError): validate_dossier(d, ROOT)


@pytest.mark.parametrize('mutation', ['erase', 'downgrade', 'explain_without_evidence'])
def test_executed_discrepancies_cannot_be_hidden_in_summary(replay, mutation):
    d = mutate(replay)
    if mutation == 'erase': d['discrepancies'] = []
    elif mutation == 'downgrade': d['discrepancies'][0]['severity'] = 'INFO'
    else: d['discrepancies'][0]['disposition'] = 'EXPLAINED'
    with pytest.raises(LegalMathError): validate_dossier(d, ROOT)


@pytest.mark.parametrize('mutation', ['objections', 'question_evidence', 'dependency', 'proposition', 'domain', 'scope'])
def test_evidence_cannot_be_relabelled_as_a_stronger_claim(replay, mutation):
    d = mutate(replay)
    if mutation == 'objections': d['hypotheses'][0]['opposing_reasons'].append('Unrecorded objection')
    elif mutation == 'question_evidence': d['open_questions'][0]['required_evidence'] = ['No further evidence needed.']
    elif mutation == 'dependency': next(m for m in d['methods'] if m['method_id'] == 'method.arguments')['shared_dependencies'] = []
    elif mutation == 'proposition': d['obligations'][0]['statement'] = 'Every English interpretation is correct.'
    elif mutation == 'domain': d['obligations'][0]['domain'] = 'All present and future circulars.'
    else: d['target_description'] = 'Every compliance question.'
    with pytest.raises(LegalMathError): validate_dossier(d, ROOT)


@pytest.mark.parametrize('path', ['../../etc/passwd', '/etc/passwd'])
def test_evidence_paths_cannot_escape_root(replay, path):
    with pytest.raises(LegalMathError): read_evidence({'path':path, 'sha256':'0'*64}, ROOT)


def test_source_change_invalidates_evidence_with_no_model_call(replay):
    d = mutate(replay); ref = copy.deepcopy(d['upstream_inputs'][0])
    path = replay[1]/'changed-input.json'; path.write_text('{}')
    ref['path'] = path.relative_to(ROOT).as_posix(); d['upstream_inputs'][0] = ref
    with pytest.raises(LegalMathError): validate_dossier(d, ROOT)


def test_original_manifest_cannot_be_removed_while_embedded_config_survives(replay):
    d = mutate(replay)
    d['upstream_inputs'] = [r for r in d['upstream_inputs'] if r != d['input_manifest']]
    with pytest.raises(LegalMathError): validate_dossier(d, ROOT)


def test_embedded_config_must_equal_the_retained_input_manifest(replay):
    d = mutate(replay)
    d['target']['input_manifest']['probe_limit'] = 1
    d['target_hash'] = digest(d['target'])
    for m in d['methods']: m['input_hash'] = d['target_hash']
    for o in d['obligations']: o['input_hash'] = d['target_hash']
    with pytest.raises(LegalMathError) as error: validate_dossier(d, ROOT)
    assert error.value.code == 'E_INTEGRITY'
    assert 'Embedded config' in str(error.value.details)


def test_verify_revalidates_manifest_limits_before_replay(replay):
    d = mutate(replay)
    manifest = read_evidence(d['input_manifest'], ROOT)
    manifest['probe_limit'] = 10**9
    path = replay[1]/'unbounded-manifest.json'; path.write_bytes(canonical(manifest))
    old = d['input_manifest']; d['input_manifest'] = evidence_file(path, ROOT)
    d['upstream_inputs'] = [d['input_manifest'] if r == old else r for r in d['upstream_inputs']]
    d['target']['input_manifest'] = manifest; d['target_hash'] = digest(d['target'])
    for m in d['methods']: m['input_hash'] = d['target_hash']
    for o in d['obligations']: o['input_hash'] = d['target_hash']
    with pytest.raises(LegalMathError) as error: validate_dossier(d, ROOT)
    assert error.value.code == 'E_SCHEMA'


def test_unseen_operator_retains_extension_without_backend_execution(replay):
    config = parse(ReplayInput, json.loads(CONFIG.read_text()))
    packet, candidates, proposal = load_inputs(config, ROOT)
    # This is an adversarial data fixture, not a new public circular or fresh model reading.
    for r in candidates.values(): r['formalization']['result'] = '(unrecognized_future_duty true)'
    path = replay[1]/'new-grammar-candidates.json'; path.write_bytes(canonical(candidates))
    config['candidates'] = evidence_file(path, ROOT); config['origin'] = 'DECLARED_TEST_PROPOSALS'
    changed = replay[1]/'novel-input.json'; changed.write_bytes(canonical(config))
    result = run_replay(ROOT, changed, replay[1]/'unsupported-run', JDK, catala=None)
    d = read_evidence(result['dossier'], ROOT)
    assert all(h['status'] == 'UNENCODED' for h in d['hypotheses'])
    assert len([q for q in d['open_questions'] if q['status'] == 'EXTENSION_REQUIRED']) == 5
    assert not d['artifacts'] and result['status'] == 'BLOCKED_UNRESOLVED'
