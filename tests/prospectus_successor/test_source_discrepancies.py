"""Source disagreements are retained as supplied, unresolved paired evidence."""
from copy import deepcopy
from pathlib import Path
import pytest
from legalmath.prospectus.successor import service, source_discrepancies
from legalmath.prospectus.successor.contracts import digest
from test_successor import request
from test_report_scope import REVIEW

FIXTURES=Path(__file__).parent/'fixtures/bes_note46'
TEXT={lang:(FIXTURES/(lang+'.txt')).read_text() for lang in ('en','pt')}

def fixture(tmp_path, texts=None):
    texts=texts or TEXT
    req=request(tmp_path,['placeholder']);req.pop('assembly');req.pop('scope')
    docs=[]
    for lang,text in texts.items():
        path=tmp_path/(lang+'.txt');path.write_text(text)
        docs.append({'id':lang,'path':str(path),'sha256':digest(path.read_bytes()),
            'format':'text','language':lang,'authority':'Development source-text diagnostic'})
    req['bundle']['documents']=docs
    req['bundle']['dependencies']=[{'id':'original-unresolved','questions':['Q1','Q2'],'status':'UNRESOLVED'}]
    p1=service.source_product(req,tmp_path);graph=p1['payload']['graph']
    req['source_report_readings']={'version':'source-report-readings.v1','graph_sha256':digest(graph),'review':REVIEW,
        'reports':[{'id':d['id'],'document':d['id'],'source_sha256':d['sha256'],
                    'pages':[{'page':1,'mode':'raw'}],'text_sha256':digest(texts[d['id']].encode())} for d in docs]}
    p1=service.source_product(req,tmp_path);p2=service.construction_product(p1,tmp_path)
    selected=p2['payload']['source_report_readings'];sides=[]
    for r in selected['reports']:
        text=r['text'];lang=r['id']
        start=text.index('On the 9th of January 2009' if lang=='en' else 'Em 9 de Janeiro de 2009')
        end=text.index('•',start)
        while text[end-1].isspace():end-=1
        sides.append({'reading':lang,'reading_sha256':r['sha256'],'language':lang,
            'context':{'start':start,'end':end,'quote':text[start:end]}})
    packet={'version':'source-discrepancies.v1','graph_sha256':digest(graph),'readings_sha256':digest(selected),
        'review':REVIEW,'discrepancies':[{'id':'note46','profile':source_discrepancies.PROFILE,'sides':sides}]}
    return req,p1,p2,packet

def products(p1,p2,packet=None):
    p3=service.interpretation_product(p1,p2,{'source_discrepancies':packet} if packet is not None else None)
    return {'P1':p1,'P2':p2,'P3':p3,'P4':service.law_product(p1,p3),
            'P5':service.financial_product(p1,p2,p3)}

def reseal(p):
    return {
        **p,'sha256':digest({k:v for k,v in p.items() if k!='sha256'})}

@pytest.mark.parametrize('mode',['current','frozen'])
def test_current_and_saved_answer_preserve_pair_without_amount_choice(tmp_path,mode):
    req,p1,p2,packet=fixture(tmp_path)
    before=service.consume(products(p1,p2),tmp_path,mode=mode,include_artifacts=True)
    after=service.consume(products(p1,p2,packet),tmp_path,mode=mode,include_artifacts=True)
    item,=after['source_discrepancies']
    assert item['status']=='UNRESOLVED_SOURCE_DISCREPANCY'
    assert [r['monetary_wording']['quote'] for r in item['sides']]==['euro 1 500 000 million','1,5 mil milhões de euros']
    assert all(s['context']['source_characters'] for s in item['sides'])
    assert item['resolved_amount'] is None and item['controlling_edition'] is None
    assert not item['automatic_discovery'] and not item['financial_calculation_authorized']
    assert not after['independent_legal_acceptance'] and not after['may_execute_transaction']
    assert after['mode']=='ASSISTED'
    assert all(after[k]==before[k] for k in ('questions','dependencies','assembly','source_map'))
    assert 'source_discrepancies' not in before
    req['source_discrepancies']=packet
    assert service.assess(req,tmp_path)['source_discrepancies']==after['source_discrepancies']

@pytest.mark.parametrize('mutation',['version','graph','readings','profile','empty','duplicate_row','missing_side',
    'duplicate_side','same_document','language','reading','quote','interval','abbreviated','wrong_event',
    'resolved_amount','controlling_edition','status','blank_review'])
