"""Document-structure and rendered-label checks for retained legal sources."""
from pathlib import Path
import re
import zipfile
import subprocess
import unicodedata
from xml.etree import ElementTree as ET

from scripts.legal_integration_master import ROOT, BASE
from scripts.legal_mission_execution import read, save, ref, verify, require

NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
TAG='{'+NS['w']+'}'


def rendered_text(text):
    lines=[]
    for line in text.splitlines():
        # The court rendering has margin letters on both sides. They are not
        # text of a judgment or a continuation of the paragraph.
        line=re.sub(r'^\s*[A-V]\s{2,}', '', line)
        line=re.sub(r'\s{2,}[A-V]\s*$', '', line)
        if re.fullmatch(r'\s*[A-V]?\s*',line):continue
        lines.append(line.strip())
    return ' '.join(' '.join(lines).split())


def visible_label(rendered, text, label):
    prefix=' '.join(text.split())[:55].rstrip()
    return bool(re.search(r'(?<![\d.])'+re.escape(label)+r'\s+'+re.escape(prefix),rendered))


def judgment(name, directory):
    previous=read(ROOT/BASE/'reviewed-reopening/corpus-audit'/(name+'-numbering.json'))
    for key in ('source','derivative','rendered'):verify(ROOT,previous[key])
    rendered=rendered_text((ROOT/previous['rendered']['path']).read_text())
    with zipfile.ZipFile(ROOT/previous['source']['path']) as archive:
        document=ET.fromstring(archive.read('word/document.xml'))
        paragraphs=document.findall('.//w:body/w:p',NS)
        notes=ET.fromstring(archive.read('word/footnotes.xml'))
    leads={r['body_paragraph_position']:r for r in previous['main_leads']}
    main=[];structural=[];owner=None;region='front matter';last=max(leads)
    note_order=list(dict.fromkeys(n.get(TAG+'id') for n in document.findall('.//w:footnoteReference',NS)))
    note_owners={nid:[] for nid in note_order}
    for position,p in enumerate(paragraphs):
        text=''.join(t.text or '' for t in p.findall('.//w:t',NS))
        if not text.strip():continue
        style=p.find('w:pPr/w:pStyle',NS)
        style=style.get(TAG+'val','') if style is not None else ''
        heading=style.startswith('H-') or text.strip()=='ANNEXURE' or re.fullmatch(r'Issue \d+',text.strip())
        if position in leads:
            owner=leads[position]['locator'];region='reasons'
            label=owner[1:]+'.'
            main.append({'locator':owner,'position':position,'display_label':label,
                'rendered_label_verified':visible_label(rendered,text,label),'text':text})
        elif heading:
            owner=None;region='annexure' if ('ANNEXURE' in text or text.strip().startswith('Issue ')) else 'schedule' if text.startswith('Schedule') else 'heading'
        elif position>last and text.strip()=='(Linda Chan)':
            owner=None;region='signature and appearances'
        row={'position':position,'text':text,'main_owner':owner,'region':region,'style':style,
            'footnote_ids':[n.get(TAG+'id') for n in p.findall('.//w:footnoteReference',NS)]}
        for nid in row['footnote_ids']:note_owners[nid].append({'position':position,'main_owner':owner,'region':region})
        structural.append(row)
    note_rows=[]
    for note in notes:
        nid=note.get(TAG+'id')
        if int(nid)<=0:continue
        text=' '.join(''.join(t.text or '' for t in p.findall('.//w:t',NS)) for p in note.findall('.//w:p',NS))
        display=str(note_order.index(nid)+1) if nid in note_order else None
        note_rows.append({'ooxml_id':nid,'display':display,'owners':note_owners.get(nid,[]),
            'text':text,'rendered_display_verified':bool(display and visible_label(rendered,text,display))})
    require(all(r['main_owner'] is None for r in structural if r['region'] in ('annexure','schedule','signature and appearances')),
            'Back matter assigned to last main paragraph')
    unresolved=[{'kind':'main-label','locator':r['locator']} for r in main if not r['rendered_label_verified']]
    unresolved += [{'kind':'footnote-display','id':r['ooxml_id']} for r in note_rows if not r['rendered_display_verified']]
    value={'profile':'judgment-ownership-structure.v1','source':previous['source'],'rendered':previous['rendered'],
        'main_paragraphs':main,'components':structural,'footnotes':note_rows,
        'heading_and_back_matter_excluded':True,'unresolved':unresolved,
        'full_document_qualified':False,
        'remaining':['Nested subparagraph/annexure/schedule display labels require individual review.',
                     'Rendered prefix checks establish labels only; complete passage fidelity and legal warrants are separate.']}
    save(directory/'ownership.json',value)
    return {'ownership':ref(ROOT,directory/'ownership.json'), 'main_labels_verified':sum(r['rendered_label_verified'] for r in main),
        'main_labels_total':len(main),'footnote_labels_verified':sum(r['rendered_display_verified'] for r in note_rows),
        'footnotes_total':len(note_rows),'_node_status':'BLOCKED',
        '_conclusion':name+': heading/signature/annexure ownership separated; main and footnote labels checked against rendering; nested labels/full fidelity remain open.'}


