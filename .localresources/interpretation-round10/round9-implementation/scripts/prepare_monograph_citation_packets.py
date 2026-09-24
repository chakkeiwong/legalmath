"""Prepare bounded source-reading packets; all support judgments stay unchecked.

Lexical retrieval selects passages to inspect, never certifies a citation.
"""
from collections import Counter
from pathlib import Path
import json
import math
import re
import zipfile

import fitz
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
REVIEW=ROOT/'docs/monograph/review/revision'
STOP=set('the a an and or of to in that this for is are as with by from not be on it which their its can but they has have we our was were at if all one into than these those each same more also such may must should will result evidence rule source claim paper section chapter appendix using used use legal model'.split())


def words(text):
    return [w for w in re.findall(r'[a-z][a-z0-9-]{2,}',text.lower()) if w not in STOP]


def textual(name,raw):
    if name.endswith('.json'):
        data=json.loads(raw)
        if isinstance(data,dict) and 'html' in data:
            return BeautifulSoup(data['html'],'html.parser').get_text(' ',strip=True)
    if name.endswith('.html'):
        return BeautifulSoup(raw,'html.parser').get_text(' ',strip=True)
    return raw


def source_sections(path):
    if path.suffix=='.pdf':
        assert path.read_bytes()[:4]==b'%PDF',str(path)
        with fitz.open(path) as pdf:
            return [(f'PDF page {i+1}',p.get_text()) for i,p in enumerate(pdf)]
    if path.suffix=='.zip':
        rows=[]
        with zipfile.ZipFile(path) as z:
            for i in z.infolist():
                if i.file_size>2_000_000 or not i.filename.endswith(('.md','.txt','.py','.json','.java','.fst','.ml')):
                    continue
                try: rows.append((i.filename,textual(i.filename,z.read(i).decode('utf8'))))
                except (UnicodeDecodeError,json.JSONDecodeError): continue
        return rows
    if path.suffix=='.html':
        return [(path.name,BeautifulSoup(path.read_bytes(),'html.parser').get_text(' ',strip=True))]
    return [(path.name,textual(path.name,path.read_text()))]


def main():
    inv=json.loads((REVIEW/'inventory.json').read_text())
    sources=json.loads((ROOT/'docs/papers/monograph-citation-archive.json').read_text())['sources']
    out=REVIEW/'citation-packets';out.mkdir(exist_ok=True)
    for source in sources:
        claims=[c for c in inv['citation_occurrences'] if c['key']==source['key']]
        if not claims:continue
        chunks=[]
        for location,content in source_sections(ROOT/source['path']):
            tokens=content.split()
            for start in range(0,len(tokens),180):
                segment=' '.join(tokens[start:start+240])
                chunks.append({'location':location,'word_offset':start,'text':segment})
        counts=[Counter(words(c['text'])) for c in chunks]
        df=Counter(w for c in counts for w in c)
        selected=set()
        for claim in claims:
            q=set(words(claim['context_tex']))
            scored=[(sum((1+math.log(len(chunks)/(1+df[w])))*min(c[w],3) for w in q if c[w]),i) for i,c in enumerate(counts)]
            selected.update(i for score,i in sorted(scored,reverse=True)[:2])
        packet={'source':source,'claims':claims,'candidate_passages':[dict(chunks[i],passage_id=i) for i in sorted(selected)],
                'status':'RETRIEVAL_ONLY_NOT_READING_EVIDENCE','selection':'Two lexical matches per occurrence; inspect broader sections and equations as needed.'}
        (out/(source['key']+'.json')).write_text(json.dumps(packet,indent=2,ensure_ascii=False)+'\n')
    print(f'Prepared {len(list(out.glob("*.json")))} unchecked reading packets.')


if __name__=='__main__':
    main()
