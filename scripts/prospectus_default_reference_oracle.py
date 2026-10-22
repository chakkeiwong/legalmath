"""Independent original default targets and complete consumer comparisons."""
from copy import deepcopy
from scripts.prospectus_margin_preparation import AUTH,ROOT,read,sha
from scripts.prospectus_governance_references import retained
from scripts.prospectus_typed_delta import equal

PREP=AUTH/'reviews/default-references-276'
KEY='basf-base-september-2022-exchange'
IDS=('default-quorum-trigger','default-quorum-exceptions','default-notice-scope')


def expected(p,missing):
    raw={u['id']:u for u in p['P1']['payload']['graph']['units']}
    selected={u['unit']:u for u in p['P2']['payload']['assembly']['units']}
    packet=p['P3']['payload']['interpretation_input']['reference_admission']
    review=read(PREP/'source-review.json')
    for source in review['sources']:assert sha(ROOT/source['path'])==source['sha256']
    for path,checksum in review['images'].items():assert sha(ROOT/path)==checksum
    deps=[]
    for identity,line,phrase,ranges in (
        (IDS[0],24,'Absatz (1)(b) und/oder (1)(c)',((126,46,75),(127,1,5))),
        (IDS[1],25,'Absatz (1)(a) und (1)(d) bis (g)',((126,44,45),(127,6,21))),
        (IDS[2],43,'Absatz (1)',((126,41,75),(127,1,23)))):
        u=raw[f'{KEY}:p127:l{line}']
        start=u['raw'].index(phrase)
        source={'unit':u['id'],'document':u['document'],'source_sha256':u['source_sha256'],
            'start':start,'end':start+len(phrase),'quote':phrase}
        targets,target_rows,unknown=[],[],[]
        for page,first,last in ranges:
            for n in range(first,last+1):
                t=raw[f'{KEY}:p{page}:l{n}']
                offset=1 if page==126 and n==41 else 0
                role='UNKNOWN' if page==127 and 12<=n<=16 else 'OPERATIVE'
                assert selected[t['id']]['text']==t['raw'][offset:] and selected[t['id']]['role']==role
                a={'unit':t['id'],'document':t['document'],'source_sha256':t['source_sha256'],
                    'start':offset,'end':len(t['raw']),'quote':t['raw'][offset:]}
                targets.append({'unit':t['id'],'start':0,'end':len(a['quote']),'source':a})
                target_rows.append({'source':a,'use':t['id'],'language':t['language']})
                if role=='UNKNOWN':unknown.append(t['id'])
        reviewed=next(r for r in review['references'] if r['id']==identity)
        equal(reviewed['source'],source,'Original default source differs')
        equal(reviewed['targets'],target_rows,'Original complete default target differs')
        if identity in missing:
            deps.append({'id':'default-reference:'+identity,'questions':['Q1','Q2'],'status':'UNRESOLVED',
                'reason':'The complete default paragraph has no reviewed source link'})
        else:
            deps.append({'id':'reviewed-reference:'+identity,'questions':['Q1','Q2'],
                'status':'UNRESOLVED' if unknown else 'RESOLVED',
                'source_use':{'unit':u['id'],'start':start,'end':start+len(phrase),'source':source},
                'targets':targets,'form':'relative','discovery_ids':[],'authority':source,
                'review':packet['review'],'automatic_discovery':False,
                **({'source_binding':'RESOLVED','unknown_target_uses':sorted(unknown)} if unknown else {})})
    assert 'gutem Glauben' in raw[f'{KEY}:p127:l2']['raw']
    assert 'erlischt' in raw[f'{KEY}:p127:l22']['raw']
    assert 'geheilt' in raw[f'{KEY}:p127:l23']['raw']
    return deps


def questions(original,extra):
    result=deepcopy(original)
    required={d['id'] for d in extra if d['status']=='UNRESOLVED'}
    for q in ('Q1','Q2'):
        nodes=[result[q],*result[q].get('subquestions',{}).values()]
        if 'Q3' in result and q in result['Q3'].get('value',{}):nodes.append(result['Q3']['value'][q])
        for node in nodes:node['unresolved']=sorted(set(node['unresolved'])|required)
    return result


def verify(p,answer=None,*,missing=()):
    before,old_answer=retained('candidate-answer')
    for stage in ('P1','P2'):equal(p[stage],before[stage],'Source/construction changed')
    old,got=before['P3']['payload'],p['P3']['payload']
    extra=expected(p,missing)
    wanted=deepcopy(old['dependencies'])
    unresolved={'Unresolved reference: '+d['id'] for d in extra
        if d['status']=='UNRESOLVED' and d.get('source_binding')=='RESOLVED'}
    for q in ('Q1','Q2'):
        closure=next(d for d in wanted if d['id']=='reference-closure:'+q)
        closure['unresolved']=sorted(set(closure['unresolved'])|unresolved)
    wanted+=extra
    equal(sorted(got['dependencies'],key=lambda d:d['id']),sorted(wanted,key=lambda d:d['id']),'Complete dependencies changed')
    equal(got['questions'],questions(old['questions'],extra),'Unexpected semantic question change')
    value=deepcopy(old['interpretation_input'])
    value['reference_admission']['version']='reviewed-references.v3'
    value['reference_admission']['references'].extend(r for r in read(PREP/'packet.json')['references'] if r['id'] not in missing)
    equal(got['interpretation_input'],value,'Unexpected interpretation input')
    omit={'dependencies','questions','interpretation_input'}
    equal({k:v for k,v in got.items() if k not in omit},{k:v for k,v in old.items() if k not in omit},'Existing meaning changed')
    if answer is not None:
        for stage in ('P4','P5'):equal(p[stage]['payload'],before[stage]['payload'],'Legal/financial content changed')
        equal(answer['questions'],questions(old_answer['questions'],extra),'Unexpected ordinary question change')
        omit={'questions','consumed_products','report_sha256','default_references'}
        equal({k:v for k,v in answer.items() if k not in omit},{k:v for k,v in old_answer.items() if k not in omit},'Unrelated whole answer changed')
        report=answer['default_references']
        equal(report['references'],read(PREP/'source-review.json')['references'],'Lost original default targets')
        equal(report['missing'],list(missing),'Missing default report differs')
        equal(report['unknown_target_uses'],[f'{KEY}:p127:l{n}' for n in range(12,17)],'Unresolved default meanings changed')
        assert report['status']==('UNREVIEWED' if missing else 'REVIEWED')
        assert report['actual_default_compliance']=='UNKNOWN' and not report['complete_reference_graph']
        equal(answer['consumed_products'],{k:v['sha256'] for k,v in p.items()},'Wrong consumed products')
    return {'status':'PASS','independent_links':3,'target_lines':[35,18,58],
        'unknown_target_uses':5,'missing':list(missing),'complete_answer_checked':answer is not None,'original_task_complete':False}
