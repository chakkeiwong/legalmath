# P0 repair: retain the document route's bounded output policy

The first execution stopped before building because the reused round-11 document
entry point rejected a round-12 output path. This is an integration defect in
the command contract, not a manuscript failure. Permit the exact round-12 root
only for the document route; source/formal/evaluation round-11 routes retain
their old output boundary. The repair command executes the focused workflow and
controller regression before retrying the same required document build. No
historical attempt or output was overwritten.
