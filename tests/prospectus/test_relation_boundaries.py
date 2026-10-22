from copy import deepcopy

import pytest

from legalmath.prospectus.relation_boundaries import discover_bounded
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.relation_discovery import discover, SCOPED_PROFILE


def fixture(marker='Gii)', *, gap=30, residue=False):
    rows = [('(i)',[20,10,30,20]), ('First:',[40,10,110,20]), ('One',[200,10,240,20]),
            ('(ii)',[20,40,30,50]), ('Second:',[40,40,110,50]), ('Two',[200,40,240,50]),
            (marker,[20,40+gap,35,50+gap]), ('Unrelated:',[40,40+gap,120,50+gap]),
            ('Other',[200,40+gap,240,50+gap])]
    if residue:
        # The residue changes the largest seed gap on the second row. Include
        # another ordinary row so v2's required repeated value column exists.
        rows.extend([('x',[590,39,592,45]), ('(iii)',[20,110,35,120]),
                     ('Third:',[40,110,110,120]), ('Three',[200,110,240,120])])
    return {'units':[{'id':f'u{i}','document':'synthetic','page':1,'source_sha256':'a'*64,
                     'order':i,'raw':text,'text_sha256':digest(text.encode()),'bbox':box,'words':[],
                     'visible':True} for i,(text,box) in enumerate(rows)]}


def second(result):
    return next(c for c in result['candidates'] if c.get('row_marker',{}).get('quote')=='(ii)')


@pytest.mark.parametrize('marker',['Gii)','7.','7,','Unrecognized'])
def test_unknown_marker_stops_both_sides_without_correcting_source(marker):
    g=fixture(marker); before=deepcopy(g)
    old=second(discover(g,SCOPED_PROFILE)); assert len(old['to'])==2
    result=discover_bounded(g); c=second(result)
    assert [a['quote'] for a in c['from']]==['Second:']
    assert [a['quote'] for a in c['to']]==['Two']
    assert c['boundary_evidence']['quote']==marker
    assert g==before
    lineage=next(r for r in result['lineage'] if r['original_id']==old['id'])
    assert lineage['status']=='BOUNDED' and {a['quote'] for a in lineage['removed']}=={'Other','Unrelated:'}


def test_parent_label_stops_row_when_arabic_marker_is_farther_left():
    g=fixture('8.')
    g['units'][6]['bbox']=[0,70,10,80]
    g['units'][7]['bbox']=[20,70,110,80]
    c=second(discover_bounded(g))
    assert [a['quote'] for a in c['to']]==['Two']
    assert c['boundary_evidence']['quote']=='Unrelated:'


@pytest.mark.parametrize('gap',[12,20,30])
def test_tightly_spaced_next_rows_do_not_enter_previous_value(gap):
    c=second(discover_bounded(fixture(gap=gap)))
    assert [a['quote'] for a in c['to']]==['Two']


def test_disconnected_real_or_noise_value_abstains_without_deleting_raw_text():
    g=fixture(residue=True); before=deepcopy(g)
    original=second(discover(g,SCOPED_PROFILE))
    result=discover_bounded(g)
    row=next(r for r in result['lineage'] if r['original_id']==original['id'])
    assert row['status']=='ABSTAINED' and row['candidate_id'] is None
    assert 'Disconnected' in row['reason']
    assert g==before


def test_multiline_value_and_full_note_qualification_are_preserved():
    g=fixture()
    g['units']=g['units'][:6]
    for raw,box in [('Note that intended holding',[200,55,350,65]),
                    ('does not establish eligibility.',[200,68,360,78])]:
        i=len(g['units']); g['units'].append({'id':f'u{i}','document':'synthetic','page':1,
            'source_sha256':'a'*64,'order':i,'raw':raw,'text_sha256':digest(raw.encode()),
            'bbox':box,'words':[],'visible':True})
    original=discover(g,SCOPED_PROFILE)
    result=discover_bounded(g)
    assert result['candidates']==original['candidates']
    assert all(r['status']=='UNCHANGED' for r in result['lineage'])
    assert len(next(c for c in result['candidates'] if c['kind']=='qualifies')['from'])==2


def test_boundary_intersecting_qualification_abstains_instead_of_clipping():
    g=fixture()
    g['units'][6]['bbox']=[20,85,35,95]
    g['units'][7]['raw']='Note that recognition';g['units'][7]['text_sha256']=digest(g['units'][7]['raw'].encode())
    g['units'][7]['bbox']=[200,55,340,65]
    g['units'][8]['raw']='requires additional criteria.';g['units'][8]['text_sha256']=digest(g['units'][8]['raw'].encode())
    g['units'][8]['bbox']=[200,85,350,95]
    result=discover_bounded(g)
    old=discover(g,SCOPED_PROFILE)
    qualifier=next(c for c in old['candidates'] if c['kind']=='qualifies')
    row=next(r for r in result['lineage'] if r['original_id']==qualifier['id'])
    assert row['status']=='ABSTAINED' and 'qualification' in row['reason']


def test_page_boundary_cannot_supply_a_stop_witness():
    g=fixture();g['units'][6]['page']=2
    assert second(discover_bounded(g))==second(discover(g,SCOPED_PROFILE))


def test_scale_translation_and_input_permutation_preserve_candidates_and_lineage():
    g=fixture(); expected=discover_bounded(g)
    for u in g['units']:u['bbox']=[3.5*x+72 for x in u['bbox']]
    g['units'].reverse()
    result=discover_bounded(g)
    assert result['candidates']==expected['candidates']
    assert result['lineage']==expected['lineage']


@pytest.mark.parametrize('case',['duplicate','text','box','word_box'])
def test_existing_integrity_refusals_remain(case):
    g=fixture()
    if case=='duplicate':g['units'].append(deepcopy(g['units'][0]))
    elif case=='text':g['units'][0]['raw']='tampered'
    elif case=='box':g['units'][0]['bbox']=None
    else:g['units'][0]['words']=[{'bbox':None}]
    if case in {'duplicate','text'}:
        with pytest.raises(ValueError):discover_bounded(g)
    else:assert not discover_bounded(g)['candidates']


def test_no_relation_admission_or_legal_scope():
    result=discover_bounded(fixture())
    assert result['accepted_relations']==[] and result['legal_scope_inferred'] is False
    assert all(c['legal_scope_established'] is False for c in result['candidates'])
