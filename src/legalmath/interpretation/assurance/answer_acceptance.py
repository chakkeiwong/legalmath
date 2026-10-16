"""Bind product acceptance to a retained manifest and original document bytes."""
from copy import deepcopy
import re

from ...canonical import digest
from .integration_contract import read_evidence
from .legal_locators import build_index, retained_html, validate_citation, require


def population_contract(inventory, question_ids):
    """Exact original populations; all-question targeting means mapping remains broad."""
    return {
        'acceptance_obligations': [{'id': r['obligation_id'], 'original_hash': r['original_hash'],
            'source_record_hash': digest(r), 'first_unresolved_step': r['first_unresolved_step'],
            'missing_premises': r['missing_premises'], 'question_ids': list(question_ids)}
            for r in inventory['original_obligations']],
        'original_readings': [{'id': r['reading_id'], 'source_record_hash': digest(r),
            'statement': r['retained_statement'], 'citations': r.get('citations', []),
            'question_ids': list(question_ids)} for r in inventory['original_readings']]}


def validate_manifest(value, questions, root):
    require(value.get('profile') == 'product-answer-acceptance.v1', 'Unknown answer acceptance profile')
    require(value['original_questions'] == questions, 'Acceptance changes original questions')
    require(value.get('acceptance_obligations') and 'cases' in value and 'source_documents' in value,
            'Acceptance lacks mandatory populations or source documents')
    qids = {q['question_id'] for q in questions}
    rows = value['acceptance_obligations'] + value.get('original_readings', [])
    require(len({r['id'] for r in rows}) == len(rows), 'Duplicate acceptance population')
    require(all(set(r['question_ids']) <= qids and r['question_ids'] for r in rows),
            'Acceptance obligation or reading lacks original target')
    cases = value['cases']
    require(len({r['case_id'] for r in cases}) == len(cases), 'Duplicate case identity')
    require(all('facts' in r and r['question_ids'] and set(r['question_ids']) <= qids for r in cases),
            'Case lacks retained facts or original target')
    if value.get('source_population') is not None:
        original = population_contract(read_evidence(value['source_population'], root), sorted(qids))
        # Permit a reviewed question mapping, but never altered or removed source records.
        for name, expected in original.items():
            supplied = value.get(name, [])
            require(len(supplied) == len(expected), 'Original population omitted')
            by_id = {r['id']: r for r in supplied}
            require(set(by_id) == {r['id'] for r in expected}, 'Original population substituted')
            for row in expected:
                require({k:v for k,v in by_id[row['id']].items() if k != 'question_ids'} ==
                        {k:v for k,v in row.items() if k != 'question_ids'}, 'Original population content changed')


def reading_quote_locations(manifest, packet):
    """Locate historical quotation text without silently changing its identity.

    An exact match is a location in this packet, not proof of edition identity,
    legal entailment, or equivalence of the old and new extraction units.
    """
    rows = []
    for reading in manifest.get('original_readings', []):
        for i, citation in enumerate(reading.get('citations', [])):
            quote = citation['quote']
            locations = []
            for unit in packet['units']:
                start = unit['text'].find(quote) if quote else -1
                while start != -1:
                    locations.append({'unit_id':unit['unit_id'],'start':start,'end':start+len(quote)})
                    start = unit['text'].find(quote, start + 1)
            rows.append({'reading_id':reading['id'],'citation_index':i,
                'original_reference_hash':digest(citation),'locations':locations,
                'status':'EXACT_TEXT_LOCATION' if len(locations)==1 else
                         'AMBIGUOUS_TEXT_LOCATION' if locations else 'UNRESOLVED',
                'source_identity_and_warrant_established':False})
    return {'packet_hash':digest(packet),'citations':rows}


def bind(request, root, reference):
    value = read_evidence(reference, root)
    validate_manifest(value, request['original_questions'], root)
    indexes = []
    for document in value['source_documents']:
        index = build_index(request['source_packet'], retained_html(document['source'], root),
            source_ref=document['source'], unit_ids=document['unit_ids'], root=root,
            numbering_profile=document.get('numbering_profile','ordered-lists'))
        indexes.append(index)
    request = deepcopy(request)
    request['answer_acceptance'] = value
    request['legal_indexes'] = indexes
    request['binding']['answer_acceptance'] = reference
    request['binding']['legal_index_hashes'] = [i['index_hash'] for i in indexes]
    request['binding_hash'] = digest(request['binding'])
    request['instructions'] += (' Legal paragraph and footnote mentions require legal_citations with exact '
        'field_path/start/end spans into the answer JSON (for example ["answers",0,"answer"]) and a source unit, exact quote, '
        'locator and approved index_hash. Use full literal source quotations. '
        'Use individual Pn or FNn references; do not use numbered ranges, lists with implicit prefixes or bracket-only numbers. '
        'A source without a verified numbering profile must be cited by exact unit quotation. '
        'Provide one case_assessments row per retained case with its exact case_id, digest of facts as facts_hash, '
        'question_ids, source support and contrary quotes, conclusion, reasons, assumptions and unresolved issues.')
    request['answer_acceptance']['case_bindings'] = {r['case_id']: digest(r['facts']) for r in value['cases']}
    request['answer_acceptance']['current_quote_locations'] = reading_quote_locations(value, request['source_packet'])
    return request


