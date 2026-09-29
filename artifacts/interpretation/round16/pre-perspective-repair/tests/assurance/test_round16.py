from copy import deepcopy
from pathlib import Path
import json
import subprocess
import sys

import pytest

from legalmath.canonical import digest, raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import fidelity_v2 as fv
from legalmath.interpretation.assurance import temporal_inputs as ti
from legalmath.interpretation.assurance import editions
from legalmath.java import decimal_boundary as db
from .support import packet, inventory, reading, fidelity
from legalmath.interpretation.assurance.semantics import representation

ROOT = Path(__file__).resolve().parents[2]
AT = '2026-09-26T00:00:00.000000Z'
EARLY = '2026-01-29T03:00:00.000000Z'
CUTOFF = '2026-01-29T04:00:00.000000Z'
LATE = '2026-01-29T05:00:00.000000Z'
START = '2026-01-28T00:00:00.000000Z'
JDK = ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1'


def scoped_fixture():
    p = packet(); claims = inventory()['claims']; candidates = {'candidate': reading()}
    q = {'control_id': 'gift.question', 'question': 'Is this gift prohibited?',
         'unit_of_assessment': 'One gift', 'actor': 'Distributor', 'temporal_basis': 'Assessment instant',
         'result_kind': 'PROHIBITED', 'true_means': 'Gift prohibited', 'false_means': 'Gift not prohibited',
         'source_evidence': deepcopy(claims[0]['evidence'])}
    evidence = deepcopy(claims[0]['evidence'])
    row = {'claim_id': claims[0]['claim_id'], 'candidate_id': 'candidate',
           'source_support': {'status': 'SUPPORTED', 'evidence': evidence, 'rationale': 'Source supports the gift restriction.'},
           'question_relation': {'status': 'RELEVANT', 'question_hash': digest(q), 'evidence': evidence,
                                 'rationale': 'Restriction answers this gift question.'},
           'executable_correspondence': {'status': 'PRESERVES', 'representation_quotes': [representation(candidates['candidate'])],
                                         'rationale': 'The supplied formula includes the exception.'},
           'authority': {'status': 'NONE_DECLARED', 'dependency_ids': [], 'rationale': 'No incorporated dependency in this fixture.'},
           'followup_questions': []}
    return p, claims, candidates, {'candidate': q}, {'checks': [row], 'additional_concerns': []}


def test_separate_advertising_duty_is_retained_without_fabricating_code_failure():
    p, claims, candidates, questions, response = scoped_fixture()
    text = 'Advertisements must state the charges.'
    p['units'].append({'unit_id': 'ad', 'text': text, 'locator': 'separate paragraph', 'normative': True, 'span': None})
    claims[0].update(statement=text, relevance='CONTEXT', evidence=[{'unit_id': 'ad', 'quote': text}])
    row = response['checks'][0]
    for key in ('source_support', 'question_relation'): row[key]['evidence'] = claims[0]['evidence']
    row['question_relation'].update(status='NOT_APPLICABLE_TO_THIS_QUESTION', rationale='Advertisements are separately assessed; this rule assesses a gift.')
    row['executable_correspondence'].update(status='NOT_APPLICABLE', representation_quotes=[], rationale='No encoding is proposed for this separate question.')
    assert len(fv.request(p, claims, candidates, questions)['required_pairs']) == 1
    result = fv.validate(response, p, claims, candidates, questions)
    combined = fv.reconcile([result, result], attempt=1)
    assert combined['status'] == 'PROPOSED_JUDGMENTS_AGREE' and combined['pruned_pairs'] == []


