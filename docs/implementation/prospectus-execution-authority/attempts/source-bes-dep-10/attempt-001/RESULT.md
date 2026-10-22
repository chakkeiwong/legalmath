# BES Finance 2010: archive issuer mismatch rejected

The retained regulator profile and financial-filings menu identify BES Finance
Ltd. The menu's annual-accounts link uses issuer parameter
`%25%22TWU%21%3D%40%20%0A`. Its archived replay redirects to a different
parameter, `%24%21%24K%5B%23%20%20%20%0A`, at capture `20090925075938`.
The returned annual index identifies **Portugal Telecom, SGPS, SA** and links
that company's 2008 Form 20-F. It is the wrong issuer and period. Those linked
PDFs were not downloaded or admitted as the BES Finance accounts.

This resumes the existing attempt after interruption. Four metadata responses
and three content responses were already retained. The refinement permits one
further content response, but the returned index provides no matching original
to retrieve. Repeating the request or downloading a known wrong issuer would
not advance the question. The exact redirect, link and retained response hashes
are in `retrieval-mismatch.json`. Missing request timings are left unknown.

The target remains the separate audited BES Finance statements for 2010/2009
named on page 3 of the 6 June 2011 supplement: income p2, balance p4, cash flow
p6, notes pp7–50 and audit pp51–52. A Bank consolidated report, prospectus or
issuer profile does not satisfy that requirement. The next distinct retrieval
route is exact-URL archive enumeration with the correct issuer parameter, or
the original Luxembourg exchange filing. No absence-from-the-internet claim
follows from this bounded search.

`reuse-result.json` checks the existing sealed actual consumer and current
source/method hashes. BES-DEP-10 remains unresolved in P3, Q1 and Q2. This is
verified reuse; no new source or final consumer invocation occurred. The task
is not complete and no legal acceptance is established.

| Decision | Primary criterion | Veto | Main uncertainty | Next justified action | Not concluded |
|---|---|---|---|---|---|
| Reject the annual index as the requested accounts | Exact original not recovered | Actual issuer and period mismatch | Coverage of the original filing in other archives | Record this result, refresh and continue BES-DEP-11; retain the exact discovery route | Source nonexistence, engine failure, package limitation or legal completion |

The failure is a retrieval mismatch, not evidence against the engine or a
fundamental package limitation. Archive URL normalization or fallback is a
possible explanation, but has not been traced to its implementation. Exact
issuer/period/page-matching original bytes would change the source finding.
This branch's missing source does not block independent authorized work.
