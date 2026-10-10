"""Reviewed display-text transformations; raw quotations keep their own geometry."""
from .anchors import bind, fields
from .contracts import digest


def admit(graph, packet):
    from .admissions import review
    fields(packet, {'version','graph_sha256','review','entries'}, {'version','graph_sha256','review','entries'})
    if packet['version'] != 'reviewed-corrections.v1' or packet['graph_sha256'] != digest(graph):
        raise ValueError('Corrected-text source graph changed')
    review(packet['review'])
    entries, ids = [], set()
    raw_units = {u['id']:u for u in graph['units']}
    for row in packet['entries']:
        fields(row, {'id','source','operations','image_sha256'}, {'id','source','operations'})
        if not row['id'] or row['id'] in ids:
            raise ValueError('Distinct corrected-text identity required')
        ids.add(row['id'])
        bind(graph, row['source'])
        unit = raw_units[row['source']['unit']]
        # The actual producer uses 'retained-pymupdf-tesseract', without
        # 'ocr' in its method name. Image provenance must survive that route
        # and the retained text fallback, including missing-image failures.
        requires_image = ('image_sha256' in unit or 'ocr' in unit['method'].lower() or
                          unit['method'] in {'retained-pymupdf-tesseract', 'retained-original-text-or-blank'})
        image = unit.get('image_sha256')
        if requires_image and (not isinstance(image, str) or len(image) != 64 or
                               any(c not in '0123456789abcdef' for c in image) or
                               row.get('image_sha256') != image):
            raise ValueError('OCR correction requires the retained source-page image identity')
        raw = row['source']['quote']
        cursor, output, segments = 0, '', []
        for op in row['operations']:
            fields(op, {'kind','start','end','text','reason'}, {'kind','start','end','text','reason'})
            a,b = op['start'],op['end']
            if (type(a) is not int or type(b) is not int or not cursor == a <= b <= len(raw) or
                    not isinstance(op['text'],str) or not op['reason']):
                raise ValueError('Correction operations must cover the raw interval in order')
            kind, text = op['kind'], op['text']
            if (kind not in {'copy','replace','delete','insert','uncertain'} or
                    kind == 'copy' and (a == b or text != raw[a:b]) or
                    kind == 'replace' and (a == b or not text) or
                    kind == 'delete' and (a == b or text) or
                    kind == 'insert' and (a != b or not text) or
                    kind == 'uncertain' and (a == b or not text)):
                raise ValueError('Invalid corrected-text operation')
            source = {**row['source'], 'start':row['source']['start']+a,
                      'end':row['source']['start']+b, 'quote':raw[a:b]} if a < b else None
            segments.append({'kind':kind, 'start':len(output), 'end':len(output)+len(text),
                             'source':source, 'reason':op['reason'], 'bbox':None})
            output += text
            cursor = b
        if cursor != len(raw):
            raise ValueError('Corrected-text map leaves raw characters unaccounted for')
        entries.append({'id':row['id'], 'source':row['source'], 'text':output, 'text_sha256':digest(output.encode()),
                        'segments':segments, 'image_sha256':row.get('image_sha256'), 'bbox':None})
    return {'version':'admitted-corrections.v1','input_sha256':digest(packet),'entries':entries,'review':packet['review']}


def sources(graph, identity, start, end):
    entries = [r for r in graph.get('corrections',{}).get('entries',[]) if r['id'] == identity]
    if len(entries) != 1:
        raise ValueError('Unknown corrected-text identity')
    row = entries[0]
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(row['text']):
        raise ValueError('Invalid corrected-text span')
    result = []
    for seg in row['segments']:
        a,b = max(start,seg['start']),min(end,seg['end'])
        if a >= b:
            continue
        raw = seg['source']
        if seg['kind'] in {'insert','uncertain'}:
            raise ValueError('Inserted or uncertain text has no admitted raw semantic span')
        if seg['kind'] == 'replace':
            if (a,b) != (seg['start'],seg['end']):
                raise ValueError('Partial replacement has ambiguous raw correspondence')
            result.append(raw)
        else:
            left,right = a-seg['start'],b-seg['start']
            result.append({**raw,'start':raw['start']+left,'end':raw['start']+right,'quote':raw['quote'][left:right]})
    for source in result:
        bind(graph, source)
    return result
