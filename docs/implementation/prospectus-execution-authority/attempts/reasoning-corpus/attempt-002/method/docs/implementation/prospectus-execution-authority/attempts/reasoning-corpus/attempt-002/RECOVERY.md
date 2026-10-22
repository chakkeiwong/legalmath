# Correct a diagnostic assertion and retain the completed case

The first finite command retained its baseline, products and case000, then
failed an overly broad assertion. Q3 remained PARTIAL as required, but its
embedded Q4 explanation correctly changed from no supplied basis to the
evaluated candidate evidence. Q1/Q2/Q5/Q6 were unchanged. The bound plan requires
Q3 to remain PARTIAL, not its Q4 explanation to ignore newly supplied evidence.

The original runner, methods and failure remain immutable. The recovery runner
reuses the completed finite baseline and case000 after checking their exact
source, product and input identities; it does not execute them again. It runs
only remaining finite cases, then the previously unstarted Z3 cases. It checks
Q3 PARTIAL, unchanged Q1/Q2/Q5/Q6 completeness entries, and the Q4 explanation
against the actual Q4 result. This is a harness repair, not a production repair,
candidate rejection or change to the original promotion criterion.

Recovery audit PASS: the changed diagnostic now matches the predeclared plan;
every oracle comparison and witness check is preserved. Preserve the failed
command in the manifest. No new task admission or live-call allowance is used.
