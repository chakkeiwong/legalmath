"""Independent literal context expectations, fixed before candidate execution."""
from pathlib import Path
import time
from scripts import prospectus_paragraph_discovery as prior
ROOT,AUTH=prior.ROOT,prior.AUTH
PREP=AUTH/'reviews/reference-scope-343'
PLAN='docs/plans/prospectus-reference-scope-2026-10-19.md'
# Offset, complete citation text, explicit section, statutory name, enclosing section.
ROWS=[
 (425,'§ 1 Absatz (4)','1',None,'1'),
 (2371,'Absatz (b) dieses § 1','1',None,'1'),
 (2393,'§ 1 Absatz (3)','1',None,'1'),
 (2557,'§ 6 Absatz (2)','6',None,'1'),
 (6661,'§ 5\nAbsatz (1)','5',None,'3'),
 (7891,'Absatzes (2)',None,None,'4'),
 (8123,'Absatz (2)',None,None,'4'),
 (8385,'Absatz (2)',None,None,'4'),
 (8571,'§ 1\nAbsatz (3)(b)','1',None,'4'),
 (12522,'§ 3 Absatz (1)','3',None,'5'),
 (13856,'§ 5 Absatz (2)','5',None,'5'),
 (15056,'§ 30 Absatz 2 des\nWertpapiererwerbs- und Übernahmegesetzes (WpÜG)','30','WpÜG','5'),
 (15993,'§ 5 Absatz (3)','5',None,'5'),
 (17340,'Absatz (b)',None,None,'5'),
 (18972,'Absatz (b)',None,None,'5'),
 (21362,'Absatzes (2)  dieses § 5','5',None,'5'),
 (21506,'Absatzes [(5)] dieses § 5','5',None,'5'),
 (28161,'§ 801 Absatz 1 Satz 1 BGB','801','BGB','8'),
 (28957,'§ 2 Absatz (2)','2',None,'9'),
 (31489,'Absatz (1)(b) und/oder (1)(c)',None,None,'9'),
 (31593,'Absatz (1)(a) und (1)(d) bis (g)',None,None,'9'),
 (31981,'Absatz (1)',None,None,'9'),
 (33951,'Unterabsätzen (a), (b), (c) und (d)',None,None,'10'),
 (34965,'Absatz 2',None,None,'11'),
 (35663,'§ 5 Absatz 3, Nr. 1 bis Nr. 8 des SchVG','5','SchVG','11'),
 (39303,'Absatz (a)(ii) und (iii)',None,None,'11'),
 (40687,'§ 50 Absatz 1 des\nWertpapierhandelsgesetzes','50','WpHG','11'),
 (43076,'Absatz (1)',None,None,'13'),
 (43200,'Absatz (1)',None,None,'13'),
 (43640,'§ 14 Absatz [4]','14',None,'13'),
]
CASES=[
 {'id':'prefix','text':'gemäß § 7 Absatz (2).','raw':'§ 7 Absatz (2)','section':'7','law':None},
 {'id':'cross-line','text':'gemäß § 7\nAbsatz (2).','raw':'§ 7\nAbsatz (2)','section':'7','law':None},
 {'id':'suffix','text':'Absatz (2) dieses § 7 gilt.','raw':'Absatz (2) dieses § 7','section':'7','law':None},
 {'id':'relative','text':'Absatz (2) gilt.','raw':'Absatz (2)','section':None,'law':None},
 {'id':'same-qualifiers','text':'§ 7 Absatz (2) dieses § 7','raw':'§ 7 Absatz (2) dieses § 7','section':'7','law':None},
 {'id':'conflict','text':'§ 7 Absatz (2) dieses § 9','raw':'§ 7 Absatz (2) dieses § 9','section':None,'law':None,'issue':'CONFLICTING_SECTION_QUALIFIERS'},
 {'id':'bgb','text':'§ 801 Absatz 1 Satz 1 BGB','raw':'§ 801 Absatz 1 Satz 1 BGB','section':'801','law':'BGB'},
 {'id':'schvg','text':'§ 5 Absatz 3, Nr. 1 bis Nr. 8 des SchVG','raw':'§ 5 Absatz 3, Nr. 1 bis Nr. 8 des SchVG','section':'5','law':'SchVG'},
 {'id':'wphg','text':'§ 50 Absatz 1 des\nWertpapierhandelsgesetzes','raw':'§ 50 Absatz 1 des\nWertpapierhandelsgesetzes','section':'50','law':'WpHG'},
 {'id':'wpug','text':'§ 30 Absatz 2 des Wertpapiererwerbs- und Übernahmegesetzes (WpÜG)','raw':'§ 30 Absatz 2 des Wertpapiererwerbs- und Übernahmegesetzes (WpÜG)','section':'30','law':'WpÜG'},
 {'id':'unknown-law','text':'§ 7 Absatz 2 des Sondergesetzes','raw':'§ 7 Absatz 2','section':'7','law':None,'issue':'UNRECOGNIZED_SUFFIX'},
 {'id':'no-prefix-across-prose','text':'§ 7 gilt. Absatz (2) gilt.','raw':'Absatz (2)','section':None,'law':None},
 {'id':'no-prefix-across-blank-line','text':'§ 7\n\nAbsatz (2)','raw':'Absatz (2)','section':None,'law':None},
 {'id':'header-adjacency','text':'§ 7\nAbsatz (2)','raw':'§ 7\nAbsatz (2)','section':None,'law':None,'header':{'start':0,'end':3},'issue':'SECTION_HEADER_IS_NOT_CITATION'},
 {'id':'missing-child','text':'§ 7 Absatz (2)(?)','raw':'§ 7 Absatz (2)','section':'7','law':None,'issue':'INCOMPLETE_PARAGRAPH'},
 {'id':'unattached-law','text':'Absatz 2 des SchVG','raw':'Absatz 2 des SchVG','section':None,'law':'SchVG','issue':'STATUTE_WITHOUT_SECTION'},
]

