import pytest
from legalmath.events.calendar import anniversary, end_of_local_date
from legalmath.errors import LegalMathError


def test_explicit_leap_and_hong_kong_cutoff():
    assert anniversary("2024-02-29", 1, "feb28") == "2025-02-28"
    assert anniversary("2024-02-29", 1, "mar1") == "2025-03-01"
    with pytest.raises(LegalMathError): anniversary("2024-02-29", 1, "reject")
    assert end_of_local_date("2026-09-01") == "2026-09-01T16:00:00.000000Z"
