"""Execute a dossier from retained proposals; never invent a successful check.

The same manifest format accepts another retained circular. Generation is an
explicit input boundary: archived hypotheses do not measure fresh-model recall.
"""
from itertools import combinations
from pathlib import Path
from typing import Literal
import json

from pydantic import Field, model_validator

from ...canonical import canonical, digest
from ...errors import LegalMathError
from ...java.manifest import build_candidate, verify_candidate
from ..contracts import Strict, Id, Text, parse, Packet
from ..search.models import Reading
from ..search.formal import bundle, Comparisons, snapshots, RULE
from .arguments import evaluate_criticism
from .sources import extract_document, audit_packet, references
from .integration_contract import evidence_file, read_evidence, EvidenceFile, parse_dossier, validate_dossier


class SourceInput(EvidenceFile):
    url: Text
    media_type: Literal['application/json', 'text/html', 'text/plain', 'application/pdf']


class ReplayInput(Strict):
    schema_version: Literal['assurance-replay-input.v1']
    origin: Literal['ARCHIVED_MODEL_PROPOSALS', 'DECLARED_TEST_PROPOSALS']
    packet: EvidenceFile
    candidates: EvidenceFile
    criticism: EvidenceFile
    sources: list[SourceInput] = Field(min_length=1, max_length=20)
    question_id: Id
    at: Text
    probe_limit: int = Field(ge=1, le=128)
    pair_limit: int = Field(ge=1, le=120)
    required_backends: list[Literal['java', 'catala']] = Field(min_length=1, max_length=2)
    require_fresh_generation: bool

    @model_validator(mode='after')
    def valid_time_and_backends(self):
        from ...domain import timestamp
        timestamp(self.at)
        if len(set(self.required_backends)) != len(self.required_backends):
            raise ValueError('Duplicate required backend')
        if len({source.url for source in self.sources}) != len(self.sources):
            raise ValueError('Duplicate source URL')
        return self


def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value))
    return path


def implementation_files(root):
    return [evidence_file(p, root) for p in sorted((root/'src/legalmath').rglob('*'))
            if p.is_file() and p.suffix in ('.py', '.java', '.json')]


def target_spec(config, packet, candidates):
    return {'question_id': config['question_id'], 'source_packet_hash': digest(packet),
            'candidate_hashes': {k: digest(v) for k, v in sorted(candidates.items())},
            'input_manifest': config, 'result_projection': 'status/type/value',
            'interpretation_origin': config['origin']}


def load_inputs(config, root):
    packet = parse(Packet, read_evidence(config['packet'], root))
    candidates = read_evidence(config['candidates'], root)
    if not isinstance(candidates, dict) or not 1 <= len(candidates) <= 16:
        raise LegalMathError('E_RESOURCE_LIMIT', details='Expected 1 to 16 candidates')
    units = {u['unit_id']: u for u in packet['units']}
    for cid, reading in candidates.items():
        parsed = parse(Reading, reading)
        if parsed != reading:
            raise LegalMathError('E_SCHEMA')
        for c in reading['citations']:
            if units.get(c['unit_id'], {}).get('text', '').count(c['quote']) != 1:
                raise LegalMathError('E_REFERENCE', details='Candidate quote is absent or ambiguous')
        formal = reading['formalization']
        if formal:
            for fact in formal['facts']:
                if not set(fact['source_unit_ids']) <= units.keys():
                    raise LegalMathError('E_REFERENCE', details='Unknown fact-definition source')
    criticism = read_evidence(config['criticism'], root)
    proposal = criticism.get('proposal', criticism)
    return packet, candidates, proposal


def source_check(config, packet, root):
    documents = []; rows = []
    for source in config['sources']:
        data = read_evidence({k: source[k] for k in ('path', 'sha256')}, root, json_value=False)
        doc = {'url': source['url'], 'media_type': source['media_type'], 'data': data}
        extracted = extract_document(doc)
        documents.append({**doc, **extracted})
        rows.append({'source': source, 'extraction': extracted, 'references': references(doc)})
    context = {'documents': documents}
    audit = audit_packet(packet, context)
    return {'sources': rows, 'packet_audit': audit,
            'authority_closure_established': False,
            'scope': 'Retained bytes and anchors only; referenced authority text must be acquired separately'}


