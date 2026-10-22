"""Exact retained-input replay for the installed conditional reasoning paths."""
from copy import deepcopy
from pathlib import Path

from legalmath.prospectus.successor import service, explanations
from scripts.prospectus_calendar_evidence import load, save, require
from scripts.prospectus_explanation_oracle import check, check_row
from scripts.prospectus_calendar_oracle import verify as calendar_check
from scripts.prospectus_agent_window_evidence import independent as notice_check
from scripts import prospectus_explanation_evidence as previous

BASE = 'docs/implementation/prospectus-execution-authority'
EXPLANATIONS = BASE + '/attempts/reasoning-corpus/attempt-008'
NOTICE = BASE + '/attempts/basf-office/attempt-003'
STAGES = ('corpus', 'original', 'calendar', 'notice', 'controls')


def same(actual, expected, label):
    require(actual == expected, 'Complete installed evidence differs: ' + label)


def products(root, cohort):
    if cohort == 'notice':
        return load(root / NOTICE / 'notice/common-products.json.gz'), None
    source = previous.ORIGINAL if cohort == 'original' else previous.CALENDAR
    cases = (load(root / previous.ORIGINAL / 'favorable-deposit-P4.json.gz')['payload']['cases']
             if cohort == 'original' else None)
    return load(root / source / 'common-products.json.gz'), cases


def records(root, cohort):
    source = NOTICE if cohort == 'notice' else EXPLANATIONS
    folder = root / source / cohort
    paths = sorted(p for p in folder.glob('*.json.gz') if p.name != 'common-products.json.gz')
    require(len(paths) == (21 if cohort == 'original' else 19), 'Missing original full records')
    return paths


def verify_record(ps, record, cohort):
    data, p4 = record['input'], record['P4']
    proofs = []
    calculations = 0
    for row in p4['payload']['question']['value']:
        proofs.append(check_row(row, data, ps['P1']['payload']['request']['bundle'], ps['P1']['payload']['graph']))
        for calculation in row.get('calendar_calculations', []):
            if calculation['status'] in {'YES', 'NO'}:
                (notice_check if 'operator' in calculation else calendar_check)(calculation)
                calculations += 1
    same(proofs, record['proofs' if cohort == 'notice' else 'verification'], cohort + ' proof')
    for mode in ('current', 'frozen'):
        answer = record['answers'][mode]
        require(answer['questions']['Q4'] == p4['payload']['question']
                and answer['mode'] == 'ASSISTED'
                and answer['assessment_mode'] == mode
                and answer['may_execute_transaction'] is False
                and answer['independent_legal_acceptance'] is False, 'Conditional result promoted or lost')
    return calculations


def replay(root, output, cohort):
    ps, cases = products(root, cohort)
    paths = records(root, cohort)
    arithmetic, rows = 0, []
    for path in paths:
        expected = load(path)
        data = expected['input']
        p4 = service.law_product(ps['P1'], ps['P3'], cases=cases, law_input=data)
        answers = {mode: service.consume({**ps, 'P4': p4}, root, mode=mode)
                   for mode in ('current', 'frozen')}
        actual = {**deepcopy(expected), 'P4': p4, 'answers': answers}
        # Verification fields are independently recalculated below, never used
        # as a substitute for executing either complete production consumer.
        same(actual, expected, cohort + '/' + path.name)
        arithmetic += verify_record(ps, actual, cohort)
        save(output / cohort / path.name, actual)
        rows.append({'case': path.name, 'full_record_equal': True})
    refused = []
    if cohort == 'original':
        selected = load(root / previous.ORIGINAL / 'cases-result.json')['cases']
        for item in selected:
            if item.get('status') != 'REJECTED':
                continue
            data = load(root / previous.ORIGINAL / (item['case'] + '-input.json.gz'))
            for optional in (False, True):
                supplied = {**data, **({'law_explanation': 'subset-minimal.v1'} if optional else {})}
                message = refusal(lambda: service.law_product(ps['P1'], ps['P3'], cases=cases, law_input=supplied))
                same(message, item['reason'], 'original refusal')
            refused.append(item['case'])
        require(len(refused) == 2, 'Missing original refusals')
    value = {'records': rows, 'complete_answers': 2 * len(rows),
             'independent_calendar_calculations': arithmetic, 'original_refusals': refused}
    save(output / (cohort + '-checks.json'), value)
    return value


def refusal(call):
    try:
        call()
    except ValueError as error:
        return str(error)
    raise ValueError('Expected actual refusal did not occur')


