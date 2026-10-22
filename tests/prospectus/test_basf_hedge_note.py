"""Footnoted unknowns and genuinely unprinted mixed-table positions."""
import pytest
from legalmath.prospectus.basf_hedge_note import numeric,text_cell


@pytest.mark.parametrize('literal,marker,value',[('107 a','a',107),('–111 a','a',-111),
    ('– a','a',None),('–',None,None),('0',None,0),('–458',None,-458)])
def test_footnote_can_qualify_an_unknown_without_imputation(literal,marker,value):
    result=numeric(literal,marker)
    assert result['integer_millions']==value
    assert result['literal']==literal
    assert result['footnote_marker']==marker


@pytest.mark.parametrize('literal,marker',[('107','a'),('– a',None),('107 b','a'),('1,20',None),('n/a',None)])
def test_changed_qualifications_and_text_are_not_parsed_as_money(literal,marker):
    with pytest.raises(ValueError):
        numeric(literal,marker)


def test_unprinted_not_applicable_and_dash_are_three_distinct_states():
    blank=text_cell([],blank_allowed=True)
    na=text_cell([{'quote':'n/a'}])
    dash=numeric('–')
    assert len({blank['status'],na['status'],dash['status']})==3
    assert blank['literal'] is None
    assert all(x['integer_millions'] is None for x in [blank,na,dash])


def test_a_missing_nonblank_caption_is_refused():
    with pytest.raises(ValueError):
        text_cell([])
