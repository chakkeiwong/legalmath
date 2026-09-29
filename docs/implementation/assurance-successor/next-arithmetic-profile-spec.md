# Measured arithmetic and bridge work for the next increment

This is a proposed continuation, not an implemented or accepted extension.
Its inputs are the retained 26EC55 candidate expressions and bridge result.
The circular's exposure classifications, common valuation unit, measurement
time, exclusion and designation premises remain interpretive questions.

## 1. Separate the two actual gaps

The expression in `node.11d4e8e1976eb5b2900022be` uses
`(+ direct_exposure indirect_exposure direct_exposure indirect_exposure)`.
`translation/expressions.py` admits exactly two operands for `+`, so this
four-operand expression is rejected. This is a syntax/profile limitation, not
evidence that addition is absent from RuleIR or Java. Another independently
generated reading, `node.ad3ed6f7c586444ec7213491`, uses nested binary addition
and compiles. It was an initial reading, not a checked repair of the first.
Neither reading has been independently established as the legally correct one.

Separately, the live factual bridge has numeric/date common facts. The existing
`assurance/repair.py::compare_derived` requires an explicit finite domain for
those facts and correctly declines to invent one. A successful shape/identity
repair therefore still returns `CONDITIONAL_BRIDGE_UNRESOLVED`. Expanding syntax
does not settle the bridge's domain or its source premises.

## 2. Implement a checked addition extension, preserving old behavior

The proposed language extension admits `(+ e1 ... en)` for n >= 2 over the
existing exact numeric types. It must preserve operand order and multiplicity;
the duplicated exposures in the observed expression must not be deduplicated.
The old binary syntax and old bundle bytes remain unchanged. Zero/unary forms,
mixed incompatible types, malformed expressions and resource-exhausting input
remain rejected. Do not generalize subtraction or multiplication by analogy.

Implement the extension in `src/legalmath/translation/expressions.py` using a
bounded binary tree of the existing `add` operation, with unique node IDs and
retained interpretation/source references. Update the advertised grammar only
after the compiler and validators agree. Expanded node/depth bounds must be
checked before invoking Java, Catala or a solver. Preserve the original reading
and issue a new source/method revision; never rewrite an old unsupported receipt.

For exact integers, the required arithmetic identity is
`sum(e1,...,en) = (...((e1+e2)+e3)...+en)`. Define the n-ary meaning explicitly
before proving a lowering. The base n=2 is the existing operation. The induction
step adds `e(n+1)` to both equal terms. Rebalancing additionally requires integer
associativity. A lifted unknown result follows only if the declared addition
semantics propagate an unknown operand on both sides. Preserve the same fact
dependencies and the rule's conflict/scope precedence; integer associativity
alone is not a proof of those statuses or of arbitrary JVM requests.

Acceptance requires original binary regressions, malformed/zero/unary/mixed-type
rejections, preserved duplicate operands and node identities, and actual Java
and Catala execution of three-, four- and many-operand examples. Include values
larger than machine integers, negative values as mathematical inputs, missing
facts and conflicting evidence. Financial admissibility of negative exposure
is a separate source premise. Compare the supported expression with its explicit
binary form through the existing symbolic comparison route; retain a separating
case for the mutation that drops an operand. These checks establish the stated
extension, not the English interpretation or a whole-compiler theorem.

## 3. Make arithmetic proof scope explicit

The existing registered Lean certificate accepts Boolean expressions only.
It must continue to reject arithmetic under that profile. A separate versioned
profile would need exact integer expressions, tagged unknowns, comparisons and
their interaction with Boolean scope/conflict semantics. Independently parse
both the source expression and emitted RuleIR into that fixed semantics, and
state exactly which equality the kernel checks. Reject unsupported operators
and changed premises. Do not describe finite boundary tests as a universal
integer/JVM proof. A source-to-RuleIR theorem and production Java conformance
remain distinct records.

## 4. Resolve the bridge without manufacturing a domain

First preserve and report the current unsupported-domain result. If a finite
comparison is useful, require a supplied, versioned domain record listing every
common fact, type, unit, allowed values, source or mathematical justification,
and whether it is exhaustive for the claim or only a probe set. Check the size
before enumeration and execute both original generated programs. A probe set
can find disagreement; matching probes cannot establish equivalence over other
numeric values or dates. Do not infer a domain from the frozen reference answers.

A stronger optional route can translate a supported mapping and both rule
expressions into a declared symbolic theory. For exact linear integers, search
for a valuation where the normalized results differ; an unsatisfiable result
supports equivalence only within that declared theory, status semantics and
encoded premises. Unsupported dates, nonlinear operations and natural-language
frame assumptions remain explicit. Independently replay any separating model
through the original Java programs before using it as an executable witness.
This route requires its own reviewed soundness target and mutation checks; it
must not be relabelled an implementation of the existing finite-domain check.

## 5. Repair, refresh and acceptance

Run the smallest syntax/status mutation tests first, then actual backend tests,
then certificate tests if the new profile is implemented. Refresh the plan from
those results before touching any retained circular dossier. Reopen only the
affected source/method revision and rerun its dependent correspondence and
program checks under the existing remaining authorization. Keep all old failures
and reference answers. A successful encoding makes a reading executable; a
different source-supported answer or unresolved premise still vetoes legal
promotion. If a compiler/certificate check fails, repair that implementation;
if the source premise remains unavailable, retain the question rather than
modifying the formal rule to match an expected case answer.
