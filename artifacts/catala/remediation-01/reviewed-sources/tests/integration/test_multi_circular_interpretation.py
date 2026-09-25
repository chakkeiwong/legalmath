"""Real retained circulars, source-written cases, compiled mutations and controls."""
from copy import deepcopy
from pathlib import Path
import shutil

import pytest

from legalmath.conformance import evaluate_case
from legalmath.errors import LegalMathError
from legalmath.interpretation.controller import Controller
from legalmath.interpretation.reports import Reports
from legalmath.interpretation.service import Interpretations
from legalmath.ir.trace import verify_result
from legalmath.review.lifecycle import Lifecycle
from legalmath.storage import Database
from .multi_circular_support import (
    IDENTITIES, REFS, bundle_for, load_fixture, load_sources, matches_expected,
    packet_for, requests_for, run_suite,
)


@pytest.fixture(scope='module')
def prepared(tmp_path_factory):
    root = Path(__file__).resolve().parents[2]
    corpus, freeze = load_fixture(root)
    db = Database(tmp_path_factory.mktemp('circular-source') / 'db')
    Lifecycle(db).register(IDENTITIES)
    return root, corpus, db, load_sources(db, root, freeze)


@pytest.mark.parametrize('ref', REFS)
def test_retained_inventory_and_frozen_python_scenarios(prepared, ref):
    _, corpus, db, sources = prepared
    case = next(c for c in corpus['cases'] if c['ref_no'] == ref)
    packet, selected, critical = packet_for(case, sources)
    assert len(packet['units']) > len(selected)  # complete text is retained beyond the slice
    assert critical in [u['unit_id'] for u in selected]
    Interpretations(db).create('author', ref + '.source-check', packet)
    bundle = bundle_for(case, selected)
    for request in requests_for(case, bundle):
        result = evaluate_case(request)
        assert matches_expected(result, request['expected']), (request['id'], request['expected'], result)
        assert verify_result(bundle, request['snapshot'], request['rule_id'], result)
    assert db.verify()


@pytest.fixture(scope='module')
def integrated(tmp_path_factory):
    root = Path(__file__).resolve().parents[2]
    out = tmp_path_factory.mktemp('five-circular-java')
    return run_suite(root, out), out


@pytest.mark.parametrize('ref', REFS)
def test_compiled_java_and_two_wrong_readings(integrated, ref):
    result, _ = integrated
    run = next(r for r in result['runs'] if r['ref_no'] == ref)
    assert run['scenario_count'] == run['named_cases_passed']
    assert run['full_python_java_parity']
    assert len(run['compiled_mutants']) == 2
    assert all(m['detected_by'] and m['jar_sha256'] for m in run['compiled_mutants'])


@pytest.mark.parametrize('ref', REFS)
def test_bounded_repairs_and_actual_release_veto(integrated, ref):
    result, out = integrated
    run = next(r for r in result['runs'] if r['ref_no'] == ref)
    assert (run['actions'], run['rounds'], run['processing_stop']) == (7, 3, 'ROUND_LIMIT')
    assert run['structural_omission_repaired'] and run['unresolved_issue_count'] > 0
    assert run['report_status'] == 'BLOCKED_UNRESOLVED'
    assert run['meaning_acceptance_rejected'] == run['release_guard_rejected'] == 'E_RELEASE_BLOCKED'
    assert run['inventory_review'] == 'UNREVIEWED' and not run['released']
    svc = Interpretations(Database(out / 'work/db'))
    # A terminal run remains read-only: re-driving cannot charge another round.
    before = svc.read('meaning', run['run_id'])
    Controller(svc).drive(run['run_id'])
    after = svc.read('meaning', run['run_id'])
    assert before == after
    assert Reports(svc).verify('meaning', run['run_id']) == run['report_hash']


@pytest.mark.parametrize('ref', REFS)
@pytest.mark.parametrize('corruption', ('quotation', 'offset'))
def test_corrupt_retained_span_is_rejected(prepared, ref, corruption):
    _, corpus, db, sources = prepared
    case = next(c for c in corpus['cases'] if c['ref_no'] == ref)
    packet, _, _ = packet_for(case, sources)
    altered = deepcopy(packet)
    if corruption == 'quotation': altered['units'][0]['text'] += ' fabricated qualification'
    else: altered['units'][0]['span']['start'] += 1
    with pytest.raises(LegalMathError) as error:
        Interpretations(db).create('author', ref + '.' + corruption, altered)
    assert error.value.code == 'E_HASH_MISMATCH'


def test_announcement_is_not_an_invented_sales_threshold(integrated):
    result, _ = integrated
    negative = result['announcement_negative_control']
    assert negative['no_executable_bundle'] and negative['member_failure_retained']
    assert negative['automatic_semantic_detection'] is False
    assert result['total_scenarios'] == 75
    assert result['compiled_mutants_detected'] == 10
    assert result['legal_meaning_verdict'] == 'NOT_ESTABLISHED'


def test_report_cannot_hide_unresolved_issues(integrated, tmp_path):
    result, out = integrated
    # Corrupt an isolated copy: preserve the evidence used by other cases.
    destination = tmp_path / 'corrupted-db'
    shutil.copytree(out / 'work/db', destination)
    svc = Interpretations(Database(destination))
    run_id = result['runs'][0]['run_id']
    with svc.db.transaction() as con:
        run = svc._run(con, run_id)
        report = svc._get(con, run_id, 'report', run['report_id'])
        svc._save(con, 'report', {**report, 'material_unresolved_issue_ids': []})
    with pytest.raises(LegalMathError) as error:
        Reports(svc).verify('meaning', run_id)
    assert error.value.code == 'E_INTEGRITY'
