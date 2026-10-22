"""Meaningful controls for text admission without fabricated OCR positions."""
import pytest
from legalmath.prospectus.successor import anchors, corrections, layout_adapter, source_graph
from legalmath.prospectus.successor.contracts import digest
from test_closure_real_scan import hybrid_correction_fixture


def optional(bundle):
    bundle['documents'][0]['hybrid_profile'].update(version='pymupdf-hybrid.v2',
        geometry_policy='preserve-text-without-invalid-box.v1')


def affected(graph):
    return next(u for u in graph['units'] if u.get('geometry_issues'))


@pytest.mark.parametrize('text', [':', 'not liable'])
@pytest.mark.parametrize('box', [[530,720,1037,726], [-10,20,100,40], [20,780,100,900]])
def test_unknown_geometry_preserves_legal_text_and_strict_rejection(tmp_path, monkeypatch, text, box):
    bundle, data, save = hybrid_correction_fixture(tmp_path, monkeypatch)
    data['pages'][0]['words'] = [[20,20,100,40,'The issuer is',0,0,0], box + [text,0,0,1]]
    data['pages'][0]['text'] = 'The issuer is ' + text
    save()
    raw_sha = digest((tmp_path / 'ocr.json').read_bytes())
    with pytest.raises(ValueError, match='outside original'):
        source_graph.build(bundle, tmp_path)
    optional(bundle)
    graph = source_graph.build(bundle, tmp_path)
    unit = affected(graph)
    assert unit['raw'] == 'The issuer is ' + text
    assert unit['bbox'] is None and unit['words'][1]['bbox'] is None
    assert unit['words'][0]['bbox'] == [20,20,100,40]
    assert unit['words'][1]['geometry_issue']['raw_bbox'] == box
    assert unit['words'][1]['geometry_issue']['kind'] == 'OCR_WORD_OUTSIDE_PAGE'
    assert unit['image_sha256'] == data['pages'][0]['image_sha256']
    assert digest((tmp_path / 'ocr.json').read_bytes()) == raw_sha
    for word in unit['words']:
        assert unit['raw'][word['start']:word['end']] == word['text']
    source = {k:unit[k] for k in ('document','source_sha256')}
    source.update(unit=unit['id'], start=14, end=len(unit['raw']), quote=text)
    bound = anchors.bind(graph, source)
    assert bound['bbox'] is None and bound['geometry_issues'] and bound['image_sha256']
    assert len([u for u in graph['units'] if u['method']=='pdftotext-bbox-layout']) == 23


@pytest.mark.parametrize('mutation', ['nan','inf','inverted','zero','bool','word-order','image','source','page'])
@pytest.mark.parametrize('degraded', [False, True])
def test_corrupt_records_still_rejected(tmp_path, monkeypatch, mutation, degraded):
    bundle, data, save = hybrid_correction_fixture(tmp_path, monkeypatch)
    if degraded:
        optional(bundle)
    word = data['pages'][0]['words'][0]
    if mutation=='nan': word[0]=float('nan')
    elif mutation=='inf': word[2]=float('inf')
    elif mutation=='inverted': word[2]=word[0]-1
    elif mutation=='zero': word[2]=word[0]
    elif mutation=='bool': word[0]=True
    elif mutation=='word-order': word[7]=-1
    elif mutation=='image': del data['pages'][0]['image_sha256']
    elif mutation=='source': data['source_sha256']='0'*64
    else: data['pages'][0]['page']=24
    save()
    with pytest.raises(ValueError): source_graph.build(bundle, tmp_path)


@pytest.mark.parametrize('degraded', [False, True])
def test_rounding_tolerance_stays_bounded(tmp_path, monkeypatch, degraded):
    bundle, data, save = hybrid_correction_fixture(tmp_path, monkeypatch)
    if degraded: optional(bundle)
    data['pages'][0]['words'][0][:4] = [-0.0005,20,612.0005,40]
    save()
    graph = source_graph.build(bundle, tmp_path)
    assert not any(u.get('geometry_issues') for u in graph['units'])
    data['pages'][0]['words'][0][2] = 612.002
    save()
    if degraded:
        assert affected(source_graph.build(bundle, tmp_path))['bbox'] is None
    else:
        with pytest.raises(ValueError): source_graph.build(bundle, tmp_path)


def test_valid_optional_words_equal_strict_words(tmp_path, monkeypatch):
    bundle, data, save = hybrid_correction_fixture(tmp_path, monkeypatch)
    baseline = source_graph.build(bundle, tmp_path)
    optional(bundle)
    assert source_graph.build(bundle, tmp_path)['units'] == baseline['units']
    bundle['documents'][0]['hybrid_profile']['geometry_policy'] = 'clip'
    with pytest.raises(ValueError): source_graph.build(bundle, tmp_path)


def test_unknown_geometry_blocks_layout_but_retains_image_bound_correction(tmp_path, monkeypatch):
    bundle, data, save = hybrid_correction_fixture(tmp_path, monkeypatch)
    data['pages'][0]['words'][0][2] = 1000
    save()
    optional(bundle)
    graph = source_graph.build(bundle, tmp_path)
    unit = affected(graph)
    units = [u for u in graph['units'] if u['page']==22]
    layout = {'texts':[{'self_ref':'body','text':unit['raw'],'prov':[{'page_no':22,
        'bbox':{'l':0,'t':0,'r':612,'b':792,'coord_origin':'TOPLEFT'}}]}]}
    for mapper, key in [(layout_adapter.map_layout,'mappings'), (layout_adapter.project_layout,'mappings')]:
        result = mapper(units, layout, source_sha256=unit['source_sha256'])
        assert not result[key] and 'Unknown word geometry' in result['failures'][0]['reason']
    source = {'unit':unit['id'],'document':unit['document'],'source_sha256':unit['source_sha256'],
        'start':0,'end':len(unit['raw']),'quote':unit['raw']}
    packet = {'version':'reviewed-corrections.v1','graph_sha256':digest(graph),
        'review':{'reviewer':'development control','reason':'Synthetic image-bound correction',
                  'kind':'DEVELOPMENT'},
        'entries':[{'id':'correction','source':source,'image_sha256':unit['image_sha256'],
            'operations':[{'kind':'copy','start':0,'end':len(unit['raw']),
                           'text':unit['raw'],'reason':'Preserve source words'}]}]}
    admitted = corrections.admit(graph, packet)
    assert admitted['entries'][0]['bbox'] is None
    assert all(s['bbox'] is None for s in admitted['entries'][0]['segments'])
    del packet['entries'][0]['image_sha256']
    with pytest.raises(ValueError, match='image identity'): corrections.admit(graph, packet)
