"""Independent original substitution targets and complete consumer comparisons."""
from copy import deepcopy
from scripts.prospectus_margin_preparation import AUTH,ROOT,read,sha
from scripts.prospectus_default_references import retained
from scripts.prospectus_typed_delta import equal

PREP=AUTH/'reviews/substitution-references-277'
KEY='basf-base-september-2022-exchange'
IDS=('substitution-certification','substitution-amendments')
DISCOVERY=KEY+':p129:l14:ref:17'
REPLACED=DISCOVERY+'@'+KEY+':p129:l14'


def expected(p,missing):
    raw={u['id']:u for u in p['P1']['payload']['graph']['units']}
    selected={u['unit']:u for u in p['P2']['payload']['assembly']['units']}
    packet=p['P3']['payload']['interpretation_input']['reference_admission']
    review=read(PREP/'source-review.json')
    for source in review['sources']:assert sha(ROOT/source['path'])==source['sha256']
    for path,checksum in review['images'].items():assert sha(ROOT/path)==checksum
    deps=[]
    for identity,line,phrase,ranges in (
        (IDS[0],35,'vorstehenden Unterabsätzen (a), (b), (c) und (d)',((128,75,81),(129,1,4),(129,12,22))),
        (IDS[1],14,'§ 11',((129,54,76),(130,1,2),(130,10,11),(130,23,74),(131,1,31)))):
        u=raw[f'{KEY}:p129:l{line}']
        start=u['raw'].index(phrase)
        source={'unit':u['id'],'document':u['document'],'source_sha256':u['source_sha256'],
            'start':start,'end':start+len(phrase),'quote':phrase}
        targets,target_rows,unknown=[],[],[]
        for page,first,last in ranges:
            for n in range(first,last+1):
                t=raw[f'{KEY}:p{page}:l{n}']
                offset=1 if (page,n) in ((129,12),(130,10)) else 0
                end=len(t['raw'])-1 if (page,n) in ((129,22),(130,11)) else len(t['raw'])
                role='UNKNOWN' if (page==130 and (n==2 or 31<=n<=38 or n==66)) or (page==131 and n in (5,13,24)) else 'OPERATIVE'
                assert selected[t['id']]['text']==t['raw'][offset:end] and selected[t['id']]['role']==role
                a={'unit':t['id'],'document':t['document'],'source_sha256':t['source_sha256'],
                    'start':offset,'end':end,'quote':t['raw'][offset:end]}
                targets.append({'unit':t['id'],'start':0,'end':len(a['quote']),'source':a})
                target_rows.append({'source':a,'use':t['id'],'language':t['language']})
                if role=='UNKNOWN':unknown.append(t['id'])
        reviewed=next(r for r in review['references'] if r['id']==identity)
        equal(reviewed['source'],source,'Original substitution source differs')
        equal(reviewed['targets'],target_rows,'Original complete substitution target differs')
        if identity in missing:
            deps.append({'id':'substitution-reference:'+identity,'questions':['Q1','Q2'],'status':'UNRESOLVED',
                'reason':'The complete substitution paragraph has no reviewed source link'})
        else:
            deps.append({'id':'reviewed-reference:'+identity,'questions':['Q1','Q2'],
                'status':'UNRESOLVED' if unknown else 'RESOLVED',
                'source_use':{'unit':u['id'],'start':start,'end':start+len(phrase),'source':source},
                'targets':targets,'form':'relative','discovery_ids':[] if identity==IDS[0] else [DISCOVERY],'authority':source,
                'review':packet['review'],'automatic_discovery':False,
                **({'source_binding':'RESOLVED','unknown_target_uses':sorted(unknown)} if unknown else {})})
    assert 'Negativverpflichtung' in raw[f'{KEY}:p129:l13']['raw']
    assert '72 Stunden' in raw[f'{KEY}:p131:l26']['raw']
    assert selected[f'{KEY}:p129:l30']['role']=='EXCLUDED'
    assert selected[f'{KEY}:p130:l19']['role']=='EXCLUDED'
    return deps


def questions(original,extra,missing):
    result=deepcopy(original)
    required={d['id'] for d in extra if d['status']=='UNRESOLVED'}
    for q in ('Q1','Q2'):
        nodes=[result[q],*result[q].get('subquestions',{}).values()]
        if 'Q3' in result and q in result['Q3'].get('value',{}):nodes.append(result['Q3']['value'][q])
        for node in nodes:
            prior=set(node['unresolved'])
            if IDS[1] not in missing:prior.discard(REPLACED)
            node['unresolved']=sorted(prior|required)
    return result


def verify(p,answer=None,*,missing=()):
    before,old_answer=retained('candidate-answer')
    for stage in ('P1','P2'):equal(p[stage],before[stage],'Source/construction changed')
    old,got=before['P3']['payload'],p['P3']['payload']
    extra=expected(p,missing)
    wanted=deepcopy(old['dependencies'])
    if IDS[1] not in missing:wanted=[d for d in wanted if d['id']!=REPLACED]
    unresolved={'Unresolved reference: '+d['id'] for d in extra
        if d['status']=='UNRESOLVED' and d.get('source_binding')=='RESOLVED'}
    for q in ('Q1','Q2'):
        closure=next(d for d in wanted if d['id']=='reference-closure:'+q)
        prior=set(closure['unresolved'])
        if IDS[1] not in missing:prior.remove('Unresolved reference: '+REPLACED)
        closure['unresolved']=sorted(prior|unresolved)
    wanted+=extra
    equal(sorted(got['dependencies'],key=lambda d:d['id']),sorted(wanted,key=lambda d:d['id']),'Complete dependencies changed')
    equal(got['questions'],questions(old['questions'],extra,missing),'Unexpected semantic question change')
    value=deepcopy(old['interpretation_input'])
    value['reference_admission']['version']='reviewed-references.v3'
    value['reference_admission']['references'].extend(r for r in read(PREP/'packet.json')['references'] if r['id'] not in missing)
    equal(got['interpretation_input'],value,'Unexpected interpretation input')
    omit={'dependencies','questions','interpretation_input'}
    equal({k:v for k,v in got.items() if k not in omit},{k:v for k,v in old.items() if k not in omit},'Existing meaning changed')
    if answer is not None:
        for stage in ('P4','P5'):equal(p[stage]['payload'],before[stage]['payload'],'Legal/financial content changed')
        equal(answer['questions'],questions(old_answer['questions'],extra,missing),'Unexpected ordinary question change')
        omit={'questions','consumed_products','report_sha256','substitution_references'}
        equal({k:v for k,v in answer.items() if k not in omit},{k:v for k,v in old_answer.items() if k not in omit},'Unrelated whole answer changed')
        report=answer['substitution_references']
        equal(report['references'],read(PREP/'source-review.json')['references'],'Lost original substitution targets')
        equal(report['missing'],list(missing),'Missing substitution report differs')
        equal(report['unknown_target_uses'],sorted([f'{KEY}:p130:l{n}' for n in (2,*range(31,39),66)]+[f'{KEY}:p131:l{n}' for n in (5,13,24)]),'Unresolved substitution meanings changed')
        assert report['status']==('UNREVIEWED' if missing else 'REVIEWED')
        assert report['actual_substitution_compliance']=='UNKNOWN' and not report['complete_reference_graph']
        equal(answer['consumed_products'],{k:v['sha256'] for k,v in p.items()},'Wrong consumed products')
    return {'status':'PASS','independent_links':2,'target_lines':[22,110],
        'unknown_target_uses':13,'missing':list(missing),'complete_answer_checked':answer is not None,'original_task_complete':False}
