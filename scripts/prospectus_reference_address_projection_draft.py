"""Create an unevaluated projection repair while retaining the failed candidate."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
PREP = AUTH / 'reviews/reference-address-projection-346'
OLD = AUTH / 'reviews/reference-addresses-345'
(PREP / 'candidate').mkdir(parents=True, exist_ok=True)
candidate = PREP / 'candidate/reference_addresses.py'
assert not candidate.exists()
body = (OLD / 'candidate/reference_addresses.py').read_text()
marker = '\ndef source_model(products, ordinary):'
addition = '''
def body_projection(text, pieces, raw_units, operations, start, end):
    result, cursor = [], start
    for index, piece in enumerate(pieces):
        left, right = max(start, piece['start']), min(end, piece['end'])
        if left >= right:
            continue
        require(left == cursor, 'Paragraph body has a source gap or overlap')
        if piece['kind'] != 'SUPPLIED_OR_TRANSFORMED':
            result.extend(projection(text, pieces, raw_units, left, right))
        else:
            require(piece.get('raw_binding') is None and piece.get('operation') == 'SUBSTITUTE'
                    and piece['text'] == text[piece['start']:piece['end']],
                    'Transformed paragraph text has an invalid source classification')
            replaced = piece.get('replaced_raw_interval')
            basis = piece.get('basis')
            require(isinstance(replaced, dict) and isinstance(basis, dict) and basis,
                    'Transformed paragraph text lacks its retained basis')
            matches = [operation for operation in operations
                       if operation.get('start') == replaced.get('start')
                       and operation.get('end') == replaced.get('end')
                       and operation.get('old') == replaced.get('quote')
                       and operation.get('new') == piece['text']
                       and operation.get('basis') == basis]
            require(len(matches) == 1, 'Paragraph transformation differs from current construction')
            result.append({'piece_index': index, 'selected_start': left, 'selected_end': right,
                'text': text[left:right], 'kind': piece['kind'], 'source': None,
                'transformation': {'operation': deepcopy(matches[0]), 'basis': deepcopy(basis),
                    'replaced_raw_interval': deepcopy(replaced),
                    'piece_start': piece['start'], 'piece_end': piece['end'],
                    'raw_quotation_established': False}})
        cursor = right
    require(cursor == end, 'Paragraph body projection incomplete')
    return result

'''
assert body.count(marker) == 1
body = body.replace(marker, addition + marker)
old_line = "node['source_projection'] = projection(text, pieces, raw, node['start'], end)"
assert body.count(old_line) == 1
body = body.replace(old_line, "node['source_projection'] = body_projection(text, pieces, raw, assembly['operations'], node['start'], end)")
ast.parse(body)
candidate.write_text(body)

oracle_path = ROOT / 'scripts/prospectus_reference_address_projection_oracle.py'
assert not oracle_path.exists()
oracle = (ROOT / 'scripts/prospectus_reference_addresses_oracle.py').read_text()
oracle = oracle.replace('def verify_projection(projected, start, end, text, pieces, raw):',
    'def verify_projection(projected, start, end, text, pieces, raw, operations=()):')
needle = "        source = piece.get('raw_binding')\n"
replacement = '''        if piece['kind'] == 'SUPPLIED_OR_TRANSFORMED':
            assert piece['raw_binding'] is None and piece['operation'] == 'SUBSTITUTE'
            assert piece['text'] == text[piece['start']:piece['end']]
            prior = piece['replaced_raw_interval']
            candidates = []
            for operation in operations:
                if (operation['start'], operation['end'], operation['old'], operation['new'], operation['basis']) == (
                        prior['start'], prior['end'], prior['quote'], piece['text'], piece['basis']):
                    candidates.append(operation)
            assert len(candidates) == 1
            expected.append({'piece_index': index, 'selected_start': a, 'selected_end': b,
                'text': text[a:b], 'kind': piece['kind'], 'source': None,
                'transformation': {'operation': candidates[0], 'basis': piece['basis'],
                    'replaced_raw_interval': prior, 'piece_start': piece['start'],
                    'piece_end': piece['end'], 'raw_quotation_established': False}})
            cursor = b
            continue
        source = piece.get('raw_binding')
'''
assert oracle.count(needle) == 1
oracle = oracle.replace(needle, replacement)
old_line = "verify_projection(target['source_projection'], target['start'], target['end'], text, pieces, raw)"
assert oracle.count(old_line) == 1
oracle = oracle.replace(old_line, old_line[:-1] + ", assembly['operations'])")
ast.parse(oracle)
oracle_path.write_text(oracle)

test_path = ROOT / 'tests/prospectus_successor/test_reference_address_projection.py'
assert not test_path.exists()
tests = (ROOT / 'tests/prospectus_successor/test_reference_addresses.py').read_text()
tests = tests.replace('reviews/reference-addresses-345', 'reviews/reference-address-projection-346')
tests = tests.replace('from scripts.prospectus_reference_addresses_oracle import verify',
                      'from scripts.prospectus_reference_address_projection_oracle import verify')
tests += '''

@pytest.mark.parametrize('kind', ['operation-missing', 'basis-changed', 'text-changed', 'raw-invented'])
def test_transformation_provenance_cannot_be_dropped_or_fabricated(kind):
    products, old = source_case()
    changed, altered = deepcopy(products), deepcopy(old)
    pieces = altered['definition_sources']['source_pieces']
    piece = next(p for p in pieces if p['start'] == 6596)
    operations = changed['P2']['payload']['assembly']['operations']
    if kind == 'operation-missing':
        operations[:] = [o for o in operations if o['start'] != piece['replaced_raw_interval']['start']]
    elif kind == 'basis-changed':
        piece['basis']['quote'] = 'invented date source'
    elif kind == 'text-changed':
        piece['text'] = 'invented date'
    else:
        piece['raw_binding'] = dict(piece['basis'])
    with pytest.raises(ValueError):
        module.body_projection(changed['P2']['payload']['assembly']['continuous_text'], pieces,
            {u['id']: u for u in changed['P1']['payload']['graph']['units']}, operations, 6470, 6871)


def test_coupon_container_preserves_transformation_separately_from_quote():
    nodes, _ = index_case()
    node = next(n for n in nodes if n['section'] == '3' and n['path'] == ['1'])
    row = next(p for p in node['source_projection'] if p['selected_start'] == 6596)
    assert row['text'] == '8. März 2023' and row['source'] is None
    assert row['transformation']['basis']['unit'] == 'basf-2032-final:p4:l58'
    assert row['transformation']['raw_quotation_established'] is False
'''
ast.parse(tests)
test_path.write_text(tests)
print('Created unevaluated body projection repair, successor oracle and tests; original methods retained')
