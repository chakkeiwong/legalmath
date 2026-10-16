"""Optional bounded reviews of scoped evidence before original-question answers.

Exact accounting and quotations are checked; semantic fidelity is not certified.
The raw dossier is retained, and every model reduction is explicitly a proposal.
"""
from copy import deepcopy
from pathlib import Path
from typing import Literal

from pydantic import Field

from ...canonical import canonical, digest, raw_digest
from ...errors import LegalMathError
from ..contracts import Hash, Id, Strict, Text, parse
from ..search.models import Settings, Quote
from . import investigation_answer as answer
from .decomposition import compact_request
from .integration_contract import evidence_file
from .monitor import save
from .semantics import check_quotes
from .transport import CompactProvider

PROFILE = 'staged-investigation-answer.v1'
MARKER = '$scoped_record'


class Account(Strict):
    record_ids: list[Id] = Field(min_length=1, max_length=4096)
    disposition: Literal['RETAINED', 'CHALLENGED', 'UNRESOLVED', 'CONTEXT_ONLY']
    explanation: Text


class Finding(Strict):
    record_ids: list[Id] = Field(min_length=1, max_length=4096)
    question_ids: list[Id] = Field(min_length=1, max_length=4)
    conclusion: Text
    inference: Text
    support: list[Quote] = Field(max_length=32)
    contrary: list[Quote] = Field(max_length=32)
    assumptions: list[Text] = Field(max_length=32)
    unresolved: list[Text] = Field(max_length=32)
    cross_record_dependencies: list[Id] = Field(max_length=4096)


class Review(Strict):
    review_binding: Hash
    accounts: list[Account] = Field(min_length=1, max_length=4096)
    findings: list[Finding] = Field(min_length=1, max_length=64)
    legal_correctness_established: Literal[False]


class ReviewAccount(Strict):
    review_binding: Hash
    review_hash: Hash
    explanation: Text


class Synthesis(answer.AnswerProposal):
    stage_binding: Hash
    review_account: list[ReviewAccount] = Field(min_length=1, max_length=64)


def require(condition, details, code='E_REFERENCE'):
    if not condition:
        raise LegalMathError(code, details=details)


def registry(scoped):
    """Extract whole judgments/concerns, with every exact occurrence retained.

    Batch metadata (including disagreement and role receipts) is separately
    accounted for. The entire report reconstructs exactly, including duplicates.
    """
    records, by_content = {}, {}

    def retain(value, kind, path, batch=None):
        key = digest({'kind': kind, 'value': value, 'batch': batch})
        if key not in by_content:
            rid = 'r' + str(len(records)).zfill(4)
            by_content[key] = rid
            records[rid] = {'record_id': rid, 'kind': kind, 'batch': batch,
                            'value': deepcopy(value), 'origins': []}
        rid = by_content[key]
        records[rid]['origins'].append(path)
        return {MARKER: rid}

    def visit(value, path, batch):
        if isinstance(value, dict):
            require(MARKER not in value, 'Reserved record marker in original evidence')
            result = {}
            for k, v in value.items():
                if k in ('checks', 'additional_concerns') and isinstance(v, list):
                    result[k] = [retain(row, k, path + [k, i], batch) for i, row in enumerate(v)]
                else:
                    result[k] = visit(v, path + [k], batch)
            return result
        if isinstance(value, list):
            return [visit(v, path + [i], batch) for i, v in enumerate(value)]
        return deepcopy(value)

    require(isinstance(scoped.get('batches'), list) and scoped['batches'], 'Scoped batches missing')
    batches, contexts = [], {}
    for index, batch in enumerate(scoped['batches']):
        transformed = visit(batch, ['batches', index], index)
        contexts[str(index)] = transformed
        batches.append(retain(transformed, 'batch_context', ['batches', index], index))
    header = {k: deepcopy(v) for k, v in scoped.items() if k != 'batches'}
    root = {'header': retain(header, 'scoped_context', []), 'batches': batches}
    value = {'profile': PROFILE, 'source_hash': digest(scoped), 'records': records,
             'root': root, 'batch_contexts': contexts}
    require(restore(value) == scoped, 'Scoped registry is not reversible', 'E_INTEGRITY')
    return value


def restore(value):
    records = value['records']
    def expand(node, seen=frozenset()):
        if isinstance(node, dict):
            if set(node) == {MARKER}:
                rid = node[MARKER]
                require(rid in records and rid not in seen, 'Missing or cyclic scoped reference')
                return expand(records[rid]['value'], seen | {rid})
            return {k: expand(v, seen) for k, v in node.items()}
        if isinstance(node, list):
            return [expand(v, seen) for v in node]
        return deepcopy(node)
    result = {**expand(value['root']['header']), 'batches': expand(value['root']['batches'])}
    require(digest(result) == value['source_hash'], 'Scoped record changed', 'E_INTEGRITY')
    return result


