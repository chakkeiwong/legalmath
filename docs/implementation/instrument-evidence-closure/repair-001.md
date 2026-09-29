# Development repair: importlib collection

The first focused diagnostic failed during collection: the repository uses
pytest's importlib mode, so a sibling test module was not available as a
top-level import. Use its package-qualified name. No contract calculation ran
and this failure supplies no evidence about the candidate's arithmetic.
The original JUnit result is retained in `development-tests-001.xml`.