def assess(tid,envelope,directory):
    from scripts.legal_integration_master import PROGRAM
    if read(ROOT/PROGRAM).get('prerequisite_repair'):
        return (judgment_fidelity('gatecoin-'+tid[-4:], directory)
                if tid.endswith(('2023','2025')) else handbook_fidelity(envelope, directory))
    if tid.endswith(('2023','2025')):return judgment('gatecoin-'+tid[-4:],directory)
    from scripts.legal_integration_substantive_continuation import ownership
    result=ownership(tid,envelope,directory)
    pages=[]
    for unit in envelope['source_packet']['units']:
        if not unit['unit_id'].startswith('handbook.'):continue
        matches=list(re.finditer(r'(?m)^\s*(\d+\.\d+[A-Z]?)\s+',unit['text']))
        pages.append({'unit_id':unit['unit_id'],'clause_starts':[{'label':m.group(1),'start':m.start()} for m in matches],
            'status':'PAGE_LOCAL_CANDIDATES; CROSS_PAGE_AND_RENDERED_BOUNDARIES_UNQUALIFIED'})
    save(directory/'handbook-clause-candidates.json',pages)
    result['clause_candidates']=ref(ROOT,directory/'handbook-clause-candidates.json')
    return result


def normalized(text):
    """Typography and whitespace only; never delete digits or punctuation."""
    return ''.join(unicodedata.normalize('NFKC', text).split())


def rendered_streams(pdf, directory):
    """Retain PDF coordinates and separate the court's body and footnote fonts."""
    target = directory/'rendered-positions.xhtml'
    data = subprocess.check_output(['pdftotext', '-bbox-layout', str(pdf), '-'], timeout=60)
    target.write_bytes(data)
    namespace = {'h': 'http://www.w3.org/1999/xhtml'}
    streams = {'body': '', 'footnotes': ''}
    positions = {'body': [], 'footnotes': []}
    for page_number, page in enumerate(ET.fromstring(data).findall('.//h:page', namespace), 1):
        rows = []
        for line in page.findall('.//h:line', namespace):
            words = [w for w in line if float(w.get('xMin')) >= 65 and float(w.get('xMax')) <= 540
                     and 65 <= float(w.get('yMin')) <= 790]
            if not words:
                continue
            y = min(float(w.get('yMin')) for w in words)
            height = max(float(w.get('yMax'))-float(w.get('yMin')) for w in words)
            rows.append((y, 'body' if height >= 14 else 'footnotes', words))
        groups = []
        for y, kind, words in sorted(rows, key=lambda r: r[0]):
            if groups and abs(groups[-1][0]-y) < 1:
                groups[-1][2].extend(words)
                if kind == 'body': groups[-1][1] = kind
            else:
                groups.append([y, kind, list(words)])
        for y, kind, words in groups:
            words.sort(key=lambda w: float(w.get('xMin')))
            text = ''.join(normalized(w.text or '') for w in words)
            start = len(streams[kind]); streams[kind] += text
            positions[kind].append({'page': page_number, 'y': y, 'start': start,
                'end': len(streams[kind]), 'text': text})
    save(directory/'rendered-streams.json', {'streams': streams, 'positions': positions,
        'normalization': 'NFKC and whitespace only; digits and punctuation preserved',
        'geometry': 'Retained court rendering: central x 65..540, y 65..790; main/quotation line height >=14.'})
    return streams, positions


def paragraph_text(paragraph, note_labels):
    parts = []
    for node in paragraph.iter():
        if node.tag == TAG+'t': parts.append(node.text or '')
        elif node.tag in (TAG+'tab', TAG+'br'): parts.append(' ')
        elif node.tag == TAG+'footnoteReference': parts.append(note_labels[node.get(TAG+'id')])
    return ''.join(parts)


