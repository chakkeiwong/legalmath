"""The presentation condition must never become the limitation clock origin."""
from copy import deepcopy
import hashlib
from pathlib import Path
import pytest
from legalmath.prospectus.successor import statutory_references as module

ROOT=Path(__file__).resolve().parents[2]


def rules(spec):
    return next(r for r in spec['records'] if r['id']=='H28')['timing_rules']


def test_exact_bgb_sources_and_distinct_clocks():
    spec=module.specification();rows=module.validate_timing_rules(spec)
    for row in rows:
        raw=(ROOT/row['source_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==row['source_sha256']
        assert raw.decode('utf-8')[row['start']:row['end']]==row['quote']
    by_id={row['id']:row for row in rows}
    rule=by_id['limitation_after_presentation']
    assert 'von dem Ende der Vorlegungsfrist an' in rule['quote']
    assert rule['meaning']['origin']=='END_OF_PRESENTATION_PERIOD'
    assert rule['meaning']['years']==2
    assert rule['meaning']['presentation_date_is_origin'] is False
    assert by_id['coupon_presentation']['meaning']['origin']=='END_OF_YEAR_PERFORMANCE_DUE'
    assert by_id['payment_stop_suspension']['meaning']['clocks']==['PRESENTATION','LIMITATION']


@pytest.mark.parametrize('kind',['presentation-origin','duration','coupon-origin','judicial',
                                'presentation-suspension','limitation-suspension','quote','offset'])
def test_self_consistent_profile_mutations_still_fail_source_rules(kind):
    spec=deepcopy(module.specification());rows=rules(spec)
    if kind=='presentation-origin':rows[1]['meaning']['origin']='PRESENTATION_DATE'
    elif kind=='duration':rows[1]['meaning']['years']=10
    elif kind=='coupon-origin':rows[3]['meaning']['origin']='PERFORMANCE_DUE'
    elif kind=='judicial':rows.pop(2)
    elif kind=='presentation-suspension':rows[-1]['meaning']['clocks']=['LIMITATION']
    elif kind=='limitation-suspension':rows[-1]['meaning']['clocks']=['PRESENTATION']
    elif kind=='quote':rows[1]['quote']+=' altered'
    else:rows[1]['start']+=1
    with pytest.raises(ValueError,match='H28'):
        module.validate_timing_rules(spec)


def test_timing_repair_preserves_every_other_h28_field():
    import json
    path=ROOT/'docs/implementation/prospectus-execution-authority/reviews/bgb-timing-302/baseline/statutory_references_spec.json'
    old=next(r for r in json.loads(path.read_text())['records'] if r['id']=='H28')
    current=next(r for r in module.specification()['records'] if r['id']=='H28')
    del current['timing_rules']
    for key in ('reviewed_reading','unresolved_application'):
        current[key]=old[key]
    assert current==old
