# Tool sessions

All commands use timeout120 and one-second yields. Poll the existing session;
never infer permission for a duplicate from a lost stream. Started markers
retain the actual PID and method identity. Stage results decide completion.

| Stage | Tool session | Last observed result |
| --- | --- | --- |
| init |49671|PASS|
| prepare |31033|PASS|
| tests |completed in launch call|PASS,137 tests|
| baseline-construct |86002|PASS|
| baseline-build |82385|PASS|
| baseline-dependencies |84679|PASS|
| baseline-interpret |14993|Running at this note; inspect result and poll|
