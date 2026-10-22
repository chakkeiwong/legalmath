"""Heading labels must not consume ordinary parenthetical prose."""
import pytest
from legalmath.prospectus.successor import reference_addresses as module

@pytest.mark.parametrize('text',['(etwaiger) bis zum Tage','(including) accrued interest',
    '(der) Emittentin','[optional] condition','[(optional)] condition'])
def test_parenthetical_words_are_not_labels(text):
    assert module.LABEL.match(text) is None

@pytest.mark.parametrize('text',['(1) Heading','[(10)] Heading','[4] Heading',
    '(a) Heading','(ii) Heading','(iv) Heading'])
def test_declared_label_forms_remain_candidates(text):
    assert module.LABEL.match(text) is not None

@pytest.mark.parametrize('text,label',[('(z) Unknown','z'),('(xxi) Unknown','xxi'),('(1000) Unknown','1000')])
def test_unsupported_label_like_tokens_still_refuse(text,label):
    assert module.LABEL.match(text) is not None
    with pytest.raises(ValueError):module.level(label)