def test_relevant_omitted_exception_and_wrongly_extracted_footnote_remain_distinct():
    p, claims, candidates, questions, response = scoped_fixture()
    row = response['checks'][0]
    row['executable_correspondence'].update(status='OMITS', representation_quotes=[], rationale='The selected expression omits the exception.')
    candidates['candidate'] = reading(True)
    diagnosed = fv.validate(response, p, claims, candidates, questions)
    assert fv.reconcile([diagnosed, diagnosed], attempt=1)['status'] == 'REPAIR_REQUESTED'
    p['units'].append({'unit_id': 'footnote3', 'text': 'A Hongkong Post e-Cert is required.', 'locator': 'Footnote 3', 'normative': True, 'span': None})
    claims[0]['statement'] = 'No e-Cert is required.'
    row['source_support'].update(status='CONTRADICTED', evidence=[{'unit_id': 'footnote3', 'quote': p['units'][-1]['text']}])
    row['executable_correspondence'].update(status='UNASSESSED')
    diagnosed = fv.validate(response, p, claims, candidates, questions)
    assert diagnosed['checks'][0]['source_support']['status'] == 'CONTRADICTED'
    assert diagnosed['checks'][0]['executable_correspondence']['status'] == 'UNASSESSED'


def test_missing_authority_is_not_available_because_formula_matches():
    p, claims, candidates, questions, response = scoped_fixture()
    row = response['checks'][0]; row['authority'].update(status='MISSING', dependency_ids=['amlo.section53zra'])
    assert fv.validate(response, p, claims, candidates, questions)
    row['authority']['status'] = 'AVAILABLE'
    with pytest.raises(LegalMathError): fv.validate(response, p, claims, candidates, questions)


def test_relational_disagreement_preserves_proposals_until_budget_then_reports():
    p, claims, candidates, questions, first = scoped_fixture()
    second = deepcopy(first); row = second['checks'][0]
    row['question_relation']['status'] = 'NOT_APPLICABLE_TO_THIS_QUESTION'
    row['executable_correspondence']['status'] = 'NOT_APPLICABLE'
    for value in (first, second): fv.validate(value, p, claims, candidates, questions)
    assert fv.reconcile([first, second], attempt=1)['additional_processing_required']
    end = fv.reconcile([first, second], attempt=3)
    assert end['status'] == 'UNCERTAINTY_REPORTED' and end['proposals'] == [first, second]
    assert not end['additional_processing_required'] and end['pruned_pairs'] == []


def test_legacy_migration_does_not_invent_separate_judgments():
    p, claims, candidates, questions, _ = scoped_fixture()
    row = fidelity(claims, candidates)['checks'][0]
    new = fv.migrate_legacy(row, provenance={'source': 'fixture'})
    assert new['legacy'] == row and set(new['dimensions'].values()) == {'UNASSESSED'}
    row['rationale'] = 'changed'
    assert new['legacy']['rationale'] != 'changed'


@pytest.mark.parametrize('fault', ['stale_question', 'missing_pair', 'fabricated_quote', 'invalid_na', 'unsupported_preserves', 'wrong_polarity'])
def test_v2_rejects_invalid_scoped_proposals(fault):
    p, claims, candidates, questions, response = scoped_fixture(); row = response['checks'][0]
    if fault == 'stale_question': questions['candidate']['question'] = 'A different question'
    elif fault == 'missing_pair': response['checks'] = []
    elif fault == 'fabricated_quote': row['source_support']['evidence'][0]['quote'] = 'invented'
    elif fault == 'invalid_na': row['executable_correspondence']['status'] = 'NOT_APPLICABLE'
    elif fault == 'wrong_polarity':
        candidates['candidate']['statement'] = '[TRUE_IS_COMPLIANT] True means compliance.'
        row['executable_correspondence']['representation_quotes'] = [representation(candidates['candidate'])]
    else: row['source_support']['status'] = 'NOT_ESTABLISHED'
    with pytest.raises(LegalMathError): fv.validate(response, p, claims, candidates, questions)


def event(when=EARLY, *, ident='contact', subject='str.s', kind='CONTACT', recorded=None, related=None):
    return {'event_id': ident, 'str_id': subject, 'kind': kind, 'related_event_id': related,
            'occurred_at': when, 'recorded_at': recorded or when, 'status': 'CONFIRMED', 'evidence_ids': ['e.'+ident]}


