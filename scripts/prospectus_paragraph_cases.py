"""Manually enumerated paragraph syntax; no candidate parser builds expectations."""
from pathlib import Path
import json,time
from scripts import prospectus_cycle_disposition as source
ROOT,AUTH=source.ROOT,source.AUTH
PREP=AUTH/'reviews/paragraph-discovery-342'
PLAN='docs/plans/prospectus-paragraph-discovery-2026-10-19.md'
ROWS=[
 (425,'Absatz (4)',[['4']],[]),(2371,'Absatz (b)',[['b']],[]),
 (2393,'Absatz (3)',[['3']],[]),(2557,'Absatz (2)',[['2']],[]),
 (6661,'Absatz (1)',[['1']],[]),(7891,'Absatzes (2)',[['2']],[]),
 (8123,'Absatz (2)',[['2']],[]),(8385,'Absatz (2)',[['2']],[]),
 (8571,'Absatz (3)(b)',[['3','b']],[]),(12522,'Absatz (1)',[['1']],[]),
 (13856,'Absatz (2)',[['2']],[]),(15056,'Absatz 2',[['2']],[]),
 (15993,'Absatz (3)',[['3']],[]),(17340,'Absatz (b)',[['b']],[]),
 (18972,'Absatz (b)',[['b']],[]),(21362,'Absatzes (2)',[['2']],[]),
 (21506,'Absatzes [(5)]',[['5']],[]),(28161,'Absatz 1',[['1']],[]),
 (28957,'Absatz (2)',[['2']],[]),(31489,'Absatz (1)(b) und/oder (1)(c)',[['1','b'],['1','c']],['und/oder']),
 (31593,'Absatz (1)(a) und (1)(d) bis (g)',[['1','a'],['1','d'],['g']],['und','bis']),
 (31981,'Absatz (1)',[['1']],[]),
 (33951,'Unterabsätzen (a), (b), (c) und (d)',[['a'],['b'],['c'],['d']],[',',',','und']),
 (34965,'Absatz 2',[['2']],[]),(35663,'Absatz 3',[['3']],[]),
 (39303,'Absatz (a)(ii) und (iii)',[['a','ii'],['iii']],['und']),
 (40687,'Absatz 1',[['1']],[]),(43076,'Absatz (1)',[['1']],[]),
 (43200,'Absatz (1)',[['1']],[]),(43640,'Absatz [4]',[['4']],[]),
]
CASES=[
 {'id':'bare','text':'gemäß Absatz 12.','raw':'Absatz 12','paths':[['12']],'connectors':[]},
 {'id':'bracket','text':'Absatz [(5)] dieses § 5','raw':'Absatz [(5)]','paths':[['5']],'connectors':[]},
 {'id':'square','text':'Absatz [4] gilt.','raw':'Absatz [4]','paths':[['4']],'connectors':[]},
 {'id':'compound','text':'§ 1\nAbsatz (3)(b).','raw':'Absatz (3)(b)','paths':[['3','b']],'connectors':[]},
 {'id':'split-components','text':'Absatz (1)\n(b) gilt.','raw':'Absatz (1)\n(b)','paths':[['1','b']],'connectors':[]},
 {'id':'range','text':'Absatz (1)(d) bis (g)','raw':'Absatz (1)(d) bis (g)','paths':[['1','d'],['g']],'connectors':['bis']},
 {'id':'roman','text':'Absatz (a)(ii) und (iii)','raw':'Absatz (a)(ii) und (iii)','paths':[['a','ii'],['iii']],'connectors':['und']},
 {'id':'list','text':'Unterabsätzen (a), (b) und (d)','raw':'Unterabsätzen (a), (b) und (d)','paths':[['a'],['b'],['d']],'connectors':[',','und']},
 {'id':'or','text':'Absatz (1) oder (2)','raw':'Absatz (1) oder (2)','paths':[['1'],['2']],'connectors':['oder']},
 {'id':'and-or','text':'Absatz (1)(b) und/oder (1)(c)','raw':'Absatz (1)(b) und/oder (1)(c)','paths':[['1','b'],['1','c']],'connectors':['und/oder']},
 {'id':'case','text':'ABSATZ (IV)','raw':'ABSATZ (IV)','paths':[['IV']],'connectors':[]},
 {'id':'unclosed','text':'Absatz [(5)','issue':'MALFORMED_OR_UNSUPPORTED_LABEL'},
 {'id':'mismatched','text':'Absatz [4)','issue':'MALFORMED_OR_UNSUPPORTED_LABEL'},
 {'id':'word-label','text':'Absatz (foo)','issue':'MALFORMED_OR_UNSUPPORTED_LABEL'},
 {'id':'suffix','text':'Absatz 2a','issue':'MALFORMED_OR_UNSUPPORTED_LABEL'},
 {'id':'missing-list','text':'Absatz (1) und','issue':'INCOMPLETE_LIST'},
 {'id':'bad-child','text':'Absatz (1)(?)','issue':'MALFORMED_OR_UNSUPPORTED_LABEL'},
 {'id':'embedded','text':'UmsatzAbsatz (2)','absent':True},
 {'id':'no-number','text':'Der Absatz ist lang.','issue':'MALFORMED_OR_UNSUPPORTED_LABEL'},
 {'id':'implicit','text':'Für die Zwecke des Vorstehenden','absent':True},
 {'id':'no-introducer','text':'(a) Die Emittentin zahlt.','absent':True},
]

def main():
    start=time.monotonic();assert not (PREP/'candidate/paragraph_references.py').exists()
    manifest=source.read(source.PRODUCTS);products={k:source.read(ROOT/r['path']) for k,r in manifest['products'].items()}
    answer=source.read(source.HERE/'ordinary-answer.json.gz')
    text=products['P2']['payload']['assembly']['continuous_text'];rows=[]
    for position,raw,paths,connectors in ROWS:
        assert text[position:position+len(raw)]==raw,(position,raw)
        rows.append({'start':position,'end':position+len(raw),'raw':raw,'paths':paths,'connectors':connectors})
    assert len(rows)==30
    save=source.save
    save(PREP/'expected.json',{'source_expressions':rows,'cases':CASES,
        'general_recall_established':False,'target_resolution_established':False})
    save(PREP/'source-freeze.json',{'candidate_absent':True,'products_sha256':source.digest(products),
        'ordinary_answer_sha256':source.digest(answer),'text_sha256':source.digest(text.encode()),
        'expected_sha256':source.sha(PREP/'expected.json'),'plan_sha256':source.sha(ROOT/PLAN),
        'cases_sha256':source.sha(Path(__file__)),'wall_seconds':time.monotonic()-start})
    print(json.dumps({'status':'PASS','source_expressions':len(rows),'grammar_cases':len(CASES),'candidate_absent':True}))

if __name__=='__main__':main()
