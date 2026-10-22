import pytest

from scripts.prospectus_margin_receipt_repair import successful_scope_receipt


@pytest.mark.parametrize('scope', ['COMPLETE_REVIEWED_SCOPE', 'PARTIAL', 'UNREVIEWED'])
def test_successful_check_preserves_both_worker_and_scope_status(scope):
    source = {'status': scope, 'groups': 54}
    actual = successful_scope_receipt(source)
    assert actual == {'status': 'PASS', 'scope_status': scope, 'groups': 54}
    assert source == {'status': scope, 'groups': 54}


@pytest.mark.parametrize('status', ['FAIL', 'PASS', None, False, 0])
def test_unknown_or_failed_check_cannot_be_normalized_to_success(status):
    with pytest.raises(ValueError, match='cannot become PASS'):
        successful_scope_receipt({'status': status})
