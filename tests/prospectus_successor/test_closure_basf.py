"""Actual BASF source copies and exact replacement evidence after construction."""
from copy import deepcopy
from pathlib import Path
import pytest
from legalmath.prospectus.successor import basf, jobs, source_graph
from legalmath.prospectus.successor.contracts import digest, read
from legalmath.prospectus.successor.occurrences import anchor, uses, segments


@pytest.fixture(scope='module')
def basf_case():
    root=Path(__file__).resolve().parents[2]
    graph=source_graph.build(jobs.basf_request(root)['bundle'],root)
    construction=basf.construct(graph,read(root/jobs.BASF))
    assembly=basf.as_assembly(graph,construction)
    return graph,construction,assembly


@pytest.fixture(scope='module')
def scalar_case(basf_case):
    root=Path(__file__).resolve().parents[2]
    admission=read(root/'docs/implementation/prospectus-integration-closure/basf-scalars/review.json')['admission']
    graph,construction,_=basf_case
    return admission,basf.as_assembly(graph,construction,admission)


def test_basf_six_reviewed_scalar_output_uses_and_separate_authority(basf_case,scalar_case):
    graph,construction,legacy=basf_case
    admission,assembly=scalar_case
    assert len([p for u in legacy['units'] for p in u.get('character_map',[])
                if p['operation']=='UnmappedSubstitution'])==6
    assert not [p for u in assembly['units'] for p in u.get('character_map',[])
                if p['operation']=='UnmappedSubstitution']
    operations={digest(o):o for o in construction['operations']}
    for row in admission['bindings']:
        operation=operations[row['operation_sha256']]
        unit=next(u for u in assembly['units'] if u['unit']==operation['source_units'][0])
        piece=next(p for p in unit['character_map'] if p.get('scalar_operation_sha256')==row['operation_sha256'])
        selected={'units':[unit]}
        matches=uses(graph,selected,row['source'],roles=('UNKNOWN',))
        assert len(matches)==1 and matches[0]['start']==piece['start'] and matches[0]['end']==piece['end']
        assert unit['text'][piece['start']:piece['end']]==operation['new']
        assert piece['source']==row['source']
        assert piece['operation']==('Text' if row['kind']=='LITERAL_SELECTION' else 'Field')
        if row['kind']=='LITERAL_SELECTION':
            assert row['source']['document']==basf.KEY
            assert piece['selection_authority']==row['selection_authority']
            assert not uses(graph,selected,row['selection_authority'],roles=('UNKNOWN',))
    assert assembly['continuous_text']==legacy['continuous_text']==construction['candidate_text']
    assert assembly['status']=='PARTIAL' and not assembly['independent_legal_review']
    assert len(construction['remaining_brackets'])==15
    assert len(construction['interval_accounting']['unresolved'])==537


@pytest.mark.parametrize('change',['version','graph','construction','missing','duplicate','operation','edition',
    'quote','template','foreign_authority','absent_authority','outside_literal','wrong_kind','reason'])
def test_basf_scalar_admission_invalid_evidence_rejects(basf_case,scalar_case,change):
    graph,construction,_=basf_case
    admission=deepcopy(scalar_case[0])
    row=admission['bindings'][0]
    literal=admission['bindings'][1]
    raw={u['id']:u for u in graph['units']}
    if change=='version': admission['version']='unreviewed'
    elif change=='graph': admission['graph_sha256']='0'*64
    elif change=='construction': admission['construction_sha256']='0'*64
    elif change=='missing': admission['bindings'].pop()
    elif change=='duplicate': admission['bindings'].append(deepcopy(row))
    elif change=='operation': row['operation_sha256']='0'*64
    elif change=='edition': row['source']['source_sha256']='0'*64
    elif change=='quote': row['source']['quote']='BASF Finance'
    elif change=='template':
        operation=next(o for o in construction['operations'] if digest(o)==row['operation_sha256'])
        unit=raw[operation['source_units'][0]]
        span=next(s for s in construction['source_map'] if s['unit']==unit['id'])
        row['source']=anchor(unit,operation['start']-span['start'],operation['end']-span['start'])
    elif change=='foreign_authority':
        unit=raw[basf.KEY+':p108:l8']
        left=unit['raw'].index('BASF SE')
        literal['selection_authority']=anchor(unit,left,left+len('BASF SE'))
    elif change=='absent_authority': del literal['selection_authority']
    elif change=='outside_literal':
        unit=next(u for u in graph['units'] if u['document']==basf.KEY and '"BASF"' in u['raw']
                  and u['id']!=literal['source']['unit'])
        left=unit['raw'].index('"BASF"')
        literal['source']=anchor(unit,left,left+len('"BASF"'))
    elif change=='wrong_kind': literal.pop('selection_authority'); literal['kind']='VALUE_COPY'
    elif change=='reason': row['reason']=' '
    with pytest.raises(ValueError):
        basf.as_assembly(graph,construction,admission)


@pytest.mark.parametrize('change',['bindings_shape','row_shape','source_shape','unit_shape','operation_shape',
    'authority_shape','review_shape','missing_source_key'])