def common_context(request):
    common = deepcopy(request)
    del common['investigation']['scoped']
    common['scoped_evidence_policy'] = (
        'The full scoped report remains in the bound dossier. Assigned raw judgments, concerns '
        'and batch metadata are reviewed separately. Other batch contents are not available in '
        'this request: cross-record uncertainty must stay explicit. Final synthesis sees model '
        'reviews, not every raw judgment; these are fallible reductions, not certified evidence.')
    return common


def review_request(common, index, record_ids):
    selected = [index['records'][rid] for rid in record_ids]
    batches = sorted({str(r['batch']) for r in selected if r['batch'] is not None})
    binding = digest({'request': digest(common), 'scoped_source': index['source_hash'], 'records': record_ids,
                      'implementation': raw_digest(Path(__file__).read_bytes())})
    return {**deepcopy(common), 'task': 'REVIEW_SCOPED_EVIDENCE', 'review_binding': binding,
            'records': deepcopy(selected),
            'batch_contexts': {k: deepcopy(index['batch_contexts'][k]) for k in batches},
            'registry_ids': list(index['records']),
            'review_instructions': (
                'Review every assigned record against the full source, readings, criticism and '
                'original questions. Account for assigned record_ids exactly once, grouping only '
                'where a shared explanation is meaningful. Distinguish support from inference, '
                'assumptions and unresolved premises. Preserve contrary reasoning and identify '
                'cross-record dependencies. References using $scoped_record identify retained '
                'records; an unassigned referenced record is not silently available or resolved. '
                'Metadata and invocation counts do not settle legal questions. Return findings '
                'with exact source quotes and preserve unresolved reading/authority differences. '
                'Do not infer legal truth from model agreement or tool PASS.')}


def partition(request, *, maximum_input_bytes=200000, maximum_batches=64):
    require(type(maximum_batches) is int and 1 <= maximum_batches <= 64, 'Batch cap', 'E_RESOURCE_LIMIT')
    require(type(maximum_input_bytes) is int and 1000 <= maximum_input_bytes <= 200000,
            'Input cap', 'E_RESOURCE_LIMIT')
    index = registry(request['investigation']['scoped'])
    common = common_context(request)
    batches, pending = [], []
    def size(ids):
        return len(canonical(compact_request(review_request(common, index, ids), profile='v2')))
    # A cheap fixed-context failure precedes quadratic incremental packing.
    require(size([]) <= maximum_input_bytes, {'stage': 'COMMON_CONTEXT', 'wire_bytes': size([])},
            'E_RESOURCE_LIMIT')
    for rid in index['records']:
        if size(pending + [rid]) > maximum_input_bytes:
            require(bool(pending), {'stage': 'RECORD_CAPACITY', 'record_id': rid,
                                   'wire_bytes': size([rid])}, 'E_RESOURCE_LIMIT')
            batches.append(pending)
            pending = []
        require(size(pending + [rid]) <= maximum_input_bytes,
                {'stage': 'RECORD_CAPACITY', 'record_id': rid, 'wire_bytes': size([rid])},
                'E_RESOURCE_LIMIT')
        pending.append(rid)
    if pending:
        batches.append(pending)
    require(len(batches) <= maximum_batches, {'stage': 'BATCH_CAPACITY', 'batches': len(batches)},
            'E_RESOURCE_LIMIT')
    assigned = [rid for batch in batches for rid in batch]
    require(assigned == list(index['records']), 'Record assignment lost or reordered evidence', 'E_INTEGRITY')
    return {'profile': PROFILE, 'original_request_hash': digest(request), 'registry': index,
            'common': common, 'batches': batches, 'wire_bytes': [size(b) for b in batches],
            'maximum_input_bytes': maximum_input_bytes, 'maximum_batches': maximum_batches}


def validate_review(value, request):
    value = parse(Review, value)
    require(value['review_binding'] == request['review_binding'], 'Changed review binding')
    expected = {r['record_id'] for r in request['records']}
    actual = [rid for a in value['accounts'] for rid in a['record_ids']]
    require(len(actual) == len(expected) and set(actual) == expected, 'Missing or duplicate record account')
    question_ids = {q['question_id'] for q in request['original_questions']}
    for f in value['findings']:
        require(set(f['record_ids']) <= expected and set(f['question_ids']) <= question_ids,
                'Finding outside assigned evidence/questions')
        require(set(f['cross_record_dependencies']) <= set(request['registry_ids']), 'Unknown dependency')
        check_quotes(f['support'] + f['contrary'], request['source_packet'])
    return value


