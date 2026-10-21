from copy import deepcopy
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.phased import synthesis_catalog
from tests.assurance.test_synthesis_successor import fixture


def catalog(f):
    return {'profile':synthesis_catalog.PROFILE, 'input_hash':'source', 'phases':[f.pointer],
        'instruction_profile':None, 'first_level_instructions':False,
        'rows':{key:f.pointer for key in f.manifest['rows']}}


def test_catalog_preserves_full_key_census_and_blocks_new_keys_in_old_level(tmp_path):
    f = fixture(tmp_path)
    pointer = f.put('catalog.json', catalog(f))
    synthesis_catalog.load(tmp_path, pointer, 'source', provider_binding=f.dispatch.provider_binding)
    assert synthesis_catalog.selected(tmp_path, pointer, 'reduce-q-0-0', 'source') == f.pointer
    assert synthesis_catalog.selected(tmp_path, pointer, 'reduce-q-1-0', 'source') is None
    with pytest.raises(LegalMathError): synthesis_catalog.selected(tmp_path, pointer, 'reduce-q-0-99', 'source')
    assert not f.provider.calls


@pytest.mark.parametrize('change', ['missing', 'duplicate_phase', 'foreign_pointer', 'instructions', 'input'])
def test_catalog_rejects_incomplete_or_conflicting_history(tmp_path, change):
    f = fixture(tmp_path)
    value = deepcopy(catalog(f))
    if change == 'missing': value['rows'].pop('reduce-q-0-0')
    elif change == 'duplicate_phase': value['phases'].append(f.pointer)
    elif change == 'foreign_pointer': value['rows']['reduce-q-0-0'] = f.account
    elif change == 'instructions': value['instruction_profile'] = 'changed'
    else: value['input_hash'] = 'foreign'
    with pytest.raises(LegalMathError): synthesis_catalog.load(tmp_path, f.put('bad-catalog.json', value), 'source')
    assert not f.provider.calls
