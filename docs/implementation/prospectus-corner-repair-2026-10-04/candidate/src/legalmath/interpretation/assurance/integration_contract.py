"""Target-bound dossier records; file verification is separate from schema parsing.

A descriptive digest cannot establish that a tool executed. Passing evidence
must refer to retained files and pass the registered deterministic verifiers.
No adapter in this version accepts a formal proof certificate.
"""
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from ...canonical import digest, raw_digest, loads
from ...errors import LegalMathError
from ..contracts import Hash, Id, Strict, Text, parse

EvidenceStatus = Literal['AGREES', 'DISAGREES', 'UNRESOLVED', 'UNAVAILABLE', 'ERROR', 'NOT_COMPARABLE', 'STALE']
ProofStatus = Literal['PROVED', 'CHECKED', 'DISPROVED', 'UNKNOWN', 'UNSUPPORTED', 'NOT_RUN']


class EvidenceFile(Strict):
    path: Text
    sha256: Hash


class SourceQuote(Strict):
    source_id: Id
    locator: Text
    text: Text
    source_sha256: Hash


class InterpretationHypothesis(Strict):
    hypothesis_id: Id
    family_id: Id
    question_id: Id
    source_packet_hash: Hash
    source_quotes: list[SourceQuote] = Field(min_length=1, max_length=32)
    controlled_language: Text
    rule_ir_hash: Hash | None
    assumptions: list[Text] = Field(max_length=32)
    supporting_reasons: list[Text] = Field(max_length=64)
    opposing_reasons: list[Text] = Field(max_length=64)
    parent_id: Id | None
    status: Literal['CANDIDATE', 'RETAINED', 'DEFEATED', 'UNENCODED']


class MethodEvidence(Strict):
    method_id: Id
    family_id: Id
    target_id: Id
    method_kind: Literal['SOURCE_INVENTORY', 'HYPOTHESIS_GENERATION', 'ARGUMENTATION', 'SEARCH',
                         'RULEIR', 'SOLVER', 'PROOF_ASSISTANT', 'PYTHON', 'JAVA', 'CATALA',
                         'CODEX_PROVIDER', 'RESEARCH_ASSISTANT', 'DYNARE_SCHEDULER', 'OTHER']
    status: EvidenceStatus
    input_hash: Hash
    evidence: EvidenceFile
    implementation_hash: Hash
    shared_dependencies: list[Id] = Field(max_length=64)
    limitations: list[Text] = Field(min_length=1, max_length=32)
    result_summary: list[Text] = Field(max_length=32)


class ProofObligation(Strict):
    obligation_id: Id
    target_id: Id
    method_id: Id
    statement: Text
    assumptions: list[Text] = Field(min_length=1, max_length=32)
    checker: Id
    status: ProofStatus
    input_hash: Hash
    evidence: EvidenceFile
    domain: Text
    limitations: list[Text] = Field(min_length=1, max_length=32)

    @model_validator(mode='after')
    def certificate_registry(self):
        if self.status == 'PROVED':
            raise ValueError('No proof-certificate checker is registered; a result hash is not a proof')
        return self


class GeneratedArtifact(Strict):
    artifact_id: Id
    kind: Literal['RULEIR', 'JAVA', 'CATALA', 'JAR']
    target_id: Id
    source_hypothesis_id: Id
    bundle_hash: Hash
    evidence: EvidenceFile
    status: Literal['BUILT', 'CHECKED']
    limitations: list[Text] = Field(min_length=1, max_length=32)


class OpenQuestion(Strict):
    question_id: Id
    target_id: Id
    status: Literal['OPEN', 'ANSWERED', 'EXTENSION_REQUIRED', 'BLOCKED']
    reason: Text
    required_evidence: list[Text] = Field(min_length=1, max_length=32)


class Discrepancy(Strict):
    discrepancy_id: Id
    target_id: Id
    kind: Literal['METHOD_DISAGREEMENT', 'STALE_EVIDENCE', 'UNSUPPORTED_CLAUSE',
                  'UNAVAILABLE_METHOD', 'NOT_COMPARABLE', 'FORMAL_COUNTEREXAMPLE',
                  'SOURCE_GAP', 'REPAIR_REQUIRED']
    method_ids: list[Id] = Field(min_length=1, max_length=32)
    severity: Literal['INFO', 'MATERIAL', 'BLOCKING']
    disposition: Literal['OPEN', 'REPAIRED', 'RETAINED', 'EXPLAINED']
    explanation: Text


