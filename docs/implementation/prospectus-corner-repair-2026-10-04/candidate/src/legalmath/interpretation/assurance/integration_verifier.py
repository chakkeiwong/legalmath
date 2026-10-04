"""Deterministic validation of the registered dossier evidence profiles.

The trust base is these checkers, the pinned tools and the retained source and
proposal inputs. Hashes detect drift; they are not third-party signatures or a
proof of a historical process. Stored runtime results are checked against the
actual Python evaluator and trace checker, and builds remain bound to bytes.
"""
from itertools import combinations

from ...canonical import digest
from ...errors import LegalMathError
from ...ir.evaluate import evaluate
from ...ir.trace import verify_result
from ...ir.typecheck import validate_bundle
from ..search.formal import bundle, snapshots, RULE, project
from .arguments import evaluate_criticism
from .integration_contract import read_evidence
from ..contracts import parse
from .integration_execution import ReplayInput, load_inputs, target_spec, implementation_files, source_check


def require(condition, message):
    if not condition:
        raise LegalMathError('E_INTEGRITY', details=message)


def verify_runtime(row, compiled, config, root):
    cases = read_evidence(row['cases'], root)
    expected_cases = [{'id': f"{row['candidate_id']}.{i}", 'bundle': compiled, 'snapshot': s, 'rule_id': RULE,
                       'valid_at': config['at'], 'known_at': config['at'], 'expected': {}}
                      for i, s in enumerate(snapshots([compiled], config['at'], maximum=config['probe_limit']))]
    require(cases == expected_cases and bool(cases), 'Replay cases differ from declared input/domain')
    manifest = read_evidence(row['build_manifest'], root)
    report = read_evidence(row['report'], root)
    results = read_evidence(row['results'], root)
    read_evidence(row['jar'], root, json_value=False)
    require(manifest['bundle_hash'] == digest(compiled) == report['bundle_hash'], 'Wrong replay bundle')
    require(manifest['jar_sha256'] == row['jar']['sha256'] == report['jar_sha256'], 'Wrong executable')
    require(report['build_manifest_hash'] == digest(manifest), 'Wrong build manifest')
    require(report['corpus_hash'] == digest(cases), 'Wrong corpus')
    require(report['passed'] is True and len(results) == len(cases), 'Missing or failed replay')
    require(report['checks'] == [{'name': 'full-semantic-conformance', 'passed': True,
                                  'evidence_hash': digest(results)}], 'Unchecked replay results')
    for case, result in zip(cases, results):
        require(result['id'] == case['id'], 'Wrong replay case id')
        actual = evaluate(compiled, case['snapshot'], RULE, config['at'], config['at'])
        require(result['python'] == actual, 'Recorded Python answer differs from reevaluation')
        verify_result(compiled, case['snapshot'], RULE, result['java'])
        strip = lambda v: {k: x for k, x in v.items() if k not in ('engine_version', 'result_hash')}
        require(strip(actual) == strip(result['java']), 'Recorded Java answer disagrees')
        require(result['java']['engine_version'] == manifest['decision_engine'] != actual['engine_version'],
                'Runtime identity is missing or equals Python')


