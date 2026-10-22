"""Archive dates are conditional source observations, not publication evidence."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from pypdf import PdfWriter
from pypdf.generic import NameObject, DictionaryObject, DecodedStreamObject

from legalmath.prospectus.successor import archive_observations, report_scope, service
from legalmath.prospectus.successor.contracts import VERSION, digest

REVIEW={'reviewer':'synthetic-reader','kind':'DEVELOPMENT','reason':'Synthetic archive controls'}
CAPTURE='2015-04-24T13:29:17Z'
RETRIEVED='2026-10-12T18:16:29Z'
URL='http://issuer.example/report.pdf'


def fixture(tmp_path, *, query='2016-01-01T00:00:00Z', known='2026-10-13T00:00:00Z', with_report=False):
    writer=PdfWriter()
    page=writer.add_blank_page(300,300)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    stream=DecodedStreamObject()
    stream.set_data(b'BT /F1 12 Tf 20 240 Td (Synthetic source report.) Tj ET')
    page[NameObject('/Contents')]=writer._add_object(stream)
    with (tmp_path/'source.pdf').open('wb') as output: writer.write(output)
    raw=(tmp_path/'source.pdf').read_bytes()
    (tmp_path/'archive.pdf').write_bytes(raw)
    header=('HTTP/1.1 200 OK\r\nDate: Mon, 12 Oct 2026 18:14:55 GMT\r\n'
        'Content-Type: application/pdf\r\nContent-Length: '+str(len(raw))+'\r\n'
        'Memento-Datetime: Fri, 24 Apr 2015 13:29:17 GMT\r\n'
        'Link: <'+URL+'>; rel="original", <https://arquivo.pt/>; rel="timegate"\r\n\r\n')
    (tmp_path/'headers').write_bytes(header.encode())
    record={'originalURL':URL,'tstamp':'20150424132917','mimeType':'application/pdf','statusCode':200,
        'linkToOriginalFile':'https://arquivo.pt/noFrame/replay/20150424132917id_/'+URL,'contentLength':7}
    (tmp_path/'index.json').write_text(json.dumps({'response_items':[record]}))
    binding=lambda name:{'path':name,'sha256':digest((tmp_path/name).read_bytes())}
    bundle={'instrument_id':'synthetic','purpose':'review','issue_date':'2011-07-15T00:00:00Z',
        'effective_at':'2011-07-15T00:00:00Z','known_at':known,
        'documents':[{'id':'d','path':'source.pdf','sha256':digest(raw),'language':'en','authority':'Synthetic source',
            'document_date':'2011-01-01T00:00:00Z','known_from':'2011-01-01T00:00:00Z'}]}
    packet={'version':archive_observations.VERSION,'query_at':query,'review':REVIEW,'captures':[
        {'id':'capture','document':'d','source_sha256':digest(raw),'original_url':URL,'capture_at':CAPTURE,
         'retrieved_at':RETRIEVED,'index':binding('index.json'),'record_index':0,
         'headers':binding('headers'),'content':binding('archive.pdf')}]}
    req={'version':VERSION,'bundle':bundle,'archive_observations':packet}
    if with_report:
        graph=service.source_product(req,tmp_path)['payload']['graph']
        text='\n'.join(u['raw'] for u in graph['units'])
        admission={'version':'source-report-readings.v1','graph_sha256':digest(graph),'review':REVIEW,
            'reports':[{'id':'r','document':'d','source_sha256':digest(raw),'pages':[{'page':1,'mode':'raw'}],'text_sha256':digest(text.encode())}]}
        req['source_report_readings']=admission
        selected=report_scope.readings(graph,admission)
        req['source_report_scope']={'version':'source-report-scope.v1','readings_sha256':digest(selected),'review':REVIEW,
            'reports':[{'id':'r','reading_sha256':selected['reports'][0]['sha256'],
                'facts':{k:{'status':'UNKNOWN','reason':'Synthetic report supplies no such fact'} for k in report_scope.FACTS}}]}
    return req


def products(req,root):
    p1=service.source_product(req,root)
    p2=service.construction_product(p1,root)
    p3=service.interpretation_product(p1,p2)
    return {'P1':p1,'P2':p2,'P3':p3,'P4':service.law_product(p1,p3),'P5':service.financial_product(p1,p2,p3)}


@pytest.mark.parametrize('query,known,expected',[
    ('2011-07-15T00:00:00Z','2026-10-13T00:00:00Z','NOT_ESTABLISHED_BY_THIS_CAPTURE'),
    ('2015-04-24T13:29:16Z','2026-10-13T00:00:00Z','NOT_ESTABLISHED_BY_THIS_CAPTURE'),
    (CAPTURE,'2026-10-13T00:00:00Z','ARCHIVE_RECORDED_BY_QUERY_DATE'),
    ('2016-01-01T00:00:00Z',RETRIEVED,'ARCHIVE_RECORDED_BY_QUERY_DATE'),
    ('2016-01-01T00:00:00Z','2026-10-12T00:00:00Z','EVIDENCE_NOT_YET_KNOWN')])
def test_archive_observations_actual_consumer_date_boundaries(tmp_path,query,known,expected):
    req=fixture(tmp_path,query=query,known=known,with_report=True)
    baseline=deepcopy(req)
    baseline.pop('archive_observations')
    before=service.assess(baseline,tmp_path)
    result=service.consume(products(req,tmp_path),tmp_path,mode='current')
    observation,=result['source_archive_observations']['observations']
    assert observation['as_of_query']==expected
    assert observation['archive_observed_by']==CAPTURE and observation['evidence_known_from']==RETRIEVED
    assert observation['publication_date']==observation['edition_authenticity']=='UNKNOWN'
    assert not observation['earlier_absence_established'] and not observation['legal_availability_established']
    assert result['source_reports'][0]['archive_observations']==[observation]
    assert [{k:v for k,v in r.items() if k!='archive_observations'} for r in result['source_reports']]==before['source_reports']
    assert result['questions']==before['questions'] and result['source_graph_sha256']==before['source_graph_sha256']
    assert result['mode']=='ASSISTED' and not result['may_execute_transaction']


@pytest.mark.parametrize('change,reason',[
    ('original','Archive evidence bytes changed'),('content','Archive evidence bytes changed'),
    ('index','Archive evidence bytes changed'),('headers','Archive evidence bytes changed'),
    ('wrong_content','complete source bytes'),('html','not a PDF'),('memento','Memento date differs'),
    ('missing_memento','one Memento'),('duplicate_header','one Memento'),('wrong_url','URL differs'),
    ('wrong_status','HTTP 200'),('length','content length'),('retrieval','times disagree'),
    ('naive','timezone'),('bad_date','Invalid archive HTTP date'),('index_url','index URL'),
    ('index_html','index URL'),('index_duplicate','ambiguous'),('index_date','index URL'),
    ('index_replay','original-file URL'),('record_index','Exact archive index record'),
    ('source_edition','source edition'),('path_escape','escapes declared root'),
    ('unknown_version','Unsupported archive'),('duplicate_id','Distinct archive'),('empty','One to 64'),
    ('malformed_index','must be an object'),('malformed_record','Exact archive index'),('microsecond','index URL')])
def test_archive_observations_adverse_binding_and_metadata(tmp_path,change,reason):
    req=fixture(tmp_path)
    packet=req['archive_observations']
    row=packet['captures'][0]
    def update_file(key,raw):
        p=tmp_path/row[key]['path']
        p.write_bytes(raw)
        row[key]['sha256']=digest(raw)
    if change in {'original','content','index','headers'}:
        p=tmp_path/('source.pdf' if change=='original' else row[change]['path'])
        p.write_bytes(p.read_bytes()+b'x')
    elif change=='wrong_content': update_file('content',(tmp_path/'archive.pdf').read_bytes()+b'x')
    elif change in {'html','memento','missing_memento','duplicate_header','wrong_url','wrong_status','length','bad_date'}:
        text=(tmp_path/'headers').read_text()
        if change=='html': text=text.replace('application/pdf','text/html')
        elif change=='memento': text=text.replace('Fri, 24 Apr 2015','Sat, 25 Apr 2015')
        elif change=='missing_memento': text='\n'.join(s for s in text.splitlines() if not s.startswith('Memento-'))+'\n\n'
        elif change=='duplicate_header': text=text.replace('Memento-Datetime:', 'Memento-Datetime: Fri, 24 Apr 2015 13:29:17 GMT\nMemento-Datetime:')
        elif change=='wrong_url': text=text.replace(URL,'http://issuer.example/other.pdf')
        elif change=='wrong_status': text=text.replace('200 OK','404 Not Found')
        elif change=='length': text=text.replace(str((tmp_path/'archive.pdf').stat().st_size),'1')
        elif change=='bad_date': text=text.replace('Mon, 12 Oct 2026 18:14:55 GMT','unknown')
        update_file('headers',text.encode())
    elif change in {'index_url','index_html','index_duplicate','index_date','index_replay'}:
        index=json.loads((tmp_path/'index.json').read_text())
        record=index['response_items'][0]
        if change=='index_url': record['originalURL']=URL+'?issuer=other'
        elif change=='index_html': record['mimeType']='text/html'
        elif change=='index_duplicate': index['response_items'].append(deepcopy(record))
        elif change=='index_date': record['tstamp']='20110424132917'
        elif change=='index_replay': record['linkToOriginalFile']=record['linkToOriginalFile'].replace('arquivo.pt','example.com')
        update_file('index',json.dumps(index).encode())
    elif change=='retrieval': row['retrieved_at']='2014-01-01T00:00:00Z'
    elif change=='naive': row['retrieved_at']='2026-10-12T18:16:29'
    elif change=='record_index': row['record_index']=True
    elif change=='source_edition': row['source_sha256']='0'*64
    elif change=='path_escape': row['content']['path']='../outside.pdf'
    elif change=='unknown_version': packet['version']='unknown'
    elif change=='duplicate_id': packet['captures'].append(deepcopy(row))
    elif change=='empty': packet['captures']=[]
    elif change=='malformed_index': update_file('index',b'[]')
    elif change=='malformed_record': update_file('index',b'{"response_items":[null]}')
    elif change=='microsecond': row['capture_at']='2015-04-24T13:29:17.001Z'
    with pytest.raises(ValueError,match=reason):
        archive_observations.admit(req['bundle'],packet,tmp_path)


def test_archive_observations_changed_after_p2_rejected_in_frozen_consumer(tmp_path):
    req=fixture(tmp_path)
    retained=products(req,tmp_path)
    (tmp_path/'headers').write_bytes((tmp_path/'headers').read_bytes()+b'x')
    with pytest.raises(ValueError,match='evidence bytes changed'):
        service.consume(retained,tmp_path)


@pytest.mark.parametrize('has_request',[False,True])
def test_archive_observations_resealed_p2_forgery_rejected(tmp_path,has_request):
    req=fixture(tmp_path)
    if not has_request: req.pop('archive_observations')
    p=products(req,tmp_path)
    payload=deepcopy(p['P2']['payload'])
    if has_request: payload['archive_observations']['observations'][0]['as_of_query']='PUBLICATION_PROVED'
    else: payload['archive_observations']={'version':'invented'}
    p['P2']=service.seal('P2',req['bundle'],{'P1':p['P1']['sha256']},payload)
    with pytest.raises(ValueError,match='Archive observation'):
        service.consume(p,tmp_path)


def test_archive_observations_last_modified_is_not_capture_authority(tmp_path):
    req=fixture(tmp_path)
    row=req['archive_observations']['captures'][0]
    raw=(tmp_path/'headers').read_bytes().replace(b'Content-Type:',b'Last-Modified: Mon, 01 Jan 2001 00:00:00 GMT\r\nContent-Type:')
    (tmp_path/'headers').write_bytes(raw)
    row['headers']['sha256']=digest(raw)
    result=service.assess(req,tmp_path)
    assert result['source_archive_observations']['observations'][0]['archive_observed_by']==CAPTURE


def test_archive_observations_redirect_blocks_and_known_timezones(tmp_path):
    req=fixture(tmp_path,query='2015-04-24T21:29:17+08:00')
    row=req['archive_observations']['captures'][0]
    raw=b'HTTP/1.1 302 Found\r\nLocation: https://arquivo.pt\r\n\r\n'+(tmp_path/'headers').read_bytes()
    (tmp_path/'headers').write_bytes(raw)
    row['headers']['sha256']=digest(raw)
    result=service.assess(req,tmp_path)
    assert result['source_archive_observations']['observations'][0]['as_of_query']=='ARCHIVE_RECORDED_BY_QUERY_DATE'


def textsearch_fixture(tmp_path, **kwargs):
    req = fixture(tmp_path, **kwargs)
    packet = req['archive_observations']
    packet['version'] = archive_observations.TEXTSEARCH_VERSION
    row = packet['captures'][0]
    index = json.loads((tmp_path / 'index.json').read_text())
    index['response_items'][0].pop('statusCode')
    index.update(linkToService='https://arquivo.pt', request_parameters={'q': 'synthetic report'})
    (tmp_path / 'index.json').write_text(json.dumps(index))
    row['index']['sha256'] = digest((tmp_path / 'index.json').read_bytes())
    memento = 'https://www.issuer.example/report.pdf'
    headers = (tmp_path / 'headers').read_bytes().replace(URL.encode(), memento.encode())
    (tmp_path / 'headers').write_bytes(headers)
    row['headers']['sha256'] = digest(headers)
    row['memento_original_url'] = memento
    replay = index['response_items'][0]['linkToOriginalFile']
    receipt = {'requests': [{'argv': ['curl', '--output', 'archive.pdf', '--dump-header', 'headers', replay],
        'http_status': 200, 'curl_exit_code': 0, 'bytes': (tmp_path / 'archive.pdf').stat().st_size,
        'sha256': row['content']['sha256'], 'headers_sha256': row['headers']['sha256']}]}
    (tmp_path / 'receipt.json').write_text(json.dumps(receipt))
    row['receipt'] = {'path': 'receipt.json', 'sha256': digest((tmp_path / 'receipt.json').read_bytes())}
    row['receipt_request_index'] = 0
    outputs = {row[k]['path']: row[k]['sha256'] for k in ('index', 'headers', 'content', 'receipt')}
    (tmp_path / 'outputs.json').write_text(json.dumps(outputs))
    row['retained_outputs'] = {'path': 'outputs.json', 'sha256': digest((tmp_path / 'outputs.json').read_bytes())}
    event = {'kind': 'RECORD', 'at': RETRIEVED, 'attempt': str(tmp_path),
             'outputs_sha256': row['retained_outputs']['sha256']}
    event['sha256'] = digest(json.dumps(event, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())
    (tmp_path / 'event.json').write_text(json.dumps(event))
    row['retrieval_record'] = {'path': 'event.json', 'sha256': digest((tmp_path / 'event.json').read_bytes())}
    return req


def reseal_textsearch_files(req, root):
    """Reseal diagnostic evidence so semantic controls do not just test stale hashes."""
    row = req['archive_observations']['captures'][0]
    for key in ('index', 'headers', 'content', 'receipt'):
        row[key]['sha256'] = digest((root / row[key]['path']).read_bytes())
    outputs = {row[k]['path']: row[k]['sha256'] for k in ('index', 'headers', 'content', 'receipt')}
    (root / 'outputs.json').write_text(json.dumps(outputs))
    row['retained_outputs']['sha256'] = digest((root / 'outputs.json').read_bytes())
    event = json.loads((root / 'event.json').read_text())
    event['outputs_sha256'] = row['retained_outputs']['sha256']
    event.pop('sha256')
    event['sha256'] = digest(json.dumps(event, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())
    (root / 'event.json').write_text(json.dumps(event))
    row['retrieval_record']['sha256'] = digest((root / 'event.json').read_bytes())


@pytest.mark.parametrize('query,known,expected', [
    ('2015-04-24T13:29:16Z', RETRIEVED, 'NOT_ESTABLISHED_BY_THIS_CAPTURE'),
    (CAPTURE, RETRIEVED, 'ARCHIVE_RECORDED_BY_QUERY_DATE'),
    ('2015-04-25T00:00:00Z', RETRIEVED, 'ARCHIVE_RECORDED_BY_QUERY_DATE'),
    (CAPTURE, '2026-10-12T18:16:28Z', 'EVIDENCE_NOT_YET_KNOWN'),
])
def test_archive_observations_textsearch_actual_consumer(tmp_path, query, known, expected):
    req = textsearch_fixture(tmp_path, query=query, known=known, with_report=True)
    baseline = deepcopy(req)
    baseline.pop('archive_observations')
    before = service.consume(products(baseline, tmp_path), tmp_path)
    actual = service.consume(products(req, tmp_path), tmp_path)
    row, = actual['source_archive_observations']['observations']
    assert row['as_of_query'] == expected
    assert row['archive_index_http_status'] == 'UNKNOWN' and row['replay_http_status'] == 200
    assert row['original_url'] == URL and row['memento_original_url'] == 'https://www.issuer.example/report.pdf'
    assert row['original_url_equivalence'] == 'NOT_ESTABLISHED'
    assert row['source_origin'] == 'BYTE_EQUAL_SUPPLIED_SOURCE'
    assert row['independent_source_comparison'] is False
    assert row['publication_date'] == row['edition_authenticity'] == 'UNKNOWN'
    assert row['evidence_known_from_basis'] == 'SUPPLIED_RETAINED_OUTPUTS_RECORD_UPPER_BOUND'
    assert not row['legal_availability_established'] and not row['earlier_absence_established']
    assert actual['source_reports'][0]['archive_observations'] == [row]
    assert [{k: v for k, v in r.items() if k != 'archive_observations'} for r in actual['source_reports']] == before['source_reports']
    assert actual['questions'] == before['questions']
    assert not actual['may_execute_transaction'] and not actual['independent_legal_acceptance']


@pytest.mark.parametrize('change,reason', [
    ('index_status', 'index URL'), ('null_status', 'index URL'), ('service', 'text-search service'),
    ('query', 'search query'), ('other_host', 'URL variation'), ('other_path', 'URL variation'),
    ('other_query', 'URL variation'), ('port', 'Unsupported text-search'),
    ('credential', 'Unsupported text-search'), ('fragment', 'Unsupported text-search'),
    ('receipt_url', 'receipt differs'), ('receipt_status', 'receipt differs'),
    ('receipt_exit', 'receipt differs'), ('receipt_size', 'receipt differs'),
    ('receipt_hash', 'receipt differs'), ('receipt_headers', 'receipt differs'),
    ('receipt_output', 'path differs'), ('receipt_header_path', 'path differs'),
    ('duplicate_output', 'path missing or ambiguous'), ('request_index', 'acquisition request'),
    ('record_time', 'upper-bound record'), ('record_kind', 'upper-bound record'),
    ('record_attempt', 'attempt differs'), ('record_hash', 'upper-bound record'),
    ('missing_output', 'outputs do not bind'), ('altered_after_binding', 'bytes changed'),
    ('duplicate_original', 'URL differs'), ('changed_pdf', 'complete source bytes'),
])
def test_archive_observations_textsearch_semantic_corruption(tmp_path, change, reason):
    req = textsearch_fixture(tmp_path)
    row = req['archive_observations']['captures'][0]
    index = json.loads((tmp_path / 'index.json').read_text())
    receipt = json.loads((tmp_path / 'receipt.json').read_text())
    event = json.loads((tmp_path / 'event.json').read_text())
    request = receipt['requests'][0]
    headers = (tmp_path / 'headers').read_text()
    if change == 'index_status': index['response_items'][0]['statusCode'] = 404
    elif change == 'null_status': index['response_items'][0]['statusCode'] = None
    elif change == 'service': index['linkToService'] = 'https://other.example'
    elif change == 'query': index['request_parameters'] = {}
    elif change in {'other_host', 'other_path', 'other_query', 'port', 'credential', 'fragment'}:
        wrong = {'other_host': 'https://other.example/report.pdf', 'other_path': 'https://issuer.example/other.pdf',
                 'other_query': 'https://issuer.example/report.pdf?different=1', 'port': 'https://issuer.example:443/report.pdf',
                 'credential': 'https://u:p@issuer.example/report.pdf', 'fragment': 'https://issuer.example/report.pdf#f'}[change]
        headers = headers.replace(row['memento_original_url'], wrong)
        row['memento_original_url'] = wrong
    elif change == 'receipt_url': request['argv'][-1] += '?different'
    elif change == 'receipt_status': request['http_status'] = 302
    elif change == 'receipt_exit': request['curl_exit_code'] = 22
    elif change == 'receipt_size': request['bytes'] += 1
    elif change == 'receipt_hash': request['sha256'] = '0' * 64
    elif change == 'receipt_headers': request['headers_sha256'] = '0' * 64
    elif change == 'receipt_output': request['argv'][2] = 'source.pdf'
    elif change == 'receipt_header_path': request['argv'][4] = 'index.json'
    elif change == 'duplicate_output': request['argv'][1:1] = ['--output', 'archive.pdf']
    elif change == 'request_index': row['receipt_request_index'] = True
    elif change == 'record_time': event['at'] = '2026-10-13T00:00:00Z'
    elif change == 'record_kind': event['kind'] = 'ADMIT'
    elif change == 'record_attempt': event['attempt'] = str(tmp_path / 'wrong')
    elif change == 'duplicate_original':
        headers = headers.replace('; rel="original"', '; rel="original", <' + row['memento_original_url'] + '>; rel="original"')
    elif change == 'changed_pdf':
        with (tmp_path / 'archive.pdf').open('ab') as stream: stream.write(b'x')
    (tmp_path / 'index.json').write_text(json.dumps(index))
    if change not in {'receipt_headers'}:
        request['headers_sha256'] = digest(headers.encode())
    (tmp_path / 'headers').write_text(headers)
    (tmp_path / 'receipt.json').write_text(json.dumps(receipt))
    (tmp_path / 'event.json').write_text(json.dumps(event))
    reseal_textsearch_files(req, tmp_path)
    if change == 'record_hash':
        event = json.loads((tmp_path / 'event.json').read_text())
        event['sha256'] = '0' * 64
        (tmp_path / 'event.json').write_text(json.dumps(event))
        row['retrieval_record']['sha256'] = digest((tmp_path / 'event.json').read_bytes())
    elif change == 'missing_output':
        outputs = json.loads((tmp_path / 'outputs.json').read_text())
        outputs.pop('index.json')
        (tmp_path / 'outputs.json').write_text(json.dumps(outputs))
        row['retained_outputs']['sha256'] = digest((tmp_path / 'outputs.json').read_bytes())
        event = json.loads((tmp_path / 'event.json').read_text())
        event['outputs_sha256'] = row['retained_outputs']['sha256']
        event.pop('sha256')
        event['sha256'] = digest(json.dumps(event, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())
        (tmp_path / 'event.json').write_text(json.dumps(event))
        row['retrieval_record']['sha256'] = digest((tmp_path / 'event.json').read_bytes())
    elif change == 'altered_after_binding':
        with (tmp_path / 'receipt.json').open('a') as stream: stream.write(' ')
    with pytest.raises(ValueError, match=reason):
        archive_observations.admit(req['bundle'], req['archive_observations'], tmp_path)


def test_archive_observations_textsearch_same_replay_source_is_explicit(tmp_path):
    req = textsearch_fixture(tmp_path)
    req['bundle']['documents'][0]['path'] = 'archive.pdf'
    result = archive_observations.admit(req['bundle'], req['archive_observations'], tmp_path)
    assert result['observations'][0]['source_origin'] == 'SAME_RETAINED_ARCHIVE_REPLAY'
    assert not result['observations'][0]['independent_source_comparison']


@pytest.mark.parametrize('with_request', [False, True])
def test_archive_observations_textsearch_resealed_consumer_forgery(tmp_path, with_request):
    req = textsearch_fixture(tmp_path)
    if not with_request: req.pop('archive_observations')
    p = products(req, tmp_path)
    payload = deepcopy(p['P2']['payload'])
    if with_request:
        payload['archive_observations']['observations'][0]['original_url_equivalence'] = 'PROVED'
    else:
        payload['archive_observations'] = {'version': archive_observations.TEXTSEARCH_VERSION}
    p['P2'] = service.seal('P2', req['bundle'], {'P1': p['P1']['sha256']}, payload)
    with pytest.raises(ValueError, match='Archive observation'):
        service.consume(p, tmp_path)


def test_archive_observations_textsearch_changed_receipt_rejected_after_p2(tmp_path):
    req = textsearch_fixture(tmp_path)
    retained = products(req, tmp_path)
    with (tmp_path / 'receipt.json').open('a') as stream: stream.write(' ')
    with pytest.raises(ValueError, match='evidence bytes changed'):
        service.consume(retained, tmp_path)
