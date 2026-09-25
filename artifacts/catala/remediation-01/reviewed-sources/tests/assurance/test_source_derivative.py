import pytest
from legalmath.canonical import digest,loads,raw_digest
from legalmath.errors import LegalMathError
from legalmath.storage import Database
from legalmath.sources.intake import import_source,resolve_span
from legalmath.sources.extract import normalize_text
from legalmath.interpretation.assurance.sources import acquire_context,packet_from_context
from legalmath.interpretation.assurance.evaluation import documents,load_frozen
from legalmath.interpretation.service import Interpretations
from legalmath.interpretation.search.engine import create_search
from tests.search.test_formal import AT


@pytest.mark.parametrize('real',[False,True])
def test_exact_anchored_derivative_survives_import_and_search_creation(root,tmp_path,real):
    if real:
        study=load_frozen(root/'.localresources/interpretation-round5/public-qa-v1/frozen')
        case=next(c for c in study['cases'] if c['case_id']=='family-offices.clean')
        public={k:case[k] for k in ('roots','selected_slice','at')}
        roots=documents(public);selected=public['selected_slice']
    else:
        roots=[{'url':'https://www.sfc.hk/test/line-endings','media_type':'text/html',
                'data':b'<p>A distributor should disclose.\r\nExcept where exempt.</p>'}]
        selected='Selected disclosure'
    context=acquire_context(roots,max_depth=0);packet=packet_from_context(context,selected)
    assert any(d['text']!=normalize_text(d['text']) for d in context['documents'])
    db=Database(tmp_path);service=Interpretations(db);service.lc.register({'author':{'token':'author','roles':['author']}})
    with db.transaction() as con:
        for d in context['documents']:
            import_source(db,con,'d'+digest(d['url'])[:12],d['data'],d['media_type'],d['url'],AT,
                retained_text=d['text'],extractor=d['primary_method'],preserve_retained_text=True)
        assert all(resolve_span(db,con,u['span'])==u['text'] for u in packet['units'])
    assert create_search(service,'author','exact-source',packet)['run_id']


def test_default_import_still_normalizes_and_exact_mode_requires_derivative_identity(tmp_path):
    db=Database(tmp_path);text='A\r\nB';raw=text.encode()
    with db.transaction() as con:
        result=import_source(db,con,'source',raw,'text/plain','https://www.sfc.hk/test/source',AT,
            retained_text=text,extractor={'name':'test'})
        assert db.get(con,result['derivative_hash'])['text_sha256']==raw_digest(b'A\nB')
        with pytest.raises(LegalMathError):
            import_source(db,con,'source',raw,'text/plain','https://www.sfc.hk/test/source',AT,
                retained_text=text,preserve_retained_text=True)
