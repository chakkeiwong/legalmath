# Local source-validator defect

The source stage failed before candidate generation or production edits.
The common same() helper JSON-encodes its arguments; this runner passes Python
sets at two coverage comparisons. Sets cannot be JSON encoded. The traceback
identifies this implementation defect in our runner, not invalid source text,
failed package capability or a disproved interpretation.

Repair: use direct set equality through require() at both comparisons in a new
reviewed refinement, retaining this frozen runner and attempt unchanged.
Reproduce the corrected source check with the retained 172 original occurrences
and independent image transcript before freezing the repair. Reuse authenticated
images and transcription; do not re-render or repeat extraction. Preserve all
37 original required task states and complete030 production/answer baseline.
Coverage and sealing remain ready. Production tests and installed verification
remain blocked in this failed attempt and will run only under the repaired
admission. No unchanged retry is authorised.
