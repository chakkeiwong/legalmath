# G3 adapter repair review

The first retrieval request failed in `legalmath.canonical._check` before a
provider reservation. Its eight BM25 scores are Python floats. The product's
canonical request format deliberately admits only exact integers, strings,
booleans, lists and dictionaries. The baseline and structured requests returned
valid source-cited answers, so this failure is not evidence of provider failure
or poorer legal reasoning with retrieval.

The repair will pass ordered passages with integer ranks, retaining raw scores
in the existing retrieval evidence. It will validate every assembled direct
request against the actual product serializer before dispatch. Changed failed
requests receive new immutable request directories, while unchanged successful
requests are reused. Original provider reservations and failures are preserved.
This changes the adapter, not the source corpus, passage order, relevance labels,
legal questions or model route. It is one counted repair within G3.

Skeptical audit: a serializer-only test is an engineering check. It cannot show
retrieval benefit. The repaired direct and actual product comparisons must still
run. A pre-dispatch failure must be distinguished from a failed counted provider
call; neither can be treated as a valid negative legal answer. No new phase or
budget increase is proposed.
