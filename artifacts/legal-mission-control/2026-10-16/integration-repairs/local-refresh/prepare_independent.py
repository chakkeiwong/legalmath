"""Authenticate retained failures and prepare source-grounded evaluation cases."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from scripts.legal_mission_execution import read, save, ref, require
from scripts.legal_integration_accounts import SOURCE, conditional_account
from scripts.legal_integration_master import BASE, DOC, QUESTIONS, TOOLS

work = Path(__file__).resolve().parent
ledger_before = ref(ROOT, BASE / 'live-calls.json')
ledger = read(ROOT / ledger_before['path'])
slots = {2285: ('gatecoin', 'reduce-gatecoin-0-69', 'provider_refusal'),
         2341: ('p14', 'reduce-p14-0-6', 'unknown_request_parameter'),
         2356: ('p14', 'reduce-p14-0-21', 'unknown_cancellation_source'),
         2357: ('p14', 'reduce-p14-0-22', 'gateway_timeout'),
         2358: ('p14', 'reduce-p14-0-23', 'unknown_cancellation_source'),
         2359: ('p14', 'reduce-p14-0-24', 'bad_gateway')}
failures = []
for directory in sorted((ROOT / BASE / 'provider-evidence').iterdir()):
    slot = int(directory.name.split('-')[0])
    if slot not in slots:
        continue
    manifest = read(directory / 'manifest.json')
    require(manifest['allowance_slot'] == slot and not manifest['complete_output_present'],
            'Failure receipt is not the declared no-output request')
    require(ledger['calls'][slot-1]['request_hash'] == manifest['request_hash'], 'Wrong ledger receipt')
    for name, record in manifest['files'].items():
        data = (directory / name).read_bytes()
        require(len(data) == record['bytes'] and hashlib.sha256(data).hexdigest() == record['retained_sha256'],
                'Changed provider evidence: ' + name)
    events = [json.loads(line) for line in (directory / 'events.jsonl').read_text().splitlines() if line.strip()]
    require(any(e.get('type') == 'turn.failed' for e in events)
            and not any(e.get('type') == 'turn.completed' for e in events), 'Not a terminal failed turn')
    question, key, classification = slots[slot]
    failures.append(dict(slot=slot, question=question, key=key, classification=classification,
        request_hash=manifest['request_hash'], receipt=ref(ROOT, directory / 'manifest.json'),
        schema=ref(ROOT, directory / 'schema.json'), events=ref(ROOT, directory / 'events.jsonl'),
        messages=[e['message'] for e in events if e.get('type') == 'error'],
        charged_utc=datetime.fromtimestamp(int(ledger['calls'][slot-1]['issued_at_ns'])/1e9, timezone.utc).isoformat(),
        local_termination_record_present=(directory / 'termination.json').exists(),
        automatic_retry_authorized=False))
require({r['slot'] for r in failures} == set(slots), 'Missing failure receipt')
save(work / 'provider-diagnostics.json', dict(profile='retained-provider-diagnosis.v1',
    model='gpt-6.1-sol', failures=failures, provider_calls=0,
    resolution_needed={
        'provider_refusal': 'Legitimate provider explanation/review; preserve refused request. No evasive redispatch.',
        'unknown_request_parameter': 'Provider diagnostic naming the rejected parameter, or a reproduced contract defect.',
        'unknown_cancellation_source': 'Gateway/client trace identifying cancellation source; no local termination recorded.',
        'gateway_timeout': 'Classify no-output 504 consistently; service requalification remains separate.',
        'bad_gateway': 'Usable shared service and a bounded reviewed continuation; do not clear the old circuit.'},
    sent_to_provider=False, ledger=ledger_before))

envelope = read(ROOT / SOURCE)
mission = read(ROOT / DOC / 'mission.json')
require(len(mission['original_obligation_ids']) == 46 and len(mission['original_reading_ids']) == 35,
        'Original scope changed')
accounts = {}
for question in QUESTIONS:
    account = conditional_account(question, envelope)
    # conditional_account verifies each exact quotation against the retained source.
    save(work / ('conditional-' + question + '.json'), account)
    accounts[question] = ref(ROOT, work / ('conditional-' + question + '.json'))

cases = {
    'p10': [
        ('outsourcing', 'Responsibility remains despite outsourcing.', 'Do not infer adequate performance from appointment.'),
        ('diligent_but_defective', 'Separate the responsibility-allocation reading from an outcome requirement.', 'Do not choose a universal liability or cure rule.'),
        ('unknown_fulfillment', 'List the missing terms, rights, powers and incident facts conditionally.', 'Unknown performance is not compliance.')],
    'evidence': [
        ('independent_correct_records', 'Assess rights, provenance and proper-record duties in addition to agreement.', 'Agreement alone does not establish title.'),
        ('common_error', 'Both records can agree and identify the wrong owner.', 'Reject the sufficiency shortcut even if its Boolean/XML encoding passes.'),
        ('unknown_title', 'Keep the ownership and record-constitution questions explicit.', 'Do not use missing evidence as a false premise.')],
    'p14': [
        ('no_request_rivals', 'Retain main-text conditional and footnote standing-demonstration readings.', 'Vacuous truth does not establish confirmation or SFC satisfaction.'),
        ('request_and_inadequate', 'Requested demonstration can fail on the declared reading.', 'Audit existence does not substitute for scoped adequacy.'),
        ('audit_v1_deployed_v2', 'Require a justified bridge from the audit to deployed version and scope.', 'High confidence alone does not establish reliance or regulatory satisfaction.'),
        ('unknown_request', 'Retain both request branches and separate paragraphs 15 and 16.', 'Unknown is not absence of a request.')],
    'gatecoin': [
        ('category_one_to_four', 'Apply only the scoped defeasible NCC direction to stipulated category facts.', 'Property capable of trust is not an actual trust finding.'),
        ('contrary_access', 'Access/use evidence defeats the default under the direction.', 'Defeat of NCC default does not prove the opposite classification.'),
        ('unknown_category', 'Keep category, terms, date, parties and record roles conditional.', 'Do not transplant a liquidation-specific rule to Product Providers.'),
        ('scenario_seven', 'Expose the reasons/disposition tension and missing authoritative clarification.', 'Do not choose a priority merely to make a solver run.')],
}
mechanisms = {
    'bm25': 'Inspect exact-question passage selection, omissions and answer use with equal full-source access.',
    'legalruleml': 'Inspect Boolean AST preservation and mutations; source-to-rule warrant remains explicit.',
    'logical-english': 'Inspect restricted Boolean translation and unknown/unsupported handling.',
    'pyarg': 'Inspect grounded/preferred consequences of supplied warrants and adverse attacks.',
    'carneades': 'Inspect the installed adapter on the same effective arguments and defeats.',
    'clingo': 'Inspect stable extensions, ambiguity and missing premises on the same effective graph.',
}
rows = []
for question in QUESTIONS:
    for tool in TOOLS:
        native = BASE / ('native-' + tool) / 'attempt-4/native.json'
        require((ROOT / native).is_file(), 'Missing retained native trial')
        rows.append(dict(question=question, tool=tool, source_account=accounts[question],
            native_evidence=ref(ROOT, native), mechanism=mechanisms[tool],
            cases=[dict(id=name, expected_answer_treatment=expected, promotion_veto=veto)
                   for name, expected, veto in cases[question]],
            prerequisites=['successful acquire-' + question, 'current source/warrant and tool-target validation',
                           'actual final-answer/review packet capacity', 'valid service/binding/finite allocation'],
            comparator='Same question, complete source/account population, provider route and answer/review criteria; tool feedback is the treatment.',
            effect_decisions=['helps', 'no observed benefit', 'harmful', 'limited/unsupported', 'inconclusive'],
            primary_criterion='Actual answer considers the delivered feedback and preserves supported/contrary source distinctions.',
            evaluation_status='PREPARED_NOT_EXECUTED', statistical_ranking_supported=False))
save(work / 'evaluation-cases.json', dict(profile='integration-matched-case-preparation.v1',
    source=ref(ROOT, SOURCE), accounts=accounts, pairs=rows,
    original_obligation_ids=mission['original_obligation_ids'], original_reading_ids=mission['original_reading_ids'],
    answer_effects_evaluated=0, provider_calls=0,
    limit='Prepared conditional cases and existing native evidence are not new complete answers or matched tool effects.'))
require(ref(ROOT, BASE / 'live-calls.json') == ledger_before, 'Preparation changed provider ledger')
save(work / 'independent-result.json', dict(verdict='PASS', provider_calls=0,
    ledger_unchanged=True, failure_receipts=len(failures), conditional_accounts=len(accounts),
    question_tool_pairs=len(rows), original_obligations=46, original_readings=35,
    evidence=[ref(ROOT, work / name) for name in ('provider-diagnostics.json', 'evaluation-cases.json')],
    legal_acceptance=False, tool_effects_evaluated=False))
print({'verified_failure_receipts': len(failures), 'conditional_accounts': len(accounts),
       'prepared_pairs': len(rows), 'provider_calls': 0})
