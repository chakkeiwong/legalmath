"""Check standalone section coverage from independently frozen source readings."""
from collections import Counter
from legalmath.prospectus.successor.contracts import digest
from scripts.prospectus_reference_address_projection_oracle import verify_projection
KEY='standalone_sections'

def verify(actual,old,products,expected):
    assert {k:v for k,v in actual.items() if k not in (KEY,'report_sha256')}=={k:v for k,v in old.items() if k!='report_sha256'}
    assert actual['report_sha256']==digest({k:v for k,v in actual.items() if k!='report_sha256'})
    report=actual[KEY]
    assert report['products_sha256']==digest(products) and report['ordinary_answer_sha256']==digest(old)
    assert report['prior_answer_preserved'] is True and report['original_semantic_targets_preserved'] is True
    for flag in ('whole_task_complete','legal_truth_established','general_recall_established','automatic_legal_interpretation'):
        assert report[flag] is False
    assembly=products['P2']['payload']['assembly'];text=assembly['continuous_text']
    pieces=old['definition_sources']['source_pieces']
    raw={u['id']:u for u in products['P1']['payload']['graph']['units']}
    units={u['unit']:u for u in assembly['units']}
    assert [{k:s[k] for k in ('start','end','raw')} for s in report['signs']]==expected['signs']
    assert Counter(s['classification'] for s in report['signs'])=={
        'SECTION_HEADER':15,'PARAGRAPH_CONTEXT':16,'STANDALONE_EXPRESSION':19}
    headers=old['reference_scope_context']['section_headers']
    covered=old['reference_scope_context']['contexts']
    for sign in report['signs']:
        a=sign['start'];assert text[a:sign['end']]==sign['raw']
        if sign['classification']=='SECTION_HEADER':assert any(h['start']<=a<h['end'] for h in headers)
        elif sign['classification']=='PARAGRAPH_CONTEXT':assert any(c['start']<=a<c['end'] for c in covered)
        else:
            matches=[r for r in report['references'] if r['start']<=a<r['end']]
            assert len(matches)==1 and sign['expression_start']==matches[0]['start']
    assert len(report['references'])==expected['logical_expressions']==18
    targets={r['section']:r for r in expected['targets']}
    for row,wanted in zip(report['references'],expected['references']):
        assert {k:row[k] for k in wanted}==wanted
        assert row['issues']==[] and row['review_required'] is True
        assert row['legal_meaning_established'] is False and row['historical_application_established'] is False
        verify_projection(row['source_projection'],row['start'],row['end'],text,pieces,raw)
        if wanted['statute']:
            assert row['status']=='EXTERNAL_STATUTE' and row['targets']==[]
            numbers=['18','5'] if row['start']==35946 else (['15'] if row['start']==34106 else ['5'])
            assert [m['number'] for m in row['members']]==numbers
        else:
            assert row['status']=='STRUCTURAL_SECTION' and len(row['targets'])==1
            node=row['targets'][0];wanted_target=targets[wanted['section']]
            assert {k:node[k] for k in wanted_target}==wanted_target and node in report['section_index']
            assert node['legal_meaning_established'] is False
            assert node['context']==row['enclosing_header']['context']
            assert node['document']==row['enclosing_header']['document']
            verify_projection(node['source_projection'],node['start'],node['end'],text,pieces,raw,assembly['operations'])
            assert node['unknown_source_units']==sorted({p['source']['unit'] for p in node['source_projection']
                if p['source'] and units[p['source']['unit']]['role']=='UNKNOWN'})
    return {'status':'PASS','section_signs':50,'headings':15,'paragraph_signs':16,
        'standalone_signs':19,'logical_expressions':18,'structural_expressions':15,
        'external_statutory_expressions':3,'complete_prior_answer_equal':True,'historical_application_established':False}