MENTION = re.compile(r'\b(?:P\s*(\d+)|(?:paragraphs?|paras?\.?)\s+(\d+)|FN\s*(\d+)|footnote\s+(\d+))\b', re.I)
IMPLICIT_NUMBER = re.compile(r'^\s*(?:[-–—/,]|and\b|to\b)\s*\d', re.I)
BRACKET_NUMBER = re.compile(r'\[\s*\d+(?:\s*[-–,]\s*\d+)*\s*\]')


def validate(answer, request, *, root=None):
    from pathlib import Path
    from .semantics import check_quotes
    root = Path(root or Path(__file__).resolve().parents[4]).resolve()
    from .answer_evidence import catalog, resolve
    if 'answer_acceptance' not in request:
        require(not answer.get('legal_citations') and not answer.get('case_assessments'),
                'Legal citations and cases require a bound acceptance manifest')
        return
    retained = read_evidence(request['binding']['answer_acceptance'], root)
    validate_manifest(retained, request['original_questions'], root)
    expected = deepcopy(retained)
    expected['case_bindings'] = {r['case_id']: digest(r['facts']) for r in retained['cases']}
    expected['current_quote_locations'] = reading_quote_locations(retained, request['source_packet'])
    require(request['answer_acceptance'] == expected and digest(request['binding']) == request['binding_hash'],
            'Bound acceptance or request changed')
    cases = {r['case_id']: r for r in retained['cases']}
    assessments = answer.get('case_assessments', [])
    require(len(assessments) == len(cases) and {r['case_id'] for r in assessments} == set(cases),
            'Missing, foreign or duplicate case assessment')
    for case in assessments:
        original = cases[case['case_id']]
        require(case['facts_hash'] == digest(original['facts']) and case['question_ids'] == original['question_ids'],
                'Case facts or target changed')
        check_quotes(case['support'] + case['contrary'], request['source_packet'])
    evidence = catalog(answer)
    indexes = {i['index_hash']: i for i in request['legal_indexes']}
    require(list(indexes) == request['binding']['legal_index_hashes'], 'Approved legal indexes changed')
    mentions = {}
    for fid, field in evidence['fields'].items():
        require(not BRACKET_NUMBER.search(field['text']), 'Ambiguous bracket locator; use individual Pn or FNn')
        for match in MENTION.finditer(field['text']):
            require(not IMPLICIT_NUMBER.match(field['text'][match.end():]),
                    'Implicit numbered range or list; cite each locator explicitly')
            number = next(v for v in match.groups() if v is not None)
            locator = ('P' if match.group(1) or match.group(2) else 'FN') + str(int(number))
            mentions[(fid, match.start(), match.end())] = locator
    covered = set()
    for citation in answer.get('legal_citations', []):
        fields = [fid for fid, row in evidence['fields'].items() if row['path'] == citation['field_path']]
        require(len(fields) == 1, 'Unknown legal citation field')
        span = {'field_id': fields[0], 'start': citation['start'], 'end': citation['end']}
        field = resolve(answer, evidence, span)
        key = (span['field_id'], span['start'], span['end'])
        require(key not in covered and mentions.get(key) == citation['locator'], 'Unbound or duplicate legal mention')
        index = indexes.get(citation['index_hash'])
        require(index is not None, 'Foreign legal index')
        validate_citation(request['source_packet'], index, unit_id=citation['unit_id'], quote=citation['quote'],
                          locator=citation['locator'], root=root, expected_index_hash=citation['index_hash'])
        # The actual supporting passage, not any passage in the same paragraph,
        # must belong to the answer's claim evidence for this question.
        claims = [c for a in answer['answers'] if field['question_id'] in (None, a['question_id'])
                  for c in a['claims']]
        if field['case_id'] is not None:
            claims = [c for c in assessments if c['case_id'] == field['case_id']]
        if len(field['path']) >= 4 and field['path'][0] == 'answers' and field['path'][2] == 'claims':
            claims = [answer['answers'][field['path'][1]]['claims'][field['path'][3]]]
        require(any(q['unit_id'] == citation['unit_id'] and citation['quote'] in q['quote']
                    for c in claims for q in c['support'] + c['contrary']), 'Locator is detached from claim support')
        covered.add(key)
    require(covered == set(mentions), 'Missing structured legal citation')
