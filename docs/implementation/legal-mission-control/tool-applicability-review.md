# Tool applicability on the qualified P10/evidence request

11 October 2026 UTC. This deterministic diagnostic asks whether the selected
tools have the inputs needed for the actual P10/evidence answer request that
received a real model proposal. The comparator is the same 54 retained source
units, exact two questions and no invented reading or argument graph. Its primary
output is a typed applicability disposition, not a claim of legal improvement.
BM25 can run source-bound retrieval on each original question. LegalRuleML and
Logical English need a validated formal candidate; PyArg, Carneades and clingo
need an effective argument graph. The actual proposal/review produced prose,
not those formal inputs. Supplying an old fixture graph would change the target.

Run only the two BM25 retrievals. Inspect their exact source offsets and where
they would be attached, but do not present them to a model after the already
recorded response. Thus no downstream effect is measured. Mark the other five
as not applicable to this raw answer stage, while retaining prior product-path
fixtures as engineering evidence. Missing candidate structure is a blocker for
their actual answer-level evaluation, not evidence the tools are useless.

This check is CPU-only and offline. No grant call, legal promotion, ranking or
default change follows. A failure in BM25 leaves the existing model answer
untouched and does not block independent source analysis. The exact receipt is
under the current continuous-execution artifact directory.
