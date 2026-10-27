# Isolate original context classifications from fresh corrected-answer reviews

This bounded follow-up concerns D5 of the registered P14 deployment. The deployed
worker and all its protected files remain unchanged while the diagnostic runs.
No provider calls, service replacements or owner attempts are granted here.

Code trace: `BoundedProduct.correct_answer` invokes `audit_answer` with
`prefix='corrected-'`. The individual-review importer deliberately skips its
historical checkpoint for that prefix. `context_disposition.review`, however,
does not pass the prefix to `prepare` or `need_rows`; those functions consult
the original decision-bound mapping and retained-source classifications for
every matching assignment ID. A legitimately new unresolved decision can thus
be rejected as an altered historical decision. That would be an implementation
failure, not evidence against the corrected legal answer.

## Evidence contract and dependencies

| Item | Prerequisite | Action and completion evidence |
|---|---|---|
| C0 | None; local diagnostic independent of the live worker | Exercise the actual corrected `audit_answer` entry with a fresh unresolved decision on an assignment having each kind of historical classification. Preserve the baseline failure. |
| C1 | C0 reproduces the error | In an isolated candidate, propagate the existing review prefix and consult historical classifications only for the original continuation. Retain exact original-decision hash checks. |
| C2 | C1 | Run both new corrected-entry cases and the existing original-predecessor/adverse-disposition tests. Require the new factual need to remain unresolved and the historical checkpoint to remain unchanged. |
| C3 | C2 and a safely settled deployment boundary | Register any deployment as a reviewed successor preserving the active attempts, decisions, charges and grants. Do not edit bound files beneath a running worker or reset its continuation. |

The baseline is the deployed source, not a hand-built replacement for its
validators. The primary diagnostic is whether the corrected product entry can
assess a new unresolved decision without applying a decision classification
from the original review. A missing fact must still veto ACCEPT. Altering a
decision in the original import must still raise an integrity error. Mocked
model responses isolate local control flow; passing establishes no legal
acceptance or live model reliability.

The existing prefix is the provenance for distinguishing original and corrected
review paths. It already governs historical review reuse. Reusing that same
distinction is preferable to treating every changed decision as exempt from its
hash check, which would weaken original-import integrity. The early test uses
the actual product entry with only group results and the provider response
scripted; no live allowance is accessed.

Skeptical review: PASS for the local diagnostic and a candidate conditional on
reproduction. The hidden assumption under test is that every later decision for
the same assignment belongs to the original decision population. Positive
results must preserve necessary factual gaps and the original integrity veto.
No acceptance threshold, legal source or answer is changed. Deployment is not
authorized by a passing mock alone: its current process/dispatch state and
successor binding must be reviewed and preserved. Current authorized independent
work continues while C0–C2 run.

Exact initial diagnostic: `.venv-context/bin/python -m pytest
tests/assurance/test_corrected_context_disposition.py -q`. Results belong under
`artifacts/legal-mission-control/2026-10-23/p14-corrected-context/`.

## Reproduction and deployment review

The deployed entry failed both mapping and retained-authority cases with
`E_INTEGRITY`, before provider dispatch. The isolated candidate propagates the
existing prefix and passes 24 focused tests. The initial whole-entry fixture was
incomplete (it omitted the ordinary capacity-checkpoint header); its failure is
retained separately. Supplying that header permits the actual local dispatcher
and all validators to run. The necessary client fact remains UNRESOLVED and
original-decision tampering still fails.

Deploy as a successor to the current deployment, preserving its intermediate
program, binding, worker evidence, every attempt and all settled calls. Count
this bounded follow-up explicitly as the next consolidated detour (63 to 64),
with zero added calls, attempts, replacements or deadline. Keep the original
deployment plan and its result immutable. Use a new runtime directory and import
exact settled dispatches so the earlier continuation is not purchased again.

Before interrupting the supervisor, acquire nonblocking locks on master state,
mission state, the shared provider worker and every current dispatch journal.
Require the recorded PID/start identity, no other active owner, no provider
child and no RESERVED dispatch. Then stop the supervisor briefly, recheck its
identity, children and unchanged ledger, retain a handover receipt, and terminate
only that idle supervisor. On a failed precondition release locks and leave the
worker running. This follows the repository's existing verified handover method.
An in-flight provider request is never killed to obtain the boundary.

## Settled checkpoint and observed contract defects

The guarded handover completed on 23 October at 07:19:32 UTC, at 4,130 calls
and 104 cumulative service replacements. All 52 failed individual reviews now
have validated continuations; 34 adverse-review assessments and the first
context follow-up are retained. Eighty-seven exact calls were imported without
new provider calls. The successor registration was stopped before publication
after examining the newly available live responses. No registry transaction was
prepared and the old binding, attempt 5 and all ledgers remain unchanged.

