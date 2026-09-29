"""Bounded public acquisition; unmet authority questions remain unmet."""
import re
import subprocess
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlparse
from pypdf import PdfReader
from resolution_support import *

SOURCES={
 'jfiu-home.html':'https://www.jfiu.gov.hk/en/',
 'jfiu-login.html':'https://www.jfiu.gov.hk/en/sbsal.html',
 'jfiu-webinar.pdf':'https://www.sfc.hk/-/media/EN/files/IS/AML/SFC-AMLCFT-Webinar-202511_JFIU_ENG.pdf?rev=f206230e309e4f5ba196bca77dfe46b9&hash=408F99B6D8750D895676F20D9A09A302',
 'gifts-faq.html':'https://www.sfc.hk/en/faqs/intermediaries/supervision/Code-of-Conduct/30-Sep-2010---Code-of-Conduct',
 'gifts-faq-original.pdf':'https://www.sfc.hk/sfc/doc/EN/faqs/super/sfocircular10025_faq_eng.pdf',
 '23ec52.json':'https://apps.sfc.hk/edistributionWeb/api/circular/content?refNo=23EC52&lang=EN',
}

class Text(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.skip+=1
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.skip=max(0,self.skip-1)
        if tag in ('p','li','h1','h2','h3','h4','div','tr'):self.parts.append('\n')
    def handle_data(self,text):
        if not self.skip:self.parts.append(text)
    def text(self):return '\n'.join(re.sub(r'\s+',' ',s).strip() for s in ''.join(self.parts).splitlines() if s.strip())

def html_text(value):
    p=Text();p.feed(value);return p.text()

def acquire():
    directory=OUT/'sources-official';directory.mkdir(parents=True,exist_ok=True);manifest=[]
    for name,url in SOURCES.items():
        path=directory/name;receipt=directory/(name+'.receipt.json')
        if receipt.exists():
            row=read(receipt)
            if row.get('sha256') and sha(path)!=row['sha256']:raise LegalMathError('E_INTEGRITY')
            if row.get('status')=='RETRIEVED':
                manifest.append(row);continue
            raise LegalMathError('E_DEPENDENCY',details='Failed acquisition must be explicitly repaired, not cached as success')
        if path.exists():
            row={'path':str(path.relative_to(ROOT)),'url':url,'final_url':url,
                 'retrieved_at':datetime.now(timezone.utc).isoformat(),'exit_code':0,
                 'sha256':sha(path),'bytes':path.stat().st_size,'status':'RETRIEVED',
                 'acquisition':'Trusted curl with exact allowlisted URL, command retained in session'}
            save(receipt,row);manifest.append(row);continue
        proc=subprocess.run(['curl','--fail','--location','--proto','=https','--proto-redir','=https',
             '--max-redirs','3','--connect-timeout','15','--max-time','60','--retry','1','--silent','--show-error',
             '--output',str(path),'--write-out','%{url_effective}',url],capture_output=True,text=True,timeout=140)
        final=proc.stdout.strip()
        if final and urlparse(final).hostname not in ('www.sfc.hk','apps.sfc.hk','www.jfiu.gov.hk'):
            raise LegalMathError('E_AUTHORITY',details='Unexpected public-source redirect')
        row={'path':str(path.relative_to(ROOT)),'url':url,'final_url':final,
             'retrieved_at':datetime.now(timezone.utc).isoformat(),'exit_code':proc.returncode}
        if proc.returncode==0:
            row.update(sha256=sha(path),bytes=path.stat().st_size,status='RETRIEVED')
        else:row.update(status='UNAVAILABLE',error=proc.stderr[-1500:])
        save(receipt,row);manifest.append(row)
    return manifest

def new_packet(path):
    raw=path.read_bytes();j=read(path);text=html_text(j['html']);units=[];offset=0
    from legalmath.sources.anchors import make_span
    for i,line in enumerate(text.splitlines()):
        units.append({'unit_id':'new.u'+str(i),'locator':'23EC52 block '+str(i),'text':line,'normative':True,
                      'span':make_span('new.s'+str(i),'sfc.23ec52',raw,text,offset,offset+len(line))})
        offset+=len(line)+1
    return {'source_key':'sfc.23ec52','authority':'RETAINED_SOURCE','selected_slice':
        'For a classified fund manager, determine whether the paragraph 28 and footnote 7 virtual-asset de-minimis trigger applies. '
        'Exclude tokenised securities from the VA category as instructed; retain all other circular provisions as separate questions.',
        'units':units,'dependencies':[],'family_ids':['sfc.tokenisation']}

def freeze_new(packet):
    path=DOC/'new-circular-official.json'
    if path.exists():
        if read(path)['packet']!=packet:raise LegalMathError('E_STALE_REVIEW')
        return read(path)
    # Fixed input vocabulary defines measurement, not the decision formula.
    facts=[]
    definitions=[('fund_manager','bool','Actor is a fund manager within paragraph 28 scope','actor',True),
      ('va_objective','bool','The stated investment objective of the fund is to invest in virtual assets as defined by the cited AMLO provision; tokenised securities alone do not satisfy this classification','fund objective',True),
      ('intended_va_bps','integer','Intended investment in AMLO virtual assets as a proportion of fund gross asset value, excluding tokenised securities; 100 basis points equals 1 percent','basis points of GAV',True)]
    anchors=[u['unit_id'] for u in packet['units'] if 'de minimis' in u['text']]
    for n,t,m,u,j in definitions:
        facts.append(dict(name=n,type=t,meaning=m,unit=u,source_unit_ids=anchors,requires_judgment=j))
    q={'control_id':'va.deminimis','question':'Does the stated VA de-minimis trigger apply to this fund manager?',
       'actor':'Fund managers in paragraph 28','unit_of_assessment':'one fund mandate and intended portfolio',
       'temporal_basis':'Frozen 23EC52 provision; no assertion about later amendments',
       'result_kind':'REQUIREMENT_APPLIES','true_means':'the selected VA de-minimis trigger applies',
       'false_means':'the selected trigger does not apply',
       'source_evidence':[{'unit_id':u['unit_id'],'quote':u['text']} for u in packet['units'] if 'de minimis' in u['text']]}
    examples=[('below',True,False,'999','FALSE',False),('at',True,False,'1000','TRUE',True),
              ('above',True,False,'1001','TRUE',True),('objective_only',True,True,'0','TRUE',True),
              ('tokenised_only',True,False,'0','FALSE',False),('mixed_excluded_tokenised',True,False,'500','FALSE',False),
              ('missing_percentage',True,False,None,'UNKNOWN',None),('objective_true_percentage_missing',True,True,None,'TRUE',True),
              ('missing_objective_at_threshold',True,None,'1000','TRUE',True),('actor_unknown',None,True,'1000','UNKNOWN',None),
              ('outside_actor',False,True,'1000','OUT_OF_SCOPE',None)]
    refs=[{'id':n,'facts':dict(fund_manager=f,va_objective=o,intended_va_bps=b),
           'expected_status':s,'expected_value':v} for n,f,o,b,s,v in examples]
    value={'packet':packet,'question':q,'facts':facts,'reference_cases':refs,'at':AT,
           'reference_basis':'Author-derived explicit-source development cases; not independently adjudicated',
           'pretraining_exposure':'UNKNOWN','selected_before_generation':True,
           'all_other_provisions':'Require explicit model coverage dispositions; this question is not overall compliance'}
    save(path,value);save(DOC/'new-circular-official-lock.json',{'sha256':sha(path),'source_sha256':sha(OUT/'sources-official/23ec52.json')})
    return value

def run(out):
    records=acquire();documents=[]
    for row in records:
        if row['status']!='RETRIEVED':continue
        path=ROOT/row['path']
        if path.suffix=='.pdf':
            pages=[p.extract_text() or '' for p in PdfReader(path).pages]
            text='\n\f\n'.join(pages)
        elif path.suffix=='.json':text=html_text(read(path)['html'])
        else:text=html_text(path.read_text())
        documents.append({**row,'text':text})
    code=OLD/'current-code.pdf';pages=[p.extract_text() or '' for p in PdfReader(code).pages]
    matches=[{'page':i+1,'text':t} for i,t in enumerate(pages) if 'In promoting a specific investment product to a client' in ' '.join(t.split())]
    if not matches:raise LegalMathError('E_REFERENCE',details='Code 3.11 passage not recovered')
    documents.append({'path':str(code.relative_to(ROOT)),'sha256':sha(code),'pages':matches,
                      'text':'\n'.join(m['text'] for m in matches),'status':'RETAINED_CODE_PASSAGE'})
    # Exact, source-bound excerpts supplied to repairs; no derived truth values.
    acquired=[]
    needles=('STREAMS 2','XML','e-Cert','re-submi','technical test','gifts','particular type','discount','3.11')
    for d in documents:
        chunks=[s for s in d['text'].split('\n\f\n') if any(n.lower() in s.lower() for n in needles)]
        selected='\n\f\n'.join(chunks)
        if len(selected)>40000:
            selected='\n'.join(s for s in selected.splitlines() if any(n.lower() in s.lower() for n in needles))
        if selected:acquired.append({'path':d['path'],'sha256':d['sha256'],'passage':selected})
    save(OUT/'acquired-authorities.json',acquired);save(out/'documents.json',documents)
    source=OUT/'sources-official/23ec52.json'
    if not source.exists():raise LegalMathError('E_DEPENDENCY',details='Preselected circular unavailable')
    new=freeze_new(new_packet(source))
    unresolved=[{'issue':x,'status':'NOT_ESTABLISHED_BY_RETRIEVAL'} for x in (
       'Operational certificate signing/holder/validity mechanics for an assessed submission',
       'JFIU XML schema content and version supplied separately',
       'Resubmission deadline and blackout-only follow-up',
       'Dominant-character or inseparability test for mixed gift packages',
       'Full structured-product classification and other advertising provisions')]
    result={'status':'PUBLIC_AUTHORITIES_RETAINED','acquisitions':records,'code_311_pages':[m['page'] for m in matches],
            'new_circular_units':len(new['packet']['units']),'new_reference_cases':len(new['reference_cases']),
            'unmet_dependencies':unresolved,'release_eligible':False}
    save(out/'result.json',result);return result
