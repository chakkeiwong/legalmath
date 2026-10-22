# Initial focused test review

finance-tests-001.xml retains 117 passes and one assertion failure. The invalid
legacy input correctly returned UNSUPPORTED with "Unexpected or missing fields";
the test incorrectly expected "Unknown fields". Corrected the expected diagnostic
without changing rejection behavior. Added actual direct/selected short-first
coupon controls before freezing the source comparison. No source trial or protected
target was used to tune these tests. The initial failure remains retained.
