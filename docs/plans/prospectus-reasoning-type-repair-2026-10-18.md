# Exact JSON types at the reasoning acceptance boundary

Post-acceptance review of revision261 found that its newly added `same` helper
uses Python equality, which equates False/0 and True/1. The installed-input
review had already identified this risk. Before further source work, determine
whether the new complete-answer validator actually accepts a type-altered Q3
coverage flag. Preserve accepted reasoning010, its history and its original
methods. This is a hypothesis about the acceptance implementation, not evidence
of a production calculation or package defect.

The smallest diagnostic copies reasoning010's source evidence to a temporary
directory, changes one original current answer's Q3/Q1 completeness from False
to0 while preserving every other field, and invokes the real retained-evidence
verification. The baseline must pass; the mutation must be refused. Retain the
actual outcome, original and mutated record identities and exact field path.
No source, old output or result is rewritten. Diagnostic bound30seconds and
8MiB temporary files; no subprocess/network/native calls in the comparison.

If reproduced, use canonical JSON equality with non-finite numbers forbidden
for complete-value comparisons. Add controls for both Boolean/integer pairs,
integer/float and nested fields, plus complete-case omissions. Freeze the
repaired helper and validator before one reviewed reasoning admission,10to11.
Revalidate the immutable010 complete source/installed records using the corrected
checker and a fresh current complete replay. No production file changes or wheel
rebuild are justified: the installed package must match the unchanged current
production map byte for byte. Verify010's actual output/admission seals and bind
all its outputs as new inputs. An old PASS or helper-only test cannot close repair.

Primary criterion is exact typed original-record equality and actual refusal of
the complete-answer attack. Missing cases, changed unrelated answers, old-source
corruption, mismatched installed bytes/imports or unbound changed methods veto
acceptance. The repair changes checker semantics; it does not change source
interpretations or legal conclusions. The original finite engineering criteria
and all59 obligations remain intact. The prior ACCEPT remains historical;
current acceptance requires the repaired validator's new actual event.

Skeptical audit PASS for this bounded reproduction and conditional repair. An
invented malformed-record unit test would not establish the actual gap, so use
the real complete-answer verifier first. Allow only the comparison helper,
acceptance wrapper, their focused tests and this support runner to change.
Keep before/after method copies and exact diffs. Reuse the original720-second
and128MiB incremental campaign envelope, adding all261/262 preparation, review,
proposal, revision, attempt and diagnostic costs; historical pre261 time remains
unknown. Each new command110seconds, preparation90seconds, no unchanged retry.
An unexpected failure requires diagnosis and a reviewed revision, not silent
changes to frozen files. Continue source-authority after recording and refresh.
