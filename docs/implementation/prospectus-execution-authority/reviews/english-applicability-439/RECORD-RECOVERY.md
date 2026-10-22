# Adopt the recorded result after projection timeout

The authority appended RECORD event
`f370e87baa0c012d1601f74595c6efcb6eb77a871892f7b79dc9beb8ce7409f0`
for source09/015, binding outputs
`3ad335b458b0c539a5e8247717e3d3c0890388d8c21d2cd5ead6ec5f3a4f20f1`.
The15second wrapper then timed out while regenerating the status projection.
Its failure is retained; it does not undo the committed RECORD or justify
rerunning the candidate, installed trial or submission.

The mistake was estimating recording from the absence of a substantive
task validator while overlooking the cost of the subsequent full status refresh.
Admit's retained event times show that its refresh alone took15.79seconds.
The narrowed15second recording limit was therefore insufficient. The original
90second allowance would have covered that workflow but did not fit the
conservative allocations charged during this preparation.

Recovery is read/verify/adopt only: check the retained output manifest against
the committed event, run the existing `resume` projection recovery with short
tool yields, collect its terminal result, then refresh and inspect continuation.
No authority record or substantive trial is redispatched. Retain projection
wall time separately under the historical startup/final-receipt exclusion;
do not turn that exclusion into another source09trial allowance. The original
1960second substantive allocation remains, with about4.36seconds of charged
headroom before any further analysis. A new substantive source09campaign needs
an explicit reviewed cumulative extension. Independent source tasks remain
available through their own reviewed continuations.

The source repair itself has155passing tests and matching candidate/current/
installed answers. This recovery concerns bookkeeping after a committed result,
not a new claim of task acceptance. Do not edit sealed015or revision439inputs.
