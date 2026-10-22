from copy import deepcopy
import json
import pytest
from legalmath.prospectus import geometry_transfer as geometry
from legalmath.prospectus.successor.contracts import digest


def pair():
    base={'version':'hybrid-ocr.v1','source_sha256':'a'*64,'page_count':1,'selected_pages':[1],
          'runtime':{'dpi':300,'language':'por','language_models':{'por':'b'*64},'pymupdf':'1','mupdf':'1'},
          'pages':[{'page':1,'image_sha256':'c'*64,'image_width':100,'image_height':100,
                    'width_points':100,'height_points':100,'text':'same same :',
                    'words':[[1,1,2,2,'same',0,0,0],[3,1,4,2,'same',0,0,1],[101,1,102,2,':',0,0,2]]}]}
    candidate=deepcopy(base);candidate['pages'][0]['words'][-1][:4]=[5,1,6,2]
    candidate['pages'][0]['words'][1][5:]=[9,8,7]
    return base,candidate


def run(base,candidate,**kw):
    args={'original_sha256':digest(base),'candidate_sha256':digest(candidate),'policy':geometry.POLICY}
    args.update(kw)
    return geometry.transfer(base,candidate,**args)


def test_transfer_preserves_all_original_content_except_positions_and_provenance():
    base,candidate=pair(); before=deepcopy(base); other=deepcopy(candidate)
    result=run(base,candidate)
    assert base==before and candidate==other
    assert result['pages'][0]['text']==base['pages'][0]['text']
    assert [w[4:] for w in result['pages'][0]['words']]==[w[4:] for w in base['pages'][0]['words']]
    assert result['pages'][0]['words'][-1][:4]==[5,1,6,2]
    assert result['runtime']['geometry_transfer']['changed_rectangles']==1
    assert result['runtime']['geometry_transfer']['automatic_segmentation'] is False


@pytest.mark.parametrize('change',['source','image','model','runtime','word','missing-word','reordered',
                                  'negative-box','nan','bad-group','missing-page','duplicate-page','dimension','version'])
def test_transfer_refuses_changed_identity_words_or_geometry(change):
    base,candidate=pair()
    if change=='source':candidate['source_sha256']='d'*64
    elif change=='image':candidate['pages'][0]['image_sha256']='d'*64
    elif change=='model':candidate['runtime']['language_models']['por']='d'*64
    elif change=='runtime':candidate['runtime']['mupdf']='2'
    elif change=='word':candidate['pages'][0]['words'][0][4]='other'
    elif change=='missing-word':candidate['pages'][0]['words'].pop()
    elif change=='reordered':candidate['pages'][0]['words'].reverse()
    elif change=='negative-box':candidate['pages'][0]['words'][0][0]=-1
    elif change=='nan':candidate['pages'][0]['words'][0][0]=float('nan')
    elif change=='bad-group':base['pages'][0]['words'][0][5]=True
    elif change=='missing-page':candidate['pages']=[]
    elif change=='duplicate-page':candidate['selected_pages']=[1,1];candidate['pages']*=2
    elif change=='dimension':candidate['pages'][0]['width_points']=101
    else:candidate['version']='unrecognized'
    with pytest.raises(ValueError):run(base,candidate)


def test_transfer_requires_explicit_policy_and_current_pins():
    a,b=pair()
    for kw in ({'policy':'guess'},{'original_sha256':'0'*64},{'candidate_sha256':'0'*64}):
        with pytest.raises(ValueError):run(a,b,**kw)
    with pytest.raises(ValueError):run(run(a,b),b)


def test_file_api_and_cli_preserve_pins_and_refuse_existing_output(tmp_path,capsys):
    a,b=pair();ap=tmp_path/'a.json';bp=tmp_path/'b.json';out=tmp_path/'out.json'
    ap.write_text(json.dumps(a));bp.write_text(json.dumps(b))
    args=['--original',str(ap),'--candidate',str(bp),'--original-sha256',geometry.sha256(ap),
          '--candidate-sha256',geometry.sha256(bp),'--policy',geometry.POLICY,'--output',str(out)]
    assert geometry.main(args)==0
    assert json.loads(capsys.readouterr().out)['changed_rectangles']==1
    result=json.loads(out.read_text());assert result['runtime']['geometry_transfer']['input_files']['original_sha256']==geometry.sha256(ap)
    with pytest.raises(ValueError,match='already exists'):geometry.main(args)
    out2=tmp_path/'changed.json';args[-1]=str(out2);bp.write_text('changed')
    with pytest.raises(ValueError,match='file identity'):geometry.main(args)
    assert not out2.exists()
