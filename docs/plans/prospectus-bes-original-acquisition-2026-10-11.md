# BES original-source acquisition, 11 October 2026

## Question and comparator

Can the fourteen onward dependencies in the preserved
`bes-onward-sources/attempt-002/source-disposition.json` be supplied with
original documents matching the cited issuer, edition, reporting or agreement
date, and required pages? The comparator is that unresolved disposition and its
hashed introducer sources. Search results are leads; a different year's report
or a prospectus mentioning an agreement is not the missing original.

## Evidence contract and skeptical audit

The primary acquisition criterion is retained original bytes with a public
publisher route, retrieval receipt, SHA-256, and source-page checks against each
dependency's expected identity and scope. Record provenance, identity matching
and independent authentication separately. A public archive copy can establish
what bytes were retrieved there; it cannot by itself establish independently
authenticated execution of an agreement or legal applicability.

Wrong issuer, period, edition, missing required pages, an HTML error disguised
as a PDF, or absent executed terms veto admission of that candidate. An
unavailable or rejected candidate schedules another distinct route within the
bound; it does not justify fabricating contents or claiming exhaustive absence.
Hash corruption or changes to the protected comparator stop the work. Counts,
search ranking, file size and elapsed time are explanatory only. No package
ranking, legal conclusion, entitlement or collateral eligibility follows.

Expected identities come from the retained prospectus and remain hypotheses
to verify against the originals. Prefer issuer, exchange and regulatory public
archives; retain other mirrors as unverified candidates. English pagination is
not assumed identical to a Portuguese edition. Inspect printed page labels as
well as PDF page indices. Distinguish reporting dates from publication dates.

This acquisition does not modify the controller, tests, input packets or plans
bound by the active R4 run. It writes a separate acquisition directory. No
emails, authenticated account actions, purchases, package installs or live
model calls are included. Public read-only retrieval is within the user's
standing source-download request. Sandbox/network restrictions remain in force.

## Bounded execution

1. Preserve the fourteen expected identities and the comparator's hash. Search
   public sources using up to 28 targeted queries, beginning with financial
   records and then the three named agreements.
2. Retain at most twenty candidate files and 200 MB total, with a 25 MB and
   60-second ceiling per retrieval. Use HTTPS, retain redirect destinations and
   response metadata, and do not overwrite existing attempts. A rejected route
   gets at most one distinct replacement within this bound.
3. Check PDF headers, parseability and page counts; extract with the installed
   `pdftotext` tool. Inspect the title, entity, period, audit status and specified
   statements/pages. Preserve exact page evidence and all rejected identities.
4. Write candidate dispositions and the next concrete consumer plan. Keep
   original dependency resolution unchanged until reviewed source identities
   are admitted into a frozen consumer with omission/date/issuer controls.
5. Resume the phase controller after R4 seals; source acquisition cannot
   substitute for R5–R8 validation.

Artifacts go under
`docs/implementation/prospectus-integration-closure/bes-original-acquisition/attempt-001/`.
Retain query/route notes, original bytes, extracts, retrieval metadata, review
records and a manifest. A focused extraction or identity check is a diagnostic,
not an accuracy benchmark. No stochastic ranking or scientific promotion is
planned.

Audit verdict: the comparator, acceptance boundary, adversarial identity
checks, budget and stop conditions are explicit. The strongest risk is mistaking
a plausible report or contractual mention for the exact incorporated edition;
page and issuer checks address that risk before any consumer integration.

## Measured transfer-bound revision

The issuer archive is reachable and lists exact 2008/2009/2010 PDF links.
The first batch inside the sandbox failed DNS resolution; those receipts stay
retained and a trusted retry uses the same routes. The trusted server returns
HTTP 200 and valid PDF starts, but its observed rate is about 40–47 kB/s. The
2010 file is 8,125,384 bytes and the 2009 file is 4,460,884 bytes; both exceed
the initial 60-second convenience deadline. These timeouts say nothing about
the source identities or engine capability.

One resumed transfer per partial PDF is admitted into a new candidate directory
under a 300-second ceiling (at most 900 seconds for three candidates). Preserve
the partial file and receipt, copy the partial bytes to the new directory, use
the received ETag with HTTP If-Range and `curl --continue-at -`, and require
the final bytes to match the declared content length and parse as a complete
PDF. A changed server entity, absent range support or another timeout stops
that candidate. The 25 MB file and 200 MB total limits remain. This is a bounded
transport repair justified by measured size/rate, not an unchanged blind retry.

The linked English report index also identifies distinct 2008–2010 English
editions. Retrieve those three exact links under the same measured 300-second
bound; keep Portuguese editions as comparison candidates, not substitutes.
This adds three candidates within the original twenty-file and 200 MB limits.

## Intake diagnostic after acquisition

The three English originals downloaded completely and their stated financial
pages match the introducing prospectus ranges. Rendered inspection shows that
2009 printed pages 173–174 (PDF 174–175) and 2008 pages 245–248 contain
substantive audit text as images while Poppler emits only headers/footers.
The 2010 audit opinion is machine-readable at printed/PDF 190; page 191 is
the Audit Committee report. Its free-English-translation qualification and
the corresponding Portuguese edition remain retained.

Run one source-intake diagnostic over the three originals using the existing
`source_graph.build` without editing the active method or source packet. The
baseline is their retained Poppler text and the rendered audit-page readings.
Require exact original bytes/page counts and a wrong-hash rejection. For the
six image-only audit pages, record whether required source phrases are absent
from the native units despite nonempty page text. This reproduces a coverage
gap; word counts alone never prove extraction completeness. Publication and
historical knowledge dates remain unestablished, so do not substitute the
reporting-period end or PDF creation metadata as legal document dates.

The diagnostic is CPU-only, bounded to 180 seconds, and retains per-page
extraction evidence. A successful source graph is engineering admission only;
no onward dependency or legal answer is promoted. If image content is omitted,
the next repair requires page-specific hybrid OCR and complete-critical-span
checks while preserving native text and provenance. Do not use image headers
as evidence that an entire page was read.
