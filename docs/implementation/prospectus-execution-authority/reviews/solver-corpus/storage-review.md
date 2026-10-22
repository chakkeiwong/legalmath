# Correct preparation accounting before admission

The first preparation exited 1 after seven checker tests passed. Its final
2 MiB preparation check included a 6,340,530-byte copy of the existing master
program. The review itself occupies 440,861 bytes; the retained route map
occupies 108,729 bytes. The original assumption that review plus full authority
proposal could fit in 2 MiB was wrong. No task was admitted and no corpus ran.
The original proposal, review, frozen files and test receipt remain unchanged.
The preparation.json PASS describes completed checks before this later failure
and must not be read as a successful complete preparation.

Revise only preparation storage to 24 MiB, inclusive of both proposal copies,
their reviews, route map, review files and the eventual accepted revision copy.
The total package ceiling remains 32 MiB with a 1 MiB reserve. This explicitly
budgets immutable copies of the large existing authority. All prior attempts,
costs, 60-second preparation bound and subsequent 120-second stage bounds stay
unchanged. Reuse the seven passing tests and frozen source identities; do not
repeat the failed preparation or run new tests. The follow-up only verifies
unchanged files and creates a reviewed proposal with this disclosure attached.

Skeptical re-audit: PASS for this correction. The candidate question, original
baselines, all substantive criteria and partial disposition remain unchanged.
The failure concerns our accounting assumption, not Z3 or the consumer. Stop
if cumulative bytes plus reserve exceed 32 MiB; no further storage allowance
or seventh task admission is granted.
