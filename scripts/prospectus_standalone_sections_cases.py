"""Freeze independently read standalone section expressions before candidate creation."""
from datetime import datetime,timezone
import time,re
from scripts import prospectus_reference_label_grammar as prior
from legalmath.prospectus.successor.contracts import digest
ROOT,AUTH=prior.ROOT,prior.AUTH
PREP=AUTH/'reviews/standalone-sections-348'
PLAN='docs/plans/prospectus-standalone-sections-2026-10-19.md'
ROWS=[(10564,'§ 7',None,False,'7'),(11768,'§ 13',None,False,'13'),
 (12590,'§ 7',None,False,'7'),(13243,'§ 13',None,False,'13'),
 (15809,'§ 13',None,False,'13'),(17946,'§ 13',None,False,'13'),
 (19368,'§ 13',None,False,'13'),(21165,'§ 13',None,False,'13'),
 (24381,'§ 13',None,False,'13'),(27484,'§ 13',None,False,'13'),
 (33596,'§ 11',None,False,'11'),(34025,'§ 10',None,False,'10'),
 (34106,'§ 15 Aktiengesetz','AktG',False,None),(34170,'§ 13',None,False,'13'),
 (35946,'§ 18 und §§ 5 ff.\nSchVG','SchVG',True,None),
 (36007,'§§ 5 ff. SchVG','SchVG',True,None),
 (39434,'§ 13',None,False,'13'),(40648,'§ 13',None,False,'13')]
TARGETS=[('7',25134,28128,'p125:l1'),('10',32176,34657,'p128:l47'),
 ('11',34657,41637,'p129:l51'),('13',42677,43829,'p132:l1')]
def main():
 start=time.monotonic();assert not(PREP/'candidate/standalone_sections.py').exists()
 products={k:prior.read(ROOT/r['path']) for k,r in prior.read(prior.previous.PRODUCTS)['products'].items()}
 answer=prior.read(prior.HERE/'ordinary-answer.json.gz');text=products['P2']['payload']['assembly']['continuous_text']
 expected=[]
 for a,raw,law,onward,section in ROWS:
  assert text[a:a+len(raw)]==raw,(a,text[a:a+len(raw)],raw)
  expected.append({'start':a,'end':a+len(raw),'raw':raw,'statute':law,'onward_scope':onward,'section':section})
 targets=[]
 for section,a,b,unit in TARGETS:
  source=next(h for h in answer['reference_scope_context']['section_headers'] if h['section']==section)
  assert source['start']==a and source['unit'].endswith(':'+unit)
  targets.append({'section':section,'start':a,'end':b,'unit':source['unit'],'text_sha256':digest(text[a:b].encode())})
 signs=[{'start':m.start(),'end':m.end(),'raw':m.group()} for m in re.finditer(r'(?<!§)§{1,2}\s*[0-9]+',text)]
 assert len(signs)==50
 prior.save(PREP/'expected.json',{'references':expected,'targets':targets,'signs':signs,
  'headings':15,'covered_by_paragraph_context':16,'remaining_signs':19,'logical_expressions':18})
 prior.save(PREP/'source-freeze.json',{'created_at':datetime.now(timezone.utc).isoformat(),'candidate_absent':True,
  'products_sha256':digest(products),'ordinary_answer_sha256':digest(answer),'plan_sha256':prior.sha(ROOT/PLAN),
  'expected_sha256':prior.sha(PREP/'expected.json'),'wall_seconds':time.monotonic()-start})
 print('Frozen 50section-sign partition,18standalone logical expressions,4structural section destinations')
if __name__=='__main__':main()
