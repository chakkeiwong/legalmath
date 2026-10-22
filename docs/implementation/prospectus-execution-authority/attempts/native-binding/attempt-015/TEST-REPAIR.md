# Correct the shared test-fixture import

The first suite stopped in collection with ModuleNotFoundError for
test_native_current_preparation. This repository has tests/__init__.py and
tests/prospectus/__init__.py. The new test imported a bare module name instead
of tests.prospectus.test_native_current_preparation. No source rehearsal or
native execution occurred; the actual exit code2, report, log and methods are
preserved in validation/run-001.

The one permitted repair changes that import to the repository package path.
No production behavior or comparator changes. Run the second/final suite on
the corrected test file before freezing methods.
