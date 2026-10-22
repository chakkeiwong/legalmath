"""Shared deterministic checks; executable with isolated installed Python."""
from copy import deepcopy
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

from legalmath.prospectus import basf_equity, basf_oci_notes, basf_hedge_note
from legalmath.prospectus.successor import service, basf_agent_report, basf_notices
from legalmath.prospectus.successor import basf_initial_agents as core
from legalmath.prospectus.successor.contracts import digest


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2).encode()
    with path.open('xb') as stream:
        stream.write(gzip.compress(raw, mtime=0) if str(path).endswith('.gz') else raw)


def finish(source, construction, baseline, interpretation=None):
    old3 = service.verify(baseline['P3'], 'P3')
    semantic = service.interpretation_product(source, construction,
        deepcopy(old3['interpretation_input']) if interpretation is None else interpretation)
    return complete(source, construction, baseline, semantic)


def complete(source, construction, baseline, semantic):
    """Build P4/P5 from an actual P3 without interpreting a second time."""
    service.verify(semantic, 'P3')
    old4, old5 = [service.verify(baseline[p], p) for p in ('P4', 'P5')]
    return {'P1': source, 'P2': construction, 'P3': semantic,
        'P4': service.law_product(source, semantic, old4['cases'], old4['law_input']),
        'P5': service.financial_product(source, construction, semantic,
            old5['cases'], old5['scenario_input'])}


def construct(baseline, root):
    old1, old2 = [service.verify(baseline[p], p) for p in ('P1', 'P2')]
    graph = old1['graph']
    request = core.prepare_request(graph, old2['assembly'], old1['request'])
    bundle = request['bundle']
    source = service.seal('P1', bundle, {'request': digest(request)}, {'request': request, 'graph': graph})
    provisional = service.construction_product(source, root)
    request['reference_admission']['assembly_sha256'] = digest(provisional['payload']['assembly'])
    source = service.seal('P1', bundle, {'request': digest(request)}, {'request': request, 'graph': graph})
    construction = service.construction_product(source, root)
    assert construction['payload'] == provisional['payload']
    return {'P1': source, 'P2': construction}


def candidate(baseline, root):
    built = construct(baseline, root)
    return finish(built['P1'], built['P2'], baseline)


def omission(products, baseline):
    return finish(products['P1'], products['P2'], products, omission_input(baseline))


def omission_input(baseline):
    interpretation = deepcopy(baseline['P3']['payload']['interpretation_input'])
    interpretation['clauses'] = deepcopy(baseline['P3']['payload']['clauses']['nodes'])
    return interpretation


def expected_questions(old):
    """Apply the admitted delta to every separately evaluated question."""
    expected = deepcopy(old['questions'])
    removed = {*core.INTRO_TEXT, core.UNKNOWN_ID}
    for q in ('Q1', 'Q2'):
        items = expected[q]['unresolved']
        assert removed <= set(items)
        expected[q]['unresolved'] = [x for x in items if x not in removed]
        expected['Q3']['value'][q]['unresolved'] = deepcopy(expected[q]['unresolved'])
    subquestions = expected['Q2']['subquestions']
    assert set(subquestions) == {'compulsory_common', 'possible_common', 'common_only'}
    for question in subquestions.values():
        items = question['unresolved']
        assert removed <= set(items)
        question['unresolved'] = [x for x in items if x not in removed]
    return expected


