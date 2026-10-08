"""Unlabelled first-reading schema and source-bound draft export admission.

Readers select spans and labels. Source hashes/quotes/offsets are recovered from
the actual CAS and immutable identity, not fields that readers must type.
Imported evidence retains its separate strict decoder in annotation_xmi.
"""
from . import annotation_xmi as xmi
from .annotation_bridge import export
from .contracts import digest

SPAN='webanno.custom.DraftEvidence'
RELATION='webanno.custom.DraftRelation'


def layers():
    result=xmi.project_layers()
    result=[row for row in result if row['name']==xmi.IDENTITY]
    for name,title,kind,names in ((SPAN,'Reading evidence','span',('groupId','label')),
                                 (RELATION,'Reading relations','relation',('relationId','kind'))):
        row={'name':name,'uiName':title,'type':kind,'description':'Unlabelled source reading; immutable edition checked on export',
             'enabled':True,'built_in':False,'readonly':False,'cross_sentence':True,'allow_stacking':True,
             'anchoring_mode':'CHARACTERS','overlap_mode':'ANY_OVERLAP','validation_mode':'ALWAYS',
             'features':[{'name':n,'uiName':n,'type':'uima.cas.String','enabled':True,'visible':True,'required':True,
                          'remember':False,'multi_value_mode':'NONE','link_mode':'NONE','curatable':True} for n in names]}
        if kind=='relation': row['attach_type']={'name':SPAN}
        result.append(row)
    return result


def empty(text,source):
    import cassis
    # Validate source hashes and text through the existing exchange validator.
    raw,types=xmi.encode(export(text,source,[],[]))
    cas=xmi.load_export(raw,types)
    ts=cas.typesystem
    for name,fields in ((SPAN,('groupId','label')),(RELATION,('relationId','kind'))):
        ts.create_type(name=name,supertypeName='uima.tcas.Annotation')
        for field in fields: ts.create_feature(name,name=field,rangeType='uima.cas.String')
    for field in ('Governor','Dependent'):
        ts.create_feature(RELATION,name=field,rangeType=SPAN)
    return cas.to_xmi().encode(),ts.to_xml().encode()


def decode(raw,source,text,*,types=None):
    cas=xmi.load_export(raw,types)
    identities=list(cas.select(xmi.IDENTITY))
    if len(identities)!=1:
        raise ValueError('One immutable source identity required')
    identity=identities[0]
    actual={'document':identity.document,'source_sha256':identity.sourceSHA,'text_sha256':identity.textSHA}
    if actual!=source or identity.exchangeVersion!='legalmath-xmi.v1':
        raise ValueError('Source edition changed')
    if cas.sofa_string!=text or digest(text.encode())!=actual['text_sha256']:
        raise ValueError('Source text changed')
    for legacy in (xmi.SPAN,xmi.RELATION):
        if cas.typesystem.contains_type(legacy) and list(cas.select(legacy)):
            raise ValueError('Mixed imported and authored evidence schemas')
    by_id={};grouped={}
    for ann in cas.select(SPAN):
        if not ann.groupId or not ann.groupId.strip() or not ann.label or not ann.label.strip() or not 0<=ann.begin<ann.end<=len(text):
            raise ValueError('Incomplete authored evidence')
        if not text[ann.begin:ann.end].strip():
            raise ValueError('Empty evidence selection')
        grouped.setdefault(ann.groupId,[]).append(ann);by_id[ann.xmiID]=ann
    heads={key:min(members,key=lambda a:(a.begin,a.end)).xmiID for key,members in grouped.items()}
    links=set();relations=[];ids=set()
    for edge in cas.select(RELATION):
        if not edge.relationId or edge.relationId in ids or not edge.kind:
            raise ValueError('Missing or duplicate relation identity')
        ids.add(edge.relationId)
        if any(a is None or a.xmiID not in by_id for a in (edge.Governor,edge.Dependent)):
            raise ValueError('Dangling authored relation')
        a,b=edge.Governor,edge.Dependent
        if (edge.begin,edge.end)!=(b.begin,b.end):
            raise ValueError('Relation target offsets changed')
        if edge.kind==xmi.GROUP_LINK:
            if a.groupId!=b.groupId or a.xmiID==b.xmiID:
                raise ValueError('Invalid discontinuity link')
            if (a.xmiID,b.xmiID) in links:
                raise ValueError('Duplicate discontinuity link')
            links.add((a.xmiID,b.xmiID))
        else:
            if a.xmiID!=heads[a.groupId] or b.xmiID!=heads[b.groupId]:
                raise ValueError('Semantic relation must connect group heads')
            relations.append({'id':edge.relationId,'from':a.groupId,'to':b.groupId,'kind':edge.kind})
    groups=[];expected_links=set()
    for key,members in sorted(grouped.items()):
        members.sort(key=lambda a:(a.begin,a.end))
        if len({a.label for a in members})!=1:
            raise ValueError('Conflicting group labels')
        expected_links.update((members[0].xmiID,a.xmiID) for a in members[1:])
        groups.append({'id':key,'label':members[0].label,'spans':[
            {'start':a.begin,'end':a.end,'quote':text[a.begin:a.end]} for a in members]})
    if links!=expected_links:
        raise ValueError('Missing, extra or redirected discontinuity links')
    packet=export(cas.sofa_string,actual,groups,sorted(relations,key=lambda r:r['id']))
    return {'packet':packet,'transformation':{'input_sha256':digest(raw),
            'operation':'Derive exact quotations and Unicode offsets from actual authored CAS selections',
            'source_sha256':actual['source_sha256'],'output_sha256':digest(packet),
            'independence':'NOT_ESTABLISHED'}}
