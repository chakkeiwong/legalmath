"""Fixed CPU package checks for new closure evidence; never historical outputs."""
import argparse
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import time
import zipfile

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from legalmath.prospectus.successor.contracts import digest, read, write, VERSION


def codec(folder):
    from scripts.prospectus_closure_fixtures import annotation_fixture
    from legalmath.prospectus.successor import annotation_authoring as draft, annotation_xmi as xmi, annotation_bridge, service
    request = annotation_fixture(folder)
    packet = request['annotation_admission']['packets'][0]['packet']
    raw, types = draft.empty(packet['text'], packet['source'])
    cas = xmi.load_export(raw, types)
    spans = cas.typesystem.get_type(draft.SPAN)
    decoded = annotation_bridge.reimport(packet, packet['text'], packet['source'])
    heads = {}
    for group in decoded['groups']:
        for piece in group['spans']:
            member = spans(begin=piece['start'], end=piece['end'], groupId=group['id'], label=group['label'])
            cas.add(member)
            if group['id'] not in heads:
                heads[group['id']] = member
            else:
                cas.add(cas.typesystem.get_type(draft.RELATION)(begin=member.begin, end=member.end,
                    Governor=heads[group['id']], Dependent=member,
                    relationId=group['id'] + ':piece:' + str(member.begin), kind=xmi.GROUP_LINK))
    for relation in decoded['relations']:
        target = heads[relation['to']]
        cas.add(cas.typesystem.get_type(draft.RELATION)(begin=target.begin, end=target.end,
            Governor=heads[relation['from']], Dependent=target, relationId=relation['id'], kind=relation['kind']))
    raw = cas.to_xmi().encode()
    write(folder/'source.json', {'text': packet['text'], 'source': packet['source']})
    (folder/'authored.xmi').write_bytes(raw)
    (folder/'TypeSystem.xml').write_bytes(types)
    with zipfile.ZipFile(folder/'authored.zip','w') as archive:
        archive.writestr('source.xmi',raw);archive.writestr('TypeSystem.xml',types)
    rows = []
    for name, with_types, success in [('authored.xmi', True, True), ('authored.zip', False, True), ('authored.xmi', False, False)]:
        out = folder/f'codec-{len(rows)}.json'
        argv = [sys.executable, '-m', 'scripts.prospectus_integration_codec', 'admit', str(folder/'source.json'), str(folder/name), str(out)]
        if with_types: argv += ['--types', str(folder/'TypeSystem.xml')]
        run = subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,timeout=30)
        if (run.returncode == 0) != success: raise ValueError(run.stderr)
        row = {'argv':argv,'returncode':run.returncode,'expected_success':success}
        if success:
            request['annotation_admission']['packets'][0]['packet'] = read(out)['packet']
            request['observations'] = {'exempt': True}
            answer = service.assess(request, folder)
            if answer['questions']['Q1']['status'] != 'NO': raise ValueError('Decoded authored exception not consumed')
            write(folder/f'report-{len(rows)}.json', answer)
            row['service_Q1'] = 'NO'
        else:
            row['error'] = run.stderr.splitlines()[-1]
        rows.append(row)
    return {'checks':rows,'human_independence':False,'live_browser_executed':False}


