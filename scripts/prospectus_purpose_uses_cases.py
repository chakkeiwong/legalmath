"""Freeze independently read uses and purposes before creating the candidate."""
from datetime import datetime, timezone
import time

from scripts import prospectus_unquoted_verifier_repair as prior
from legalmath.prospectus.successor.contracts import digest

ROOT, AUTH = prior.ROOT, prior.AUTH
PREP = AUTH / 'reviews/purpose-use-discovery-351'
PLAN = 'docs/plans/prospectus-purpose-use-discovery-2026-10-19.md'
ROWS = (
    (10213, 10243, 'vorzeitigen\nRückzahlungsbetrag', 'USE_CANDIDATE', [], None),
    (11831, 11861, 'vorzeitigen Rückzahlungsbetrag', 'USE_CANDIDATE', [21343], 'tax'),
    (19119, 19149, 'vorzeitigen\nRückzahlungsbetrag', 'USE_CANDIDATE', [21487], 'makewhole'),
    (21305, 21335, 'Vorzeitiger Rückzahlungsbetrag', 'HEADING_CANDIDATE', [], None),
    (21403, 21432, 'vorzeitige Rückzahlungsbetrag', 'DECLARATION_TERM', [21343], 'tax'),
    (21547, 21576, 'vorzeitige\nRückzahlungsbetrag', 'DECLARATION_TERM', [21487], 'makewhole'),
)
SCOPES = (
    (21343, 'U06-tax-early-amount', '2', '(2)', 11500, 13468),
    (21487, 'U07-makewhole-early-amount', '5', '[(5)]', 18874, 20226),
)


def main():
    started = time.monotonic()
    assert not (PREP / 'candidate/purpose_uses.py').exists(), 'Candidate precedes source freeze'
    products = {k: prior.read(ROOT / row['path']) for k, row in prior.read(prior.PRODUCTS)['products'].items()}
    answer = prior.read(prior.prior.HERE / 'ordinary-answer.json.gz')
    text = products['P2']['payload']['assembly']['continuous_text']
    readings = []
    for a, b, quote, role, matches, rule in ROWS:
        assert text[a:b] == quote
        readings.append({'start': a, 'end': b, 'raw': quote, 'role': role,
                         'selected_declaration_starts': matches, 'reviewed_rule': rule})
    frozen = prior.read(prior.prior.PREP / 'expected.json')['candidates']
    scopes = []
    for a, record, paragraph, printed, left, right in SCOPES:
        original = next(row for row in frozen if row['review_record'] == record)
        assert original['start'] == a and text[left:left + len(printed)] == printed
        scopes.append({'declaration_start': a, 'record': record, 'section': '5',
            'path': [paragraph], 'printed_label': printed, 'start': left, 'end': right,
            'term': original['term'], 'restriction': original['scope'], 'value': original['value']})
    prior.save(PREP / 'expected.json', {'occurrences': readings, 'scopes': scopes,
        'candidate_count': 6, 'declaration_count': 2,
        'broad_use_remains_unresolved': True, 'heading_is_not_operative': True,
        'no_synthetic_10a_node': True,
        'not_established': ['General recall', 'Governing legal scope', 'Actual legal facts', 'Historical law', 'Whole task/build']})
    prior.save(PREP / 'source-freeze.json', {'created_at': datetime.now(timezone.utc).isoformat(),
        'candidate_absent': True, 'products_sha256': digest(products), 'ordinary_answer_sha256': digest(answer),
        'source_expectations_from': prior.rel(prior.prior.PREP / 'expected.json'),
        'source_expectations_sha256': prior.sha(prior.prior.PREP / 'expected.json'),
        'expected_sha256': prior.sha(PREP / 'expected.json'), 'plan_sha256': prior.sha(ROOT / PLAN),
        'wall_seconds': time.monotonic() - started})
    print('Frozen six independently read source occurrences and two distinct printed purposes')


if __name__ == '__main__':
    main()
