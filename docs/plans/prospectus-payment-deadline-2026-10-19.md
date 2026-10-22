# Derive payment nonperformance within the selected30-day periods

Continue basf-references after cutoff047; use its complete answer as baseline.
Preserve all59 obligations,44 tasks,sealed evidence,user deferrals and prior
costs. Do not require real client facts or external advisers for this conditional
source application.

## Source and question

Selected default(a) concerns principal or interest not paid within30days after
the due date. Default(c)'s payment alternative concerns the qualifying debt or
guarantee amount aboveEUR200m not paid within30days after due date or,for a
guarantee,after invocation. The existing amount adapter derives the exact money
threshold but receives the30-day condition as a hypothesis. The new adapter
derives that condition under explicit clock hypotheses and composes it with the
existing amount adapter. It also supplies default.a.payment30 for the full
default(a) formula. Do not apply the payment deadline to accelerated-debt or
security-enforcement alternatives. Keep notice,cure,dispute,quorum,other grounds
and representative restrictions unchanged.

## Assumptions and research intent

Two clock hypotheses are offered,neither promoted to a legal default: an
inclusive exact30x24-hour endpoint from a timezone-aware trigger instant,or an
inclusive civil day30 ending immediately before midnight that begins day31 in
a separately declared fixed UTC offset. Fixed-offset civil counting is a
limited declared mathematical convention; DST-sensitive local civil deadlines
must remain unsupported unless that offset premise is independently satisfied.
No hidden weekend,holiday,business-day or date-roll adjustment is made.

The source trigger is explicitly DUE_DATE for default(a) and direct debt,or
GUARANTEE_INVOCATION for guarantee timing. A source_trigger_supported premise
exposes that mapping. Other-note obligation breaches are outside this adapter.
Assessment follows the trigger. A payment-state enumeration distinguishes a
stipulated full payment,stipulated unpaid through assessment,and unknown payment
status. Full payment requires a payment timestamp and must not postdate assessment;
unpaid/unknown states must not carry a payment timestamp. Payment before trigger
is permitted as stipulated advance full performance. The FULL_PAYMENT state
asserts completeness as a hypothesis; a partial/uncertain payment must use UNKNOWN
without a full-payment timestamp. A timestamp alone proves neither full payment
nor the correct obligation. If assessment has not passed the deadline,
the30-day failure condition is false; if it has,unpaid is true,known timely
full payment is false,known late full payment is true and unknown status stays unknown.
Cure remains separate,so late payment never silently proves an exercisable
right persists. Missing dates remain unknown; malformed supplied dates refuse.

## Evidence contract and skeptical audit

Primary criteria: independent integer-Gregorian/microsecond oracle and manually
transcribed complete formulas agree; complete047 baseline fields remain exactly
unchanged; full ordinary and isolated installed answers match. For default(c),
the independent oracle also recomputes amount/FX through the existing separate
integer amount oracle,with derived timing substituted. Production composes the
existing amount module; callers may not override its computed time premise.

Cases: inclusive elapsed endpoint and one microsecond past; civil final-day
23:59:59.999999 versus next-day midnight; due versus guarantee invocation;
leap/month/year boundaries; explicit offset equivalent instants; advance payment;
assessment before/at/after deadline; paid/unpaid/unknown state; partial/unmatched
payment premises; missing dates; invalid date/offset/role/identity/state;
EUR exactly200m and above; accelerated/security branches without valid payment
timing; dispute,cure,notice,quorum and representative restrictions.

Promotion vetoes: wrong endpoint,state confusion,guarantee/debt trigger mixing,
time threshold leaking to independent branches,lost qualifiers,accepted override,
unexpected baseline delta or installed mismatch. Continuation vetoes: corrupt
evidence,unexplained method drift or exhausted cumulative resources. Counts and
runtime explain execution only. No actual default,complete performance,legal
counting convention,historical application or completed build follows.

Skeptical audit: PASS for the conditional calculation after distinguishing
"within30days" from the strict continuous-omission rule. The clock endpoint is
explicit,not inferred from the helper'sGT operator. Known late payment and cure
are different propositions. Missing payment is not treated as nonpayment.
Civil fixed-offset arithmetic is deliberately conditional and its limitations
remain visible. The source's debt/guarantee trigger split and amount branch
scope must be verified through both original complete nodes.047 is the current
baseline; helper success alone is insufficient for delivery.

## Execution and resources

Prepare immutable candidates,source profile and precomputed independent
expectations;review same-task revision;check/status/admit;install;tests;complete
consumer;adverse controls;offline package;isolated installed answer;seal;record;
refresh. Continue source-specific causal-rating derivation and wider coverage.
Keep cumulative026 bounds9600measured seconds and1024MiB including4MiB reserve;
forecast<=850seconds and<=120MiB additional. Review any required increase before
admission,retaining every prior cost. Stages<=210seconds;installed child<=195.
CPU only,GPU hidden;one-second tool yields,poll existing sessions,no new GETs,
permission changes,commits or publication.
