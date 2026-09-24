# Decomposed live investigation: evidence to date

The round5 investigation failed before producing an inventory: one request
returned a service-overload message and the next timed out after 180 seconds.
Those observations did not establish that the input exceeded a provider limit.

The round6 attempt used the same retained SFC family-office FAQ selection:
29 units containing 4,903 source characters. It split them into three intact
groups of 16, 6 and 7 units, then required a whole-source context check from each
of two readers. The compact inventory requests contained 5,681, 4,371 and 3,868
bytes for the first reader, excluding the response schema. The earlier whole
inventory request contained 21,224 bytes. Source language and IDs were preserved.

The 200-byte availability request succeeded in 11.837 seconds. Its reported
24,289 input tokens include surrounding Codex context; application JSON size is
not total model input. All six reading requests and both whole-source checks
returned outputs that passed the declared schema and exact-quotation checks.
This attempt therefore establishes feasibility of the inventory path on this
source. It does not identify the cause of the earlier failures or establish a
reliability rate from one attempt.

Both context checks identified local uncertainties that the other pieces
resolved, including the three licensing factors in Q3 and the identity of the
Circular and Ordinance. They also retained uncertainty about the scope of a
negation, statutory qualifications and office-specific facts. The system records
these discrepancies instead of converting the agreement into a probability of
correct interpretation. Contexts were separate, but the model and supplied source
were shared; statistical independence has not been established.

The initial investigation then failed before generation. Its HTML extraction
contained 33,887 characters; import normalized CRLF to LF and produced a different
32,526-character derivative. Existing exact source spans could not resolve against
that derivative. Replaying the eight recorded responses reproduced the traceback
without live calls. An explicit option now preserves already-anchored text during
import. Twenty-one targeted tests passed after this repair, including the actual
retained page, mixed line endings and a synthetic source-to-Java path. The first
targeted attempt also exposed an incorrect test assertion about the location of
Java-check results; both test reports are retained.

The D1 attempt consumed nine calls, leaving 11 under the existing ceiling of 100.
Its investigation status remains `FAILED_INTEGRITY`; its phase acceptance records
only successful evidence capture and budget enforcement. D1R resumes the eight
responses using original reservation identities and may spend at most the
remaining 11 calls downstream. Its final result will be recorded in the execution
report. No repeated reading is counted as an additional independent judgment.

D1R subsequently completed three initial generation passes, one refinement and
one controlled-English reconstruction. It retained four candidate interpretations,
four Java/Python conformance checks, six candidate comparisons and one
reconstruction comparison that was equivalent within its declared domain. The
source-to-code fidelity matrix had 51 source claims and four candidates, hence
204 required comparisons. At 32 pairs per batch, it needed seven calls plus a
criticism call; only six journal slots remained. Admission correctly reported
incomplete fidelity without dispatching an unaffordable partial matrix.

The criticism response was also rejected. Some attacks did not express the
opposite signed proposition, one purported to undercut a strict inference, and
another cited a premise outside its target argument. The original response and
validation error remain recorded. This is a model-output failure detected by the
argument validator, not evidence that its proposed legal conclusion is false.
D1R used six new calls and left five; its investigation remains `UNRESOLVED` with
`execution_complete=false`.

The [final continuation audit](final-live-audit.md) admits four equal batches of
51 pairs and one bounded criticism repair, with all prior responses replayed.
This experimental batch setting permits a complete attempt within the remaining
allowance. It does not increase the allowance, drop a claim or candidate, or
change the default batch size. Failures can still leave the result incomplete.

D1F's first 51-pair call timed out at the existing 180-second deadline. No pair
from that call validated. The circuit stopped the attempted criticism repair
before another paid dispatch, leaving four calls. Its investigation remains
`UNRESOLVED`; the timeout supplies no evidence for or against any legal reading.

The subsequent [four-pair diagnostic plan](fidelity-piece-audit.md) removes
unneeded peer claims from each fidelity request while preserving complete source
context and all required candidate meanings. The reviewed request is 18,386 bytes,
compared with the preceding 68,584-byte request, excluding response schemas. The
first four pairs are fixed before inspecting the response. They are an execution
diagnostic only: the parent matrix has 204 pairs, and its unchecked portion must
remain explicit. The final result is recorded in the execution report.

D1S attempt-02 validated all four requested pairs in 58.557 seconds. All labels
were `NOT_ESTABLISHED`, on the claim about the FAQ's purpose and audience. This
raises a source-relevance question, not four established legal errors. Two hundred
pairs remain unchecked. A first attempt failed in local JSON serialization before
dispatch; it consumed no call and was retained before repair. The ledger now
contains 97 of 100 calls. Full regression then passed 538 tests with no failures
or skips. Completing the unchanged matrix at the tested task size would require
50 further fidelity calls plus at least one criticism repair; the existing three
remaining calls cannot fund that complete path.

| Decision | Primary criterion | Veto evidence | Main uncertainty | Next justified action | Conclusion not supported |
| --- | --- | --- | --- | --- | --- |
| Retain optional decomposition | Exact coverage, merge, context checks and live inventory completion observed | No inventory validation failure in D1 | Model omissions and shared errors remain possible | Continue downstream verification through retained replay | Universal English completeness |
| Reject the first investigation as complete | Inventory completed; investigation did not | Reproducible source-derivative mismatch | Downstream behavior had not executed | Execute exact-text import repair and replay successor | Successful end-to-end interpretation |
| Preserve unresolved context findings | Both checks retained explicit issues | No adjudicated legal reference for ambiguous wording | True legal meaning remains unsettled | Generate and compare supported alternatives | Agreement proves the law |

| Inference status | Finding |
| --- | --- |
| Hard veto screen | The initial source-derivative mismatch blocks the complete-investigation claim. |
| Statistically supported ranking | None; no comparative randomized or replicated experiment was run. |
| Descriptive observations | All eight decomposed inventory actions returned in this attempt; earlier whole-inventory attempts failed. Service conditions and task shape changed together. |
| Default readiness | Decomposition remains optional. It has not been promoted as the production default. |
| Next evidence needed | Complete downstream execution, measured failure/coverage behavior across independent source families, and separate reference-quality assessment. |

The strongest alternative explanation for the live success is service recovery,
rather than decomposition. A fair comparison under matched service conditions
would be needed to attribute the difference to the task design. The most important
remaining weakness is the lack of an independent adjudicated reference for the
full English interpretation. Generated Java can be tested against a proposed
formal meaning without settling that source-interpretation question.