Two additional failures belong to this same unregistered repair package.
First, context slot 4130 supplied answer quotations using JSONPath strings
(`$.payload.answer.unresolved[4]`) while the checker requires an answer-relative
JSON Pointer (`/unresolved/4`). The broad prose checker reports the bracketed
index as an ambiguous legal citation before the pointer checker can diagnose it.
The request schema left the path unconstrained and the instructions did not
state its syntax. Enumerate the actual answer's string-leaf pointers in the
context response schema and explain that they are answer-relative. Preserve
exact-quotation and false-waiver checks. Give the failed canary one reviewed
continuation under the corrected contract; its failure stays retained, and
previously undispatched context assignments keep their original one-call bound.

Second, six issue occurrences labelled WARRANTED explicitly say that they
criticize an unnecessary dependency and identify no answer defect. The correction
consumer previously passed only the original issue text and dropped the warrant
reason. Preserve the full assessment with every admitted correction issue so the
consumer sees that distinction. Require an explicit correction target and exact
answer quotation for new answer-defect warrants. For the six observed issues,
use a narrowly enumerated, result-hash-bound exclusion from answer correction;
do not relabel their historical decisions or infer acceptance. Reuse all existing
warrants and charges. Untargeted criticism remains visible; source-supported
evidence-description repairs continue independently.

A further review of warrant 1463 finds a different scope mismatch: it criticizes
the answer for omitting an annual-report clause, whereas the actual question asks
about the request trigger, objects and standards in paragraph 14, footnote 5,
and paragraphs 15–16. The assigned source reading itself says that the annual-
report passage does not resolve that question. The warrant identifies no
incorrect answer statement and supplies no connection making this separate
reporting obligation necessary to the requested inference. Preserve its adverse
decision and treat its claimed relevance as unresolved; exclude this seventh
issue from automatic answer correction. This is a scope-based correction veto,
not an ACCEPT decision or a finding that the annual-report obligation lacks legal
effect. Fresh review may restore a correction only with an explicit answer
defect or justified missing premise. The source, question, full assessment and
exact hashes must accompany that exclusion.

| Item | Success prerequisite | Result and stop condition |
|---|---|---|
| C4 | Settled saved responses | Reproduce invalid path handling and the six non-answer warrants from exact saved bytes; no provider call |
| C5 | C4 | Constrain answer pointers; preserve full warrant reasons and reviewed target exclusions; reject altered checkpoints and unsupported answer quotations |
| C6 | C5 | Focused regression and actual-request preparation pass; register the amended package under the same detour 64 and attempt 5 |
| C7 | C6 | One corrected-contract context canary; if valid, continue original per-need reviews and supported correction; if invalid, retain it and continue independent work |

Skeptical revision review: PASS for this bounded amendment before publication.
The first defect is a response-contract mismatch, not a finding that the supplied
law is insufficient. The second risks changing a correct claim because the
assessment and consumer disagree about the object being criticized. Exact
answer quotation, preservation of full reasons and enumerated non-answer
exclusions prevent label-only correction. No regex-based legal relabelling,
acceptance relaxation, successful-review rerun, extra attempt, reset charge or
new deadline is authorized. The inherited 288 recovery and 8,100 call ceilings
remain. A failed contract canary blocks its bulk queue, not independent source
analysis or supported correction.

The resumed review found two handover hazards before deployment. A closed
service circuit may still reserve an exact retry; require no half-open request,
schema or reservation and hold the circuit lock as well. Recheck the complete
dispatch-journal set after stopping the idle supervisor, so a newly created
journal cannot evade the precondition. Require agreement between the armed
receipt, worker receipt and P14's active supervisor. Archive service ledgers as
evidence without projecting their unchanged snapshots into historical programs;
that would create conflicting historical archive identities. These are local
deployment correctness conditions, not new call or repair allowances.

Before handover, test refusal without signalling for active calls, child
processes, an open/half-open circuit and changed ownership. Test the successful
idle handover with simulated processes, exact dispatch import (including failure
retention and tamper refusal), worker-directory selection and attempt/veto
preservation. Inspect the staged full mission before publication. Stop deployment
on an uncertain dispatch, changed frozen predecessor or failed validator; leave
the original worker running unless a verified settled handover has completed.
The fixed settle command may poll these same nonblocking preconditions with
`--wait-seconds 50`; the option grants no different signal or dispatch authority.
Its finite wait catches the short interval between completed requests without
interrupting a provider or emitting repeated approval prompts.

The successor changes the context module, the deployment validator/worker
selection and the mission's counted-revision check. Its registry transaction
must validate the staged mission and unchanged authority before publication.
Historical classifications remain tied to the original decisions; fresh review
needs receive no inherited waiver. The existing fixed deployment `arm` command
will select the successor worker directory, keeping its command approval scope.

Skeptical deployment review: PASS conditional on settled-process evidence,
authenticated call import, all focused checks and staged mission validation.
The largest risks are duplicate calls after migration, accidentally changing an
existing attempt, and weakening original import integrity. Exact request/schema
comparison, unchanged predecessor bytes and the adversarial tests are required
vetoes. The current original-review work may run while the candidate is prepared;
its results must be captured at the boundary, not ignored by a stale census.
