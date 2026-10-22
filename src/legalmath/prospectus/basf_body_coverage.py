"""Explain pending body intervals while preserving every unknown legal effect."""
from collections import Counter
from copy import deepcopy
from pathlib import Path

from . import basf_body_spec as spec
from .successor.anchors import bind, fields
from .successor.contracts import digest
from .successor.meaning_coverage import explain
from .successor.occurrences import anchor, segments

VERSION = 'basf-pending-body-review.v1'


def selected_sources(graph, unit, start, end, *, raw=None):
    """Clip only checked COPY mappings; selected offsets are not raw offsets."""
    raw = {u['id']:u for u in graph['units']} if raw is None else raw
    if len(raw)!=len(graph['units']):
        raise ValueError('Duplicate original source unit')
    if type(start) is not int or type(end) is not int or not 0<=start<end<=len(unit['text']):
        raise ValueError('Invalid selected interval')
    out=[];cursor=start
    pieces=sorted(segments(graph,unit,_raw=raw),key=lambda r:(r['start'],r['end']))
    for piece in pieces:
        left,right=max(start,piece['start']),min(end,piece['end'])
        if left>=right: continue
        if left!=cursor:
            raise ValueError('Missing or overlapping raw-to-selected mapping')
        source=piece['source'];a=source['start']+left-piece['start'];b=a+right-left
        exact=anchor(raw[source['unit']],a,b)
        if exact['quote']!=unit['text'][left:right]:
            raise ValueError('Raw-to-selected text changed')
        out.append({'selected_start':left,'selected_end':right,'source':exact});cursor=right
    if cursor!=end:
        raise ValueError('Incomplete raw-to-selected mapping')
    return out


def inventory(products):
    graph=products['P1']['payload']['graph'];p2=products['P2']['payload'];p3=products['P3']['payload']
    assembly=p2['assembly'];clauses=p3['clauses']
    coverage=explain(graph,p2['selected_contract'],assembly,clauses)
    raw={u['id']:u for u in graph['units']};selected={u['unit']:u for u in assembly['units']}
    unknown={}
    for node in clauses['nodes']:
        if node['effect']=='unknown':
            for s in node['spans']:
                unknown.setdefault(s['unit'],[]).append({'node':node['id'],**s})
    rows=[]
    for pending in coverage['selected_body_pending']:
        key=pending['unit'];u=selected[key];original=raw[key]
        if original['document']!=spec.DOCUMENT or not original['visible'] or original['text_sha256']!=digest(original['raw'].encode()):
            raise ValueError('Pending original body source changed')
        spans=[]
        for s in unknown.get(key,[]):
            spans.append({**s,'quote':u['text'][s['start']:s['end']],
                'sources':selected_sources(graph,u,s['start'],s['end'],raw=raw)})
        if pending['uncovered_characters'] or not spans:
            raise ValueError('This finite review requires the retained complete pending spans')
        rows.append({'unit':key,'page':original['page'],'line':original['order'],
            'original':anchor(original),'bbox':original['bbox'],'selected_text':u['text'],
            'assembly_role':u['role'],'coverage':pending,'spans':spans})
    return coverage,rows


def reviewed_roles(row):
    expected=spec.REVIEW.get((row['page'],row['line']))
    if expected is None or len(expected)!=len(row['spans']):
        raise ValueError('Pending source outside the finite reviewed inventory')
    roles=[]
    for span,(start,end,role,text) in zip(row['spans'],expected):
        end=len(row['selected_text']) if end is None else end
        if (span['start'],span['end'])!=(start,end) or ' '.join(span['quote'].split())!=text:
            raise ValueError('Reviewed pending caption or substantive wording changed')
        roles.append(role)
    return roles


def meeting_heading(rows):
    indexed={(r['page'],r['line']):r for r in rows}
    chosen=[indexed[(130,n)] for n in spec.MEETING_ORDER]
    quote=' '.join(' '.join(r['selected_text'].split()) for r in chosen)
    if quote!=spec.MEETING_TEXT:
        raise ValueError('Complete meeting-heading reading changed')
    return {'original_occurrence_order':[indexed[(130,n)]['unit'] for n in sorted(spec.MEETING_ORDER)],
            'reviewed_reading_order':[r['unit'] for r in chosen],'quote':quote,
            'basis':'SUPPLIED_ORIGINAL_IMAGE_REVIEW','legal_effect_resolved':False}


