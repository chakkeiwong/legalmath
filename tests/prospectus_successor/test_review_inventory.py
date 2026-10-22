"""Preparation accounts for source rows; none of these tests creates readers."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from legalmath.prospectus.successor import review_inventory as inventory
from legalmath.prospectus.successor.contracts import digest

def put(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value));return path

def fixture(root):
    (root/'sources').mkdir(exist_ok=True)
    for name,text in [('a','shared'),('b','shared'),('c','different'),('d','unknown')]:
        (root/'sources'/name).write_text(text)
    rows=[{'id':n,'file':'sources/'+n,'sha256':digest((root/'sources'/n).read_bytes())} for n in 'abcd']
    rows[0]['data_role']='development'
    put(root/'manifest.json',{'documents':rows})
    note=root/'review.txt';note.write_text('b and c share family X; a uses family Y.')
    ev={'path':'review.txt','sha256':digest(note.read_bytes()),'quote':note.read_text()}
    families={'manifest.json#'+n:{'family':f,'reason':'Finite fixture review','evidence':[ev]}
              for n,f in [('a','Y'),('b','X'),('c','X')]}
    return rows,families

def test_duplicate_bytes_propagate_exposure_across_reviewed_family_alias(tmp_path):
    _,families=fixture(tmp_path)
    result=inventory.build(tmp_path,['manifest.json'],families,{})
    rows={r['id']:r for r in result['documents']}
    assert all(rows[k]['exposure']=='CONFIRMED_DEVELOPMENT' for k in 'abc')
    assert rows['d']['exposure']=='NOT_ESTABLISHED'
    assert result['document_count']==4 and result['source_issue_count']==0
    assert len(rows['a']['source_aliases'])==2
    assert not result['unexposed_cohort_established'] and not result['complete_family_alias_inventory']
    selected=inventory.preflight(result,[r['entry'] for r in result['documents']])
    assert not selected['eligible']
    assert {r['reason'] for r in selected['candidates']}=={'EXPOSED_DEVELOPMENT_SOURCE_OR_FAMILY','UNEXPOSED_STATUS_NOT_ESTABLISHED'}

@pytest.mark.parametrize('key',['file','original','path'])
@pytest.mark.parametrize('schema',['list','dict','single'])
def test_supported_manifest_forms_retain_exact_source(tmp_path,key,schema):
    (tmp_path/'sub').mkdir();path=tmp_path/'sub/a.txt';path.write_text('text')
    row={'id':'a',key:'a.txt','sha256':digest(path.read_bytes())}
    value={'documents':[row]} if schema=='list' else {'documents':{'a':row}} if schema=='dict' else row
    put(tmp_path/'sub/manifest.json',value)
    result=inventory.build(tmp_path,['sub/manifest.json'],{},{})
    assert result['document_count']==1 and result['source_issue_count']==0
    assert result['documents'][0]['source']=='sub/a.txt'

@pytest.mark.parametrize('mutation',['missing','hash','nohash','escape','conflicting','ambiguous','blank'])
def test_bad_source_is_accounted_and_blocked(tmp_path,mutation):
    rows,families=fixture(tmp_path);row=rows[0]
    if mutation=='missing':row['file']='missing.txt'
    elif mutation=='hash':row['sha256']='0'*64
    elif mutation=='nohash':del row['sha256']
    elif mutation=='escape':row['file']='../outside.txt'
    elif mutation=='conflicting':row['original']='sources/c'
    elif mutation=='blank':row['file']=''
    else:
        put(tmp_path/'sub/manifest.json',{'documents':[{'id':'a','original':'sources/a','sha256':row['sha256']}]})
        (tmp_path/'sub/sources').mkdir();(tmp_path/'sub/sources/a').write_text('shared')
        result=inventory.build(tmp_path,['sub/manifest.json'],{},{})
        assert result['source_issue_count']==1
        return
    put(tmp_path/'manifest.json',{'documents':rows})
    result=inventory.build(tmp_path,['manifest.json'],families,{})
    assert result['document_count']==4 and result['source_issue_count']==1
    assert inventory.preflight(result,['manifest.json#a'])['candidates'][0]['reason']=='SOURCE_INTEGRITY_UNRESOLVED'

def test_repeated_ids_across_manifests_are_not_dropped(tmp_path):
    fixture(tmp_path);data=json.loads((tmp_path/'manifest.json').read_text())
    put(tmp_path/'other.json',data)
    result=inventory.build(tmp_path,['manifest.json','other.json'],{},{})
    assert result['document_count']==8
    assert len({r['entry'] for r in result['documents']})==8

def test_duplicate_identity_within_manifest_refuses_ambiguous_selection(tmp_path):
    rows,_=fixture(tmp_path);rows[1]['id']='a';put(tmp_path/'manifest.json',{'documents':rows})
    with pytest.raises(ValueError,match='Duplicate document'):inventory.build(tmp_path,['manifest.json'],{},{})

def test_missing_identity_is_retained_with_issue(tmp_path):
    rows,_=fixture(tmp_path);del rows[0]['id'];put(tmp_path/'manifest.json',{'documents':rows})
    result=inventory.build(tmp_path,['manifest.json'],{},{})
    assert result['document_count']==4 and result['source_issue_count']==1

@pytest.mark.parametrize('mutation',['hash','quote','escape','unknown_entry','reason'])
def test_unbound_family_evidence_refuses(tmp_path,mutation):
    _,families=fixture(tmp_path);row=families['manifest.json#a']
    if mutation=='hash':row['evidence'][0]['sha256']='0'*64
    elif mutation=='quote':row['evidence'][0]['quote']='invented'
    elif mutation=='escape':row['evidence'][0]['path']='../outside'
    elif mutation=='reason':row['reason']=''
    else:families['missing#x']=deepcopy(row)
    with pytest.raises(ValueError):inventory.build(tmp_path,['manifest.json'],families,{})

def test_changed_inventory_and_unknown_selection_refuse(tmp_path):
    _,families=fixture(tmp_path);result=inventory.build(tmp_path,['manifest.json'],families,{})
    with pytest.raises(ValueError):inventory.preflight(result,['unknown'])
    with pytest.raises(ValueError):inventory.preflight(result,['manifest.json#a']*2)
    result['documents'][0]['exposure']='NOT_ESTABLISHED'
    with pytest.raises(ValueError):inventory.preflight(result,['manifest.json#a'])
