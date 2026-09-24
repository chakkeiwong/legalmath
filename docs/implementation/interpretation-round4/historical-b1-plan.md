# B1: resolve exact public authorities without losing their qualifications

B1 follows the B0 acceptance manifest under
`artifacts/interpretation/round4/B0`. Its machine plan is refreshed automatically
at `artifacts/interpretation/round4/B1/next-plan.json`. B1 is not yet implemented
or executable by the supervisor. Preserve the completed A7 and B0 records as
comparators. The original B1–B5 backlog remains in
`docs/implementation/interpretation-round3/next-phase-plan.md`.

## Concrete starting workload

The retained 23EC46 investigation has 19 DEPENDENCY findings. The selected-control
inventories identify two required public sources: paragraph 3.11 of the *Code of
Conduct for Persons Licensed by or Registered with the Securities and Futures
Commission*, and answer 1 of the SFC Code of Conduct FAQ identified as issued
30 September 2010. The two readers use different word orders for the FAQ title;
these are candidate aliases to verify against a retained authoritative identity.
Several remaining findings ask where these provisions and their dates are bound
to the executable control. Repeating model readings cannot supply absent text.

The 24EC16 investigation has one DEPENDENCY finding whose locator is the circular
itself: `SFC circular, refNo=24EC16 (official locator in source packet)`. First
check exact identity against the already retained root document. It may be a
resolvable self-reference rather than a new missing authority. Do not count
removing a redundant dependency question as evidence of improved legal accuracy.

Other provisions were marked outside the selected gift-control scope by the
inventory readers. Retain those decisions and their source evidence. Expanding
the selected control requires revisiting their relevance; a stored CONTEXT label
does not prove an authority irrelevant to every application.

## Implementation order and interfaces

1. Add strict records for authority identity, document edition and provision.
   Identity includes issuer, jurisdiction, authority type, official locator and
   verified aliases. Edition records separately represent publication date,
   effective interval, retrieval time, raw bytes hash and provenance. Unknown
   effective dates remain unknown. A model-proposed alias needs retained evidence;
   a similar title alone cannot establish identity.
2. Build a versioned local catalog and explicit relationships for citation,
   incorporation, amendment and replacement. Bind each relationship to source
   spans and affected control IDs. Resolve an exact self-reference from retained
   root metadata before attempting a network retrieval. Return RESOLVED,
   AMBIGUOUS_IDENTITY, UNKNOWN_VERSION, MISSING_PROVISION or UNAVAILABLE with the
   considered alternatives and evidence. None of these results is legal approval.
3. Acquire and retain complete official bytes for the two 23EC46 authorities.
   Match the applicable edition to the declared evaluation date, with authority
   for the date relationship. Current website text is insufficient evidence of
   an older edition. Preserve superseded editions for applicable historical dates;
   reject using them for a date they do not govern. Document an unresolved edition
   rather than inventing an effective date.
4. Implement bounded provision selection with source locations, parent headings,
   attached footnotes, referenced definitions and material qualifications. Its
   output must include selected spans, reasons, unresolved references and omitted
   context. Retain full bytes separately. A size limit returns CONTEXT_INCOMPLETE,
   not a silently shortened packet described as complete law. Review changes to
   `audit_packet` explicitly; do not disable whole-source coverage checks merely
   to make excerpt selection pass.
5. Add page-level visual-completeness diagnostics for PDFs. A partially scanned
   page or image-based footnote must remain an unresolved acquisition problem when
   the available extractors cannot recover it. Agreeing text extractors do not
   prove completeness. If OCR is introduced, retain engine/version, page images,
   located text and uncertainty, and verify it against controlled image/text
   fixtures before using it to resolve a dependency.
6. Feed the expanded, version-bound packet through both blind inventories and the
   existing source-fidelity checks. Use B0 preflight before dispatch: added source
   claims may increase the matrix beyond budget. Pass changed dependency hashes
   to the monitor; create immutable successor investigations only for controls
   whose declared dependency closure changes. Retain failed retrieval and retry
   exhaustion in that closure.

Implement under the existing assurance/source and monitor boundaries. The exact
module split should follow a code audit, not a parallel catalog disconnected from
the runtime. The CLI must accept a catalog manifest and expose the selected
edition/provision evidence in the investigation report. Preserve compatibility
with explicitly retained documents while making implicit alias decisions visible.

## Required acceptance cases

| Input | Required behavior |
| --- | --- |
| Exact verified circular self-reference | Resolve to the retained root and its hash; make no retrieval call |
| Two verified aliases of the same FAQ edition/provision | One dependency identity, with both original requests retained |
| Same title, different edition or regulator | Report ambiguity or wrong identity; do not select by similarity score |
| Edition not applicable at the evaluation date, or applicability date unknown | Keep the control unresolved and identify the temporal evidence gap |
| Incorporated definition or remote footnote affects the selected provision | Include it, or mark context incomplete before interpretation |
| Page with text and a scanned qualification; two agreeing incomplete extractors | Flag unsupported visual content; do not certify source completeness |
| Provision text exceeds the request budget | Retain complete bytes and explicit missing-context evidence; make no truncated model request |
| Missing, denied or corrupted retrieval | Retain failure, bounded retries and unchanged unresolved dependency |
| One shared incorporated provision changes | Invalidate exactly the controls whose declared closure includes it; retain prior versions |
| Model/meaning remains uncertain after authority acquisition | Preserve rival readings and questions; no majority-vote resolution |

Before execution, add a B1 evidence contract specifying frozen inputs, exact
commands, acquisition limits and any live-call allocation. Deterministic catalog,
version and visual-completeness tests should precede live interpretation. The
standing ledger is 78/100; re-read it before allocating any of the remaining
calls. Keep acquisition of extra evidence separate from a comparison of reasoning
methods: unequal source access cannot establish that a search method is better.

Success means correct identity/version selection, context accounting and affected
control invalidation on these declared cases, followed by an honest account of
remaining uncertainty. Question counts and dependency counts are explanatory.
Corrupt source provenance or wrong temporal applicability stops dependent claims;
a recoverable retrieval/selection failure triggers the next bounded repair.
Authority resolution by itself supplies no population error rate for English
interpretation and does not justify removing all human escalation paths.
