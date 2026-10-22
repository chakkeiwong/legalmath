"""Bounded supplied-form proposals with exact original source intervals."""
import hashlib
import re
import unicodedata
from .definition_discovery import normalized, attached


def require(condition, message):
    if not condition:
        raise ValueError(message)

def split_compound(text, at, step):
    cursor=at
    gap=[]
    while 0<=cursor<len(text) and text[cursor] in ' \t\n\r\u00a0':
        gap.append(text[cursor])
        cursor+=step
    # Conservatively withhold a term separated from a dash by one line/space.
    # This does not join text, invent morphology, or cross a paragraph.
    return bool(gap) and len(re.findall(r'\r\n|[\r\n]',''.join(gap[::step])))<=1 and (
        0<=cursor<len(text) and (unicodedata.category(text[cursor])=='Pd' or text[cursor]=='\u00ad'))


def discover_forms(request):
    require(isinstance(request, dict), 'Form request must be a mapping')
    require(set(request)=={'text','text_sha256','forms','regions'}, 'Unexpected form request fields')
    text=request['text']
    require(isinstance(text,str) and 0<len(text)<=100000, 'Unsupported form source size/type')
    require(hashlib.sha256(text.encode()).hexdigest()==request['text_sha256'], 'Changed form source identity')
    forms=request['forms']
    require(isinstance(forms,list) and 0<len(forms)<=256, 'Invalid supplied form list')
    ids=set()
    for row in forms:
        require(isinstance(row,dict) and set(row)=={'id','text'}, 'Invalid supplied form')
        identity,form=row['id'],row['text']
        require(isinstance(identity,str) and identity and identity not in ids, 'Invalid supplied form identity')
        ids.add(identity)
        require(isinstance(form,str) and 0<len(form)<=256 and form==' '.join(form.split())
                and all(not c.isspace() or c==' ' for c in form), 'Form needs canonical single spaces')
        require(not form.startswith(' ') and not form.endswith(' '), 'Form has surrounding spaces')
    regions=request['regions']
    require(isinstance(regions,list) and 0<len(regions)<=256, 'Invalid form regions')
    last=0
    for region in regions:
        require(isinstance(region,list) and len(region)==2 and all(type(v) is int for v in region),
                'Invalid form region interval')
        a,b=region
        require(last<=a<b<=len(text), 'Overlapping or invalid form region')
        last=b
    found={}
    associations=0
    for region_index,(left,right) in enumerate(regions):
        plain,spans=normalized(text[left:right],left)
        for row in forms:
            form=row['text']
            cursor=0
            while True:
                start=plain.find(form,cursor)
                if start<0:
                    break
                end=start+len(form)
                cursor=start+1
                a,b=spans[start][0],spans[end-1][1]
                if (attached(text[a-1] if a else '') or attached(text[b:b+1])
                        or split_compound(text,a-1,-1) or split_compound(text,b,1)):
                    continue
                valid=True
                for i in range(start,end):
                    if plain[i]!=' ':
                        continue
                    x,y=spans[i]
                    gap=text[x:y]
                    if (any(c not in ' \t\n\r\u00a0' for c in gap)
                            or len(re.findall(r'\r\n|[\r\n]',gap))>1):
                        valid=False
                        break
                if not valid:
                    continue
                key=(a,b,form,region_index)
                require(key in found or len(found)<4096, 'Form proposal bound exceeded')
                associations+=1
                require(associations<=8192, 'Form association bound exceeded')
                value=found.setdefault(key,{'start':a,'end':b,'raw':text[a:b],
                    'normalized_form':form,'normalization_map':spans[start:end],
                    'region':region_index,'supplied_form_ids':[],'review_required':True,
                    'governing_scope':None,'meaning':None})
                value['supplied_form_ids'].append(row['id'])
    return {'version':'supplied-form-discovery.v1','text_sha256':request['text_sha256'],
        'uses':[found[k] for k in sorted(found)],'scope_admitted':False,'meaning_admitted':False,
        'general_recall_established':False,'excluded':['morphology','dehyphenation','paragraph crossing',
            'region crossing','legal scope inference','implicit or missing definitions']}

