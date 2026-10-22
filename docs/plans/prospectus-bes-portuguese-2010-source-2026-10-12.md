# BES 2010 Portuguese source acquisition and conditional comparison

## Question and comparator

Can the exact Portuguese 2010 report linked in the retained issuer archive be
acquired and its sustainability-assurance section matched to the English
report? The baseline is the English original SHA
`f6c1196ffcbaed34dc4068b4fbc095b4494e421e224977bfa54b215134e32f25`, PDF pages
88–89, and the retained reviewed wording that the Portuguese version prevails
in doubt or misinterpretation. The exact archive link is retained in
`bes-original-acquisition/attempt-001/routes.json`:
`https://www.bes.pt/RelatorioseContas/2010_Relatorio_Consolidado.pdf`.

## Evidence contract and defaults

Acquisition passes only with successful HTTP retrieval, actual PDF bytes,
retained response headers/final URL/status, SHA-256, page count and extraction
diagnostics. A matching filename or visible year is not independent issuer,
edition or historical-publication authentication. PDF metadata and today's
retrieval timestamp must not be promoted to a 2011 public-availability date.

For comparison, locate the Portuguese section by its wording and context,
never by assuming that it shares English page numbers. Inspect the actual
source images before freezing critical language, including assurance level,
subject, criteria, addressee and third-party reliance. Native/OCR counts are
navigation aids only. A text match can support a conditional comparison; it
does not certify translation or a legal right to rely on the report.

The one URL comes from an already retained issuer-archive link, not a guessed
path. Curl follows HTTPS redirects only. Use a 15-second connection bound and
a 120-second total transfer bound, return a session ID promptly, retain partial
downloads/failures and allow at most one transfer retry after diagnosing the
first failure. Never treat HTTP error HTML as a PDF. CPU-only parser; GPU is
hidden. No new packages or runtime/default changes.

## Dependencies and stop conditions

1. Acquire to a new attempt directory with start record and binding to the
   retained archive route. This is independent of the running controller R4.
2. Validate PDF and locate candidate assurance pages; depends on successful
   acquisition. Retain page-labeled native text and metadata locally, small
   summaries only in tool output. If image-only, record that fact and use a
   bounded source-specific OCR plan before interpretation.
3. Inspect only candidate page/crop images and record a conditional comparison;
   requires valid source identity and legible evidence. Missing critical
   wording blocks claims about translation agreement, not other ready work.
4. Refresh source-evidence status with success or exact failure. Keep the
   fourteen dependencies and overall legal acceptance unchanged unless their
   separate admission requirements are actually satisfied.

Audit PASS for a bounded acquisition and inspection: exact baseline and link,
no page-number or authenticity assumption, finite transfer bound, explicit
continuation dependencies and no default promotion. Malformed or changed
shared baseline evidence vetoes this branch. A remote failure does not stop
the independent engineering checks. Retain artifacts under
`bes-original-acquisition/portuguese-2010/acquisition-001/`.
