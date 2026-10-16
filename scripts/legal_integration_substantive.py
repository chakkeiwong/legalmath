"""Original-source targets, ownership diagnostics and bounded product qualification."""
from copy import deepcopy
from pathlib import Path
import re
import zipfile
from xml.etree import ElementTree as ET

from scripts.legal_integration_master import ROOT, DOC, BASE, PRIOR, QUESTIONS, TOOLS, TOKENIZER
from scripts.legal_mission_execution import read, save, ref, verify, require
from legalmath.canonical import digest


def quote(packet, text):
    matches = []
    pattern = re.compile(r'\s+'.join(re.escape(p) for p in text.split()))
    for unit in packet['units']:
        for match in pattern.finditer(unit['text']):
            matches.append({'unit_id': unit['unit_id'], 'quote': match.group()})
    require(len(matches) == 1, 'Target quotation is absent or ambiguous: ' + text[:70])
    return matches[0]


def prepare_targets(envelope, directory):
    packet = envelope['source_packet']
    retained = read(ROOT / 'artifacts/legal-mission-control/2026-10-09/continuation/product-contribution/reviewed/prepared.json')
    def rebind(node):
        if isinstance(node, dict):
            if 'quote' in node and 'unit_id' in node:
                return {**node, **quote(packet, node['quote'])}
            if 'source_unit_ids' in node:
                result = {k: rebind(v) for k, v in node.items()}
                # Fact source identities follow the actual citations of the
                # corresponding retained candidate, never old extraction IDs.
                result['source_unit_ids'] = []
                return result
            return {k: rebind(v) for k, v in node.items()}
        if isinstance(node, list): return [rebind(v) for v in node]
        return node
    common = rebind(retained)
    for candidate in common['candidates'].values():
        if candidate.get('formalization'):
            for fact in candidate['formalization']['facts']:
                fact['source_unit_ids'] = sorted({q['unit_id'] for q in candidate['citations']})
    # The supported subset is explicit: conditional dependency/trigger checks,
    # never an executable resolution of an undefined legal standard.
    p14_quotes = [quote(packet, s) for s in (
        'Product Providers should confirm and, upon SFC’s request, demonstrate to the SFC’s satisfaction the management and operational soundness of the tokenisation arrangement, record keeping of ownership and the integrity of the smart contracts5.',
        'Product Providers should confirm and demonstrate to the SFC that, at a minimum, they comply with the requirements as set out in paragraphs 10 to 13 above and the smart contracts are not subject to any contract vulnerabilities or security flaws with a high level of confidence.')]
    gate_quotes = [quote(packet, s) for s in (
        'The customers should be regarded as NCCs unless there is evidence to show that they have accessed or used the Platform to effect the transactions;',
        'The transactions described in the 7th scenario did not exist and the customers should not be regarded as NCC.')]
    def candidate(cid, statement, names, result, citations, limitation):
        return {'local_id': cid, 'family': 'dependencies', 'subject': 'Declared conditional source question',
            'statement': statement, 'distinction': limitation, 'citations': citations,
            'assumptions': ['The actor, period, source applicability and stated hypothetical facts are established separately.'],
            'questions': ['What source and facts establish each predicate?'],
            'formalization': {'facts': [{'name': name, 'type': 'bool', 'meaning': meaning,
                'unit': 'truth value', 'source_unit_ids': sorted({q['unit_id'] for q in citations}),
                'requires_judgment': True} for name, meaning in names],
                'scope': 'true', 'result': result, 'result_type': 'bool'}}
    p14 = candidate('p14.requested-demonstration',
        'Under the main-text conditional reading, an established request activates demonstration; '
        'a no-request result answers activation only, with footnote-based standing-duty rivals retained.',
        [('request', 'An applicable SFC demonstration request is established.'),
         ('satisfactory', 'The demonstration meets the applicable object and SFC-satisfaction standard.')],
        '(or (not request) satisfactory)', p14_quotes,
        'True without a request means only this conditional demonstration predicate is satisfied; '
        'it does not establish confirmation, underlying compliance or the truth of the selected reading.')
    gatecoin = candidate('gatecoin.scenarios-one-to-four',
        'Within the court’s first four scenarios, the direction treats the customer as NCC '
        'subject to contrary evidence of access or use to effect the transactions.',
        [('category', 'The event is established to be within scenarios one to four in this liquidation.'),
         ('contrary', 'Evidence of customer access/use to effect the transaction is established.')],
        '(and category (not contrary))', gate_quotes,
        'Only the stated defeasible direction is represented. Unknown contrary evidence is not false. '
        'Scenario seven, general consent, trust formation and transfer to a Product Provider are unsupported.')
    targets = {}
    for qid, candidates, citations, caution in (
        ('p10', common['candidates'], common['candidates']['evidence.dependencies']['citations'],
         'Retained reconciliation counterexample; undefined P10 discharge standards remain unformalized.'),
        ('evidence', common['candidates'], common['candidates']['evidence.dependencies']['citations'],
         'Establishing evidence dependencies is not sufficient for proper records or adequate supervision.'),
        ('p14', {p14['local_id']: p14}, p14_quotes,
         'Requested demonstration versus standing-footnote rival; no-request is not whole compliance.'),
        ('gatecoin', {gatecoin['local_id']: gatecoin}, gate_quotes,
         'Direction limited to scenarios one to four; scenario seven and target transfer remain unresolved.')):
        targets[qid] = {'question': next(q['text'] for q in envelope['original_questions'] if q['question_id'] == qid),
            'candidates': candidates, 'citations': citations, 'warrant_limit': caution,
            'proposals': common['proposals'] if qid in ('p10', 'evidence') else {},
            'source_packet_hash': digest(packet), 'actual_answer_effect': 'NOT_EVALUATED'}
    path = directory / 'original-targets.json'
    save(path, targets)
    save(directory / 'target-review.json', {'targets': ref(ROOT, path),
        'review': ref(ROOT, DOC / 'remaining-work-source-review-2026-10-13.md'),
        'supported': 'Exact restricted conditional targets; source predicates require judgment.',
        'unsupported': 'Complete formalization of each original legal question; no scope-only tool rejection.'})
    return {'targets': ref(ROOT, path), 'target_review': ref(ROOT, directory / 'target-review.json')}


