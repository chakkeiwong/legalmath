"""Retain the bounded public-source search, with no legal acceptance claim."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,zipfile,xml.etree.ElementTree as ET
ROOT=Path('/home/chakwong/python/legalmath')
WORK=ROOT/'artifacts/legal-mission-control/2026-10-26/product-closure'
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def read(n):return json.loads((WORK/n).read_text())
name=read('hklii-name.json');note23=read('hklii-noteup-2023.json');note25=read('hklii-noteup-2025.json')
assert name['count']==len(name['results']) and isinstance(note23,list) and isinstance(note25,list)
assert not name.get('recommendation',{}).get('message','').startswith('Exception')
with zipfile.ZipFile(WORK/'hkcfi-2024-1819.docx') as z:
    document=ET.fromstring(z.read('word/document.xml'))
    text=' '.join(n.text or '' for n in document.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'))
assert 'Gatecon' in text and '1079' in text and 'constructive trust' in text
out=WORK/'hkcfi-2024-1819-official-text.txt'
with out.open('x') as f:f.write(text)
files=['hklii-search-entry.html','hklii-search-client.js','hklii-name.json','hklii-case.json',
    'hklii-noteup-2023.json','hklii-noteup-2025.json','hkcfi-2024-1819.json','hkcfi-2024-1819.docx',
    'hkcfi-2024-1819-official-text.txt','hkdc-2024-1628.json','hkdc-2026-1402.json']
value=dict(at_utc=datetime.now(timezone.utc).isoformat(),question='Bounded later treatment of the two Gatecoin judgments',
    baseline=ref(ROOT/'artifacts/legal-mission-control/2026-10-11/source-applicability/gatecoin-citation-search.json'),
    queries=[dict(endpoint='simplesearch',params=dict(searchstring='Gatecoin',disablefuzzy=True)),
        dict(endpoint='getappealhistory',params=dict(caseno='HCCW18/2019')),
        dict(endpoint='getcasenoteup',params=dict(abbr='hkcfi',year=2023,num=914)),
        dict(endpoint='getcasenoteup',params=dict(abbr='hkcfi',year=2025,num=493))],
    source_host='www.hklii.hk',name_count=name['count'],noteup_2023=note23,noteup_2025=note25,
    recovered_missing_name_search_case='[2024] HKCFI 1819',official_document_checked=True,
    result_note=ref(ROOT/'docs/implementation/legal-mission-control/results/product-closure-treatment-search-2026-10-26.md'),
    evidence=[ref(WORK/n) for n in files],provider_calls=0,scenario_seven_resolved=False,
    current_law_completeness=False,client_applicability_established=False,legal_acceptance=False)
with (WORK/'treatment-search-result.json').open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False)
print(json.dumps(dict(name_count=name['count'],noteup_2023=len(note23),noteup_2025=len(note25),official_checked=True)))