class AssuranceDossier(Strict):
    schema_version: Literal['proof-carrying-assurance.v3']
    dossier_id: Id
    question_id: Id
    target_description: Text
    target: dict
    target_hash: Hash
    source_packet_hash: Hash
    source_packet: EvidenceFile
    input_manifest: EvidenceFile
    upstream_inputs: list[EvidenceFile] = Field(min_length=1, max_length=512)
    hypotheses: list[InterpretationHypothesis] = Field(min_length=1, max_length=128)
    required_method_ids: list[Id] = Field(min_length=1, max_length=64)
    methods: list[MethodEvidence] = Field(min_length=1, max_length=128)
    obligations: list[ProofObligation] = Field(min_length=1, max_length=256)
    artifacts: list[GeneratedArtifact] = Field(max_length=512)
    open_questions: list[OpenQuestion] = Field(max_length=256)
    discrepancies: list[Discrepancy] = Field(max_length=256)
    legal_correctness_established: Literal[False] = False
    probability_of_legal_correctness: None = None
    release_eligible: Literal[False] = False

    @model_validator(mode='after')
    def bindings(self):
        if self.input_manifest not in self.upstream_inputs:
            raise ValueError('original input manifest binding is missing')
        paths = [ref.path for ref in self.upstream_inputs]
        if len(set(paths)) != len(paths):
            raise ValueError('duplicate upstream file path')
        for rows, name in [(self.hypotheses, 'hypothesis_id'), (self.methods, 'method_id'),
                           (self.obligations, 'obligation_id'), (self.artifacts, 'artifact_id'),
                           (self.open_questions, 'question_id'), (self.discrepancies, 'discrepancy_id')]:
            ids = [getattr(row, name) for row in rows]
            if len(set(ids)) != len(ids):
                raise ValueError('duplicate ' + name)
        if digest(self.target) != self.target_hash:
            raise ValueError('target hash mismatch')
        if self.target.get('source_packet_hash') != self.source_packet_hash or self.target.get('question_id') != self.question_id:
            raise ValueError('target source/question mismatch')
        hypotheses = {h.hypothesis_id: h for h in self.hypotheses}
        for h in self.hypotheses:
            if h.question_id != self.question_id or h.source_packet_hash != self.source_packet_hash:
                raise ValueError('hypothesis uses a different source or question')
            seen = {h.hypothesis_id}; parent = h.parent_id
            while parent is not None:
                if parent not in hypotheses or parent in seen:
                    raise ValueError('unknown or cyclic parent')
                seen.add(parent); parent = hypotheses[parent].parent_id
        methods = {m.method_id: m for m in self.methods}
        required = set(self.required_method_ids)
        if not required <= methods.keys() or len(required) != len(self.required_method_ids):
            raise ValueError('missing or duplicate required method')
        if len({methods[m].family_id for m in required}) < 2:
            raise ValueError('required evidence must contain two method families')
        for m in self.methods:
            if m.target_id != self.question_id or m.input_hash != self.target_hash:
                raise ValueError('method evidence targets a different question or input')
        valid = {self.question_id, *hypotheses}
        for o in self.obligations:
            if o.target_id not in valid or o.method_id not in methods or o.input_hash != self.target_hash:
                raise ValueError('unbound obligation')
            if o.evidence != methods[o.method_id].evidence:
                raise ValueError('obligation must refer to its checker evidence')
        for a in self.artifacts:
            if a.target_id != self.question_id or a.source_hypothesis_id not in hypotheses:
                raise ValueError('artifact has unknown target or hypothesis')
            if a.bundle_hash != hypotheses[a.source_hypothesis_id].rule_ir_hash:
                raise ValueError('artifact bundle differs from hypothesis')
        for q in self.open_questions:
            if q.target_id not in valid:
                raise ValueError('unknown question target')
        for d in self.discrepancies:
            if d.target_id not in valid or not set(d.method_ids) <= methods.keys():
                raise ValueError('unbound discrepancy')
        return self


def parse_dossier(value):
    return parse(AssuranceDossier, value)


def dossier_digest(value):
    return digest(parse_dossier(value))


def evidence_file(path, root):
    path, root = Path(path).resolve(), Path(root).resolve()
    if not path.is_file() or not path.is_relative_to(root):
        raise LegalMathError('E_REFERENCE', details='Evidence must be a retained file within root')
    return {'path': path.relative_to(root).as_posix(), 'sha256': raw_digest(path.read_bytes())}


def read_evidence(ref, root, *, json_value=True):
    ref = parse(EvidenceFile, ref)
    root = Path(root).resolve(); name = Path(ref['path'])
    if name.is_absolute() or '..' in name.parts:
        raise LegalMathError('E_REFERENCE', details='Unsafe evidence path')
    path = (root / name).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise LegalMathError('E_REFERENCE', details=ref['path'])
    data = path.read_bytes()
    if raw_digest(data) != ref['sha256']:
        raise LegalMathError('E_HASH_MISMATCH', details=ref['path'])
    return loads(data) if json_value else data


def validate_dossier(value, root=None):
    dossier = parse_dossier(value)
    blocking = []
    methods = {m['method_id']: m for m in dossier['methods']}
    required = set(dossier['required_method_ids'])
    for key in required:
        if methods[key]['status'] != 'AGREES':
            blocking.append({'method_id': key, 'status': methods[key]['status']})
    for o in dossier['obligations']:
        if o['status'] != 'CHECKED':
            blocking.append({'obligation_id': o['obligation_id'], 'status': o['status']})
    for q in dossier['open_questions']:
        if q['status'] != 'ANSWERED':
            blocking.append({'question_id': q['question_id'], 'status': q['status']})
    for d in dossier['discrepancies']:
        if d['severity'] in ('MATERIAL', 'BLOCKING') and d['disposition'] not in ('REPAIRED', 'EXPLAINED'):
            blocking.append({'discrepancy_id': d['discrepancy_id'], 'kind': d['kind']})
    if any(a['status'] != 'CHECKED' for a in dossier['artifacts']):
        blocking.append({'kind': 'UNCHECKED_ARTIFACT'})
    verified = False
    if root is not None:
        from .integration_verifier import verify_evidence
        verify_evidence(dossier, Path(root))
        verified = True
    else:
        blocking.append({'kind': 'EVIDENCE_FILES_NOT_VERIFIED'})
    groups = {}
    for m in dossier['methods']:
        for dependency in m['shared_dependencies']:
            groups.setdefault(dependency, []).append(m['method_id'])
    return {'status': 'BLOCKED_UNRESOLVED' if blocking else 'READY_FOR_REVIEW',
            'dossier_hash': dossier_digest(dossier), 'evidence_files_verified': verified,
            'blocking_reasons': blocking,
            'required_method_families': sorted({methods[m]['family_id'] for m in required}),
            'shared_dependency_groups': {d: sorted(ms) for d, ms in groups.items() if len(ms) > 1},
            'legal_correctness_established': False, 'probability_of_legal_correctness': None,
            'release_eligible': False}
