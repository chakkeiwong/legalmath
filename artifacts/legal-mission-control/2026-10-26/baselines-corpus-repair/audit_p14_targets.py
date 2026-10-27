"""Distinguish exact text identity from the substance of saved P14 objections."""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json

ROOT = Path('/home/chakwong/python/legalmath')
OUT = Path(__file__).resolve().parent

def read_checked(reference):
    path = ROOT / reference['path']
    assert sha256(path.read_bytes()).hexdigest() == reference['sha256']
    return json.loads(path.read_text())

def strings(value, pointer=''):
    if isinstance(value, str):
        yield pointer, value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from strings(child, pointer + '/' + key.replace('~', '~0').replace('/', '~1'))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from strings(child, pointer + '/' + str(index))

rows = json.loads((OUT / 'p14-warrant-semantic-reassessment.json').read_text())['rows']
inventory = []
answers = {}
network_examples = []
for row in rows:
    request = read_checked(row['request'])
    raw = read_checked(row['raw'])['value']
    answer = request['payload']['answer']
    answers[row['answer_hash']] = answer
    fields = {p: text for p, text in strings(answer) if not p.startswith('/support/')}
    for decision in raw['decisions']:
        evidence = decision['answer_evidence']
        quote = evidence['quote']
        exact = [p for p, text in fields.items() if quote and quote in text]
        folded = [p for p, text in fields.items() if quote and quote.casefold() in text.casefold()]
        category = ('EMPTY_EVIDENCE' if not quote else
            'EXACT_SELECTED_FIELD' if evidence['path'] in exact else
            'EXACT_DIFFERENT_FIELD' if exact else
            'CASE_CHANGED_QUOTE' if folded else 'NOT_AN_EXACT_ANSWER_QUOTE')
        issue = next(i for i in row['original_issue_texts'] if i['id'] == decision['issue_id'])
        inventory.append({
            'call': row['call'], 'request': row['request'], 'raw': row['raw'],
            'answer_hash': row['answer_hash'], 'issue': issue,
            'disposition_unchanged': decision['disposition'],
            'correction_target_unchanged': decision['correction_target'],
            'selected_path': evidence['path'], 'original_quote': quote,
            'exact_matches': exact, 'casefold_matches': folded, 'classification': category,
            'correction_authorized_by_this_audit': False
        })
    if not network_examples:
        for record in request['records']:
            text = record.get('text', '')
            marker = 'adequate controls'
            index = text.casefold().find(marker)
            if index >= 0:
                start = max(0, index - 350)
                end = min(len(text), index + 300)
                network_examples.append({'request': row['request'], 'record_id': record['id'],
                    'record_text_sha256': sha256(text.encode()).hexdigest(),
                    'character_span': [start, end], 'exact_excerpt': text[start:end],
                    'scope': 'Text present in this retained request; no claim of current legal applicability.'})
assert len(rows) == 20 and len(answers) == 1
answer_hash, answer = next(iter(answers.items()))
assert 'the incorporated intermediary discussion of network risks is absent.' in answer['unresolved'][2]
assert 'network risks is absent' not in answer['conclusion']
assert 'The neighbouring provisions concern procurement' in answer['conclusion']
result = {
    'profile': 'retained-p14-target-location-audit.v1',
    'warrant_calls': len(rows), 'issue_decisions': len(inventory),
    'counts': dict(Counter(row['classification'] for row in inventory)),
    'warranted_counts': dict(Counter(row['classification'] for row in inventory if row['disposition_unchanged'] == 'WARRANTED')),
    'answer_hash': answer_hash,
    'exact_network_absence_target': {'path': '/unresolved/2', 'text': answer['unresolved'][2]},
    'network_source_examples': network_examples,
    'clarification': [
        'The network-absence statement is present in /unresolved/2. Its absence from /conclusion does not show that the objection has no answer target.',
        'Some failed quotations select the wrong field; others paraphrase the answer or change capitalization. The optional selector only removes retyping error.',
        'The neighbouring-provision objection asserts absence although /conclusion discusses those provisions. That quotation is absent from the answer and needs explicit adverse-issue reassessment.',
        'All original responses, issue identities, verdicts and failed receipts remain unchanged. No local simulation is accepted as a legal correction warrant.',
        'A future reviewer must choose the actual field and assess source support and remaining gaps issue by issue, distinguishing main operative text from missing explanatory material.'
    ],
    'rows': inventory, 'provider_calls': 0, 'live_attempts': 0,
    'legal_acceptance': False, 'automatic_retargeting': False
}
destination = OUT / 'p14-target-location-audit.json'
if destination.exists():
    assert json.loads(destination.read_text()) == result
else:
    destination.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
print(json.dumps({k:result[k] for k in ('warrant_calls','issue_decisions','counts','warranted_counts','provider_calls','legal_acceptance')}))