def compare_answers(old, new, products):
    """Require the complete question delta, rather than just equal status labels."""
    assert new['questions'] == expected_questions(old), 'Unexpected question change'
    changed = {'request_sha256', 'consumed_products', 'questions', 'basf_agents', 'meaning_coverage', 'report_sha256'}
    assert {k: v for k, v in old.items() if k not in changed} == {
        k: v for k, v in new.items() if k not in changed}, 'Outside ordinary answer changed'
    agents = deepcopy(old['basf_agents'])
    old_rows = {r['id']: r for r in agents['readings']}
    new_rows = {r['id']: r for r in new['basf_agents']['readings']}
    assert old_rows.keys() == new_rows.keys()
    assert all(old_rows[k] == new_rows[k] for k in old_rows if k != core.IDENTITY)
    initial = new_rows[core.IDENTITY]
    units = {u['unit']: u for u in products['P2']['payload']['assembly']['units']}
    spans = core.introduction_spans(units)
    expected_initial = deepcopy(old_rows[core.IDENTITY])
    expected_initial['reading']['appointment_wording'] = core.APPOINTMENT_WORDING
    expected_initial['quote'] = ' '.join(
        [units[s['unit']]['text'][s['start']:s['end']] for s in spans] + [expected_initial['quote']])
    expected_initial['source_spans'] = basf_agent_report._sources(
        products['P1']['payload']['graph'], units, spans) + expected_initial['source_spans']
    expected_initial['sources'] = [s for group in expected_initial['source_spans'] for s in group['sources']]
    assert initial == expected_initial, 'Unexpected initial-agent report change'
    agents['readings'] = deepcopy(new['basf_agents']['readings'])
    for row in agents['unresolved_context']:
        if row['unit'] in core.INTRO_TEXT:
            row['role'] = 'OPERATIVE'
    assert new['basf_agents'] == agents
    assert initial['actual_appointment_or_change'] == 'NOT_ESTABLISHED'
    assert new['basf_agents']['calculation_agent_office'] == 'UNRESOLVED'
    coverage = deepcopy(old['meaning_coverage'])
    coverage['assembly_sha256'] = digest(products['P2']['payload']['assembly'])
    coverage['clauses_sha256'] = digest(products['P3']['payload']['clauses'])
    spans = core.introduction_spans({u['unit']: u for u in products['P2']['payload']['assembly']['units']})
    counts = {s['unit']: sum(not c.isspace() for c in core.INTRO_TEXT[s['unit']][s['start']:s['end']]) for s in spans}
    body = coverage['source_categories']['BODY_CANDIDATE']
    body['assembly_roles']['UNKNOWN'] -= 3
    body['assembly_roles']['OPERATIVE'] += 3
    body['active_characters']['unknown_only'] -= sum(counts.values())
    body['active_characters']['known_only'] += sum(counts.values())
    pending = []
    for row in coverage['selected_body_pending']:
        if row['unit'] in counts:
            row['role_unresolved'] = False
            row['unknown_characters'] -= counts[row['unit']]
            if not row['unknown_characters'] and not row['uncovered_characters']:
                continue
        pending.append(row)
    coverage['selected_body_pending'] = pending
    assert new['meaning_coverage'] == coverage, 'Unexpected coverage change'
    assert not new['independent_legal_acceptance'] and not new['may_execute_transaction']
    return {'status': 'PASS', 'outside_answer_equal': True, 'exact_question_delta': True,
        'intro_nonspace_characters': sum(counts.values()), 'body_pending_before': len(old['meaning_coverage']['selected_body_pending']),
        'body_pending_after': len(pending), 'calculation_agent_office': 'UNRESOLVED',
        'actual_appointment': 'NOT_ESTABLISHED', 'independent_legal_acceptance': False}


def financial(products, prior_profiles, baseline, root):
    profiles = deepcopy(prior_profiles['preceding'])
    preceding = profiles['preceding']
    sp, ep = preceding['statement'], preceding['equity']
    equity = basf_equity.consume(products, sp, ep, root,
        expected_statement_profile_sha256=digest(sp), expected_profile_sha256=digest(ep))
    preceding['oci']['prior_sha256'] = digest(equity)
    np = preceding['oci']
    oci = basf_oci_notes.consume(products, sp, ep, np, root,
        expected_statement_profile_sha256=digest(sp), expected_equity_profile_sha256=digest(ep), expected_profile_sha256=digest(np))
    profiles['hedge']['prior_sha256'] = digest(oci)
    hp = profiles['hedge']
    result = basf_hedge_note.consume(products, preceding, hp, root,
        expected_prior_profiles_sha256=digest(preceding), expected_profile_sha256=digest(hp))
    for key in ('statement_review', 'equity_review'):
        assert result[key] == baseline[key], 'Changed financial meaning: ' + key
    for key, profile in (('oci_note_review', np), ('hedge_note_review', hp)):
        expected = deepcopy(baseline[key])
        assert {k: v for k, v in expected['profile'].items() if k != 'prior_sha256'} == {
            k: v for k, v in profile.items() if k != 'prior_sha256'}
        expected['profile'] = deepcopy(profile)
        expected['profile_sha256'] = digest(profile)
        assert result[key] == expected, 'Changed financial meaning/diagnostics: ' + key
    return result, profiles


CONTROL_NAMES = ('omitted-intro-line', 'caption-included', 'changed-raw-offset', 'current-appointment',
    'invented-office', 'extra-appointment-assertion', 'malformed-version', 'missing-version', 'unknown-intro-role',
    'caption-node-lost', 'outside-node-changed', 'stale-financial-prior')