def coverage(kind='CONTACT'):
    return [{'str_id': 'str.s', 'kinds': [kind], 'from_inclusive': START,
             'through_inclusive': CUTOFF, 'recorded_at': CUTOFF, 'evidence_ids': ['coverage.assertion']}]


def projected(events, covers=None, **kw):
    return ti.project(events, coverage() if covers is None else covers, str_id='str.s', kind='CONTACT',
                      since=START, assessment_at=CUTOFF, known_at=CUTOFF, **kw)


@pytest.mark.parametrize('ev,expected', [(event(), 'TRUE'), (event(CUTOFF), 'TRUE'), (event(LATE), 'FALSE'),
    (event(subject='str.other'), 'FALSE'), (event(recorded=LATE), 'FALSE')])
def test_contact_same_report_and_cutoff(ev, expected):
    assert projected([ev])['status'] == expected


def test_absence_needs_complete_visible_history_and_disputes_are_not_truth():
    assert projected([], [])['status'] == 'UNKNOWN'
    c = coverage(); c[0]['recorded_at'] = LATE
    assert projected([], c)['status'] == 'UNKNOWN'
    ev = event(); ev['status'] = 'DISPUTED'
    assert projected([ev])['status'] == 'CONFLICT'
    duplicate = event(LATE)
    with pytest.raises(LegalMathError, match='identity'): projected([event(), duplicate])


def test_future_history_cannot_be_certified_in_advance():
    c = coverage(); c[0]['recorded_at'] = EARLY
    with pytest.raises(LegalMathError): projected([], c)
    with pytest.raises(LegalMathError): projected([event(LATE, recorded=EARLY)])


def test_resubmission_needs_attributed_original_and_event_link():
    original = event(START, ident='original', kind='ORIGINAL_SUBMISSION')
    later = event(EARLY, ident='resubmit', kind='RESUBMISSION', related='original')
    def assess(ev): return ti.project(ev, coverage('RESUBMISSION'), str_id='str.s', kind='RESUBMISSION',
        since=START, assessment_at=CUTOFF, known_at=CUTOFF, original_event_id='original')
    assert assess([original, later])['status'] == 'TRUE'
    assert assess([later])['status'] == 'UNKNOWN'
    assert assess([original])['status'] == 'FALSE'
    wrong = deepcopy(later); wrong['related_event_id'] = 'other'
    assert assess([original, wrong])['status'] == 'FALSE'
    original['str_id'] = 'str.other'
    with pytest.raises(LegalMathError): assess([original, later])


def test_historical_bundle_not_backdated_and_trigger_never_becomes_performance():
    args = {'bundle_interval': {'valid_from': AT, 'valid_until': None}, 'source_interval': None,
            'documents': {}, 'assessment_at': CUTOFF, 'known_at': AT}
    assert ti.context(**args)['status'] == 'BUNDLE_TIME_UNSUPPORTED'
    args['assessment_at'] = AT
    assert ti.context(**args)['status'] == 'SOURCE_EFFECTIVENESS_UNKNOWN'
    result = ti.trigger_and_performance({'status': 'TRUE', 'value': True}, None)
    assert result['status'] == 'PERFORMANCE_UNENCODED' and result['overall_compliance'] == 'NOT_ESTABLISHED'


def rational_bundle():
    return json.loads((ROOT/'artifacts/interpretation/round15/phase-results.json').read_bytes())['P5']['result']['rational_extension']['cases'][0]['bundle']


def decimal_request(value='10', objective=False):
    def known(typ, val): return {'type': typ, 'status': 'known', 'value': val, 'valid_from': AT,
        'valid_until': None, 'recorded_at': AT, 'evidence_ids': ['host.evidence']}
    return {'profile': db.PROFILE, 'subject_id': 'host.s', 'mode': 'draft', 'valid_at': AT, 'known_at': AT,
        'facts': {'fund_manager': known('bool', True), 'va_objective': known('bool', objective),
                  'intended_va_percent': known('decimal_percent', value)}}


