from legalmath.interpretation.semantics.precedent import parse_citation

def test_known_generic_and_unparsed_hong_kong_forms_are_explicit():
    parsed=parse_citation("[2020] UKSC 1")
    assert parsed.parsed and parsed.year=="2020"
    unknown=parse_citation("HCMP 123/2020")
    assert not unknown.parsed and unknown.reason
