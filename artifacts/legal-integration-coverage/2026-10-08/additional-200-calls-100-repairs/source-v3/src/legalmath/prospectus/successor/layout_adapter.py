"""Conservative exact-character maps from optional layout items to retained words."""
from .contracts import digest
import difflib


def map_layout(raw_units, document, *, source_sha256):
    if any(u["source_sha256"] != source_sha256 for u in raw_units):
        raise ValueError("Layout source edition mismatch")
    mappings, failures = [], []
    # Keep every text label, including footnotes, headers and legal margins.
    for item in document.get("texts", []):
        text = item.get("text", "")
        marker = item.get("marker", "") if item.get("enumerated") else ""
        if marker and not text.lstrip().startswith(marker):
            text = marker + " " + text
        provenance = item.get("prov", [])
        if len(provenance) != 1:
            failures.append({"item": item.get("self_ref"), "reason": "Multi-page/missing geometry requires explicit mapping"})
            continue
        prov = provenance[0]
        page = prov["page_no"]
        box = prov["bbox"]
        left, top, right, bottom = box["l"], box["t"], box["r"], box["b"]
        if box.get("coord_origin") == "BOTTOMLEFT":
            height = document["pages"][str(page)]["size"]["height"]
            top, bottom = height-top, height-bottom
        words = []
        for unit in raw_units:
            if unit["page"] != page:
                continue
            for word in unit.get("words", []):
                x0,y0,x1,y1 = word["bbox"]
                if left <= (x0+x1)/2 <= right and top <= (y0+y1)/2 <= bottom:
                    words.append((unit, word))
        # Word font metrics can differ within a line. Use the retained line
        # order, then the original word offset; sorting word y reordered bold
        # definitions and made exact text look lost in the first trial.
        words.sort(key=lambda pair: (round(pair[0].get("bbox", pair[1]["bbox"])[1], 1),
                                     pair[0].get("bbox", pair[1]["bbox"])[0], pair[1]["start"]))
        raw_chars = [(unit["id"], word["start"]+i, char) for unit, word in words
                     for i,char in enumerate(word["text"]) if not char.isspace()]
        candidate_chars = [(i, char) for i, char in enumerate(text) if not char.isspace()]
        if not raw_chars or [r[2] for r in raw_chars] != [r[1] for r in candidate_chars]:
            failures.append({"item": item.get("self_ref"), "label": item.get("label"), "page": page,
                "reason": "Candidate characters differ from retained words or reading order", "candidate": text,
                "retained": " ".join(word["text"] for unit, word in words)})
            continue
        mappings.append({"item": item.get("self_ref"), "label": item.get("label"), "page": page,
            "text": text, "structural_marker": marker, "characters": [{"output": c[0], "unit": r[0], "source_offset": r[1], "character": r[2]}
                                         for c,r in zip(candidate_chars, raw_chars)],
            "whitespace": "Candidate whitespace is formatting; original words and boxes remain unchanged"})
    return {"version": "layout-map.v1", "source_sha256": source_sha256, "raw_units_sha256": digest(raw_units),
            "mappings": mappings, "failures": failures, "raw_replaced": False,
            "margin_attachment": "Requires explicit relation; geometric adjacency does not establish governing scope"}


