"""Verify frozen exact expectations and reversible source maps independently."""


def verify(case,result):
    assert result['text_sha256']==case['text_sha256']
    assert result['quotation_convention']==case['quotation_convention']
    assert result['scope_admitted'] is False and result['meaning_admitted'] is False
    assert result['general_recall_established'] is False
    for key,expected in (('names','expected_names'),('uses','expected_uses')):
        rows=result[key]
        assert sorted([r['start'],r['end']] for r in rows)==sorted(case[expected]),(case['id'],key)
        for row in rows:
            a,b=row['start'],row['end'];raw=case['text'][a:b]
            assert row['raw']==raw
            assert row['label']==' '.join(raw.split())
            assert row['review_required'] is True
            assert key!='uses' or row['governing_scope'] is None
            mapping=row['normalization_map']
            assert len(mapping)==len(row['label'])
            cursor=a
            for char,(start,end) in zip(row['label'],mapping,strict=True):
                assert start==cursor<end<=b
                source=case['text'][start:end]
                assert source.isspace() if char==' ' else source==char
                cursor=end
            assert cursor==b
    assert {i['kind'] for i in result['issues']}==set(case['expected_issue_kinds']),case['id']
    names={n['id']:n for n in result['names']}
    for use in result['uses']:
        expected={k for k,n in names.items() if n['label']==use['label']}
        assert set(use['name_candidates'])==expected
    return {'status':'PASS','case':case['id'],'exact_source_and_maps':True}