def number_labels(document, numbering):
    """Resolve explicit Word numbering, including per-list starts and restarts."""
    abstracts = {n.get(TAG+'abstractNumId'): n for n in numbering.findall('w:abstractNum', NS)}
    numbers = {n.get(TAG+'numId'): n for n in numbering.findall('w:num', NS)}
    counters, labels = {}, {}
    def val(node, field, default=None):
        child = node.find('w:'+field, NS)
        return child.get(TAG+'val') if child is not None else default
    def format_value(n, fmt):
        if fmt == 'decimal': return str(n)
        if fmt in ('lowerLetter', 'upperLetter') and 1 <= n <= 26:
            return chr((97 if fmt == 'lowerLetter' else 65)+n-1)
        if fmt in ('lowerRoman', 'upperRoman') and 1 <= n < 40:
            result = ''; remaining = n
            for value, symbol in ((10,'x'),(9,'ix'),(5,'v'),(4,'iv'),(1,'i')):
                while remaining >= value: result += symbol; remaining -= value
            return result if fmt == 'lowerRoman' else result.upper()
        raise ValueError('Unsupported numbered display '+str((n,fmt)))
    for paragraph in document.findall('.//w:body//w:p', NS):
        prop = paragraph.find('w:pPr/w:numPr', NS)
        if prop is None: continue
        num_id, level = val(prop,'numId'), int(val(prop,'ilvl','0'))
        if num_id == '0': continue
        number = numbers[num_id]; abstract = abstracts[val(number,'abstractNumId')]
        levels = {int(n.get(TAG+'ilvl')): n for n in abstract.findall('w:lvl', NS)}
        overrides = {int(n.get(TAG+'ilvl')): n for n in number.findall('w:lvlOverride', NS)}
        def level_node(k):
            override = overrides.get(k)
            node = override.find('w:lvl',NS) if override is not None else None
            return node if node is not None else levels[k]
        state = counters.setdefault(num_id,{})
        for k in list(state):
            restart = int(val(level_node(k),'lvlRestart',str(k)))
            if k > level and restart and level < restart: del state[k]
        node = level_node(level)
        start = val(overrides[level],'startOverride') if level in overrides else None
        state[level] = state[level]+1 if level in state else int(start or val(node,'start','1'))
        template = val(node,'lvlText','')
        label = re.sub(r'%([1-9])', lambda m: format_value(
            state.get(int(m.group(1))-1,1), val(level_node(int(m.group(1))-1),'numFmt','decimal')), template)
        labels[id(paragraph)] = {'display':label,'num_id':num_id,'level':level}
    return labels


