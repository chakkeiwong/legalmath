# Keep parenthetical prose out of paragraph addressing

Attempt085 passed the transformation controls but failed the original source test.
Its broad [a-z]+ heading pattern reads (etwaiger), an ordinary German word, as a
paragraph label. That resets section9's parent and truncates its first paragraph;
the retained diagnostic locates all three remaining destination differences in
that affected section. This is our lexical implementation error.

Change only the candidate heading pattern: digits, a single letter, or a Roman
letter sequence may be label candidates. Other multi-letter parenthetical words
are prose. Label-like unsupported forms still fail through the existing level
validator; the supported alphabet and Roman hierarchy are unchanged. Preserve
all original destination intervals, expected hashes, interpretations, grammar
tests, transformation provenance and failed085 evidence. Add lexical regression
tests for ordinary words, bracket variants and unsupported label-like tokens.

Evidence contract: unchanged independently frozen29destination readings and all
original source/grammar/adverse cases, plus the new lexical controls, must pass
before complete ordinary/installed consumers. Exact complete answer equality is
the primary criterion. Wrong parents, truncated intervals, missing transformation
provenance or legal/UNKNOWN promotion veto acceptance. Frozen drift, corrupt
baseline and cumulative resource exhaustion veto this attempt. Counts and time
are explanatory. General grammar recall and legal meaning remain unevaluated.

Skeptical audit PASS. A blanket skip of every invalid heading would conceal
unsupported true labels; the revised lexical distinction avoids that failure.
The diagnostic was not used to relax expected destinations. It isolates the
wrong lexical assumption and keeps all unchanged source comparisons mandatory.
No package defect or fundamental method failure is established.

Use original basf-references admission086/revision347. Preserve all85admissions
and costs; keep24000accounted seconds/3456MiB with4MiBreserve. Forecast1150seconds
and128MiB. No unchanged retry, network,GPU,subagents or Git writes. CPU-only,
one-second yields and original-session polling. Run prepare/revise/check/status/
admit/install/tests/consume/controls/package/installed/seal/record/refresh with
scripts.prospectus_reference_label_grammar and the same prospectus controller.
