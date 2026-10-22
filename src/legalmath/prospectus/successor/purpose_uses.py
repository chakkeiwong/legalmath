"""Source-discovered inflected uses and proposed printed-purpose connections."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from .anchors import fields
from .contracts import digest
from .definition_discovery import attached, normalized
from .reference_addresses import body_projection
from .unquoted_definitions import discover as declarations_from_source

KEY = 'purpose_use_discovery'
VERSION = 'purpose-use-discovery.v1'
SPEC_SHA256 = '1c517441a4d8790e051359bce724817224e5ed9e4ceab3d2460ce78b5b1043ba'
ENDINGS = ('en', 'er', 'es', 'em', 'e')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def family(label):
    words = label.split()
    if len(words) != 2 or not words[0].islower():
        return None
    adjective, noun = words
    # Simple regex case matching preserves sharp-s; full case folding would expand it.
    for ending in ENDINGS:
        if adjective.endswith(ending) and len(adjective) - len(ending) >= 3:
            return adjective[:-len(ending)].lower(), noun.lower()
    return None


def checked_index(index, text):
    require(type(index) is list and len(index) <= 4096, 'Bounded source index required')
    for node in index:
        require(type(node) is dict and {'section', 'path', 'start', 'end', 'printed_label'} <= set(node),
                'Incomplete source index node')
        require(type(node['section']) is str and type(node['path']) is list
                and all(type(x) is str for x in node['path']), 'Invalid printed address')
        require(type(node['start']) is int and type(node['end']) is int
                and 0 <= node['start'] < node['end'] <= len(text), 'Invalid index interval')
        require(type(node['printed_label']) is str and node['printed_label']
                and text[node['start']:node['start'] + len(node['printed_label'])] == node['printed_label'],
                'Printed index label differs from selected source')


def discover(request, index):
    syntax = declarations_from_source(request)
    text = request['text']
    checked_index(index, text)
    declarations, unsupported = [], []
    for source in syntax['candidates']:
        if source['kind'] != 'PURPOSE_CONDITIONED_AMOUNT':
            continue
        group = family(source['label'])
        if group is None:
            unsupported.append({'start': source['start'], 'end': source['end'],
                                'reason': 'UNSUPPORTED_ADJECTIVE_NOUN_FORM'})
            continue
        address = source['printed_scope_address']
        targets = [node for node in index if node['section'] == address['section']
                   and node['path'] == [address['paragraph']]]
        status = ('EXACT_PRINTED_ADDRESS' if len(targets) == 1 else
                  'MISSING_PRINTED_ADDRESS' if not targets else 'AMBIGUOUS_PRINTED_ADDRESS')
        declarations.append({'declaration_start': source['start'], 'declaration_end': source['end'],
            'raw': source['raw'], 'term': deepcopy(source['term']), 'restriction': deepcopy(source['scope']),
            'value': deepcopy(source['value']), 'printed_scope_address': deepcopy(address),
            'family': {'adjective_stem': group[0], 'noun': group[1]},
            'address_status': status, 'targets': deepcopy(targets)})
    families = {}
    for declaration in declarations:
        group = tuple(declaration['family'][k] for k in ('adjective_stem', 'noun'))
        families.setdefault(group, []).append(declaration)
    occurrences = []
    for region in request['regions']:
        if not region['selected'] or region['language'] != request['language']:
            continue
        plain, spans = normalized(text[region['start']:region['end']], region['start'])
        for (stem, noun), members in families.items():
            pattern = re.compile(re.escape(stem) + r'(?:en|er|es|em|e) ' + re.escape(noun), re.IGNORECASE)
            for match in pattern.finditer(plain):
                x, y = match.span()
                if attached(plain[x - 1] if x else '') or attached(plain[y:y + 1]):
                    continue
                a, b = spans[x][0], spans[y - 1][1]
                if re.search(r'\r?\n[ \t]*\r?\n', text[a:b]):
                    continue
                own = [d['declaration_start'] for d in members
                       if (d['term']['start'], d['term']['end']) == (a, b)]
                heading = any(node['start'] <= a < b < node['end']
                    and text[node['start']:a].strip() == node['printed_label'].strip()
                    and text[b:b + 1] == '.' for node in index)
                if own:
                    role, selected, status = 'DECLARATION_TERM', own, 'SELF_DECLARATION'
                elif heading:
                    role, selected, status = 'HEADING_CANDIDATE', [], 'NON_OPERATIVE_HEADING'
                else:
                    selected = [d['declaration_start'] for d in members if d['address_status'] == 'EXACT_PRINTED_ADDRESS'
                                and d['targets'][0]['start'] <= a < b <= d['targets'][0]['end']]
                    role = 'USE_CANDIDATE'
                    status = ('UNIQUE_PRINTED_PURPOSE' if len(selected) == 1 else
                              'AMBIGUOUS_PRINTED_PURPOSE' if selected else 'UNRESOLVED_PRINTED_PURPOSE')
                occurrences.append({'start': a, 'end': b, 'raw': text[a:b], 'region': region['id'],
                    'family': {'adjective_stem': stem, 'noun': noun}, 'role': role, 'status': status,
                    'compatible_declaration_starts': [d['declaration_start'] for d in members],
                    'selected_declaration_starts': selected, 'review_required': True,
                    'governing_scope': None, 'meaning': None, 'legal_meaning_established': False})
                require(len(occurrences) <= 4096, 'Purpose use bound exceeded')
    occurrences.sort(key=lambda row: (row['start'], row['end']))
    require(len({(r['start'], r['end']) for r in occurrences}) == len(occurrences), 'Ambiguous occurrence family')
    return {'version': VERSION, 'text_sha256': request['text_sha256'], 'language': request['language'],
        'declarations': declarations, 'occurrences': occurrences, 'unsupported_declarations': unsupported,
        'scope_admitted': False, 'meaning_admitted': False, 'general_recall_established': False,
        'automatic_legal_interpretation': False,
        'unsupported': ['Other morphology and noun inflection', 'Implicit and global precedence',
                        'Unlisted title syntax', 'Unindexed printed addresses', 'Legal governing scope']}


def reconciliation(result, ordinary):
    supplement = ordinary['definition_sources']['application_supplement']
    rules = supplement['rules']
    applications = {(r['start'], r['end']): r for r in supplement['applications']}
    links = {d['declaration_start']: [r['id'] for r in rules if any(
        p['start'] <= d['declaration_start'] < d['declaration_end'] <= p['end'] for p in r['premises'])]
        for d in result['declarations']}
    rows = []
    for row in result['occurrences']:
        app = applications.get((row['start'], row['end']))
        proposed = sorted({r for start in row['selected_declaration_starts'] for r in links[start]})
        if app is None:
            status = 'NOT_PRESENT_IN_REVIEWED_APPLICATIONS'
        elif app['rule'] is None and not proposed:
            status = 'AGREES_ON_EXPLICIT_REMAINDER'
        elif proposed == [app['rule']] and (
                (row['role'] == 'DECLARATION_TERM' and app['role'] == 'DECLARATION') or
                (row['role'] == 'USE_CANDIDATE' and app['role'] == 'OPERATIVE_USE')):
            status = 'AGREES_WITH_REVIEWED_CONDITIONAL_BINDING'
        else:
            status = 'DISAGREEMENT_REQUIRES_REVIEW'
        rows.append({'start': row['start'], 'end': row['end'],
            'reviewed_application_id': app['id'] if app else None,
            'reviewed_role': app['role'] if app else None, 'reviewed_rule': app['rule'] if app else None,
            'proposed_reviewed_rule_ids': proposed, 'status': status,
            'meaning_derived': False, 'independent_legal_proof': False})
    return {'declaration_rule_candidates': {str(k): v for k, v in links.items()}, 'occurrences': rows,
            'reviewed_matrix_used_to_select_occurrences': False,
            'reviewed_matrix_changed': False, 'new_semantic_capability': False}


def content(products, ordinary):
    assembly = products['P2']['payload']['assembly']
    text = assembly['continuous_text']
    result = discover({'text': text, 'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
        'language': 'de', 'regions': [{'id': 'selected-contract', 'start': 0, 'end': len(text),
                                     'selected': True, 'language': 'de'}]}, ordinary['reference_addresses']['index'])
    pieces = ordinary['definition_sources']['source_pieces']
    raw = {u['id']: u for u in products['P1']['payload']['graph']['units']}
    for declaration in result['declarations']:
        declaration['source_projection'] = body_projection(text, pieces, raw, assembly['operations'],
            declaration['declaration_start'], declaration['declaration_end'])
        for key in ('term', 'restriction', 'value'):
            part = declaration[key]
            part['source_projection'] = body_projection(text, pieces, raw, assembly['operations'], part['start'], part['end'])
    for row in result['occurrences']:
        row['source_projection'] = body_projection(text, pieces, raw, assembly['operations'], row['start'], row['end'])
    result['reviewed_binding_reconciliation'] = reconciliation(result, ordinary)
    return {**result, 'prior_answer_preserved': True, 'original_records_preserved': True,
            'whole_task_complete': False, 'legal_truth_established': False}


def evaluate(products, ordinary, profile, root, *, expected_profile_sha256):
    keys = {'version', 'products_sha256', 'ordinary_answer_sha256', 'specification_sha256',
            'whole_task_complete', 'legal_truth_established'}
    fields(profile, keys, keys)
    spec = json.loads(Path(__file__).with_name('purpose_uses_spec.json').read_text())
    require(SPEC_SHA256 is not None and digest(spec) == SPEC_SHA256, 'Purpose-use specification differs')
    require(profile['version'] == VERSION and digest(profile) == expected_profile_sha256
        and profile['specification_sha256'] == SPEC_SHA256
        and profile['products_sha256'] == digest(products) == spec['products_sha256']
        and profile['ordinary_answer_sha256'] == digest(ordinary) == spec['ordinary_answer_sha256']
        and ordinary.get('report_sha256') == digest({k: v for k, v in ordinary.items() if k != 'report_sha256'})
        and KEY not in ordinary and profile['whole_task_complete'] is False
        and profile['legal_truth_established'] is False, 'Pinned purpose-use baseline differs')
    return {KEY: {'profile_sha256': digest(profile), 'products_sha256': digest(products),
                  'ordinary_answer_sha256': digest(ordinary), **content(products, ordinary)}}
