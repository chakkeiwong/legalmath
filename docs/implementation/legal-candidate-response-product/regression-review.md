# Regression failure review

The first broader run passed 352 tests and failed
`test_incomplete_investigation_is_retained_as_incomplete`. This is a stale
fixture: it supplied `maximum_scoped_actions=1` to a stage requiring both
perspectives and expected an incomplete dossier. The checkpoint implementation
already rejects insufficient full-coverage capacity at `SCOPED_ADMISSION`, before
question/scoped dispatch. The new response option did not add that admission
check. Existing integration-repair tests explicitly require it.

Preserve the admission policy and the incomplete-observation assertion. Change
the fixture to supply adequate capacity, return a valid first perspective and a
rejected second perspective, and stop after its one configured round. The
observation must retain the missing perspective and count the dossier as
incomplete. This tests an actual reachable incomplete execution without weakening
the budget check or manufacturing a dossier.

The skeptical audit passes for this fixture repair: the baseline admission check
is unchanged; the full observation verifier remains active; assertions still
require pending scoped pairs, one incomplete observation, zero complete
observations and an unchanged task denominator. Rerun this test first, then the
same broader suite. Product source did not change, so the successful 984-check
replay remains applicable and does not need another run.
