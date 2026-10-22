# Raw source-hash repair review

PASS after tracing TextUnit.json in the production contracts module. It hashes
raw.encode(),not the JSON string. The unchanged source rows have correct byte
hashes. Candidate339 and its hand-built fixture shared the wrong convention;
both failures remain evidence. Candidate340 changes only the byte input and
uses the production TextUnit constructor in its new fixture. Seven mutation
cases include the wrong JSON-string hash. The original21tests and frozen
expected inventory remain unchanged. No source or acceptance requirement is
weakened. This fixes a local implementation/test assumption,not a package defect.

Wrong baseline,proxy promotion,hidden defaults,stops,environment and meaningful
command output were reviewed. Retain78admissions and all costs; one reviewed79th
admission remains within21600seconds/3200MiB. Forecast360seconds/64MiB. Continue
the original discovery work after exact baseline and isolated assessment pass.