@pytest.fixture(scope='module')
def percent_jar(tmp_path_factory):
    return db.build(rational_bundle(), tmp_path_factory.mktemp('percent-java'), JDK, profile=db.PROFILE)


@pytest.mark.parametrize('value,objective,status', [('9.999', False, 'FALSE'), ('10', False, 'TRUE'),
    ('10.001', False, 'TRUE'), ('9.999999999999', False, 'FALSE'), ('10.000000000001', False, 'TRUE'),
    ('0', True, 'TRUE'), ('0', False, 'FALSE'), ('-0.000', False, 'FALSE'), ('-1', False, 'FALSE'),
    ('9.'+'9'*62, False, 'FALSE'), ('10.'+'0'*60+'1', False, 'TRUE')])
def test_packaged_java_exact_decimal_cases(percent_jar, value, objective, status):
    request = decimal_request(value, objective); actual = db.run(percent_jar, [request], JDK)[0]
    reference = db.evaluate_request(rational_bundle(), request)
    assert actual['boundary_status'] == reference['boundary_status'] == 'ACCEPTED'
    assert actual['result']['status'] == reference['result']['status'] == status
    assert actual['snapshot'] == reference['snapshot']
    assert int(actual['snapshot']['facts']['va_bps_denominator']['value']) > 0


@pytest.mark.parametrize('value', ['1e1', 'NaN', 'Infinity', '+10', '01', ' 10', '10.', '.1', '1,0',
                                  '1'*65, True, 10, '１０'])
def test_packaged_java_rejects_malformed_decimal(percent_jar, value):
    request = decimal_request(value)
    assert db.run(percent_jar, [request], JDK)[0]['boundary_status'] == 'REJECTED'


def test_packaged_java_missing_conflict_bypass_and_float(percent_jar):
    requests = []
    missing = decimal_request(); missing['facts'].pop('intended_va_percent'); requests.append(missing)
    conflict = decimal_request(); conflict['facts']['intended_va_percent'] = {
        'type': 'decimal_percent', 'status': 'conflict', 'evidence_ids': ['a', 'b']}; requests.append(conflict)
    for denominator in ('0', '-1', '1.5', '01'):
        bypass = decimal_request(); bypass['facts']['va_bps_denominator'] = {'type': 'integer', 'status': 'known', 'value': denominator}
        requests.append(bypass)
    wrong = decimal_request(); wrong['snapshot'] = {}; requests.append(wrong)
    actual = db.run(percent_jar, requests, JDK)
    assert [r['result']['status'] for r in actual[:2]] == ['UNKNOWN', 'CONFLICT']
    assert all(r['boundary_status'] == 'REJECTED' for r in actual[2:])
    # A float must reach Java, not merely be rejected by Python canonical JSON.
    raw = decimal_request(10.0)
    p = subprocess.run([str(JDK/'bin/java'), '-jar', percent_jar['jar']], input=json.dumps(raw)+'\n',
                       text=True, capture_output=True, check=True, timeout=30)
    assert json.loads(p.stdout)['boundary_status'] == 'REJECTED'


