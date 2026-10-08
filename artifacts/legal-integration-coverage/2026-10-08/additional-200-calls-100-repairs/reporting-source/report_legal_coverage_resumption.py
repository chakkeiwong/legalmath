"""Build the final evidence report after the continuation runner has exited."""
import sys
import json
from collections import Counter
import subprocess
import time

sys.path.insert(0, '/home/chakwong/python/legalmath')
from scripts import legal_coverage_resume as r

with (r.OUT / '.lock').open('a') as lock:
    r.fcntl.flock(lock, r.fcntl.LOCK_EX | r.fcntl.LOCK_NB)
verified = r.verify()
state = r.aggregate(verify_transport=True)
assert state['execution_complete'] or state['failed_roles'], 'Do not restart an unfinished active run from reporting.'
inputs = r.read(r.BASE / 'inputs.json')
claims = {c['claim_id']: c for c in inputs['claims']}
rows, followups, concerns = [], [], []
counts = {cid: Counter() for cid in inputs['candidates']}
dimensions = Counter()
for number, batch in enumerate(state['batches']):
    proposals = {a['role']: p for a, p in zip(batch['attempts'], batch['proposals'])}
    origins = {a['role']: {'origin': a['origin'], 'receipt': a['receipt']} for a in batch['attempts']}
    complete = r.scoped.fully_assessed_pairs([batch])
    for role, proposal in proposals.items():
        concerns.extend({'batch': number, 'role': role, 'concern': q, **origins[role]}
                        for q in proposal['additional_concerns'])
    for claim, candidate in batch['required_pairs']:
        perspectives = {role: next(x for x in proposal['checks']
            if (x['claim_id'], x['candidate_id']) == (claim, candidate)) for role, proposal in proposals.items()}
        row = {'batch': number, 'claim_id': claim, 'candidate_id': candidate,
               'claim_relevance': claims[claim]['relevance'], 'assessed': (claim, candidate) in complete,
               'perspectives': perspectives, 'provenance': origins}
        rows.append(row)
        counts[candidate]['assessed'] += row['assessed']
        for role, proposal in perspectives.items():
            followups.extend({'claim_id': claim, 'candidate_id': candidate, 'role': role,
                              'question': q, **origins[role]} for q in proposal['followup_questions'])
        statuses = [x['executable_correspondence']['status'] for x in perspectives.values()]
        for name, predicate in (
                ('compared', row['assessed'] and all(s in ('PRESERVES', 'CONFLICTS', 'OMITS') for s in statuses)),
                ('unavailable', 'UNAVAILABLE' in statuses), ('blocked', 'BLOCKED' in statuses),
                ('not_applicable', row['assessed'] and statuses == ['NOT_APPLICABLE', 'NOT_APPLICABLE'])):
            counts[candidate][name] += bool(predicate)
        if len(perspectives) == 2:
            for dimension in ('source_support', 'question_relation', 'executable_correspondence', 'authority'):
                if len({v[dimension]['status'] for v in perspectives.values()}) > 1:
                    dimensions[dimension] += 1
assert len(rows) == 492 and len({(x['claim_id'], x['candidate_id']) for x in rows}) == 492
assert sum(x['assessed'] for x in rows) == verified['coverage']['assessed_pairs']
r.immutable(r.OUT / 'pair-assessments.json', rows)
r.immutable(r.OUT / 'model-followups.json', followups)
r.immutable(r.OUT / 'model-additional-concerns.json', concerns)
r.immutable(r.OUT / 'candidate-results.json', dict(counts))
targets = [{'candidate_id': cid, 'question': inputs['questions'][cid]['question'],
            'formalized': candidate.get('formalization') is not None, 'counts': dict(counts[cid])}
           for cid, candidate in sorted(inputs['candidates'].items())]
r.immutable(r.OUT / 'candidate-targets.json', targets)

