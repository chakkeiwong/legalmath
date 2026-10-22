# Archive observation continuation

Follow the reviewed prospectus-archive-observation plan and unchanged original
budget. Read attempt001 and its complete Arquivo response. The matching metadata
is response_items[9] in arquivo-history-page2.body. The retained content has
8,125,384 bytes; the HTTP Content-Length agrees. The archive index contentLength
is a different stored size and must not be compared to decompressed content.

HTTP Date records 2026-10-12T18:14:55Z; use the retained archive-result creation
time 2026-10-12T18:16:29.625036Z as the supplied retrieval/provenance upper bound.
The header alone is server time, not proof of the exact local completion instant.
Require capture <= response date <= supplied retrieval time; require retrieval
<= query known_at before using the observation for that query. Retain the whole
time chain and this qualification. Baseline comparisons explicitly move known_at
to 2026-10-13 for current evidence, while keeping the original query as a control.

The adapter's file-size bounds (2 MiB metadata, 128 KiB headers, 32 MiB PDF) are
reviewed resource guards covering the retained 8.1 MiB case. Larger evidence stays
unsupported. They are not authentication rules. Support one successful final
HTTP response block, allowing preceding redirect/proxy blocks; duplicate critical
headers or duplicate matching archive records reject. No additional network calls.

Implementation clarification: the admitted plan said to validate Content-Length
when present. The finite implemented profile requires exactly one Content-Length
and validates it against retained PDF bytes; a missing length stays unsupported.
It also requires exactly one Content-Type, Date, Memento-Datetime and Link. This
narrows supported inputs without changing the recorded evidence contract or any
frozen method. Keep the admitted plan bytes unchanged and retain this clarification
with the attempt. A temporary wording edit to that plan was restored before
recording after checking its admission binding; no sealed evidence changed.

