"""Official authority evidence and narrow dated/bilingual comparisons."""
from pathlib import Path
from html.parser import HTMLParser
import json
import re
from legalmath.canonical import raw_digest,digest
from legalmath.interpretation.assurance.diversity import save
from legalmath.interpretation.assurance.legal_profile import precedence,bilingual_pair
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'artifacts/interpretation/round13'
DOC=ROOT/'docs/implementation/interpretation-round13'

class Plain(HTMLParser):
    def __init__(self):super().__init__();self.parts=[]
    def handle_data(self,text):self.parts.append(text)
    def handle_endtag(self,tag):
        if tag in ('p','li','div'):self.parts.append('\n')

def document(path,ident,language,authority):
    raw=Path(path).read_bytes()
    if path.suffix=='.pdf':
        from pypdf import PdfReader
        pages=[p.extract_text() for p in PdfReader(path).pages]
        text='\n\f\n'.join(pages);metadata={'page_count':len(pages)}
    else:
        value=json.loads(raw);parser=Plain();parser.feed(value['html']);text=''.join(parser.parts)
        metadata={k:value[k] for k in ('refNo','lang','releasedDate','title')}
    return {'document_id':ident,'authority_id':authority,'language':language,'path':str(path.relative_to(ROOT)),
            'source_sha256':raw_digest(raw),'text':text,'metadata':metadata}

def anchor(doc,phrase):
    start=doc['text'].find(phrase)
    if start<0:
        match=re.search(r'\s+'.join(re.escape(p) for p in phrase.split()),doc['text'])
        if not match:raise ValueError((doc['document_id'],phrase))
        start=match.start();phrase=match.group()
    return {'document_id':doc['document_id'],'source_sha256':doc['source_sha256'],
            'start':start,'end':start+len(phrase),'quote':phrase}

def run(out):
    out=Path(out)
    docs={}
    specs=[(BASE/'current-code.pdf','code.jan2026','EN','sfc.code'),
           (BASE/'eip-predecessor.json','eip.24ec33','EN','sfc.eip.24ec33'),
           (ROOT/'examples/integrated-assurance/sources/24ec50.json','eip.24ec50','EN','sfc.eip.24ec50'),
           (ROOT/'examples/integrated-assurance/sources/25ec71.json','margin.25ec71','EN','sfc.margin.25ec71'),
           (ROOT/'examples/integrated-assurance/sources/26ec2.json','str.en','EN','sfc.str.26ec2'),
           (BASE/'str-chinese.json','str.tc','TC','sfc.str.26ec2')]
    for spec in specs:
        doc=document(*spec);docs[doc['document_id']]=doc
    code=docs['code.jan2026'];start=anchor(code,'non-centrally cleared single-stock options, equity basket')['start']
    end=code['text'].index('until further notice',start)+len('until further notice')
    evidence=anchor(code,code['text'][start:end])
    margin={'status':'CURRENT_CODE_EXPLICITLY_SUPPORTS_ANNOUNCED_EXTENSION',
            'evidence':evidence,'source_publication':'January 2026 edition; exact gazettal day not established',
            'conclusion':'Current paragraph 7(e) and footnote 9 retain the listed options exemption from 4 January 2026.',
            'rival_disposition':'Gazettal-as-an-additional-transaction-fact has no condition in this retained provision; historical gazettal timing remains unevaluated.',
            'residual':'A future/later notice could displace the exemption. This packet does not establish universal absence of later notices.',
            'historical_applicability_proved':False}
    later=docs['eip.24ec50'];earlier=docs['eip.24ec33']
    phrase='extend the parallel run period of its new online application/submission system for investment products, e-IP, by one month to 29 November 2024.'
    edge={'higher':'24ec50.parallel','lower':'24ec33.parallel','question':'eip.parallel.end',
          'effective_from':'2024-10-24','effective_until':None,'evidence':[anchor(later,phrase)]}
    order=precedence(['24ec33.parallel','24ec50.parallel'],[edge],docs,question='eip.parallel.end',at='2024-11-01')
    reverse={**edge,'higher':edge['lower'],'lower':edge['higher']}
    cycle=precedence(['24ec33.parallel','24ec50.parallel'],[edge,reverse],docs,question='eip.parallel.end',at='2024-11-01')
    if cycle['status']!='UNRESOLVED_PRIORITY':raise ValueError('Priority cycle silently resolved')
    categories='Investment-linked assurance schemes, mandatory provident fund products, open-ended fund companies, paper gold schemes, pooled retirement funds, real estate investment trusts, unit trusts and mutual funds and unlisted structured investment products.'
    anchors=[anchor(d,categories) for d in [earlier,later]]
    alignments=[]
    pairs=[('Hongkong Post e-Cert (electronic certificate) is required for this submission.',
            '此提交方式須使用香港郵政電子證書。','e-Cert footnote 3'),
           ('licensed firms are required to re-submit the STRs via STREAMS 2.',
            '持牌機構須透過STREAMS 2重新提交有關可疑交易報告。','resubmission footnote 2'),
           ('9:00am on 2 February 2026','2026年2月2日上午9時正','operational launch')]
    for en,tc,meaning in pairs:
        alignments.append(bilingual_pair(anchor(docs['str.en'],en),anchor(docs['str.tc'],tc),docs,
            relationship=meaning,assessment='Both retained versions express the same selected condition on author inspection.',
            residuals=['Provision pairing is proposed, not certified translation equivalence.','Other provisions and referenced JFIU materials need separate checks.']))
    value={'status':'ANCHORED_AUTHORITY_INVESTIGATION','documents':docs,'margin':margin,
           'eip':{'category_evidence':anchors,'priority':order,'cycle_fault':cycle,
                  'definition_boundary':'Listed categories can be represented explicitly; deciding an unfamiliar product belongs to one remains a factual/legal classification.'},
           'bilingual':alignments,'release_eligible':False}
    save(out/'result.json',value)
    return value
