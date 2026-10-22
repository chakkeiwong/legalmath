"""Retained Portuguese worker through actual P1, correction and report consumers."""
import argparse
from collections import Counter
from copy import deepcopy
import gzip
from pathlib import Path
import re
import unicodedata
from scripts.prospectus_geometry_program import ROOT, HERE, OLD, read, seal, verify, write
from scripts.prospectus_report_scope import FIELDS, REVIEW, oracle_reading, span
from legalmath.prospectus.successor import anchors, layout_adapter, report_scope, service
from legalmath.prospectus.successor.contracts import digest


def normalized(text):
    return ' '.join(unicodedata.normalize('NFC', text).split())


def compressed(path, data):
    import json
    with gzip.open(path, 'wt', compresslevel=3) as stream:
        json.dump(data, stream, ensure_ascii=False)


def answer(p1, p2, p3):
    return service.consume({'P1':p1, 'P2':p2, 'P3':p3,
        'P4':service.law_product(p1,p3), 'P5':service.financial_product(p1,p2,p3)}, ROOT,
        include_artifacts=True)


def corrections(graph):
    entries = []
    for page, raw, corrected in [(176,'S.A,','S.A.'), (178,'Lisboa.','Lisboa,')]:
        units = [u for u in graph['units'] if u['page']==page
                 and u['method']=='retained-pymupdf-tesseract' and raw in u['raw']]
        unit, = units
        left = unit['raw'].index(raw)
        right = left + len(raw)
        operations = []
        for kind, a, b, text in [('copy',0,left,unit['raw'][:left]),
                ('replace',left,right,corrected), ('copy',right,len(unit['raw']),unit['raw'][right:])]:
            if a < b:
                operations.append({'kind':kind,'start':a,'end':b,'text':text,
                    'reason':'Source-image punctuation review; original raw text retained'})
        entries.append({'id':f'pt2009-punctuation-p{page}',
            'source':{'unit':unit['id'],'document':unit['document'],'source_sha256':unit['source_sha256'],
                      'start':0,'end':len(unit['raw']),'quote':unit['raw']},
            'image_sha256':unit['image_sha256'],'operations':operations})
    return {'version':'reviewed-corrections.v1','graph_sha256':digest(graph),
            'review':REVIEW,'entries':entries}


