# Plan and implementation review

29 September 2026. The master plan passed the skeptical review recorded in
`docs/plans/prospectus-master-program.md`. Approval concerns operational execution
only; it contributes no quality evidence.

Preflight repair: the first attempt used the `elan` dispatch executable. Its
`lean --version` tried to resolve the machine's moving default and timed out after
20 seconds. This was an environment-selection failure, not a failed theorem.
The repair uses the already-installed Lean 4.20.0 binary also used by LegalMath's
qualification module. No toolchain or package installation is required. The
fixed command prefix was approved before downloads or research execution.

Remaining implementation reviews and terminal findings are appended after the
relevant checks; phase receipts retain failures and refreshed next-phase plans.

Download repair: forcing HTTP/1.1 and a custom user agent failed on Capital One
and the published UBS final-terms route. A bounded plain-curl probe retrieved both
PDFs successfully. The archive now uses curl's default negotiated transport and
identifies the changed acquisition method in the retained attempts. Previously
failed URLs are retried under this repaired method; successful bytes are retained.

P1 attempt 003 exposed a real implementation failure: the public UBS final-terms
PDF uses AES, while the installed pypdf lacks its optional cryptography dependency.
The already installed Poppler extractor successfully read that exact PDF. Added a
bounded fallback for this specific dependency failure, recorded extractor identity
and added Poppler to preflight. Original bytes remain unchanged. The failed phase
is retained and the repaired phase will run again before interpretation.

Pre-run review of the implemented checks: seven declared formal models translate
through both targets. Lean compilation and independent SMT obligations pass in a
smoke run; 27 focused regression tests pass. Source matching remains provisional,
including negation, foreign referents and programme/issue distinctions. Monetary
thresholds use integer HKD cents and contract effects use rational arithmetic.
Backend cases contain factual inputs only. The forthcoming full run must require
both native targets and independent evaluation, keep every unavailable original
visible, and replay before the final qualification. A prospective freeze is not
an observed future result; zero future publications are claimed.

Final source-scope repair: the recovered Lloyds filing says the securities are not
convertible at the holders' option, alongside automatic conversion after a Trigger
Event. The earlier candidate extractor mistakenly treated the limited negative as
a denial of every conversion route. It now retains that quotation as a limited
negation and does not negate the mandatory-conversion premise. A focused test
covers both clauses together. A second bug marked an unpaginated final HTML filing
as preliminary because its appended base text mentioned an earlier draft; draft
indicators now inspect the first cover fragment only and remain indicators, not
finality certificates. The new text schema forces actual derivative regeneration.
Reusing a source ID for changed URLs, roles or instruments now fails instead of
silently reusing different provenance. All 49 regression tests pass. These repairs
use the development corpus and establish no held-out or future legal accuracy.

Terminal review criteria: each of P0-P6 must be current after these changes;
regenerated text must match preserved originals; all native backend cases must
agree with independent formal evaluation; the final verify command must pass.
Remaining English entailment and document/law closure are qualified premises,
not implementation failures concealed by passing tests.

The final limited-negation regression also covers "not convertible into Settlement
Shares at the option of the holders". Both the shorter and expanded wording now
preserve mandatory trigger conversion as a separate candidate premise. The actual
Lloyds filing now yields a conditional complex-bond candidate rather than a false
conversion conflict. Fifty tests pass. All current source interpretations remain
explicit hypotheses; this corpus was used for repair and is development evidence.

Terminal outcome: all seven phases are CURRENT. The final `verify` action returned
CHECKED with 21 preserved sources and all 206 independently matched backend
executions retained from replay. Fifty regression tests passed. The `future`
action returned READY with zero submissions. Actual automatic recovery rebuilt
21 stale derivatives in P2; the failed attempt and repair event remain in the
campaign history. The campaign is complete with the explicit legal and future
qualifications in report.md, not a certificate of unrestricted legal correctness.
