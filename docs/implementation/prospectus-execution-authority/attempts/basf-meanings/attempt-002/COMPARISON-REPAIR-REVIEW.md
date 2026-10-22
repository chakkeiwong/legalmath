# Exact heading-reference exception to the preservation criterion

The role-only actual consumer passes but the first comparator fails. Investigation
finds one removed dependency: the raw recognizer treated the isolated heading
`§ 5` on base page 118 line 15 as an unresolved operative reference. The inspected
page image and the frozen source show that line 15 and `RUECKZAHLUNG` on line 16
are section headings. The plan deliberately changes their role to HEADER, which
also removes them from reference-closure roots and reachable units. It necessarily
removes the single corresponding unresolved reference from each closure. No
substantive source, target, authority, prior meaning or dependency changes.

The initial contract's demand that every dependency remain byte-identical was
wrong for this reviewed heading change. This is a harness/plan error, not a failed
candidate or package limitation. Preserve compare_case.py and roles-comparison.json
as failure evidence. The revised comparator explicitly constructs the expected
dependency list: drop only the exact dependency whose quote is `§ 5` and whose
targets are empty; remove only those two known heading identities from Q1/Q2
closure roots/reachability and that single reference from closure unresolved.
Require full equality of every remaining field and dependency. Permit that exact
dependency id in the expected Q1/Q2 unresolved delta. The 146 selected operative
occurrences, supplied meanings and frozen product methods remain unchanged.

Audit PASS for one bounded comparator repair within the existing admission. A
different removed reference or any additional closure change must still fail.
The original result is not overwritten and no successful consumer is rerun. This
correction does not authorize general filtering of headings, a lower gap count as
legal progress, or an extra budget/admission.