def main():
    start=time.monotonic()
    assert not (PREP/'candidate/reference_scope.py').exists()
    manifest=prior.read(prior.PRODUCTS)
    products={k:prior.read(ROOT/r['path']) for k,r in manifest['products'].items()}
    answer=prior.read(prior.HERE/'ordinary-answer.json.gz')
    text=products['P2']['payload']['assembly']['continuous_text']
    old=prior.read(prior.PREP/'expected.json')['source_expressions']
    expected=[]
    for (offset,raw,section,law,enclosing),candidate in zip(ROWS,old):
        assert offset==candidate['start']
        a=text.index(raw,max(0,offset-20),candidate['end']+140)
        b=a+len(raw)
        assert a<=offset<candidate['end']<=b
        expected.append({'paragraph_start':offset,'start':a,'end':b,'raw':raw,
            'explicit_section':section,'statute':law,'enclosing_section':enclosing,
            'scope_kind':'EXPLICIT_STATUTE' if law else ('EXPLICIT_SECTION' if section else 'RELATIVE_PARAGRAPH')})
    assert len(expected)==30
    prior.save(PREP/'expected.json',{'source_contexts':expected,'cases':CASES,
        'target_resolution_established':False,'general_recall_established':False})
    prior.save(PREP/'source-freeze.json',{'candidate_absent':True,
        'products_sha256':prior.digest(products),'ordinary_answer_sha256':prior.digest(answer),
        'expected_sha256':prior.sha(PREP/'expected.json'),'plan_sha256':prior.sha(ROOT/PLAN),
        'cases_sha256':prior.sha(Path(__file__)),'wall_seconds':time.monotonic()-start})
    print('PASS: froze 30 source contexts and 16 grammar cases before candidate creation')

if __name__=='__main__':main()