def source_output():
    program = read(ROOT / DOC / 'integration-master.json')
    task = next(t for t in program['tasks'] if t['id'] == 'sources')
    return ROOT / Path(task['deliverable']).parent


def native_targets(tool, envelope, directory):
    from scripts.legal_independent_tools import IndependentProductToolBackend
    from legalmath.interpretation.assurance.arguments import evaluate_criticism
    from scripts.legal_mission_logical_english import compile_reading, conditional_values, evaluate
    from itertools import product
    targets = read(source_output() / 'original-targets.json')
    backend = IndependentProductToolBackend([tool])
    before = backend.identity()
    outputs = {}
    for qid, target in targets.items():
        work = directory / qid
        if tool == 'bm25':
            outputs[qid] = backend.retrieval(envelope['source_packet'], {'question': target['question']}, work)
        elif tool in ('legalruleml', 'logical-english'):
            outputs[qid] = backend.candidates(envelope['source_packet'], target['candidates'], work)
        elif target['proposals']:
            outputs[qid] = {}
            for name, proposal in target['proposals'].items():
                evaluation = evaluate_criticism(proposal, envelope['source_packet'], list(target['candidates']))
                outputs[qid][name] = backend.criticism(envelope['source_packet'],
                    {'proposal': proposal, 'evaluation': evaluation}, work / name)
        else:
            outputs[qid] = {'status': 'TARGET_REQUIRED', 'reason': 'No reviewed original-question argument graph yet.'}
    require(before == backend.identity(), 'Native dependency content changed during execution')
    save(directory / 'native.json', {'tool': tool, 'output': outputs, 'identity': before,
        'targets': ref(ROOT, source_output() / 'original-targets.json'), 'answer_effect_evaluated': False})
    def failed(value):
        if isinstance(value, dict): return value.get('status') == 'FAILED' or any(failed(v) for v in value.values())
        if isinstance(value, list): return any(failed(v) for v in value)
        return False
    require(not failed(outputs), 'Supported original-source target failed in native adapter')
    return {'native_result': ref(ROOT, directory / 'native.json'), 'scope': 'Restricted source-bound original-question targets',
            '_conclusion': tool + ': actual native source-bound targets executed; complete matched-answer effects remain open.'}