def edition_fixture(tmp_path):
    pdf = tmp_path/'source.pdf'; pdf.write_bytes(b'locked fixture bytes')
    pages = ['clean definition\nfootnote qualifies it', 'notice qualification', 'deleted definition replacement definition']
    def prov(ident, edition, page, start, end, links, relationship):
        return {'provision_id': ident, 'edition_id': edition, 'page': page, 'start': start, 'end': end,
                'quote': pages[page-1][start:end], 'required_links': links, 'relationship': relationship}
    manifest = {'source_sha256': raw_digest(pdf.read_bytes()), 'page_hashes': [raw_digest(p.encode()) for p in pages],
        'editions': [{'edition_id': 'clean', 'kind': 'CLEAN', 'first_page': 1, 'last_page': 2, 'printed_edition': '2023'},
                     {'edition_id': 'changes', 'kind': 'MARKED_CHANGES', 'first_page': 3, 'last_page': 3, 'printed_edition': '2019 2023'}],
        'provisions': [prov('definition', 'clean', 1, 0, 16, ['footnote', 'notice'], 'SECTION'),
                       prov('footnote', 'clean', 1, 17, len(pages[0]), [], 'FOOTNOTE'),
                       prov('notice', 'clean', 2, 0, len(pages[1]), [], 'CONTINUATION'),
                       prov('marked', 'changes', 3, 0, len(pages[2]), [], 'SECTION')],
        'structural_review': 'Synthetic provenance test', 'unresolved_authority_questions': ['Effectiveness?']}
    return pdf, pages, manifest


@pytest.mark.parametrize('fault', ['cross_edition', 'missing_footnote', 'missing_notice', 'marked_active', 'changed_pdf', 'changed_text', 'stale_manifest'])
def test_edition_selection_rejects_contamination_and_lost_qualifications(tmp_path, fault):
    pdf, pages, manifest = edition_fixture(tmp_path); expected = digest(manifest)
    selected = ['definition', 'footnote', 'notice']; edition = 'clean'
    if fault == 'cross_edition': selected.append('marked')
    elif fault == 'missing_footnote': selected.remove('footnote')
    elif fault == 'missing_notice': selected.remove('notice')
    elif fault == 'marked_active': selected = ['marked']; edition = 'changes'
    elif fault == 'changed_pdf': pdf.write_bytes(b'changed')
    elif fault == 'changed_text': pages[0] += ' changed'
    else: manifest['structural_review'] = 'changed'
    with pytest.raises(LegalMathError): editions.select(pdf, pages, manifest, expected_manifest_hash=expected,
                                                       edition_id=edition, provision_ids=selected)


def test_edition_packet_retains_authority_uncertainty_and_revision_history(tmp_path):
    pdf, pages, manifest = edition_fixture(tmp_path)
    value = editions.select(pdf, pages, manifest, expected_manifest_hash=digest(manifest), edition_id='clean',
                            provision_ids=['definition', 'footnote', 'notice'])
    assert value['source_effectiveness'] == 'NOT_ESTABLISHED' and value['excluded_editions'][0]['edition_id'] == 'changes'
    assert value['packet']['dependencies'][0]['source_hash'] is None
    assert all('deleted' not in u['text'] for u in value['packet']['units'])


def master_fixture(monkeypatch, tmp_path):
    sys.path.insert(0, str(ROOT/'scripts'))
    import run_assurance_round16 as master
    monkeypatch.setattr(master, 'OUT', tmp_path)
    (tmp_path/'baseline.json').write_text('{}')
    monkeypatch.setattr(master, 'audit', lambda: {'status': 'FIXTURE_BASELINE'})
    version = {'code': 'v1'}
    monkeypatch.setattr(master, 'code_binding', lambda: dict(version))
    calls = []
    def run(phase, work):
        calls.append(phase)
        return {'status': 'PASS', 'output': {}, 'manifest': {'test_fixture': True}}
    monkeypatch.setattr(master, 'run_phase', run)
    return master, calls, version


def test_round16_master_resumes_and_binds_copied_predecessor_lists(monkeypatch, tmp_path):
    master, calls, version = master_fixture(monkeypatch, tmp_path)
    master.execute('N2'); assert calls == ['N0', 'N1', 'N2']
    master.execute('N2'); assert calls == ['N0', 'N1', 'N2']
    actions = master.journal().report()['actions']
    assert [len(a['spec']['inputs']['preceding']) for a in actions] == [0, 1, 2]
    version['code'] = 'v2'; master.execute('N2')
    assert calls == ['N0', 'N1', 'N2'] * 2
    assert len(master.journal().report()['actions']) == 6


