# Smaller interpretation tasks

This continuation addresses an overloaded service response and a separate
180-second timeout in the round5 live experiment. Those failures occurred before
the source inventory completed. They do not identify a document-size limit or a
failure in the legal interpretation. The optional decomposition path reduces the
size of each reading task while keeping the complete source available for checking
relationships between pieces.

## Processing a document

Set `inventory_piece_characters` to a positive integer in `AssuranceSettings` to
enable decomposition; zero retains the previous whole-document path. Set
`inventory_piece_units` to bound the number of units as well as their character
count. The reviewed diagnostic uses 2,300 characters and at most 16 units per
piece. These are experimental settings, not recommended production defaults.

The implementation keeps source units intact, in their original order. A unit
that exceeds the character bound produces an explicit resource error. It is not
truncated. The first reader inventories all pieces, then compares its assembled
claims with the complete source. The second reader independently repeats this
process. Neither reader receives the other's inventory. Local claim IDs receive
distinct namespaces during assembly, so an ID repeated in two pieces cannot
accidentally join unrelated claims.

The final context check looks for definitions, exceptions, actor changes and
dependencies that cross a piece boundary. It must account for every source unit,
cite exact source text, and refer only to existing claim IDs. Its findings become
unresolved inventory questions. A missing piece or missing context check prevents
that reader from being treated as complete. The check is a model judgment with
validated references; it does not prove that no omitted qualification exists.

`CompactProvider` keeps the exact unit IDs, text, normative flags and source
identity in requests. Repeated storage locators and span dictionaries stay in
the local original request. Each transport record contains both forms, their
hashes, the response schema, and the returned response or error. This makes the
size reduction inspectable without deleting legal language. The remaining
generation and fidelity stages still receive full source context; decomposition
of the inventory alone does not bound every later synthesis request.

Request-byte measurements describe the application JSON, not the entire model
context. In the live D1 availability probe, the application supplied 200 bytes
and the provider reported 24,289 input tokens. Codex adds substantial surrounding
context. The transport reduction therefore cannot be read as an equivalent
reduction in billed tokens, total processing or latency.

## Failure, retry and resumption

The fixed live runner first requests a tiny structured availability response.
The probe contains no regulatory question and supplies no evidence of legal
correctness. It permits at most one retry for a recognized temporary service
failure. Authentication, schema, authority and input-size errors stop the probe.
The persistent allowance counts all dispatched calls, including failed probes.

After a successful probe, calls run sequentially. A transport availability error
opens a circuit for that investigation and prevents further paid requests through
that provider wrapper. The system saves the incomplete investigation and its
remaining uncertainty; it does not reinterpret a timeout as a rejected legal
reading. Invalid structured outputs remain distinguishable from transport errors.

For a reviewed successor, `RetainedProvider` can replay exact requests and schemas
from a completed investigation manifest. It verifies the retained files, response
hash, compact transformation and original allowance reservation. The replay is
marked as a previously counted action, not a new independent reader. A changed
request or schema is a replay miss; a new live task requires explicit admission
to the successor's bounded work. Running the original completed phase again is
refused. Never delete failed calls, reset the allowance or overwrite an attempt.

## Commands and evidence

The phase runner accepts only its fixed commands. It hashes source code, tests,
contracts and public source snapshots, checks its recorded review, and protects
previous evidence before and after execution. A failed acceptance attempt needs
an executed repair note and a refreshed review before retry.

```sh
/home/chakwong/python/legalmath/.venv/bin/python /home/chakwong/python/legalmath/scripts/run_decomposition_plan.py preflight
/home/chakwong/python/legalmath/.venv/bin/python /home/chakwong/python/legalmath/scripts/run_decomposition_plan.py status
```

The phases are D0 (focused engineering checks), D1 (bounded live feasibility),
D1R (resume after the observed source-derivative repair), D1F (attempt to finish
the complete matrix), D1S (four-pair size diagnostic) and D2 (final regression).
A live phase marked `PASSED` means the
runner recorded valid evidence and respected the allowance. Consult
`D1/attempt-*/live/summary.json` for whether the service answered, whether the
investigation completed, and what remains unresolved. These distinct meanings
must not be collapsed into a claim of correct English interpretation.

The [pre-run plan](../../plans/interpretation-d1-decomposition.md) states the
evidence contract. The [pre-live audit](pre-live-audit.md) records the actual
replay and retry repairs. The existing 100-call ceiling is unchanged; the first
D1 attempt begins at 80 consumed calls and admits at most 20 more.

D1 completed both readers and their whole-source checks. It then exposed a
database import error: source spans used the original HTML extraction's CRLF
offsets, while database import normalized that derivative to LF. The explicit
`preserve_retained_text=True` import option now preserves the derivative already
used for citations. Default imports still normalize text. D1R replays the eight
retained reading responses against exactly the same source packet; it admits at
most 11 new downstream calls from the 89-call ledger checkpoint. The original
failure remains recorded.

Fidelity requests now include only the extracted claims and candidate meanings
needed for the exact requested pairs; each request still includes the full
source text. The aggregate validator continues to require the entire declared
matrix. A completed small batch is a checkpoint toward that matrix, not a
substitute for all of it. The original 32-pair default remains unchanged. D1F's
one-run 51-pair setting timed out; D1S examines a four-pair task separately.
