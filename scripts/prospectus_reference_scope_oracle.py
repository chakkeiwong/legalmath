"""Source/context oracle; does not import or call the candidate qualifier."""
from legalmath.prospectus.successor.contracts import digest
KEY='reference_scope_context'

def verify(actual,ordinary,products,expected):
    assert {k:v for k,v in actual.items() if k not in (KEY,'report_sha256')}=={
        k:v for k,v in ordinary.items() if k!='report_sha256'}
    assert actual['report_sha256']==digest({k:v for k,v in actual.items() if k!='report_sha256'})
    report=actual[KEY]
    assert report['products_sha256']==digest(products) and report['ordinary_answer_sha256']==digest(ordinary)
    assert report['prior_answer_preserved'] is True
    for name in ('target_resolution_established','whole_task_complete','automatic_legal_interpretation','general_recall_established'):
        assert report[name] is False
    text=products['P2']['payload']['assembly']['continuous_text']
    raw={u['id']:u for u in products['P1']['payload']['graph']['units']}
    selected={u['unit']:u for u in products['P2']['payload']['assembly']['units']}
    pieces=ordinary['definition_sources']['source_pieces']
    references=products['P3']['payload']['interpretation_input']['reference_admission']['references']
    rows=report['contexts'];assert len(rows)==len(expected['source_contexts'])
    for row,wanted in zip(rows,expected['source_contexts']):
        assert {k:row[k] for k in wanted}==wanted
        assert text[row['start']:row['end']]==row['raw']
        assert row['issues']==[] and row['target'] is None and row['review_required'] is True
        assert row['target_resolution_established'] is False
        assert row['enclosing_section_resolves_target'] is False
        assert row['overlap_establishes_target'] is False
        header=row['enclosing_header'];unit=selected[header['unit']]
        assert header in report['section_headers'] and unit['role']=='HEADER'
        assert unit['text']=='§ '+wanted['enclosing_section']
        assert text[header['start']:header['end']]==unit['text']
        assert header['section']==wanted['enclosing_section']
        assert header['context']==unit['context'] and header['document']==unit['source']['document']
        applicable=[h for h in report['section_headers'] if h['start']<row['paragraph_start']
            and h['context']==header['context'] and h['document']==header['document']]
        assert header==max(applicable,key=lambda h:h['start'])
        mapped=[];cursor=row['start']
        for index,piece in enumerate(pieces):
            left=max(piece['start'],row['start']);right=min(piece['end'],row['end'])
            if left>=right:continue
            assert left==cursor
            source=piece.get('raw_binding');anchor=None
            if source:
                assert piece['end']-piece['start']==source['end']-source['start']
                a=source['start']+left-piece['start'];b=source['start']+right-piece['start']
                anchor={k:source[k] for k in ('unit','document','source_sha256')}
                anchor.update(start=a,end=b,quote=text[left:right])
                u=raw[source['unit']]
                assert u['raw'][a:b]==anchor['quote'] and all(u[k]==anchor[k] for k in ('document','source_sha256'))
            else:assert piece['kind']=='GENERATED_SEPARATOR' and text[left:right].isspace()
            mapped.append({'piece_index':index,'selected_start':left,'selected_end':right,
                'text':text[left:right],'kind':piece['kind'],'source':anchor})
            cursor=right
        assert cursor==row['end'] and row['source_projection']==mapped
        matches=[]
        for reference in references:
            s=reference['source']
            if any(p['source'] and all(p['source'][k]==s[k] for k in ('unit','document','source_sha256'))
                and max(p['source']['start'],s['start'])<min(p['source']['end'],s['end']) for p in mapped):
                matches.append(reference['id'])
        assert row['overlapping_reviewed_references']==matches
    split=next(r for r in rows if r['paragraph_start']==8571)
    assert split['overlapping_reviewed_references']==['payment-exchange-certification']
    assert len([p for p in split['source_projection'] if p['source']])==2
    assert len([r for r in rows if r['statute']])==4
    return {'status':'PASS','source_contexts':len(rows),'explicit_statutes':4,
        'cross_page_expression_preserved':True,'complete_prior_answer_equal':True,
        'target_resolution_established':False}