def test_basf_scalar_malformed_input_rejects_cleanly(basf_case,scalar_case,change):
    graph,construction,_=basf_case
    admission=deepcopy(scalar_case[0])
    if change=='bindings_shape': admission['bindings']={}
    elif change=='row_shape': admission['bindings'][0]=None
    elif change=='source_shape': admission['bindings'][0]['source']=[]
    elif change=='unit_shape': admission['bindings'][0]['source']['unit']=[]
    elif change=='operation_shape': admission['bindings'][0]['operation_sha256']=[]
    elif change=='authority_shape': admission['bindings'][1]['selection_authority']=None
    elif change=='review_shape': admission['review']['kind']=[]
    elif change=='missing_source_key': del admission['bindings'][0]['source']['unit']
    with pytest.raises(ValueError):
        basf.as_assembly(graph,construction,admission)


def test_basf_scalar_altered_construction_rejects(basf_case,scalar_case):
    graph,construction,_=basf_case
    changed=deepcopy(construction)
    operation=next(o for o in changed['operations'] if o['new']=='4,250')
    operation['new']='5,250'
    with pytest.raises(ValueError,match='construction changed'):
        basf.as_assembly(graph,changed,scalar_case[0])


@pytest.mark.parametrize('change',['text','source','authority','missing','repeated'])
def test_basf_scalar_consumer_rejects_altered_output(basf_case,scalar_case,change):
    from scripts.prospectus_closure_basf import check_report
    graph,construction,_=basf_case
    admission,original=scalar_case
    assembly=deepcopy(original)
    unit,piece=next((u,p) for u in assembly['units'] for p in u.get('character_map',[])
                    if p.get('scalar_operation_sha256')==admission['bindings'][1]['operation_sha256'])
    if change=='text': unit['text']=unit['text'][:piece['start']]+'X'+unit['text'][piece['start']+1:]
    elif change=='source': piece['source']=deepcopy(piece['selection_authority'])
    elif change=='authority': piece['selection_authority']=deepcopy(piece['source'])
    elif change=='missing': unit['character_map'].remove(piece)
    elif change=='repeated': unit['character_map'].append(deepcopy(piece))
    report={'source_map':graph,'selected_contract':construction,'assembly':assembly}
    with pytest.raises(ValueError,match='scalar'):
        check_report(report,{'construction':{'scalar_admission':admission}})


def test_basf_same_page_duplicate_is_not_reviewed_output_provenance(basf_case,scalar_case):
    from scripts.prospectus_closure_basf import prepared_request
    from legalmath.prospectus.successor.admissions import dispositions
    graph,construction,_=basf_case
    admission,assembly=scalar_case
    row=admission['bindings'][2]
    unit=next(u for u in assembly['units'] if any(p.get('scalar_operation_sha256')==row['operation_sha256']
                                               for p in u.get('character_map',[])))
    duplicate=next(u for u in graph['units'] if u['id']=='basf-2032-final:p3:l22')
    assert duplicate['raw']==row['source']['quote']
    wrong_source=anchor(duplicate)
    assert not uses(graph,{'units':[unit]},wrong_source,roles=('UNKNOWN',))
    changed=deepcopy(admission)
    changed['bindings'][2]['source']=wrong_source
    # A newly supplied same-page interpretation is not adjudicated by quote
    # equality. Its changed map must fail the original downstream binding.
    changed_assembly=basf.as_assembly(graph,construction,changed)
    request=prepared_request(Path(__file__).resolve().parents[2],graph)
    with pytest.raises(ValueError,match='disposition assembly changed'):
        dispositions(graph,changed_assembly,request['reviewed_dispositions'])


def test_basf_construction_and_obligations_preserved(basf_case):
    _,construction,_=basf_case
    root=Path(__file__).resolve().parents[2]
    baseline=read(root/'docs/implementation/prospectus-adoption/phases/A1/attempt-008/product.json')
    assert construction==baseline
    assert construction['status']=='PARTIAL' and not construction['independent_legal_review']


def test_basf_partial_copy_survives_and_deleted_bracket_does_not(basf_case):
    graph,_,assembly=basf_case
    raw=next(u for u in graph['units'] if u['id']==basf.KEY+':p120:l90')
    source=anchor(raw,1)
    selected=next(u for u in assembly['units'] if u['unit']==raw['id'])
    subset={'units':[selected]}
    matches=uses(graph,subset,source,roles=('UNKNOWN',))
    assert len(matches)==1 and matches[0]['start']==0
    assert selected['text'][matches[0]['start']:matches[0]['end']]==source['quote']
    assert not uses(graph,subset,anchor(raw,0,1),roles=('UNKNOWN',))
    assert not uses(graph,subset,anchor(raw),roles=('UNKNOWN',))


