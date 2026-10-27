# Acceptance evidence follow-through within the product-closure amendment

26 October 2026. This is completion of U/C/F in the reviewed closure amendment,
not a new task graph or grant. The active worker and all bound sources remain
unchanged while a candidate is prepared in the existing isolated tree.

Question: can a corpus review declare a proposition supported without locating
that proposition in the exact answer under review? Current source checks bind
the answer file but never inspect `answer_evidence`. Source accuracy alone does
not establish that the answer says what the review attributes to it.

Baseline: installed corpus_review.py and corpus_components.py, plus exact
retained P14/Gatecoin answer reviews. First reproduce invented, absent and
wrong-field quotations being accepted. This is an engineering diagnostic only.

Dependency map:
- G1: reproduce the omission; no provider or other branch dependency.
- G2: after G1 succeeds, stage one shared exact JSON-pointer/quote checker and
  wire both corpus consumers. Require answer evidence for SUPPORTED findings;
  unresolved omissions may remain explicit without fabricated positive quotes.
- G3: after G2, run positive and adverse controls including wrong-field, absent,
  blank, invalid-pointer and changed-answer cases, and both actual callers.
- G4: independently check the retained P14/Gatecoin passage references.
- G5: after G3/G4, retain a reviewed candidate for activation only at a verified
  safe checkpoint. Do not change bound code while the worker is running.
- F: retain results in mission history and refresh once after the checkpoint.

Pass criterion: both consumers reject missing/invented/misattributed answer
passages while accepting exact passages from the bound answer. The checker
establishes attribution, not entailment, legal correctness or full acceptance.
Human/model substantive review remains necessary. An empty or boilerplate
quote cannot become sufficient merely by matching bytes.

One local repair with targeted corrections. No calls, attempts, service reserves
or deadline added. Active question work continues independently. Stop activation
for lost history, binding mismatch, uncertain ownership or unreviewed answer
identity; do not stop unrelated running questions because the candidate fails.

Skeptical audit: PASS for reproduction and isolated implementation. Wrong
baseline avoided by copying installed dirty bytes; no cache or source checks
removed. Exact quotation is an attribution check only, not a promotion proxy.
No runtime or fixture comparison uses the candidate as its own baseline.
Artifacts remain in this product-closure directory; the existing registered
program and final original-question/tool criteria continue to govern.