def test_round16_master_repair_retains_failure_and_refreshes_next_phase(monkeypatch, tmp_path):
    master, calls, version = master_fixture(monkeypatch, tmp_path)
    original = master.run_phase; failed = []
    def run(phase, work):
        if phase == 'N1' and not failed:
            failed.append(True); (work/'failure.log').write_text('Retained diagnostic')
            return {'status': 'FAILED', 'output': None, 'manifest': {}}
        return original(phase, work)
    monkeypatch.setattr(master, 'run_phase', run)
    with pytest.raises(LegalMathError): master.execute('N2')
    next_plan = json.loads((tmp_path/'next-phase-plan.json').read_bytes())
    assert next_plan['repair_required']['phase'] == next_plan['next_phase'] == 'N1'
    master.execute('N2')
    actions = master.journal().report()['actions']
    assert [a['spec']['stage'] for a in actions] == ['n0', 'n1', 'n1', 'n2']
    assert (tmp_path/'execution/action-0001/failure.log').read_text() == 'Retained diagnostic'
    assert json.loads((tmp_path/'next-phase-plan.json').read_bytes())['repair_required'] is None


def test_round16_master_repair_does_not_reset_attempt_limit(monkeypatch, tmp_path):
    master, calls, version = master_fixture(monkeypatch, tmp_path)
    original = master.run_phase
    monkeypatch.setattr(master, 'run_phase', lambda p,w: {'status':'FAILED','output':None,'manifest':{}}
                        if p == 'N1' else original(p,w))
    for _ in range(3):
        with pytest.raises(LegalMathError): master.execute('N1')
    with pytest.raises(LegalMathError) as caught: master.execute('N1')
    assert caught.value.code == 'E_RESOURCE_LIMIT'
    assert len(master.journal().report()['actions']) == 4


class ScopedProvider:
    provider_id = 'local.scoped.fixture'
    live = False
    routing = {'provider': 'scripted', 'family': 'fixture-not-independent-evidence'}
    def __init__(self, responses):
        self.responses = responses; self.calls = []
    def complete(self, request, schema, settings):
        from legalmath.interpretation.search.providers import Completion
        self.calls.append(deepcopy(request))
        response = self.responses[min(len(self.calls)-1,len(self.responses)-1)]
        if isinstance(response, Exception): raise response
        return Completion(deepcopy(response), {'fixture': True, 'independence_established': False})


def test_scoped_investigation_executes_discrepancy_followups_and_preserves_uncertainty(tmp_path):
    from legalmath.interpretation.assurance.control_investigation import investigate_scoped
    p,c,r,q,first = scoped_fixture(); second = deepcopy(first)
    second['checks'][0]['question_relation']['status'] = 'NOT_APPLICABLE_TO_THIS_QUESTION'
    second['checks'][0]['executable_correspondence']['status'] = 'NOT_APPLICABLE'
    provider = ScopedProvider([first, second, first])
    result = investigate_scoped(p,c,r,q,provider,tmp_path,maximum_rounds=3)
    assert len(provider.calls) == result['journal_actions'] == 6
    assert result['status'] == 'UNCERTAINTY_REPORTED' and result['pruned_pairs'] == []
    assert len(result['batches'][0]['proposals']) == 6
    assert all(v['investigation']['prior_round_evidence'] is None for v in provider.calls[:2])
    assert provider.calls[2]['investigation']['prior_round_evidence']['disputes']
    resumed = investigate_scoped(p,c,r,q,provider,tmp_path,maximum_rounds=3)
    assert len(provider.calls) == 6 and resumed['batches'][0]['proposals'] == result['batches'][0]['proposals']


