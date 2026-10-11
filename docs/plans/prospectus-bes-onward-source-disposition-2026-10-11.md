# BES Series 23 onward-source disposition and applicability consumer

## Research intent and evidence contract

The question is whether the retained BES Series 23 source chain can represent
the named onward records and agency instruments without silently treating a
mention as a supplied source. The candidate mechanism is an exact retained
corpus disposition for each missing item, followed by a source-specific service
consumer that binds the final terms to the base prospectus passages describing
the agency instruments and their Portuguese-law, forum, book-entry, and generic
ICSD contexts.

The immutable comparator is `bes-source-chain/consumer/attempt-007` and its
assisted report. The consumer must preserve the 23 final-terms readings and
the seven previously resolved source-chain edges. The primary criterion is
source identity and applicability integrity: every missing item has an exact
introducer anchor, expected issuer/date/scope, a retained-corpus search record,
and remains `UNRESOLVED` when no authenticated original bytes are present. The
new reviewed applicability edges must resolve only when their selected retained
passages survive the assembly.

Promotion vetoes are a missing introducer anchor, a candidate accepted without
original bytes and an acquisition identity, a source/date/issuer mismatch, a
changed final-terms raw map, or an automatic legal conclusion from a generic
ICSD or Portuguese-law statement. Omission controls are diagnostic gates for
the new applicability edges; they do not establish legal correctness. Counts,
runtime and the number of search files are explanatory. This phase cannot
establish source authenticity, the contents of any absent agreement, actual
Eurosystem eligibility, independent legal acceptance, or package superiority.

## Skeptical audit and defaults

The phase uses the retained repository corpus only. This is deliberate: the
previous source-chain plan prohibited network acquisition, and a web hit without
an authenticated original would not close the source gap. The corpus boundary
is recorded and hashed, so `NOT_LOCATED_IN_RETAINED_CORPUS` is not presented as
an exhaustive internet search.

The expected dates and issuers come from the exact incorporation titles and
the 2010 base prospectus. They are hypotheses used to reject mismatches, not
proof that a missing record exists. The agency applicability review uses only
the retained base and final-terms passages; it cannot be promoted to a review
of the absent agreements. The service remains in CPU mode and uses existing
retained OCR/native inputs; no OCR or package installation is needed.

Pre-mortem: a report could list the 14 dependencies while omitting their
issuer/date/scope bindings; the disposition schema rejects that. A generic
book-entry or safekeeper sentence could be mistaken for the operative agency
terms; category-separated applicability records and separate edges prevent
that. A source edge could appear resolved after its representative is removed;
the four omission controls veto that result. A stale or foreign edition could
be accepted; wrong-edition and wrong-date controls veto it.

## Ordered execution

1. Build and hash a deterministic retained-corpus manifest. For each of the 11
   financial records and three agency agreements, bind the introducing source
   hash/page/quote, expected issuer/date/scope, candidate paths, original-byte
   hash (null when absent), and disposition reason. A missing or unauthenticated
   item remains unresolved.
2. Review and retain exact source anchors for (a) named agency instruments and
   precedence, (b) Portuguese-law and jurisdiction language, (c) Interbolsa
   book-entry and Common Representative language, and (d) generic ICSD/common
   safekeeper language. Keep these categories in a separate applicability file.
3. Construct one request from the existing eight-document source-chain request,
   adding only the reviewed applicability edges and the bound unresolved
   dispositions. Run the actual service with `CUDA_VISIBLE_DEVICES=-1` under a
   1,200-second bound. Compare final-terms source units and question statuses
   with the immutable comparator.
4. Run four matched omission controls, including the Common Representative
   edge, plus wrong-edition and wrong-date controls. Record the exact rejected
   or unresolved dependency IDs and the request/report hashes.
5. Write the result, reset memo and next program. Refresh the root residual
   ledger only with the evidence this phase actually establishes; absent source
   bytes, independent legal review, native confinement/portability and broader
   scan families remain open.

