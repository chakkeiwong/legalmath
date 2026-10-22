# Close the remaining normal-input comparison boundary

The four successful matched report replays start from frozen P1 products. They
establish downstream compatibility, but do not by themselves show that the
changed intake rebuilds those products. This is a material proxy limitation.

Rebuild only P1 for those same four frozen requests using the current service,
then compare the entire source graph and sealed P1 identity with the protected
baseline. Do not rerun the already-passing downstream consumers if their exact
P1 input is reproduced. Require retained OCR on every OCR-enabled document:
this diagnostic rerenders source images but must not launch fresh recognition.
Comparator: source-report freeze-002. Criterion: exact graph/P1 equality for all
four cases. Missing original/model identity, any changed unit, correction or
layout map vetoes compatibility. Runtime is explanatory only; no completeness
or independent acceptance conclusion follows. CPU only, one sequential pass,
600-second bound, no retries. Audit PASS: this directly checks the previously
unexercised builder without replacing the baseline or repeating downstream work.
