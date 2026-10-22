# Compact serialization repair and verification

Attempt 055 failed because indented P1 JSON exceeded the existing 128 MiB
product limit. Its complete extracted P1 equalled the retained baseline;
compact serialization occupies 65,765,520 bytes. This is a local serialization
defect, not evidence that extraction or an external package failed.

Attempt 056 changes only the production product writer to lossless compact
UTF-8 JSON with flush, fsync and replacement. It preserves the size limit,
source inputs, recipe, semantic hashes and conditional profile pins. The
failed attempt and its evidence remain unchanged.

The inherited test selection omitted the unchanged preparation suite. This
omission was caught before the source trial and the suite was run explicitly;
its command, log, XML and passing result are retained under
stages/supplementary-preparation-tests. The primary suite also passed.

Installed execution regenerated all five complete products from the retained
PDF sources with exact semantic equality. The installed consumer then produced
the complete coverage-054 answer unchanged, with answer SHA-256
e87a95ae98fda4a8854fe9bb4db283231013d34fac213f36fa5bb28c1c1643a8.

These results establish this bounded source-to-answer regeneration and the
serialization repair. They do not establish correctness of every supplied
reading, interpretation of unseen prospectuses, or completion of the original
reference task or the general build. Continue substantive integration and
source gaps through reviewed refinements of their original tasks.
