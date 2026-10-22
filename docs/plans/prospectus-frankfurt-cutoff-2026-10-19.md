# Calculate the selected control-put exercise cutoff

Continue basf-references after strict-duration046. Use its complete answer as
the comparator and preserve every earlier supplement and source requirement.
This is conditional source application; real holdings,external opinions,CDM
receivers and portability remain deferred under the user's directions.

## Question and source

The complete selected basf-redemption:control_put clause requires receipt at
the designated Fiscal Agent office within45days after publication of the event
notice,and makes receipt after17:00 Frankfurt time on day45 ineffective.
It separately describes repayment on day15 after the exercise period ends.
The engine already preserves these as premises,including earlier tax-call
notice as an exception. It lacks a source-specific exact timestamp derivation.

Add an optional review computing the deadline under explicit counting and
timezone hypotheses,then derive control_put.timely_exercise and evaluate BOTH
the existing condition and its earlier-tax-notice exception. Retain control,
causal rating,event notice,valid declaration,delivery,payment day and the
specific representative restriction. Do not make missing event notice
extinguish the underlying option; this is the modeled exercised repayment.

## Intent, defaults and assumptions

Use exact timezone-aware ISO timestamps with at most microsecond precision.
Publication and receipt carry distinct roles and one instrument/scenario.
Convert to a retained Europe/Berlin TZif file rather than the host's mutable
current timezone database. Preserve the local installed2026c version marker,
TZif hash and available license provenance. This establishes reproducibility,
not the accuracy of historical legal time or future timezone legislation.
No network acquisition is needed or claimed. Refuse dates outside2000–2030,
the explicitly reviewed calendar comparison domain,including computed dates
that fall beyond it. This is a test domain choice,not a legal coverage claim.

Two explicit interval-start hypotheses are supported: publication instant
inclusive,or midnight at the start of the next local day. Both place day45
on publication local date+45,with an inclusive17:00 cutoff. The adapter chooses
neither as a legal default. Separate premises expose publication identity,
receipt at the designated office,counting convention and timezone applicability.
Missing publication/receipt remains unknown; invalid supplied values refuse
even when another operand is absent. Inputs cannot override the derived
timely-exercise premise. Day15 is a conditional expected calendar date only;
it must not automatically prove that actual repayment occurs then.

## Evidence contract and skeptical audit

Baseline: complete046 products and answer. Primary criterion: independent
integer-Gregorian/UTC oracle agrees on deadline,earliest instant,receipt result
and the complete formula including tax exception; ordinary and isolated
installed answers match with every prior field unchanged. The oracle derives
Berlin offset in2000–2030 from the last-Sunday March/October rule and checks it
against the retained TZif over that finite domain. This is an independent
implementation comparison,not an independent legal authority.

Test exact cutoff and one microsecond after; winter/summer deadlines; periods
crossing both DST changes; leap/month/year boundaries; input offsets differing
from Frankfurt; ambiguous repeated-hour receipt expressed by each explicit
offset; receipt before the start; alternative start rules; missing and malformed
operands; unsupported identity/convention/domain; tax exception; causal rating
unknown; declaration,delivery,notice,payment and representative restrictions.
Mutate source,baseline,products,premise override,timezone data and outputs.

Promotion vetoes: wrong boundary/timezone conversion,omitted tax exception,
forged or role-confused input accepted,baseline delta or installed mismatch.
Continuation vetoes: corrupt retained evidence,unexplained method drift or
exhausted reviewed cumulative resources. Counts/runtime are explanatory.
No actual exercise,legal calendar selection,historical applicability,automatic
classification,external package superiority or whole-build completion follows.

Skeptical audit: PASS for this declared finite computation. The source explicitly
provides the17:00 and45-day cutoff; the start/counting conventions and timezone
applicability remain hypotheses. Including the exception is essential: checking
only node.conditions would incorrectly omit the earlier tax call. A pinned
timezone fixture plus separately implemented finite calendar oracle prevents
silent host drift. Preserve unsupported scope explicitly. Full consumer and
installed comparison remain primary delivery checks,not test counts.

## Ordered work and cumulative resources

Retain immutable candidate,timezone provenance,independent oracle,source profile
and precomputed expectations; revise the same task; check/status/admit;
install; focused regressions and finite timezone verification; complete answer;
adverse controls; offline wheel and installed replay; seal,record,refresh.
Continue source-specific payment deadlines and causal-rating derivation.

Forecast<=850additional measured seconds and<=120MiB. Retain all cumulative026
costs. Explicitly extend8400 to9600measured seconds and896 to1024MiB including
4MiB reserve for this additional substantive adapter and its complete delivery;
admissions46 to47. This is a same-scope revision,never a reset or unchanged retry.
Each stage<=210seconds,installed child<=195. One-second
tool yields and existing-session polls. CPU only,GPU intentionally hidden.
No network acquisitions,global permission changes,commits or publication.
