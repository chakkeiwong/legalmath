# Run-001: failed test oracle

The new notice-preservation assertion expected `Der Rückzahlungstag`; the
original base p120 line 62 and unchanged comparator both say `(iii) den
Rückzahlungstag`. The other 39 checks passed. This is a local test-oracle error,
not a construction or package failure. Repair the assertion to the exact source
wording and rerun; preserve the failed log, XML and manifest unchanged. The
source/comparator are valid, so no continuation veto fired.