## Stop rules

Stop this phase on hash corruption, an unexpected source graph or final-terms
map change, a service timeout, an accepted wrong edition/date, or an omission
that leaves its edge resolved. A valid missing-source disposition is not a
continuation veto; it schedules an external acquisition/authentication work
order.

## Exact command

```text
timeout 1200 .venv/bin/python docs/implementation/prospectus-integration-closure/bes-onward-sources/consumer.py
```

The output directory is
`docs/implementation/prospectus-integration-closure/bes-onward-sources/`.
The command is deterministic apart from timestamps and must be run with
assertions enabled and the repository worktree fixed.

Skeptical audit: PASS. The comparator, source boundary, primary criterion,
promotion/continuation vetoes, omission controls, and artifact paths are
explicit. No artifact from this phase can answer the absent-agreement or
independent-acceptance questions, so those remain named limits.

## Post-run audit and bounded revision

The initial service checks passed, but their broader source-disposition claim
is unsupported. The filename-only search cannot identify originals named
`source.pdf`; its empty hits are not evidence of absence. Several one-line
anchors omit the date, parties, Portuguese-law conclusion, precedence
qualification or other-competent-courts sentence described by their readings.
The wrong-date control exercises graph identity after metadata changes, not
authentication or an independent effective-date interpretation.

Preserve the latest initial package as `bes-onward-sources/attempt-001/`,
including the executed consumer bytes. Earlier repeated runs overwrote that
package; their individual reports cannot be reconstructed and are not separate
observations. Repeated service calls to refresh documentation hashes were
unnecessary. All future execution artifacts go to a new immutable attempt;
human result notes sit outside that attempt and do not trigger service reruns.

One revised local execution is admitted, still CPU-only and bounded to 1,200
seconds. First scan retained text and metadata, including decodable `.bin`
responses, and bind every hit and every unsearched binary. Search leads are
not authenticated originals: use `NO_AUTHENTICATED_ORIGINAL_BOUND` rather than
claiming repository-wide absence. Validate every historical introducer's PDF
hash, text hash, page and quoted span. Retain complete identity and governing
paragraphs, including dates, named parties, the Interbolsa precedence branch,
Portuguese-law conflicts qualification, other competent courts and the full
eligibility disclaimer. Pass those anchors through the actual service.

Before the revised service run, perform a cheap preflight on the disposition
and paragraph coverage. Keep the original 23 readings, all source units and
all seven chain edges. Four omission controls must remove substantive clauses
including the Common Representative passage; save each request and report
digest. Preserve exact edition and changed-date-graph rejections with their
actual diagnostic scope. No source acquisition, OCR or package installation is
admitted here. Any remaining absence of an original is a promotion veto and
an acquisition task, not a reason to replay local checks.

Audit of this revision: PASS with explicit limits. The source comparator and
host environment are unchanged; complete paragraphs replace incomplete
representatives, content searches replace filename proxies, and ambiguous
search hits stay unreviewed. Runtime and counts remain explanatory. Stop on
input corruption, source-map drift, failed controls or timeout. Preserve an
unsuccessful attempt and investigate before any further run. This is a source
and engineering repair; it cannot validate legal interpretation or package
superiority. Hash-only/documentation changes need a manifest check, not a
service run.

## Execution record

`attempt-002/` passed the revised command. It consumed eight documents and
18,036 source units, preserved seven earlier chain edges, resolved four
category-separated applicability edges, retained 14 unresolved onward rows,
and passed four omission plus two adverse controls. The final question
statuses are Q1/Q2 `UNKNOWN`, Q3 `PARTIAL`, Q4 `UNKNOWN`, Q5 `UNSUPPORTED`,
and Q6 `UNKNOWN`. The run completed in about three minutes under the bound.
The complete package is hash-bound in `attempt-002/manifest.json`; the initial
unsupported package remains in `attempt-001/` for diagnostic history.