def test_basf_substituted_principal_uses_final_terms_not_template(basf_case):
    graph,construction,assembly=basf_case
    raw={u['id']:u for u in graph['units']}
    op=next(o for o in construction['operations'] if o['new']=='EUR 500.000.000')
    selected=next(u for u in assembly['units'] if u['unit']==op['source_units'][0])
    subset={'units':[selected]}
    matches=uses(graph,subset,op['basis'],roles=('UNKNOWN',))
    assert len(matches)==1
    assert selected['text'][matches[0]['start']:matches[0]['end']]=='EUR 500.000.000'
    unit=raw[selected['unit']]
    left=unit['raw'].index('[Gesamtnennbetrag]')
    assert not uses(graph,subset,anchor(unit,left,left+len('[Gesamtnennbetrag]')),roles=('UNKNOWN',))


def test_basf_legacy_page_basis_is_not_invented_occurrence(basf_case):
    graph,_,assembly=basf_case
    pieces=[p for u in assembly['units'] for p in u.get('character_map',[]) if p['operation']=='UnmappedSubstitution']
    assert pieces and all('source' not in p for p in pieces)
    rate=next(u for u in assembly['units'] if any(p.get('basis',{}).get('quote','').startswith('Rate of Interest')
                                                          for p in u.get('character_map',[])))
    raw={u['id']:u for u in graph['units']}
    for piece in segments(graph,rate,_raw=raw):
        assert piece['source']['quote'] != '4,250'


@pytest.mark.parametrize('change',['edition','quote','replacement'])
def test_basf_replacement_source_mutation_rejects(basf_case,change):
    graph,construction,_=basf_case
    changed=deepcopy(construction)
    op=next(o for o in changed['operations'] if o['new']=='EUR 500.000.000')
    if change=='edition': op['basis']['source_sha256']='0'*64
    elif change=='quote': op['basis']['quote']='EUR 600.000.000'
    else: op['new']='EUR 600.000.000'
    with pytest.raises(ValueError,match='edition|quote|replacement'):
        basf.as_assembly(graph,changed)


def test_basf_replacement_across_lines_preserves_suffix_and_true_source():
    from legalmath.prospectus.successor.contracts import digest
    raws=['prefix [long','placeholder] suffix','value']
    units=[{'id':str(i),'document':'d','source_sha256':'a'*64,'raw':text,'text_sha256':digest(text.encode()),
        'page':1,'bbox':[0,0,1,1],'parent':'p','language':'de','visible':True} for i,text in enumerate(raws)]
    text=raws[0]+'\n'+raws[1]+'\n'
    left,right=text.index('['),text.index(']')+1
    construction={'raw_body':text,'source_map':[{'unit':'0','start':0,'end':len(raws[0])},
        {'unit':'1','start':len(raws[0])+1,'end':len(text)-1}],
        'unit_accounting':[{'unit':str(i),'role':'BODY_CANDIDATE' if i<2 else 'OTHER_DOSSIER_SOURCE'} for i in range(3)],
        'operations':[{'start':left,'end':right,'new':'value','basis':anchor(units[2])}],
        'candidate_text':'prefix value suffix\n'}
    graph={'units':units}
    assembly=basf.as_assembly(graph,construction)
    assert [u['text'] for u in assembly['units'][:2]]==['prefix value',' suffix']
    inserted=uses(graph,{'units':assembly['units'][:2]},anchor(units[2]),roles=('UNKNOWN',))
    assert len(inserted)==1 and inserted[0]['unit']=='0' and inserted[0]['start']==7
    source=anchor(units[1],raws[1].index(' suffix'))
    assert uses(graph,assembly,source,roles=('UNKNOWN',))[0]['start']==0
    assert not uses(graph,assembly,anchor(units[1],0,12),roles=('UNKNOWN',))


def test_basf_reviewed_references_reach_p3_and_missing_target_rejects(basf_case):
    from scripts.prospectus_closure_basf import prepared_request
    from legalmath.prospectus.successor import service
    from legalmath.prospectus.successor.contracts import digest
    graph,_,_=basf_case
    root=Path(__file__).resolve().parents[2]
    request=prepared_request(root,graph)
    p1=service.seal('P1',request['bundle'],{'request':digest(request)},{'request':request,'graph':graph})
    p2=service.construction_product(p1,root)
    p3=service.interpretation_product(p1,p2)
    deps={d['id']:d for d in p3['payload']['dependencies']}
    for row in request['reference_admission']['references']:
        found=deps['reviewed-reference:'+row['id']]
        assert found['status']=='RESOLVED' and len(found['targets'])==len(row['targets'])
        assert all(key+'@'+row['from_use'] not in deps for key in row['discovery_ids'])
    assert [p3['payload']['questions'][q]['status'] for q in ('Q1','Q2')]==['UNKNOWN','UNKNOWN']
    selected=deepcopy(p2['payload'])
    missing=request['reference_admission']['references'][2]['targets'][-1]['use']
    next(u for u in selected['assembly']['units'] if u['unit']==missing)['role']='UNKNOWN'
    changed=service.seal('P2',request['bundle'],{'P1':p1['sha256']},selected)
    packet=deepcopy(request['reference_admission'])
    packet['assembly_sha256']=digest(selected['assembly'])
    with pytest.raises(ValueError,match='not operative'):
        service.interpretation_product(p1,changed,{'reference_admission':packet})
