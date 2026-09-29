# Why the STR reference cases remain unexecuted

The five frozen STR reference scenarios ask whether footnote 3 requires an e-Cert
for the selected method and retain the blackout contact exception. The generated
executable candidates mainly answer whether a submission satisfies combined
channel, format and certificate conditions, or whether an event triggers a
separate resubmission duty. These are different output questions.

For example, `node.c8bd87cfd64bba8762d9b3a0` evaluates a combined compliance
predicate using a supplied `ecert_requirement_satisfied` fact. The frozen XML
scenario says the requirement applies; it does not say whether the certificate
requirement has actually been satisfied. Mapping its expected `REQUIRED` label
directly to Java `TRUE` would compare different quantities. Setting the missing
fact to true would silently add the answer instead of testing the requirement.

The urgent-blackout scenario also concerns a distinct instruction. An ordinary
post-launch predicate returning `OUT_OF_SCOPE` would not itself establish that
the urgent-contact instruction was preserved and correctly implemented.

Accordingly, no complete binding is supplied for these five references. The P5
evaluation must count them as unaligned and unexecuted. The ten runnable STR
candidate binaries and their independent conformance checks remain useful
engineering evidence, but they do not answer this frozen reference question.

The appropriate repair is a separately identified e-Cert-applicability control,
plus typed composition with channel compliance and the distinct blackout and
resubmission controls. A paired factual challenge with certificate satisfaction
true and false could test dependence of the combined predicate, but that would
be an additional conditional test with its own assumptions, not the originally
frozen direct applicability test. Keep that distinction explicit when designing
the successor experiment.