def project_layout(raw_units, document, *, source_sha256):
    """Bind structure proposals to raw quotations, preserving candidate changes.

    The old exact candidate-text mapper remains available. This projection emits
    raw source text, never normalized Docling text as a legal quotation. A known
    line-final hyphen deletion is recorded as an unaccepted display proposal;
    any other mismatch rejects that region. No fuzzy text search binds a region.
    """
    if len({u['id'] for u in raw_units}) != len(raw_units):
        raise ValueError('Duplicate source occurrence')
    if any(u['source_sha256'] != source_sha256 for u in raw_units):
        raise ValueError('Layout source edition mismatch')
    projections, failures, owners = [], [], {}
    for item in document.get('texts', []):
        try:
            if not item.get('self_ref'):
                raise ValueError('Missing region identity')
            prov = item.get('prov', [])
            if len(prov) != 1:
                raise ValueError('One-page geometry required for this bounded projection')
            page, box = prov[0]['page_no'], prov[0]['bbox']
            l,t,r,b = (box[k] for k in ('l','t','r','b'))
            origin = box.get('coord_origin')
            if origin == 'BOTTOMLEFT':
                height = document['pages'][str(page)]['size']['height']
                t,b = height-t,height-b
            elif origin != 'TOPLEFT':
                raise ValueError('Unknown geometry origin')
            if not l < r or not t < b:
                raise ValueError('Invalid region geometry')
            pieces=[]
            for unit in raw_units:
                if unit['page'] != page:
                    continue
                selected=[]
                for word in unit.get('words', []):
                    x0,y0,x1,y1=word['bbox']
                    if l <= (x0+x1)/2 <= r and t <= (y0+y1)/2 <= b:
                        a,z=word['start'],word['end']
                        if (type(a) is not int or type(z) is not int or not 0<=a<z<=len(unit['raw'])
                                or unit['raw'][a:z] != word['text'] or z-a != len(word['text'])):
                            raise ValueError('Raw word offset or quotation changed')
                        selected.append(word)
                if selected:
                    selected.sort(key=lambda w:w['start'])
                    for first,second in zip(selected,selected[1:]):
                        if first['end'] > second['start'] or unit['raw'][first['end']:second['start']].strip():
                            raise ValueError('Region selected discontinuous or overlapping raw words')
                    pieces.append((unit,selected[0]['start'],selected[-1]['end']))
            pieces.sort(key=lambda p:(round(p[0]['bbox'][1],1),p[0]['bbox'][0],p[1]))
            raw_text=''; chars=[]; segments=[]
            for unit,a,z in pieces:
                if raw_text:
                    raw_text+='\n'  # Declared formatting separator, not a PDF character.
                offset=len(raw_text)
                raw_text+=unit['raw'][a:z]
                segments.append({'unit':unit['id'],'start':a,'end':z,'quote':unit['raw'][a:z],
                                 'output_start':offset,'output_end':len(raw_text)})
                chars.extend({'output':offset+i-a,'unit':unit['id'],'source_offset':i,'character':unit['raw'][i]}
                             for i in range(a,z))
            candidate=item.get('text','')
            marker=item.get('marker','') if item.get('enumerated') else ''
            if marker and not candidate.lstrip().startswith(marker):
                candidate=marker+' '+candidate
            raw_indices=[c for c in chars if not c['character'].isspace()]
            left=''.join(c['character'] for c in raw_indices)
            right=''.join(c for c in candidate if not c.isspace())
            if not left:
                raise ValueError('No raw words in proposed region')
            changes=[]
            by_id={u['id']:u for u in raw_units}
            for tag,a,z,c,d in difflib.SequenceMatcher(None,left,right,autojunk=False).get_opcodes():
                if tag=='equal':
                    continue
                deleted=raw_indices[a:z]
                if (tag!='delete' or left[a:z]!='-' or len(deleted)!=1
                        or deleted[0]['source_offset']!=len(by_id[deleted[0]['unit']]['raw'])-1):
                    raise ValueError('Unaccounted candidate change: '+repr((left[a:z],right[c:d])))
                changes.append({'kind':'CANDIDATE_DELETED_LINE_FINAL_HYPHEN', 'source':deleted[0],
                                'candidate_nonspace_offset':c, 'disposition':'RAW_HYPHEN_PRESERVED; NORMALIZATION_NOT_ADMITTED'})
            key=item['self_ref']
            if any(p['item']==key for p in projections):
                raise ValueError('Duplicate region identity')
            for char in chars:
                source=(char['unit'],char['source_offset'])
                owners.setdefault(source,[]).append(key)
            projections.append({'item':key,'page':page,'label':item.get('label'),
                'text':raw_text,'candidate_text':candidate,'segments':segments,'characters':chars,
                'candidate_changes':changes,'separator':'LF between retained source segments',
                'status':'RAW_SOURCE_PROJECTED; STRUCTURE_REQUIRES_REVIEW'})
        except (KeyError,TypeError,ValueError) as exc:
            failures.append({'item':item.get('self_ref'),'reason':str(exc)})
    ambiguous={owner for rows in owners.values() if len(rows)>1 for owner in rows}
    if ambiguous:
        failures.extend({'item':key,'reason':'Overlapping source ownership across proposed regions'} for key in sorted(ambiguous))
        projections=[p for p in projections if p['item'] not in ambiguous]
    return {'version':'layout-source-projection.v1','source_sha256':source_sha256,
            'raw_units_sha256':digest(raw_units),'mappings':projections,'failures':failures,
            'raw_replaced':False,'legal_scope_inferred':False}


def evaluate_relationships(raw_units, mappings, proposed, reviewed):
    """Measure supplied edges against explicit reviewed targets, never constants."""
    from .anchors import bind
    graph={'units':raw_units}
    covered={(c['unit'],c['source_offset']) for m in mappings for c in m['characters']}
    def identity(edge):
        if edge.get('kind')!='governs' or not edge.get('scope'):
            raise ValueError('Typed relationship and explicit scope required')
        endpoints=[]
        for name in ('from','to'):
            spans=edge[name]
            if not spans:
                raise ValueError('Empty relationship endpoint')
            for span in spans:
                bind(graph,span)
                if any((span['unit'],i) not in covered for i in range(span['start'],span['end'])
                       if not span['quote'][i-span['start']].isspace()):
                    raise ValueError('Relationship lacks complete mapped endpoint')
            endpoints.append(tuple((s['unit'],s['start'],s['end'],s['source_sha256']) for s in spans))
        return (edge['kind'],edge['scope'],*endpoints)
    expected={identity(e) for e in reviewed}
    actual={identity(e) for e in proposed}
    return {'expected':len(expected),'proposed':len(actual),'correct':len(expected&actual),
            'missing':len(expected-actual),'wrong':len(actual-expected),
            'status':'PASS' if expected==actual else 'FAIL',
            'meaning_basis':'SUPPLIED_REVIEWED_TARGETS; NOT MODEL_INDEPENDENT_LEGAL_TRUTH'}
