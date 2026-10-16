from copy import deepcopy
from pathlib import Path

import pytest

from legalmath.canonical import loads
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.legal_locators import validate_citation, build_index, retained_html

ROOT = Path(__file__).resolve().parents[2]


def test_actual_large_23ec52_unit_can_cite_exact_numbered_passage():
    base = ROOT/'artifacts/legal-mission-control/2026-10-12/completion/target-qualification'
    index = loads((base/'23ec52-locators.json').read_bytes())
    packet = loads((base/'mandatory-envelope.json').read_bytes())['source_packet']
    index = build_index(packet,retained_html(index['source'],ROOT),source_ref=index['source'],
                        unit_ids=list(index['units']),root=ROOT,numbering_profile='decimal-paragraphs')
    assert [r['locator'] for r in index['records']] == ([f'P{i}' for i in range(1,37)] + [f'FN{i}' for i in range(1,10)])
    paragraph = next(r for r in index['records'] if r['locator']=='P18')
    quote = paragraph['text']
    unit = next(u for u in packet['units'] if quote in u['text'])
    assert index['units'][unit['unit_id']]['status']=='UNLOCATED'
    validate_citation(packet,index,unit_id=unit['unit_id'],quote=quote,locator='P18',root=ROOT)
    for wrong in ('P17','P19','FN1'):
        with pytest.raises(LegalMathError):
            validate_citation(packet,index,unit_id=unit['unit_id'],quote=quote,locator=wrong,root=ROOT)
    with pytest.raises(LegalMathError):
        validate_citation(packet,index,unit_id=unit['unit_id'],quote='the',locator='P18',root=ROOT)
    changed = deepcopy(index); changed['records'][0]['text'] += 'Substituted document.'
    with pytest.raises(LegalMathError):
        validate_citation(packet,changed,unit_id=unit['unit_id'],quote=quote,locator='P18',root=ROOT)
