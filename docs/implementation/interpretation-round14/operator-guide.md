# Run and inspect the round-14 implementation

The reviewed plan is [assurance-round14-execution.md](../../plans/assurance-round14-execution.md).
Read its [repair review](repair-review.md) and [completion review](completion-review.md)
before resuming. The preliminary execution is rejected; only
`artifacts/interpretation/round14/execution-reviewed` supplies accepted phase
receipts. Every model reservation, including failed attempts, remains in the
shared round-7 allowance ledger.

## Fixed commands and resumption

Run from `/home/chakwong/python/legalmath`, using the installed Python 3.11
environment. The live provider requires trusted host execution with the existing
authenticated Codex installation. Do not override `CODEX_HOME` or copy credentials.
The approved command prefix is the absolute interpreter followed by this relative
script path:

```sh
/home/chakwong/python/legalmath/.venv/bin/python scripts/run_resolution_master.py audit
/home/chakwong/python/legalmath/.venv/bin/python scripts/run_resolution_master.py execute
```

The master fixes its eight phases and arguments. It hashes relevant inputs,
records each attempt, reuses unchanged successful work, and refreshes the next
phase's findings before dispatch. A code change invalidates the affected phase;
dependent phases rerun. Exact model request/response reuse avoids charging an
old response as a new judgment. The `repair` command follows the same execution
path; it grants no bypass around validation. A continuation such as
`execute --from R6` is accepted only when every predecessor receipt, result and
current input binding verifies.

The reviewed journal permits three attempts per phase, 24 total attempts and
eight hours from creation. R3 stops at 41 model actions or reservation 470;
the full round stops before dispatch beyond reservation 480. The shared user
allowance remains 500. Structural output repair is bounded, and the first
transport/resource failure stops further dependent dispatch. Failed and
interrupted reservations are never refunded. An exhausted journal requires a
new explicitly reviewed continuation bound to the old record; deleting a journal
or resetting its clock is not a repair.

## Evidence to inspect

`phase-results.json` identifies the current accepted directory for each phase;
do not infer it from an action number. R3's `result.json` preserves every original
unencoded parent, proposed children, parent/child reviews, and the 272 exclusion
challenges. `live-reviewed/restored-pairs.json` is a required queue for the next
source-fidelity investigation, not a record of completed fidelity checks.

R5's directory contains `prepared.json`, `generations.json`, `formal-input.json`,
`assured-cases.json`, compiled individual policies, and `assured-java/`.
The exact official circular and the withheld development cases are in
`docs/implementation/interpretation-round14/new-circular-official.json` with
the corresponding lock file. Its input facts are supplied classifications;
this increment does not derive asset classifications from bank records.

The older `new-circular.json` and `sources/23ec52.json` belong to the rejected
manually reconstructed capture. They must not be substituted for the official
files merely because their filenames are shorter. `sources-official` retains
the six successful public-source acquisitions and their receipts.

R6 contains the cvc5 comparisons and Catala build/verification reports. Its
parent action directory contains the full regression JUnit XML and log. R7
contains the document build/check logs and page count. The final execution
result and post-execution review distinguish passing engineering checks from
unresolved interpretation and document comprehension.

The completed run also has a deterministic post-build review in
`artifacts/interpretation/round14/post-execution-review.json`. It records the
two typography repairs made after the third R7 attempt, refreshed citation
context hashes, final PDF hashes and inspected page numbers. A future source or
document edit must create a new bounded post-review and repeat the rendered
inspection; it must not overwrite the accepted phase result.

The fixed offline delivery check is
`.venv/bin/python scripts/resolution_delivery_review.py`. It verifies all
accepted immutable journals, the exact tested implementation, retained source
and chapter hashes, backend results, final rendered PDF identity and the
unrefunded allowance prefix. It binds the final delivery manifest without
making model requests. It is deliberately tied to this completed round; the
next round needs a separately reviewed program and budget.

## Calling the generated Java

Read the actual `class_name`, `jar`, `jar_sha256` and source hash from R5's
`ensemble_build` record. The class exposes:

```java
String evaluate(String snapshotJson, String sourcePacketHash,
                String validAt, String knownAt)
```

Use the snapshots and ISO timestamps in `assured-cases.json` for an exact replay.
The command-line entry point accepts one JSON request per line with keys
`snapshot`, `source_packet_hash`, `valid_at`, and `known_at`; invoke Java with
`-cp <jar> <class_name>`. A bank adapter would call the same method after
constructing evidence-bearing facts and checking the expected source edition.
No bank adapter or production authorization is supplied by this increment.

The response includes each reading's result and the question, source, snapshot
and retained-set hashes. `INVARIANT_KNOWN` means that every retained executable
reading returned the same Boolean on these supplied facts. `INVARIANT_NOT_APPLICABLE`
means that all readings placed the facts outside scope. Missing encodings,
unknown/conflicting facts, differing results and changed source editions receive
distinct refusal states. A missing branch cannot be dropped to obtain agreement.
Every response remains `release_eligible: false` and conditional on the retained
interpretations. Hashes bind the supplied contents; they do not authenticate an
untrusted caller or prove completeness of English interpretation.

## Repairs and limits

A null formalization represents unresolved meaning until demonstrated otherwise.
Propose a new formalization or decomposition with every parent item accounted
for, compile it, and obtain a fresh review of the actual compiled meaning.
Keep the original parent and any unestablished conditions. A compiling child
cannot silently replace a broader duty.

Reacquire an authority when its bytes change, retain the old edition for
historical replay, and invalidate current assurance. The public JFIU sources do
not themselves supply the XML schema, operational certificate mechanics or an
invented resubmission deadline. The gifts FAQ does not automatically resolve
the mixed-package question. The new-circular packet includes the body and
footnotes; its appendix and incorporated legislation remain separate dependencies.

The program checks useful positive and negative decisions as well as refusals.
Successful refusal alone is not a successful useful-decision demonstration.
The frozen reference cases are author-created development expectations and
the readers share one model family. Further cases, more votes, or additional
software tests cannot by themselves establish an independently measured legal
accuracy rate or savings in professional review.