def ownership_audit(envelope, directory):
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    tag = '{' + ns['w'] + '}'
    summary = []
    for source in read(ROOT / PRIOR / 'gatecoin-source-provenance.json'):
        previous = read(ROOT / BASE / 'reviewed-reopening/corpus-audit' / (source['name'] + '-numbering.json'))
        for key in ('source', 'derivative', 'rendered'): verify(ROOT, previous[key])
        with zipfile.ZipFile(ROOT / previous['source']['path']) as archive:
            body = ET.fromstring(archive.read('word/document.xml'))
            paragraphs = body.findall('.//w:body/w:p', ns)
            notes = ET.fromstring(archive.read('word/footnotes.xml'))
            rows, used = [], set()
            for i, lead in enumerate(previous['main_leads']):
                start = lead['body_paragraph_position']
                end = previous['main_leads'][i + 1]['body_paragraph_position'] if i + 1 < len(previous['main_leads']) else len(paragraphs)
                pieces = []
                for position in range(start, end):
                    p = paragraphs[position]
                    text = ''.join(x.text or '' for x in p.findall('.//w:t', ns))
                    if not text.strip(): continue
                    num = p.find('w:pPr/w:numPr', ns)
                    pieces.append({'position': position, 'text': text,
                        'numbering': {x.tag.split('}')[-1]: x.get(tag + 'val') for x in num} if num is not None else None,
                        'footnote_ids': [x.get(tag + 'id') for x in p.findall('.//w:footnoteReference', ns)]})
                    used.add(position)
                rows.append({'locator': lead['locator'], 'components': pieces,
                    'ownership': 'Candidate main-number interval; headings/annexure boundary require review'})
            note_rows = [{'id': note.get(tag + 'id'), 'text': '\n'.join(''.join(t.text or '' for t in p.findall('.//w:t', ns))
                for p in note.findall('.//w:p', ns))} for note in notes if int(note.get(tag + 'id')) > 0]
        retained = (ROOT / previous['derivative']['path']).read_text()
        normalized = ' '.join(retained.split())
        for row in rows:
            for piece in row['components']:
                piece['derivative_occurrences'] = normalized.count(' '.join(piece['text'].split()))
                require(piece['derivative_occurrences'] > 0, 'Original paragraph component missing from derivative')
        linked = {note for row in rows for p in row['components'] for note in p['footnote_ids']}
        require(linked <= {r['id'] for r in note_rows}, 'Missing linked footnote')
        path = directory / (source['name'] + '-ownership.json')
        save(path, {'original': previous['source'], 'derivative': previous['derivative'], 'rendered': previous['rendered'],
            'paragraph_intervals': rows, 'footnotes': note_rows, 'linked_footnotes': sorted(linked, key=int),
            'unassigned_body_paragraphs': [i for i, p in enumerate(paragraphs) if i not in used and
                ''.join(t.text or '' for t in p.findall('.//w:t', ns)).strip()],
            'legal_locator_qualified': False,
            'remaining': ['Review heading/annexure boundaries and numbering restarts before assigning all interval text to a legal paragraph.',
                          'Map rendered footnote display numbers to OOXML IDs; these are not automatically equal.']})
        summary.append({'name': source['name'], 'main_intervals': len(rows),
            'body_components': sum(len(r['components']) for r in rows), 'footnotes': len(note_rows),
            'evidence': ref(ROOT, path)})
    save(directory / 'ownership-summary.json', {'judgments': summary,
        'full_corpus_qualified': False, 'handbook': 'Exact retained page text; clause/annexure ownership remains unqualified.'})
    return {'ownership': ref(ROOT, directory / 'ownership-summary.json'), '_node_status': 'BLOCKED',
            '_conclusion': 'All retained judgment paragraph components and footnote links mapped; rendered label/heading/annexure ownership remains unqualified.'}


