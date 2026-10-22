"""Check attribution of supplied legal analysis through the ordinary consumer."""
from copy import deepcopy
import pytest

from legalmath.prospectus.successor import service
from scripts.prospectus_law_mode_evidence import verify
from test_calendar_facts import world as calendar_world, NOW
from test_ratio_facts import world as ratio_world


def assemble(p1, root, law_input=None):
    p2 = service.construction_product(p1, root)
    p3 = service.interpretation_product(p1, p2)
    return {'P1': p1, 'P2': p2, 'P3': p3, 'P4': service.law_product(p1, p3, law_input=law_input),
            'P5': service.financial_product(p1, p2, p3)}


@pytest.mark.parametrize('route', ['request', 'law_overlay'])
@pytest.mark.parametrize('kind', ['calendar', 'ratio', 'booleans', 'unknown'])
@pytest.mark.parametrize('mode', ['current', 'frozen'])
def test_supplied_legal_models_report_assistance(tmp_path, route, kind, mode):
    products, data, _ = ratio_world(tmp_path) if kind == 'ratio' else calendar_world(tmp_path)
    if kind in {'booleans', 'unknown'}:
        row = data.pop('calendar_facts')[0]
        if kind == 'booleans':
            data['facts'] = [{'name': row['name'], 'basis_id': row['basis_id'], 'value': True,
                'instrument_id': row['instrument_id'], 'jurisdiction': row['jurisdiction'],
                'source': row['source'], 'valid_from': NOW, 'known_from': NOW, 'observed_at': NOW}]
    if route == 'request':
        request = {**deepcopy(products['P1']['payload']['request']), **data}
        p1 = service.source_product(request, tmp_path)
        result = assemble(p1, tmp_path)
    else:
        result = assemble(products['P1'], tmp_path, data)
    output = service.consume(result, tmp_path, mode=mode)
    assert output['mode'] == 'ASSISTED'
    assert output['independent_legal_acceptance'] is False and output['may_execute_transaction'] is False
    if kind == 'unknown':
        assert output['questions']['Q4']['status'] == 'UNKNOWN'


@pytest.mark.parametrize('overlay', [None, {'law_bases': [], 'facts': []},
                                    {'law_bases': [], 'facts': [], 'ratio_facts': [], 'calendar_facts': []}])
@pytest.mark.parametrize('mode', ['current', 'frozen'])
def test_empty_legal_inputs_do_not_imply_assistance(tmp_path, overlay, mode):
    products, _, _ = calendar_world(tmp_path)
    result = assemble(products['P1'], tmp_path, overlay)
    assert service.consume(result, tmp_path, mode=mode)['mode'] == 'AUTOMATIC_BOUNDED'


@pytest.mark.parametrize('mode', ['current', 'frozen'])
def test_explicit_empty_overrides_clear_unused_top_level_legal_model(tmp_path, mode):
    products, data, _ = calendar_world(tmp_path)
    request = {**deepcopy(products['P1']['payload']['request']), **data}
    p1 = service.source_product(request, tmp_path)
    overlay = {'law_bases': [], 'facts': [], 'ratio_facts': [], 'calendar_facts': []}
    result = assemble(p1, tmp_path, overlay)
    output = service.consume(result, tmp_path, mode=mode)
    assert output['mode'] == 'AUTOMATIC_BOUNDED'
    assert output['questions']['Q4']['status'] == 'UNKNOWN'


@pytest.mark.parametrize('attack', ['question', 'products', 'permission', 'digest', 'mode'])
def test_exact_mode_projection_does_not_hide_other_changes(tmp_path, attack):
    products, data, _ = calendar_world(tmp_path)
    original = service.consume(assemble(products['P1'], tmp_path, data), tmp_path, mode='current')
    # A historical AUTOMATIC label with its correct historical digest.
    original['mode'] = 'AUTOMATIC_BOUNDED'
    original['report_sha256'] = service.digest({k: v for k, v in original.items() if k != 'report_sha256'})
    actual = deepcopy(original)
    actual['mode'] = 'ASSISTED'
    if attack == 'question':
        actual['questions']['Q4']['status'] = 'NO'
    elif attack == 'products':
        actual['consumed_products']['P4'] = '0' * 64
    elif attack == 'permission':
        actual['may_execute_transaction'] = True
    elif attack == 'mode':
        actual['mode'] = 'AUTOMATIC_BOUNDED'
    actual['report_sha256'] = service.digest({k: v for k, v in actual.items() if k != 'report_sha256'})
    if attack == 'digest':
        actual['report_sha256'] = original['report_sha256']
    with pytest.raises(ValueError, match='beyond exact reviewed'):
        verify(actual, original, assisted=True)