def verify_tables(document, rows, note_labels, directory):
    """Compare complete cells at the Word grid's rendered coordinates."""
    ns = {'h':'http://www.w3.org/1999/xhtml'}
    pages = ET.parse(directory/'rendered-positions.xhtml').findall('.//h:page',ns)
    body_lines = read(directory/'rendered-streams.json')['positions']['body']
    body = document.find('w:body',NS); children = list(body)
    direct = {id(p):i for i,p in enumerate(document.findall('.//w:body/w:p',NS))}
    indexed = {r['position']:r for r in rows if r['container']=='body'}
    table_rows = [r for r in rows if r['container']=='table']; cursor = 0; results = []
    for table_id, table in enumerate(body.findall('w:tbl',NS)):
        child_index = children.index(table)
        prev = next(indexed[direct[id(p)]] for p in reversed(children[:child_index])
                    if id(p) in direct and direct[id(p)] in indexed and indexed[direct[id(p)]]['matches'])
        after = next(indexed[direct[id(p)]] for p in children[child_index+1:]
                    if id(p) in direct and direct[id(p)] in indexed and indexed[direct[id(p)]]['matches'])
        allowed_pages = range(prev['matches'][-1]['pages'][-1],after['matches'][0]['pages'][0]+1)
        indent = table.find('w:tblPr/w:tblInd',NS)
        left = 79.3 + (float(indent.get(TAG+'w'))/20 if indent is not None else 0)
        widths = [float(c.get(TAG+'w'))/20 for c in table.findall('w:tblGrid/w:gridCol',NS)]
        edges = [left]
        for width in widths: edges.append(edges[-1]+width)
        expected_rows = []
        for tr in table.findall('w:tr',NS):
            expected_rows.append([''.join(normalized(paragraph_text(p,note_labels)) for p in tc.findall('w:p',NS))
                for tc in tr.findall('w:tc',NS)])
        candidates = []
        for page_number in allowed_pages:
            columns = []
            for col in range(len(widths)):
                words = [w for w in pages[page_number-1].findall('.//h:word',ns)
                    if edges[col] <= float(w.get('xMin')) < edges[col+1]
                    and float(w.get('xMax')) <= edges[col+1]+1 and 65<float(w.get('yMin'))<710]
                words.sort(key=lambda w:(round(float(w.get('yMin'))),float(w.get('xMin'))))
                columns.append(words)
            anchors = []
            for cells in expected_rows:
                col = next(i for i,t in enumerate(cells) if t)
                stream = ''.join(normalized(w.text or '') for w in columns[col])
                hits = [m.start() for m in re.finditer(re.escape(cells[col]),stream)]
                if len(hits) != 1: break
                offset = 0
                for w in columns[col]:
                    end = offset+len(normalized(w.text or ''))
                    if offset <= hits[0] < end:
                        anchors.append(float(w.get('yMin'))); break
                    offset = end
            if len(anchors) != len(expected_rows) or anchors != sorted(set(anchors)): continue
            cells_checked = []
            for ri,cells in enumerate(expected_rows):
                # Bound the last row by the next verified body paragraph, not
                # an estimated line count that could hide extra table text.
                following = [line['y'] for line in body_lines if line['page'] == page_number
                    and line['start'] <= after['matches'][0]['start'] < line['end']]
                end = anchors[ri+1] if ri+1<len(anchors) else min(following, default=710)
                for ci,target in enumerate(cells):
                    selected = [w for w in columns[ci] if anchors[ri]-1<=float(w.get('yMin'))<end-1]
                    actual = ''.join(normalized(w.text or '') for w in selected)
                    cells_checked.append({'row':ri,'column':ci,'expected':target,'rendered':actual,
                        'match':target==actual,'page':page_number,'bounds':[edges[ci],anchors[ri]-1,edges[ci+1],end-1]})
            candidates.append(cells_checked)
        match = len(candidates)==1 and all(c['match'] for c in candidates[0])
        results.append({'table':table_id,'grid_points':edges,'cells':candidates[0] if len(candidates)==1 else [],
            'qualified':match,'candidate_count':len(candidates)})
        for p in table.findall('.//w:p',NS):
            if not paragraph_text(p,note_labels).strip():continue
            table_rows[cursor]['full_text_and_label_verified'] = match
            table_rows[cursor]['table_evidence'] = {'table':table_id,'qualified':match}
            table_rows[cursor]['owner'] = prev['owner']
            table_rows[cursor]['region'] = prev['region']
            cursor += 1
    return results


