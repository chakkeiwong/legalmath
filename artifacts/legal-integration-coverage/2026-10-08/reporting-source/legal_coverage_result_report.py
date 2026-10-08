"""Post-run evidence report; no provider calls or judgments invented."""
import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, '/home/chakwong/python/legalmath')

from scripts.legal_integration_coverage import (
    OUT, ROOT, DOC, PRIOR, read, save, ref, immutable, checked_review, verify,
    collected, latest_receipt, tested, review_path, scoped, check_ref)

checked = verify()
rows = collected()
inputs = read(OUT / 'inputs.json')
claims = {c['claim_id']: c for c in inputs['claims']}
assessments = []
candidate_counts = Counter()
all_followups = []
tool_checks = []
additional_concerns = []
for row in rows:
    if row['arm'] != 'combined' or not row.get('result'):
        continue
    result = read(check_ref(row['result']))
    if row.get('tools'):
        tool_report = read(check_ref(row['tools']))
        tool_checks.extend({'batch': row['batch'], 'tool': check.get('tool'),
            'kind': check.get('kind'), 'status': check.get('status'), 'key': check.get('key'),
            'report': row['tools']} for check in tool_report['checks'])
    for batch in result['batches']:
        proposals = iter(batch['proposals']); latest = {}
        for attempt in batch['attempts']:
            if attempt['status'] == 'VALIDATED_PROPOSAL':
                latest[attempt['role']] = next(proposals)
        additional_concerns.extend({'batch': row['batch'], 'perspective': role, 'concern': concern,
            'result': row['result']} for role, proposal in latest.items()
            for concern in proposal['additional_concerns'])
        complete = scoped.fully_assessed_pairs([batch])
        for claim, candidate in batch['required_pairs']:
            perspectives = {}
            for role, proposal in latest.items():
                value = next(c for c in proposal['checks'] if c['claim_id'] == claim and c['candidate_id'] == candidate)
                perspectives[role] = value
                all_followups += [{'claim_id': claim, 'candidate_id': candidate,
                                  'perspective': role, 'question': q} for q in value['followup_questions']]
            is_assessed = (claim, candidate) in complete
            if is_assessed: candidate_counts[candidate] += 1
            assessments.append({'claim_id': claim, 'claim_relevance': claims[claim]['relevance'],
                'candidate_id': candidate, 'assessed': is_assessed, 'batch': row['batch'],
                'receipt': ref(check_ref(row['result']).parent.parent / 'receipt.json'),
                'perspectives': perspectives})

universe = [(claim, candidate) for candidate in sorted(inputs['candidates']) for claim in sorted(claims)]
observed = {(r['claim_id'], r['candidate_id']): r for r in assessments}
pair_inventory = [observed.get((claim, candidate), {'claim_id': claim, 'claim_relevance': claims[claim]['relevance'],
    'candidate_id': candidate, 'assessed': False, 'batch': None, 'perspectives': {}}) for claim, candidate in universe]
assert len(pair_inventory) == 492 and len(observed) == len(assessments)
assert sum(r['assessed'] for r in pair_inventory) == checked['coverage']['assessed_pairs']
immutable(OUT / 'pair-assessments.json', pair_inventory)
immutable(OUT / 'model-followups.json', all_followups)
immutable(OUT / 'tool-check-inventory.json', tool_checks)
immutable(OUT / 'model-additional-concerns.json', additional_concerns)

call_rows = read(OUT / 'allowance.json')['calls']
transport = []
for slot, row in enumerate(call_rows, 1):
    directory = OUT / 'provider-evidence' / f"{slot:04}-{row['request_hash'][:16]}"
    manifest = read(directory / 'manifest.json')
    events_path = directory / 'events.jsonl'
    events = [json.loads(line) for line in events_path.read_text().splitlines() if line.strip()] if events_path.exists() else []
    transport.append({'slot': slot, 'purpose': row['purpose'], 'batch': row['batch'],
        'request_hash': row['request_hash'], 'complete_output': manifest['complete_output_present'],
        'request_bytes': manifest['files'].get('request.json', {}).get('bytes'),
        'event_types': [e.get('type') for e in events], 'manifest': ref(directory / 'manifest.json')})
immutable(OUT / 'transport-summary.json', transport)

