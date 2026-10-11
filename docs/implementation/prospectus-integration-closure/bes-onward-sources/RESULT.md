# BES onward-source disposition and applicability consumer

The revised bounded phase passed on 11 October 2026 with:

```text
timeout 1200 .venv/bin/python docs/implementation/prospectus-integration-closure/bes-onward-sources/consumer.py
```

The run is retained in `attempt-002/` and completed in roughly three minutes
in CPU mode. It consumed the same eight retained BES documents as the protected
source-chain comparator, preserved all 18,036 source units and seven earlier
source-chain edges, and kept Q1/Q2/Q3/Q4/Q5/Q6 at `UNKNOWN`, `UNKNOWN`,
`PARTIAL`, `UNKNOWN`, `UNSUPPORTED`, `UNKNOWN`.

The revised search indexed 255 retained files across the four declared roots,
decoded text, JSON, HTML and printable binary responses, recorded 36 files that
could not be searched, and preserved every file hash and nearest source
manifest metadata. It found content or metadata leads for all 14 dependencies
(9–103 leads for the financial records and seven leads for each agency
instrument). Those leads are explicitly marked
`TEXT_OR_METADATA_LEADS_ONLY_NO_AUTHENTICATED_ORIGINAL_BOUND`; they are not
accepted as the missing originals. Every financial introducer PDF/text hash,
page and quote was revalidated. The 11 financial records and three agency
agreements therefore remain `UNRESOLVED` pending acquisition and
authentication of separate original bytes.

The applicability review now carries complete retained paragraphs rather than
isolated line fragments. It keeps four categories separate: named agency
instruments and precedence; Portuguese law, conflicts and forum; Interbolsa
book-entry and Common Representative language; and generic ICSD
common-safekeeper language. The full paragraphs are source evidence only. They
do not supply the absent executed agreements, independent legal advice, an
actual holding chain or Eurosystem eligibility.

| Decision | Primary evidence | Veto status | Consequence |
|---|---|---|---|
| Retained corpus search | 255 hashed files, content/metadata leads, 36 unsearched files recorded | PASS with bounded scope | Search leads remain unreviewed acquisition leads |
| Introducer integrity | All 11 historical introducer source/text hashes and quotes validate | PASS | Dependency identity remains bound to the cited source |
| Paragraph applicability | Four complete category-separated paragraph packets | PASS | Conditional source applicability may be consumed |
| Omission integrity | Four matched omissions expose both Q1/Q2 dependencies | PASS | An edge cannot resolve without its representative content |
| Edition/date integrity | Wrong-edition and changed-date graph controls reject | PASS | Exact source identity remains required |
| Legal/source completion | Authenticated originals, independent acceptance, collateral eligibility | NOT_ESTABLISHED | Keep all 14 onward records unresolved |

The first package was preserved as `attempt-001/`. Its filename-only search and
single-line applicability anchors were insufficient for the broader absence
claim. The revised plan records that audit and the bounded repair. The initial
attempt is retained as a diagnostic; it is not an additional independent
observation. No package or PDF-extractor unsuitability follows from its local
request-schema failure or from the revision.

The next phase is acquisition and authentication of the 14 originals, followed
by a frozen source-complete consumer and independent qualified legal readings.
Native dependency confinement, second-host portability and broader scan-family
coverage remain separate engineering work.