def scan(folder, language='eng'):
    import fitz
    from legalmath.prospectus.successor import service
    os.environ['LEGALMATH_OCR_PYTHON'] = sys.executable
    original = fitz.open();page=original.new_page()
    control = 'Die Schuldverschreibungen werden am Ende der Laufzeit zurueckgezahlt.' if language=='deu' else 'The Notes are unsecured obligations of the Issuer.'
    phrase = 'Schuldverschreibungen' if language=='deu' else 'unsecured obligations'
    page.insert_text((50,90),control,fontsize=12)
    page.insert_text((50,120),'The Notes will be redeemed at maturity.',fontsize=14)
    pix=page.get_pixmap(dpi=150)
    scan=fitz.open();page=scan.new_page();page.insert_image(page.rect,stream=pix.tobytes('png'))
    scan.new_page()
    path=folder/'new-scan.pdf';scan.save(path)
    model=ROOT/('.localresources/prospectus/ocr-models/deu.traineddata' if language=='deu' else 'docs/prospectus/closure-2026-10-05/tools/eng.traineddata')
    time_value='2026-01-01T00:00:00Z'
    request={'version':VERSION,'bundle':{'instrument_id':'synthetic-new-scan','purpose':'review',
        'issue_date':time_value,'effective_at':time_value,'known_at':time_value,
        'documents':[{'id':'scan','path':str(path.relative_to(ROOT)),'sha256':digest(path.read_bytes()),
            'language':'de' if language=='deu' else 'en','authority':'Synthetic scan intake check','document_date':time_value,'known_from':time_value,
            'scan_profile':{'version':'pymupdf-scan.v1','dpi':300,'language':language,'max_pages':2,
                'tessdata':str(model.parent.relative_to(ROOT)), 'models':{language:digest(model.read_bytes())}}}]}}
    write(folder/'request.json',request)
    result=service.assess(request,ROOT)
    write(folder/'report.json',result)
    graph=result['source_map'];text=' '.join(u['raw'] for u in graph['units'] if u['page']==1)
    if phrase not in text or not any(u['page']==2 and not u['raw'].strip() for u in graph['units']):
        raise ValueError('Scan/blank-page consumer invariant failed')
    return {'pages':graph['documents'][0]['page_count'],'recognized_control':True,'blank_page_retained':True,
        'Q1':result['questions']['Q1']['status'],'language':language,'non_english_profile_tested':language=='deu',
        'interpretation':'Synthetic new scan exercises intake only; blank page and unreviewed meaning remain unresolved'}


def scan_de(folder):
    return scan(folder,'deu')


def numeric(folder):
    import QuantLib as ql
    from scripts.prospectus_closure_fixtures import term_fixture
    from legalmath.prospectus.successor import service
    from fractions import Fraction
    from legalmath.prospectus.successor.fixed_coupon import year_fraction, adjusted
    request=term_fixture(folder)
    report=service.assess(request,folder)
    calculation=report['questions']['Q5']['value']['calculation']
    counter=ql.ActualActual(ql.ActualActual.ISMA)
    fraction=counter.yearFraction(ql.Date(1,1,2024),ql.Date(1,1,2025),ql.Date(1,1,2024),ql.Date(1,1,2025))
    if fraction != 1.0 or calculation['day_fraction'] != '1': raise ValueError('Full annual coupon comparator differs')
    expected=[Fraction(1001,100),Fraction(501,100)]
    if [Fraction(t['amount']) for t in calculation['transfers']] != expected: raise ValueError('Exact holder rounding differs')
    cases=[
        ('annual-leap','2024-01-01','2025-01-01','ACT_ACT_ICMA',1,False,[('2024-01-01','2025-01-01')],Fraction(1)),
        ('short-first','2024-07-01','2025-01-01','ACT_ACT_ICMA',1,False,[('2024-01-01','2025-01-01')],Fraction(184,366)),
        ('short-final','2024-01-01','2024-07-01','ACT_ACT_ICMA',1,False,[('2024-01-01','2025-01-01')],Fraction(182,366)),
        ('long-first','2023-07-01','2025-01-01','ACT_ACT_ICMA',1,False,[('2023-01-01','2024-01-01'),('2024-01-01','2025-01-01')],1+Fraction(184,365)),
        ('long-final','2024-01-01','2025-07-01','ACT_ACT_ICMA',1,False,[('2024-01-01','2025-01-01'),('2025-01-01','2026-01-01')],1+Fraction(181,365)),
        ('semiannual-eom','2024-02-29','2024-08-31','ACT_ACT_ICMA',2,True,[('2024-02-29','2024-08-31')],Fraction(1,2)),
        ('act365-leap','2024-01-01','2025-01-01','ACT_365_FIXED',1,False,[],Fraction(366,365)),
        ('isda-split','2023-07-01','2024-07-01','ACT_ACT_ISDA',1,False,[],Fraction(184,365)+Fraction(182,366))]
    def qdate(value):
        return ql.DateParser.parseISO(value)
    rows=[]
    for name,start,end,convention,frequency,eom,refs,oracle in cases:
        actual=year_fraction(start,end,convention,references=[{'start':a,'end':b} for a,b in refs],frequency=frequency,eom=eom)
        dc = counter if convention=='ACT_ACT_ICMA' else ql.Actual365Fixed() if convention=='ACT_365_FIXED' else ql.ActualActual(ql.ActualActual.ISDA)
        # The library computes the entire stub using the applicable regular
        # reference period. The explicit rational oracle is a third comparator.
        ref=refs[-1] if name=='long-first' else refs[0] if refs else None
        value=dc.yearFraction(qdate(start),qdate(end),*(map(qdate,ref) if ref else []))
        if actual!=oracle or abs(value-float(oracle))>1e-12:
            raise ValueError('Day-count comparator mismatch: '+name)
        rows.append({'case':name,'exact':str(actual),'quantlib':value,'oracle':str(oracle),'tolerance':1e-12})
    calendar={'edition':'Synthetic identical calendar','valid_from':'2024-01-01','valid_until':'2026-01-01',
        'holidays':['2025-01-01'],'weekend':[5,6],'coverage':'COMPLETE_DECLARED_INTERVAL'}
    qcalendar=ql.WeekendsOnly();qcalendar.addHoliday(qdate('2025-01-01'))
    calendar_rows=[]
    for day,rule,answer in [('2024-08-31','FOLLOWING','2024-09-02'),('2024-08-31','MODIFIED_FOLLOWING','2024-08-30'),
                            ('2024-08-31','PRECEDING','2024-08-30'),('2025-01-01','FOLLOWING','2025-01-02')]:
        qrule={'FOLLOWING':ql.Following,'MODIFIED_FOLLOWING':ql.ModifiedFollowing,'PRECEDING':ql.Preceding}[rule]
        if adjusted(day,rule,calendar)!=answer or qcalendar.adjust(qdate(day),qrule).ISO()!=answer:
            raise ValueError('Calendar comparator mismatch')
        calendar_rows.append({'day':day,'rule':rule,'answer':answer})
    write(folder/'expanded-comparisons.json',{'fractions':rows,'calendar':calendar_rows})
    write(folder/'request.json',request);write(folder/'report.json',report)
    return {'quantlib_version':ql.__version__,'fraction':fraction,'exact_payments':[str(v) for v in expected],
            'terms_consumed_by_service':True,'real_instrument':False,'full_settlement':False,
            'fraction_cases':len(rows),'exact_calendar_cases':len(calendar_rows)}


