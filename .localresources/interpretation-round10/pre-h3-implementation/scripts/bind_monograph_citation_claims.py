"""Bind citations only to separately retained, exact-context review decisions.

This program never creates a support judgment. A changed passage, edition or
reading note needs a new author review before it can be bound again.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'docs/monograph/review/revision'


def record_digest(record):
    return hashlib.sha256(json.dumps(record, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def bind_claims(inventory, reading, archive, reviews):
    decisions = {r['id']: r for r in reviews['occurrences']}
    if len(decisions) != len(reviews['occurrences']):
        raise ValueError('Duplicate citation review identities')
    if set(decisions) != {c['id'] for c in inventory['citation_occurrences']}:
        raise ValueError('Citation set changed: occurrence review required')
    rows = []
    for occurrence in inventory['citation_occurrences']:
        record = reading[occurrence['key']]
        source = archive[occurrence['key']]
        decision = decisions[occurrence['id']]
        expected = {
            'key': occurrence['key'],
            'context_sha256': hashlib.sha256(occurrence['context_tex'].encode()).hexdigest(),
            'source_sha256': source['sha256'],
            'reading_record_sha256': record_digest(record)}
        if any(decision.get(k) != v for k, v in expected.items()):
            raise ValueError('Changed claim, source or reading evidence: '+occurrence['id'])
        if decision.get('decision') != 'supported_in_stated_scope' or not decision.get('judgment'):
            raise ValueError('Unresolved citation support: '+occurrence['id'])
        rows.append({**occurrence,
            'context_sha256': expected['context_sha256'],
            'support_status': 'supported_with_recorded_scope_after_author_review',
            'occurrence_review': decision,
            'source_path': source['path'], 'source_sha256': source['sha256'],
            'inspected_location': record['read_scope'],
            'quotation_evidence': record['quotes'],
            'support_explanation': record['support'],
            'qualification': record['limitations']})
    return {
        'review_kind': 'Author/executor claim review following the retained technical reading; not independent legal adjudication',
        'quotation_role': 'Short quotations demonstrate examination of the source. The support judgment depends on the surrounding sections named in inspected_location; one quotation is not a proof of every clause in a paragraph.',
        'occurrence_review_sha256': record_digest(reviews),
        'occurrences': rows}


def main():
    inventory = json.loads((REVIEW/'inventory.json').read_text())
    reading = json.loads((REVIEW/'citation-reading.json').read_text())['sources']
    archive = {s['key']: s for s in json.loads((ROOT/'docs/papers/monograph-citation-archive.json').read_text())['sources']}
    reviews = json.loads((REVIEW/'citation-occurrence-review.json').read_text())
    result = bind_claims(inventory, reading, archive, reviews)
    (REVIEW/'citation-claims.json').write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')
    print(f"Bound {len(result['occurrences'])} citation occurrences to {len(archive)} archived records.")


if __name__ == '__main__':
    main()
