# Independent source wiring audit

The supplementary AST scan inspects task-name literals outside the capacity
policy, executor, adapters and checkpoint modules. Every one of the 20 registered
model stages has a source call site. Direct `service.complete` calls in the
active bounded product are confined to its dispatch transport, after shared
capacity handling. The acquisition route, phased answer route and matched-effect
comparison explicitly select the registered common-capacity profile.

The broad scan also finds historical alternative route names:
REVIEW_SOURCE_CLAIMS, REVIEW_SOURCE_INTERACTIONS, REVIEW_SOURCE_OMISSIONS,
REVIEW_DOSSIER_EVIDENCE, REVIEW_DOSSIER_INTERACTIONS,
SYNTHESIZE_WHOLE_DOSSIER_ANSWER, REVIEW_GROUNDED_PRODUCT_ANSWER,
ANSWER_COMPLETE_INVESTIGATION, REVIEW_SCOPED_EVIDENCE and
SYNTHESIZE_INVESTIGATION_ANSWER. These are used by older non-bounded routes.
`legal_product_completion.py` selects the bounded route explicitly and passes
its session into investigation/dossier entry points. The old route branch
appears after that branch returns. The error marker
STRUCTURED_CRITICISM_UNAVAILABLE and prefix AUDIT_ are not model stages.

The source check complements, rather than replaces, the 174-test regression
report: looping over the registry alone would not prove call-site coverage.
It does not establish arbitrary future stages, successful live legal judgments
or correctness of historical routes outside this migration.
