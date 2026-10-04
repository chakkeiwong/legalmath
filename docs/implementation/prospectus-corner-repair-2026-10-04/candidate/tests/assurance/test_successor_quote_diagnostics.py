from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.semantics import check_quotes


@pytest.mark.parametrize('quote,unit,expected',[
    ('8 July 2027','u',0),('8 July\x00a02027','u',0),
    ('repeat','u',2),('8 July\u00a02027','missing',0)])
def test_rejected_quote_remains_rejected_with_actionable_evidence(quote,unit,expected):
    source='Deadline 8 July\u00a02027; repeat repeat.'
    packet={'units':[{'unit_id':'u','text':source}]}
    assert source.count(quote)!=1 or unit!='u'
    with pytest.raises(LegalMathError) as e:check_quotes([{'unit_id':unit,'quote':quote}],packet)
    d=e.value.details
    assert e.value.code=='E_REFERENCE' and d['unit_id']==unit and d['occurrences']==expected
    assert d['quote']==quote and not d['quote_truncated']
    assert d['unit_present']==(unit=='u')
    if unit=='u':
        assert d['source_unit']==source
        assert {'offset':15,'codepoint':'U+00A0'} in d['source_special_characters']
    if '\x00' in quote:assert any(c['codepoint']=='U+0000' for c in d['quote_special_characters'])


def test_exact_quote_still_passes_without_mutation():
    packet={'units':[{'unit_id':'u','text':'8 July\u00a02027'}]}
    q={'unit_id':'u','quote':'8 July\u00a02027'}
    assert check_quotes([q],packet) is None
    assert q['quote']==packet['units'][0]['text']


def test_diagnostic_size_is_bounded_and_truncation_is_visible():
    packet={'units':[{'unit_id':'u','text':'\u00a0'*5000}]}
    with pytest.raises(LegalMathError) as e:check_quotes([{'unit_id':'u','quote':' '*5000}],packet)
    d=e.value.details
    assert len(d['quote'])==len(d['source_unit'])==2048
    assert d['quote_truncated'] and d['source_unit_truncated']
    assert len(d['source_special_characters'])==32