def legal_review(qid, envelope, directory):
    from scripts.legal_integration_acceptance import validate_inventory
    targets = read(source_output() / 'original-targets.json')
    individual = read(ROOT / PRIOR / 'individual-statement-review.json')
    acceptance = envelope['answer_acceptance']
    rows = []
    for field, kind, old_field in (('acceptance_obligations', 'obligation', 'obligations'), ('original_readings', 'reading', 'readings')):
        old_rows = {r['id']: r for r in individual[old_field]}
        for row in acceptance[field]:
            old = old_rows[row['id']]
            if kind == 'reading':
                require(old['statement'] == row['statement'] and old['statement_hash'] == digest(row['statement']),
                        'Individual reading changed')
            else:
                require(old['requests'] == [r['statement'] for r in row['missing_premises']], 'Individual premise population changed')
            rows.append({'id': row['id'], 'kind': kind, 'disposition': 'retained', 'reason': old['review'],
                'reviewed': True, 'review_evidence': [ref(ROOT, PRIOR / 'individual-statement-review.json'),
                    ref(ROOT, DOC / 'remaining-work-source-review-2026-10-13.md')],
                'evidence': [ref(ROOT, BASE / 'remaining-work/combined-envelope.json')],
                'question_impact': old['review'],
                'reopen_when': 'A specific standard, contrary authority, source warrant or stated factual premise changes.',
                'fulfillment': 'OPEN; retained for conditional assessment, not declared satisfied'})
    document = {'profile': 'legal-original-inventory-review.v1', 'records': rows,
        'method': 'Carry forward individually reasoned retained dispositions after exact statement/premise identity check; no population deletion or legal closure.'}
    validate_inventory(document, [r['id'] for r in acceptance['acceptance_obligations']],
        [r['id'] for r in acceptance['original_readings']], ROOT)
    save(directory / 'inventory-dispositions.json', document)
    source_review = ROOT / DOC / 'remaining-work-source-review-2026-10-13.md'
    research = read(ROOT / PRIOR / 'research-evidence.json')
    save(directory / 'conditional-analysis.json', {'question_id': qid, 'question': targets[qid]['question'],
        'target': targets[qid], 'source_review': ref(ROOT, source_review),
        'individual_inventory': ref(ROOT, directory / 'inventory-dispositions.json'),
        'dated_research': ref(ROOT, PRIOR / 'research-evidence.json'),
        'research_scope': [{k: s[k] for k in ('query', 'response_dates', 'limitation')} for s in research['searches']],
        'coverage_correction': 'The original 46 obligation tags all name p10/evidence. Four explicitly contain the P14/FN5 issue; historical counts do not establish four-question coverage.',
        'legal_disposition': 'CONDITIONAL; unresolved sources and actual facts remain stated',
        'current_law_exhaustive': False, 'actual_tool_answer_effect': False})
    return {'analysis': ref(ROOT, directory / 'conditional-analysis.json'),
            'inventory': ref(ROOT, directory / 'inventory-dispositions.json'),
            '_conclusion': qid + ': original source-bound conditional targets and individual retained dispositions verified; factual and governing-standard conclusions remain conditional.'}


def qualify(qid, envelope, directory):
    from legalmath.interpretation.assurance.bounded_product import BoundedProduct, NOTE, AUDIT
    from legalmath.interpretation.assurance.bounded_context import tokenizer
    from scripts.legal_integration_rehearsal import UnresolvedProvider
    class MeasureReference(UnresolvedProvider):
        reference_transport = True
    product = BoundedProduct(ROOT, directory / 'product-construction', MeasureReference(), envelope,
        tokenizer(ROOT / TOKENIZER), active_questions=[qid])
    packets, blocks = product.reading_packets()
    measurements, failures = [], []
    for i, packet in enumerate(packets):
        if not any(qid in product.acquisition_questions(r) for r in packet['request']['records']): continue
        try: measurements.append({'packet': i, **product.dispatch.measure(packet['request'], packet['schema'])})
        except Exception as exc: failures.append({'packet': i, 'reason': str(getattr(exc, 'details', None) or exc)})
    save(directory / 'capacity.json', {'actual_product_constructed': True, 'question': qid,
        'measurements': measurements, 'construction_blocks': blocks, 'request_failures': failures,
        'live_calls': 0, 'service_framing': 'UNMEASURED', 'semantic_preservation': 'UNQUALIFIED',
        'final_answer_review': 'Requires actual generated original-answer population; input compaction has local regression coverage.'})
    return {'capacity': ref(ROOT, directory / 'capacity.json'), 'measured_requests': len(measurements),
            '_node_status': 'BLOCKED', '_conclusion': qid + ': actual product constructs with rebuilt indexes; ' +
            str(len(failures) + len(blocks)) + ' local request-capacity blockers; live semantics/final answer review remain unqualified.'}
