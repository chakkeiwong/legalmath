from copy import deepcopy
from pathlib import Path
import pytest
from legalmath.canonical import digest, loads
from legalmath.catala.native.source_review import validate_packet, admit_heldout
from legalmath.errors import LegalMathError
from scripts.prepare_catala_source_repair import repair

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def retained():
    source = ROOT / 'artifacts/catala/gap-closure/source-review'
    packet = loads((source / 'packet.json').read_bytes())
    blobs = {p.stem: p.read_bytes() for p in (source / 'sources').glob('*.bin')}
    return packet, blobs


def test_successor_retains_exact_footnotes_without_rewriting_original(retained):
    packet, blobs = retained; original = digest(packet)
    successor = repair(packet, blobs)
    report = validate_packet(successor, list(blobs.values()))
    assert report['tasks'] == 4 and report['adjudication'] == 'PENDING'
    assert digest(packet) == original == successor['repair_of']
    assert [len(row['task']['packet']['units']) for row in successor['corpus']] == [1, 2, 2, 2]
    fact = successor['corpus'][3]['task']['inputs'][-1]
    assert 'SFC-authorised' in fact['meaning']


@pytest.mark.parametrize('mutation', ['missing_bytes', 'altered_quote', 'altered_offset'])
def test_retained_source_corruption_is_rejected(retained, mutation):
    packet, blobs = retained
    unit = packet['corpus'][0]['task']['packet']['units'][0]
    if mutation == 'missing_bytes': blobs.pop(unit['span']['raw_sha256'])
    elif mutation == 'altered_quote': unit['text'] += ' Invented qualification.'
    else: unit['span']['start'] += 1
    with pytest.raises(LegalMathError): validate_packet(packet, list(blobs.values()))


def test_heldout_admission_requires_external_review_bound_to_exact_reference(retained):
    packet, _ = retained
    assert not admit_heldout(packet, set(), {})['admitted']
    attestations = {r['task']['task_id']: {
        'independent_human': True, 'reviewer': 'Fixture independent reviewer',
        'reference_hash': digest({k: r[k] for k in ('task', 'cases', 'witness')}),
        'verdict': 'ACCEPT'} for r in packet['corpus']}
    assert admit_heldout(packet, set(), attestations)['admitted']
    changed = deepcopy(packet)
    changed['corpus'][0]['cases'][0]['expected']['value']['result'] = '999'
    assert not admit_heldout(changed, set(), attestations)['admitted']
    exposed = deepcopy(packet)
    row = exposed['corpus'][0]
    original_family = row['lineage_family']
    row['lineage_family'] = 'renamed.family'; row['source_family'] = 'renamed.raw'
    assert not admit_heldout(exposed, {original_family}, attestations)['admitted']


def test_citation_in_source_field_gets_actionable_repair_feedback(tmp_path):
    from legalmath.catala.native.converter import convert
    from legalmath.interpretation.search.providers import Completion
    from tests.catala.backend_support import TOOLCHAIN, JDK
    from .reference import controls
    task, candidate, _ = controls()[-1]

    class Provider:
        provider_id = 'fixture.source-repair'
        def __init__(self): self.requests = []
        def complete(self, request, schema, limits):
            self.requests.append(request)
            if request['operation'] == 'native_catala_source_criticism':
                return Completion({'verdict': 'SUPPORTED', 'findings': []}, {'fixture': True})
            value = deepcopy(candidate)
            if len(self.requests) == 1:
                value['source'] = task['packet']['source_key']
            else:
                assert 'executable scope definitions' in request['feedback']['details']
                assert '```catala' in request['response_fields']['source']
                assert 'Executable Catala' in schema['properties']['source']['description']
            return Completion(value, {'fixture': True})

    provider = Provider()
    result = convert(task, tmp_path / 'conversion', provider, JDK, **TOOLCHAIN)
    assert result['status'] == 'READY_FOR_BEHAVIOR_CHECK'
    assert len(provider.requests) == 3
