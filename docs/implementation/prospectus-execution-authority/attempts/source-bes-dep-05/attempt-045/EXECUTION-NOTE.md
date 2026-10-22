# Execution note

After the tests stage returned PASS, an accidental repeated `tests` dispatch
was refused immediately with `Stage already started or unknown`. It did not
start another worker or rewrite the completed test receipt. The original
41-test result remains the evidence. Subsequent work used the ready baseline
stage. This refusal demonstrates this particular duplicate guard, not general
restart correctness. No external call or production change was involved.
