# Historical source recovery review, 2026-10-04

This note describes requests 008-012 before the additional authorisation. Its
12-request ceiling and missing-PDF statements are historical. The user subsequently
authorised 100 additional requests. See recovery-round-2026-10-04.md and
recovery-identity-review-2026-10-04.json for the current recovery evidence.

This note records origin/route observations. It does not admit a governing
edition or close a contractual dependency.

| Request | Observation | Consequence |
| --- | --- | --- |
| 008 BASF programme archive candidate | HTTP 404; response and headers retained. No source-linked archive route was found in the response. | The 9 September 2022 base, 27 February 2023 supplement and selected German Option I remain missing. Do not repeat this guessed route. |
| 009 SEB funding-programmes | HTTP 301 with Location /investor-relations/debt-investors/funding-programs. | Follow the exact same-host redirect as a separately counted request. |
| 010 SEB funding-programs | HTTP 200. Programme directory lists a 2024 programme, Q2/Q3 supplements and an archive link. | Retain the page as route evidence. Its current fiscal-agency links name 2026, 2025 and 2021 editions, which cannot substitute for the 2023 agreement named in the AT1 terms. |

The retained SEB AT1 information memorandum, source hash
`76f510479585e1015d61d35c9cfc5d451a35f47f62c0bfce5d3e8d10de2df364`,
identifies these exact dependencies:

- Amended and restated fiscal agency agreement dated 6 July 2023.
- Supplemental fiscal agency agreements dated 14 June 2024, 25 October 2024
  and 4 November 2024.
- Programme information memorandum dated 14 June 2024, supplemented on
  22 July 2024 and 25 October 2024, for the specified incorporated sections.

The terms state that they prevail on inconsistency with the fiscal agency
agreement, and that copies are available for inspection at the paying and
conversion agents' offices. That availability statement is not proof that an
executed copy or its complete amendment chain has been inspected here.

Request 011 returned the archive page (HTTP 200); it showed older programme
material but no 2023 fiscal-agency link in the inspected page. Request 012
returned HTTP 200 with a 3,165-byte HTML download landing page, not PDF bytes.
Its source-linked PDF route is retained in proposed-next-request.json. The
cumulative budget is now 12/12. No exact missing contract or programme PDF has
been newly admitted, and no additional request has been dispatched.

The exact programme-archive href from request 010 was followed and retained.
The current total ceiling remains 12; no increase has been approved. New
documents observed on 4 October after 00:00 UTC cannot retrospectively support
the existing assessment's 00:00 UTC knowledge cutoff.

IC-1 V.3 is registered in the new bank store using the actual retained receipt
time, 2026-10-03T11:09:32.100844+00:00. Its force interval, freshness, related
circulars and date-specific applicability remain unresolved. Registration is
an engineering result, not a current-law finding.