def controls(products, baseline, current_financial, profiles, root):
    observed = []
    for name in CONTROL_NAMES:
        try:
            if name == 'stale-financial-prior':
                prior = {k: current_financial[k] for k in ('answer', 'statement_review', 'equity_review')}
                profile = deepcopy(profiles['preceding']['oci'])
                profile['prior_sha256'] = '0' * 64
                basf_oci_notes.evaluate(products['P1']['payload']['graph'], prior, profile, root,
                    expected_profile_sha256=digest(profile))
            elif name in ('caption-node-lost', 'outside-node-changed'):
                changed = deepcopy(products)
                payload = changed['P3']['payload']
                if name == 'caption-node-lost':
                    payload['clauses']['nodes'] = [n for n in payload['clauses']['nodes'] if n['id'] != core.UNKNOWN_ID[:-1] + '6']
                else:
                    next(n for n in payload['clauses']['nodes'] if n['id'] != core.IDENTITY)['origin'] = 'altered'
                changed['P3'] = service.seal('P3', products['P1']['payload']['request']['bundle'], products['P3']['inputs'], payload)
                core.validate_transition(baseline, changed)
            else:
                p3 = products['P3']['payload']
                clauses, assembly = deepcopy(p3['clauses']), deepcopy(products['P2']['payload']['assembly'])
                node = next(n for n in clauses['nodes'] if n['id'] == core.IDENTITY)
                if name == 'omitted-intro-line': node['spans'].pop(1)
                elif name == 'caption-included': node['spans'][0]['start'] = 0
                elif name == 'changed-raw-offset': node['source_uses'][0]['source']['start'] += 1
                elif name == 'current-appointment': node['agent_reading']['appointment_wording'] = 'The agent is currently appointed.'
                elif name == 'invented-office': node['agent_reading']['calculation_agent_office'] = 'London'
                elif name == 'extra-appointment-assertion': node['actual_appointment'] = True
                elif name == 'malformed-version': node['initial_agent_provenance'] = None
                elif name == 'missing-version': del node['initial_agent_provenance']
                else: next(u for u in assembly['units'] if u['unit'] in core.INTRO_TEXT)['role'] = 'UNKNOWN'
                basf_agent_report.explain(clauses, products['P1']['payload']['graph'], assembly, p3['dependencies'])
        except ValueError as error:
            observed.append({'case': name, 'refused': True, 'reason': str(error), 'binding_hashes_recomputed_where_applicable': True})
        else:
            raise AssertionError('Adverse control accepted: ' + name)
    return observed


def main():
    here, root = [Path(p).resolve() for p in sys.argv[1:3]]
    mode = sys.argv[3]
    assert mode in ('answer', 'financial', 'controls')
    target = here / ('installed-' + mode)
    target.mkdir(exist_ok=False)
    env = Path(sys.prefix).resolve()
    package = env / 'lib/python3.11/site-packages/legalmath'
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    expected = read(here / 'source-package.json')
    actual = {str(p.relative_to(package)): sha(p) for p in package.rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    assert actual == expected and sys.flags.isolated == 1
    assert all(not Path(p).resolve().is_relative_to(root / 'src') for p in sys.path if p)
    proof = {'python': sys.executable, 'prefix': sys.prefix, 'isolated': sys.flags.isolated,
        'sys_path': sys.path, 'modules': {},
        'dependencies': {d.metadata['Name']: d.version for d in importlib.metadata.distributions()}}
    for name, module in list(sys.modules.items()):
        if name == 'legalmath' or name.startswith('legalmath.'):
            p = Path(module.__file__).resolve()
            assert p.is_relative_to(package) and sha(p) == expected[str(p.relative_to(package))]
            proof['modules'][name] = {'path': str(p), 'sha256': sha(p)}
    def no_native(*args, **kwargs): raise AssertionError('Native children forbidden in initial-agent repair')
    subprocess.Popen = no_native
    service.source_product = no_native
    products = read(here / 'products.json.gz')
    baseline = read(here / 'baseline-products.json.gz')
    if mode == 'answer':
        rebuilt = candidate(baseline, root)
        assert rebuilt == products
        answer = service.consume(rebuilt, root, mode='frozen')
        assert answer == read(here / 'ordinary-answer.json.gz')
        omitted = omission(rebuilt, baseline)
        assert omitted == read(here / 'omitted-products.json.gz')
        omitted_answer = service.consume(omitted, root, mode='frozen')
        assert omitted_answer == read(here / 'omitted-answer.json.gz')
        save(target / 'ordinary-answer.json.gz', answer)
        result = {'status': 'PASS', 'full_output_equal': True, 'rebuilt_products_equal': True,
            'matched_omission_equal': True, 'native_calls': 0, 'same_host_only': True}
    elif mode == 'financial':
        assert read(here / 'installed-answer/result.json')['status'] == 'PASS'
        value, profiles = financial(products, read(here / 'prior-profiles.json'),
            read(here / 'baseline-consumer.json.gz'), root)
        assert value == read(here / 'current-financial-consumer.json.gz')
        assert profiles == read(here / 'financial-profiles.json')
        save(target / 'current-financial-consumer.json.gz', value)
        result = {'status': 'PASS', 'financial_outputs_equal': True,
            'profiles_equal': True, 'native_calls': 0, 'same_host_only': True}
    else:
        value = controls(products, baseline, read(here / 'current-financial-consumer.json.gz'),
            read(here / 'financial-profiles.json'), root)
        assert value == read(here / 'actual-controls.json')
        save(target / 'controls.json', value)
        result = {'status': 'PASS', 'controls': len(value), 'native_calls': 0, 'same_host_only': True}
    # Include lazily imported financial/reporting modules in the final import proof.
    proof['runner'] = {'path': str(Path(__file__).resolve()), 'sha256': sha(Path(__file__))}
    for name, module in list(sys.modules.items()):
        if name == 'legalmath' or name.startswith('legalmath.'):
            p = Path(module.__file__).resolve()
            assert p.is_relative_to(package) and sha(p) == expected[str(p.relative_to(package))]
            proof['modules'][name] = {'path': str(p), 'sha256': sha(p)}
    save(target / 'package-files.json', actual)
    save(target / 'import-proof.json', proof)
    save(target / 'result.json', result)
    print(result)


if __name__ == '__main__': main()