attempts = []
for folder in sorted((r.OUT / 'roles').glob('*/*')):
    if not folder.is_dir(): continue
    number = int(folder.parent.name)
    _, selected = r.latest_role(folder, inputs, r.read(r.BASE / 'partition.json')['batches'][number])
    for path in [folder / 'receipt.json', *sorted(folder.glob('attempt-*/receipt.json'))]:
        receipt = r.read(path)
        attempts.append({k: receipt[k] for k in ('batch', 'role', 'complete', 'calls', 'purpose', 'stopped')} |
            {'receipt': r.ref(path), 'selected': path == selected})
r.immutable(r.OUT / 'role-attempt-history.json', attempts)
assert sum(x['calls'] for x in attempts) == verified['new_calls']

selected_reports = {}
for batch in state['batches']:
    for attempt in batch['attempts']:
        receipt = r.read(r.checked(attempt['receipt']))
        if receipt.get('tools'):
            selected_reports[receipt['tools']['path']] = receipt['tools']
checks = []
for report_ref in selected_reports.values():
    report = r.read(r.checked(report_ref))
    checks.extend({'report': report_ref, 'kind': c['kind'], 'tool': c.get('tool'),
                   'status': c['status'], 'key': c['key']} for c in report['checks'])
r.immutable(r.OUT / 'tool-check-inventory.json', checks)
tool_counts = dict(Counter(f"{x['tool']}:{x['status']}" for x in checks))
tool_table = '\n'.join(f"| {key.split(':')[0]} | {key.split(':')[1]} | {count} |" for key, count in sorted(tool_counts.items()))

before = (r.OUT / 'allowance.json').read_bytes()
before_repairs = (r.OUT / 'repairs.json').read_bytes()
restart_dir = r.OUT / 'restart-check'; restart_dir.mkdir(exist_ok=True)
command = ['.venv/bin/python', 'scripts/run_legal_integration_coverage.py', 'resume-execute']
began = time.monotonic()
reply = subprocess.run(command, cwd=r.ROOT, text=True, capture_output=True, timeout=120)
(restart_dir / 'stdout.json').write_text(reply.stdout)
(restart_dir / 'stderr.txt').write_text(reply.stderr)
assert reply.returncode == 0, reply.stderr
assert (r.OUT / 'allowance.json').read_bytes() == before
assert (r.OUT / 'repairs.json').read_bytes() == before_repairs
response = json.loads(reply.stdout)
assert response.get('execution_complete') == verified['execution_complete']
r.immutable(restart_dir / 'result.json', {'status': 'PASS', 'command': command,
    'wall_seconds': time.monotonic()-began, 'new_calls': 0,
    'ledger_sha256': r.raw_digest(before), 'repairs_sha256': r.raw_digest(before_repairs),
    'response': response, 'stdout': r.ref(restart_dir / 'stdout.json'), 'stderr': r.ref(restart_dir / 'stderr.txt')})

summary = {**verified, 'status': 'COMPLETE_SCOPED_PROCESSING_WITH_OPEN_LEGAL_GAPS'
    if verified['execution_complete'] else 'INCOMPLETE_SCOPED_PROCESSING_WITH_OPEN_LEGAL_GAPS',
    'per_candidate': dict(counts), 'dimension_disagreements': dict(dimensions),
    'proposed_followups': len(followups), 'additional_concerns': len(concerns),
    'tool_status_counts': tool_counts, 'tests': r.tested()['counts'],
    'finished_epoch': time.time(), 'wall_seconds': time.time()-r.read(r.OUT / 'run-manifest.json')['started_epoch'],
    'original_unformalized_readings': 32, 'original_readings': 35,
    'generated_unformalized_candidates': 6, 'new_restart_calls': 0}
summary['failed_role_attempts'] = [x for x in attempts if not x['complete']]
summary['recovery_reviews'] = [r.ref(p) for p in sorted(r.OUT.glob('service-recovery-*.json'))]
r.immutable(r.OUT / 'execution-summary.json', summary)

table = '\n'.join(f"| `{cid}` | {v['assessed']}/41 | {v['compared']} | {v['unavailable']} | {v['blocked']} | {v['not_applicable']} |"
                  for cid, v in sorted(counts.items()))
