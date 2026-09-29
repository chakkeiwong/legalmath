# D3 reproduction and D4 source revision

D3 audit attempt 02 passed against the frozen D2 verification implementation.
Its plan is `docs/plans/gregorian-profile-audit.md`; the exact result is
`artifacts/gregorian-profile-audit/2026-09-29/attempt-02/result.json`.

The audit regenerated the three Gregorian Lean propositions and their disclosed
standard axioms, repeated the 3,652,059-date codec comparison, executed the 49
declared known-date cases on each target, and regenerated preservation evidence
for all eight unchanged encoded UCITS readings. The ninth remained unencoded.
The 29 date/constructor tests passed. The theorem, codec and retained-reading
receipts match the earlier G4 result exactly. These are repetitions of scoped
evidence, not new future observations.

The first D3 attempt preserved all those successful checks but failed the added
unknown/conflict assertion. The test expected a native UNKNOWN/CONFLICT result;
the actual complete.v1 profile rejects the input at a shared boundary with
ABSTAIN and INCOMPLETE_INPUTS or CONFLICTING_INPUTS. Inspection of the policy and
pipeline established this distinction. A focused executed repair checked eight
requests against the built targets, requiring the exact abstention reason and
`execution=None`; only then did attempt 02 rerun the audited campaign. A relative
repair-note path also needed normalization; its rejected invocation happened
before reservation and is described in the causal repair record.

The final evidence is **98 native executions plus eight shared boundary
requests**, not 106 native executions or two independent abstention methods.
The boundary requests have zero complete-value oracle matches, as required.
Integer calendar order has kernel evidence; canonical-string/codec behavior has
an exhaustive finite check. Neither proves date libraries, whole compilers,
legal date selection, business-day calendars, or lifted unknown/conflict semantics.

D4 source-revision attempt 01 passed its mechanical criteria. Its plan is
`docs/plans/authority-source-revision.md`; result and full packet are under
`artifacts/authority-source-revision/2026-09-29/attempt-01/`. The main 23EC52
circular and three-page appendix now enter the same context through the existing
source routines. The complete extracted text is bound to the original byte
hashes and acquisition receipts. Both extractions, unresolved links and visual
findings remain visible. All six original authority questions and their prior
request/result identities are retained, without model calls or reused judgments.

The separate JFIU XML schema bytes/version are still missing. No current or
applicable edition is inferred from a historical download. In particular, a
catalogue link with unassessed relevance is not an established incorporation
premise. The eDDA/authentication source-to-question inventories remain incomplete.
D4 as a whole is therefore **partial**, despite successful source attachment.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain scoped D3 profile | Exact theorem/codec/known-case/reading reproduction passed | First harness assertion repaired; final checks passed | String libraries and compilers outside theorem; legal date selection open | Preserve these boundaries when applying a supported profile | Legal correctness or whole-compiler proof |
| Retain D4 source revision | Main body and appendix attached with full extracted-text accounting | No original question, bytes or history changed | Missing schema and unestablished applicability/interpretation | Supply precise missing sources and perform an eligible bounded investigation | Six authority questions closed |

Strongest alternative explanation: the retained readings could still encode the
wrong legal date or obligation while every mathematical and source-identity
check passes. Any changed original reading, discrepancy in the finite codec or
native comparison, or missing source span would invalidate the corresponding
engineering result. None occurred in the final scoped runs. No stochastic
ranking or legal-error probability was estimated.