repairs = read(OUT / 'repairs.json')
summary = {**checked, 'completed_candidate_counts': dict(candidate_counts),
    'original_legal_obligations_open': 46, 'original_readings': 35, 'original_unformalized_readings': 32,
    'scoped_candidate_count': 12, 'scoped_unformalized_candidates': 6, 'followup_proposals': len(all_followups),
    'route': checked_review()['route'], 'review': ref(review_path()),
    'tests': tested(), 'pairs': ref(OUT / 'pair-assessments.json'),
    'followups': ref(OUT / 'model-followups.json'), 'transport': ref(OUT / 'transport-summary.json'),
    'additional_concerns': ref(OUT / 'model-additional-concerns.json'),
    'tool_checks': ref(OUT / 'tool-check-inventory.json'),
    'tool_status_counts': dict(Counter(f"{r['tool']}:{r['status']}" for r in tool_checks)),
    'finished_epoch': time.time(), 'wall_seconds': time.time() - read(OUT / 'run-manifest.json')['started_epoch'],
    'decision': 'COMPLETE_SCOPED_PROCESSING_WITH_OPEN_LEGAL_GAPS' if checked['execution_complete'] else 'INCOMPLETE_SCOPED_PROCESSING_WITH_OPEN_LEGAL_GAPS'}
immutable(OUT / 'execution-summary.json', summary)

table = '\n'.join(f"| `{cid}` | {candidate_counts[cid]}/41 | {'No' if r['formalization'] is None else 'Yes'} |"
                  for cid, r in sorted(inputs['candidates'].items()))