def run_replay(root, manifest_path, output, jdk, *, catala=None):
    root, manifest_path, output = Path(root).resolve(), Path(manifest_path).resolve(), Path(output).resolve()
    if not output.is_relative_to(root) or not manifest_path.is_relative_to(root):
        raise LegalMathError('E_REFERENCE')
    output.mkdir(parents=True, exist_ok=False)
    config = parse(ReplayInput, json.loads(manifest_path.read_text()))
    packet, candidates, criticism = load_inputs(config, root)
    target = target_spec(config, packet, candidates); target_hash = digest(target)
    impl = implementation_files(root); impl_hash = digest(impl)
    inputs = [evidence_file(manifest_path, root), config['packet'], config['candidates'], config['criticism']]
    inputs += [{k: s[k] for k in ('path', 'sha256')} for s in config['sources']]
    tool_refs = []
    for p in [Path(jdk)/'bin/java', Path(jdk)/'bin/javac']:
        if p.is_file():
            tool_refs.append(evidence_file(p, root))
    if catala:
        for key in ('compiler', 'lock'):
            if Path(catala[key]).is_file():
                tool_refs.append(evidence_file(catala[key], root))
    methods = []; obligations = []; artifacts = []; questions = []; discrepancies = []
    qid = config['question_id']

    def record(mid, family, kind, status, payload, *, shared=(), limits):
        envelope = {'schema_version': 'assurance-evidence.v2', 'method_id': mid,
                    'target_hash': target_hash, 'status': status, 'implementation_hash': impl_hash,
                    'payload': payload}
        ref = evidence_file(save(output/(mid+'.json'), envelope), root)
        methods.append({'method_id': mid, 'family_id': family, 'target_id': qid,
                        'method_kind': kind, 'status': status, 'input_hash': target_hash,
                        'evidence': ref, 'implementation_hash': impl_hash,
                        'shared_dependencies': list(shared), 'limitations': limits,
                        'result_summary': [payload.get('summary', 'See retained checker output')]})
        return ref

    def obligation(oid, mid, status, statement, ref, *, target_id=None, domain):
        obligations.append({'obligation_id': oid, 'target_id': target_id or qid, 'method_id': mid,
                            'statement': statement, 'assumptions': ['Retained fact definitions and RuleIR semantics apply.'],
                            'checker': mid, 'status': status, 'input_hash': target_hash, 'evidence': ref,
                            'domain': domain, 'limitations': ['Conditional engineering result; legal interpretation remains open.']})

    source = source_check(config, packet, root)
    # Source closure is deliberately not inferred from an anchor check.
    record('method.source', 'family.source', 'SOURCE_INVENTORY', 'UNRESOLVED', source,
           shared=['shared.source'], limits=['Referenced authority text and visual completeness are not established.'])
    proposal_ref = record('method.proposals', 'family.interpretation', 'HYPOTHESIS_GENERATION', 'UNRESOLVED',
                         {'origin': config['origin'], 'candidate_ids': sorted(candidates),
                          'fresh_generation': False, 'summary': 'All retained proposals imported; no new generation'},
                         shared=['shared.source', 'shared.proposals'],
                         limits=['Imported alternatives can share omissions; new sources require new investigation.'])
    argument = evaluate_criticism(criticism, packet, set(candidates))
    arg_ref = record('method.arguments', 'family.argumentation', 'ARGUMENTATION',
                     'AGREES' if argument['status'] == 'ARGUMENT_CHECKS_COMPLETED' else 'UNRESOLVED',
                     {'proposal': criticism, 'evaluation': argument}, shared=['shared.source', 'shared.proposals'],
                     limits=['Bounded criticism profile; priorities and premises are not legal adjudication.'])
    for i, question in enumerate(argument.get('questions', [])):
        questions.append({'question_id': f'question.argument.{i}', 'target_id': qid, 'status': 'OPEN',
                          'reason': question, 'required_evidence': ['Source-backed response to the recorded critical question.']})

    checker = Comparisons(output/'java', jdk, config['at'])
    bundles = {}; bundle_refs = {}; hypotheses = []; type_rows = []; unsupported = []
    # Complete the breadth pass before scheduling any pair or accepting a winner.
    visits = []
    for index, (cid, reading) in enumerate(sorted(candidates.items())):
        visits.append({'index': index, 'candidate_id': cid, 'depth': 0, 'event': 'VISIT_RETAINED_PROPOSAL'})
        try:
            compiled = bundle(reading, packet, config['at'])
        except LegalMathError as exc:
            if exc.code != 'E_UNSUPPORTED_PROFILE':
                raise
            compiled = None; unsupported.append(cid)
            type_rows.append({'candidate_id': cid, 'status': 'UNSUPPORTED', 'error': exc.code})
        if compiled is not None:
            bundles[cid] = compiled
            bundle_refs[cid] = evidence_file(save(output/'bundles'/(cid+'.json'), compiled), root)
            type_rows.append({'candidate_id': cid, 'status': 'CHECKED', 'bundle': bundle_refs[cid]})
        units = {u['unit_id']: u for u in packet['units']}
        quotes = [{'source_id': c['unit_id'], 'locator': units[c['unit_id']]['locator'],
                   'text': c['quote'], 'source_sha256': units[c['unit_id']]['span']['raw_sha256']}
                  for c in reading['citations']]
        hypotheses.append({'hypothesis_id': cid, 'family_id': 'family.'+reading['family'], 'question_id': qid,
                           'source_packet_hash': digest(packet), 'source_quotes': quotes,
                           'controlled_language': reading['statement'], 'rule_ir_hash': digest(compiled) if compiled else None,
                           'assumptions': reading['assumptions'], 'supporting_reasons': [],
                           'opposing_reasons': reading['questions'], 'parent_id': None,
                           'status': 'RETAINED' if compiled else 'UNENCODED'})
        if compiled:
            artifacts.append({'artifact_id': 'bundle.'+cid, 'kind': 'RULEIR', 'target_id': qid,
                              'source_hypothesis_id': cid, 'bundle_hash': digest(compiled), 'evidence': bundle_refs[cid],
                              'status': 'CHECKED', 'limitations': ['Source meaning remains a proposal.']})
        else:
            questions.append({'question_id': 'extension.'+cid, 'target_id': cid, 'status': 'EXTENSION_REQUIRED',
                              'reason': 'The proposed rule cannot be represented by the supported formal grammar.',
                              'required_evidence': ['A separately reviewed grammar/semantics extension or a justified reformulation.']})
    type_ref = record('method.types', 'family.formal', 'RULEIR', 'UNRESOLVED' if unsupported else 'AGREES',
                      {'rows': type_rows}, shared=['shared.ruleir', 'shared.proposals'],
                      limits=['Well-typed expressions do not establish faithful English translation.'])
    obligation('obligation.types', 'method.types', 'UNSUPPORTED' if unsupported else 'CHECKED',
               'Every retained candidate has a well-typed encoding.', type_ref, domain='Supplied candidate set')

    replays = {'java': [], 'catala': []}; backend_status = {'java': 'AGREES', 'catala': 'AGREES'}
    for cid, compiled in bundles.items():
        cases = [{'id': f'{cid}.{i}', 'bundle': compiled, 'snapshot': s, 'rule_id': RULE,
                  'valid_at': config['at'], 'known_at': config['at'], 'expected': {}}
                 for i, s in enumerate(snapshots([compiled], config['at'], maximum=config['probe_limit']))]
        case_ref = evidence_file(save(output/'cases'/(cid+'.json'), cases), root)
        for backend in ('java', 'catala'):
            try:
                if backend == 'catala' and not catala:
                    raise LegalMathError('E_NOT_FOUND', details='Catala not configured')
                built = checker.build(compiled) if backend == 'java' else build_candidate(
                    compiled, output/'catala'/cid, jdk, backend='catala', catala_toolchain=catala)
                report = verify_candidate(built, cases, jdk)
                directory = Path(built['jar']).parent
                row = {'candidate_id': cid, 'status': 'CHECKED', 'cases': case_ref,
                       'build_manifest': evidence_file(directory/'build-manifest.json', root),
                       'report': evidence_file(directory/'verification-report.json', root),
                       'results': evidence_file(directory/'verification-results.json', root),
                       'jar': evidence_file(built['jar'], root), 'class_name': built['class_name']}
                artifacts.append({'artifact_id': backend+'.'+cid, 'kind': 'JAVA' if backend == 'java' else 'CATALA',
                                  'target_id': qid, 'source_hypothesis_id': cid, 'bundle_hash': digest(compiled),
                                  'evidence': row['jar'], 'status': 'CHECKED',
                                  'limitations': ['Finite Python/runtime conformance under shared RuleIR and facts.']})
            except (FileNotFoundError, LegalMathError) as exc:
                code = getattr(exc, 'code', 'E_NOT_FOUND')
                if code not in ('E_NOT_FOUND', 'E_UNSUPPORTED_PROFILE'):
                    raise
                row = {'candidate_id': cid, 'status': 'UNAVAILABLE' if code == 'E_NOT_FOUND' else 'UNSUPPORTED', 'error': code}
                backend_status[backend] = 'UNAVAILABLE' if code == 'E_NOT_FOUND' else 'UNRESOLVED'
            replays[backend].append(row)
    for backend, rows in replays.items():
        status = backend_status[backend] if rows and not unsupported else 'UNRESOLVED'
        backend_status[backend] = status
        ref = record('method.'+backend, 'family.runtime', backend.upper(), status, {'rows': rows},
                     shared=['shared.ruleir', 'shared.proposals', 'shared.facts'],
                     limits=['Same input preparation and RuleIR; this does not add an independent English interpretation.'])
        obligation('obligation.'+backend, 'method.'+backend, 'CHECKED' if status == 'AGREES' else 'NOT_RUN',
                   'The runtime agrees with Python on every declared replay case.', ref,
                   domain='The explicitly stored finite replay cases; not all inputs')

    pairs = []; total_pairs = len(candidates)*(len(candidates)-1)//2
    for left, right in list(combinations(sorted(candidates), 2))[:config['pair_limit']]:
        a, b = candidates[left], candidates[right]
        if left not in bundles or right not in bundles:
            result = {'status': 'UNSUPPORTED'}
        elif a['formalization']['facts'] != b['formalization']['facts']:
            result = {'status': 'NOT_COMPARABLE', 'reason': 'No reviewed mapping between different fact definitions.'}
        elif not (a['statement'].startswith('[TRUE_IS_PROHIBITED]') and b['statement'].startswith('[TRUE_IS_PROHIBITED]')):
            result = {'status': 'NOT_COMPARABLE', 'reason': 'A common result meaning is not declared.'}
        else:
            result = checker.compare(a, b, packet)
        pairs.append({'left': left, 'right': right, 'result': result})
    search_ref = record('method.search', 'family.search', 'SEARCH', 'UNRESOLVED',
                        {'scheduler': 'BREADTH_THEN_BOUNDED_PAIRS', 'visits': visits, 'pairs': pairs,
                         'total_pairs': total_pairs, 'unvisited_pairs': total_pairs-len(pairs),
                         'candidate_pruning_authorized': False, 'fresh_expansion': False},
                        shared=['shared.proposals', 'shared.ruleir'],
                        limits=['Searches retained alternatives only; stopping at a budget never proves completeness.'])
    for i, pair in enumerate(pairs):
        if pair['result']['status'] != 'EQUIVALENT_WITHIN_DOMAIN':
            kind = 'FORMAL_COUNTEREXAMPLE' if pair['result']['status'] == 'DIFFERENT' else 'NOT_COMPARABLE'
            discrepancies.append({'discrepancy_id': f'pair.{i}', 'target_id': qid, 'kind': kind,
                                  'method_ids': ['method.search'], 'severity': 'MATERIAL', 'disposition': 'RETAINED',
                                  'explanation': pair['left']+' versus '+pair['right']+': '+pair['result']['status']})
    provider_ref = record('method.provider', 'family.generation', 'CODEX_PROVIDER', 'UNAVAILABLE',
                          {'live_calls': 0, 'reason': 'Offline replay does not invoke a provider.'},
                          limits=['New interpretation generation and fresh criticism were not executed.'])
    if config['require_fresh_generation']:
        obligation('obligation.fresh', 'method.provider', 'NOT_RUN', 'Generate fresh source-driven alternatives.',
                   provider_ref, domain='Current source question')
    proof_ref = record('method.proof', 'family.proof', 'PROOF_ASSISTANT', 'UNAVAILABLE',
                       {'registered_certificate_checkers': [], 'reason': 'No general proof-certificate adapter is registered.'},
                       limits=['No whole-compiler theorem, English theorem or imported proof certificate is claimed.'])
    obligation('obligation.proof', 'method.proof', 'NOT_RUN', 'Check a general translation-preservation certificate.',
               proof_ref, domain='All supported RuleIR inputs; not established by finite replay')
    required = ['method.source', 'method.proposals', 'method.arguments', 'method.types', 'method.search']
    required += ['method.'+b for b in config['required_backends']]
    dossier = parse_dossier({'schema_version': 'proof-carrying-assurance.v3',
        'dossier_id': 'dossier.'+target_hash[:24], 'question_id': qid,
        'target_description': packet['selected_slice'], 'target': target, 'target_hash': target_hash,
        'source_packet_hash': digest(packet), 'source_packet': config['packet'],
        'input_manifest': inputs[0],
        'upstream_inputs': inputs+impl+tool_refs, 'hypotheses': hypotheses, 'required_method_ids': required,
        'methods': methods, 'obligations': obligations, 'artifacts': artifacts,
        'open_questions': questions, 'discrepancies': discrepancies,
        'legal_correctness_established': False, 'probability_of_legal_correctness': None, 'release_eligible': False})
    save(output/'dossier.json', dossier)
    validation = validate_dossier(dossier, root)
    save(output/'validation.json', validation)
    return {'dossier': evidence_file(output/'dossier.json', root), 'validation': evidence_file(output/'validation.json', root),
            'status': validation['status'], 'evidence_files_verified': validation['evidence_files_verified'],
            'candidates': len(candidates), 'pairs': len(pairs),
            'different_pairs': sum(p['result']['status'] == 'DIFFERENT' for p in pairs),
            'backend_status': backend_status, 'release_eligible': False}
