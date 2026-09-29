# C4 diagnostic repair: recursive schema alternatives

The first focused addition run completed nine checks, including actual three-
and four-operand Java/Catala runs. The twenty-operand case then consumed Python
CPU before producing a target build. An owned SIGINT retained the traceback in
`jsonschema/_types.py:52`; the run ended after 242.45 seconds. This is an
implementation/capacity failure, not evidence against ordered exact addition.

The RuleIR expression schema uses recursive `oneOf` alternatives. Several
alternatives contain the same `left`/`right` recursive fields; ordinary schema
validation explores those fields even when that alternative's constant `op`
already makes it impossible. A long left fold magnifies this repeated work.

Reviewed repair: specialize `oneOf` evaluation only by discarding alternatives
whose required string discriminator (`op` or `type`) contradicts the actual
string value, including a nested `oneOf` when every branch is impossible. Leave
all uncertain branches and all their ordinary schema checks intact. No
acceptance condition is weakened, and the schema bytes stay unchanged. The
logical justification is that a conjunction containing a false required
constant/enum condition cannot satisfy a `oneOf` branch. Numeric equality,
optional properties and arbitrary schemas receive no inferred shortcut.

Acceptance: compare the specialized validator to the original Draft 2020-12
validator on nested expressions and malformed variations, preserve all existing
RuleIR regressions, then execute the unchanged twenty-operand backend test.
No runtime ranking or legal-accuracy inference follows. This is a repair within
C4; neither the stopped run nor its missing result is counted as a pass.
