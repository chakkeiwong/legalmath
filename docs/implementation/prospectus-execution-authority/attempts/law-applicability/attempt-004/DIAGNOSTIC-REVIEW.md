# The single-document control did not reproduce the predicted failure

The first diagnostic retained all four actual products and answers, then failed
its anticipated-NO assertion. Hidden intended, unclassified and excluded cases
all stayed UNKNOWN/PARTIAL. The source issue was absent from dependencies, but
the evaluator's separate absence-of-repayment safeguard prevented a conclusion.
Preserve those outputs and the exit1. Do not rerun them.

Code inspection explains the result: clause_graph.answer returns UNKNOWN when
there is no affirmative absence/repayment interpretation. This is a separate
guard, not availability accounting. The smallest remaining discriminating case
keeps a visible repayment clause and places a principal-loss clause in a second
document. Only that second document becomes unavailable. This directly tests
whether the remaining repayment can supply an unsupported negative answer.
Retain visible/hidden intended, unclassified and explicitly excluded controls.
No production change is permitted unless this changed test reproduces the gap.

Skeptical audit PASS for the mixed-document probe. It repairs an insufficient
diagnostic rather than weakening the evidence contract or repeating the failed
command. The source issue must appear in the answer when intent is operative
or unclassified. Explicitly excluded text remains outside the declared contract.
The test proves engineering behavior only; no real legal premise is supplied.
