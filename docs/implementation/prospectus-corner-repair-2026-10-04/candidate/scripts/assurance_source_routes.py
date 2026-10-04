"""Page-complete source recovery and discrepancy actions, all local and CPU-only."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

from legalmath.interpretation.assurance.diversity import Investigation,page_discrepancy,save,assess_methods,identity
from assurance_tool_preflight import BASE,ocr_environment

ROOT=Path(__file__).resolve().parents[1]
PDFS=[ROOT/'.localresources/sfc'/p for p in ('23EC35-annex1.pdf','23EC35-annex2.pdf','23EC49-appendix.pdf')]


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def command(argv,timeout=60,env=None):
    return subprocess.run(list(map(str,argv)),capture_output=True,text=True,check=True,timeout=timeout,env=env).stdout


def ocr(image,output,psm):
    exe=BASE/'ocr/usr/bin/tesseract'
    command([exe,image,output,'-l','eng','--psm',str(psm),'txt','tsv'],env=ocr_environment())
    text=output.with_suffix('.txt').read_text()
    return {'text':text,'text_sha256':digest(output.with_suffix('.txt')),'tsv':str(output.with_suffix('.tsv')),
            'tsv_sha256':digest(output.with_suffix('.tsv')),'psm':psm,'engine':'Tesseract 4, local English data'}


def docling_pages(pdf,output,count):
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.datamodel.accelerator_options import AcceleratorOptions,AcceleratorDevice
    from docling.document_converter import DocumentConverter,PdfFormatOption
    options=PdfPipelineOptions(artifacts_path=BASE/'models')
    options.do_ocr=False;options.do_table_structure=False
    options.accelerator_options=AcceleratorOptions(num_threads=2,device=AcceleratorDevice.CPU)
    result=DocumentConverter(format_options={InputFormat.PDF:PdfFormatOption(pipeline_options=options)}).convert(pdf)
    doc=result.document;raw=doc.export_to_dict();save(output/'docling.json',raw)
    if str(result.status).split('.')[-1].lower()!='success' or set(doc.pages)!=set(range(1,count+1)):
        raise ValueError('Docling conversion incomplete; retained raw output requires investigation')
    pages=[[] for _ in range(count)]
    for item,_ in doc.iterate_items():
        text=getattr(item,'text',None)
        if not text:continue
        for prov in getattr(item,'prov',[]):
            if 1<=prov.page_no<=count:pages[prov.page_no-1].append(text)
    return ['\n'.join(p) for p in pages],{'status':str(result.status),'actual_page_ids':sorted(map(str,doc.pages)),
                'layout_json_sha256':digest(output/'docling.json'),'ocr':False,'table_structure':False,
                'limitations':['Table cell semantics and picture descriptions disabled; empty text on image-only pages is a finding.']}


def extract_one(pdf,out,maximum_actions=2):
    from pypdf import PdfReader
    import pdfplumber
    out.mkdir(parents=True,exist_ok=False)
    reader=PdfReader(pdf);count=len(reader.pages)
    if not 1<=count<=32:raise ValueError('PDF page budget exceeded')
    if pdf.stat().st_size>20*1024*1024:raise ValueError('PDF size budget exceeded')
    source_hash=digest(pdf)
    primary=[p.extract_text() or '' for p in reader.pages]
    ra_src='/home/chakwong/python/ResearchAssistant/src'
    if ra_src not in sys.path:sys.path.insert(0,ra_src)
    from research_assistant.ingest.pdf_extract import extract_pdf_text
    ra_text=extract_pdf_text(pdf);(out/'researchassistant.txt').write_text(ra_text)
    ra_pages=ra_text.split('\f')
    if ra_pages and not ra_pages[-1].strip():ra_pages.pop()
    if len(ra_pages)!=count:raise ValueError('ResearchAssistant page coverage differs')
    layout=[]
    with pdfplumber.open(pdf) as book:
        for i,p in enumerate(book.pages):
            words=p.extract_words();save(out/f'pdfplumber-{i+1:02}.json',{'words':words,'width':p.width,'height':p.height})
            layout.append(p.extract_text() or '')
    doc_pages,doc_meta=docling_pages(pdf,out,count)
    pages=[];issues=[]
    for i in range(count):
        number=i+1;page=out/f'page-{number:02}';page.mkdir()
        raster=page/'raster'
        command(['/usr/bin/pdftoppm','-f',str(number),'-l',str(number),'-r','180','-png','-singlefile',pdf,raster])
        image=raster.with_suffix('.png');direct=ocr(image,page/'ocr-initial',3)
        text={'pypdf':primary[i],'researchassistant-poppler':ra_pages[i],'pdfplumber':layout[i],'docling':doc_pages[i],'tesseract':direct['text']}
        for name,value in text.items():(page/(name+'.txt')).write_text(value)
        comparisons={name:page_discrepancy(primary[i],value) for name,value in text.items() if name!='pypdf'}
        claim_hash=identity({'source':source_hash,'page':number})
        families={'researchassistant-poppler':'poppler','pdfplumber':'pdfminer','docling':'docling-layout','tesseract':'pixels-ocr'}
        method_results=[{'method_id':name,'family':families[name],'claim_hash':claim_hash,
                         'status':'AGREES' if value['agreement'] else 'DISAGREES','evidence_hash':identity(value),
                         'shared_dependencies':['retained PDF']+([] if name=='tesseract' else ['embedded text layer'])}
                        for name,value in comparisons.items()]
        row={'page':number,'source_sha256':source_hash,'raster_sha256':digest(image),'comparisons':comparisons,
             'required_method_assessment':assess_methods(method_results,list(families),claim_hash),
             'routes':{name:{'text_path':str(page/(name+'.txt')),'sha256':digest(page/(name+'.txt'))} for name in text}}
        if any(not c['agreement'] for c in comparisons.values()):
            issue_key=f'{source_hash}:page:{number}'
            actions=[(f'ocr-psm-{psm}',lambda psm=psm:ocr(image,page/f'ocr-repair-{psm}',psm)) for psm in (6,11)]
            investigation=Investigation(page/'investigation.json',{'source':source_hash,'page':number,'initial':comparisons},maximum_actions).run(actions)
            issue={'issue_id':issue_key,'stage':'EXTRACTION','page':number,'status':'UNRESOLVED',
                   'evidence':str(page),'automatic_actions':len(investigation['actions']),
                   'reason':'At least one complete page reading differs. Token/order/materiality adjudication remains required.'}
            issues.append(issue);row['investigation']=investigation
        pages.append(row)
    report={'source':str(pdf),'source_sha256':source_hash,'page_count':count,'pages':pages,'issues':issues,
            'docling':doc_meta,'route_families':{'pypdf':'pdf-text','researchassistant-poppler':'poppler-text',
                    'pdfplumber':'pdfminer-layout','docling':'layout-model-with-text-layer','tesseract':'rendered-pixels-ocr'},
            'shared_dependencies':['All PDF text routes use the same embedded text layer.',
                                   'ResearchAssistant invokes Poppler; direct Poppler is not an extra independent vote.',
                                   'Both repair configurations use the same OCR engine.'],
            'engineering_status':'PASS','assurance_status':'UNCERTAINTY_RETAINED' if issues else 'OBSERVED_AGREEMENT',
            'visual_completeness_established':False,'release_eligible':False}
    save(out/'report.json',report);return report


def synthetic_pdf(path):
    from PIL import Image,ImageDraw,ImageFont
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    image=Image.new('RGB',(1800,260),'white');draw=ImageDraw.Draw(image)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',44)
    draw.text((30,30),'EXCEPTION: discounts of fees or charges are excluded.',fill='black',font=font)
    draw.text((30,110),'FOOTNOTE: a particular type of product is also covered.',fill='black',font=font)
    c=canvas.Canvas(str(path));c.setFont('Helvetica',16)
    c.drawString(55,770,'SYNTHETIC EXTRACTION CHALLENGE')
    c.drawString(55,730,'Distributors should not offer gifts in product promotion.')
    c.drawImage(ImageReader(image),45,540,width=500,height=90)
    c.save()


def run(out):
    out.mkdir(parents=True,exist_ok=False)
    reports=[extract_one(pdf,out/pdf.stem) for pdf in PDFS]
    fixture=out/'synthetic.pdf';synthetic_pdf(fixture)
    synthetic=extract_one(fixture,out/'synthetic-scanned-exception')
    text=(out/'synthetic-scanned-exception/page-01/tesseract.txt').read_text().lower()
    primary=(out/'synthetic-scanned-exception/page-01/pypdf.txt').read_text().lower()
    checks={'image_exception_absent_from_text':'discounts' not in primary,
            'image_exception_recovered':'discounts of fees or charges' in text,
            'footnote_recovered':'particular type of product' in text,
            'discrepancy_opened':bool(synthetic['issues']),
            'automatic_actions_executed':all(a['status']=='EXECUTED' for row in synthetic['pages'] for a in row.get('investigation',{}).get('actions',[]))
                and sum(i['automatic_actions'] for i in synthetic['issues'])==2,
            'no_false_release':not synthetic['release_eligible']}
    result={'engineering_status':'PASS' if all(checks.values()) else 'FAIL','challenge_checks':checks,
            'public_documents':len(reports),'public_pages':sum(r['page_count'] for r in reports),
            'issues':[i for r in reports for i in r['issues']],'synthetic_issues':synthetic['issues'],
            'assurance_status':'UNCERTAINTY_RETAINED','release_eligible':False}
    save(out/'result.json',result)
    if not all(checks.values()):raise ValueError('Source fault challenge failed: '+str(checks))
    return result
