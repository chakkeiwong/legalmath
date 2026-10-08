from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
from closure_references import snapshot
from .support import reading
from tests.search.test_formal import AT


def test_reference_binding_preserves_unknown_and_requires_full_explicit_vocabulary():
    model = reading()
    values = {f['name']: None for f in model['formalization']['facts']}
    binding = {'reference_id': 'unknown', 'fact_values': values}
    result = snapshot(model, binding, AT)
    assert all(f['status'] == 'unknown' for f in result['facts'].values())
    values.pop(next(iter(values)))
    with pytest.raises(ValueError, match='every declared fact'):
        snapshot(model, binding, AT)


def test_reference_binding_does_not_coerce_a_text_label_to_boolean():
    model = reading()
    binding = {'reference_id': 'bad-label', 'fact_values':
               {f['name']: 'unknown' for f in model['formalization']['facts']}}
    with pytest.raises(ValueError, match='type differs'):
        snapshot(model, binding, AT)
