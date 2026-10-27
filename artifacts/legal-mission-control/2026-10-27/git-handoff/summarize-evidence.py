"""Summarize retained review evidence without changing decisions or spending calls."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import json
import sys
ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from legalmath.interpretation.assurance.phased.evidence_store import load_exact
from scripts.legal_mission_execution import ref, save, require
source = Path('artifacts/legal-mission-control/2026-10-26/repaired-retry-continuation/live/arms/evidence/baseline/result.json')
result = load_exact(ROOT / source)
answer = result['answers']['evidence']
reviews = answer['reviews']
failed = [r for r in reviews if r.get('status') == 'FAILED']
counts = Counter((r.get('error', ''), r.get('reason', '')) for r in failed)
report = {
    'profile': 'retained-evidence-review-diagnosis.v1',
    'at_utc': datetime.now(timezone.utc).isoformat(),
    'source': ref(ROOT, source),
    'source_storage': 'Exact chunked store reconstructed and each retained record hash verified',
    'new_calls': 0, 'changed_verdicts': 0, 'review_accepted': answer['review_accepted'],
    'review_count': len(reviews),
    'verdict_counts': dict(Counter(r.get('value', {}).get('verdict', 'NO_VERDICT') for r in reviews)),
    'failed_review_reasons': [{'error': e, 'reason': reason, 'count': n}
                              for (e, reason), n in counts.most_common()],
    'correction': {'status': answer['correction']['status'],
                   'candidate': answer['correction']['candidate']},
    'reviewer_objections_for_source_review': [
        {'request_hash': r.get('request_hash'), 'reason': r['value'].get('reason'),
         'issues': r['value'].get('issues')}
        for r in reviews if r.get('value', {}).get('verdict') == 'REJECT'][:2],
    'interpretation': 'Counts describe review occurrences, not independent legal defects. Reviewer objections require source adjudication; local aggregation does not accept or repair the answer.',
}
target = ROOT / 'docs/implementation/legal-mission-control/checkpoint-2026-10-27/evidence-diagnosis.json'
require(not target.exists(), 'Diagnosis already retained')
save(target, report)
print(json.dumps({k: v for k, v in report.items() if k not in ('reviewer_objections_for_source_review',)}, indent=2))
