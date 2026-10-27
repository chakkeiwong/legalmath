# Remaining U/E defect found during execution

The resumed P14 caller authenticates the retained correction, then calls
`review_warrants` on the original answer before applying the complete checked
current-answer dispositions. The retained correction already includes the 77
original warrant assessments needed to authenticate all 121 issue occurrences.
The current-answer disposition deliberately binds the original review identity,
not a mutable reassessment. Repeating those historical assessments therefore
cannot change the reviewed disposition and spends the small remaining P14 budget
before its fresh current-answer reviews. This is a reproduced caller-order defect.

Extend G2/G3 within the same local repair: authenticate a registered disposition
against retained original assessments before any reassessment call. If no
disposition is registered, retain the existing path. A registered but stale,
incomplete or forged disposition fails closed; never fall back to provider calls
that conceal the mismatch. All fresh answer/dependency reviews still execute,
and STILL_REQUIRED entries still block acceptance. No issue or prior call is
removed. Test no duplicate historical call, fresh rejection, pending issues,
stale evidence, missing original assessments and the unchanged legacy path.

Skeptical review: PASS for isolated repair. Retained evidence is authenticated
by `fixed_correction` and the disposition validator; no acceptance verdict is
inferred from avoiding a repeated assessment. Activate only at a proved terminal
phase boundary with unchanged existing reservations. This completes U/E rather
than granting another detour or reopening exhausted tasks.
