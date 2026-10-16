"""Three finite protocol controls and two independent conditional-review controls."""
from copy import deepcopy
from pathlib import Path
from scripts.legal_integration_master import ROOT, BASE, PROGRAM, TOKENIZER
from scripts.legal_integration_account_repair import WORK, AUDIT, C
from scripts.legal_mission_execution import read, ref, verify, require
from scripts.legal_integration_reopening_live import fixture
from legalmath.interpretation.assurance.bounded_context import Limits, tokenizer
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased import account_contract, account_input
from legalmath.interpretation.assurance.phased.controls import control_answers
from legalmath.interpretation.assurance.phased.evidence_store import save_exact


def check_account(product, request, value, case):
    account_contract.validate(value, product, request['records'])
    require(len(value['considered']) == len(set(value['considered'])) and
        set(value['considered']) == set(request['required_considered']), 'Lost account assignment')
    if case['name'] == 'largest-actual':
        return
    require(value['conclusion'].startswith(case['expected']), 'Wrong conditional consequence')
    cited = {c['record_id'] for c in value['support'] + value['contrary']}
    require(set(case['operative_source_ids']) <= cited, 'Operative duty/exception not cited')
    if case['name'] == 'near-cap-missing':
        require(len(value['alternatives']) >= 2 and value['unresolved'], 'Missing conditional alternatives')
        require('schedule z' in ' '.join(value['unresolved']).lower(), 'Missing authority limitation lost')


def qualify_accounts(service):
    from scripts.legal_integration_phased_live import phase_admit
    correction = read(ROOT / PROGRAM).get('response_schema_repair')
    work = WORK
    if correction:
        from scripts.legal_integration_schema_repair import WORK as work
    lossless = read(ROOT / PROGRAM).get('lossless_account_repair')
    if lossless:
        from scripts.legal_integration_lossless_repair import WORK as work
    inputs = read(ROOT / work / 'qualification-inputs.json')
    response_schema = account_contract.provider_schema() if correction else account_contract.schema()
    rows = []
    for case in inputs['cases']:
        for k in ('request', 'envelope'):
            verify(ROOT, case[k])
        directory = ROOT / work / 'live/account-qualification' / case['name']
        product = PhasedProduct(ROOT, directory, service, read(ROOT / case['envelope']['path']),
            tokenizer(ROOT / TOKENIZER), limits=Limits(), maximum_calls=1,
            phase_admit=phase_admit('account-qualification-' + case['name']),
            phase_identity=ref(ROOT, BASE / 'current-binding.json')['sha256'],
            requirement_account_profile=account_contract.PROFILE,
            requirement_account_input_profile=account_input.PROFILE)
        request = read(ROOT / case['request']['path'])
        measurement = product.dispatch.measure(request, response_schema)
        require(measurement == case['measurement'], 'Qualification measurement changed')
        phase = product.run_phase('account-protocol', [{'key': 'account-protocol', 'request': request,
            'schema': response_schema, 'validate': lambda value, p=product, r=request, c=case:
                check_account(p, r, value, c)}])
        result = phase['results'][0]['result'] if phase['results'] else phase['resource_refusal']
        rows.append({'name': case['name'], 'result': result, 'measurement': measurement,
                     'passed': result['status'] == 'VALIDATED'})
        save_exact(ROOT / work / 'live/account-qualification/progress.json', {'rows': rows, 'complete': False})
    passed = all(r['passed'] for r in rows)
    save_exact(ROOT / work / 'live/account-qualification/result.json', {'rows': rows, 'qualified': passed,
        'complete': True, 'logical_call_ceiling': 3,
        'scope': 'Live account protocol and declared synthetic consequences; real legal entailment remains for original answer review.'})
    return {'qualification': ref(ROOT, work / 'live/account-qualification/result.json'),
        '_node_status': 'SUCCEEDED' if passed else 'BLOCKED',
        '_conclusion': 'Account input protocol ' + ('qualified for named recovery.' if passed else 'failed; preserve exact failed control.')}


def qualify_reviewer(service):
    from scripts.legal_integration_phased_live import session
    correction = read(ROOT / PROGRAM).get('response_schema_repair')
    work = WORK
    if correction:
        from scripts.legal_integration_schema_repair import WORK as work
    revision = read(ROOT / PROGRAM)['route_context_repair']
    verify(ROOT, revision['qualification_replay'])
    retained = read(ROOT / revision['qualification_replay']['path'])
    require(retained['valid'] and retained['unsupported_rejected'], 'Invalid prior controls')
    for pointer in retained['evidence']:
        verify(ROOT, pointer)
    envelope = fixture(False, explicit_scope=True, missing_authority=True)
    product = session(ROOT / work / 'live/reviewer-qualification', service,
        owner='conditional-review-qualification', envelope=envelope, maximum_calls=1 if correction else 2)
    records = [r for r in product.route.records.values() if r['kind'] == 'source']
    rows = {}
    positive_replay = None
    if correction:
        from jsonschema import validate as validate_schema
        from legalmath.interpretation.assurance.phased import group_review
        verify(ROOT, correction['positive_replay'])
        positive_replay = read(ROOT / correction['positive_replay']['path'])
        require(positive_replay['positive_passed'], 'Retained positive control failed')
        for pointer in positive_replay['evidence']:
            verify(ROOT, pointer)
        old_request = read(ROOT / positive_replay['request']['path'])
        old_result = read(ROOT / positive_replay['result']['path'])
        validate_schema(old_result['value'], read(ROOT / positive_replay['schema']['path']))
        decisions = group_review.validate(product, 'p14', old_result['value'],
            old_request['required_considered'], old_request['records'])
        require(old_result['status'] == 'VALIDATED' and
            all(row['decision']['verdict'] == 'ACCEPT' for row in decisions.values()), 'Positive replay failed')
    for label, answer in control_answers(records, missing=True):
        if correction and label == 'supported':
            continue
        rows[label] = product.audit_answer('p14', envelope['original_questions'][0], answer, [], prefix=label + '-')
    positive = bool(positive_replay) if correction else bool(rows['supported']) and all(
        r['status'] == 'VALIDATED' and r['value']['verdict'] == 'ACCEPT' for r in rows['supported'])
    negative = any(r['status'] == 'VALIDATED' and r['value']['verdict'] in ('REJECT', 'UNRESOLVED')
        for r in rows['unsupported'])
    passed = positive and negative
    save_exact(ROOT / work / 'live/reviewer-qualification/result.json', {'reviews': rows,
        'qualified': passed, 'positive_passed': positive, 'negative_passed': negative,
        'logical_call_ceiling': 1 if correction else 2, 'positive_replay': positive_replay,
        'retained_controls': revision['qualification_replay'],
        'scope': 'Fresh conditional-review scope control; old rejected response unchanged.'})
    return {'qualification': ref(ROOT, work / 'live/reviewer-qualification/result.json'),
        '_node_status': 'SUCCEEDED' if passed else 'BLOCKED',
        '_conclusion': 'Conditional reviewer ' + ('qualified on positive/adverse controls.' if passed else 'still fails; account preparation remains independent.')}
