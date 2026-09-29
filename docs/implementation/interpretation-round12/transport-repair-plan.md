# Bounded live recovery and final controller audit

This repair is being prepared while the first complete P4 pass runs. Apply it
after that pass ends, preserving its code/input identity and outputs.

The question is whether retained source-only proposals can complete the required
checks without restarting paid successful work after a provider failure. The
baseline is P4 attempt 02: a stream disconnect in 24EC50 and 180-second inventory
deadlines in 23EC46 and 26EC2. These reject execution of those cases; they do not
reject the proposed interpretation methods.

The repair will retry only identified transient transport failures, at most
twice per dispatch and at most three reservations for an identical question in
the persistent journal. Every failure and interrupted reservation still consumes
the existing case/global allowance. A completed but incomplete interpretation
stage can be reinvestigated explicitly; semantic uncertainty alone is not a
transport retry. A new attempt reuses exact completed responses and revalidates
them rather than inventing a response or resetting the journal.

For source inventories that exceeded the time limit, use the existing piecewise
inventory implementation: smaller source units, both readers, and both cross-unit
checks. Every original source unit must remain accounted for. Use smaller
fidelity batches. Timeout/batch choices are resource hypotheses; a failed batch
remains incomplete. A finite per-call time increase remains within the existing
provider contract and master wall limit.

The controller audit also requires phase dependencies to include actual fixture
files, fixed helper scripts and tool locks; recovery of an interrupted supervisor
must preserve consumed phase attempts. A transfer-reference packet needs explicit
hash binding. These are engineering repairs, not grounds to relabel the new
examples as independently adjudicated holdouts.

Acceptance: forced transient failure succeeds only after a counted retry; a
permanent failure is not retried; retry exhaustion retains evidence; settings
changes cannot reset consumed calls; completed reports cannot hide unavailable
abstraction or argument checks. Focused tests precede the master retry and full
regression follows. Missing service after bounded repair is a real live-run
blocker; independent regression/evaluation should still finish and the final
report must show the incomplete live evidence rather than a blanket pass.

No fresh model-family diversity, legal error-rate estimate or reviewer-time
saving follows from successful recovery. The recorded artifact is the next P4
attempt, its durable case journals, and the final execution result.