def test_scoped_investigation_missing_pair_is_repaired_by_another_call(tmp_path):
    from legalmath.interpretation.assurance.control_investigation import investigate_scoped
    p,c,r,q,value = scoped_fixture(); invalid = deepcopy(value); invalid['checks'] = []
    provider = ScopedProvider([invalid, value])
    result = investigate_scoped(p,c,r,q,provider,tmp_path,maximum_rounds=3)
    assert len(provider.calls) == 4
    assert result['status'] == 'PROPOSED_JUDGMENTS_AGREE' and result['pairs_with_two_validated_proposals'] == 1
    assert len(result['batches'][0]['diagnostics']) == 1
    assert provider.calls[2]['investigation']['prior_round_evidence']['diagnostics']
    assert (tmp_path/'model/action-0000/raw-response.json').is_file()


@pytest.mark.parametrize('prefix', [False, True])
def test_scoped_investigation_transport_failure_stops_resume_without_losing_valid_output(tmp_path, prefix):
    from legalmath.interpretation.assurance.control_investigation import investigate_scoped
    p,c,r,q,value = scoped_fixture(); error = LegalMathError('E_DEPENDENCY',details='overloaded')
    provider = ScopedProvider(([value] if prefix else [])+[error])
    first = investigate_scoped(p,c,r,q,provider,tmp_path)
    second = investigate_scoped(p,c,r,q,provider,tmp_path)
    assert len(provider.calls) == 1+int(prefix)
    assert first['status'] == second['status'] == 'DISPATCH_BLOCKED'
    assert first['batches'][0]['proposals'] == second['batches'][0]['proposals']


@pytest.mark.parametrize('change', ['question', 'source', 'settings'])
def test_scoped_investigation_source_question_and_settings_changes_invalidate_resume(tmp_path, change):
    from legalmath.interpretation.assurance.control_investigation import investigate_scoped
    from legalmath.interpretation.search.models import Settings
    p,c,r,q,value = scoped_fixture();provider = ScopedProvider([value])
    investigate_scoped(p,c,r,q,provider,tmp_path)
    args = {}
    if change == 'question': q['candidate']['question'] = 'Another gift question'
    elif change == 'source': p['selected_slice'] += ' changed'
    else: args['settings'] = Settings(timeout_seconds=123, max_input_bytes=200000, max_output_bytes=200000)
    with pytest.raises(LegalMathError): investigate_scoped(p,c,r,q,provider,tmp_path,**args)
    assert len(provider.calls) == 2


def test_scoped_investigation_accounts_for_all_batches_including_context(tmp_path):
    from legalmath.interpretation.assurance.control_investigation import investigate_scoped
    p,c,r,q,first = scoped_fixture();c[0]['relevance']='CONTEXT'
    r['second']=deepcopy(r['candidate']);q['second']=deepcopy(q['candidate'])
    second=deepcopy(first);second['checks'][0]['candidate_id']='second'
    provider=ScopedProvider([first,first,second,second])
    result=investigate_scoped(p,c,r,q,provider,tmp_path,batch_size=1)
    assert len(provider.calls)==4 and result['pairs_with_two_validated_proposals']==2
    assert result['required_pairs']==[['gift','candidate'],['gift','second']]
    assert result['pending_pairs']==result['pruned_pairs']==[]


def test_scoped_investigation_no_live_dispatch_and_persistent_action_budget(tmp_path):
    from legalmath.interpretation.assurance.control_investigation import investigate_scoped
    p,c,r,q,value = scoped_fixture(); provider = ScopedProvider([value]);provider.live=True
    with pytest.raises(LegalMathError): investigate_scoped(p,c,r,q,provider,tmp_path)
    assert not provider.calls
    provider.live=False
    first = investigate_scoped(p,c,r,q,provider,tmp_path,maximum_actions=1)
    second = investigate_scoped(p,c,r,q,provider,tmp_path,maximum_actions=1)
    assert len(provider.calls) == 1 and first['status'] == second['status'] == 'DISPATCH_BLOCKED'
    assert first['pending_pairs'] == second['pending_pairs'] == [['gift','candidate']]
