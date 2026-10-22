"""Optional quotation conventions; lexical candidates never establish meaning."""
import hashlib
from copy import deepcopy
from pathlib import Path
from .definition_discovery import normalized, attached, require
from .anchors import fields
from .contracts import bound_path, digest

PAIRS={'english':{'“':'”','"':'"'},
       'german':{'„':'“','"':'"'},
       'guillemets':{'«':'»','"':'"'}}
QUOTE_CHARACTERS=set('“”„«»"〝〞')
MAX_USES=20000
MAX_MAP_ENTRIES=200000
VERSION='unicode-label-review.v1'
KEY='unicode_label_review'


def _quote_pairs(plain,spans,region,convention):
    pairs=PAIRS[convention]
    closers=set(pairs.values())
    stack=[];invalid=False;found=[];issues=[]
    def issue(kind,index):
        issues.append({'kind':kind,'region':region,'start':spans[index][0],'end':spans[index][1]})
    for index,char in enumerate(plain):
        if stack and char==stack[-1][1]:
            opening,_=stack.pop()
            if not stack:
                if not invalid:found.append((opening,index))
                invalid=False
        elif char in pairs:
            if stack:
                invalid=True
                issue('NESTED_QUOTE',index)
            stack.append((index,pairs[char]))
        elif char in QUOTE_CHARACTERS:
            issue('UNMATCHED_QUOTE' if char in closers else 'UNSUPPORTED_QUOTE',index)
            if stack:invalid=True
    for index,_ in stack:issue('UNBALANCED_QUOTE',index)
    return found,issues


def discover(request):
    keys={'text','text_sha256','language','regions','quotation_convention'}
    require(isinstance(request,dict) and set(request)==keys,'Explicit bounded quotation request required')
    text=request['text']
    require(isinstance(text,str) and 0<len(text)<=100000,'Unsupported source size/type')
    identity=hashlib.sha256(text.encode()).hexdigest()
    require(request['text_sha256']==identity,'Changed source identity')
    language=request['language']
    require(isinstance(language,str) and bool(language),'Missing selected language')
    convention=request['quotation_convention']
    require(isinstance(convention,str) and convention in PAIRS,'Explicit supported quotation convention required')
    regions=request['regions']
    require(isinstance(regions,list) and 0<len(regions)<=256,'Missing/big region partition')
    cursor=0;ids=set()
    for region in regions:
        require(isinstance(region,dict) and set(region)=={'id','language','selected','start','end'},'Invalid region fields')
        require(isinstance(region['id'],str) and region['id'] and region['id'] not in ids,'Invalid region identity')
        ids.add(region['id'])
        require(type(region['start']) is int and type(region['end']) is int
                and region['start']==cursor<region['end']<=len(text),'Changed/nonpartitioning region offsets')
        require(type(region['selected']) is bool and isinstance(region['language'],str),'Invalid region selection')
        cursor=region['end']
    require(cursor==len(text),'Incomplete source partition')
    names=[];uses=[];issues=[];views=[];mapped=0
    for region in regions:
        if not region['selected'] or region['language']!=language:continue
        plain,spans=normalized(text[region['start']:region['end']],region['start'])
        views.append((region,plain,spans))
        pairs,found_issues=_quote_pairs(plain,spans,region['id'],convention)
        issues.extend(found_issues)
        for opening,closing in pairs:
            left,right=opening+1,closing
            while left<right and plain[left].isspace():left+=1
            while right>left and plain[right-1].isspace():right-=1
            if left==right:
                issues.append({'kind':'EMPTY_QUOTE','region':region['id'],
                               'start':spans[opening][0],'end':spans[closing][1]})
                continue
            require(len(names)<2048,'Quoted candidate bound exceeded')
            mapped+=right-left
            require(mapped<=MAX_MAP_ENTRIES,'Source mapping bound exceeded')
            a,b=spans[left][0],spans[right-1][1]
            names.append({'id':f'q:{len(names)}:{a}:{b}','region':region['id'],
                'start':a,'end':b,'raw':text[a:b],'label':plain[left:right],
                'quote_start':spans[opening][0],'quote_end':spans[closing][1],
                'normalization_map':spans[left:right],'kind':'QUOTED_LABEL_CANDIDATE',
                'review_required':True})
    labels={}
    for name in names:labels.setdefault(name['label'],[]).append(name['id'])
    for region,plain,spans in views:
        for label,candidates in labels.items():
            cursor=0
            while True:
                start=plain.find(label,cursor)
                if start<0:break
                end=start+len(label);cursor=start+1
                if attached(plain[start-1] if start else '') or attached(plain[end:end+1]):continue
                require(len(uses)<MAX_USES,'Literal use bound exceeded')
                mapped+=end-start
                require(mapped<=MAX_MAP_ENTRIES,'Source mapping bound exceeded')
                a,b=spans[start][0],spans[end-1][1]
                uses.append({'region':region['id'],'start':a,'end':b,'raw':text[a:b],
                    'label':label,'normalization_map':spans[start:end],'name_candidates':list(candidates),
                    'kind':'LITERAL_USE_CANDIDATE','review_required':True,'governing_scope':None})
    order=lambda row:(row['start'],row['end'],row['label'])
    names.sort(key=order);uses.sort(key=order)
    return {'version':'quoted-label-discovery.v2','text_sha256':identity,
        'language':language,'quotation_convention':convention,'names':names,'uses':uses,'issues':issues,
        'scope_admitted':False,'meaning_admitted':False,'general_recall_established':False,
        'unsupported_mechanisms':['unquoted declarations','single-quote disambiguation','morphology',
            'hyphen repair','page-header removal','legal scope and precedence','implicit definitions','nested quotations'],
        'limits':{'source_characters':100000,'regions':256,'names':2048,'uses':MAX_USES,
                  'mapping_entries':MAX_MAP_ENTRIES}}