def layout(folder):
    from legalmath.prospectus.successor import service, source_graph
    from scripts.prospectus_closure_fixtures import REVIEW, TIME
    retained = ROOT/'docs/implementation/prospectus-adoption/phases/A3/attempt-008'
    original = read(retained/'layout-input.json')['pages'][0]
    target_path = ROOT/'docs/implementation/prospectus-integration-repair/layout-003/margin-target.json'
    target = read(target_path)
    request = {'version':VERSION, 'bundle':{'instrument_id':'basf-page112-development', 'purpose':'review',
        'issue_date':TIME,'effective_at':TIME,'known_at':TIME,'documents':[{
            'id':original['document'],'path':original['path'],'sha256':original['sha256'], 'language':'de',
            'authority':'Retained BASF September 2022 base prospectus', 'document_date':TIME,'known_from':TIME}]}}
    graph=source_graph.build(request['bundle'],ROOT)
    definition = {s['unit'] for s in target['edge']['to']}
    request['assembly']={'operations':[{'unit':u['id'],'role':'OPERATIVE' if u['id'] in definition else 'HEADER',
        'source_text_sha256':u['text_sha256'],'reason':'Isolated shared-definition consumer control; not whole-contract selection',
        'context':'page112'} for u in graph['units']]}
    docling = read(retained/'layout/layout-0.json')
    request['layout_admission']={'version':'prospectus-layout.v1','graph_sha256':digest(graph),
        'review':{**REVIEW,'reason':'Retained implementer page-image review; shared Actual/Actual definition'},
        'documents':[{'document':original['document'],'source_sha256':original['sha256'],'docling':docling}],
        'governing':[{'id':'actual-actual-'+str(i),'kind':'governs','from':s,'to':target['edge']['to'],
            'questions':['Q1'],'reason':target['basis']} for i,s in enumerate(target['edge']['from'])]}
    p1=service.source_product(request,ROOT)
    p2=service.construction_product(p1,ROOT)
    p3=service.interpretation_product(p1,p2)
    edges=[d for d in p3['payload']['dependencies'] if d['id'].startswith('governing:')]
    if len(edges)!=3 or any(d['status']!='RESOLVED' for d in edges):
        raise ValueError('Retained BASF shared definition did not reach governing consumer')
    for row in p2['payload']['assembly']['units']:
        if row['unit'] == target['edge']['to'][0]['unit']:
            row['role']='EXCLUDED'
    # Rebuild legitimately with the changed supplied selection, not a forged product.
    operation=next(o for o in request['assembly']['operations'] if o['unit']==target['edge']['to'][0]['unit'])
    operation['role']='EXCLUDED'
    changed1=service.source_product(request,ROOT)
    changed2=service.construction_product(changed1,ROOT)
    changed3=service.interpretation_product(changed1,changed2)
    changed=[d for d in changed3['payload']['dependencies'] if d['id'].startswith('governing:')]
    if any(d['status']!='UNRESOLVED' for d in changed):
        raise ValueError('Missing BASF definition failed to invalidate scope')
    result={'source_sha256':original['sha256'],'retained_docling_sha256':digest((retained/'layout/layout-0.json').read_bytes()),
        'review_sha256':digest(target_path.read_bytes()),'projections':p1['payload']['graph']['layout']['projections'],
        'valid_governing_dependencies':edges,'deleted_definition_dependencies':changed,
        'automatic_legal_scope':False,'full_basf_contract':False}
    write(folder/'consumer-result.json',result)
    return {'retained_real_docling_consumed':True,'governing_control_and_mutation':True,
        'page':112,'mapped_regions':len(result['projections'][0]['mappings']),
        'scope':'Three retained German shared-definition lines; complete BASF selection not established'}