def verify_evidence(dossier, root):
    for ref in dossier['upstream_inputs']:
        read_evidence(ref, root, json_value=False)
    config = parse(ReplayInput, read_evidence(dossier['input_manifest'], root))
    require(config == dossier['target']['input_manifest'], 'Embedded config differs from retained input manifest')
    packet, candidates, criticism = load_inputs(config, root)
    require(target_spec(config, packet, candidates) == dossier['target'], 'Target was not reconstructed from inputs')
    require(digest(packet) == dossier['source_packet_hash'], 'Wrong source packet')
    require(dossier['target_description'] == packet['selected_slice'], 'Target description differs from source scope')
    require(dossier['source_packet'] == config['packet'], 'Wrong packet file')
    impl = implementation_files(root)
    require(all(ref in dossier['upstream_inputs'] for ref in impl), 'Implementation inventory missing')
    required_inputs = [config[k] for k in ('packet', 'candidates', 'criticism')]
    required_inputs += [{k: s[k] for k in ('path', 'sha256')} for s in config['sources']]
    require(all(ref in dossier['upstream_inputs'] for ref in required_inputs), 'Upstream file binding missing')
    impl_hash = digest(impl)
    methods = {m['method_id']: m for m in dossier['methods']}
    registry = {'method.source': ('family.source', 'SOURCE_INVENTORY'),
                'method.proposals': ('family.interpretation', 'HYPOTHESIS_GENERATION'),
                'method.arguments': ('family.argumentation', 'ARGUMENTATION'),
                'method.types': ('family.formal', 'RULEIR'), 'method.java': ('family.runtime', 'JAVA'),
                'method.catala': ('family.runtime', 'CATALA'), 'method.search': ('family.search', 'SEARCH'),
                'method.provider': ('family.generation', 'CODEX_PROVIDER'), 'method.proof': ('family.proof', 'PROOF_ASSISTANT')}
    dependencies = {'method.source': {'shared.source'},
                    'method.proposals': {'shared.source', 'shared.proposals'},
                    'method.arguments': {'shared.source', 'shared.proposals'},
                    'method.types': {'shared.ruleir', 'shared.proposals'},
                    'method.search': {'shared.proposals', 'shared.ruleir'},
                    'method.java': {'shared.ruleir', 'shared.facts', 'shared.proposals'},
                    'method.catala': {'shared.ruleir', 'shared.facts', 'shared.proposals'},
                    'method.provider': set(), 'method.proof': set()}
    require(set(methods) == set(registry), 'Unknown or missing method adapter')
    expected_required = {'method.source', 'method.proposals', 'method.arguments', 'method.types', 'method.search'}
    expected_required |= {'method.'+b for b in config['required_backends']}
    require(set(dossier['required_method_ids']) == expected_required, 'Required methods differ from target')
    payloads = {}
    for mid, method in methods.items():
        require((method['family_id'], method['method_kind']) == registry[mid], 'Method family/kind mismatch')
        require(dependencies[mid] <= set(method['shared_dependencies']), 'Method shared dependencies omitted')
        envelope = read_evidence(method['evidence'], root)
        require(envelope.get('schema_version') == 'assurance-evidence.v2', 'Unregistered evidence profile')
        require(envelope.get('method_id') == mid and envelope.get('target_hash') == dossier['target_hash'], 'Mis-targeted method evidence')
        require(envelope.get('status') == method['status'], 'Status differs from executed evidence')
        require(envelope.get('implementation_hash') == method['implementation_hash'] == impl_hash, 'Stale method implementation')
        payloads[mid] = envelope['payload']
    expected_source = source_check(config, packet, root)
    require(payloads['method.source'] == expected_source, 'Source result differs from extraction/audit')
    require(methods['method.source']['status'] == 'UNRESOLVED', 'Authority closure cannot be inferred')
    proposals = payloads['method.proposals']
    require(proposals['candidate_ids'] == sorted(candidates) and proposals['origin'] == config['origin']
            and proposals['fresh_generation'] is False, 'False candidate origin or dropped alternatives')
    require(methods['method.proposals']['status'] == 'UNRESOLVED', 'Archived proposals are not fresh coverage')
    arg = evaluate_criticism(criticism, packet, set(candidates))
    require(payloads['method.arguments'] == {'proposal': criticism, 'evaluation': arg}, 'Argument evaluation mismatch')
    status = 'AGREES' if arg['status'] == 'ARGUMENT_CHECKS_COMPLETED' else 'UNRESOLVED'
    require(methods['method.arguments']['status'] == status, 'Argument uncertainty lost')
    expected_questions = [{'question_id': f'question.argument.{i}', 'target_id': dossier['question_id'],
                           'status': 'OPEN', 'reason': question,
                           'required_evidence': ['Source-backed response to the recorded critical question.']}
                          for i, question in enumerate(arg['questions'])]

    bundles = {}; unsupported = set()
    for cid, reading in candidates.items():
        try:
            bundles[cid] = bundle(reading, packet, config['at'])
        except LegalMathError as exc:
            if exc.code != 'E_UNSUPPORTED_PROFILE':
                raise
            unsupported.add(cid)
    hypotheses = {h['hypothesis_id']: h for h in dossier['hypotheses']}
    require(set(hypotheses) == set(candidates), 'Candidate set changed')
    units = {u['unit_id']: u for u in packet['units']}
    for cid, reading in candidates.items():
        h = hypotheses[cid]
        quotes = [{'source_id': c['unit_id'], 'locator': units[c['unit_id']]['locator'], 'text': c['quote'],
                   'source_sha256': units[c['unit_id']]['span']['raw_sha256']} for c in reading['citations']]
        require(h['source_quotes'] == quotes and h['controlled_language'] == reading['statement']
                and h['assumptions'] == reading['assumptions'] and h['family_id'] == 'family.'+reading['family'],
                'Hypothesis differs from retained proposal')
        require(h['opposing_reasons'] == reading['questions'] and h['supporting_reasons'] == []
                and h['parent_id'] is None, 'Archived hypothesis objections or provenance changed')
        require(h['rule_ir_hash'] == (digest(bundles[cid]) if cid in bundles else None), 'Hypothesis bundle mismatch')
        require(h['status'] == ('RETAINED' if cid in bundles else 'UNENCODED'), 'Unsupported hypothesis hidden')
        if cid in unsupported:
            expected_questions.append({'question_id': 'extension.'+cid, 'target_id': cid,
                'status': 'EXTENSION_REQUIRED',
                'reason': 'The proposed rule cannot be represented by the supported formal grammar.',
                'required_evidence': ['A separately reviewed grammar/semantics extension or a justified reformulation.']})
    require(sorted(dossier['open_questions'], key=lambda q: q['question_id']) ==
            sorted(expected_questions, key=lambda q: q['question_id']), 'Critical questions or their evidence requirements changed')
    rows = payloads['method.types']['rows']
    require({r['candidate_id'] for r in rows} == set(candidates) and len(rows) == len(candidates), 'Typecheck coverage incomplete')
    for row in rows:
        cid = row['candidate_id']
        if cid in bundles:
            require(row['status'] == 'CHECKED' and read_evidence(row['bundle'], root) == bundles[cid], 'Typecheck target mismatch')
            require(not validate_bundle(bundles[cid]), 'Invalid RuleIR')
        else:
            require(row['status'] == 'UNSUPPORTED', 'Unsupported candidate marked typed')
    require(methods['method.types']['status'] == ('UNRESOLVED' if unsupported else 'AGREES'), 'Type status mismatch')

    for backend in ('java', 'catala'):
        rows = payloads['method.'+backend]['rows']
        require(len(rows) == len(bundles) and {r['candidate_id'] for r in rows} == set(bundles), 'Runtime coverage incomplete')
        for row in rows:
            if row['status'] == 'CHECKED':
                verify_runtime(row, bundles[row['candidate_id']], config, root)
            else:
                require(row['status'] in ('UNAVAILABLE', 'UNSUPPORTED'), 'Unknown backend result')
        passed = bool(rows) and not unsupported and all(r['status'] == 'CHECKED' for r in rows)
        require((methods['method.'+backend]['status'] == 'AGREES') == passed, 'False backend agreement')
        require({'shared.ruleir', 'shared.facts', 'shared.proposals'} <= set(methods['method.'+backend]['shared_dependencies']),
                'Backend shared dependencies omitted')
    search = payloads['method.search']
    require(search['visits'] == [{'index': i, 'candidate_id': cid, 'depth': 0, 'event': 'VISIT_RETAINED_PROPOSAL'}
                                for i, cid in enumerate(sorted(candidates))], 'Incomplete initial breadth pass')
    expected_pairs = list(combinations(sorted(candidates), 2))[:config['pair_limit']]
    require([(p['left'], p['right']) for p in search['pairs']] == expected_pairs, 'Pair coverage mismatch')
    total = len(candidates)*(len(candidates)-1)//2
    require(search['total_pairs'] == total and search['unvisited_pairs'] == total-len(expected_pairs), 'Hidden search truncation')
    require(search['fresh_expansion'] is False and search['candidate_pruning_authorized'] is False, 'Unauthorized pruning/expansion claim')
    for pair in search['pairs']:
        left, right, result = pair['left'], pair['right'], pair['result']
        comparable = left in bundles and right in bundles and candidates[left]['formalization']['facts'] == candidates[right]['formalization']['facts']
        comparable = comparable and all(candidates[c]['statement'].startswith('[TRUE_IS_PROHIBITED]') for c in (left, right))
        if not comparable:
            require(result['status'] in ('NOT_COMPARABLE', 'UNSUPPORTED'), 'Unreviewed fact mapping')
        elif result['status'] == 'DIFFERENT':
            require(len(result['replays']) == 2, 'Missing witness replay')
            projections = []
            for cid, replay in zip((left, right), result['replays']):
                b = bundles[cid]; s = result['snapshot']
                actual = evaluate(b, s, RULE, config['at'], config['at'])
                require(replay['python'] == actual, 'Witness target mismatch')
                verify_result(b, s, RULE, replay['java'])
                require(project(actual) == project(replay['java']), 'Witness Java disagreement')
                projections.append(project(actual))
            require(projections[0] != projections[1], 'False separating witness')
        else:
            # A solver's UNSAT claim is retained, not promoted to a checked certificate.
            require(result['status'] in ('EQUIVALENT_WITHIN_DOMAIN', 'NO_DIFFERENCE_IN_FINITE_PROBES',
                                        'UNKNOWN', 'UNSUPPORTED', 'INCONSISTENT_DOMAIN'), 'Unknown solver status')
    require(methods['method.search']['status'] == 'UNRESOLVED', 'Finite retained search cannot prove completeness')
    expected_discrepancies = []
    for i, pair in enumerate(search['pairs']):
        if pair['result']['status'] != 'EQUIVALENT_WITHIN_DOMAIN':
            expected_discrepancies.append({'discrepancy_id': f'pair.{i}', 'target_id': dossier['question_id'],
                'kind': 'FORMAL_COUNTEREXAMPLE' if pair['result']['status'] == 'DIFFERENT' else 'NOT_COMPARABLE',
                'method_ids': ['method.search'], 'severity': 'MATERIAL', 'disposition': 'RETAINED',
                'explanation': pair['left']+' versus '+pair['right']+': '+pair['result']['status']})
    require(dossier['discrepancies'] == expected_discrepancies, 'Executed discrepancies were omitted or misreported')
    for mid in ('method.provider', 'method.proof'):
        require(methods[mid]['status'] == 'UNAVAILABLE', 'Unexecuted tool marked successful')
    require(payloads['method.provider']['live_calls'] == 0, 'Offline run claims provider calls')
    require(payloads['method.proof']['registered_certificate_checkers'] == [], 'Unregistered proof checker')
    obligations = {o['obligation_id']: o for o in dossier['obligations']}
    expected = {'obligation.types', 'obligation.java', 'obligation.catala', 'obligation.proof'}
    if config['require_fresh_generation']:
        expected.add('obligation.fresh')
    require(set(obligations) == expected, 'Required obligation missing or changed')
    proposition_profiles = {
        'obligation.types': ('method.types', 'Every retained candidate has a well-typed encoding.', 'Supplied candidate set'),
        'obligation.java': ('method.java', 'The runtime agrees with Python on every declared replay case.',
                            'The explicitly stored finite replay cases; not all inputs'),
        'obligation.catala': ('method.catala', 'The runtime agrees with Python on every declared replay case.',
                              'The explicitly stored finite replay cases; not all inputs'),
        'obligation.proof': ('method.proof', 'Check a general translation-preservation certificate.',
                             'All supported RuleIR inputs; not established by finite replay'),
        'obligation.fresh': ('method.provider', 'Generate fresh source-driven alternatives.', 'Current source question')}
    for oid, obligation in obligations.items():
        mid, statement, domain = proposition_profiles[oid]
        require(obligation['target_id'] == dossier['question_id'] and obligation['method_id'] == mid
                and obligation['checker'] == mid and obligation['statement'] == statement
                and obligation['domain'] == domain
                and obligation['assumptions'] == ['Retained fact definitions and RuleIR semantics apply.'],
                'Obligation proposition differs from the registered evidence profile')
    for oid, mid in [('obligation.types', 'method.types'), ('obligation.java', 'method.java'), ('obligation.catala', 'method.catala')]:
        require((obligations[oid]['status'] == 'CHECKED') == (methods[mid]['status'] == 'AGREES'), 'False discharged obligation')
    require(obligations['obligation.proof']['status'] == 'NOT_RUN', 'No registered general proof')
    if 'obligation.fresh' in obligations:
        require(obligations['obligation.fresh']['status'] == 'NOT_RUN', 'No fresh generation')
    expected_artifacts = {(cid, 'RULEIR') for cid in bundles}
    expected_artifacts |= {(r['candidate_id'], 'JAVA' if b == 'java' else 'CATALA') for b in ('java', 'catala')
                           for r in payloads['method.'+b]['rows'] if r['status'] == 'CHECKED'}
    require({(a['source_hypothesis_id'], a['kind']) for a in dossier['artifacts']} == expected_artifacts, 'Artifact coverage mismatch')
    for artifact in dossier['artifacts']:
        raw = read_evidence(artifact['evidence'], root, json_value=artifact['kind'] == 'RULEIR')
        if artifact['kind'] == 'RULEIR':
            require(digest(raw) == artifact['bundle_hash'], 'Wrong RuleIR artifact')
        else:
            backend = 'java' if artifact['kind'] == 'JAVA' else 'catala'
            row = next(r for r in payloads['method.'+backend]['rows'] if r['candidate_id'] == artifact['source_hypothesis_id'])
            require(artifact['evidence'] == row['jar'], 'Artifact does not identify replayed binary')