def judgment_fidelity(name, directory):
    directory.mkdir(parents=True, exist_ok=True)
    previous = judgment(name, directory)
    value = read(directory/'ownership.json')
    pdf = ROOT/BASE/'corpus-work'/(name+'.pdf')
    streams, positions = rendered_streams(pdf, directory)
    with zipfile.ZipFile(ROOT/value['source']['path']) as archive:
        document = ET.fromstring(archive.read('word/document.xml'))
        notes = ET.fromstring(archive.read('word/footnotes.xml'))
        numbering = ET.fromstring(archive.read('word/numbering.xml'))
    direct = {id(p): i for i,p in enumerate(document.findall('.//w:body/w:p',NS))}
    labels = {r['ooxml_id']: r['display'] for r in value['footnotes']}
    display = number_labels(document, numbering)
    owners = {r['position']:r for r in value['components']}
    rows = []
    for p in document.findall('.//w:body//w:p',NS):
        text = paragraph_text(p, labels)
        if not text.strip(): continue
        position = direct.get(id(p))
        row = {'position':position, 'container':'body' if position is not None else 'table',
               'text':text, 'owner': owners.get(position,{}).get('main_owner'),
               'region':owners.get(position,{}).get('region','table'),
               'footnote_ids':[n.get(TAG+'id') for n in p.findall('.//w:footnoteReference',NS)],
               'numbering':display.get(id(p))}
        target = normalized((display.get(id(p),{}).get('display',''))+text)
        hits = [m.start() for m in re.finditer('(?='+re.escape(target)+')', streams['body'])]
        row['matches'] = [{'start':i,'end':i+len(target), 'pages':sorted({l['page']
            for l in positions['body'] if l['start'] < i+len(target) and l['end'] > i})} for i in hits]
        row['full_text_and_label_verified'] = len(hits) == 1
        rows.append(row)
    body_rows = [r for r in rows if r['container']=='body']
    for i,row in enumerate(body_rows):
        if row['full_text_and_label_verified']:continue
        lower = next((r['matches'][0]['end'] for r in reversed(body_rows[:i]) if r['full_text_and_label_verified']),0)
        upper = next((r['matches'][0]['start'] for r in body_rows[i+1:] if r['full_text_and_label_verified']),len(streams['body']))
        candidates = [m for m in row['matches'] if lower<=m['start'] and m['end']<=upper]
        if len(candidates)==1:
            row['matches'] = candidates; row['full_text_and_label_verified'] = True
            row['disambiguation'] = 'Between adjacent verified Word paragraphs in document order.'
    tables = verify_tables(document,rows,labels,directory)
    note_owners = {nid:[] for nid in labels}
    for row in rows:
        for nid in row['footnote_ids']:
            note_owners[nid].append({'position':row['position'],'main_owner':row['owner'],
                'region':row['region'],'container':row['container'],
                'table':row.get('table_evidence',{}).get('table')})
    for note in value['footnotes']:
        note['owners'] = note_owners[note['ooxml_id']]
    footnotes = []
    for note in notes:
        nid = note.get(TAG+'id')
        if int(nid) <= 0: continue
        text = ' '.join(paragraph_text(p,labels) for p in note.findall('.//w:p',NS))
        target = normalized(labels[nid]+text)
        hits = [m.start() for m in re.finditer(re.escape(target), streams['footnotes'])]
        footnotes.append({'ooxml_id':nid,'display':labels[nid], 'text':text,
            'matches':hits,'owners':note_owners[nid],
            'full_text_and_label_verified':len(hits)==1 and bool(note_owners[nid])})
    unresolved = [{'kind':r['container'],'position':r['position'],'owner':r['owner'],
        'reason':'MISSING' if not r['matches'] else 'AMBIGUOUS'} for r in rows if not r['full_text_and_label_verified']]
    unresolved += [{'kind':'footnote','id':r['ooxml_id']} for r in footnotes if not r['full_text_and_label_verified']]
    value.update(profile='judgment-rendered-fidelity.v2', pdf=ref(ROOT,pdf),
        rendered_positions=ref(ROOT,directory/'rendered-positions.xhtml'),
        rendered_streams=ref(ROOT,directory/'rendered-streams.json'),
        full_components=rows, full_footnotes=footnotes, tables=tables, unresolved=unresolved,
        full_document_qualified=not unresolved,
        remaining=[] if not unresolved else ['Unmatched/ambiguous rendered components remain explicitly unqualified.'])
    save(directory/'ownership.json',value)
    main = {r['position']:r for r in rows if r['container']=='body'}
    return {'ownership':ref(ROOT,directory/'ownership.json'),
        'main_labels_verified':sum(main[r['position']]['full_text_and_label_verified'] for r in value['main_paragraphs']),
        'main_labels_total':len(value['main_paragraphs']),
        'components_verified':sum(r['full_text_and_label_verified'] for r in rows), 'components_total':len(rows),
        'footnotes_verified':sum(r['full_text_and_label_verified'] for r in footnotes), 'footnotes_total':len(footnotes),
        'unresolved_count':len(unresolved),'_node_status':'BLOCKED' if unresolved else 'SUCCEEDED',
        '_conclusion':name+': full paragraph/footnote/numbering comparison '+('qualified.' if not unresolved
            else 'retained; '+str(len(unresolved))+' rendered components remain unresolved.')}


