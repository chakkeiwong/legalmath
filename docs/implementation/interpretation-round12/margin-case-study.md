# A real source-to-Java demonstration, with its unresolved interpretation

The retained public circular is SFC 25EC71. Its local response is included in
`examples/integrated-assurance/sources/25ec71.json`, with SHA-256
`1dedb0b381106d5b0d91450c6e99e7da3b96e9646710c502a67263301da99d79`.
The selected question concerns the announced margin exemption for the listed
non-centrally cleared equity options, the specified commencement date, and the
continuing effect of later notices. Surrounding discussion of overseas policy
and the future Code amendment stays available to the readers.

The live process generated nine candidates in the first full pass and compiled
six. One retained rival interprets gazettal as a prerequisite; it supplies no
executable formalization. Another supplies English prose in fields that require
expressions and is marked unsupported. Several executable proposals instead
interpret the announcement's stated commencement as the operative condition,
while preserving questions about the underlying Code and later notices.

The candidate selected for the explicit reference replay is
`node.298564cf01d1366a4a8e2db5`. It separates the actor, identified margin
requirement, clearing status, three product classifications, assessment date and
effective later notice. Its proposed rule is:

```text
scope = licensed_corporation AND schedule_10_margin_requirement
result = non_centrally_cleared
         AND (single_stock_option OR equity_basket_option OR equity_index_option)
         AND assessment_date >= 2026-01-04
         AND NOT effective_notice_displaces_exemption
```

Here `TRUE` answers the selected exemption question under the supplied scope and
classification facts. `FALSE` does not mean the bank has breached a margin rule.
An unknown relevant input remains unknown. The date is an explicit fact; it is
not silently taken from the host computer's clock. The continuing effect of the
announcement requires a fact about subsequent notices, rather than an assumption
that the retained circular is the last word indefinitely.

The five expected scenarios were frozen before live generation. To execute them,
an author subsequently reviewed every candidate fact definition and supplied a
complete mapping. That mapping additionally stipulates that the assessed margin
requirement is within the referenced Schedule 10 regime. It is retained in
`transfer-bindings/25ec71.json`; the original expected cases were not changed.
Candidate selection and mapping were not blind, and this is not an independent
legal accuracy test.

| Frozen scenario | Conditional Java/Python/cvc5 result | Interpretation of the observed result |
|---|---|---|
| Classified single-stock option at commencement | TRUE | Meets this candidate's stated conditions |
| Classified equity basket option at commencement | TRUE | Basket classification is expressly represented |
| Centrally cleared equity index option | FALSE | Does not meet this candidate's non-central-clearing condition |
| Unknown clearing classification | UNKNOWN | Missing information is not replaced by false |
| Effect of later notices not checked | UNKNOWN | The retained announcement alone does not settle current applicability |

All five outcomes agreed in the focused replay. The actual binary, source-linked
bundle, fact snapshots, command and independent solver comparisons are retained
under `artifacts/interpretation/round12/diagnostics/transfer-reference-01/25ec71`.
This is executable evidence: the sidecar ran the generated Java class and compared
its status, type and value with Python and cvc5. It is not a test that merely
compared two copies of a model's answer.

The same five scenarios also passed through a separately compiled Catala-to-Java
package. Its full result and trace comparison with Python is retained under
`artifacts/interpretation/round12/diagnostics/transfer-reference-catala-02`.
Both Java routes still share input meanings and host infrastructure; this
additional compilation does not settle the source interpretation.

The unresolved issue is upstream. Some source-fidelity responses say that the
future Code amendment and gazettal are not expressed in the predicate. Other
candidate readings treat those statements as context about implementation of the
announced change. Both positions remain visible. Counting fidelity votes or adding
a gazettal Boolean automatically would not resolve which interpretation is
supported. The next discriminating evidence is the applicable Code edition and
official amendment/commencement material, with their authority and dates checked.

This demonstration therefore establishes a concrete conditional execution result
and exposes a specific interpretation question. It does not establish that the
question has already been answered correctly for the bank's operational use.

One diagnostic question also arose from our task wording: the phrase
"classified licensed corporations" was intended to mean that the actor's status
was supplied. It is not a new category named by the circular. A question about
that phrase must be recorded as a task-wording issue, not evidence of ambiguity
in the regulator's text. The frozen request remains unchanged in this run so its
history and exposure are preserved.