def evaluate(products,prior,profile,root,*,expected_profile_sha256):
    keys={'version','products_sha256','prior_sha256','reviewer','source','rows','meeting_heading',
          'legal_scope_resolved','independent_legal_acceptance','unknowns_resolved'}
    fields(profile,keys,keys)
    if (profile['version']!=VERSION or digest(profile)!=expected_profile_sha256 or
            profile['products_sha256']!=digest(products) or profile['prior_sha256']!=digest(prior)):
        raise ValueError('Pinned body review or complete comparator changed')
    if (profile['legal_scope_resolved'] is not False or profile['independent_legal_acceptance'] is not False
            or type(profile['unknowns_resolved']) is not int or profile['unknowns_resolved']!=0):
        raise ValueError('Structural context cannot resolve legal unknowns or establish independent acceptance')
    reviewer=profile['reviewer']
    fields(reviewer,{'identity','basis','independent'},{'identity','basis','independent'})
    if (not isinstance(reviewer['identity'],str) or not reviewer['identity'].strip() or
            reviewer['basis']!='AGENT_EXPOSED_DEVELOPMENT_REVIEW' or reviewer['independent'] is not False):
        raise ValueError('Unsupported body review authority')
    coverage,expected_rows=inventory(products)
    if coverage!=prior['answer']['meaning_coverage']:
        raise ValueError('Full prior meaning coverage differs from actual products')
    expected_keys={spec.DOCUMENT+':p'+str(p)+':l'+str(n) for p,n in spec.REVIEW}
    if {r['unit'] for r in expected_rows}!=expected_keys:
        raise ValueError('Complete pending body inventory changed')
    if [r.get('unit') for r in profile['rows']]!=[r['unit'] for r in expected_rows]:
        raise ValueError('Missing, duplicate or reordered pending occurrence')
    source=profile['source']
    fields(source,{'document','path','sha256','images'},{'document','path','sha256','images'})
    document=next(d for d in products['P1']['payload']['request']['bundle']['documents'] if d['id']==spec.DOCUMENT)
    if {k:source[k] for k in ('path','sha256')}!={k:document[k] for k in ('path','sha256')} or source['document']!=spec.DOCUMENT:
        raise ValueError('Original body source edition changed')
    pages=sorted({r['page'] for r in expected_rows})
    if [r.get('page') for r in source['images']]!=pages:
        raise ValueError('Complete original-image page inventory required')
    for row in source['images']: fields(row,{'page','path','sha256'},{'page','path','sha256'})
    root=Path(root).resolve()
    for item in [source,*source['images']]:
        name=item['path'];p=(root/name).resolve()
        if Path(name).is_absolute() or not p.is_relative_to(root) or not p.is_file() or digest(p.read_bytes())!=item['sha256']:
            raise ValueError('Original body PDF or inspected image changed')
    output=[];by_role=Counter();characters=Counter();unit_kinds=Counter()
    for row,expected in zip(profile['rows'],expected_rows):
        fields(row,set(expected)|{'roles'},set(expected)|{'roles'})
        if {k:v for k,v in row.items() if k!='roles'}!=expected:
            raise ValueError('Exact original/selected interval, mapping or coverage changed')
        roles=reviewed_roles(expected)
        if row['roles']!=roles:
            raise ValueError('Reviewed structural/substantive classification changed')
        structural=any(r in spec.STRUCTURAL for r in roles)
        substantive=any(r not in spec.STRUCTURAL for r in roles)
        unit_kinds['mixed' if structural and substantive else 'structural_only' if structural else 'substantive_only']+=1
        seen=set()
        for span,role in zip(row['spans'],roles):
            indexes={i for i in range(span['start'],span['end']) if not row['selected_text'][i].isspace()}
            if seen & indexes:
                raise ValueError('Unknown characters credited twice')
            seen.update(indexes);by_role[role]+=1;characters[role]+=len(indexes)
        if len(seen)!=row['coverage']['unknown_characters']:
            raise ValueError('Unknown character accounting differs')
        output.append(deepcopy(row))
    heading=meeting_heading(expected_rows)
    if profile['meeting_heading']!=heading:
        raise ValueError('Supplied meeting-heading order changed')
    questions=[]
    for role,question in spec.QUESTIONS.items():
        evidence=[{'unit':r['unit'],'page':r['page'],'spans':[s for s,c in zip(r['spans'],r['roles']) if c==role]}
                  for r in output if role in r['roles']]
        questions.append({'id':role,**question,'evidence':evidence,'status':'UNRESOLVED'})
    return {'version':VERSION,'profile_sha256':digest(profile),'reviewer':deepcopy(reviewer),
        'source':deepcopy(source),'original_meaning_coverage':deepcopy(coverage),'rows':output,
        'meeting_heading':heading,'remaining_questions':questions,
        'counts':{'pending_units':len(output),'unknown_spans':sum(by_role.values()),
                  'unknown_characters':sum(characters.values()),'units_by_kind':dict(unit_kinds),
                  'spans_by_role':dict(by_role),'characters_by_role':dict(characters)},
        'count_role':'EXPLANATORY_ONLY','unknowns_resolved':0,'legal_scope_resolved':False,
        'independent_legal_acceptance':False,
        'structural_context':'Headings and captions remain available for interpretation; their supplied structural classification does not establish legal irrelevance or a known legal effect.',
        'question_scope':'Only the retained selected-body pending set; other sources, incorporation, applicable law, actual facts and independent acceptance remain separate.'}


def consume(products,prior_profiles,profile,root,*,expected_prior_profiles_sha256,expected_profile_sha256):
    from . import basf_hedge_note
    fields(prior_profiles,{'preceding','hedge'},{'preceding','hedge'})
    if digest(prior_profiles)!=expected_prior_profiles_sha256:
        raise ValueError('Pinned complete earlier profiles changed')
    old,hp=prior_profiles['preceding'],prior_profiles['hedge']
    prior=basf_hedge_note.consume(products,old,hp,root,
        expected_prior_profiles_sha256=digest(old),expected_profile_sha256=digest(hp))
    review=evaluate(products,prior,profile,root,expected_profile_sha256=expected_profile_sha256)
    return {**prior,'body_coverage_review':review}