def test_adverse_packet_refuses_public_interpretation(tmp_path,mutation):
    _,p1,p2,packet=fixture(tmp_path);row=packet['discrepancies'][0];side=row['sides'][0]
    if mutation=='version':packet['version']='source-discrepancies.v9'
    elif mutation in ('graph','readings'):packet[mutation+'_sha256']='0'*64
    elif mutation=='profile':row['profile']='all-translations'
    elif mutation=='empty':packet['discrepancies']=[]
    elif mutation=='duplicate_row':packet['discrepancies'].append(deepcopy(row))
    elif mutation=='missing_side':row['sides'].pop()
    elif mutation=='duplicate_side':row['sides'][1]=deepcopy(side)
    elif mutation=='same_document':row['sides'][1].update(reading=side['reading'],reading_sha256=side['reading_sha256'])
    elif mutation=='language':side['language']='pt'
    elif mutation=='reading':side['reading_sha256']='0'*64
    elif mutation=='quote':side['context']['quote']+=' changed'
    elif mutation=='interval':side['context']['start']=True
    elif mutation=='abbreviated':
        r=p2['payload']['source_report_readings']['reports'][0];text=r['text']
        a=text.index('euro 1 500 000 million');side['context']={'start':a,'end':a+len('euro 1 500 000 million'),'quote':'euro 1 500 000 million'}
    elif mutation=='wrong_event':
        text=p2['payload']['source_report_readings']['reports'][0]['text'];a=text.index('Capital increase:')
        side['context']={'start':a,'end':len(text),'quote':text[a:]}
    elif mutation=='blank_review':packet['review']={**REVIEW,'reason':''}
    else:row[mutation]='asserted correction'
    with pytest.raises(ValueError):products(p1,p2,packet)

@pytest.mark.parametrize('mutation',['event','amount','placement','heading','additional_sentence'])
def test_altered_source_does_not_match_inspected_full_context(tmp_path,mutation):
    texts=deepcopy(TEXT)
    if mutation=='event':texts['en']=texts['en'].replace('3 year','5 year',1)
    elif mutation=='amount':texts['en']=texts['en'].replace('1 500 000 million','1 500 million',1)
    elif mutation=='placement':texts['en']=texts['en'].replace('80%','20%',1)
    elif mutation=='heading':texts['en']=texts['en'].replace('Note 46 -','Note 47 -',1)
    else:texts['en']=texts['en'].replace('euro 1,900 million.','euro 1,900 million. This corrects an earlier figure.',1)
    _,p1,p2,packet=fixture(tmp_path,texts)
    with pytest.raises(ValueError,match='Complete inspected'):products(p1,p2,packet)

@pytest.mark.parametrize('mode',['current','frozen'])
@pytest.mark.parametrize('mutation',['amount','missing','unbound'])
def test_resealed_saved_result_cannot_invent_or_drop_discrepancy(tmp_path,mode,mutation):
    _,p1,p2,packet=fixture(tmp_path);ps=products(p1,p2,packet)
    p3=deepcopy(ps['P3'])
    if mutation=='amount':p3['payload']['source_discrepancies']['discrepancies'][0]['resolved_amount']='1500000000'
    elif mutation=='missing':del p3['payload']['source_discrepancies']
    else:p3['payload']['interpretation_input']=None
    p3=reseal(p3);ps['P3']=p3
    ps['P4']=service.law_product(p1,p3);ps['P5']=service.financial_product(p1,p2,p3)
    with pytest.raises(ValueError):service.consume(ps,tmp_path,mode=mode)

@pytest.mark.parametrize('mutation',['language','character','omitted','duplicate'])
def test_rebound_character_map_still_requires_original_language_and_text(tmp_path,mutation):
    _,p1,p2,packet=fixture(tmp_path);graph=deepcopy(p1['payload']['graph']);selected=deepcopy(p2['payload']['source_report_readings'])
    reading=selected['reports'][0];start=packet['discrepancies'][0]['sides'][0]['context']['start']
    index=next(i for i,c in enumerate(reading['characters']) if c['output']==start)
    if mutation=='language':graph['units'][0]['language']='pt'
    elif mutation=='character':reading['characters'][index]['character']='?'
    elif mutation=='omitted':reading['characters'].pop(index)
    else:reading['characters'].insert(index,deepcopy(reading['characters'][index]))
    reading['sha256']=digest({k:v for k,v in reading.items() if k!='sha256'})
    selected['graph_sha256']=digest(graph);packet['graph_sha256']=digest(graph);packet['readings_sha256']=digest(selected)
    packet['discrepancies'][0]['sides'][0]['reading_sha256']=reading['sha256']
    with pytest.raises(ValueError):source_discrepancies.admit(graph,selected,packet)

def test_heading_requires_source_characters_too(tmp_path):
    _,p1,p2,packet=fixture(tmp_path)
    selected=deepcopy(p2['payload']['source_report_readings']);reading=selected['reports'][0]
    heading=reading['text'].index('Note 46 - SUBSEQUENT EVENTS')
    reading['characters']=[c for c in reading['characters'] if c['output']!=heading]
    reading['sha256']=digest({k:v for k,v in reading.items() if k!='sha256'})
    packet['readings_sha256']=digest(selected)
    packet['discrepancies'][0]['sides'][0]['reading_sha256']=reading['sha256']
    with pytest.raises(ValueError,match='Unmapped discrepancy'):
        source_discrepancies.admit(p1['payload']['graph'],selected,packet)

def test_frozen_consumer_rejects_rebound_false_selected_page(tmp_path):
    _,p1,p2,packet=fixture(tmp_path)
    changed=deepcopy(p2);selected=changed['payload']['source_report_readings']
    reading=selected['reports'][0];reading['pages']=[{'page':9,'mode':'raw'}]
    reading['sha256']=digest({k:v for k,v in reading.items() if k!='sha256'})
    packet['readings_sha256']=digest(selected)
    packet['discrepancies'][0]['sides'][0]['reading_sha256']=reading['sha256']
    changed=reseal(changed)
    with pytest.raises(ValueError):
        service.consume(products(p1,changed,packet),tmp_path,mode='frozen')
