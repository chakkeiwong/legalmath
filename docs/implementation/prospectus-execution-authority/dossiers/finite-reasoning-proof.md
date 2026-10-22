# Conditional finite-inference argument

Let S be the sorted set of syntactically occurring fact names in a supported
expression, with n <= 12. The checker numbers the 2^n complete valuations by
integers j. Fact i is true in valuation j exactly when bit i of j is set.
A truth table is an integer whose bit j is the value at that valuation.

The independent postfix interpreter assigns a constant the all-zero or all-one
table, assigns a name its column, uses intersection for conjunction and union
for disjunction, and complements within the finite universe for negation.
Structural induction on the expression therefore establishes that bit j is
exactly the ordinary Boolean value of the expression in valuation j. The
inductive cases depend only on Boolean identities for bit intersection, union
and complement, not on the production recursive interpreter.

For nonconflicting observations, intersecting the universe with each observed
fact's column (or its complement for a false observation) leaves exactly the
valuations extending those observations. Unknown or absent names impose no
restriction. Intersecting that compatibility table with the expression table
counts the true extensions; intersecting with its complement counts the false
extensions. Every extension is in exactly one set, and the compatible set is
nonempty. All-true means YES, all-false means NO, and two nonempty sets mean
UNKNOWN. Each supplied witness is checked for exact support, compatibility and
membership in the claimed set. The world count is the sum of both cardinalities.

Relevant explicit conflict yields CONFLICT and no worlds or witnesses. This is
the declared evidence policy, not a consequence of classical entailment from
inconsistent premises. An irrelevant conflict is ignored. Both policies are
tested, including a tautology containing the conflicted fact. Syntactic support
is intentional: algebraic simplification may not erase evidence conflicts.

The parser bounds depth at24, arity at128 and nodes at4096. More than12 facts
must yield the production DOMAIN_LIMIT refusal and cannot receive a positive
inference certificate. The certificate does not cover source constraints or the
optional Z3 engine. Digest checks bind expected inputs and output integrity;
they do not authenticate a publisher, prove a formula's legal interpretation,
or establish cryptographic resistance against a compromised verifier host.

The three separately encoded BASF hypotheses retain their distinct causal
premises. Agreement with production formulas proves that the implementation
checked those disclosed formulas. It does not prove that the candidate set is
exhaustive. Source interpretation, dates, notice, cure and actual holdings remain
separate premises. The actual consumer preserves its unresolved source question.