def evaluate(products,ordinary,profile,root,*,expected_profile_sha256):
    keys={'version','products_sha256','ordinary_answer_sha256','sources','scope_admitted','meaning_admitted'}
    fields(profile,keys,keys)
    require(profile['version']==VERSION and digest(profile)==expected_profile_sha256,
            'Pinned lexical profile changed')
    require(profile['products_sha256']==digest(products) and profile['ordinary_answer_sha256']==digest(ordinary),
            'Lexical profile products or complete baseline changed')
    require(ordinary.get('report_sha256')==digest({k:v for k,v in ordinary.items() if k!='report_sha256'})
            and KEY not in ordinary,'Complete prior answer required')
    require(profile['scope_admitted'] is False and profile['meaning_admitted'] is False,
            'Lexical candidates cannot admit source scope or meaning')
    rows=profile['sources']
    require(isinstance(rows,list) and 1<=len(rows)<=8,'Bounded explicit text source list required')
    ids=set();reports=[]
    for row in rows:
        keys={'id','path','file_sha256','text_sha256','language','regions','quotation_convention'}
        fields(row,keys,keys)
        require(isinstance(row['id'],str) and bool(row['id']) and row['id'] not in ids,
                'Distinct source identities required')
        ids.add(row['id'])
        require(isinstance(row['path'],str) and bool(row['path']) and not Path(row['path']).is_absolute(),
                'Explicit repository-relative source path required')
        path=bound_path(root,row['path'])
        with path.open('rb') as stream:raw=stream.read(512*1024+1)
        require(len(raw)<=512*1024,'Source text byte bound exceeded')
        require(digest(raw)==row['file_sha256'],'Retained source text bytes changed')
        try:text=raw.decode('utf-8')
        except UnicodeDecodeError as error:raise ValueError('Explicit UTF8 text derivative required') from error
        request={k:deepcopy(row[k]) for k in ('text_sha256','language','regions','quotation_convention')}
        request['text']=text
        reports.append({'source':deepcopy(row),'report':discover(request),
            'authority_of_named_source':'NOT_ESTABLISHED','source_role':'SUPPLIED_TEXT_REVIEW'})
    return {'version':VERSION,'profile_sha256':digest(profile),'products_sha256':digest(products),
        'ordinary_answer_sha256':digest(ordinary),'sources':reports,
        'scope_admitted':False,'meaning_admitted':False,'general_legal_interpretation':False,
        'meaning':'Exact lexical proposals from supplied text; source authority, declarations and legal scope require separate analysis'}


def verify_answer(answer,ordinary,profile,products,root,*,expected_profile_sha256):
    require(answer.get('report_sha256')==digest({k:v for k,v in answer.items() if k!='report_sha256'}),
            'Lexical answer seal changed')
    require({k:v for k,v in answer.items() if k not in (KEY,'report_sha256')}
            =={k:v for k,v in ordinary.items() if k!='report_sha256'},
            'Lexical review changed the complete prior answer')
    require(answer.get(KEY)==evaluate(products,ordinary,profile,root,expected_profile_sha256=expected_profile_sha256),
            'Lexical review differs from actual source reconstruction')
    return {'status':'PASS','baseline_unchanged':True,'sources':len(profile['sources'])}