def synthesis_request(original, prepared, reviews):
    expected = [review_request(prepared['common'], prepared['registry'], b) for b in prepared['batches']]
    require(len(reviews) == len(expected), 'Missing batch review')
    validated = [validate_review(v, r) for v, r in zip(reviews, expected)]
    result = {**deepcopy(prepared['common']), 'task': 'SYNTHESIZE_INVESTIGATION_ANSWER',
              'reviews': validated,
              'stage_binding': digest({'original_request': digest(original), 'registry': digest(prepared['registry']),
                                       'review_hashes': [digest(v) for v in validated]}),
              'synthesis_instructions': (
                  'Answer the exact original questions using the sources, all readings, criticism '
                  'and every review. Explicitly resolve or retain cross-batch dependencies, '
                  'contrary rules, exceptions and disagreements. Reviews are fallible model '
                  'proposals; identifier coverage cannot establish faithful reduction. The raw '
                  'scoped dossier remains retained but is not all supplied in this request. '
                  'Account for every review by review_binding and review_hash with an explanation. '
                  'Return stage_binding unchanged and the original answer contract. Preserve '
                  'all source/extraction qualifications and any unresolved legal standard.')}
    result['review_hashes'] = {v['review_binding']: digest(v) for v in validated}
    return result


def validate_synthesis(value, request, original):
    value = parse(Synthesis, value)
    require(value['stage_binding'] == request['stage_binding'], 'Changed synthesis binding')
    accounts = value['review_account']
    require(len(accounts) == len(request['review_hashes'])
            and len({a['review_binding'] for a in accounts}) == len(accounts)
            and {a['review_binding']: a['review_hash'] for a in accounts} == request['review_hashes'],
            'Missing, duplicate or changed synthesis review account')
    answer.validate_answer({k: v for k, v in value.items() if k not in ('stage_binding', 'review_account')}, original)
    return value


def propose(root, dossier_ref, provider, directory, *, maximum_batches=64,
            maximum_review_output_bytes=8000, settings=None, **arguments):
    """No retries, no implicit recursive reduction, and evidence rechecked per call."""
    settings = settings or Settings(max_input_bytes=200000, max_output_bytes=200000)
    settings = Settings(**parse(Settings, settings.model_dump()))
    require(type(maximum_review_output_bytes) is int and 1000 <= maximum_review_output_bytes <= 8000,
            'Review output cap', 'E_RESOURCE_LIMIT')
    root, directory = Path(root).resolve(), Path(directory).resolve()
    require(directory.is_relative_to(root), 'Output leaves evidence root')
    directory.mkdir(parents=True, exist_ok=False)
    result = {'profile': PROFILE, 'provider_calls': 0, 'legal_quality_evaluated': False,
              'tool_consideration_verified': False, 'legal_correctness_established': False,
              'release_eligible': False}
    try:
        original = answer.prepare_request(root, dossier_ref, **arguments)
        save(directory / 'original-request.json', original)
        prepared = partition(original, maximum_input_bytes=settings.max_input_bytes, maximum_batches=maximum_batches)
        save(directory / 'partition.json', prepared)
        def unchanged():
            require(answer.prepare_request(root, dossier_ref, **arguments) == original,
                    'Evidence changed during staged consumption', 'E_STALE_REVIEW')
        transport = CompactProvider(provider, directory / 'transport')
        reviews = []
        for i, ids in enumerate(prepared['batches']):
            unchanged()
            request = review_request(prepared['common'], prepared['registry'], ids)
            save(directory / f'review-{i:03}-request.json', request)
            result['provider_calls'] += 1
            response = transport.complete(request, Review.model_json_schema(), settings.model_copy(
                update={'max_output_bytes': maximum_review_output_bytes}))
            save(directory / f'review-{i:03}-raw.json', {'value': response.value, 'provenance': response.provenance})
            require(len(canonical(response.value)) <= maximum_review_output_bytes,
                    'Review output exceeds cap', 'E_RESOURCE_LIMIT')
            unchanged()
            reviews.append(validate_review(response.value, request))
        request = synthesis_request(original, prepared, reviews)
        save(directory / 'synthesis-request.json', request)
        wire_bytes = len(canonical(compact_request(request, profile='v2')))
        result.update(review_batches=len(reviews), synthesis_wire_bytes=wire_bytes)
        require(wire_bytes <= settings.max_input_bytes, {'stage': 'SYNTHESIS_CAPACITY', 'wire_bytes': wire_bytes},
                'E_RESOURCE_LIMIT')
        unchanged()
        result['provider_calls'] += 1
        response = transport.complete(request, Synthesis.model_json_schema(), settings)
        save(directory / 'synthesis-raw.json', {'value': response.value, 'provenance': response.provenance})
        require(len(canonical(response.value)) <= settings.max_output_bytes, 'Answer output cap', 'E_RESOURCE_LIMIT')
        unchanged()
        value = validate_synthesis(response.value, request, original)
        save(directory / 'answer.json', value)
        result.update(status='STRUCTURALLY_VALID_PROPOSAL', answer=evidence_file(directory / 'answer.json', root))
    except LegalMathError as exc:
        result.update(status='CAPACITY_BLOCKED' if exc.code == 'E_RESOURCE_LIMIT' else 'REJECTED',
                      error=exc.code, details=exc.details)
    except Exception as exc:
        result.update(status='FAILED', error=type(exc).__name__, details=str(exc))
        save(directory / 'result.json', result)
        raise
    save(directory / 'result.json', result)
    return result