def consume(output):
    verify(OLD)
    verify(HERE / 'freeze-001')
    request = read(OLD / 'ocr-consumer-001/request.json')
    worker = read(OLD / 'ocr-consumer-001/worker.json')
    oracle = read(OLD / 'critical-spans.json')
    document = request['bundle']['documents'][0]
    if digest((ROOT / document['path']).read_bytes()) != oracle['source_sha256']:
        raise ValueError('Original source changed')
    output.mkdir(parents=True, exist_ok=False)
    checks = {}
    try:
        service.source_product(request, ROOT)
    except ValueError as error:
        if 'outside original rendered page geometry' not in str(error):
            raise
        write(output / 'strict-rejection.json', {'status':'REJECTED','reason':str(error)})
        checks['strict_rejection_preserved'] = True
    else:
        raise ValueError('Strict original accepted invalid geometry')
    native_request = deepcopy(request)
    native_doc = native_request['bundle']['documents'][0]
    native_doc.pop('hybrid_profile')
    native_doc.pop('hybrid_ocr')
    native = service.source_product(native_request, ROOT)['payload']['graph']['units']
    document['hybrid_profile'].update(version='pymupdf-hybrid.v2',
        geometry_policy='preserve-text-without-invalid-box.v1')
    print('actual optional P1', flush=True)
    p1 = service.source_product(request, ROOT)
    graph = p1['payload']['graph']
    checks['native_units_preserved'] = [u for u in graph['units']
        if u['method']!='retained-pymupdf-tesseract'] == native
    units = [u for u in graph['units'] if u['method']=='retained-pymupdf-tesseract']
    raw_words = Counter((p['page'],w[4],tuple(w[:4])) for p in worker['pages'] for w in p['words'])
    product_words = Counter((u['page'],w['text'],tuple(w.get('geometry_issue',{}).get('raw_bbox',w['bbox'])))
        for u in units for w in u['words'])
    checks['all_raw_words_and_boxes_preserved'] = raw_words == product_words
    bad, = [u for u in units if u.get('geometry_issues')]
    checks['one_unknown_colon'] = (bad['page']==177 and bad['bbox'] is None and
        sum(w['bbox'] is None for u in units for w in u['words'])==1 and
        [w['text'] for w in bad['words'] if w['bbox'] is None]==[':'])
    source = {'unit':bad['id'],'document':bad['document'],'source_sha256':bad['source_sha256'],
              'start':0,'end':len(bad['raw']),'quote':bad['raw']}
    checks['anchor_withholds_geometry'] = anchors.bind(graph,source)['bbox'] is None
    layout = {'texts':[{'self_ref':'page177','text':bad['raw'],'prov':[{'page_no':177,
        'bbox':{'l':0,'t':0,'r':641,'b':859,'coord_origin':'TOPLEFT'}}]}]}
    for mapper in (layout_adapter.map_layout,layout_adapter.project_layout):
        result = mapper(units,layout,source_sha256=document['sha256'])
        checks[mapper.__name__+'_refuses_unknown_page'] = not result['mappings'] and bool(result['failures'])
    request['correction_admission'] = corrections(graph)
    write(output / 'correction-admission.json',request['correction_admission'])
    p1 = service.source_product(request,ROOT)
    graph = p1['payload']['graph']
    corrected = {r['source']['unit']:r['text'] for r in graph['corrections']['entries']}
    spans = []
    for row in oracle['spans']:
        raw = '\n'.join(u['raw'] for u in units if u['page']==row['page'])
        display = '\n'.join(corrected.get(u['id'],u['raw']) for u in units if u['page']==row['page'])
        spans.append({**row,'raw_match':normalized(row['text']) in normalized(raw),
            'assisted_match':normalized(row['text']) in normalized(display)})
    write(output / 'span-results.json',spans)
    checks['eleven_image_reviewed_spans'] = all(r['assisted_match'] for r in spans)
    checks['raw_recognition_misses_retained'] = {r['id'] for r in spans if not r['raw_match']} == {
        'audit_complete_opinion','committee_report_date'}
    baseline_p2 = service.construction_product(p1,ROOT)
    baseline_p3 = service.interpretation_product(p1,baseline_p2)
    baseline = answer(p1,baseline_p2,baseline_p3)
    quotes = {r['id']:r['text'] for r in oracle['spans']}
    specs = [
        ('audit-2009-pt',[174,175,176], {'identity':'audit_identity','subject':'audit_subject',
            'assurance_level':'audit_assurance','criteria':'audit_criteria','conclusion':'audit_complete_opinion',
            'report_date':'audit_report_date'}, {'identity':'STATUTORY_FINANCIAL_AUDIT',
            'subject':'FINANCIAL_STATEMENTS','assurance_level':'REASONABLE','conclusion':'AFFIRMATIVE_FINANCIAL_OPINION'}),
        ('committee-2009-pt',[177,178], {'identity':'committee_identity','subject':'committee_subject',
            'conclusion':'committee_complete_concurrence','addressee':'committee_addressee',
            'report_date':'committee_report_date'}, {'identity':'COMMITTEE_REPORT',
            'subject':'FINANCIAL_STATEMENTS_AND_PROFIT_APPROPRIATION','conclusion':'CONCURRENCE_WITH_AUDITORS'})]
    readings, facts_by_id = [], {}
    for identity,pages,fields,codes in specs:
        text = oracle_reading(graph, {'document':document['id'],'pages':pages,'regions':{}})
        readings.append({'id':identity,'document':document['id'],'source_sha256':document['sha256'],
            'pages':[{'page':p,'mode':'raw'} for p in pages],'text_sha256':digest(text.encode())})
        facts = {field:{'status':'UNKNOWN','reason':'Not established by the retained report'} for field in FIELDS}
        for field, quote_id in fields.items():
            # These are explicit RAW quotations; corrected display remains a separate P1 map.
            quote = quotes[quote_id]
            if quote_id=='audit_complete_opinion': quote=quote.replace('S.A. em','S.A, em')
            if quote_id=='committee_report_date': quote=quote.replace('Lisboa,','Lisboa.')
            facts[field] = {'status':'SUPPLIED','spans':[span(text,quote)],
                            **({'value':codes[field]} if field in codes else {})}
        facts_by_id[identity] = facts
    request['source_report_readings'] = {'version':'source-report-readings.v1','graph_sha256':digest(graph),
        'review':{**REVIEW,'reason':'Source image review; REASONABLE is a supplied translation of grau de segurança aceitável; raw punctuation remains quoted'},
        'reports':readings}
    p1 = service.seal('P1',request['bundle'],{'request':digest(request)},{'request':request,'graph':graph})
    print('actual Portuguese report consumers',flush=True)
    p2 = service.construction_product(p1,ROOT)
    selected = p2['payload']['source_report_readings']
    scope = {'version':'source-report-scope.v1','readings_sha256':digest(selected),
        'review':request['source_report_readings']['review'],
        'reports':[{'id':r['id'],'reading_sha256':r['sha256'],'facts':facts_by_id[r['id']]} for r in selected['reports']]}
    p3 = service.interpretation_product(p1,p2,{'source_report_scope':scope})
    final = answer(p1,p2,p3)
    checks.update(questions_unchanged=final['questions']==baseline['questions'],
        assembly_unchanged=p2['payload']['assembly']==baseline_p2['payload']['assembly'],
        dependencies_unchanged=p3['payload']['dependencies']==baseline_p3['payload']['dependencies'],
        external_facts_unknown=all(r['facts'][k]['status']=='UNKNOWN' for r in final['source_reports'] for k in report_scope.EXTERNAL),
        both_reports_consumed=len(final['source_reports'])==2 and all(r['status']=='CONDITIONAL_SUPPLIED_READING' for r in final['source_reports']),
        independent_acceptance_not_claimed=not final['independent_legal_acceptance'],
        correction_maps_retained=final['source_map']['corrections']==graph['corrections'])
    write(output/'request.json',request)
    write(output/'scope-admission.json',scope)
    compressed(output/'source-product.json.gz',p1)
    compressed(output/'answer.json.gz',final)
    write(output/'result.json',{'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,
        'raw_spans':sum(r['raw_match'] for r in spans),'assisted_spans':sum(r['assisted_match'] for r in spans),
        'total_spans':len(spans),'native_units':len(native),'ocr_words':sum(raw_words.values()),
        'geometry_issues':1,'report_scope_uses':'Exact raw quotes, with separate image-bound P1 corrections',
        'limits':'Exposed supplied readings; OCR producer cause unresolved; no completeness or independent acceptance'})
    seal(output)
    return all(checks.values())


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    return 0 if consume(args.output) else 1


if __name__=='__main__':
    raise SystemExit(main())
