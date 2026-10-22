"""Independent source-span/answer checks; never invokes the candidate scanner."""
from copy import deepcopy
from legalmath.prospectus.successor.contracts import digest
KEY='paragraph_reference_discovery'

def verify(actual,ordinary,products,expected):
    assert {k:v for k,v in actual.items() if k not in (KEY,'report_sha256')}=={k:v for k,v in ordinary.items() if k!='report_sha256'}
    assert actual['report_sha256']==digest({k:v for k,v in actual.items() if k!='report_sha256'})
    report=actual[KEY];discovery=report['discovery'];text=products['P2']['payload']['assembly']['continuous_text']
    assert report['products_sha256']==digest(products) and report['ordinary_answer_sha256']==digest(ordinary)
    assert report['whole_task_complete'] is False and report['target_resolution_established'] is False
    assert report['automatic_legal_interpretation'] is False and report['prior_answer_preserved'] is True
    assert discovery['text_sha256']==digest(text.encode()) and discovery['issues']==[]
    assert discovery['general_recall_established'] is False and discovery['target_resolution_established'] is False
    candidates=discovery['candidates'];assert len(candidates)==report['candidate_count']==len(expected['source_expressions'])
    assert len(report['source_candidates'])==len(candidates)
    pieces=ordinary['definition_sources']['source_pieces']
    refs=products['P3']['payload']['interpretation_input']['reference_admission']['references']
    for c,source,wanted in zip(candidates,report['source_candidates'],expected['source_expressions']):
        assert {k:c[k] for k in wanted}==wanted and text[c['start']:c['end']]==c['raw']
        assert c['syntax_complete'] is True and c['target'] is None and c['review_required'] is True
        assert [t['value'] for t in c['tokens']]==[v for path in wanted['paths'] for v in path]
        previous=c['start']
        for t in c['tokens']:
            assert previous<=t['start']<t['end']<=c['end'] and text[t['start']:t['end']]==t['raw']
            assert t['raw'].replace('[','').replace(']','').replace('(','').replace(')','').strip()==t['value']
            previous=t['end']
        mapped=[]
        for i,p in enumerate(pieces):
            a,b=max(p['start'],c['start']),min(p['end'],c['end'])
            if a>=b:continue
            raw=p.get('raw_binding');clipped=None
            if raw and raw.get('unit') and p['end']-p['start']==raw['end']-raw['start']:
                delta=raw['start']-p['start']
                clipped={'unit':raw['unit'],'document':raw['document'],'source_sha256':raw['source_sha256'],
                    'start':a+delta,'end':b+delta,'quote':text[a:b]}
                assert raw['quote'][a-p['start']:b-p['start']]==text[a:b]
            mapped.append({'index':i,'piece':p,'selected_start':a,'selected_end':b,'clipped_source':clipped})
        assert {k:source[k] for k in c}==c and source['source_pieces']==mapped
        matching=[]
        for r in refs:
            s=r['source']
            if any(m['clipped_source'] and m['clipped_source']['unit']==s['unit'] and
                m['clipped_source']['start']<s['end'] and s['start']<m['clipped_source']['end'] for m in mapped):matching.append(r['id'])
        assert source['overlapping_reviewed_references']==matching and source['overlap_establishes_target'] is False
    return {'status':'PASS','source_expressions':len(candidates),'complete_prior_answer_equal':True,'independent_source_mapping':True}
