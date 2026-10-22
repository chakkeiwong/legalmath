"""Independent original paragraph bounds and full-answer comparisons."""
from copy import deepcopy
from scripts.prospectus_margin_preparation import AUTH,ROOT,read,sha
from scripts.prospectus_reference_integrity import retained
from scripts.prospectus_typed_delta import equal

PREP=AUTH/'reviews/governance-references-275'
KEY='basf-base-september-2022-exchange'
IDS=('governance-majority','governance-registration-proof')


def expected(p,missing):
    raw={u['id']:u for u in p['P1']['payload']['graph']['units']}
    selected={u['unit']:u for u in p['P2']['payload']['assembly']['units']}
    packet=p['P3']['payload']['interpretation_input']['reference_admission']
    review=read(PREP/'source-review.json')
    for source in review['sources']:assert sha(ROOT/source['path'])==source['sha256']
    for path,checksum in review['images'].items():assert sha(ROOT/path)==checksum
    deps=[]
    for identity,page,line,phrase,tp,first,last in (
        (IDS[0],129,57,'Absatz 2',129,63,68),
        (IDS[1],130,70,'Absatz (a)(ii) und (iii)',130,46,65)):
        u=raw[f'{KEY}:p{page}:l{line}']
        start=u['raw'].index(phrase)
        source={'unit':u['id'],'document':u['document'],'source_sha256':u['source_sha256'],
            'start':start,'end':start+len(phrase),'quote':phrase}
        targets=[]
        target_rows=[]
        for n in range(first,last+1):
            t=raw[f'{KEY}:p{tp}:l{n}']
            assert selected[t['id']]['text']==t['raw'] and selected[t['id']]['role']=='OPERATIVE'
            a={'unit':t['id'],'document':t['document'],'source_sha256':t['source_sha256'],
                'start':0,'end':len(t['raw']),'quote':t['raw']}
            targets.append({'unit':t['id'],'start':0,'end':len(t['raw']),'source':a})
            target_rows.append({'source':a,'use':t['id'],'language':t['language']})
        reviewed=next(r for r in review['references'] if r['id']==identity)
        equal(reviewed['source'],source,'Original governance source differs')
        equal(reviewed['targets'],target_rows,'Original complete governance target differs')
        if identity in missing:
            deps.append({'id':'governance-reference:'+identity,'questions':['Q1','Q2'],'status':'UNRESOLVED',
                'reason':'The complete governance paragraph has no reviewed source link'})
        else:
            deps.append({'id':'reviewed-reference:'+identity,'questions':['Q1','Q2'],'status':'RESOLVED',
                'source_use':{'unit':u['id'],'start':start,'end':start+len(phrase),'source':source},
                'targets':targets,'form':'relative','discovery_ids':[],'authority':source,
                'review':packet['review'],'automatic_discovery':False})
    assert 'einfachen Mehrheit' in raw[f'{KEY}:p129:l67']['raw']
    assert 'SchVG' in raw[f'{KEY}:p129:l66']['raw']
    assert raw[f'{KEY}:p129:l69']['raw'].startswith('(3)')
    assert raw[f'{KEY}:p130:l66']['raw'].startswith('(b)')
    return deps


def questions(original,missing):
    result=deepcopy(original)
    for q in ('Q1','Q2'):
        nodes=[result[q],*result[q].get('subquestions',{}).values()]
        if 'Q3' in result and q in result['Q3'].get('value',{}):nodes.append(result['Q3']['value'][q])
        for node in nodes:node['unresolved']=sorted(set(node['unresolved'])|{'governance-reference:'+k for k in missing})
    return result


def verify(p,answer=None,*,missing=()):
    before,old_answer=retained('candidate-answer')
    for stage in ('P1','P2'):equal(p[stage],before[stage],'Source/construction changed')
    old,got=before['P3']['payload'],p['P3']['payload']
    wanted=old['dependencies']+expected(p,missing)
    equal(sorted(got['dependencies'],key=lambda d:d['id']),sorted(wanted,key=lambda d:d['id']),'Complete dependencies changed')
    equal(got['questions'],questions(old['questions'],missing),'Unexpected semantic question change')
    value=deepcopy(old['interpretation_input'])
    value['reference_admission']['references'].extend(r for r in read(PREP/'packet.json')['references'] if r['id'] not in missing)
    equal(got['interpretation_input'],value,'Unexpected interpretation input')
    omit={'dependencies','questions','interpretation_input'}
    equal({k:v for k,v in got.items() if k not in omit},{k:v for k,v in old.items() if k not in omit},'Existing meaning changed')
    if answer is not None:
        for stage in ('P4','P5'):equal(p[stage]['payload'],before[stage]['payload'],'Legal/financial content changed')
        equal(answer['questions'],questions(old_answer['questions'],missing),'Unexpected ordinary question change')
        omit={'questions','consumed_products','report_sha256','governance_references'}
        equal({k:v for k,v in answer.items() if k not in omit},{k:v for k,v in old_answer.items() if k not in omit},'Unrelated whole answer changed')
        report=answer['governance_references']
        equal(report['references'],read(PREP/'source-review.json')['references'],'Lost original governance targets')
        equal(report['missing'],list(missing),'Missing governance report differs')
        assert report['status']==('UNREVIEWED' if missing else 'REVIEWED')
        assert report['actual_governance_compliance']=='UNKNOWN' and not report['complete_reference_graph']
        equal(answer['consumed_products'],{k:v['sha256'] for k,v in p.items()},'Wrong consumed products')
    return {'status':'PASS','independent_links':2,'target_lines':[6,20],
        'missing':list(missing),'complete_answer_checked':answer is not None,'original_task_complete':False}