coverage = verified['coverage']
doc = r.ROOT / 'docs/implementation/legal-integration-coverage/resumption/execution-result.md'
doc.write_text(f'''# Legal integration coverage continuation result

The retained combined assessment completed **{coverage['assessed_pairs']}/492
original claim–candidate pairs**. The verdict is **{summary['status']}**.
This continuation used **{verified['new_calls']}/200 new provider calls** and
**{verified['new_repairs']}/100 new repair entries**. The preceding 54 calls and
20 repairs remain unchanged. A completed restart check used **zero new calls**.
The current focused suite passed **{summary['tests']['tests']} tests**, with no
failures, errors or skipped tests.

The governing extension is `docs/plans/legal-integration-coverage-resumption.md`.
It continues the original coverage program and original 492-pair denominator.
Machine-readable results, pair-level judgments and provenance are in
`artifacts/legal-integration-coverage/2026-10-08/additional-200-calls-100-repairs/`.
The original **46 substantive legal obligations remain open**.

## What the repair established

The previous qualification-first reply for batch 17 selected another
candidate's executable request trigger for an unformalized accountability-
satisfaction question. The raw reply contained the confusion; alias expansion
was exact. The new response schema restricts each pair to its own candidate's
expressions and actual executable availability. Explicit pair descriptions
state its claim and exact typed question. Existing source, executable and
fidelity validators remain authoritative, and no local code supplies legal
labels, missing citations or a rewritten model judgment.

Offline checks accepted the retained source-first response unchanged and
rejected the retained foreign-expression response. The live replacement then
validated on the original mixed-candidate batch. It treated the unformalized
accountability reading as UNAVAILABLE and asked for the governing standard,
executable meaning and arrangement-specific evidence. This established a
valid replacement assessment; its legal interpretation remains a model
proposal. The valid old source-first response was reused with its original
provenance and was not sent to the replacement perspective.

The runner then processed the remaining original batches using a separate
journal and durable reservation for each perspective. This permits reuse of
a valid perspective without issuing it again. Started work without a receipt
cannot be silently resent. Failed calls are nonrefundable. Source snapshots,
review records, tests and the new authorization are independently bound; the
old ledgers and original expiry 1791519402.34676 were preserved.

Batch 21's qualification-first dispatch returned HTTP 502 with no complete
output. The failed call remains charged and its receipt and transport were
preserved. A separately reviewed successor reused the original verified tool
context, required identical request and schema hashes, and retained the valid
source-first perspective. Review v2 covers immutable attempt histories,
hash-bound selection and no redispatch after a completed or failed replacement.
The full attempt ledger is `role-attempt-history.json`; failed attempts are
also listed in `execution-summary.json`. Reused tool evidence is not counted
as a new tool invocation.

Batch 36's source-first call later hit the 300-second timeout without a returned
answer. A separate review permitted one identical-request successor capped at
450 seconds. Preflight caught the ordinary settings type's 300-second ceiling;
a dedicated bounded recovery settings type fixed that mismatch while preserving
the normal product limit. Review v3 was never executed; review v4 records the
correction and fresh tests. The replacement validated in 213.72 seconds, below
the original cap, so this does not establish that the larger limit was needed.
This attempt and its outcome remain in the same ledger; they do not identify
the cause of the original timeout.

## Coverage and actual tool use

| Measure | Count |
|---|---:|
| Original required pairs, including CONTEXT | 492 |
| Assessed in both perspectives | {coverage['assessed_pairs']} |
| Still unassessed | {coverage['unassessed_pairs']} |
| Executable comparisons in both perspectives | {coverage['executable_compared_pairs']} |
| Either perspective reports unavailable meaning | {coverage['unavailable_pairs']} |
| Either perspective reports blocked premises | {coverage['blocked_pairs']} |
| Both perspectives report not applicable | {coverage['not_applicable_pairs']} |
| Different correspondence labels | {coverage['mixed_correspondence_pairs']} |
| Proposed followup questions retained | {len(followups)} |

These categories overlap; unavailable and blocked assessments are not
executable comparisons. Label frequencies and disagreements describe model
proposals, not legal accuracy. Each pair, both perspectives and their original
receipts are retained in `pair-assessments.json`. Proposed questions and wider
concerns are retained separately without silently discarding their provenance.
The perspectives disagree on question-relation labels for {dimensions['question_relation']}
pairs, executable-correspondence labels for {dimensions['executable_correspondence']},
and authority labels for {dimensions['authority']}. These are descriptive model
disagreements requiring adjudication, not an error-rate estimate.

Selected combined receipts record these tool outcomes:

| Tool | Reported status | Count |
|---|---|---:|
{tool_table}

Counts include repeated invocations across batches and perspectives. BM25
retrieved locations in the supplied packet for each exact candidate question.
LegalRuleML checked eligible Boolean representations and retained unsupported
readings explicitly. There was no supplied criticism graph, so this scoped
continuation makes no new PyArg, Carneades or clingo execution claim. Earlier
controlled-product Java, Lean and graph evidence remains separate.

| Generated candidate | Assessed | Compared | Unavailable | Blocked | Not applicable |
|---|---:|---:|---:|---:|---:|
{table}

## Decision and evidence limits

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
|---|---|---|---|---|---|
| Retain the candidate-binding repair | Valid original mixed case plus current tests | Foreign selections and unsupported executable claims rejected | Wider inputs and free-text semantic confusion | Preserve the versioned method and test additional independent targets when available | General interpretation correctness |
| Record scoped coverage | {coverage['assessed_pairs']}/492 assessed pairs | Evidence and zero-call restart verified | Both perspectives use the same model | Inspect the per-pair proposals and unresolved premises | New independent adjudication or full fresh product generation |
| Keep 46 obligations open | No new governing facts/authority/standards establish closure | Missing premises and rival readings remain | Applicable standards, facts and legal construction | Obtain the named premises and adjudicate original questions | Compliance, legal closure or release readiness |

| Inference status | Finding |
|---|---|
| Hard veto screen | Retained invalid responses were rejected; current accepted responses pass source/target/executable binding checks. |
| Statistically supported ranking | None. |
| Descriptive-only differences | Latency, bytes, label counts, tool counts and model disagreement. |
| Default-readiness | This bounded continuation does not qualify a universal legal interpretation default. |
| Next evidence needed | Independent target labels/adjudication, authority and applicability sources, actual facts and supported normative standards. |

The two original baseline pilot batches precede the response-schema revisions
and are not a matched comparison with every later request. Both perspectives
may share model bias. Structural constraints can prevent foreign expression
selection while allowing a coherent but wrong legal rationale. That is the
strongest alternative explanation of apparent agreement and the weakest part
of the evidence. Independent source-grounded adjudication could overturn an
accepted legal proposal even when every engineering check passes.

This is the retained scoped stage, with previous generated readings and typed
questions. Six of the twelve generated candidates remain unformalized. The
six executable candidates concern demonstration-duty activation or request
occurrence; they do not supply a test of substantive fulfillment. The six
unformalized candidates ask about effective accountability or fulfillment
through supervision and operational or record-keeping performance. The original
wording and per-target results are preserved in `candidate-targets.json`.
These different questions must remain distinct: a trigger result cannot stand
in for evidence that responsibility has been discharged.

The separate original register contains 35 readings, 32 unformalized, and 46 open
obligations. Their remaining gaps include authority/applicability, client facts,
normative standards, modal/temporal/exception scope, case-law analogy and later
treatment, and independent calibration. They are documented in
`docs/implementation/legal-integration-assessment/remaining-gaps.md` and
`docs/implementation/legal-integration-coverage/remaining-gaps.md`.

No new time window, provider route, client fact or legal standard was inferred
from the increased allowance. No commit or push was performed.
''')
print(json.dumps({k: summary[k] for k in ('status', 'coverage', 'new_calls', 'new_repairs', 'tool_status_counts', 'tests')}, indent=2))