def compass(folder):
    from scripts.prospectus_closure_compass import exercise
    return exercise(folder, ROOT)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('codec','scan','scan_de','numeric','layout','compass'));args=parser.parse_args()
    base=ROOT/'docs/implementation/prospectus-integration-closure/packages'/args.action
    attempts=sorted(base.glob('attempt-*'))
    folder=base/f'attempt-{len(attempts)+1:03d}';folder.mkdir(parents=True)
    started=time.monotonic()
    paths = [*sorted((ROOT/'src/legalmath/prospectus/successor').glob('*.py')),
             *sorted((ROOT/'scripts').glob('prospectus_closure_*.py'))]
    initial_method = {str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in paths}
    write(folder/'started.json', {'argv':[sys.executable,*sys.argv], 'method':initial_method,
        'timeout_seconds':300, 'cpu_gpu':'CPU; CUDA_VISIBLE_DEVICES=-1'})
    def expired(signum, frame):
        raise TimeoutError('Declared 300-second exercise budget exhausted')
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(300)
    try:
        outcome=globals()[args.action](folder)
        if initial_method != {str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in paths}:
            raise ValueError('Exercise method changed during execution')
        result={'status':'PASS','outcome':outcome}
    except (Exception, KeyboardInterrupt) as exc:
        result={'status':'FAIL','error':type(exc).__name__+': '+str(exc)}
    finally:
        signal.alarm(0)
    diff = subprocess.check_output(['git','diff','--binary'], cwd=ROOT)
    result.update(argv=[sys.executable,*sys.argv],python=sys.version,cpu_gpu='CPU; CUDA_VISIBLE_DEVICES=-1',
        wall_seconds=time.monotonic()-started,plan='docs/plans/prospectus-integration-closure-2026-10-08.md',
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        git_diff_sha256=digest(diff),
        method_sha256=digest(Path(__file__).read_bytes()),random_seeds='Deterministic fixtures',
        fixture_sha256=digest((ROOT/'scripts/prospectus_closure_fixtures.py').read_bytes()),
        service_method={str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in sorted((ROOT/'src/legalmath/prospectus/successor').glob('*.py'))},
        helper_methods={str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in sorted((ROOT/'scripts').glob('prospectus_closure_*.py'))},
        initial_method=initial_method,
        data_version='Development fixtures; exact requests and retained real-source identities are preserved in this attempt')
    write(folder/'result.json',result)
    files={str(p.relative_to(folder)):digest(p.read_bytes()) for p in folder.rglob('*') if p.is_file()}
    write(folder/'manifest.json',{'files':files,'status':result['status']})
    print(json.dumps({'directory':str(folder.relative_to(ROOT)),'status':result['status'],
                      'outcome':result.get('outcome'),'error':result.get('error')},indent=2))
    if result['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