def controls(root, output):
    ps, _ = products(root, 'notice')
    original = load(root / NOTICE / 'notice/30-days.json.gz')
    base = original['input']
    expected = load(root / NOTICE / 'notice-evidence.json')['controls']
    actual = []
    for attack in ('operator', 'rule-identity', 'event', 'subject', 'source'):
        data = deepcopy(base)
        if attack == 'operator': data['calendar_facts'][1]['operator'] = 'LT'
        if attack == 'rule-identity':
            row = deepcopy(data['calendar_facts'][1]); row.update(id='different-rule', operator='GE')
            data['calendar_facts'].append(row)
        if attack == 'event': data['calendar_facts'][1]['event_id'] = 'different-event'
        if attack == 'subject': data['calendar_facts'][1]['instrument_id'] = 'different-bond'
        if attack == 'source': data['calendar_facts'][1]['source']['quote'] = 'forged'
        actual.append({'attack': attack, 'refused': refusal(
            lambda: service.law_product(ps['P1'], ps['P3'], law_input=data))})
    same(actual, expected, 'original notice refusal reasons')
    malformed = []
    for option in (None, False, True, 0, 1, {}, [], '', 'minimum-cardinality.v1'):
        for route in ('request', 'overlay'):
            data = {**deepcopy(base), 'law_explanation': option}
            call = (lambda: service.source_product({**ps['P1']['payload']['request'], **data}, root)) if route == 'request' else (
                lambda: service.law_product(ps['P1'], ps['P3'], law_input=data))
            reason = refusal(call)
            require('Unsupported law explanation' in reason, 'Wrong malformed-option failure')
            malformed.append({'option': option, 'route': route, 'reason': reason})
    expression = {'any': ['a', {'all': ['b', 'c']}]}
    observations = {'a': True, 'b': True, 'c': True}
    good = explanations.explain(expression, observations)
    require(check(expression, observations, good)['status'] == 'VERIFIED', 'Invalid forgery baseline')
    attacks = []
    for attack in ('insufficient', 'nonminimal', 'missing-witness', 'wrong-witness',
                   'invented', 'wrong-status', 'wrong-identity', 'extra'):
        bad = deepcopy(good)
        if attack == 'insufficient': bad['literals'].pop('b'); bad['deletion_counterexamples'].pop('b')
        if attack == 'nonminimal':
            bad['literals']['a'] = True
            bad['deletion_counterexamples']['a'] = {'a': False, 'b': False, 'c': False}
        if attack == 'missing-witness': bad['deletion_counterexamples'].pop('b')
        if attack == 'wrong-witness': bad['deletion_counterexamples']['b'] = observations
        if attack == 'invented': bad['literals']['b'] = False
        if attack == 'wrong-status': bad['conclusion'] = 'NO'
        if attack == 'wrong-identity': bad['expression_sha256'] = '0' * 64
        if attack == 'extra': bad['verified_legal_truth'] = True
        attacks.append({'attack': attack, 'input': bad,
                        'reason': refusal(lambda: check(expression, observations, bad))})
    bad = deepcopy(original['P4'])
    bad['payload']['question']['value'][0]['explanation']['authority_source']['quote'] = 'forged'
    bad['sha256'] = service.digest({k: v for k, v in bad.items() if k != 'sha256'})
    consumer = refusal(lambda: service.consume({**ps, 'P4': bad}, root, mode='current'))
    require('differs; reassessment' in consumer, 'Wrong forged-output consumer failure')
    oracle = refusal(lambda: check_row(bad['payload']['question']['value'][0], base,
        ps['P1']['payload']['request']['bundle'], ps['P1']['payload']['graph']))
    boundaries = []
    for size in (12, 13):
        expression = {'all': ['f' + str(i) for i in range(size)]}
        observations = {n: True for n in expression['all']}
        result = explanations.explain(expression, observations)
        verified = check(expression, observations, result)
        require(verified['status'] == ('VERIFIED' if size == 12 else 'NOT_AVAILABLE'), 'Wrong domain boundary')
        boundaries.append({'facts': size, 'explanation': result, 'verification': verified})
    for engine, active, reason in (('z3', True, 'UNSUPPORTED_ENGINE'), ('finite', False, 'INACTIVE_AUTHORITY')):
        result = explanations.explain('a', {'a': True}, engine=engine, authority_active=active)
        verified = check('a', {'a': True}, result, engine=engine, active=active)
        require(verified == {'status': 'NOT_AVAILABLE', 'reason': reason}, 'Wrong unavailable boundary')
        boundaries.append({'engine': engine, 'active': active, 'explanation': result, 'verification': verified})
    value = {'notice': actual, 'malformed_options': malformed, 'proof_forgeries': attacks,
             'repinned_forgery': {'P4': bad, 'current_consumer': consumer, 'independent_checker': oracle},
             'boundaries': boundaries}
    save(output / 'controls.json', value)
    return {'notice_refusals': len(actual), 'malformed_options': len(malformed),
            'proof_forgeries': len(attacks), 'repinned_forgery_refusals': 2, 'domain_engine_boundaries': len(boundaries)}


def evaluate(root, output, stage):
    root, output = Path(root), Path(output)
    if stage == 'corpus':
        result = previous.corpus(root, output)
        same(load(output / 'corpus.json.gz'), load(root / EXPLANATIONS / 'corpus.json.gz'), '4096 complete corpus records')
        return result
    if stage in ('original', 'calendar', 'notice'):
        return replay(root, output, stage)
    require(stage == 'controls', 'Unknown installed reasoning stage')
    return controls(root, output)


def verify_retained(root, output):
    corpus = load(output / 'corpus.json.gz')
    same(corpus, load(root / EXPLANATIONS / 'corpus.json.gz'), 'corpus seal')
    for case in corpus['cases']:
        same(check(corpus['expressions'][case['expression']], case['observations'], case['explanation']),
             case['verification'], 'independent corpus check')
    full, arithmetic = 0, 0
    for cohort in ('original', 'calendar', 'notice'):
        ps, _ = products(root, cohort)
        expected = records(root, cohort)
        same(sorted(p.name for p in (output / cohort).glob('*.json.gz')),
             sorted(p.name for p in expected), 'complete retained denominator')
        for path in expected:
            record = load(output / cohort / path.name)
            same(record, load(path), 'full retained record')
            arithmetic += verify_record(ps, record, cohort)
            full += 2
    require(full == 118, 'Incomplete installed full answers')
    return {'independent_corpus_cases': len(corpus['cases']), 'complete_answers': full,
            'independent_calendar_calculations': arithmetic}
