"""Register the six individually reviewed, unchanged literature contexts."""
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.bind_monograph_citation_claims import bind_claims, record_digest

HERE = Path(__file__).resolve().parent
BOOK = ROOT / 'docs/monograph'
REVIEW = BOOK / 'review/reader-facing'
SOURCE = 'docs/monograph/chapters/02f-prospectus-integration-closure.tex'
CONTEXT = '3b143ae21aea55ac13f1081a09a80319adda84d0a44e8985a500f935f6aa27c9'
JUDGMENTS = {
    'contractnli2021': 'Sections 2–5 and Appendix A.1 motivate self-contained span evidence and treatment of distant exceptions. Refusing to infer contractual absence is the local design inference. No scan capability or NDA accuracy is transferred.',
    'connecting2023': 'Sections 3–5 and Appendices B/D/E describe typed spans, events and argument edges used in statutory reasoning. Actor/effect/condition/date fields are our proposed representation, not a claimed prospectus implementation from this paper.',
    'legalinterpretations2014': 'Sections 3–4 distinguish sources, interpretations and contexts and model an authoritative choice between alternatives. The paragraph invokes that distinction without claiming automatic legal selection.',
    'aspic2010': 'Section 3 distinguishes premises, strict/defeasible arguments, attacks and preference-dependent defeat. Section 6 gives conditional rationality results; the retained correction remains applicable. The paragraph imports representation, not a universal consistency theorem or a source of legal authority.',
    'catala2021': 'Sections 4.1 and 4.4–4.5 concern formal default/exception semantics and a scoped compilation argument. Section 6.1 concerns legal/programmer collaboration. Neither establishes natural-language prospectus fidelity; the paragraph states that limit.',
    'dates2024': 'Sections 2, 3.2 and 4.3 expose ambiguous month/year operations, operation order and rounding sensitivity. Requiring contractual conventions is a local design consequence; the paper does not supply calendars or select legally applicable rounding.',
}


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def main():
    if len(sys.argv) != 1:
        raise ValueError('No options accepted')
    out = HERE / 'citation-review-001'
    if out.exists():
        raise ValueError('Prior review exists; inspect it before any further change')
    previous_path = REVIEW / 'citation-occurrence-review.json'
    previous = read(previous_path)
    contexts = read(REVIEW / 'citation-contexts.json')
    reading = read(BOOK / 'review/revision/citation-reading.json')['sources']
    archive = {r['key']: r for r in read(ROOT / 'docs/papers/monograph-citation-archive.json')['sources']}
    historical = defaultdict(list)
    for row in previous['occurrences']:
        historical[(row['key'], row['context_sha256'])].append(row)
    baseline = (HERE / 'baseline/02f-prospectus-integration-closure.tex').read_text()
    decisions, additions = [], []
    for context in contexts:
        identity = context['key'], context['context_sha256']
        matches = historical[identity]
        if matches:
            decisions.append({**matches.pop(0), 'id': context['id']})
            continue
        key = context['key']
        if context['source'] != SOURCE or context['context_sha256'] != CONTEXT or key not in JUDGMENTS:
            raise ValueError('Unexpected unreviewed context: ' + context['id'])
        if context['context_tex'] not in baseline:
            raise ValueError('The literature paragraph differs from the protected subsection')
        if sha(ROOT / archive[key]['path']) != archive[key]['sha256']:
            raise ValueError('Retained primary source changed: ' + key)
        decision = {
            'id': context['id'], 'key': key, 'context_sha256': CONTEXT,
            'source_sha256': archive[key]['sha256'],
            'reading_record_sha256': record_digest(reading[key]),
            'decision': 'supported_in_stated_scope', 'judgment': JUDGMENTS[key],
            'reviewer': 'Codex executor; scoped author review, not independent acceptance',
            'additional_reading': 'docs/implementation/prospectus-root-cause-2026-10-06/LITERATURE-REVIEW.md',
            'basis': 'Exact unchanged paragraph reviewed against retained technical reading records and source-specific notes; primary PDF identities verified. No claim of a new full-paper reading.',
        }
        additions.append(decision)
        decisions.append(decision)
    if len(additions) != 6 or {r['key'] for r in additions} != set(JUDGMENTS):
        raise ValueError('Expected exactly the six reviewed contexts')
    if any(historical.values()):
        raise ValueError('An existing reviewed context would be removed')
    updated = {**previous, 'occurrences': decisions, 'prospectus_closure_review': {
        'reviewed_at': datetime.now(timezone.utc).isoformat(),
        'prior_sha256': sha(previous_path), 'new_contexts': 6,
        'record': str((out / 'judgments.json').relative_to(ROOT)),
        'independent_acceptance': False,
    }}
    bind_claims({'citation_occurrences': contexts}, reading, archive, updated)
    out.mkdir()
    (out / 'citation-review-before.json').write_bytes(previous_path.read_bytes())
    save(out / 'judgments.json', additions)
    save(previous_path, updated)
    save(out / 'result.json', {'status': 'PASS', 'new_contexts': 6,
        'total_occurrences': len(decisions), 'previous_contexts_preserved': True,
        'review_sha256': sha(previous_path), 'source_sha256': sha(ROOT / SOURCE),
        'plan': 'docs/plans/prospectus-scan-documentation-2026-10-11.md',
        'independent_acceptance': False})
    save(out / 'manifest.json', {'files': {p.name: sha(p) for p in out.iterdir() if p.is_file()}})
    print(json.dumps(read(out / 'result.json')))


if __name__ == '__main__':
    main()
