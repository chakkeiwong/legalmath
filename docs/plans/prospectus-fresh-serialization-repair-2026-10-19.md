# Repair fresh product serialization and finish regeneration

Attempt055's installed source command really extracted four original PDFs and
produced exactly the baseline P1. Its indented JSON occupied139068110bytes,
exceeding the128MiBcap. The same product occupies65765520bytes compactly. The
cap was based on compact measured products, while the candidate used the existing
indented writer. This is a reproduced local implementation mismatch.

Skeptical audit PASS for changing only product serialization: use compact UTF-8
JSON in a temporary file, flush/fsync it and replace the new product path.
Retain the128MiBcap, every semantic hash, all parent checks, the original recipe
and source files. Add a regression whose product fits the compact cap but fails
when indented. Keep the entire failed055attempt unchanged and recorded REJECT.
No retry of that frozen stage is authorized. New attempt056 reruns the changed
installed candidate and completes the already reviewed source-to-answer test.

The scientific/engineering question, comparator, primary criteria and vetoes
remain those in prospectus-fresh-preparation-2026-10-19.md. A compact file alone
does not pass: every installed P1-P5 must equal the earlier complete products,
and their actual conditional answer must equal coverage054 with unchanged pins.
Small tests, counts and package file equality are supplementary checks.

Retain all measured costs, failed139MBfile and unknown manual time. Forecast
at most1100new measured seconds and300MiB;keep cumulative02612600seconds and
2048MiBincluding4MiBreserve. Admission55 becomes56 through reviewed revision.
Stage210seconds,child195seconds,one-second yields,poll existing sessions.
No external calls or new host permissions. Any further failure must be explained
from retained evidence; an unchanged retry is never a repair.

This rejects a serializer candidate,not source extraction,an external package
or the direction of staged preparation. Remaining source/legal completeness,
historical editions,new-source profile preparation and whole-build acceptance
remain separate and unproved even after successful regeneration.