coverage = checked['coverage']
calls = checked['calls_by_purpose']
result_text = f'''# Retained legal integration execution result

The combined assessment completed **{coverage['assessed_pairs']}/492 original
claim–reading pairs**. The current completion verdict is
**{summary['decision']}**. The original **46 legal obligations remain open**;
coverage is processing evidence, not a legal accuracy or closure finding.

The program is `docs/plans/legal-integration-coverage-program.md`, supplemented
by the append-only repair reviews in this directory. Current method:
`{review_path().relative_to(ROOT)}`. Machine-readable decisions and provenance:
`{(OUT / 'execution-summary.json').relative_to(ROOT)}`. The complete 492-row
`pair-assessments.json` preserves both perspectives, including every unavailable,
blocked, disputed and unassessed pair. Nothing is silently dropped.

## What executed and what changed

The runner binds the user's additional 100-call/20-repair authorization to
unchanged old ledgers and the preceding sealed result. It partitions all
41 claims and 12 readings, including 72 CONTEXT pairs; 420 is only the CONTROL
subset. Both perspectives assess each retained pair under its original typed
question. Actual BM25 retrieval and eligible LegalRuleML checks supply
source/candidate-bound evidence. Unsupported code remains explicit. No criticism
graph was supplied in this scoped continuation, so graph tools are not claimed
executed here. Previous complete controlled-product checks remain separate.

The first nested provider call could not write its state database in the sandbox.
Trusted execution fixed that environment problem. Large requests then encountered
retained timeouts. A tiny sentinel and two-pair baseline/combined diagnostic
completed, testing an unformalized reading under its original satisfaction
question. Each arm reported one UNAVAILABLE and one NOT_APPLICABLE pair. The
first response-alias envelope increased request bytes and timed out; it was
corrected before promotion. The compact codec changes identity spelling only:
it retains source, questions, statuses and free text and expands the selected
keys before unchanged source/executable validators run. The retained twelve-pair
response round-trips exactly, from 17,572 to 13,446 serialized output bytes.
That reduction is descriptive engineering evidence, not a latency proof.

The inherited 180-second call cap was reviewed against observed large-response
latency and the remaining overall window. New large batches use a bounded
300-second cap; the original absolute expiry stays 1791519402.34676. Both
twelve-pair pilots subsequently completed in both arms. One bulk response
omitted required followups on nine UNAVAILABLE rows and was rejected. Its
reviewed replacement supplied no predetermined legal labels; both perspectives
then validated. The rejected and replacement responses remain available because
their changed relevance judgments require substantive review.

Batch 17 subsequently returned a quotation combining paragraph 14 and
footnote 5 as one continuous span. The source validator rejected it. Revision
v12 constrains each evidence entry to one selected source span; every full
source unit remains selectable and separate provisions need separate entries.
It requests a fresh assessment without supplying prior legal labels. The
original 51-call ledger prefix is preserved by an explicit allocation revision:
combined 81, baseline 3, repair 16, still within the user's total of 100 calls
and 20 repairs. No original reservation is rewritten or refunded.

The first batch-17 replacement used valid quotation formatting but omitted
scope evidence on ten not-applicable rows and paired those judgments with
OMITS correspondence. It was rejected. Revision v13 mirrors the existing
scope-evidence and label-consistency rules in nested response-schema branches.
It preserves uncertain and unassessed states and requests fresh judgments
without copying the rejected legal answer. Its implementation and live attempt
exhaust the 20 repair entries. Another response or transport failure therefore
ends dependent live execution, even if normal-call allocations remain unused.

Local repairs also bind test reuse to current runner and product hashes, verify
the selected attempt's journal, preserve prior failed receipts, correct tool
report lookup and prohibit generic unchanged retries. The current focused suite
has **{summary['tests']['counts']['tests']} passed tests**, no failures/errors.
Earlier stale-cache and test-authoring mistakes are documented with retained
logs; the v2 cached test receipt was not a fresh v2 run.

## Scope and results

| Measure | Recorded count |
|---|---:|
| Required scoped pairs | 492 |
| Assessed in both perspectives | {coverage['assessed_pairs']} |
| Remaining unassessed | {coverage['unassessed_pairs']} |
| Executable comparisons in both perspectives | {coverage['executable_compared_pairs']} |
| Either perspective reports unavailable code | {coverage['unavailable_pairs']} |
| Either perspective reports blocked premises | {coverage['blocked_pairs']} |
| Both perspectives report not applicable | {coverage['not_applicable_pairs']} |
| Mixed correspondence labels | {coverage['mixed_correspondence_pairs']} |
| New provider reservations, including failures | {checked['calls']}/100 |
| Recorded repair batches | {len(repairs['repairs'])}/20 |

Unavailable/blocked counts may overlap and are not executable comparisons.
Relevance labels and source-support rationales are model proposals, even after
identity and consistency validation. The matched baseline covers two batches
(24 pairs), not the full matrix. Same-model perspectives are not independent
legal adjudicators. There is no supported quality or speed ranking.

The preserved baseline pilots precede the v12/v13 response-schema revisions.
They are applicability diagnostics; they are not a matched comparison with
every later revised combined batch. The coverage total retains validated
results across the explicitly versioned request methods.

| Generated candidate | Assessed pairs | Executable present |
|---|---:|---|
{table}

This is a continuation of the scoped stage on retained generation and question
assignments. It does not constitute a fresh complete source-to-generation-to-
execution product run. The original 35-reading register has 32 unformalized
readings; those are distinct from the six unformalized generated candidates.

## Decision and uncertainty

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
|---|---|---|---|---|---|
| Retain verified local repairs | Current focused suite and retained reference checks | Invalid aliases, questions and unsupported executable claims rejected | Wider inputs and concurrency | Keep versioned source and exact evidence binding | General legal correctness |
| Record scoped execution | {coverage['assessed_pairs']}/492 assessed pairs | Failed attempts retained; current completion {checked['execution_complete']} | Model interpretation and service variability | Inspect the per-pair findings and unresolved followups | A full fresh product run or release readiness |
| Keep legal obligations open | No new authority/factual/standard premises establish closure | Missing premises and rival readings remain | Governing target and legal standards | Obtain named premises and independent adjudication | Any of the 46 obligations closed |

| Inference status | Finding |
|---|---|
| Hard veto screen | Sandbox/timeout executions and invalid followup response were rejected and preserved. |
| Statistically supported ranking | None. |
| Descriptive-only differences | Latency, output bytes, response labels, agreement and followup counts. |
| Default-readiness | Not established; alias transport is a reviewed continuation method, not a general legal accuracy default. |
| Next evidence needed | Independent target adjudication, authority/factual/standard premises, robust task-specific service evidence and a fresh complete product execution. |

Post-run red team: exact source quotes can accompany a wrong relevance judgment.
The repair reminder may influence status choices even without prescribed labels;
the rejected and revised outputs must remain available for independent review.
Both perspectives may share the same model bias. Successful dispatch does not
diagnose earlier timeouts or prove the codec caused the observed latency.
The strongest evidence is structural identity and actual bounded processing;
the weakest remains legal interpretation and target generalization.

Call allocation used: {calls}. Original predecessor consumption stays 73/96
calls and 10/12 repairs. No prior grant was reset. The fixed wrapper prefix is
approved; local checks use the sandbox, live provider actions need trusted
state-database/network access. All tool work was CPU-only. No commit or push
was performed. Remaining substantive gaps and their remedies are in
`remaining-gaps.md`; operations and recovery are in `operator.md` and
`reset-memo.md`.
'''
(DOC / 'execution-result.md').write_text(result_text)
print(json.dumps({k: summary[k] for k in ('decision', 'coverage', 'calls', 'calls_by_purpose', 'repairs')}, indent=2))
