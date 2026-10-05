# Integration verification — 5 October 2026

Integration passed at `f3ff411365e2345be6038b35de086be172fff80d`.
That merge contains campaign commit
`0423f3bffb70ca2846c014f4dd04fb3dee7a8291` and the pre-existing main commit
`00c1b4bb8b63464050f0265de4cdf1e253d43d30`. Git resolved the merge without
conflicts. A subsequent fetch and merge of origin/main reported that the fetched
main history was already included.

A fresh detached checkout of the integrated commit passed all 186 focused
OCR/refresh/BASF tests, with zero failures, errors or skips. Import-location
checks confirmed that both legalmath and the BASF runner loaded from that
checkout. GPU devices were intentionally hidden. The checkout was clean before
and after validation.

The BASF status reported BOUNDED_PHASES_VERIFIED. The preceding refresh status
reported PASS, with no remaining executable phase in that bounded round.
Both retained their explicit prohibition on production promotion.

| Check | Result |
| --- | --- |
| Complete staged campaign | 2,924 paths; 9,558 required evidence paths present in the index |
| Hidden evidence | 191 ignored logs and support files included; three unbound runtime locks excluded |
| Large files | Largest campaign file 4,113,088 bytes; no file reached the 100 MiB Git-host threshold |
| Merged implementation | 186 tests pass; source and receipt status checks pass in a clean checkout |
| Unrelated main work | All 37,729 pre-existing dirty files retain their exact contents, modes and symlink identities |
| Conflicts and staged unrelated work | No merge conflicts; no unrelated files staged |

The [machine result](integration/verification.json),
[test log](integration/tests.log), [JUnit report](integration/integration-tests.xml),
[BASF status](integration/basf-status.log),
[refresh status](integration/refresh-status.log) and
[preservation result](integration/main-preserved.json) retain the evidence.

These results apply to the integrated source commit above. The subsequent
delivery commit adds only these records and the summary link. Final publication
is checked with normal pushes and local/remote branch-head comparison, as
specified in the [delivery plan](../../plans/prospectus-delivery-2026-10-05.md).