def handbook_fidelity(envelope, directory):
    directory.mkdir(parents=True,exist_ok=True)
    supplement_ref = ref(ROOT,BASE/'corpus-work/source-supplement.json')
    supplement = read(ROOT/supplement_ref['path']); handbook = supplement['handbook']
    for key in ('current_pdf','current_headers','codes_index'): verify(ROOT,handbook[key])
    data = subprocess.check_output(['pdftotext','-layout',str(ROOT/handbook['current_pdf']['path']),'-'],timeout=60)
    (directory/'handbook-rendered.txt').write_bytes(data)
    pages = data.decode().split('\f')
    units = [u for u in envelope['source_packet']['units'] if u['unit_id'].startswith('handbook.')]
    rows=[]
    for unit in units:
        page = int(unit['unit_id'].split('page')[-1])
        rows.append({'unit_id':unit['unit_id'],'page':page,'section':'OPS' if page<=18 else 'UT',
            'complete_page_equal':unit['text']==pages[page-1],'text_hash':__import__('hashlib').sha256(unit['text'].encode()).hexdigest()})
    # Explicit section boundaries taken from the retained edition's section
    # title pages. A chapter number alone cannot identify the product code.
    require('Overarching Principles Section' in pages[6] and 'Unit Trusts' in pages[18], 'Handbook section boundaries changed')
    require('Chapter 7: Investment' in pages[46], 'UT chapter-six boundary changed')
    sections = [('OPS',7,18),('UT',24,46)]
    clauses = []
    for section,start,end in sections:
        text=''; offsets=[]
        for n in range(start,end+1):
            offsets.append((n,len(text),len(text)+len(pages[n-1])))
            text += pages[n-1]
        starts = list(re.finditer(r'(?m)^\s*(\d+\.\d+[A-Z]?)\s+(?=[A-Za-z])',text))
        for i,m in enumerate(starts):
            finish = starts[i+1].start() if i+1<len(starts) else len(text)
            passage = text[m.start():finish]
            involved=[n for n,a,b in offsets if a<finish and b>m.start()]
            clauses.append({'section':section,'label':m.group(1),'start':m.start(),'end':finish,
                'pages':involved,'text':passage,
                'boundary':'NEXT_CLAUSE' if i+1<len(starts) else 'VERIFIED_SECTION_OR_CHAPTER_END',
                'fully_delivered_pages':all(n in {r['page'] for r in rows} for n in involved)})
    general = [r for r in clauses if r['section']=='OPS' and r['label']=='6.8']
    unit_trust = [r for r in clauses if r['section']=='UT' and r['label']=='6.8']
    require(len(general)==len(unit_trust)==1, 'Ambiguous Handbook clause 6.8')
    old_quote = next(u['text'] for u in envelope['source_packet']['units'] if u['unit_id']=='d497635c84096.u0.0')
    sentence = '6.8 The scheme, or in the case of a unit trust, the trustee or the person so appointed by the trustee must maintain a register of holders.'
    equal = normalized(sentence) in normalized(unit_trust[0]['text']) and sentence in old_quote
    require(equal and 'Product Key Facts' in general[0]['text'],'General and product code conflated')
    relevant = [r for r in clauses if set(r['pages']) & {p['page'] for p in rows}]
    gaps = [{'section':r['section'],'clause':r['label'],'required_pages':r['pages']}
        for r in relevant if not r['fully_delivered_pages']]
    value={'profile':'handbook-passage-fidelity.v2','source':handbook['current_pdf'],
        'official_retrieval':supplement_ref,'index':handbook['codes_index'],'response_headers':handbook['current_headers'],
        'edition':handbook['pdf_edition'],'index_date':handbook['index_label'],
        'page_checks':rows,'clauses':relevant,'cross_page_delivery_gaps':gaps,
        'rendered':ref(ROOT,directory/'handbook-rendered.txt'),'unit_trust_6_8_matches_original':equal,
        'source_passages_qualified':all(r['complete_page_equal'] for r in rows),
        'full_document_qualified':False,
        'applicability':{'status':'CONDITIONAL','basis':'Retained official index and PDF identify the October 2024 fifth edition as retrieved on 13 October 2026. Section I 1.1-1.6 separates general principles, product-specific requirements and legal effect; UT 1.1 concerns authorization under SFO section 104.',
            'needed_facts':['Product type and authorization status','Relevant actor and transaction date','Applicable waivers, amendments and constitutive terms'],
            'not_established':'Exhaustive current-law/amendment search or applicability to an unspecified client.'}}
    save(directory/'handbook-ownership.json',value)
    failures = [r['unit_id'] for r in rows if not r['complete_page_equal']]
    return {'ownership':ref(ROOT,directory/'handbook-ownership.json'),'verified_pages':sum(r['complete_page_equal'] for r in rows),
        'pages':len(rows),'page_mismatches':failures,'cross_page_delivery_gaps':gaps,
        '_node_status':'BLOCKED' if gaps or failures else 'SUCCEEDED',
        '_conclusion':('Retained Handbook has page mismatches: '+', '.join(failures)+'. ' if failures else
            'Retained Handbook edition and exact pages verified; ')+ 'OPS/UT clause ownership distinguished; '
            + (str(len(gaps))+' cross-page delivery gaps remain; applicability is conditional.' if gaps else 'applicability remains conditional on product/date/actor facts.')}
