# Senior and junior bond comparison prospectuses

Four final prospectus PDFs are preserved here: 201 pages covering eight issued
bond series. The implemented classifier returned `non loss absorption` for all
eight under its qualified offering-document analysis. The
[executed report](../../implementation/bond-loss-absorption-classification/results.md)
gives the generated reason and source page for each series. Absence of a keyword
is not treated as proof that a feature is absent.

| Issuer and issue | Rank | Retained prospectus | Source |
| --- | --- | --- | --- |
| Apple: 4.000% 2028, 4.200% 2030, 4.500% 2032, 4.750% 2035 | Senior unsecured | [5 May 2025 supplement and base prospectus, 54 pages](originals/apple-senior-2025.pdf) | [Filing PDF](https://d18rn0p25nwr6d.cloudfront.net/CIK-0000320193/d9065b65-eeb8-439b-97fc-be1d38ce0d2e.pdf) |
| Duke Energy: 5.45% 2034 and 5.80% 2054 | Senior | [5 June 2024 supplement and base prospectus, 49 pages](originals/duke-senior-2024.pdf) | [Filing PDF](https://d18rn0p25nwr6d.cloudfront.net/CIK-0001326160/21faa7ae-4c58-40e0-9928-d7e573d1d2f5.pdf) |
| Southern Company: Series 2025A 6.50%, due 15 March 2085 | Junior subordinated | [8 January 2025 supplement and base prospectus, 40 pages](originals/southern-junior-2025a.pdf) | [Filing PDF](https://d18rn0p25nwr6d.cloudfront.net/CIK-0000092122/2ae8f159-818e-4e94-a3e5-1714a0375503.pdf) |
| Duke Energy: 6.45% fixed-to-fixed reset, due 1 September 2054 | Junior subordinated | [19 August 2024 supplement and base prospectus, 58 pages](originals/duke-junior-2024.pdf) | [Filing PDF](https://d18rn0p25nwr6d.cloudfront.net/CIK-0001326160/36bfc95c-f014-45bb-91c5-32d0eec52bb2.pdf) |

The junior issues are useful because they expressly permit interest deferral;
that alone does not meet the user's principal-write-down or compulsory-common-
share-conversion definition. The Duke base prospectus also describes other
security types, providing a concrete instrument-scope challenge. These are
reasons to examine the sources, not preassigned legal-quality labels.

[manifest.json](manifest.json) records URLs, retrieval dates, filing accessions,
downloaded-byte hashes, headers, extraction hashes and provisional issue rows.
The original download representation is a filing PDF copy from the
investor-relations filing CDN. The page text is a PyMuPDF derivative; it is not
an authenticated replacement for the original filing. Final/preliminary cover
checks and nonempty extraction passed for every PDF. Incorporated-document
completeness, exact issue identifiers and legal interpretation remain pending.

The [reviewed implementation plan](../../plans/bond-loss-absorption-classification.md)
and [execution record](../../implementation/bond-loss-absorption-classification/RESET.md)
cover retained CoCos, exclude preferred-share securities, and preserve the
comparison bonds' generated labels, reasons and evidence qualifications.
